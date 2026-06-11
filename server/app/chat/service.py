"""聊天服务层 — 对话流编排、记忆管理、附件分析、文件上传。

核心类 ChatUseCases 是前端 SSE 流的入口，编排完整对话生命周期：
  1. 解析请求，创建 turn 记录
  2. 调用 TurnOrchestrator 执行四阶段流水线（附件→搜索→推理→图解）
  3. 安全过滤最终回答
  4. 持久化消息、工具调用、turn 事件
  5. 后台触发记忆管线（压缩+长期记忆）和画像更新

内联模块（原独立文件合并）：
  - ContentSafetyFilter / safety_filter — 基于正则的敏感词过滤
  - LocalFileStore — 用户上传文件的磁盘读写

单例管理：get_chat_usecases() / get_avatar_chat_usecases() 分别服务主对话和数字人对话。
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, NamedTuple

from app.chat.memory.service import get_chat_memory_service as _get_chat_memory_service
from app.chat.orchestrator import TurnOrchestrator, project_turn_run
from app.chat.stages import AttachmentAnalyzer
from app.chat.schemas import ChatHistoryMessage, UploadResponse
from app.chat.runtime import _classify_attachments, build_user_message_record, latest_user_message
from app.chat.schemas import TurnRequest
from app.chat.utils import normalize_message_content
from app.config import CHAT_DIR, MAX_UPLOAD_FILES_PER_REQUEST
from app.infra.logging import get_logger
from app.profile.service import get_profile_service

logger = get_logger(__name__)


# -----------------------------------------------------------------------
# 内容安全过滤（原 utils/safety.py 内联）
# -----------------------------------------------------------------------

class SafetyResult(NamedTuple):
    has_violation: bool
    sanitized_text: str

class ContentSafetyFilter:
    def __init__(self):
        self.sensitive_patterns = [
            re.compile(r"色情|赌博|毒品|暴力", re.IGNORECASE)
        ]

    async def check(self, text: str) -> SafetyResult:
        if not text:
            return SafetyResult(has_violation=False, sanitized_text=text)
        sanitized = text
        has_violation = False
        for pattern in self.sensitive_patterns:
            if pattern.search(sanitized):
                has_violation = True
                sanitized = pattern.sub("***", sanitized)
        return SafetyResult(has_violation=has_violation, sanitized_text=sanitized)

safety_filter = ContentSafetyFilter()


# -----------------------------------------------------------------------
# 本地文件存储（原 utils/storage.py 内联）
# -----------------------------------------------------------------------

class LocalFileStore:
    """用户上传文件的本地存储。"""

    def __init__(self) -> None:
        self.upload_dir = CHAT_DIR
        self.allowed_image_ext = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        self.allowed_doc_ext = {".pdf", ".docx", ".txt", ".md", ".log", ".xlsx", ".xls", ".csv", ".tsv"}
        self.max_image_size = 5 * 1024 * 1024
        self.max_doc_size = 10 * 1024 * 1024

    def list_files(self, *, user_id: int, session_id: str) -> list[Path]:
        session_dir = self.upload_dir / str(user_id) / session_id
        if not session_dir.exists():
            return []
        return [path for path in session_dir.iterdir() if path.is_file()]

    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        user_id: int,
        session_id: str,
    ) -> dict:
        suffix = Path(filename).suffix.lower()
        if suffix in self.allowed_image_ext:
            file_type = "image"
            max_size = self.max_image_size
        elif suffix in self.allowed_doc_ext:
            file_type = "document"
            max_size = self.max_doc_size
        else:
            raise ValueError(f"不支持的文件类型: {suffix}")

        if len(content) > max_size:
            raise ValueError(f"文件大小超过限制（{max_size // (1024 * 1024)}MB）")

        session_dir = self.upload_dir / str(user_id) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        safe_name = self._safe_filename(filename)
        if not safe_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = f"{timestamp}{suffix}"

        file_path = session_dir / safe_name
        file_path.write_bytes(content)

        return UploadResponse(
            url=f"/api/v1/ai/chat/uploads/{user_id}/{session_id}/{safe_name}",
            file_type=file_type,
            original_name=filename,
            size_bytes=len(content),
            storage_key=f"{user_id}/{session_id}/{safe_name}",
            mime_type=_guess_mime_type(suffix),
            extension=suffix,
        ).model_dump()

    def _safe_filename(self, filename: str) -> str:
        safe = re.sub(r'[\\/*?:"<>|]', "", filename).strip()
        if len(safe) > 100:
            name, ext = Path(safe).stem, Path(safe).suffix
            safe = f"{name[:100 - len(ext)]}{ext}"
        return safe

    def resolve_user_file(
        self,
        *,
        current_user_id: int,
        owner_id: int,
        session_id: str,
        filename: str,
    ) -> Path:
        if owner_id != current_user_id:
            raise PermissionError("无权访问该文件")

        filename_path = Path(filename)
        if ".." in filename_path.parts:
            raise ValueError("非法文件名")

        if filename_path.parent != Path("."):
            parent_name = filename_path.parent.name
            if parent_name not in {"diagrams"}:
                raise ValueError("非法子目录")
            if filename_path.name != filename_path.parts[-1]:
                raise ValueError("非法文件名")
        else:
            if filename_path.name != filename:
                raise ValueError("非法文件名")

        session_dir = (self.upload_dir / str(owner_id) / session_id).resolve()
        file_path = (session_dir / filename).resolve()
        if not str(file_path).startswith(str(session_dir)):
            raise ValueError("非法文件路径")
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("文件不存在")
        return file_path


def _guess_mime_type(suffix: str) -> str:
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".log": "text/plain",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".csv": "text/csv",
        ".tsv": "text/tab-separated-values",
    }
    return mapping.get(suffix, "application/octet-stream")


class AttachmentAnalysisResult:
    def __init__(self, *, images: list[dict[str, Any]], documents: list[dict[str, Any]]) -> None:
        self.images = images
        self.documents = documents

    @property
    def analysis_context(self) -> str:
        parts: list[str] = []
        for img in self.images:
            if desc := img.get("description", ""):
                parts.append(f"[图片] {desc}")
        for doc in self.documents:
            if summary := doc.get("summary", ""):
                parts.append(f"[文档] {summary}")
        return "\n".join(parts)


class AttachmentInfo:
    def __init__(self, *, url: str, type: str, name: str) -> None:
        self.url = url
        self.type = type
        self.name = name

    def model_dump(self) -> dict[str, Any]:
        return {"url": self.url, "type": self.type, "name": self.name}


class ChatMessageItem:
    def __init__(
        self,
        *,
        id: int,
        role: str,
        content: str,
        attachments: list[AttachmentInfo] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        knowledge_sources: list[dict[str, Any]] | None = None,
        attachment_analyses: list[dict[str, Any]] | None = None,
        teaching_diagram: dict[str, Any] | None = None,
        turn_id: int | None = None,
        message_kind: str | None = None,
        created_at: Any = None,
    ) -> None:
        self.id = id
        self.role = role
        self.content = content
        self.attachments = attachments
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
        self.knowledge_sources = knowledge_sources
        self.attachment_analyses = attachment_analyses
        self.teaching_diagram = teaching_diagram
        self.turn_id = turn_id
        self.message_kind = message_kind
        self.created_at = created_at

    def model_dump(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
        }
        if self.attachments:
            data["attachments"] = [item.model_dump() for item in self.attachments]
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.knowledge_sources:
            data["knowledge_sources"] = self.knowledge_sources
        if self.attachment_analyses:
            data["attachment_analyses"] = self.attachment_analyses
        if self.teaching_diagram:
            data["teaching_diagram"] = self.teaching_diagram
        if self.turn_id is not None:
            data["turn_id"] = self.turn_id
        if self.message_kind:
            data["message_kind"] = self.message_kind
        return data


class ChatUseCases:
    def __init__(self) -> None:
        self._memory_service = get_chat_memory_service()
        self.file_store: LocalFileStore = LocalFileStore()
        self._background_tasks: set[asyncio.Task] = set()
        self._uploaded_file_ids_by_url: dict[str, int] = {}
        self._attachment_analyzer = AttachmentAnalyzer()
        self._orchestrator = TurnOrchestrator(attachments=self._attachment_analyzer)

    def default_session_id(self, user_id: int) -> str:
        return f"user-{user_id}-default-mentor"

    async def list_sessions(self, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        sessions = await self._memory_service.list_sessions(user_id=user_id, limit=limit)
        return [{"id": item.id, "title": item.title, "updated_at": item.updated_at} for item in sessions]

    async def create_session(self, user_id: int, title: str = "新对话") -> dict[str, Any]:
        session = await self._memory_service.create_session(user_id=user_id, title=title)
        return {"id": session.id, "title": session.title}

    async def archive_session(self, user_id: int, session_id: str) -> bool:
        return await self._memory_service.archive_session(user_id=user_id, session_id=session_id)

    async def update_session_title(self, user_id: int, session_id: str, title: str) -> bool:
        return await self._memory_service.update_session_title(user_id=user_id, session_id=session_id, title=title)

    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[ChatMessageItem]:
        if not session_id:
            sessions = await self._memory_service.list_sessions(user_id=user_id, limit=1)
            if not sessions:
                return []
            session_id = sessions[0].id

        raw_messages = await self._memory_service.list_messages(user_id=user_id, session_id=session_id, limit=limit)
        attachment_analyses = await self._memory_service.list_attachment_analyses(
            user_id=user_id,
            session_id=session_id,
            limit=max(limit, 20),
        )
        analyses_by_message_id: dict[int, list[dict[str, Any]]] = {}
        for analysis in attachment_analyses:
            message_id = getattr(analysis, "message_id", None)
            if not message_id:
                continue
            analyses_by_message_id.setdefault(message_id, []).append(
                {
                    "id": getattr(analysis, "id", None),
                    "file_id": getattr(analysis, "file_id", None),
                    "file_name": getattr(analysis, "file_name", None),
                    "file_url": getattr(analysis, "file_url", None),
                    "analysis_type": getattr(analysis, "analysis_type", ""),
                    "summary_text": getattr(analysis, "summary_text", ""),
                    "structured_json": getattr(analysis, "structured_json", None),
                }
            )
        attachment_records_by_message_id = await self._memory_service.list_message_attachments(
            user_id=user_id,
            session_id=session_id,
            message_ids=[item.id for item in raw_messages if getattr(item, "id", None) is not None],
        )
        result: list[ChatMessageItem] = []
        for message in raw_messages:
            parsed_attachments = None
            bound_attachments = attachment_records_by_message_id.get(message.id, []) if isinstance(attachment_records_by_message_id, dict) else []
            if bound_attachments:
                parsed_attachments = [
                    AttachmentInfo(url=item.get("url", ""), type=item.get("type", ""), name=item.get("name", ""))
                    for item in bound_attachments
                ]
            elif message.attachments:
                try:
                    raw = message.attachments if isinstance(message.attachments, list) else json.loads(message.attachments)
                    parsed_attachments = [
                        AttachmentInfo(url=item.get("url", ""), type=item.get("type", ""), name=item.get("name", ""))
                        for item in raw
                    ]
                except Exception:
                    parsed_attachments = None
            result.append(
                ChatMessageItem(
                    id=message.id,
                    role=message.role,
                    content=message.content,
                    attachments=parsed_attachments,
                    tool_calls=message.tool_calls if isinstance(message.tool_calls, list) else None,
                    tool_call_id=getattr(message, "tool_call_id", None),
                    knowledge_sources=message.knowledge_sources if isinstance(message.knowledge_sources, list) else None,
                    attachment_analyses=analyses_by_message_id.get(message.id, []),
                    teaching_diagram=message.teaching_diagram if isinstance(message.teaching_diagram, dict) else None,
                    turn_id=getattr(message, "turn_id", None),
                    message_kind=getattr(message, "message_kind", None),
                    created_at=message.created_at,
                )
            )
        return result

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
    ) -> None:
        await self._memory_service.save_message(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            knowledge_sources=knowledge_sources,
            attachment_analyses=attachment_analyses,
            teaching_diagram=teaching_diagram,
            usage_metadata=usage_metadata,
            turn_id=turn_id,
            message_kind=message_kind,
        )

    async def count_messages(self, user_id: int, session_id: str) -> int:
        return await self._memory_service.count_messages(user_id=user_id, session_id=session_id)

    async def clear_history(self, user_id: int, session_id: str) -> int:
        deleted_count = await self._memory_service.delete_short_term_messages(user_id=user_id, session_id=session_id)
        await self._memory_service.reset_session_counters(user_id=user_id, session_id=session_id)
        return deleted_count

    async def analyze_attachments_parallel(
        self,
        attachments: list[str],
        *,
        user_id: int,
        session_id: str,
    ) -> AttachmentAnalysisResult:
        output = await self._attachment_analyzer.analyze(
            TurnRequest(
                user_id=user_id,
                session_id=session_id,
                message="请分析这些附件",
                attachments=attachments,
                uploaded_file_ids_by_url=dict(self._uploaded_file_ids_by_url),
            )
        )
        images: list[dict[str, Any]] = []
        documents: list[dict[str, Any]] = []
        for item in output.evidence:
            details = item.details if isinstance(item.details, dict) else {}
            if details.get("kind") == "image":
                images.append({"description": item.summary.replace("[图片] ", "", 1), "mode": "", "source_count": len(details.get("urls", []))})
            elif details.get("kind") == "document":
                documents.append({"summary": item.summary.replace("[文档] ", "", 1), "documents": details.get("documents", [])})
        return AttachmentAnalysisResult(images=images, documents=documents)

    async def analyze_uploaded_attachments(
        self,
        *,
        user_id: int,
        question: str,
        session_id: str | None = None,
        files: list[tuple[str, bytes]] | None = None,
        attachments: list[str] | None = None,
    ) -> dict[str, Any]:
        effective_session = session_id or self.default_session_id(user_id)
        all_urls = list(attachments or [])
        for filename, content in files or []:
            if not filename:
                continue
            saved = await self.save_upload(
                filename=filename,
                content=content,
                user_id=user_id,
                session_id=effective_session,
            )
            all_urls.append(saved["url"])
        if not all_urls:
            return {"analysis_context": "", "image_count": 0, "document_count": 0}

        result = await self.analyze_attachments_parallel(all_urls, user_id=user_id, session_id=effective_session)
        return {
            "analysis_context": result.analysis_context,
            "image_count": len(result.images),
            "document_count": len(result.documents),
        }

    async def stream_chat(
        self,
        *,
        user_id: int,
        user_message: str | None = None,
        history: list[ChatHistoryMessage] | None = None,
        session_id: str | None = None,
        attachments: list[str] | None = None,
        need_teaching_diagram: bool = False,
        generate_video: bool = False,
        enable_search: bool | None = None,
        enable_web_search: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        if enable_search is not None:
            enable_web_search = bool(enable_search)
        async for event in self.stream_chat_events(
            user_id=user_id,
            user_message=user_message,
            history=history,
            session_id=session_id,
            attachments=attachments,
            need_teaching_diagram=need_teaching_diagram,
            enable_web_search=enable_web_search,
            persist=True,
        ):
            yield event

    async def stream_chat_events(
        self,
        *,
        user_id: int,
        user_message: str | None = None,
        history: list[ChatHistoryMessage] | None = None,
        session_id: str | None = None,
        attachments: list[str] | None = None,
        need_teaching_diagram: bool = False,
        generate_video: bool = False,
        enable_search: bool | None = None,
        enable_web_search: bool = False,
        persist: bool = True,
    ) -> AsyncIterator[dict[str, Any]]:
        if enable_search is not None:
            enable_web_search = bool(enable_search)
        effective_session = session_id or self.default_session_id(user_id)
        merged_attachments = list(dict.fromkeys(attachments or []))
        normalized_history = list(history or [])
        if not normalized_history and (user_message or "").strip():
            normalized_history = [ChatHistoryMessage(role="user", content=str(user_message).strip())]

        current_message = latest_user_message(normalized_history)
        if not current_message:
            yield {"event": "error", "data": "本轮对话缺少用户消息。"}
            yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
            return

        logger.info(
            "[ChatUseCases] 开始对话: user_id=%s session_id=%s msg_len=%d attachments=%d web_search=%s diagram=%s",
            user_id,
            effective_session,
            len(current_message),
            len(merged_attachments),
            enable_web_search,
            need_teaching_diagram,
        )

        yield {
            "event": "status",
            "data": {
                "stage": "preparing_context",
                "message": "正在分析附件并准备本轮对话..." if merged_attachments else "正在准备本轮对话...",
            },
        }

        turn_id: int | None = None
        if persist:
            user_record = build_user_message_record(current_message, attachments=merged_attachments)
            turn_row = await self._memory_service.create_turn(
                user_id=user_id,
                session_id=effective_session,
                route="default",
                execution_mode="default",
                has_attachments=bool(merged_attachments),
                used_web_search=enable_web_search,
                used_teaching_diagram=need_teaching_diagram,
                status="running",
            )
            turn_id = turn_row.id
            await self._memory_service.append_turn_event(
                user_id=user_id,
                session_id=effective_session,
                turn_id=turn_id,
                event_type="turn.started",
                payload={"status": "running"},
            )
            await self.save_message(
                user_id=user_id,
                session_id=effective_session,
                role="user",
                content=user_record.content,
                attachments=user_record.attachments,
                turn_id=turn_id,
                message_kind="user_input",
            )
            await self._memory_service.append_turn_event(
                user_id=user_id,
                session_id=effective_session,
                turn_id=turn_id,
                event_type="user.message",
                payload={"content": user_record.content},
            )
            recent_messages = await self._memory_service.list_messages(user_id=user_id, session_id=effective_session, limit=1)
            if recent_messages:
                await self._memory_service.bind_message_attachments(
                    user_id=user_id,
                    session_id=effective_session,
                    message_id=recent_messages[-1].id,
                    turn_id=turn_id,
                    attachments=user_record.attachments or [],
                )
            if await self.count_messages(user_id, effective_session) <= 1:
                self._spawn_background(
                    self._memory_service.generate_session_title(
                        user_id=user_id,
                        session_id=effective_session,
                        first_message=current_message,
                    ),
                    label="generate_title",
                )

        if merged_attachments:
            yield {"event": "status", "data": {"stage": "attachment_analysis", "message": "正在分析附件内容..."}}
        if enable_web_search:
            yield {"event": "status", "data": {"stage": "search", "message": "正在检索相关资料..."}}
        yield {"event": "status", "data": {"stage": "answer", "message": "正在组织回答..."}}

        try:
            run_stream = self._orchestrator.astream_run(
                TurnRequest(
                    user_id=user_id,
                    session_id=effective_session,
                    message=current_message,
                    attachments=merged_attachments,
                    attachment_analysis_enabled=bool(merged_attachments),
                    search_enabled=enable_web_search,
                    diagram_enabled=need_teaching_diagram,
                    history=normalized_history,
                    uploaded_file_ids_by_url=dict(self._uploaded_file_ids_by_url),
                )
            )
            result = None
            async for item in run_stream:
                if isinstance(item, str):
                    safety_result = await safety_filter.check(item)
                    safe_chunk = safety_result.sanitized_text if safety_result.has_violation else item
                    if safe_chunk:
                        yield {"event": "token", "data": safe_chunk}
                else:
                    result = item
            
            if result is None:
                raise ValueError("未收到编排器返回的结果")
        except Exception as exc:
            logger.exception("[ChatUseCases] 编排执行失败")
            if persist and turn_id is not None:
                await self._memory_service.append_turn_event(
                    user_id=user_id,
                    session_id=effective_session,
                    turn_id=turn_id,
                    event_type="turn.failed",
                    payload={"error": str(exc)},
                )
                await self._memory_service.update_turn(
                    user_id=user_id,
                    session_id=effective_session,
                    turn_id=turn_id,
                    status="failed",
                    route="default",
                    execution_mode="default",
                    used_web_search=enable_web_search,
                    used_teaching_diagram=need_teaching_diagram,
                    error_message=str(exc),
                )
            yield {"event": "error", "data": f"服务器出错: {exc}"}
            yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
            return

        projection = project_turn_run(result)
        full_answer = str(result.final_answer or "").strip()
        teaching_diagram = result.teaching_diagram if isinstance(result.teaching_diagram, dict) else None

        if full_answer:
            safety_result = await safety_filter.check(full_answer)
            if safety_result.has_violation:
                full_answer = safety_result.sanitized_text
                yield {
                    "event": "status",
                    "data": {"stage": "safety_filter", "message": "内容触发安全策略，已进行部分过滤"},
                }

        if teaching_diagram is not None:
            yield {"event": "diagram", "data": teaching_diagram}

        tool_calls = [
            {
                "id": item["tool_call_id"],
                "name": item["tool_name"],
                "args": item.get("arguments_json") or {},
            }
            for item in projection.tool_invocations
        ]
        transcript_messages = list(projection.transcript_messages)
        knowledge_sources = list(projection.knowledge_sources)
        attachment_analyses = list(result.attachment_analyses)
        usage_metadata = None

        has_assistant_output = bool(full_answer) or teaching_diagram is not None
        if persist and has_assistant_output and turn_id is not None:
            yield {"event": "status", "data": {"stage": "persisting_turn", "message": "正在保存本轮学习记录..."}}
            if attachment_analyses:
                await self._memory_service.append_turn_event(
                    user_id=user_id,
                    session_id=effective_session,
                    turn_id=turn_id,
                    event_type="attachment.analyzed",
                    payload={"count": len(attachment_analyses)},
                )
            if enable_web_search:
                await self._memory_service.append_turn_event(
                    user_id=user_id,
                    session_id=effective_session,
                    turn_id=turn_id,
                    event_type="search.completed",
                    payload={"tool_calls": len(tool_calls)},
                )
            assistant_messages = [item for item in transcript_messages if str(item.get("role") or "") == "assistant"]
            if assistant_messages:
                for index, assistant_message in enumerate(assistant_messages):
                    content = str(assistant_message.get("content") or "")
                    if index == len(assistant_messages) - 1 and full_answer:
                        content = full_answer
                    await self.save_message(
                        user_id=user_id,
                        session_id=effective_session,
                        role="assistant",
                        content=content,
                        tool_calls=assistant_message.get("tool_calls") if isinstance(assistant_message.get("tool_calls"), list) else None,
                        knowledge_sources=knowledge_sources if index == len(assistant_messages) - 1 else None,
                        teaching_diagram=teaching_diagram if index == len(assistant_messages) - 1 else None,
                        usage_metadata=usage_metadata if index == len(assistant_messages) - 1 else None,
                        attachment_analyses=attachment_analyses if index == len(assistant_messages) - 1 else None,
                        turn_id=turn_id,
                        message_kind=str(assistant_message.get("message_kind") or "assistant_answer"),
                    )
            else:
                await self.save_message(
                    user_id=user_id,
                    session_id=effective_session,
                    role="assistant",
                    content=full_answer,
                    tool_calls=tool_calls,
                    knowledge_sources=knowledge_sources,
                    teaching_diagram=teaching_diagram,
                    usage_metadata=usage_metadata,
                    attachment_analyses=attachment_analyses,
                    turn_id=turn_id,
                    message_kind="assistant_answer",
                )
            for tool_message in transcript_messages:
                if str(tool_message.get("role") or "") != "tool":
                    continue
                await self.save_message(
                    user_id=user_id,
                    session_id=effective_session,
                    role="tool",
                    content=str(tool_message.get("content") or ""),
                    tool_call_id=str(tool_message.get("tool_call_id") or ""),
                    turn_id=turn_id,
                    message_kind="tool_result",
                )
            await self._memory_service.save_tool_invocations(
                user_id=user_id,
                session_id=effective_session,
                turn_id=turn_id,
                invocations=projection.tool_invocations,
            )
            await self._memory_service.append_turn_event(
                user_id=user_id,
                session_id=effective_session,
                turn_id=turn_id,
                event_type="answer.completed",
                payload={"answer": full_answer},
            )
            await self._memory_service.append_turn_event(
                user_id=user_id,
                session_id=effective_session,
                turn_id=turn_id,
                event_type="turn.completed",
                payload={"status": "completed"},
            )
            await self._memory_service.finalize_turn_transcript(
                user_id=user_id,
                session_id=effective_session,
                turn_id=turn_id,
                status="completed",
                final_answer=full_answer,
                constraint_report=result.constraint_report.model_dump(),
            )
            await self._memory_service.update_turn(
                user_id=user_id,
                session_id=effective_session,
                turn_id=turn_id,
                status="completed",
                route=result.route,
                execution_mode=result.execution_mode,
                used_web_search=enable_web_search,
                used_teaching_diagram=need_teaching_diagram,
                error_message=None,
            )

        if persist and full_answer:
            self._spawn_background(
                self._memory_service.after_turn(
                    user_id=user_id,
                    session_id=effective_session,
                    user_message=current_message,
                    assistant_reply=full_answer,
                    usage_metadata=usage_metadata,
                ),
                label="memory_pipeline",
            )
            self._spawn_background(
                self._update_learner_profile(user_id=user_id, session_id=effective_session),
                label="profile_update",
            )

        yield {
            "event": "done",
            "data": {
                "session_id": effective_session,
                "full_response": full_answer,
                "knowledge_sources": knowledge_sources,
                "resource": None,
                "teaching_diagram": teaching_diagram,
                "resources": {"teaching_diagram": teaching_diagram, "video": None},
                "tool_calls": tool_calls,
                "transcript_messages": transcript_messages,
                "attachment_analyses": attachment_analyses,
                "usage_metadata": usage_metadata,
            },
        }

    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        user_id: int,
        session_id: str,
    ) -> dict[str, Any]:
        if not filename:
            raise ValueError("文件名不能为空")
        existing = self.file_store.list_files(user_id=user_id, session_id=session_id)
        if len(existing) >= MAX_UPLOAD_FILES_PER_REQUEST:
            raise ValueError(f"单次上传最多 {MAX_UPLOAD_FILES_PER_REQUEST} 个文件")
        payload = await self.file_store.save_upload(
            filename=filename,
            content=content,
            user_id=user_id,
            session_id=session_id,
        )
        file_record = await self._memory_service.save_uploaded_file(user_id=user_id, session_id=session_id, payload=payload)
        self._uploaded_file_ids_by_url[str(payload.get("url") or "")] = file_record.id
        return payload

    def resolve_uploaded_file(
        self,
        *,
        current_user_id: int,
        owner_id: int,
        session_id: str,
        filename: str,
    ) -> Path:
        if current_user_id != owner_id:
            raise PermissionError("无权访问此文件")
        return self.file_store.resolve_user_file(
            current_user_id=current_user_id,
            owner_id=owner_id,
            session_id=session_id,
            filename=filename,
        )

    async def _update_learner_profile(self, *, user_id: int, session_id: str) -> None:
        await get_profile_service().maybe_update_from_tutoring_turn(user_id=user_id, session_id=session_id)

    def _spawn_background(self, coro, *, label: str = "") -> None:
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
            task = asyncio.ensure_future(_run())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        else:
            logger.warning("[ChatUseCases] 无法在非事件循环中启动后台任务 label=%s", label)


_chat_usecases: ChatUseCases | None = None
_avatar_chat_usecases: ChatUseCases | None = None


def get_chat_usecases() -> ChatUseCases:
    global _chat_usecases
    if _chat_usecases is None:
        _chat_usecases = ChatUseCases()
    return _chat_usecases


def get_chat_memory_service():
    return _get_chat_memory_service()


def get_avatar_chat_usecases() -> ChatUseCases:
    global _avatar_chat_usecases
    if _avatar_chat_usecases is None:
        _avatar_chat_usecases = ChatUseCases()
    return _avatar_chat_usecases
