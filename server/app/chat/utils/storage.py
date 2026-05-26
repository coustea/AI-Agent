"""Local filesystem storage adapter."""

from __future__ import annotations

import random
import re
import string
from datetime import datetime
from pathlib import Path

from app.chat.schemas import UploadResponse
from app.infra.paths import CHAT_DIR


class LocalFileStore:
    """Local file storage for user uploads."""

    def __init__(self) -> None:
        self.upload_dir = CHAT_DIR
        self.allowed_image_ext = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        self.allowed_doc_ext = {".pdf", ".docx", ".txt", ".md", ".log", ".xlsx", ".xls", ".csv", ".tsv"}
        self.max_image_size = 5 * 1024 * 1024
        self.max_doc_size = 10 * 1024 * 1024

    def ensure_roots(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)

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

    async def save_diagram_image(
        self,
        *,
        filename: str,
        content: bytes,
        user_id: int,
        session_id: str,
    ) -> dict:
        """保存图解 PNG 图片到 diagrams 子目录。

        Args:
            filename: 原始文件名。
            content: PNG 文件内容。
            user_id: 用户ID。
            session_id: 会话ID。

        Returns:
            保存结果，包含 url、file_type 等字段。

        Raises:
            ValueError: 文件类型不支持或大小超限。
        """
        # 验证文件类型
        suffix = Path(filename).suffix.lower()
        if suffix != ".png":
            raise ValueError("图解仅支持 PNG 格式")

        if len(content) > self.max_image_size:
            raise ValueError(f"文件大小超过限制（{self.max_image_size // (1024 * 1024)}MB）")

        # 保存到 diagrams 子目录
        diagram_dir = self.upload_dir / str(user_id) / session_id / "diagrams"
        diagram_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名：diagram_{timestamp}_{random}.png
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        safe_name = f"diagram_{timestamp}_{random_suffix}.png"

        file_path = diagram_dir / safe_name
        file_path.write_bytes(content)

        return UploadResponse(
            url=f"/api/v1/ai/chat/uploads/{user_id}/{session_id}/diagrams/{safe_name}",
            file_type="image",
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


local_file_store = LocalFileStore()
