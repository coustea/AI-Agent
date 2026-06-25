"""聊天服务层 — 对话流编排、记忆管理、文件上传。

核心函数：
  build_messages()  — 从数据库构建 LangChain 消息列表（含工具调用链）
  chat()            — 总编排：build_messages → TutorAgent.chat() → 转发 SSE 事件 → 持久化

ChatUseCases 保留会话管理、文件上传等辅助功能，对话核心逻辑委托给 TutorAgent。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, AsyncIterator

from app.chat.agent import TutorAgent
from app.chat.context_builder import ChatContextBuilder, build_user_content
from app.chat.emitter import ChatEvents, ChatEventName, ChatRuntimeEventMapper, SSE_EVENT_MAP, runtime_status
from app.chat.agent.background import run_background_memory_jobs
from app.chat.memory.service import get_chat_memory_service
from app.chat.streaming import safety_filter
from app.chat.schemas import TutorAgentInput
from app.chat.storage.file_store import LocalFileStore
from app.chat.schemas import ChatMessageItem
from app.config import MAX_UPLOAD_FILES_PER_REQUEST
from app.infra.logging import get_logger

logger = get_logger(__name__)

# 共享实例
_context_builder = ChatContextBuilder()
_event_mapper = ChatRuntimeEventMapper()

# -----------------------------------------------------------------------
# 核心函数：build_messages / chat helpers / chat
# -----------------------------------------------------------------------


async def build_messages(
    user_id: int,
    session_id: str,
    *,
    exclude_message_id: int | None = None,
) -> list[AnyMessage]:
    """从数据库构建 LangChain 消息列表（委托给 ChatContextBuilder）。"""
    return await _context_builder.build_history(
        user_id, session_id, exclude_message_id=exclude_message_id,
    )


async def chat(
    *,
    user_id: int,
    session_id: str,
    user_input: str,
    attachments: list[str] | None = None,
    enable_web_search: bool = False,
    need_teaching_diagram: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """执行一次辅导对话，流式返回 SSE 事件。

    简化流程（不再创建 turn）：
    1. 保存用户消息
    2. 构建上下文
    3. 调用 TutorAgent
    4. 保存助手回复
    5. 后台记忆任务
    """
    uc = get_chat_usecases()
    effective_session = session_id or uc.default_session_id(user_id)
    merged_attachments = list(dict.fromkeys(attachments or []))
    current_message = (user_input or "").strip()

    if not current_message and not merged_attachments:
        yield {"event": "error", "data": "请输入您的问题。"}
        yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
        return

    if not current_message and merged_attachments:
        current_message = "请分析我上传的附件，并解答其中的问题。"

    logger.info(
        "[chat] 开始对话: user_id=%s session_id=%s msg_len=%d attachments=%d",
        user_id, effective_session, len(current_message), len(merged_attachments),
    )

    yield {
        "event": "status",
        "data": {
            "stage": "preparing_context",
            "message": "正在分析附件并准备本轮对话..." if merged_attachments else "正在准备本轮对话...",
        },
    }

    # ── 1. 持久化用户消息 ──
    memory_svc = get_chat_memory_service()
    content_parts = build_user_content(current_message, merged_attachments)

    user_message = await memory_svc.save_message(
        user_id=user_id,
        session_id=effective_session,
        role="user",
        content=content_parts,
    )
    user_message_id: int | None = getattr(user_message, "id", None)

    # 如果是第一条消息，后台生成标题
    if await memory_svc.count_messages(user_id=user_id, session_id=effective_session) <= 1:
        uc._spawn_background(
            memory_svc.generate_session_title(
                user_id=user_id,
                session_id=effective_session,
                first_message=current_message,
            ),
            label="generate_title",
        )

    # ── 2. 构建上下文 ──
    history_messages = await build_messages(
        user_id, effective_session,
        exclude_message_id=user_message_id,
    )
    session_summary = await memory_svc.get_session_summary_context(user_id=user_id, session_id=effective_session)

    # ── 3. 调用 TutorAgent ──
    agent_input = TutorAgentInput(
        user_id=user_id,
        session_id=effective_session,
        question=current_message,
        attachments=merged_attachments,
        history_messages=history_messages,
        session_summary=session_summary,
        enable_web_search=enable_web_search,
        need_teaching_diagram=need_teaching_diagram,
    )

    agent = TutorAgent()
    full_answer = ""
    tool_invocations: list[dict[str, Any]] = []
    diagram_result: dict[str, Any] | None = None
    sources: list[dict[str, Any]] = []
    has_error = False

    try:
        async for event in agent.chat(agent_input):
            sse_event = SSE_EVENT_MAP.get(event.type, "status")
            sse_data = event.payload

            if event.type == "answer_token":
                yield {"event": "token", "data": sse_data.get("token", "")}
                continue

            if event.type == "final":
                full_answer = sse_data.get("final_answer", "")
                diagram_result = sse_data.get("diagram_result")
                tool_invocations = sse_data.get("tool_invocations", [])
                sources = sse_data.get("sources", [])

                if diagram_result is not None:
                    yield {"event": "diagram", "data": diagram_result}

                yield {
                    "event": "status",
                    "data": {
                        "stage": "answer_done",
                        "message": "回答已生成，正在保存...",
                    },
                }
                continue

            if event.type == "error":
                has_error = True
                yield {"event": "error", "data": sse_data.get("error", "未知错误")}
                yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
                return

            yield {"event": sse_event, "data": sse_data}

    except Exception as exc:
        logger.exception("[chat] TutorAgent 执行失败")
        has_error = True
        yield {"event": "error", "data": f"服务器出错: {exc}"}
        yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
        return

    # ── 4. 持久化助手回复（含图解、来源等元数据） ──
    if not has_error and full_answer:
        # 安全过滤
        safety_result = await safety_filter.check(full_answer)
        if safety_result.has_violation:
            full_answer = safety_result.sanitized_text

        usage_meta: dict[str, Any] = {}
        if diagram_result:
            usage_meta["diagram"] = diagram_result
        if sources:
            usage_meta["sources"] = sources
        if tool_invocations:
            usage_meta["tool_invocations"] = [
                {"tool_name": inv.get("tool_name", ""), "payload": inv.get("payload", {})}
                for inv in tool_invocations
            ]

        await memory_svc.save_message(
            user_id=user_id,
            session_id=effective_session,
            role="assistant",
            content=full_answer,
            usage_metadata=usage_meta or None,
        )

    # ── 5. 最终内容校准：确保前端显示与数据库一致 ──
    if not has_error and full_answer:
        yield {
            "event": "content_replace",
            "data": {"content": full_answer},
        }

    # ── 6. 返回最终结果 ──
    if not has_error:
        yield {
            "event": "done",
            "data": {
                "session_id": effective_session,
                "full_response": full_answer,
                "tool_calls": [
                    {"id": inv.get("tool_name", ""), "name": inv.get("tool_name", ""), "args": inv.get("payload", {})}
                    for inv in tool_invocations
                ],
            },
        }

    # ── 5. 后台记忆任务 ──
    if full_answer:
        uc._spawn_background(
            run_background_memory_jobs(
                uc._memory_service,
                user_id=user_id,
                session_id=effective_session,
                user_message=current_message,
                assistant_reply=full_answer,
            ),
            label="post_turn",
        )


async def _publish_chat_runtime_event(
    events: ChatEvents,
    event: dict[str, Any],
) -> bool:
    """把辅导内部事件映射成 ChatEvent 并发送（委托给 ChatRuntimeEventMapper）。"""
    result = await _event_mapper.publish(events, event)
    return result.failed


async def run_chat_agent(
    *,
    run_id: str,
    user_id: int,
    session_id: str,
    user_input: str,
    attachments: list[str],
    enable_web_search: bool,
    need_teaching_diagram: bool,
) -> None:
    """后台执行一次辅导，并通过 ChatEvents 推送运行状态。

    频道已在 router 中通过 ChatEvents.open() 注册。
    """
    events = ChatEvents(user_id=user_id, session_id=session_id, run_id=run_id)
    await events.open()
    await events.send(event="run.started", message="智能辅导已开始", data={})
    failed = False
    try:
        async for event in chat(
            user_id=user_id,
            session_id=session_id,
            user_input=user_input,
            attachments=attachments or None,
            enable_web_search=enable_web_search,
            need_teaching_diagram=need_teaching_diagram,
        ):
            failed = await _publish_chat_runtime_event(events, event) or failed
        if failed:
            await events.send(event="run.failed", message="回答失败", data={"error": "智能辅导暂时无法完成本次回答"})
        else:
            await events.send(event="run.completed", message="回答完成", data={})
    except Exception as e:
        logger.exception("chat_agent_run_failed: run_id=%s", run_id)
        await events.send(event="run.failed", message="回答失败", data={"error": str(e)})





class ChatUseCases:
    """聊天服务核心类 — 负责附件上传、文件解析和对话流编排。

    职责：
    1. 附件上传、存储和分析
    2. 流式对话（SSE 事件流）
    3. 安全过滤（敏感词检测）
    4. 消息持久化（通过 memory_service）
    5. 后台任务（记忆管线、画像更新）

    会话 CRUD 等简单操作直接通过 get_chat_memory_service() 调用，
    不需要再经过此层转发。
    """

    def __init__(self) -> None:
        # 本地文件存储：用户上传文件的磁盘读写
        self.file_store: LocalFileStore = LocalFileStore()
        # 后台任务集合：防止未等待的协程被 GC 回收
        self._background_tasks: set[asyncio.Task] = set()
        self._memory_service = get_chat_memory_service()

    def default_session_id(self, user_id: int) -> str:
        """生成默认会话 ID — 格式: user-{user_id}-default-mentor。"""
        return f"user-{user_id}-default-mentor"





    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[ChatMessageItem]:
        """获取会话历史消息，组装为 ChatMessageItem 列表。"""
        memory_svc = get_chat_memory_service()
        if not session_id:
            sessions = await memory_svc.list_sessions(user_id=user_id, limit=1)
            if not sessions:
                return []
            session_id = sessions[0].id

        raw_messages = await memory_svc.list_messages(user_id=user_id, session_id=session_id, limit=limit)

        result: list[ChatMessageItem] = []
        for message in raw_messages:
            msg_content: list[dict[str, Any]] = list(message.content) if isinstance(message.content, list) else [{"type": "text", "text": str(message.content)}]

            result.append(
                ChatMessageItem(
                    id=message.id,
                    role=message.role,
                    content=msg_content,
                    tool_calls=message.tool_calls if isinstance(message.tool_calls, list) else None,
                    tool_call_id=getattr(message, "tool_call_id", None),
                    created_at=message.created_at,
                )
            )
        return result




    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        user_id: int,
        session_id: str,
    ) -> dict[str, Any]:
        """保存用户上传的文件：磁盘存储 + 数据库记录。

        流程：
        1. 校验文件名非空
        2. 检查单次上传文件数是否超限
        3. 调用 LocalFileStore 写入磁盘
        4. 在数据库中保存文件记录
        5. 维护 URL→数据库 ID 映射，供附件分析器引用
        """
        if not filename:
            raise ValueError("文件名不能为空")
        # 检查文件数上限
        existing = self.file_store.list_files(user_id=user_id, session_id=session_id)
        if len(existing) >= MAX_UPLOAD_FILES_PER_REQUEST:
            raise ValueError(f"单次上传最多 {MAX_UPLOAD_FILES_PER_REQUEST} 个文件")
        # 写入磁盘
        payload = await self.file_store.save_upload(
            filename=filename,
            content=content,
            user_id=user_id,
            session_id=session_id,
        )
        # 保存文件记录到数据库
        await self._memory_service.save_uploaded_file(user_id=user_id, session_id=session_id, payload=payload)
        return payload

    def resolve_uploaded_file(
        self,
        *,
        current_user_id: int,
        owner_id: int,
        session_id: str,
        filename: str,
    ) -> Path:
        """解析上传文件路径，带权限校验。

        只有文件所有者才能访问，防止越权读取。
        实际路径解析委托给 LocalFileStore.resolve_user_file。
        """
        if current_user_id != owner_id:
            raise PermissionError("无权访问此文件")
        return self.file_store.resolve_user_file(
            current_user_id=current_user_id,
            owner_id=owner_id,
            session_id=session_id,
            filename=filename,
        )

    def _spawn_background(self, coro, *, label: str = "") -> None:
        """安全地启动后台协程任务。

        关键设计：
        1. 任务加入 _background_tasks 集合，防止被 GC 回收
        2. 完成回调自动从集合移除，避免内存泄漏
        3. 异常被 catch 并记录日志，不会影响主流程
        4. 若当前不在事件循环中（极端情况），记录警告而非崩溃
        """
        async def _run() -> None:
            try:
                await coro
            except Exception as exc:
                logger.error("[ChatUseCases] 后台任务失败 label=%s err=%s", label, exc)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            # 确保任务被引用，不会被垃圾回收
            task = asyncio.ensure_future(_run())
            self._background_tasks.add(task)
            # 完成后自动从集合移除
            task.add_done_callback(self._background_tasks.discard)
        else:
            logger.warning("[ChatUseCases] 无法在非事件循环中启动后台任务 label=%s", label)


# ── 单例管理 ──
# 两个独立单例：主对话和数字人对话，避免共享状态
_chat_usecases: ChatUseCases | None = None
_avatar_chat_usecases: ChatUseCases | None = None


def get_chat_usecases() -> ChatUseCases:
    """获取主对话的 ChatUseCases 单例。

    懒加载模式：首次调用时创建实例，后续复用。
    """
    global _chat_usecases
    if _chat_usecases is None:
        _chat_usecases = ChatUseCases()
    return _chat_usecases


def get_avatar_chat_usecases() -> ChatUseCases:
    """获取数字人对话的 ChatUseCases 单例。

    与主对话单例独立，避免上传文件映射等状态互相干扰。
    """
    global _avatar_chat_usecases
    if _avatar_chat_usecases is None:
        _avatar_chat_usecases = ChatUseCases()
    return _avatar_chat_usecases
