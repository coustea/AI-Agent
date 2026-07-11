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
from uuid import uuid4

from app.chat.agent import TutorAgent
from app.chat.context_builder import ChatContextBuilder, build_user_content
from app.chat.diagram_image_renderer import ensure_teaching_diagram_png_payload
from app.chat.emitter import ChatEvents, ChatRuntimeEventMapper, SSE_EVENT_MAP, build_workflow_activity_payload
from app.chat.agent.background import run_background_memory_jobs
from app.chat.events import record_dialogue_event
from app.chat.memory.service import get_chat_memory_service
from app.chat.schemas import TutorAgentInput
from app.chat.storage.file_store import LocalFileStore
from app.chat.schemas import ChatMessageItem
from app.config import MAX_UPLOAD_FILES_PER_REQUEST
from app.infra.database import session_scope
from app.infra.logging import get_logger

logger = get_logger(__name__)

# 共享实例：上下文构建器与事件映射器（模块级复用）
_context_builder = ChatContextBuilder()
_event_mapper = ChatRuntimeEventMapper()

# -----------------------------------------------------------------------
# 核心函数：build_messages / chat helpers / chat
# -----------------------------------------------------------------------


# 从数据库构建 LangChain 消息列表（委托给 ChatContextBuilder，排除本轮消息）
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


# 对话总编排：构建上下文 → 调用 TutorAgent → 转发 SSE 事件 → 持久化助手回复
async def chat(
    *,
    user_message_id: int,
    user_id: int,
    username: str,
    session_id: str,
    user_input: str,
    attachments: list[str] | None = None,
    enable_web_search: bool = False,
    need_teaching_diagram: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """执行一次辅导对话，所有派生记录关联当前 UserMessage。"""
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

    # ── 1. 持久化用户消息 ──
    # 发送“正在理解问题”活动并持久化，随后产出初始 status 事件
    memory_svc = get_chat_memory_service()
    preparing_payload = build_workflow_activity_payload(
        stage="preparing_context",
        activity_id="workflow:current",
        title="正在理解问题",
        summary="包含附件" if merged_attachments else "",
        message="正在读取附件和问题" if merged_attachments else "正在读取你的问题",
        status="running",
    )
    await memory_svc.upsert_activity(
        user_id=user_id,
        session_id=effective_session,
        user_message_id=user_message_id,
        payload=preparing_payload,
    )
    yield {"event": "status", "data": preparing_payload}

    # 若是首条消息，后台异步生成会话标题
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
    # 构建历史消息与会话摘要上下文
    history_messages = await build_messages(
        user_id, effective_session,
        exclude_message_id=user_message_id,
    )
    session_summary = await memory_svc.get_session_summary_context(user_id=user_id, session_id=effective_session)

    # ── 3. 调用 TutorAgent ──
    # 组装 Agent 输入并创建 TutorAgent 实例
    agent_input = TutorAgentInput(
        user_id=user_id,
        username=username,
        session_id=effective_session,
        user_message_id=user_message_id,
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

    # 迭代 Agent 流式事件并转换为前端事件
    try:
        async for event in agent.chat(agent_input):
            sse_event = SSE_EVENT_MAP.get(event.type, "status")
            sse_data = event.payload

            # 增量回答 token 直接透传
            if event.type == "answer_token":
                yield {"event": "token", "data": sse_data.get("token", "")}
                continue

            # 最终事件：收集完整回答/图解/工具调用/来源，并发送图解与保存中状态
            if event.type == "final":
                full_answer = sse_data.get("final_answer", "")
                diagram_result = sse_data.get("diagram_result")
                tool_invocations = sse_data.get("tool_invocations", [])
                sources = sse_data.get("sources", [])

                # 图解数据通过单独事件发送，前端在回答后立即渲染
                if diagram_result is not None:
                    diagram_result = await ensure_teaching_diagram_png_payload(
                        diagram_result,
                        username=username,
                        session_id=effective_session,
                    )
                    yield {"event": "diagram", "data": diagram_result}

                yield {
                    "event": "status",
                    "data": {
                        "stage": "answer_done",
                        "message": "回答已生成，正在保存...",
                    },
                }
                continue

            # 错误事件：标记失败并结束流
            if event.type == "error":
                has_error = True
                yield {"event": "error", "data": sse_data.get("error", "未知错误")}
                yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
                return

            # 其余事件按映射表转发
            yield {"event": sse_event, "data": sse_data}

    # 捕获 Agent 执行异常，向前端报告错误
    except Exception as exc:
        logger.exception("[chat] TutorAgent 执行失败")
        has_error = True
        yield {"event": "error", "data": f"服务器出错: {exc}"}
        yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
        return

    # ── 4. 持久化助手回复（含图解、来源等元数据） ──
    # 若正常产出，则保存助手消息并记录工具/来源/图解元数据
    saved_message_id: int | None = None
    if not has_error and full_answer:
        usage_meta: dict[str, Any] = {}
        if sources:
            usage_meta["sources"] = sources
        if tool_invocations:
            usage_meta["tool_invocations"] = [
                {"tool_name": inv.get("tool_name", ""), "payload": inv.get("payload", {})}
                for inv in tool_invocations
            ]
        if diagram_result:
            usage_meta["diagram"] = diagram_result

        saved = await memory_svc.save_message(
            user_id=user_id,
            session_id=effective_session,
            user_message_id=user_message_id,
            role="assistant",
            content=[{"type": "text", "text": full_answer}],
            usage_metadata=usage_meta or None,
        )
        saved_message_id = saved.id
    # 未产出回答则视为错误并结束
    elif not has_error:
        has_error = True
        yield {"event": "error", "data": "模型未生成可用回答"}
        yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
        return

    # ── 5. 最终内容校准：确保前端显示与数据库一致 ──
    # 用完整回答覆盖前端已流式显示的内容
    if not has_error and full_answer:
        yield {
            "event": "content_replace",
            "data": {"content": full_answer},
        }

    # ── 6. 返回最终结果 ──
    # 发送 done 事件，附带完整回答与工具调用信息
    if not has_error:
        yield {
            "event": "done",
            "data": {
                "session_id": effective_session,
                "saved_message_id": saved_message_id,
                "full_response": full_answer,
                "tool_calls": [
                    {"id": inv.get("tool_name", ""), "name": inv.get("tool_name", ""), "args": inv.get("payload", {})}
                    for inv in tool_invocations
                ],
            },
        }

    # ── 5. 后台记忆任务 ──
    # 对话成功后触发长期记忆与压缩等后台任务
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


# 将内部运行事件映射为 ChatEvent 并发送（委托给 ChatRuntimeEventMapper）
async def _publish_chat_runtime_event(
    events: ChatEvents,
    event: dict[str, Any],
) -> bool:
    """把辅导内部事件映射成 ChatEvent 并发送（委托给 ChatRuntimeEventMapper）。"""
    return await _event_mapper.publish(events, event)


# 后台入口：执行对话并通过 ChatEvents 推送运行状态，最后记录对话事件
async def run_chat_agent(
    *,
    user_message_id: int,
    user_id: int,
    username: str,
    session_id: str,
    user_input: str,
    attachments: list[str],
    enable_web_search: bool,
    need_teaching_diagram: bool,
) -> None:
    """后台执行一次辅导，并通过 ChatEvents 推送运行状态。

    频道已在 router 中通过 ChatEvents.open() 注册。
    """
    # 创建频道并发送初始“正在思考”状态
    events = ChatEvents(
        user_id=user_id,
        session_id=session_id,
        user_message_id=user_message_id,
    )
    memory_svc = get_chat_memory_service()
    await events.open()
    started = build_workflow_activity_payload(
        stage="run_started",
        activity_id="workflow:current",
        title="正在思考",
        message="正在准备回答",
    )
    # 持久化开始活动并推送 message.started 事件
    await memory_svc.upsert_activity(
        user_id=user_id,
        session_id=session_id,
        user_message_id=user_message_id,
        payload=started,
    )
    await events.send(event="message.started", message=started["message"], data=started)
    failed = False
    try:
        # 逐个转发对话事件；只要有一次失败即标记 failed
        async for event in chat(
            user_message_id=user_message_id,
            user_id=user_id,
            username=username,
            session_id=session_id,
            user_input=user_input,
            attachments=attachments or None,
            enable_web_search=enable_web_search,
            need_teaching_diagram=need_teaching_diagram,
        ):
            failed = await _publish_chat_runtime_event(events, event) or failed
        if failed:
            # 失败：持久化失败活动并发送 message.failed
            await memory_svc.upsert_activity(
                user_id=user_id,
                session_id=session_id,
                user_message_id=user_message_id,
                payload=build_workflow_activity_payload(
                    stage="failed",
                    activity_id="workflow:current",
                    title="回答未完成",
                    message="智能辅导暂时无法完成本次回答",
                    status="failed",
                ),
            )
            await events.send(event="message.failed", message="回答失败", data={"error": "智能辅导暂时无法完成本次回答"})
        else:
            # 成功：持久化完成活动并发送 message.completed
            await memory_svc.upsert_activity(
                user_id=user_id,
                session_id=session_id,
                user_message_id=user_message_id,
                payload=build_workflow_activity_payload(
                    stage="answer_done",
                    activity_id="workflow:current",
                    title="回答已完成",
                    message="回答已生成并保存",
                    status="done",
                ),
            )
            # 图解数据通过 chat() 生成器的 diagram 事件发送，
            # 由 ChatRuntimeEventMapper 自动转换为 diagram.ready 前端事件
            await events.send(event="message.completed", message="回答完成", data={})
            # 记录对话埋点事件（与压缩任务异步解耦）
            try:
                async with session_scope() as db:
                    await record_dialogue_event(
                        db=db,
                        user_id=user_id,
                        session_id=session_id,
                    )
            except Exception:
                logger.exception(
                    "[Chat] 记录对话事件失败: session=%s",
                    session_id,
                )
    # 捕获整体异常，标记失败并发送 message.failed
    except Exception as e:
        logger.exception("聊天 Agent 执行失败: user_message_id=%s", user_message_id)
        await memory_svc.upsert_activity(
            user_id=user_id,
            session_id=session_id,
            user_message_id=user_message_id,
            payload=build_workflow_activity_payload(
                stage="failed",
                activity_id="workflow:current",
                title="回答未完成",
                message=str(e),
                status="failed",
            ),
        )
        await events.send(event="message.failed", message="回答失败", data={"error": str(e)})





# ChatUseCases：聊天服务核心类（附件上传、文件解析、对话流编排、后台任务）
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

    # 初始化文件存储、后台任务集合与记忆服务
    def __init__(self) -> None:
        # 本地文件存储：用户上传文件的磁盘读写
        self.file_store: LocalFileStore = LocalFileStore()
        # 后台任务集合：防止未等待的协程被 GC 回收
        self._background_tasks: set[asyncio.Task] = set()
        self._memory_service = get_chat_memory_service()

    # 生成与 PostgreSQL UUID 列一致的新会话 ID
    def default_session_id(self, user_id: int) -> str:
        """生成与 PostgreSQL UUID 列一致的新会话 ID。"""
        return str(uuid4())

    # 将文字与原始附件快照写入 UserMessage（带 URL 校验与文件类型识别）
    async def create_user_message(
        self,
        *,
        user_id: int,
        session_id: str,
        text: str,
        attachments: list[dict[str, Any]],
    ) -> Any:
        """把文字和原始附件快照直接写入 UserMessage。"""
        # 校验并归一化每个附件（URL 前缀 + 去重）
        normalized_attachments: list[dict[str, Any]] = []
        prefix = f"/api/v1/ai/chat/uploads/{user_id}/{session_id}/"
        seen_urls: set[str] = set()
        for attachment in attachments:
            url = str(attachment.get("url") or "").strip()
            if not url.startswith(prefix) or url in seen_urls:
                raise ValueError("附件地址无效或不属于当前会话")
            filename = url.removeprefix(prefix)
            path = self.file_store.resolve_user_file(
                current_user_id=user_id,
                owner_id=user_id,
                session_id=session_id,
                filename=filename,
            )
            suffix = path.suffix.lower()
            file_type = "image" if suffix in self.file_store.allowed_image_ext else "document"
            normalized_attachments.append({
                "url": url,
                "file_type": file_type,
                "original_name": str(attachment.get("original_name") or filename),
                "mime_type": str(attachment.get("mime_type") or "") or None,
                "size_bytes": path.stat().st_size,
            })
            seen_urls.add(url)
        # 持久化最终归一化的用户消息
        return await self._memory_service.save_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=build_user_content(text, normalized_attachments),
        )

    # 获取会话历史消息，组装为 ChatMessageItem 列表（含附件分析与活动）
    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[ChatMessageItem]:
        """获取会话历史消息，组装为 ChatMessageItem 列表。"""
        # 未指定会话则取最近一个
        memory_svc = get_chat_memory_service()
        if not session_id:
            sessions = await memory_svc.list_sessions(user_id=user_id, limit=1)
            if not sessions:
                return []
            session_id = sessions[0].id

        # 读取原始消息、附件分析与活动记录
        raw_messages = await memory_svc.list_messages(user_id=user_id, session_id=session_id, limit=limit)
        analyses = await memory_svc.list_attachment_analyses(user_id=user_id, session_id=session_id)
        activities = await memory_svc.list_activities(user_id=user_id, session_id=session_id)

        # 按 user_message_id 分组附件分析与活动
        analyses_by_message: dict[int, list[dict[str, Any]]] = {}
        for analysis in analyses:
            analyses_by_message.setdefault(analysis.user_message_id, []).append({
                "id": str(analysis.id),
                "analysis_type": analysis.analysis_type,
                "status": analysis.status,
                "content": analysis.content,
                "error": analysis.error_message,
            })

        activities_by_message: dict[int, list[dict[str, Any]]] = {}
        for activity in activities:
            activities_by_message.setdefault(activity.user_message_id, []).append({
                "activity_id": activity.activity_id,
                "kind": activity.kind,
                "stage": activity.stage,
                "status": activity.status,
                "title": activity.title,
                "summary": activity.summary,
                "message": activity.message,
                "detail": activity.detail or {},
            })

        # 组装每条消息项
        result: list[ChatMessageItem] = []
        final_answer_roots = {
            message.user_message_id
            for message in raw_messages
            if message.role == "assistant" and not message.tool_calls
        }
        for message in raw_messages:
            msg_content: list[dict[str, Any]] = list(message.content) if isinstance(message.content, list) else [{"type": "text", "text": str(message.content)}]
            root_message_id = message.id if message.role == "user" else message.user_message_id
            is_final_assistant = message.role == "assistant" and not message.tool_calls

            result.append(
                ChatMessageItem(
                    id=message.id,
                    user_message_id=root_message_id,
                    role=message.role,
                    content=msg_content,
                    tool_calls=message.tool_calls if isinstance(message.tool_calls, list) else None,
                    tool_call_id=getattr(message, "tool_call_id", None),
                    attachment_analyses=analyses_by_message.get(root_message_id, []) if is_final_assistant else [],
                    activities=activities_by_message.get(root_message_id, []) if is_final_assistant else [],
                    usage_metadata=message.usage_metadata if isinstance(message.usage_metadata, dict) else None,
                    diagram=message.usage_metadata.get("diagram") if (is_final_assistant and isinstance(message.usage_metadata, dict)) else None,
                    created_at=message.created_at,
                )
            )

        # 为仅有活动、无最终回答的用户消息补充一条活动展示项
        for message in raw_messages:
            if message.role != "user" or message.id in final_answer_roots:
                continue
            message_activities = activities_by_message.get(message.id, [])
            if not message_activities:
                continue
            result.append(
                ChatMessageItem(
                    id=-message.id,
                    user_message_id=message.id,
                    role="assistant",
                    content=[],
                    attachment_analyses=analyses_by_message.get(message.id, []),
                    activities=message_activities,
                    created_at=message.created_at,
                )
            )
        # 按时间、角色、ID 排序
        result.sort(key=lambda item: (
            item.created_at,
            0 if item.role == "user" else 1,
            item.id,
        ))
        return result




    # 保存用户上传文件：校验后写入磁盘并返回附件快照
    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        username: str,
        session_id: str,
    ) -> dict[str, Any]:
        """保存用户上传的文件。

        流程：
        1. 校验文件名非空
        2. 检查单次上传文件数是否超限
        3. 调用 LocalFileStore 写入磁盘
        4. 返回附件快照，随 UserMessage 一起提交
        """
        # 校验文件名非空
        if not filename:
            raise ValueError("文件名不能为空")
        # 检查文件数上限
        existing = self.file_store.list_files(username=username, session_id=session_id)
        if len(existing) >= MAX_UPLOAD_FILES_PER_REQUEST:
            raise ValueError(f"单次上传最多 {MAX_UPLOAD_FILES_PER_REQUEST} 个文件")
        # 写入磁盘并返回快照
        payload = await self.file_store.save_upload(
            filename=filename,
            content=content,
            username=username,
            session_id=session_id,
        )
        return payload

    # 解析上传文件路径，带所有者权限校验
    def resolve_uploaded_file(
        self,
        *,
        current_username: str,
        owner_username: str,
        session_id: str,
        filename: str,
    ) -> Path:
        """解析上传文件路径，带权限校验。

        只有文件所有者才能访问，防止越权读取。
        实际路径解析委托给 LocalFileStore.resolve_user_file。
        """
        # 仅文件所有者可访问，防止越权读取
        if current_username != owner_username:
            raise PermissionError("无权访问此文件")
        return self.file_store.resolve_user_file(
            current_username=current_username,
            owner_username=owner_username,
            session_id=session_id,
            filename=filename,
        )

    # 安全地启动后台协程任务，避免被 GC 回收并记录异常
    def _spawn_background(self, coro, *, label: str = "") -> None:
        """安全地启动后台协程任务。

        关键设计：
        1. 任务加入 _background_tasks 集合，防止被 GC 回收
        2. 完成回调自动从集合移除，避免内存泄漏
        3. 异常被 catch 并记录日志，不会影响主流程
        4. 若当前不在事件循环中（极端情况），记录警告而非崩溃
        """
        # 包装协程，捕获并记录异常
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


# 获取主对话的 ChatUseCases 单例（懒加载）
def get_chat_usecases() -> ChatUseCases:
    """获取主对话的 ChatUseCases 单例。

    懒加载模式：首次调用时创建实例，后续复用。
    """
    global _chat_usecases
    if _chat_usecases is None:
        _chat_usecases = ChatUseCases()
    return _chat_usecases


# 获取数字人对话的 ChatUseCases 单例（独立，避免状态互相干扰）
def get_avatar_chat_usecases() -> ChatUseCases:
    """获取数字人对话的 ChatUseCases 单例。

    与主对话单例独立，避免上传文件映射等状态互相干扰。
    """
    global _avatar_chat_usecases
    if _avatar_chat_usecases is None:
        _avatar_chat_usecases = ChatUseCases()
    return _avatar_chat_usecases
