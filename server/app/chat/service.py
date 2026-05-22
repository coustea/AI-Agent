"""Chat application service boundary.

集中保留 chat 的应用层编排，明确主链路为：api -> service -> agent。

主要组件：
- 文件/图片处理接口（含保护机制）
- ConversationStore: 会话/历史持久化
- ChatUseCases: 路由入口与 agent 调用
- get_chat_usecases: 模块装配

通用服务已提取到 app/shared/ 与 app/memory/：
- request_context: ContextVar 请求上下文
- memory facade: MemoryService（记忆/画像/上下文构建）
- vision: VisionService（图片分析）
- file_service: 文件路径解析、内容读取
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Callable

# ---- 通用服务（从 utils 导入） ----
from app.utils.context import runtime_context as chat_runtime_context
from app.memory import MemoryService
from app.utils.vision import build_vision_service
from app.utils.files import resolve_uploaded_path

from app.chat.agent import TutorAgent
from app.chat.runtime import build_user_message_record, latest_user_message, render_recent_chat_context
from app.chat.utils import normalize_message_content, truncate
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.utils.storage import local_file_store

from app.chat.request import ChatHistoryMessage
from app.chat.schemas import AttachmentInfo, ChatMessageItem, TutorAgentContext
from app.prompts import registry
from app.resource.graph_store import get_graph_store

# 模块名称常量
CHAT_MODULE_NAME = "mentor"

logger = get_logger(__name__)
llm = get_llm()

# ---- 保护机制常量 ----
MAX_FILE_CONTENT_CHARS = 15000  # 单个文件最大字符数
MAX_ANALYZE_FILE_COUNT = 8  # 单次分析最大文件数
MAX_ANALYZE_TOTAL_CHARS = 40000  # 单次分析总字符数上限
MAX_PDF_PAGES_TO_READ = 80  # PDF 最大读取页数
MAX_DOCX_PARAGRAPHS_TO_READ = 1200  # DOCX 最大读取段落数
MAX_IMAGE_ANALYZE_COUNT = 8  # 单次分析最大图片数
MAX_UPLOAD_FILES_PER_REQUEST = 12  # 单次上传最大文件数
AVATAR_MODULE_NAME = "avatar"  # 数字人模块名称


# ---------------------------------------------------------------------------
# SSE 编码
# ---------------------------------------------------------------------------

def format_sse(event: str, data: Any) -> str:
    """编码单个 SSE 帧。

    Args:
        event: 事件类型名称。
        data: 事件数据，字符串或可 JSON 序列化的对象。

    Returns:
        符合 SSE 规范的文本帧。
    """
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    lines = payload.splitlines() or [""]
    body = "\n".join(f"data: {line}" for line in lines)
    return f"event: {event}\n{body}\n\n"


# ---------------------------------------------------------------------------
# 增强文件读取（带保护机制的版本，chat 模块专用）
# ---------------------------------------------------------------------------

def read_uploaded_file_content_with_meta(absolute_path: str) -> dict[str, Any]:
    """读取上传文档内容并返回保护机制元数据。

    支持 PDF、DOCX、TXT、MD、LOG 格式，包含页数/段落/长度截断提示。

    Args:
        absolute_path: 文件绝对路径。

    Returns:
        包含 success、content、notes 字段的字典。
    """
    path = Path(absolute_path)
    if not path.exists():
        return {
            "success": False,
            "content": f"文件不存在: {absolute_path}",
            "notes": [],
        }
    if not path.is_file():
        return {
            "success": False,
            "content": f"路径不是文件: {absolute_path}",
            "notes": [],
        }

    notes: list[str] = []
    suffix = path.suffix.lower()

    # 处理 PDF 文件
    if suffix == ".pdf":
        from pymupdf import open as pdf_open

        text_parts = []
        with pdf_open(str(path)) as doc:
            total_pages = len(doc)
            pages_to_read = min(total_pages, MAX_PDF_PAGES_TO_READ)
            for idx in range(pages_to_read):
                text_parts.append(doc[idx].get_text())
            # 超过页数限制时添加提示
            if total_pages > MAX_PDF_PAGES_TO_READ:
                notes.append(f"PDF 共 {total_pages} 页，为保护性能仅分析前 {MAX_PDF_PAGES_TO_READ} 页。")
        content = "\n".join(text_parts)

    # 处理 DOCX 文件
    elif suffix == ".docx":
        from docx import Document

        doc = Document(str(path))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        total_paragraphs = len(paragraphs)
        # 超过段落限制时添加提示
        if total_paragraphs > MAX_DOCX_PARAGRAPHS_TO_READ:
            notes.append(
                f"DOCX 共 {total_paragraphs} 个段落，为保护性能仅分析前 {MAX_DOCX_PARAGRAPHS_TO_READ} 个段落。"
            )
        content = "\n".join(paragraphs[:MAX_DOCX_PARAGRAPHS_TO_READ])

    # 处理纯文本文件
    elif suffix in {".txt", ".md", ".log"}:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

    else:
        return {
            "success": False,
            "content": f"不支持的文件类型: {suffix}（支持: .pdf, .docx, .txt, .md, .log）",
            "notes": [],
        }

    # 处理空内容
    if not content or not content.strip():
        return {
            "success": True,
            "content": "文件内容为空",
            "notes": notes,
        }

    # 超过字符限制时截断
    if len(content) > MAX_FILE_CONTENT_CHARS:
        content = content[:MAX_FILE_CONTENT_CHARS] + "\n\n[...文档内容过长，已截断...]"
        notes.append(f"文档文本超过 {MAX_FILE_CONTENT_CHARS} 字符，已截断。")

    return {
        "success": True,
        "content": content,
        "notes": notes,
    }


async def analyze_documents(*, current_user_id: int, file_urls: list[str], question: str) -> dict:
    """批量读取用户上传的文档内容（含保护机制），返回分析摘要。

    Args:
        current_user_id: 当前用户ID。
        file_urls: 文件URL列表。
        question: 用户问题。

    Returns:
        包含 success、documents、analysis_text、error、notices 字段的字典。
    """
    documents: list[dict[str, str]] = []
    snippets: list[str] = []
    notices: list[str] = []
    remaining_chars = MAX_ANALYZE_TOTAL_CHARS

    # 限制文件数量
    limited_file_urls = (file_urls or [])[:MAX_ANALYZE_FILE_COUNT]
    if len(file_urls or []) > MAX_ANALYZE_FILE_COUNT:
        notices.append(
            f"本次上传文档 {len(file_urls)} 个，为保护性能仅分析前 {MAX_ANALYZE_FILE_COUNT} 个文档。"
        )

    for file_url in limited_file_urls:
        # 检查剩余字符预算
        if remaining_chars <= 0:
            notices.append("已达到本轮分析内容上限，后续文档将不再展开解析。")
            break

        # 解析文件路径
        resolved = resolve_uploaded_path(file_url)
        if resolved is None:
            logger.warning("[DocumentAnalysis] failed to resolve %s", file_url)
            continue

        owner_id, absolute_path = resolved
        # 权限校验
        if owner_id != current_user_id:
            logger.warning("[DocumentAnalysis] forbidden file access user=%s owner=%s", current_user_id, owner_id)
            continue

        # 读取文件内容
        content_payload = read_uploaded_file_content_with_meta(absolute_path)
        content = str(content_payload.get("content", ""))
        note_items = [str(item) for item in (content_payload.get("notes") or []) if str(item).strip()]
        notices.extend(note_items)

        # 截断超出预算的内容
        if len(content) > remaining_chars:
            content = content[:remaining_chars] + "\n\n[...超出本轮分析内容预算，已截断...]"
            notices.append(f"分析总文本已达到 {MAX_ANALYZE_TOTAL_CHARS} 字符上限，后续内容已截断。")
        remaining_chars = max(0, remaining_chars - len(content))

        documents.append({
            "url": file_url,
            "name": Path(absolute_path).name,
            "absolute_path": absolute_path,
            "content": content,
        })
        note_text = f"\n[保护提示] {'; '.join(note_items)}" if note_items else ""
        snippets.append(f"文件《{Path(absolute_path).name}》内容如下：\n{content}{note_text}")

    # 无有效文档时返回错误
    if not documents:
        return {
            "success": False,
            "documents": [],
            "analysis_text": "未能读取可分析的文档内容。",
            "error": "未找到可访问的文档。",
            "notices": notices,
        }

    # 构建分析文本
    notice_prefix = ""
    if notices:
        uniq_notices = list(dict.fromkeys(notices))
        notice_prefix = "分析保护提示：\n" + "\n".join(f"- {msg}" for msg in uniq_notices) + "\n\n"
    analysis_text = (
        f"用户问题：{question or '请分析这些文档'}\n\n"
        + notice_prefix
        + "以下是已提取的文档内容，请基于它们回答用户问题，并在回答中尽量提炼知识点：\n\n"
        + "\n\n".join(snippets)
    )

    return {
        "success": True,
        "documents": documents,
        "analysis_text": analysis_text,
        "error": None,
        "notices": list(dict.fromkeys(notices)),
    }


def _build_attachment_analysis_context(
    *,
    image_result: dict[str, Any] | None,
    document_result: dict[str, Any] | None,
) -> str:
    """构建附件分析上下文文本。

    合并图片和文档的分析结果。

    Args:
        image_result: 图片分析结果。
        document_result: 文档分析结果。

    Returns:
        合并后的上下文文本。
    """
    sections: list[str] = []

    if isinstance(image_result, dict):
        image_text = str(image_result.get("analysis_text", "")).strip()
        if image_text:
            mode = str(image_result.get("mode", "unknown")).strip() or "unknown"
            sections.append(f"### 图片预分析（mode={mode}）\n{image_text}")

    if isinstance(document_result, dict):
        doc_text = str(document_result.get("analysis_text", "")).strip()
        if doc_text:
            sections.append(f"### 文档预分析\n{doc_text}")

    if not sections:
        return ""
    return truncate("\n\n".join(sections), 8000)


async def analyze_attachments_parallel(
    *,
    current_user_id: int,
    image_urls: list[str],
    file_urls: list[str],
    question: str,
    vision_service: "VisionService",
) -> dict[str, Any]:
    """并行分析附件（图片 + 文档），返回结构化结果与可注入上下文。

    Args:
        current_user_id: 当前用户ID。
        image_urls: 图片URL列表。
        file_urls: 文件URL列表。
        question: 用户问题。
        vision_service: 视觉服务实例。

    Returns:
        包含 success、image、document、analysis_context、notices 字段的字典。
    """
    image_urls = image_urls or []
    file_urls = file_urls or []
    notices: list[str] = []

    # 限制图片数量
    if len(image_urls) > MAX_IMAGE_ANALYZE_COUNT:
        notices.append(f"本次上传图片 {len(image_urls)} 张，为保护性能仅分析前 {MAX_IMAGE_ANALYZE_COUNT} 张。")
        image_urls = image_urls[:MAX_IMAGE_ANALYZE_COUNT]

    result: dict[str, Any] = {
        "success": False,
        "image": None,
        "document": None,
        "analysis_context": "",
        "notices": notices,
    }
    if not image_urls and not file_urls:
        return result

    # 并行启动图片和文档分析任务
    tasks: list[asyncio.Task] = []
    slots: list[str] = []

    if image_urls:
        tasks.append(asyncio.create_task(vision_service.analyze_images(image_urls, question)))
        slots.append("image")
    if file_urls:
        tasks.append(
            asyncio.create_task(
                analyze_documents(
                    current_user_id=current_user_id,
                    file_urls=file_urls,
                    question=question,
                )
            )
        )
        slots.append("document")

    # 等待所有任务完成
    done = await asyncio.gather(*tasks, return_exceptions=True)
    for slot, payload in zip(slots, done):
        if isinstance(payload, Exception):
            logger.exception("[AttachmentAnalysis] %s analyze failed", slot)
            result[slot] = {
                "success": False,
                "analysis_text": "",
                "error": str(payload),
            }
            continue
        result[slot] = payload

    # 构建分析上下文
    image_result = result.get("image")
    document_result = result.get("document")
    result["analysis_context"] = _build_attachment_analysis_context(
        image_result=image_result if isinstance(image_result, dict) else None,
        document_result=document_result if isinstance(document_result, dict) else None,
    )

    # 添加保护提示
    if notices:
        notice_block = "### 附件分析保护提示\n" + "\n".join(f"- {msg}" for msg in notices)
        result["analysis_context"] = (
            f"{notice_block}\n\n{result['analysis_context']}" if result["analysis_context"] else notice_block
        )
    result["success"] = bool(result["analysis_context"])
    return result


# ---------------------------------------------------------------------------
# 知识图谱持久化
# ---------------------------------------------------------------------------

async def store_knowledge_graph(
    *,
    user_id: int,
    session_id: str,
    graph: dict[str, Any],
) -> dict[str, Any]:
    """将知识图谱存储到 Neo4j。

    Args:
        user_id: 用户ID。
        session_id: 会话ID。
        graph: 归一化后的图谱数据。

    Returns:
        存储结果元数据。
    """
    try:
        return await get_graph_store().upsert_graph(
            user_id=user_id,
            resource_id=session_id or "chat",
            agent_id="chat",
            graph=graph,
        )
    except Exception as exc:
        logger.exception("[ChatService] 聊天知识图谱 Neo4j 存储失败")
        return {"stored": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# 会话与历史持久化
# ---------------------------------------------------------------------------

class ConversationStore:
    """对话会话与历史持久化。

    封装会话列表、创建、归档和历史查询操作。
    """

    async def list_sessions(self, user_id: int, limit: int = 30, module_name: str = CHAT_MODULE_NAME) -> list[dict]:
        """获取用户的会话列表。

        Args:
            user_id: 用户ID。
            limit: 返回数量限制。
            module_name: 模块名称。

        Returns:
            会话信息列表，包含 id、title、updated_at 字段。
        """
        memory_layer = MemoryService(module=module_name)
        sessions = await memory_layer.list_sessions(user_id=user_id, limit=limit)
        return [{"id": s.id, "title": s.title, "updated_at": s.updated_at} for s in sessions]

    async def create_session(
        self,
        user_id: int,
        title: str = "新对话",
        module_name: str = CHAT_MODULE_NAME,
    ) -> dict:
        """创建新会话。

        Args:
            user_id: 用户ID。
            title: 会话标题。
            module_name: 模块名称。

        Returns:
            新创建的会话信息。
        """
        memory_layer = MemoryService(module=module_name)
        session = await memory_layer.create_session(user_id=user_id, title=title)
        return {"id": session.id, "title": session.title}

    async def archive_session(self, user_id: int, session_id: str, module_name: str = CHAT_MODULE_NAME) -> bool:
        """归档会话（软删除）。

        Args:
            user_id: 用户ID。
            session_id: 会话ID。
            module_name: 模块名称。

        Returns:
            操作是否成功。
        """
        memory_layer = MemoryService(module=module_name)
        return await memory_layer.archive_session(user_id=user_id, session_id=session_id)

    async def update_session_title(
        self,
        user_id: int,
        session_id: str,
        title: str,
        module_name: str = CHAT_MODULE_NAME,
    ) -> bool:
        """更新会话标题。

        Args:
            user_id: 用户ID。
            session_id: 会话ID。
            title: 新标题。
            module_name: 模块名称。

        Returns:
            操作是否成功。
        """
        memory_layer = MemoryService(module=module_name)
        return await memory_layer.update_session_title(user_id=user_id, session_id=session_id, title=title)

    async def generate_session_title(
        self,
        user_id: int,
        session_id: str,
        first_message: str,
        module_name: str = CHAT_MODULE_NAME,
    ) -> str | None:
        """使用 spark-x2-flash 生成会话标题。

        Args:
            user_id: 用户ID。
            session_id: 会话ID。
            first_message: 用户的第一条消息。
            module_name: 模块名称。

        Returns:
            生成的标题，失败返回 None。
        """
        memory_layer = MemoryService(module=module_name)
        return await memory_layer.generate_session_title(
            user_id=user_id,
            session_id=session_id,
            first_message=first_message,
        )

    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
        module_name: str = CHAT_MODULE_NAME,
    ) -> list[ChatMessageItem]:
        """获取聊天历史。

        Args:
            user_id: 用户ID。
            session_id: 可选的会话ID，为空则返回最近会话的历史。
            limit: 返回消息数量限制。
            module_name: 模块名称。

        Returns:
            消息条目列表。
        """
        memory_layer = MemoryService(module=module_name)
        target_session = session_id
        # 未指定会话时获取最近的会话
        if not target_session:
            sessions = await memory_layer.list_sessions(user_id=user_id, limit=1)
            if not sessions:
                return []
            target_session = sessions[0].id

        messages = await memory_layer.list_messages(
            user_id=user_id,
            session_id=target_session,
            limit=limit,
            only_unexpired=False,
        )

        # 转换为 API 响应格式
        items: list[ChatMessageItem] = []
        for msg in messages:
            attachments = None
            if msg.attachments:
                try:
                    attachments = [AttachmentInfo(**value) for value in msg.attachments]
                except (TypeError, ValueError):
                    attachments = None

            items.append(
                ChatMessageItem(
                    role=msg.role,
                    content=msg.content,
                    attachments=attachments,
                    knowledge_graph=msg.knowledge_graph,
                    created_at=msg.created_at,
                )
            )
        return items


# ---------------------------------------------------------------------------
# Chat 用例入口
# ---------------------------------------------------------------------------

class ChatUseCases:
    """路由层可调用的 chat 应用入口。

    封装对话流、文件上传、会话管理等业务逻辑。
    """

    def __init__(
        self,
        *,
        conversation_store: ConversationStore,
        file_store: Any = local_file_store,
        module_name: str = CHAT_MODULE_NAME,
        default_session_suffix: str | None = None,
        stream_runner: Callable[..., Any] | None = None,
    ) -> None:
        """初始化 ChatUseCases。

        Args:
            conversation_store: 会话存储实例。
            file_store: 文件存储实例。
            module_name: 模块名称。
            default_session_suffix: 默认会话ID后缀。
            stream_runner: 可选的流式运行器。
        """
        self.conversation_store = conversation_store
        self.file_store = file_store
        self.module_name = module_name
        self.default_session_suffix = default_session_suffix or module_name
        self._stream_runner = stream_runner

    def default_session_id(self, user_id: int) -> str:
        """生成默认会话ID。

        Args:
            user_id: 用户ID。

        Returns:
            格式化的默认会话ID。
        """
        return f"user-{user_id}-default-{self.default_session_suffix}"

    @staticmethod
    def _normalize_history(
        *,
        history: list[ChatHistoryMessage | dict[str, Any]] | None,
        user_message: str | None,
    ) -> list[ChatHistoryMessage]:
        normalized: list[ChatHistoryMessage] = []
        for item in history or []:
            try:
                normalized.append(item if isinstance(item, ChatHistoryMessage) else ChatHistoryMessage(**item))
            except Exception:
                logger.warning("[ChatUseCases] 忽略无效 history item=%s", truncate(item, 160))
        if not normalized and (user_message or "").strip():
            normalized.append(ChatHistoryMessage(role="user", content=str(user_message).strip()))
        return normalized

    @staticmethod
    def _normalize_stream_event(event: Any) -> dict[str, Any]:
        if isinstance(event, dict):
            if "event" in event and "data" in event:
                return event
            if "type" in event:
                normalized_data = event.get("data")
                if normalized_data is None and "content" in event:
                    normalized_data = event.get("content")
                if normalized_data is None and "full_response" in event:
                    normalized_data = {"full_response": event.get("full_response", "")}
                if normalized_data is None:
                    normalized_data = ""
                return {"event": str(event.get("type")), "data": normalized_data}
        return {"event": "message", "data": event}

    def _spawn_background(self, coro: Any, *, task_name: str) -> None:
        task = asyncio.create_task(coro, name=task_name)

        def _done_callback(done_task: asyncio.Task) -> None:
            if done_task.cancelled():
                return
            try:
                done_task.result()
            except Exception:
                logger.exception("[ChatUseCases] 后台任务异常 task=%s", task_name)

        task.add_done_callback(_done_callback)

    async def _build_attachment_analysis(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        image_urls: list[str],
        file_urls: list[str],
        attachment_analysis: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """构建附件分析结果。

        如果已提供分析结果则直接返回，否则执行并行分析。

        Args:
            user_id: 用户ID。
            session_id: 会话ID。
            user_message: 用户消息。
            image_urls: 图片URL列表。
            file_urls: 文件URL列表。
            attachment_analysis: 可选的预分析结果。

        Returns:
            附件分析结果字典。
        """
        if attachment_analysis is not None:
            return attachment_analysis

        if not image_urls and not file_urls:
            return None

        try:
            vision_service = build_vision_service(llm)
            built = await analyze_attachments_parallel(
                current_user_id=user_id,
                image_urls=image_urls,
                file_urls=file_urls,
                question=user_message,
                vision_service=vision_service,
            )
            logger.info(
                "[ChatUseCases] 附件并行预分析完成 module=%s user=%s session=%s has_image=%s has_doc=%s has_context=%s",
                self.module_name,
                user_id,
                session_id,
                bool(image_urls),
                bool(file_urls),
                bool((built or {}).get("analysis_context")),
            )
            return built
        except Exception:
            logger.exception(
                "[ChatUseCases] 附件并行预分析失败 module=%s user=%s session=%s",
                self.module_name,
                user_id,
                session_id,
            )
            return None

    async def build_tutor_agent_context(
        self,
        *,
        memory_layer: MemoryService,
        user_id: int,
        session_id: str,
        history: list[ChatHistoryMessage],
        image_urls: list[str],
        file_urls: list[str],
        attachment_analysis: dict[str, Any] | None,
        enable_search: bool,
        enable_long_term_memory: bool,
        need_knowledge_graph: bool,
        generate_video: bool,
        resource_mode: str = "none",
    ) -> TutorAgentContext:
        """Build initialized TutorAgent context; all persistence stays in service layer."""
        profile_context = await memory_layer.build_profile_context(user_id)
        long_term_context = (
            await memory_layer.build_memory_context(user_id)
            if enable_long_term_memory
            else "长期记忆未启用。"
        )
        session_summary_context = await self._build_session_summary_context(
            memory_layer=memory_layer,
            user_id=user_id,
            session_id=session_id,
        )
        recent_chat_context = render_recent_chat_context(history)
        file_context = memory_layer.build_file_context(image_urls, file_urls)
        attachment_analysis_context = str((attachment_analysis or {}).get("analysis_context", "")).strip()

        recent_sections: list[str] = []
        if session_summary_context:
            recent_sections.append(f"# 会话概要\n{session_summary_context}")
        recent_sections.append(f"# 最近对话\n{recent_chat_context}")
        if file_context:
            recent_sections.append(f"# 文件上下文\n{file_context}")
        prompt_recent_context = "\n\n".join(recent_sections)
        analysis_hint = (
            f"\n\n### 附件并行预分析结果\n{attachment_analysis_context}\n"
            if attachment_analysis_context
            else ""
        )
        system_prompt = registry.get("chat/tutor_system").format(
            profile_context=profile_context,
            fact_context=long_term_context,
            recent_chat_context=prompt_recent_context,
        ) + analysis_hint

        return TutorAgentContext(
            user_id=user_id,
            session_id=session_id,
            system_prompt=system_prompt,
            profile_context=profile_context,
            long_term_memory_context=long_term_context,
            session_summary_context=session_summary_context,
            recent_chat_context=recent_chat_context,
            file_context=file_context,
            attachment_analysis_context=attachment_analysis_context,
            attachment_analysis=attachment_analysis or {},
            image_urls=list(image_urls),
            file_urls=list(file_urls),
            enable_search=enable_search,
            need_knowledge_graph=need_knowledge_graph,
            generate_video=generate_video,
            resource_mode=resource_mode,
        )

    async def _build_session_summary_context(
        self,
        *,
        memory_layer: MemoryService,
        user_id: int,
        session_id: str,
    ) -> str:
        try:
            summaries = await memory_layer.list_summaries(user_id=user_id, session_id=session_id, limit=2)
        except Exception:
            logger.debug("[ChatUseCases] build session summary context failed", exc_info=True)
            return ""
        return "\n\n---\n\n".join(
            str(getattr(summary, "summary_markdown", "") or "").strip()
            for summary in summaries
            if str(getattr(summary, "summary_markdown", "") or "").strip()
        )

    async def stream_chat_events(
        self,
        *,
        user_id: int,
        user_message: str | None = None,
        history: list[ChatHistoryMessage | dict[str, Any]] | None = None,
        session_id: str | None = None,
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
        need_knowledge_graph: bool = False,
        generate_video: bool = False,
        enable_search: bool = False,
        enable_long_term_memory: bool = False,
        attachment_analysis: dict[str, Any] | None = None,
        stream_runner: Callable[..., Any] | None = None,
        input_source: str | None = None,
        persist: bool = True,
    ):
        """流式生成对话事件。

        Args:
            user_id: 用户ID。
            user_message: 兼容字段；为空时从 history 最后一条用户消息读取。
            history: 调用方传入的对话历史。
            session_id: 可选的会话ID。
            image_urls: 图片URL列表。
            file_urls: 文件URL列表。
            need_knowledge_graph: 是否生成知识图谱。
            generate_video: 是否生成视频。
            enable_search: 是否启用搜索。
            enable_long_term_memory: 是否启用长期记忆读写。
            attachment_analysis: 可选的附件预分析结果。
            stream_runner: 可选的流式运行器。
            input_source: 输入来源标识。
            persist: 是否由 chat 服务层保存消息并触发后处理。

        Yields:
            事件字典，包含 event 和 data 字段。
        """
        effective_session = session_id or self.default_session_id(user_id)
        # 去重URL
        merged_image_urls = list(dict.fromkeys(image_urls or []))
        merged_file_urls = list(dict.fromkeys(file_urls or []))
        normalized_history = self._normalize_history(history=history, user_message=user_message)
        current_user_message = latest_user_message(normalized_history)
        if not current_user_message:
            yield {"event": "error", "data": "缺少用户消息：请在 history 中传入至少一条 user 消息。"}
            yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
            return

        # 构建附件分析
        prepared_attachment_analysis = await self._build_attachment_analysis(
            user_id=user_id,
            session_id=effective_session,
            user_message=current_user_message,
            image_urls=merged_image_urls,
            file_urls=merged_file_urls,
            attachment_analysis=attachment_analysis,
        )
        memory_layer = MemoryService(module=self.module_name)
        user_record = build_user_message_record(
            current_user_message,
            image_urls=merged_image_urls,
            file_urls=merged_file_urls,
        )
        if persist:
            try:
                await memory_layer.save_message(
                    user_id=user_id,
                    session_id=effective_session,
                    role="user",
                    content=user_record.content,
                    attachments=user_record.attachments,
                )
            except Exception as exc:
                logger.exception("[ChatUseCases] 用户消息保存失败")
                yield {"event": "error", "data": f"保存消息失败: {exc}"}
                yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
                return

        agent_context = await self.build_tutor_agent_context(
            memory_layer=memory_layer,
            user_id=user_id,
            session_id=effective_session,
            history=normalized_history,
            image_urls=merged_image_urls,
            file_urls=merged_file_urls,
            attachment_analysis=prepared_attachment_analysis,
            enable_search=bool(enable_search),
            enable_long_term_memory=bool(enable_long_term_memory),
            need_knowledge_graph=bool(need_knowledge_graph),
            generate_video=bool(generate_video),
        )
        runner = stream_runner or self._stream_runner

        full_reply = ""
        final_done_payload: Any = None
        knowledge_graph: dict[str, Any] | None = None
        stream_had_error = False

        with chat_runtime_context(user_id, effective_session):
            event_source = (
                runner(context=agent_context, history=normalized_history)
                if runner is not None
                else TutorAgent(agent_context).chat_stream(normalized_history)
            )
            async for event in event_source:
                normalized_event = self._normalize_stream_event(event)
                event_name = str(normalized_event.get("event", "message"))
                payload = normalized_event.get("data")

                if event_name == "token":
                    full_reply += normalize_message_content(payload)
                    yield normalized_event
                    continue
                if event_name == "error":
                    stream_had_error = True
                    yield normalized_event
                    continue
                if event_name == "done":
                    final_done_payload = payload
                    if isinstance(payload, dict):
                        maybe_reply = normalize_message_content(
                            payload.get("full_response") or payload.get("response") or ""
                        )
                        if maybe_reply:
                            full_reply = maybe_reply
                        resources = payload.get("resources")
                        if isinstance(resources, dict) and isinstance(resources.get("knowledge_graph"), dict):
                            knowledge_graph = resources["knowledge_graph"]
                    continue
                yield normalized_event

        if stream_had_error:
            yield {"event": "done", "data": final_done_payload or {"session_id": effective_session, "error": True}}
            return

        if persist and full_reply:
            try:
                await memory_layer.save_message(
                    user_id=user_id,
                    session_id=effective_session,
                    role="assistant",
                    content=full_reply,
                    knowledge_graph=knowledge_graph,
                )
                self._spawn_background(
                    memory_layer.after_turn(
                        user_id=user_id,
                        session_id=effective_session,
                        user_message=current_user_message,
                        assistant_reply=full_reply,
                        enable_long_term_memory=enable_long_term_memory,
                    ),
                    task_name="post_chat_pipeline",
                )
            except Exception as exc:
                logger.exception("[ChatUseCases] 回复保存失败")
                yield {"event": "error", "data": f"保存回复失败: {exc}"}
                yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
                return

        yield {"event": "done", "data": final_done_payload or {"session_id": effective_session}}

    async def prepare_uploads(
        self,
        *,
        files: list[tuple[str, bytes]],
        user_id: int,
        session_id: str | None = None,
    ) -> tuple[str, list[str], list[str]]:
        """准备上传文件。

        Args:
            files: 文件列表，每项为 (文件名, 文件内容) 元组。
            user_id: 用户ID。
            session_id: 可选的会话ID。

        Returns:
            (有效会话ID, 图片URL列表, 文件URL列表) 元组。

        Raises:
            ValueError: 文件数量超过限制或文件名为空。
        """
        if len(files) > MAX_UPLOAD_FILES_PER_REQUEST:
            raise ValueError(f"单次最多上传 {MAX_UPLOAD_FILES_PER_REQUEST} 个文件，请分批上传。")
        effective_session = session_id or self.default_session_id(user_id)
        image_urls: list[str] = []
        file_urls: list[str] = []

        for filename, content in files:
            if not filename:
                raise ValueError("文件名不能为空")
            saved = await self.save_upload(
                filename=filename,
                content=content,
                user_id=user_id,
                session_id=effective_session,
            )
            if saved["file_type"] == "image":
                image_urls.append(saved["url"])
            else:
                file_urls.append(saved["url"])

        return effective_session, image_urls, file_urls

    async def analyze_uploaded_attachments(
        self,
        *,
        user_id: int,
        question: str,
        session_id: str | None = None,
        files: list[tuple[str, bytes]] | None = None,
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        """上传并并行分析附件，返回可复用的分析结果。

        Args:
            user_id: 用户ID。
            question: 用户问题。
            session_id: 可选的会话ID。
            files: 可选的文件列表。
            image_urls: 可选的图片URL列表。
            file_urls: 可选的文件URL列表。

        Returns:
            包含会话ID、URL列表和附件分析结果的字典。
        """
        upload_payloads = files or []
        effective_session = session_id or self.default_session_id(user_id)

        uploaded_image_urls: list[str] = []
        uploaded_file_urls: list[str] = []
        # 处理上传文件
        if upload_payloads:
            (
                effective_session,
                uploaded_image_urls,
                uploaded_file_urls,
            ) = await self.prepare_uploads(
                files=upload_payloads,
                user_id=user_id,
                session_id=effective_session,
            )

        # 合并URL
        merged_image_urls = list(dict.fromkeys(uploaded_image_urls + list(image_urls or [])))
        merged_file_urls = list(dict.fromkeys(uploaded_file_urls + list(file_urls or [])))

        # 构建附件分析
        attachment_analysis = await self._build_attachment_analysis(
            user_id=user_id,
            session_id=effective_session,
            user_message=question,
            image_urls=merged_image_urls,
            file_urls=merged_file_urls,
            attachment_analysis=None,
        )
        return {
            "session_id": effective_session,
            "uploaded_image_urls": uploaded_image_urls,
            "uploaded_file_urls": uploaded_file_urls,
            "image_urls": merged_image_urls,
            "file_urls": merged_file_urls,
            "attachment_analysis": attachment_analysis or {
                "success": False,
                "image": None,
                "document": None,
                "analysis_context": "",
                "notices": [],
            },
        }

    async def stream_chat(
        self,
        *,
        user_id: int,
        user_message: str | None = None,
        history: list[ChatHistoryMessage | dict[str, Any]] | None = None,
        session_id: str | None = None,
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
        need_knowledge_graph: bool = False,
        generate_video: bool = False,
        enable_search: bool = False,
        enable_long_term_memory: bool = False,
        attachment_analysis: dict[str, Any] | None = None,
        stream_runner: Callable[..., Any] | None = None,
        input_source: str | None = None,
        persist: bool = True,
    ):
        """流式生成对话响应（SSE 格式）。

        Args:
            user_id: 用户ID。
            user_message: 兼容字段；为空时从 history 最后一条用户消息读取。
            history: 调用方传入的对话历史。
            session_id: 可选的会话ID。
            image_urls: 图片URL列表。
            file_urls: 文件URL列表。
            need_knowledge_graph: 是否生成知识图谱。
            generate_video: 是否生成视频。
            enable_search: 是否启用搜索。
            enable_long_term_memory: 是否启用长期记忆读写。
            attachment_analysis: 可选的附件预分析结果。
            stream_runner: 可选的流式运行器。
            input_source: 输入来源标识。

        Yields:
            SSE 格式的文本帧。
        """
        async for event in self.stream_chat_events(
            user_id=user_id,
            user_message=user_message,
            history=history,
            session_id=session_id,
            image_urls=image_urls,
            file_urls=file_urls,
            need_knowledge_graph=need_knowledge_graph,
            generate_video=generate_video,
            enable_search=enable_search,
            enable_long_term_memory=enable_long_term_memory,
            attachment_analysis=attachment_analysis,
            stream_runner=stream_runner,
            input_source=input_source,
            persist=persist,
        ):
            yield format_sse(event["event"], event["data"])

    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        user_id: int,
        session_id: str,
    ) -> dict:
        """保存上传文件。

        Args:
            filename: 文件名。
            content: 文件内容。
            user_id: 用户ID。
            session_id: 会话ID。

        Returns:
            保存结果，包含 url、file_type 等字段。
        """
        return await self.file_store.save_upload(
            filename=filename,
            content=content,
            user_id=user_id,
            session_id=session_id,
        )

    def resolve_uploaded_file(
        self,
        *,
        current_user_id: int,
        owner_id: int,
        session_id: str,
        filename: str,
    ):
        """解析上传文件路径（带权限校验）。

        Args:
            current_user_id: 当前用户ID。
            owner_id: 文件所有者ID。
            session_id: 会话ID。
            filename: 文件名。

        Returns:
            文件绝对路径。

        Raises:
            PermissionError: 权限不足。
            ValueError: 参数无效。
            FileNotFoundError: 文件不存在。
        """
        return self.file_store.resolve_user_file(
            current_user_id=current_user_id,
            owner_id=owner_id,
            session_id=session_id,
            filename=filename,
        )

    async def list_sessions(self, user_id: int, limit: int = 20) -> list[dict]:
        """获取用户的会话列表。

        Args:
            user_id: 用户ID。
            limit: 返回数量限制。

        Returns:
            会话信息列表。
        """
        return await self.conversation_store.list_sessions(user_id, limit, module_name=self.module_name)

    async def create_session(self, user_id: int, title: str = "新对话") -> dict:
        """创建新会话。

        Args:
            user_id: 用户ID。
            title: 会话标题。

        Returns:
            新创建的会话信息。
        """
        return await self.conversation_store.create_session(user_id, title, module_name=self.module_name)

    async def archive_session(self, user_id: int, session_id: str) -> bool:
        """归档会话。

        Args:
            user_id: 用户ID。
            session_id: 会话ID。

        Returns:
            操作是否成功。
        """
        return await self.conversation_store.archive_session(user_id, session_id, module_name=self.module_name)

    async def update_session_title(self, user_id: int, session_id: str, title: str) -> bool:
        """更新会话标题。

        Args:
            user_id: 用户ID。
            session_id: 会话ID。
            title: 新标题。

        Returns:
            操作是否成功。
        """
        return await self.conversation_store.update_session_title(user_id, session_id, title, module_name=self.module_name)

    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
    ):
        """获取聊天历史。

        Args:
            user_id: 用户ID。
            session_id: 可选的会话ID。
            limit: 返回消息数量限制。

        Returns:
            消息条目列表。
        """
        return await self.conversation_store.get_history(
            user_id=user_id,
            session_id=session_id,
            limit=limit,
            module_name=self.module_name,
        )


# ---------------------------------------------------------------------------
# 模块装配
# ---------------------------------------------------------------------------

# 会话存储单例
conversation_store = ConversationStore()
# Chat 用例单例
chat_usecases: ChatUseCases | None = None
# 数字人 Chat 用例单例
avatar_chat_usecases: ChatUseCases | None = None


def get_chat_usecases() -> ChatUseCases:
    """获取 Chat 用例单例。

    Returns:
        ChatUseCases 实例。
    """
    global chat_usecases
    if chat_usecases is None:
        chat_usecases = ChatUseCases(
            conversation_store=conversation_store,
            module_name=CHAT_MODULE_NAME,
            default_session_suffix=CHAT_MODULE_NAME,
        )
    return chat_usecases


def get_avatar_chat_usecases() -> ChatUseCases:
    """获取数字人 Chat 用例单例。

    Returns:
        用于数字人模块的 ChatUseCases 实例。
    """
    global avatar_chat_usecases
    if avatar_chat_usecases is None:
        avatar_chat_usecases = ChatUseCases(
            conversation_store=conversation_store,
            module_name=AVATAR_MODULE_NAME,
            default_session_suffix=AVATAR_MODULE_NAME,
        )
    return avatar_chat_usecases


__all__ = [
    "CHAT_MODULE_NAME",
    "ChatUseCases",
    "ConversationStore",
    "chat_runtime_context",
    "chat_usecases",
    "conversation_store",
    "format_sse",
    "get_avatar_chat_usecases",
    "get_chat_usecases",
    "resolve_uploaded_path",
    "read_uploaded_file_content_with_meta",
    "analyze_documents",
    "analyze_attachments_parallel",
    "build_vision_service",
    "store_knowledge_graph",
]
