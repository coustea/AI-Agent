"""文件服务：上传路径解析、文件内容读取、文档分析。

供 chat、avatar 等需要处理用户上传文件的模块共享。

安全策略：
  resolve_uploaded_path — 校验路径不包含 ..，resolve() 后必须以 user_dir 为前缀
  read_uploaded_file_content — 按 max_content_chars 截断，防止超大文件撑爆内存
  pymupdf / python-docx 采用延迟导入(lazy import)，因为它们是可选重依赖
"""

from __future__ import annotations

from pathlib import Path

from app.infra.logging import get_logger
from app.config import WORKPLACE_DIR

logger = get_logger(__name__)

# 单个文件最大读取字符数，防止超大文件撑爆 LLM 上下文窗口
MAX_FILE_CONTENT_CHARS = 15000


# 将上传文件 URL 解析为 (username, absolute_path)，并校验路径安全与存在性
def resolve_uploaded_path(file_url: str) -> tuple[str, str] | None:
    """将 URL 路径解析为 (username, absolute_path)，校验路径安全性和文件存在性。

    新 URL 格式: /static/{username}/chat/{session_id}/uploads/{filename}

    安全策略：
    1. 路径遍历攻击防护：resolve() 后必须以 user_dir 为前缀
    2. 目录穿越防护：session_id 和 filename 不能包含路径分隔符
    3. 所有路径操作使用 resolve() 解析符号链接

    Args:
        file_url: 上传文件的 URL 路径。

    Returns:
        元组 (username, absolute_path)，无效路径返回 None。
    """
    # 支持 /static/{username}/chat/{session_id}/uploads/{filename} 格式
    if file_url.startswith("/static/"):
        relative = file_url.removeprefix("/static/")
        parts = [p for p in relative.split("/") if p]
        # 期望格式: {username}/chat/{session_id}/uploads/{filename}
        # 或: {username}/chat/{session_id}/diagrams/{filename}
        if len(parts) >= 5 and parts[1] == "chat":
            username = parts[0]
            session_id = parts[2]
            subdir = parts[3]  # uploads 或 diagrams
            filename = "/".join(parts[4:])  # 支持子目录中的文件

            # 安全校验：session_id 和 filename 不能包含路径分隔符（防目录穿越）
            if session_id and Path(session_id).name != session_id:
                return None
            if subdir not in {"uploads", "diagrams"}:
                return None

            # 构建路径
            user_dir = (WORKPLACE_DIR / username).resolve()
            file_path = (user_dir / "chat" / session_id / subdir / filename).resolve()

            # 解析后路径必须落在用户目录内且文件存在
            if not str(file_path).startswith(str(user_dir)):
                return None
            if not file_path.exists():
                return None
            return username, str(file_path)

        # 兼容旧格式: {username}/chat/{session_id}/{filename} (无 uploads 层级)
        if len(parts) == 4 and parts[1] == "chat":
            username = parts[0]
            session_id = parts[2]
            filename = parts[3]

            if session_id and Path(session_id).name != session_id:
                return None
            if Path(filename).name != filename:
                return None

            user_dir = (WORKPLACE_DIR / username).resolve()
            file_path = (user_dir / "chat" / session_id / "uploads" / filename).resolve()

            if not str(file_path).startswith(str(user_dir)):
                return None
            if not file_path.exists():
                return None
            return username, str(file_path)

    # 兜底：支持直接传入本地绝对路径
    try:
        local_path = Path(file_url).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return None

    if not local_path.exists():
        return None

    # 尝试从路径中提取 username
    try:
        relative_parts = local_path.relative_to(WORKPLACE_DIR).parts
        if len(relative_parts) >= 3 and relative_parts[1] == "chat":
            username = relative_parts[0]
            return username, str(local_path)
    except ValueError:
        pass

    return None


# 解析图片 URL 为本地 Path（不存在或非文件返回 None）
def resolve_uploaded_image_path(image_url: str) -> Path | None:
    """解析图片 URL 为本地 Path。

    Args:
        image_url: 图片 URL 路径。

    Returns:
        本地 Path，无效路径返回 None。
    """
    resolved = resolve_uploaded_path(image_url)
    if resolved is None:
        return None
    _, absolute_path = resolved
    path = Path(absolute_path)
    return path if path.is_file() else None


# 读取上传文件内容并截断，支持多种文档格式（依赖延迟导入）
def read_uploaded_file_content(
    absolute_path: str,
    *,
    max_content_chars: int = MAX_FILE_CONTENT_CHARS,
    max_pdf_pages: int | None = None,
    max_docx_paragraphs: int | None = None,
) -> str:
    """读取上传文件内容，支持 .pdf / .docx / .txt / .md / .log。

    Args:
        absolute_path: 文件绝对路径。

    Returns:
        文件内容字符串，失败时返回错误提示信息。
    """
    path = Path(absolute_path)
    # 基本的文件存在性校验
    if not path.exists():
        return f"文件不存在: {absolute_path}"
    if not path.is_file():
        return f"路径不是文件: {absolute_path}"

    # 根据文件扩展名选择不同的解析策略
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        # 延迟导入 pymupdf — 仅在实际处理 PDF 时才加载，减少启动开销
        from pymupdf import open as pdf_open

        text_parts = []
        with pdf_open(str(path)) as doc:
            # 可选限制页数，避免超长 PDF 占用过多 token
            pages = doc if max_pdf_pages is None else list(doc)[:max_pdf_pages]
            for page in pages:
                text_parts.append(page.get_text())
        content = "\n".join(text_parts)
    elif suffix == ".docx":
        # 延迟导入 python-docx — 仅在处理 Word 文档时加载
        from docx import Document

        doc = Document(str(path))
        # 可选限制段落数，防止超大文档撑爆内存
        paragraphs = doc.paragraphs if max_docx_paragraphs is None else doc.paragraphs[:max_docx_paragraphs]
        # 过滤空段落，只保留有实际内容的文本
        content = "\n".join(para.text for para in paragraphs if para.text.strip())
    elif suffix in {".txt", ".md", ".log"}:
        # 纯文本文件直接读取，errors="replace" 防止编码异常中断
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    elif suffix in {".xlsx", ".xls"}:
        import pandas as pd

        df = pd.read_excel(str(path), dtype=str, nrows=500)
        content = df.to_string(index=False)
    elif suffix in {".csv", ".tsv"}:
        import pandas as pd

        sep = "\t" if suffix == ".tsv" else ","
        df = pd.read_csv(str(path), sep=sep, dtype=str, nrows=500)
        content = df.to_string(index=False)
    else:
        return f"不支持的文件类型: {suffix}（支持: .pdf, .docx, .txt, .md, .log, .xlsx, .xls, .csv, .tsv）"

    # 空内容处理与超长截断
    if not content or not content.strip():
        return "文件内容为空"
    # 截断超长内容，防止撑爆 LLM 上下文窗口
    if len(content) > max_content_chars:
        content = content[:max_content_chars] + "\n\n[...文档内容过长，已截断...]"
    return content


# 批量读取文档并拼装为可注入 LLM 的分析提示词
async def analyze_documents(
    *,
    current_username: str,
    file_urls: list[str],
    question: str,
    max_total_chars: int = 40000,
    max_file_content_chars: int = MAX_FILE_CONTENT_CHARS,
    max_pdf_pages: int | None = None,
    max_docx_paragraphs: int | None = None,
) -> dict:
    """批量读取用户上传的文档内容，返回可直接注入 LLM 上下文的分析提示词。

    流程：URL 解析 → 权限校验 → 内容读取 → 截断 → 拼接为分析上下文。

    Args:
        current_username: 当前用户名（用于权限校验）。
        file_urls: 文件 URL 列表。
        question: 用户问题（用于构建分析提示词）。

    Returns:
        分析结果字典，包含 success、documents、analysis_text、error 字段。
    """
    # 存储所有成功读取的文档元数据和内容
    documents: list[dict[str, str]] = []
    # 存储每个文档的内容片段，用于后续拼接为分析提示词
    snippets: list[str] = []

    for file_url in file_urls:
        # 将 URL 解析为 (username, absolute_path)，失败则跳过
        resolved = resolve_uploaded_path(file_url)
        if resolved is None:
            logger.warning("[DocumentAnalysis] 解析路径失败: %s", file_url)
            continue

        owner_username, absolute_path = resolved
        # 安全校验：确保当前用户只能访问自己的文件
        if owner_username != current_username:
            logger.warning(
                "[DocumentAnalysis] 禁止访问文件: user=%s owner=%s",
                current_username, owner_username,
            )
            continue

        # 读取文件内容，支持 PDF/DOCX/TXT/MD/LOG
        content = read_uploaded_file_content(
            absolute_path,
            max_content_chars=max_file_content_chars,
            max_pdf_pages=max_pdf_pages,
            max_docx_paragraphs=max_docx_paragraphs,
        )
        documents.append({
            "url": file_url,
            "name": Path(absolute_path).name,
            "absolute_path": absolute_path,
            "content": content,
        })
        # 构建单个文件的内容片段，用于拼接为完整的分析上下文
        snippets.append(f"文件《{Path(absolute_path).name}》内容如下：\n{content}")

    # 无可读文档时返回失败
    if not documents:
        return {
            "success": False,
            "documents": [],
            "analysis_text": "未能读取可分析的文档内容。",
            "error": "未找到可访问的文档。",
        }

    # 将所有文档内容拼接为一个字符串
    joined_snippets = "\n\n".join(snippets)
    # 全局截断：防止多个文档总内容超出 LLM 上下文限制
    if len(joined_snippets) > max_total_chars:
        joined_snippets = joined_snippets[:max_total_chars] + "\n\n[...文档总内容过长，已截断...]"

    # 构建最终的分析提示词，引导 LLM 基于文档内容回答问题并提炼知识点
    analysis_text = (
        f"用户问题：{question or '请分析这些文档'}\n\n"
        "以下是已提取的文档内容，请基于它们回答用户问题，并在回答中尽量提炼知识点：\n\n"
        + joined_snippets
    )
    return {
        "success": True,
        "documents": documents,
        "analysis_text": analysis_text,
        "error": None,
    }
