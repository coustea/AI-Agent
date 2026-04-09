import os
from pathlib import Path
from langchain.tools import tool


def _read_text(path: Path) -> str:
    """读取纯文本文件。"""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _read_pdf(path: Path) -> str:
    """读取 PDF 文件，提取文本内容。"""
    from pymupdf import open as pdf_open

    text_parts = []
    with pdf_open(str(path)) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def _read_docx(path: Path) -> str:
    """读取 Word 文档，提取段落文本。"""
    from docx import Document

    doc = Document(str(path))
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())

# 允许访问的根目录
BASE_DIR = str(Path(__file__).resolve().parents[4])  # server/ 目录

# 允许读取的文件类型
ALLOWED_EXTENSIONS = {
    ".docx", ".pdf", ".html", ".md", ".log"
}

# ⏱ 最大读取大小（1MB）
MAX_FILE_SIZE = 1 * 1024 * 1024


def is_safe_path(file_path: Path):
    """检查路径是否合法（防止越权访问）"""
    try:
        file_path = file_path.resolve()
        return str(file_path).startswith(str(BASE_DIR))
    except Exception:
        return False


@tool("read_file", description="安全读取文件内容，仅允许访问指定目录下的文本文件")
def read_file_safe(file_path: str) -> str:
    """
    安全读取文件内容
    """

    try:
        path = Path(file_path)

        # 1️⃣ 转绝对路径
        if not path.is_absolute():
            path = BASE_DIR / path

        path = path.resolve()

        # 2️⃣ 路径安全检查
        if not is_safe_path(path):
            return " 拒绝访问：越权路径"

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
            content = _read_pdf(path)
        elif suffix == ".docx":
            content = _read_docx(path)
        else:
            content = _read_text(path)

        return content if content else "⚠️ 文件为空"

    except Exception as e:
        return f"❌ 读取失败: {str(e)}"