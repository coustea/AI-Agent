"""Chat 私有记忆管线与持久化门面。

核心类 ChatMemoryService 是记忆操作的统一入口，编排两阶段后处理管线：
  after_turn → post_turn:
    1. 压缩(compressor.maybe_compress) — 短期消息过多时生成摘要块
    2. 长期记忆(long_term_memory.maybe_update) — 检测稳定信号并增量更新

画像更新由 ChatUseCases 的智能辅导后置管线在记忆管线之后串行触发，
避免与压缩/长期记忆同时争抢同一个会话计数器。

其余方法提供会话 CRUD、消息存取、摘要查询等基础能力。

内联模块（原 persistence.py 合并）：
  - TranscriptEvent / TurnTranscript — transcript 事件模型
  - ChatPersistenceAdapter — transcript 持久化适配器（追加事件 + 终态落盘）

单例管理：get_chat_memory_service(module=) 按 module 缓存实例。
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlmodel import func, select

from app.chat.memory.compression import ChatSessionCompressor
from app.chat.memory.long_term import ChatLongTermMemoryService
from app.chat.memory.types import (
    DEFAULT_SESSION_TITLE,
    LTM_CATEGORY_NAMES,
    MESSAGE_EXPIRE_DAYS,
    TITLE_MAX_LENGTH,
    estimate_token_count,
    now,
)
from app.infra.database import session_scope
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import (
    ChatAttachmentAnalysis,
    ChatLongTermMemory,
    ChatMessageAttachment,
    ChatMessage,
    ChatSession,
    ChatSessionSummaryBlock,
    ChatToolInvocation,
    ChatTurn,
    ChatTurnTranscript,
    ChatUploadedFile,
)

logger = get_logger(__name__)

# -----------------------------------------------------------------------
# 常量定义
# -----------------------------------------------------------------------

# 压缩保留的最近原始消息数（压缩后仍保留这 8 条不被摘要化）
RECENT_RAW_MESSAGES = 8
# 触发压缩的最小消息数（消息数 ≥ 14 时才考虑压缩）
COMPRESS_MIN_MESSAGES = 14
# 触发压缩的最小 token 数（token ≥ 3500 时才考虑压缩）
COMPRESS_MIN_TOKENS = 3500
# 注入 system prompt 的最大摘要块数
SUMMARY_CONTEXT_BLOCKS = 3
# 长期记忆更新的轮次间隔（每 8 轮检查一次）
LTM_PERIODIC_TURNS = 8
# 长期记忆更新的最低置信度阈值
LTM_MIN_CONFIDENCE = 0.75
# 长期记忆更新的冷却期（分钟），防止频繁写入
LTM_UPDATE_COOLDOWN_MINUTES = 30


# -----------------------------------------------------------------------
# Transcript 模型（原 persistence.py 内联）
#
# Transcript 是一个 turn 的完整事件记录，包含：
#   - events：有序事件列表（如 tool_call、thought、search_result 等）
#   - final_answer：最终回复文本
#   - constraint_report：约束检查报告（如安全拒绝原因）
#
# 以 JSON 形式存储在 ChatTurnTranscript.transcript_json 列中，
# 避免为每个事件创建独立行，保证事件序列的原子性和有序性。
# -----------------------------------------------------------------------

class TranscriptEvent(BaseModel):
    """单条 transcript 事件：事件类型 + 负载数据。"""
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class TurnTranscript(BaseModel):
    """一个 turn 的完整 transcript，包含事件列表、最终答案和约束报告。"""
    turn_id: int | None = None
    events: list[TranscriptEvent] = Field(default_factory=list)
    final_answer: str = ""
    constraint_report: dict[str, Any] | None = None

    def append(self, event_type: str, **payload: Any) -> None:
        """向事件列表追加一条新事件。"""
        self.events.append(TranscriptEvent(event_type=event_type, payload=payload))


class ChatPersistenceAdapter:
    # -------------------------------------------------------------------
    # append_transcript_event: 追加单条 transcript 事件到指定 turn
    #
    # 工作流：
    #   1. 按 turn_id 查询是否已有 transcript 行
    #   2. 有 → 反序列化现有 JSON；无 → 创建空 TurnTranscript
    #   3. append(event_type, payload) 追加事件
    #   4. 若为新行 → INSERT；若已有行 → UPDATE 覆写 transcript_json
    #   5. commit 落盘
    #
    # 为什么用 JSON 而非独立行：
    #   transcript 是一个 turn 的有序事件流，JSON 列保证原子追加
    #   且查询时一次性拿到完整事件序列，避免多次 JOIN。
    # -------------------------------------------------------------------
    async def append_transcript_event(
        self,
        *,
        turn_id: int,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        async with session_scope() as db:
            # 按 turn_id 查找已有的 transcript 行（首次调用时 row 为 None）
            row = (
                await db.exec(
                    select(ChatTurnTranscript).where(ChatTurnTranscript.turn_id == turn_id)
                )
            ).first()
            transcript = TurnTranscript()
            # 若已有行且 JSON 合法，反序列化恢复状态
            if row is not None and isinstance(row.transcript_json, dict):
                transcript = TurnTranscript.model_validate(row.transcript_json)
            transcript.turn_id = turn_id
            # 追加新事件到事件列表
            transcript.append(event_type, **(payload or {}))
            # 根据是否新建决定 INSERT 还是 UPDATE
            if row is None:
                row = ChatTurnTranscript(
                    turn_id=turn_id,
                    transcript_json=transcript.model_dump(),
                    final_answer=transcript.final_answer,
                )
            else:
                row.transcript_json = transcript.model_dump()
                row.final_answer = transcript.final_answer
            db.add(row)
            await db.commit()

    # -------------------------------------------------------------------
    # finalize_turn: 结束一个 turn 的 transcript，写入最终答案和约束报告
    #
    # 与 append_transcript_event 的区别：
    #   - append 是增量追加事件（流式过程中调用）
    #   - finalize 是终态落盘（turn 结束后一次性写入）
    #
    # constraint_report 记录本轮对话是否符合约束规则（如拒绝违规请求），
    # 供后续分析和审计使用。
    # -------------------------------------------------------------------
    async def finalize_turn(
        self,
        *,
        turn_id: int,
        final_answer: str,
        constraint_report: dict[str, Any] | None = None,
    ) -> None:
        async with session_scope() as db:
            # 查询已有 transcript 行（通常 finalize 时行已存在）
            row = (
                await db.exec(
                    select(ChatTurnTranscript).where(ChatTurnTranscript.turn_id == turn_id)
                )
            ).first()
            # 构造终态 TurnTranscript 对象
            transcript = TurnTranscript(turn_id=turn_id, final_answer=final_answer)
            if row is not None and isinstance(row.transcript_json, dict):
                transcript = TurnTranscript.model_validate(row.transcript_json)
                transcript.turn_id = turn_id
                transcript.final_answer = final_answer
            # 附加约束报告（如安全检查结果）
            transcript.constraint_report = constraint_report
            # INSERT 或 UPDATE 落盘
            if row is None:
                row = ChatTurnTranscript(
                    turn_id=turn_id,
                    transcript_json=transcript.model_dump(),
                    final_answer=final_answer,
                    constraint_report_json=constraint_report,
                )
            else:
                row.transcript_json = transcript.model_dump()
                row.final_answer = final_answer
                row.constraint_report_json = constraint_report
            db.add(row)
            await db.commit()


class ChatMemoryService:
    """Chat-owned memory pipeline and persistence facade."""

    # -------------------------------------------------------------------
    # __init__: 初始化记忆管线的三大组件
    #
    # 组件职责：
    #   compressor        — 短期记忆压缩：消息过多时将旧消息摘要化
    #   long_term_memory  — 长期记忆更新：检测稳定信号（如重复出现的知识偏好）
    #                       并增量写入长期记忆 markdown
    #   persistence       — transcript 持久化：事件追加 + 终态落盘
    #   llm               — LLM 实例，供标题生成等辅助功能使用
    #
    # module 参数区分不同业务模块（mentor/quiz 等），
    # 确保各模块记忆互不干扰。
    # -------------------------------------------------------------------
    def __init__(self, *, module: str = "mentor") -> None:
        # 业务模块标识，用于数据库行的 module 字段隔离
        self.module = module
        # 压缩器：保留最近 8 条原始消息，超过 14 条或 3500 token 时触发压缩
        self.compressor = ChatSessionCompressor(
            module=module,
            keep_recent=RECENT_RAW_MESSAGES,
            min_messages=COMPRESS_MIN_MESSAGES,
            min_tokens=COMPRESS_MIN_TOKENS,
        )
        # 长期记忆服务：每 8 轮检查一次，置信度 ≥ 0.75 才写入，冷却期 30 分钟
        self.long_term_memory = ChatLongTermMemoryService(
            module=module,
            periodic_turns=LTM_PERIODIC_TURNS,
            min_confidence=LTM_MIN_CONFIDENCE,
            cooldown_minutes=LTM_UPDATE_COOLDOWN_MINUTES,
        )
        # transcript 持久化适配器，负责事件追加和终态落盘
        self.persistence = ChatPersistenceAdapter()
        # LLM 实例，用于标题生成等需要语言模型的辅助功能
        self.llm = get_llm()

    # -------------------------------------------------------------------
    # create_session: 创建新的聊天会话
    #
    # 每个 session 属于一个用户和一个模块（如 mentor/quiz），
    # 初始标题为 DEFAULT_SESSION_TITLE，后续由 generate_session_title 自动更新。
    # 返回创建的 session 对象（含自动生成的 id 和时间戳）。
    # -------------------------------------------------------------------
    async def create_session(self, *, user_id: int, title: str = DEFAULT_SESSION_TITLE) -> Any:
        async with session_scope() as db:
            chat_session = ChatSession(user_id=user_id, module=self.module, title=title)
            db.add(chat_session)
            await db.commit()
            await db.refresh(chat_session)
            return chat_session

    # -------------------------------------------------------------------
    # list_sessions: 获取用户未归档的会话列表
    #
    # 按 updated_at 降序排列（最近活跃的在前），限制返回数量。
    # 仅返回当前模块的会话，不同模块的会话互不可见。
    # -------------------------------------------------------------------
    async def list_sessions(self, *, user_id: int, limit: int = 20) -> list[Any]:
        async with session_scope() as db:
            stmt = (
                select(ChatSession)
                .where(
                    ChatSession.user_id == user_id,
                    ChatSession.is_archived.is_(False),
                    ChatSession.module == self.module,
                )
                .order_by(ChatSession.updated_at.desc())
                .limit(limit)
            )
            return list((await db.exec(stmt)).all())

    # -------------------------------------------------------------------
    # archive_session: 归档指定会话（软删除）
    #
    # 将 is_archived 设为 True，会话不再出现在 list_sessions 中，
    # 但数据仍保留在数据库中供审计和恢复使用。
    # 返回 True 表示归档成功，False 表示 session 不存在或无权限。
    # -------------------------------------------------------------------
    async def archive_session(self, *, user_id: int, session_id: str) -> bool:
        async with session_scope() as db:
            chat_session = (
                await db.exec(
                    select(ChatSession).where(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id,
                    )
                )
            ).first()
            if not chat_session:
                return False
            chat_session.is_archived = True
            chat_session.updated_at = now()
            db.add(chat_session)
            await db.commit()
            return True

    # -------------------------------------------------------------------
    # update_session_title: 更新会话标题
    #
    # 标题截断到 TITLE_MAX_LENGTH 字符，防止过长标题影响 UI 展示。
    # 返回 True 表示更新成功，False 表示 session 不存在或无权限。
    # -------------------------------------------------------------------
    async def update_session_title(self, *, user_id: int, session_id: str, title: str) -> bool:
        async with session_scope() as db:
            chat_session = (
                await db.exec(
                    select(ChatSession).where(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id,
                    )
                )
            ).first()
            if not chat_session:
                return False
            chat_session.title = title[:TITLE_MAX_LENGTH]
            chat_session.updated_at = now()
            db.add(chat_session)
            await db.commit()
            return True

    # -------------------------------------------------------------------
    # save_message: 持久化单条聊天消息及其附件分析结果
    #
    # 工作流：
    #   1. 查找/创建 session（upsert），更新 updated_at
    #   2. 校验 session 所属用户和模块（权限检查）
    #   3. 构造 ChatMessage 并 flush 获取 message.id
    #   4. 遍历 attachment_analyses，为每条非空分析写入 ChatAttachmentAnalysis
    #   5. 一次性 commit 提交所有变更
    #
    # 为什么用 flush 而非直接 commit：
    #   需要 message.id 来关联 attachment_analyses，flush 后 id 可用
    #   但仍在一个事务内，便于原子提交。
    # -------------------------------------------------------------------
    async def save_message(
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        knowledge_sources: list[dict[str, Any]] | None = None,
        attachment_analyses: list[dict[str, Any]] | None = None,
        teaching_diagram: dict[str, Any] | None = None,
        usage_metadata: dict[str, Any] | None = None,
        turn_id: int | None = None,
        message_kind: str | None = None,
    ) -> ChatMessage:
        async with session_scope() as db:
            # 查找 session，不存在则自动创建（隐式 upsert）
            chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
            if chat_session:
                # 权限校验：session 必须属于当前用户且匹配模块
                if chat_session.user_id != user_id or chat_session.module != self.module:
                    raise PermissionError("会话不属于当前用户或模块")
                # 更新 session 的最后活跃时间
                chat_session.updated_at = now()
            else:
                # session 不存在时自动创建（首次发消息的场景）
                chat_session = ChatSession(id=session_id, user_id=user_id, module=self.module)
            db.add(chat_session)
            # 构造消息实体，包含角色、内容、工具调用、知识来源等所有元数据
            message = ChatMessage(
                user_id=user_id,
                session_id=session_id,
                turn_id=turn_id,
                module=self.module,
                role=role,
                message_kind=message_kind,
                content=content,
                attachments=attachments,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id,
                knowledge_sources=knowledge_sources,
                teaching_diagram=teaching_diagram,
                usage_metadata=usage_metadata,
            )
            db.add(message)
            # flush 以获取 message.id，后续 attachment 分析需要引用此 id
            await db.flush()

            # 为每条附件分析结果创建独立的分析记录
            for analysis in attachment_analyses or []:
                # 跳过没有有效摘要文本的分析条目
                summary_text = str(analysis.get("summary_text") or "").strip()
                if not summary_text:
                    continue
                db.add(
                    ChatAttachmentAnalysis(
                        user_id=user_id,
                        session_id=session_id,
                        message_id=message.id,
                        file_id=analysis.get("file_id"),
                        file_name=analysis.get("file_name"),
                        file_url=analysis.get("file_url"),
                        turn_id=turn_id,
                        module=self.module,
                        analysis_type=str(analysis.get("analysis_type") or "general"),
                        summary_text=summary_text,
                        extracted_text=analysis.get("extracted_text"),
                        structured_json=analysis.get("structured_json"),
                    )
                )

            # 原子提交：消息 + 所有附件分析在同一个事务中落盘
            await db.commit()
            return message

    # -------------------------------------------------------------------
    # save_tool_invocations: 批量保存工具调用记录
    #
    # 在 assistant 发起工具调用后调用，记录每次工具调用的：
    #   - tool_call_id（LLM 生成的调用标识）
    #   - tool_name（工具名称，如 web_search、calculate）
    #   - arguments_json（输入参数）
    #   - result_text / result_json（执行结果）
    #   - status（success / error）
    #
    # 空列表时直接返回，避免不必要的数据库操作。
    # -------------------------------------------------------------------
    async def save_tool_invocations(
        self,
        *,
        user_id: int,
        session_id: str,
        invocations: list[dict[str, Any]],
        turn_id: int | None = None,
    ) -> None:
        # 空列表时跳过，避免不必要的数据库操作
        if not invocations:
            return
        async with session_scope() as db:
            for invocation in invocations:
                # 跳过缺少必要字段的条目
                tool_call_id = str(invocation.get("tool_call_id") or "").strip()
                tool_name = str(invocation.get("tool_name") or "").strip()
                if not tool_call_id or not tool_name:
                    continue
                db.add(
                    ChatToolInvocation(
                        user_id=user_id,
                        session_id=session_id,
                        turn_id=turn_id,
                        module=self.module,
                        assistant_message_id=invocation.get("assistant_message_id"),
                        tool_message_id=invocation.get("tool_message_id"),
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                        arguments_json=invocation.get("arguments_json"),
                        result_text=invocation.get("result_text"),
                        result_json=invocation.get("result_json"),
                        status=str(invocation.get("status") or "success"),
                    )
                )
            await db.commit()

    # -------------------------------------------------------------------
    # create_turn: 创建一个新的对话轮次（turn）
    #
    # turn 是记忆管线的核心调度单元，每次用户提问到回答完成为一个 turn。
    # 它记录本轮的元数据：路由策略、执行模式、是否使用了附件/搜索/教学图。
    #
    # turn_index 自增逻辑：
    #   查询当前 session 中最大 turn_index，+1 作为新 turn 的 index。
    #   这保证同一 session 内 turn 有序，便于后续回溯和压缩。
    # -------------------------------------------------------------------
    async def create_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        route: str = "default",
        execution_mode: str = "default",
        has_attachments: bool = False,
        used_web_search: bool = False,
        used_teaching_diagram: bool = False,
        status: str = "running",
    ) -> Any:
        async with session_scope() as db:
            # 查找/创建 session，更新最后活跃时间
            chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
            if chat_session:
                # 权限校验：session 必须属于当前用户且匹配模块
                if chat_session.user_id != user_id or chat_session.module != self.module:
                    raise PermissionError("会话不属于当前用户或模块")
                chat_session.updated_at = now()
            else:
                chat_session = ChatSession(id=session_id, user_id=user_id, module=self.module)
            db.add(chat_session)
            await db.flush()

            # 查询当前 session 中最新的 turn，计算下一个 turn_index
            latest = (
                await db.exec(
                    select(ChatTurn)
                    .where(
                        ChatTurn.user_id == user_id,
                        ChatTurn.session_id == session_id,
                        ChatTurn.module == self.module,
                    )
                    .order_by(ChatTurn.turn_index.desc())
                    .limit(1)
                )
            ).first()
            # 最新 turn 的 index + 1，若无历史 turn 则从 1 开始
            next_index = int(getattr(latest, "turn_index", 0) or 0) + 1
            turn = ChatTurn(
                user_id=user_id,
                session_id=session_id,
                module=self.module,
                turn_index=next_index,
                route=route,
                execution_mode=execution_mode,
                has_attachments=has_attachments,
                used_web_search=used_web_search,
                used_teaching_diagram=used_teaching_diagram,
                status=status,
            )
            db.add(turn)
            await db.commit()
            await db.refresh(turn)
            return turn

    # -------------------------------------------------------------------
    # update_turn: 更新已有 turn 的状态和元数据
    #
    # 在 turn 执行过程中或结束后调用，用于：
    #   - 标记 turn 为 completed/failed 等终态
    #   - 记录最终的路由策略和执行模式
    #   - 标记是否使用了网络搜索或教学图
    #   - 记录错误信息（失败时）
    #
    # 只有 status == "completed" 时才写入 completed_at 时间戳，
    # 用于后续统计 turn 耗时。
    # -------------------------------------------------------------------
    async def update_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        turn_id: int,
        status: str,
        route: str = "default",
        execution_mode: str = "default",
        used_web_search: bool = False,
        used_teaching_diagram: bool = False,
        error_message: str | None = None,
    ) -> None:
        async with session_scope() as db:
            # 按 id + user_id + session_id + module 精确查找 turn
            turn = (
                await db.exec(
                    select(ChatTurn).where(
                        ChatTurn.id == turn_id,
                        ChatTurn.user_id == user_id,
                        ChatTurn.session_id == session_id,
                        ChatTurn.module == self.module,
                    )
                )
            ).first()
            if turn is None:
                return
            turn.status = status
            turn.route = route
            turn.execution_mode = execution_mode
            turn.used_web_search = used_web_search
            turn.used_teaching_diagram = used_teaching_diagram
            turn.error_message = error_message
            # 完成时记录完成时间，用于耗时统计
            if status == "completed":
                turn.completed_at = now()
            db.add(turn)
            await db.commit()

    # -------------------------------------------------------------------
    # append_turn_event: 向指定 turn 的 transcript 追加一条事件
    #
    # 这是 ChatPersistenceAdapter.append_transcript_event 的门面方法，
    # 添加了 user_id 和 session_id 参数（当前未用于权限校验，但保持
    # 接口一致性），便于上层调用方传入完整的会话上下文。
    # -------------------------------------------------------------------
    async def append_turn_event(
        self,
        *,
        user_id: int,
        session_id: str,
        turn_id: int,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        # 委托给 persistence 适配器执行实际的追加操作
        await self.persistence.append_transcript_event(
            turn_id=turn_id,
            event_type=event_type,
            payload=payload,
        )

    # -------------------------------------------------------------------
    # finalize_turn_transcript: 结束 turn 的 transcript 并写入终态
    #
    # 将 status 注入 constraint_report 字典（作为顶层 status 字段），
    # 然后委托给 persistence 适配器执行终态落盘。
    #
    # 与 finalize_turn 的区别：
    #   - finalize_turn 是 persistence 适配器的底层方法
    #   - 本方法是 ChatMemoryService 的门面，添加了 status 注入逻辑
    # -------------------------------------------------------------------
    async def finalize_turn_transcript(
        self,
        *,
        user_id: int,
        session_id: str,
        turn_id: int,
        status: str,
        final_answer: str,
        constraint_report: dict[str, Any] | None = None,
    ) -> None:
        # 将 turn status 注入 constraint_report 顶层字段
        report = dict(constraint_report or {})
        report.setdefault("status", status)
        await self.persistence.finalize_turn(
            turn_id=turn_id,
            final_answer=final_answer,
            constraint_report=report,
        )

    # -------------------------------------------------------------------
    # save_uploaded_file: 持久化用户上传的文件元数据
    #
    # 在文件上传到对象存储后调用，记录文件的：
    #   - storage_url：对象存储中的访问 URL
    #   - storage_key：对象存储中的文件标识（用于删除/引用）
    #   - original_name：用户上传时的原始文件名
    #   - file_kind：文件类型分类（document/image/audio 等）
    #   - mime_type / extension：MIME 类型和扩展名
    #   - size_bytes：文件大小（字节）
    #
    # 返回创建的记录对象，供后续 bind_message_attachments 使用。
    # -------------------------------------------------------------------
    async def save_uploaded_file(
        self,
        *,
        user_id: int,
        session_id: str,
        payload: dict[str, Any],
    ) -> Any:
        async with session_scope() as db:
            record = ChatUploadedFile(
                user_id=user_id,
                session_id=session_id,
                module=self.module,
                storage_url=str(payload.get("url") or ""),
                storage_key=payload.get("storage_key"),
                original_name=str(payload.get("original_name") or ""),
                file_kind=str(payload.get("file_type") or "document"),
                mime_type=payload.get("mime_type"),
                extension=payload.get("extension"),
                size_bytes=int(payload.get("size_bytes") or 0),
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return record

    # -------------------------------------------------------------------
    # bind_message_attachments: 将已上传的文件绑定到消息
    #
    # 工作流：
    #   1. 从 attachments 中提取所有 URL
    #   2. 通过 URL 批量查找对应的 ChatUploadedFile 记录
    #   3. 为每个匹配的文件创建 ChatMessageAttachment 关联记录
    #   4. 保留 attachment_order 以维持用户指定的文件顺序
    #
    # 为什么用 URL 匹配而非 file_id：
    #   前端上传文件后只知道 URL，不知道数据库中的 file_id，
    #   所以通过 storage_url 反查对应的文件记录。
    # -------------------------------------------------------------------
    async def bind_message_attachments(
        self,
        *,
        user_id: int,
        session_id: str,
        message_id: int,
        turn_id: int | None,
        attachments: list[dict[str, Any]],
    ) -> None:
        # 空列表时跳过
        if not attachments:
            return
        async with session_scope() as db:
            # 提取所有有效的 URL
            urls = [str(item.get("url") or "").strip() for item in attachments if str(item.get("url") or "").strip()]
            if not urls:
                return
            # 批量查找对应的上传文件记录
            uploaded_files = list(
                (
                    await db.exec(
                        select(ChatUploadedFile).where(
                            ChatUploadedFile.user_id == user_id,
                            ChatUploadedFile.session_id == session_id,
                            ChatUploadedFile.module == self.module,
                            ChatUploadedFile.storage_url.in_(urls),
                        )
                    )
                ).all()
            )
            # 构建 URL → 文件记录的映射，便于快速查找
            file_by_url = {item.storage_url: item for item in uploaded_files}
            for index, attachment in enumerate(attachments):
                url = str(attachment.get("url") or "").strip()
                file_record = file_by_url.get(url)
                # URL 未匹配到文件记录时跳过
                if file_record is None:
                    continue
                # 创建消息-文件关联记录，保留原始顺序
                db.add(
                    ChatMessageAttachment(
                        user_id=user_id,
                        session_id=session_id,
                        message_id=message_id,
                        file_id=file_record.id,
                        turn_id=turn_id,
                        module=self.module,
                        attachment_order=index,
                        attachment_role="input",
                    )
                )
            await db.commit()

    # -------------------------------------------------------------------
    # list_message_attachments: 批量查询多条消息的附件列表
    #
    # 通过 JOIN ChatUploadedFile 获取附件的完整元数据（URL、类型、大小等）。
    # 返回格式：{message_id: [附件字典列表]}，按 message_id 和 attachment_order 排序。
    #
    # 为什么一次查多条消息：
    #   避免 N+1 查询问题，前端展示消息列表时需要一次性拿到
    #   所有消息的附件信息。
    # -------------------------------------------------------------------
    async def list_message_attachments(
        self,
        *,
        user_id: int,
        session_id: str,
        message_ids: list[int],
    ) -> dict[int, list[dict[str, Any]]]:
        # 空列表时直接返回空字典
        if not message_ids:
            return {}
        async with session_scope() as db:
            # JOIN 查询：消息附件关联 + 上传文件元数据
            stmt = (
                select(ChatMessageAttachment, ChatUploadedFile)
                .join(ChatUploadedFile, ChatUploadedFile.id == ChatMessageAttachment.file_id)
                .where(
                    ChatMessageAttachment.user_id == user_id,
                    ChatMessageAttachment.session_id == session_id,
                    ChatMessageAttachment.module == self.module,
                    ChatMessageAttachment.message_id.in_(message_ids),
                )
                # 先按 message_id 分组，再按附件顺序排列
                .order_by(ChatMessageAttachment.message_id.asc(), ChatMessageAttachment.attachment_order.asc())
            )
            rows = (await db.exec(stmt)).all()
            # 构建 message_id → 附件列表 的映射
            result: dict[int, list[dict[str, Any]]] = {}
            for relation, uploaded in rows:
                result.setdefault(relation.message_id, []).append(
                    {
                        "file_id": uploaded.id,
                        "url": uploaded.storage_url,
                        "type": uploaded.file_kind,
                        "name": uploaded.original_name,
                        "mime_type": uploaded.mime_type,
                        "extension": uploaded.extension,
                        "storage_key": uploaded.storage_key,
                        "size_bytes": uploaded.size_bytes,
                    }
                )
            return result

    # -------------------------------------------------------------------
    # list_messages: 获取指定 session 的消息列表
    #
    # 支持两种查询模式：
    #   - only_unexpired=True（默认）：仅返回未过期的消息（MESSAGE_EXPIRE_DAYS 天内）
    #   - only_unexpired=False：返回所有消息
    #
    # 智能分页逻辑：
    #   当总消息数超过 limit 时，只返回最新的 limit 条（offset=total-limit），
    #   而非从第 0 条开始取。这保证用户始终看到最新的对话内容。
    #
    # 消息按 created_at 升序排列，保证对话时间线的正确性。
    # -------------------------------------------------------------------
    async def list_messages(
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int | None = None,
        only_unexpired: bool = True,
    ) -> list[Any]:
        async with session_scope() as db:
            # 构建过滤条件
            filters = [
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == self.module,
            ]
            # 过期消息过滤（仅返回 MESSAGE_EXPIRE_DAYS 天内的消息）
            if only_unexpired:
                filters.append(ChatMessage.created_at >= now() - timedelta(days=MESSAGE_EXPIRE_DAYS))
            # 统计符合条件的总消息数
            total = (await db.exec(select(func.count()).where(*filters))).one()
            # 按时间升序查询所有消息
            stmt = select(ChatMessage).where(*filters).order_by(ChatMessage.created_at.asc())
            # 当消息数超限时，用 offset 跳过旧消息，只保留最新的 limit 条
            if limit is not None and limit > 0 and total > limit:
                stmt = stmt.offset(total - limit)
            return list((await db.exec(stmt)).all())

    # -------------------------------------------------------------------
    # count_messages: 统计指定 session 中的消息总数
    #
    # 使用 COUNT 聚合函数，避免查询全部消息行再计数的性能开销。
    # 用于压缩器判断是否需要触发压缩。
    # -------------------------------------------------------------------
    async def count_messages(self, *, user_id: int, session_id: str) -> int:
        async with session_scope() as db:
            return (
                await db.exec(
                    select(func.count()).where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == self.module,
                    )
                )
            ).one()

    # -------------------------------------------------------------------
    # delete_short_term_messages: 删除指定 session 的所有短期消息
    #
    # 用于会话重置或压缩后清理旧消息。返回删除的消息数量。
    # 注意：此操作不可逆，仅删除 ChatMessage 行，
    # 不影响 transcript、摘要块等关联数据。
    # -------------------------------------------------------------------
    async def delete_short_term_messages(self, *, user_id: int, session_id: str) -> int:
        async with session_scope() as db:
            # 查询该 session 下的所有消息
            messages = (
                await db.exec(
                    select(ChatMessage).where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == self.module,
                    )
                )
            ).all()
            # 逐条删除（SQLModel 需要逐条 delete）
            for message in messages:
                await db.delete(message)
            await db.commit()
            return len(messages)

    # -------------------------------------------------------------------
    # reset_session_counters: 重置 session 的 token 计数器
    #
    # 将 summary_token_count 归零，通常在会话重置或重新开始时调用。
    # -------------------------------------------------------------------
    async def reset_session_counters(self, *, user_id: int, session_id: str) -> None:
        async with session_scope() as db:
            chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
            if chat_session:
                chat_session.summary_token_count = 0
                db.add(chat_session)
                await db.commit()

    # -------------------------------------------------------------------
    # list_summary_blocks: 获取最近的会话摘要块列表
    #
    # 摘要块由压缩器（ChatSessionCompressor）在压缩旧消息时生成，
    # 每个块包含一段 markdown 格式的摘要文本。
    # 按 created_at 降序返回最新的 limit 个摘要块。
    # -------------------------------------------------------------------
    async def list_summary_blocks(self, *, user_id: int, session_id: str, limit: int = SUMMARY_CONTEXT_BLOCKS) -> list[Any]:
        async with session_scope() as db:
            stmt = (
                select(ChatSessionSummaryBlock)
                .where(
                    ChatSessionSummaryBlock.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                    ChatSessionSummaryBlock.module == self.module,
                )
                .order_by(ChatSessionSummaryBlock.created_at.desc())
                .limit(limit)
            )
            return list((await db.exec(stmt)).all())

    # -------------------------------------------------------------------
    # list_attachment_analyses: 获取消息附件的分析结果列表
    #
    # 分析结果由附件处理流程生成（如 OCR 提取、内容摘要等），
    # 按 created_at 降序返回最近的 limit 条。
    # -------------------------------------------------------------------
    async def list_attachment_analyses(
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int = 20,
    ) -> list[Any]:
        async with session_scope() as db:
            stmt = (
                select(ChatAttachmentAnalysis)
                .where(
                    ChatAttachmentAnalysis.user_id == user_id,
                    ChatAttachmentAnalysis.session_id == session_id,
                    ChatAttachmentAnalysis.module == self.module,
                )
                .order_by(ChatAttachmentAnalysis.created_at.desc())
                .limit(limit)
            )
            return list((await db.exec(stmt)).all())

    # -------------------------------------------------------------------
    # list_tool_invocations: 获取会话中的工具调用记录列表
    #
    # 按 created_at 降序返回最近的 limit 条工具调用记录，
    # 用于前端展示"已使用的工具"或后端审计工具调用历史。
    # -------------------------------------------------------------------
    async def list_tool_invocations(
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int = 20,
    ) -> list[Any]:
        async with session_scope() as db:
            stmt = (
                select(ChatToolInvocation)
                .where(
                    ChatToolInvocation.user_id == user_id,
                    ChatToolInvocation.session_id == session_id,
                    ChatToolInvocation.module == self.module,
                )
                .order_by(ChatToolInvocation.created_at.desc())
                .limit(limit)
            )
            return list((await db.exec(stmt)).all())

    # -------------------------------------------------------------------
    # get_session_summary_context: 获取会话的摘要上下文（供 LLM 拼接 prompt）
    #
    # 从数据库取最近 N 个（默认 3 个）ChatSessionSummaryBlock，
    # 按时间正序用分隔符拼接为 markdown 文本。
    #
    # reversed 的原因：查询按 created_at DESC 排序，拼接时需要
    # 从旧到新排列，所以取结果后反转。
    #
    # 返回的 markdown 会注入到 system prompt 中，让 LLM 了解
    # "之前聊过什么"，避免重复询问或遗忘上下文。
    # -------------------------------------------------------------------
    async def get_session_summary_context(self, *, user_id: int, session_id: str) -> str:
        # 获取最近的摘要块（降序）
        blocks = await self.list_summary_blocks(user_id=user_id, session_id=session_id, limit=SUMMARY_CONTEXT_BLOCKS)
        if not blocks:
            return "暂无会话概要。"
        # 反转为时间正序，用分隔符拼接各块的 markdown 内容
        return "\n\n---\n\n".join(
            block.summary_markdown
            for block in reversed(blocks)
            if block.summary_markdown
        ) or "暂无会话概要。"

    # -------------------------------------------------------------------
    # get_long_term_memory: 获取用户的长期记忆记录对象
    #
    # 每个 user + module 组合对应一条 ChatLongTermMemory 记录，
    # 其中 memory_markdown 列存储完整的长期记忆 markdown。
    # 返回 ORM 对象（可能为 None），调用方可直接读取各字段。
    # -------------------------------------------------------------------
    async def get_long_term_memory(self, *, user_id: int) -> Any:
        async with session_scope() as db:
            return (
                await db.exec(
                    select(ChatLongTermMemory).where(
                        ChatLongTermMemory.user_id == user_id,
                        ChatLongTermMemory.module == self.module,
                    )
                )
            ).first()

    # -------------------------------------------------------------------
    # get_profile_markdown: 获取用户学习画像的 markdown 内容
    #
    # 委托给 ProfileService 执行，支持按维度过滤。
    # 画像由 profiling 服务在对话过程中持续更新，
    # 包含学习风格、知识水平、偏好等维度的信息。
    # -------------------------------------------------------------------
    async def get_profile_markdown(self, user_id: int, dimension: str | None = None) -> str:
        from app.profile.service import get_profile_service
        return await get_profile_service().get_profile_markdown(user_id, dimension=dimension)

    # -------------------------------------------------------------------
    # after_turn: 每轮对话结束后的 token 计数与后处理管线入口
    #
    # 工作流：
    #   1. 计算本轮 token 增量（优先使用 LLM 返回的 usage_metadata，
    #      否则用本地估算函数 estimate_token_count）
    #   2. 将 token 增量累加到 session.summary_token_count
    #      （该计数器用于判断是否触发压缩）
    #   3. 触发 post_turn 后处理管线（压缩 + 长期记忆更新）
    #
    # 为什么 token 计数在这里而非 post_turn 中：
    #   token 计数是独立的副作用，即使 post_turn 失败，
    #   计数器仍应准确反映会话的 token 消耗。
    # -------------------------------------------------------------------
    async def after_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        usage_metadata: dict[str, Any] | None = None,
        turn_count: int = 0,
    ) -> None:
        # 优先使用 LLM 返回的精确 token 数，回退到本地估算
        if usage_metadata and "total_tokens" in usage_metadata:
            delta = usage_metadata["total_tokens"]
        else:
            delta = estimate_token_count(user_message) + estimate_token_count(assistant_reply)

        # 更新 session 的累计 token 计数（失败不阻塞后续流程）
        try:
            async with session_scope() as db:
                chat_session = (
                    await db.exec(
                        select(ChatSession).where(
                            ChatSession.id == session_id,
                            ChatSession.user_id == user_id,
                            ChatSession.module == self.module,
                        )
                    )
                ).first()
                if not chat_session:
                    # session 不存在时兜底创建，避免计数丢失
                    chat_session = ChatSession(
                        id=session_id,
                        user_id=user_id,
                        module=self.module,
                        title=DEFAULT_SESSION_TITLE,
                    )
                # 累加 token 增量，确保不为负数
                chat_session.summary_token_count = max(0, (chat_session.summary_token_count or 0) + delta)
                chat_session.updated_at = now()
                db.add(chat_session)
                await db.commit()
        except Exception as exc:
            logger.error("[ChatMemoryService] token 计数更新失败 user=%s session=%s err=%s", user_id, session_id, exc)

        # 触发后处理管线：压缩 + 长期记忆更新
        await self.post_turn(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
            turn_count=turn_count,
        )

    # -------------------------------------------------------------------
    # post_turn: 后处理管线 — 压缩 + 长期记忆更新
    #
    # 两阶段管线按顺序执行，各自独立 try/except 互不影响：
    #
    # 阶段 1 — 短期记忆压缩（compressor.maybe_compress）：
    #   当 session 中消息数 ≥ 14 条 或 token ≥ 3500 时，
    #   将旧消息摘要化，保留最近 8 条原始消息。
    #   压缩后生成一个 ChatSessionSummaryBlock 行。
    #
    # 阶段 2 — 长期记忆更新（long_term_memory.maybe_update）：
    #   每 8 轮检查一次（由 turn_count 控制），检测本轮对话中
    #   是否包含稳定信号（如重复出现的知识偏好、学习习惯），
    #   置信度 ≥ 0.75 时增量更新 ChatLongTermMemory.memory_markdown。
    #
    # 返回值：字典标记哪些阶段实际执行了更新，供调用方判断。
    # -------------------------------------------------------------------
    async def post_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        turn_count: int = 0,
    ) -> dict[str, bool]:
        # 跟踪各阶段是否实际执行了更新
        results = {
            "compressed": False,
            "ltm_updated": False,
        }

        # 阶段 1：尝试压缩短期消息（失败不影响后续阶段）
        try:
            async with session_scope() as db:
                summary = await self.compressor.maybe_compress(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    reason="post_turn",
                )
                # summary 非 None 表示实际执行了压缩
                results["compressed"] = summary is not None
        except Exception as exc:
            logger.error("[ChatMemoryService] compression failed: %s", exc)

        # 阶段 2：尝试更新长期记忆（独立于压缩，失败不影响）
        try:
            async with session_scope() as db:
                updated = await self.long_term_memory.maybe_update(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_message,
                    assistant_reply=assistant_reply,
                    turn_count=turn_count,
                )
                results["ltm_updated"] = updated
        except Exception as exc:
            logger.error("[ChatMemoryService] long-term update failed: %s", exc)

        
        return results


# -------------------------------------------------------------------
# 模块级缓存：按 module 名缓存 ChatMemoryService 单例
# 确保同一 module 的所有调用共享同一实例，避免重复初始化管线组件。
# -------------------------------------------------------------------
_chat_memory_service_cache: dict[str, ChatMemoryService] = {}


# -------------------------------------------------------------------
# get_chat_memory_service: 获取指定 module 的 ChatMemoryService 单例
#
# 按 module 隔离缓存，首次访问时创建实例并缓存，后续直接返回。
# module 参数区分不同业务域（如 mentor、quiz），各域的记忆管线
# 使用独立的压缩器和长期记忆服务实例。
# -------------------------------------------------------------------
def get_chat_memory_service(*, module: str = "mentor") -> ChatMemoryService:
    if module not in _chat_memory_service_cache:
        _chat_memory_service_cache[module] = ChatMemoryService(module=module)
    return _chat_memory_service_cache[module]
