"""用户上传文件的本地存储。"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.chat.schemas import UploadResponse
from app.config import user_chat_uploads_dir, chat_upload_url
from app.infra.logging import get_logger

logger = get_logger(__name__)


# LocalFileStore：用户上传文件的本地磁盘存储（按用户/会话分目录）
class LocalFileStore:
    """用户上传文件的本地存储。

    目录结构: static/{username}/chat/{session_id}/uploads/{filename}
    每个用户每个会话独立一个文件夹，避免文件名冲突。
    """

    # 初始化允许的文件扩展名与大小上限
    def __init__(self) -> None:
        self.allowed_image_ext = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        self.allowed_doc_ext = {".pdf", ".docx", ".txt", ".md", ".log", ".xlsx", ".xls", ".csv", ".tsv"}
        self.max_image_size = 5 * 1024 * 1024
        self.max_doc_size = 10 * 1024 * 1024

    # 列出某会话上传目录下的全部文件
    def list_files(self, *, username: str, session_id: str) -> list[Path]:
        uploads_dir = user_chat_uploads_dir(username, session_id)
        if not uploads_dir.exists():
            return []
        return [path for path in uploads_dir.iterdir() if path.is_file()]

    # 保存上传文件：校验类型/大小 → 防重名 → 写盘 → 返回附件快照
    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        username: str,
        session_id: str,
    ) -> dict:
        # 按扩展名区分图片/文档类型及大小上限
        suffix = Path(filename).suffix.lower()
        if suffix in self.allowed_image_ext:
            file_type, max_size = "image", self.max_image_size
        elif suffix in self.allowed_doc_ext:
            file_type, max_size = "document", self.max_doc_size
        else:
            raise ValueError(f"不支持的文件类型: {suffix}")

        # 校验文件大小
        if len(content) > max_size:
            raise ValueError(f"文件大小超过限制（{max_size // (1024 * 1024)}MB）")

        # 创建上传目录
        uploads_dir = user_chat_uploads_dir(username, session_id)
        uploads_dir.mkdir(parents=True, exist_ok=True)

        # 生成安全文件名，必要时加时间戳
        safe_name = self._safe_filename(filename)
        if not safe_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = f"{timestamp}{suffix}"

        # 文件名冲突则追加随机后缀
        file_path = uploads_dir / safe_name
        if file_path.exists():
            file_path = uploads_dir / f"{file_path.stem}-{uuid4().hex[:8]}{file_path.suffix}"
            safe_name = file_path.name
        # 写入文件内容
        file_path.write_bytes(content)

        # 返回标准上传响应
        return UploadResponse(
            url=chat_upload_url(username, session_id, safe_name),
            file_type=file_type,
            original_name=filename,
            size_bytes=len(content),
            mime_type=_guess_mime_type(suffix),
        ).model_dump()

    # 清洗文件名：去除非法字符并截断长度
    def _safe_filename(self, filename: str) -> str:
        safe = re.sub(r'[\\/*?:"<>|]', "", filename).strip()
        if len(safe) > 100:
            name, ext = Path(safe).stem, Path(safe).suffix
            safe = f"{name[:100 - len(ext)]}{ext}"
        return safe

    # 解析并校验用户文件路径（防越权与目录穿越）
    def resolve_user_file(
        self,
        *,
        current_username: str,
        owner_username: str,
        session_id: str,
        filename: str,
    ) -> Path:
        # 仅文件所有者可访问
        if owner_username != current_username:
            raise PermissionError("无权访问该文件")

        # 路径穿越防护：禁止 .. 及非法子目录
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

        # 最终校验解析后的路径仍在上传目录内且文件存在
        uploads_dir = user_chat_uploads_dir(owner_username, session_id).resolve()
        file_path = (uploads_dir / filename).resolve()
        if not str(file_path).startswith(str(uploads_dir)):
            raise ValueError("非法文件路径")
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("文件不存在")
        return file_path


# 根据扩展名推断 MIME 类型，未知类型回退为二进制流
def _guess_mime_type(suffix: str) -> str:
    mapping = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain", ".md": "text/markdown", ".log": "text/plain",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel", ".csv": "text/csv",
        ".tsv": "text/tab-separated-values",
    }
    return mapping.get(suffix, "application/octet-stream")
