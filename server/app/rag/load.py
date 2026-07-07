"""统一文档加载器 — 手动遍历目录，按文件类型加载为 LangChain Document。

传入一个目录路径，遍历所有支持的文件，返回 Document 列表。
支持格式：.md/.txt 等纯文本（直接 UTF-8 读取）、.pdf（PyMuPDFLoader），可扩展。

公共接口：
  load_directory()        加载目录下所有文档
  SUPPORTED_EXTENSIONS   支持的文件扩展名集合

设计说明：纯文本不依赖 LangChain TextLoader——它的 __init__ 参数（如 errors）
随版本漂移，曾导致整库加载失败（0 文档）。直接用 pathlib.read_text(errors="replace")
既稳定又能容忍个别坏字节，PDF 才需要 PyMuPDFLoader 的版面/分页解析。

Called by: app/rag/indexing/build.py
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader

from app.infra.logging import get_logger

logger = get_logger(__name__)

# 支持的文件扩展名（.md/.txt 纯文本 + .pdf 版面解析）
SUPPORTED_EXTENSIONS: set[str] = {".md", ".txt", ".pdf"}

# 默认排除的文件名。README/SUMMARY/INDEX 在净化后的 source/ 里是课程正文，
# 不再作为元信息排除——噪声已由 curate_source.py 物理删除，loader 不再靠
# 脆弱的文件名黑名单猜测内容。仅保留真正的仓库元文件。
_EXCLUDE_NAMES: set[str] = {
    "CONTRIBUTING.md",
    "LICENSE.md",
    "CHANGELOG.md",
}

# 默认排除的目录名（防御性：即便 curate 漏删，这些子树也不入库）
_EXCLUDE_DIRS: frozenset[str] = frozenset({
    ".git", ".github",
    "node_modules", "__pycache__",
    ".idea", ".vscode",
    "assets", "images", "imgs", "figures", "figs",
    "scripts", "styles", "templates",
})


def _load_file(path: Path) -> list[Document]:
    """加载单个文件为 Document 列表。

    按扩展名分派：
      - .pdf  → PyMuPDFLoader（需要版面/分页解析）
      - 其他（.md/.txt 等纯文本）→ pathlib.read_text(encoding="utf-8", errors="replace")

    纯文本不走 TextLoader：其构造参数随 langchain 版本漂移（如不支持 errors=），
    曾造成整库加载失败。errors="replace" 保证个别坏字节不会丢掉整篇文档。

    Args:
        path: 文件路径。

    Returns:
        Document 列表（纯文本恒为 0 或 1 条；PDF 可能多条，每页一条）。
    """
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PyMuPDFLoader(str(path)).load()

    text = path.read_text(encoding="utf-8", errors="replace")
    if not text or not text.strip():
        return []
    return [Document(page_content=text, metadata={"source": str(path)})]


def _should_skip(source: str) -> bool:
    """判断文件是否应跳过（基于相对路径）。"""
    parts = Path(source).parts

    # 跳过排除目录下的文件
    for part in parts:
        if part in _EXCLUDE_DIRS:
            return True

    # 跳过排除文件名
    filename = Path(source).name
    if filename in _EXCLUDE_NAMES:
        return True

    # 跳过隐藏文件
    if filename.startswith("."):
        return True

    return False


def load_directory(
    source_dir: Path,
    *,
    extensions: set[str] | None = None,
) -> list[Document]:
    """加载目录下所有支持的文档。

    手动遍历文件，避免 DirectoryLoader 对 loader_kwargs 的隐式行为影响中文文件读取。
    """
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

    exts = extensions or SUPPORTED_EXTENSIONS
    all_docs: list[Document] = []

    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        if suffix not in exts:
            continue

        try:
            rel_path = path.relative_to(source_dir).as_posix()
        except ValueError:
            rel_path = path.name

        if _should_skip(rel_path):
            continue

        try:
            docs = _load_file(path)
        except Exception as exc:
            logger.warning("[load] failed to load %s: %s", rel_path, exc)
            continue

        for doc in docs:
            if not doc.page_content or not doc.page_content.strip():
                continue

            # 保留 PDF loader 产生的 page 等元数据，同时统一 source/file_type
            doc.metadata["source"] = rel_path
            doc.metadata["file_type"] = suffix
            all_docs.append(doc)

    logger.info("[load] loaded %d documents from %s", len(all_docs), source_dir)
    return all_docs
