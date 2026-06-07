"""本地文件系统存储适配器。"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from app.chat.response import UploadResponse
from app.config import CHAT_DIR


class LocalFileStore:
    """用户上传文件的本地存储。"""

    def __init__(self) -> None:
        self.upload_dir = CHAT_DIR
        self.allowed_image_ext = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        self.allowed_doc_ext = {".pdf", ".docx", ".txt", ".md", ".log", ".xlsx", ".xls", ".csv", ".tsv"}
        self.max_image_size = 5 * 1024 * 1024
        self.max_doc_size = 10 * 1024 * 1024

    def list_files(self, *, user_id: int, session_id: str) -> list[Path]:
        """列出用户某次会话中已上传的文件。"""
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

        # 保留原始文件名（清理非法字符），如果为空则用时间戳命名
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
        ).model_dump()

    def _safe_filename(self, filename: str) -> str:
        """清理文件名中的非法字符，保留原始名称。"""
        # 移除路径分隔符和其他非法字符
        safe = re.sub(r'[\\/*?:"<>|]', "", filename).strip()
        # 限制长度
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

        # 支持 diagrams 子目录：filename 可以是 "diagrams/xxx.png" 格式
        # 验证路径不包含目录遍历
        filename_path = Path(filename)
        if ".." in filename_path.parts:
            raise ValueError("非法文件名")

        # 对于 diagrams 子目录，允许子路径
        if filename_path.parent != Path("."):
            # 子目录情况（如 diagrams/xxx.png）
            # 验证父目录名是合法的
            parent_name = filename_path.parent.name
            if parent_name not in {"diagrams"}:
                raise ValueError("非法子目录")
            # 验证文件名本身不包含路径分隔符
            if filename_path.name != filename_path.parts[-1]:
                raise ValueError("非法文件名")
        else:
            # 普通文件，验证文件名不包含路径分隔符
            if filename_path.name != filename:
                raise ValueError("非法文件名")

        session_dir = (self.upload_dir / str(owner_id) / session_id).resolve()
        file_path = (session_dir / filename).resolve()
        if not str(file_path).startswith(str(session_dir)):
            raise ValueError("非法文件路径")
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("文件不存在")
        return file_path
