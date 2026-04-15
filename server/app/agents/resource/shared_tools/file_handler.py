"""
共享文件处理工具模块。

提供跨 Agent 使用的通用文件处理函数和类，包括：
- FileHandler: 类版本，保留备用
- save_to_workplace: @tool 装饰器版本，保存文件到 workplace
- read_file_safe: @tool 装饰器版本，安全读取文件内容
"""

import os
import re
import time
from pathlib import Path
from typing import Literal

from langchain.tools import tool

from app.utils.paths import SERVER_DIR, WORKPLACE_DIR

# 允许访问的根目录
BASE_DIR = str(SERVER_DIR)

# 允许读取的文件类型
ALLOWED_EXTENSIONS = {
    ".docx", ".pdf", ".html", ".md", ".log"
}

# 最大读取大小（1MB）
MAX_FILE_SIZE = 1 * 1024 * 1024


# ──────────────────────────────────────────────────────────────
# FileHandler 类（保留备用）
# ──────────────────────────────────────────────────────────────

class FileHandler:
    """文件处理工具类，提供文件读写的基本功能。"""

    @staticmethod
    def _read_text(path: Path) -> str:
        """读取纯文本文件。"""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    @staticmethod
    def _read_pdf(path: Path) -> str:
        """读取 PDF 文件，提取文本内容。"""
        from pymupdf import open as pdf_open

        text_parts = []
        with pdf_open(str(path)) as doc:
            for page in doc:
                text_parts.append(page.get_text())
        return "\n".join(text_parts)

    @staticmethod
    def _read_docx(path: Path) -> str:
        """读取 Word 文档，提取段落文本。"""
        from docx import Document

        doc = Document(str(path))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())

    @staticmethod
    def is_safe_path(file_path: Path) -> bool:
        """检查路径是否合法（防止越权访问）"""
        if not file_path:
            return False
        try:
            resolved_path = file_path.resolve()
            return str(resolved_path).startswith(str(BASE_DIR))
        except (OSError, ValueError, RuntimeError):
            # 处理路径解析异常（如无效字符、权限问题等）
            return False

    @staticmethod
    def save_to_workplace(sub_dir: str, topic: str, content: str, ext: str = "md") -> str:
        """
        将内容保存到 workplace 下的指定子目录，文件名按主题+时间戳生成。

        Args:
            sub_dir: workplace 下的子目录名（如 "content", "code" 等）
            topic: 文件主题（用于文件名）
            content: 要写入的文件内容
            ext: 文件扩展名（不含点，默认为 "md"）

        Returns:
            保存的绝对文件路径
        """
        target_dir = WORKPLACE_DIR / sub_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # 净化 topic 名称，去除非法字符并限制长度
        safe_topic = re.sub(r'[\\/*?:"<>|]', "", topic).strip()[:50]
        if not safe_topic:
            safe_topic = "untitled"

        filename = f"{safe_topic}_{int(time.time())}.{ext}"
        filepath = target_dir / filename

        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    @staticmethod
    def read_file_safe(file_path: str) -> str:
        """
        安全读取文件内容。

        Args:
            file_path: 文件路径

        Returns:
            文件内容或错误消息
        """
        try:
            path = Path(file_path)

            # 1️⃣ 转绝对路径
            if not path.is_absolute():
                path = BASE_DIR / path

            path = path.resolve()

            # 2️⃣ 路径安全检查
            if not FileHandler.is_safe_path(path):
                return "❌ 拒绝访问：越权路径"

            # 3️⃣ 文件是否存在
            if not path.exists():
                return "❌ 文件不存在"

            if not path.is_file():
                return "❌ 不是文件"

            # 4️⃣ 后缀检查
            if path.suffix not in ALLOWED_EXTENSIONS:
                return f"❌ 不允许的文件类型: {path.suffix}"

            # 5️⃣ 文件大小限制
            size = os.path.getsize(path)
            if size > MAX_FILE_SIZE:
                return f"❌ 文件过大: {size} bytes"

            # 6️⃣ 按类型读取文件
            suffix = path.suffix.lower()
            if suffix == ".pdf":
                content = FileHandler._read_pdf(path)
            elif suffix == ".docx":
                content = FileHandler._read_docx(path)
            else:
                content = FileHandler._read_text(path)

            return content if content else "⚠️ 文件为空"

        except Exception as e:
            return f"❌ 读取失败: {str(e)}"


# ──────────────────────────────────────────────────────────────
# @tool 装饰器版本（推荐使用）
# ──────────────────────────────────────────────────────────────

@tool("save_to_workplace")
def save_to_workplace(
    sub_dir: Literal["mindmap", "content", "code", "quiz", "reading", "image", "video", "ppt"],
    topic: str,
    content: str,
    ext: str = "md"
) -> str:
    """将内容保存到 workplace 下的指定子目录，文件名按主题+时间戳生成。

    Args:
        sub_dir: workplace 下的子目录名（如 "mindmap", "content" 等）
        topic: 文件主题（用于文件名）
        content: 要写入的文件内容
        ext: 文件扩展名（不含点，默认为 "md"）

    Returns:
        保存的绝对文件路径
    """
    return FileHandler.save_to_workplace(sub_dir, topic, content, ext)


@tool("read_file_safe")
def read_file_safe(file_path: str) -> str:
    """安全读取文件内容，仅允许访问指定目录下的文本文件。

    Args:
        file_path: 文件路径（绝对或相对路径）

    Returns:
        文件内容或错误消息
    """
    return FileHandler.read_file_safe(file_path)
