"""离线知识库索引构建器。

唯一入口：python -m app.rag.indexing.build

安全构建流程：
  1. 检查源目录与文档
  2. 构建到临时目录 *.building-<uuid>
  3. 校验 collection count
  4. 写 manifest.json
  5. 重新打开验证
  6. 全部成功后原子替换正式目录
  7. 任一步失败删除临时目录，正式目录不变
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb

from app.config import (
    KB_DIR,
    KB_EMBED_MODEL,
    SERVER_DIR,
)
from app.infra.logging import get_logger
from app.rag.embeddings import embed_documents
from app.rag.bm25 import BM25Index  # called by _build_temp_index for BM25 index creation
from app.rag.models import CHROMA_COLLECTION

logger = get_logger(__name__)

SCHEMA_VERSION = "1"
_MANIFEST_FILENAME = "manifest.json"

# 切分参数
_CHUNK_MAX_SIZE = 800
_CHUNK_MIN_SIZE = 100
_CHUNK_OVERLAP = 100

# 知识库源文档定位（锚定 server/，glob 固定为清洗后的最终 md）
_SOURCE_DIR = SERVER_DIR / "app/rag/data/book"
_SOURCE_GLOB = "**/*.final.md"


# ============ 切分器 ============


def _split_markdown(text: str) -> list[tuple[str, str]]:
    """将 Markdown 文本按标题结构切分为块，保留标题层级路径。

    Returns:
        列表，每项为 (chunk_text, heading_path) 元组。
    """
    if not text or not text.strip():
        return []

    from langchain_text_splitters import MarkdownHeaderTextSplitter

    # 第一阶段：保护代码块
    code_blocks: list[str] = []
    placeholder_map: dict[str, str] = {}
    idx = 0
    safe_text = text
    while "```" in safe_text:
        start = safe_text.index("```")
        end_pos = safe_text.find("```", start + 3)
        if end_pos == -1:
            break
        code_block = safe_text[start : end_pos + 3]
        placeholder = f"<<CODE_BLOCK_{idx}>>"
        code_blocks.append(code_block)
        placeholder_map[placeholder] = code_block
        safe_text = safe_text[:start] + placeholder + safe_text[end_pos + 3 :]
        idx += 1

    # 第二阶段：Markdown 标题分割
    headers_to_split_on = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ]
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )

    try:
        md_chunks = splitter.split_text(safe_text)
    except Exception:
        # 回退：按段落分割
        md_chunks = []
        for para in safe_text.split("\n\n"):
            if para.strip():
                from langchain_core.documents import Document
                md_chunks.append(Document(page_content=para.strip(), metadata={}))

    # 第三阶段：提取 heading_path 并处理超长块
    results: list[tuple[str, str]] = []
    for chunk in md_chunks:
        content = chunk.page_content
        # 恢复代码块
        for placeholder, code in placeholder_map.items():
            content = content.replace(placeholder, code)

        # 构建 heading_path
        meta = chunk.metadata
        heading_parts = []
        for key in ("h1", "h2", "h3"):
            if key in meta and meta[key]:
                heading_parts.append(meta[key])
        heading_path = " > ".join(heading_parts)

        content = content.strip()
        if not content:
            continue

        # 超长块按句子拆分
        if len(content) > _CHUNK_MAX_SIZE:
            sub_chunks = _split_by_sentences(content)
            for sc in sub_chunks:
                results.append((sc, heading_path))
        else:
            results.append((content, heading_path))

    # 第四阶段：合并过短块
    final: list[tuple[str, str]] = []
    buf_text = ""
    buf_heading = ""
    for chunk_text, heading in results:
        candidate = (buf_text + "\n\n" + chunk_text).strip() if buf_text else chunk_text.strip()
        if len(chunk_text) < _CHUNK_MIN_SIZE and len(candidate) <= _CHUNK_MAX_SIZE * 1.5:
            buf_text = candidate
            buf_heading = heading or buf_heading
        else:
            if buf_text:
                final.append((buf_text, buf_heading))
            buf_text = chunk_text
            buf_heading = heading
    if buf_text.strip():
        final.append((buf_text, buf_heading))

    return [(c, h) for c, h in final if c.strip()]


def _split_by_sentences(text: str) -> list[str]:
    """按中英文句号拆分超长文本。"""
    import re

    sentences = re.split(r"([。！？\.!?]+)", text)
    chunks: list[str] = []
    buf = ""
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else "")
        candidate = (buf + sentence).strip()
        if len(candidate) > _CHUNK_MAX_SIZE and buf:
            chunks.append(buf.strip())
            buf = sentence
        else:
            buf = candidate
    if len(sentences) % 2 == 1 and sentences[-1]:
        buf = (buf + sentences[-1]).strip()
    if buf.strip():
        if len(buf) > _CHUNK_MAX_SIZE:
            for j in range(0, len(buf), _CHUNK_MAX_SIZE):
                chunks.append(buf[j : j + _CHUNK_MAX_SIZE])
        else:
            chunks.append(buf.strip())
    return chunks


def _apply_overlap(chunks: list[tuple[str, str]], overlap: int = _CHUNK_OVERLAP) -> list[tuple[str, str]]:
    """在相邻块间添加滑动窗口重叠。"""
    if overlap <= 0 or len(chunks) <= 1:
        return chunks
    result: list[tuple[str, str]] = []
    for i, (chunk_text, heading) in enumerate(chunks):
        if i > 0:
            prev_text = chunks[i - 1][0]
            tail = prev_text[-overlap:] if len(prev_text) > overlap else prev_text
            chunk_text = tail + "\n" + chunk_text
        result.append((chunk_text, heading))
    return result


# ============ 文档加载 ============


def _load_documents(source_dir: Path, source_glob: str) -> list[dict[str, Any]]:
    """从源目录加载 Markdown 文档。"""
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

    docs: list[dict[str, Any]] = []
    for path in sorted(source_dir.glob(source_glob)):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            if text.strip():
                try:
                    rel_path = path.relative_to(source_dir).as_posix()
                except ValueError:
                    rel_path = path.name
                docs.append({"path": rel_path, "text": text})
    return docs


# ============ Metadata ============


def _stable_chunk_id(source: str, section: str, content: str, heading_path: str = "") -> str:
    """生成稳定的 chunk 哈希 ID。"""
    raw = f"{source}|{section}|{heading_path}|{content}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _infer_title(source: str) -> str:
    """从相对路径推断教材标题。"""
    name = Path(source).name
    for suffix in (".final.md", ".md"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name


def _infer_course(title: str) -> str:
    """从标题推断课程名。"""
    mapping = {
        "计算机网络": "计算机网络",
        "操作系统": "操作系统",
        "数据结构": "数据结构",
        "计算机组成原理": "计算机组成原理",
        "数据库": "数据库",
        "Java": "Java",
        "Python": "Python",
        "Redis": "Redis",
        "算法": "算法",
        "高等数学": "高等数学",
        "线性代数": "线性代数",
        "概率论": "概率论",
    }
    title_lower = title.lower()
    for keyword, course in mapping.items():
        if keyword.lower() in title_lower:
            return course
    return ""


def _extract_section(text: str) -> str:
    """提取第一行标题作为章节信息。"""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") and " " in stripped:
            return stripped.lstrip("# ").strip()
    return ""


# ============ Manifest ============


def _write_manifest(output_dir: Path, collection: str, chunk_count: int, doc_count: int) -> None:
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "collection": collection,
        "embedding_model": KB_EMBED_MODEL,
        "distance_metric": "cosine",
        "document_count": doc_count,
        "chunk_count": chunk_count,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / _MANIFEST_FILENAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_manifest(output_dir: Path) -> dict[str, Any] | None:
    p = output_dir / _MANIFEST_FILENAME
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


# ============ 主构建流程 ============


def _build_temp_index(
    docs: list[dict[str, Any]],
    output_dir: Path,
    collection: str,
    batch_size: int = 32,
) -> tuple[int, int]:
    """构建临时索引，返回 (doc_count, chunk_count)。"""
    client = chromadb.PersistentClient(path=str(output_dir))
    col = client.create_collection(name=collection)

    doc_count = len(docs)
    all_ids: list[str] = []
    all_texts: list[str] = []
    all_metas: list[dict[str, Any]] = []

    for doc_idx, doc in enumerate(docs):
        source = doc["path"]
        text = doc["text"]
        title = _infer_title(source)
        parent_id = hashlib.md5(source.encode("utf-8")).hexdigest()[:16]
        chunks = _split_markdown(text)
        chunks = _apply_overlap(chunks)
        chunks = [(c, h) for c, h in chunks if c.strip()]

        for chunk_idx, (chunk_text, heading_path) in enumerate(chunks):
            section = _extract_section(chunk_text)
            chunk_id = _stable_chunk_id(source, section, chunk_text, heading_path)
            course = _infer_course(title)

            meta: dict[str, Any] = {
                "chunk_id": chunk_id,
                "source": source,
                "title": title,
                "section": section,
                "course": course,
                "chunk_index": chunk_idx,
                "parent_id": parent_id,
                "heading_path": heading_path,
                "schema_version": SCHEMA_VERSION,
            }
            all_ids.append(chunk_id)
            all_texts.append(chunk_text)
            all_metas.append(meta)

    total_chunks = len(all_ids)
    if total_chunks == 0:
        raise ValueError("No chunks produced from source documents")

    for start in range(0, total_chunks, batch_size):
        end = min(start + batch_size, total_chunks)
        batch_texts = all_texts[start:end]
        batch_ids = all_ids[start:end]
        batch_metas = all_metas[start:end]

        embeddings = embed_documents(batch_texts)
        if embeddings is None:
            raise RuntimeError(
                f"Embedding failed at batch starting index {start}. "
                "Cannot build index without embeddings."
            )

        col.add(ids=batch_ids, documents=batch_texts, embeddings=embeddings, metadatas=batch_metas)
        if end < total_chunks:
            time.sleep(0.1)

    # 构建 BM25 索引并持久化
    try:
        bm25 = BM25Index()
        bm25.build(all_texts, all_metas)
        bm25.save(output_dir)
    except Exception as exc:
        logger.warning("[build] BM25 index build failed (non-fatal): %s", exc)

    return doc_count, total_chunks


def _verify_temp_index(output_dir: Path, collection: str, expected_count: int) -> None:
    """重新打开临时索引验证。"""
    client = chromadb.PersistentClient(path=str(output_dir))
    col = client.get_collection(name=collection)
    actual = col.count()
    if actual != expected_count:
        raise RuntimeError(
            f"Verification failed: expected {expected_count} chunks, found {actual}"
        )


def _swap_index(temp_dir: Path, final_dir: Path) -> None:
    """原子替换正式索引目录。"""
    backup_dir = final_dir.parent / f"{final_dir.name}.backup-{uuid.uuid4().hex[:8]}"
    if final_dir.exists():
        final_dir.rename(backup_dir)
    temp_dir.rename(final_dir)

    try:
        client = chromadb.PersistentClient(path=str(final_dir))
        col = client.get_collection(name=CHROMA_COLLECTION)
        logger.info("[build] index swapped and verified: %d chunks", col.count())
    except Exception as exc:
        logger.error("[build] verification of swapped index failed: %s", exc)
        if final_dir.exists():
            shutil.rmtree(final_dir)
        backup_dir.rename(final_dir)
        logger.info("[build] restored backup index")
        raise


def build_index(
    source_dir: Path | None = None,
    source_glob: str | None = None,
    output_dir: Path | None = None,
    collection: str | None = None,
    batch_size: int = 32,
) -> None:
    """执行完整的安全构建流程。"""
    src_dir = source_dir or _SOURCE_DIR
    src_glob = source_glob or _SOURCE_GLOB
    out_dir = output_dir or Path(KB_DIR)
    col_name = collection or CHROMA_COLLECTION

    logger.info("[build] loading from %s (glob=%s)", src_dir, src_glob)
    docs = _load_documents(src_dir, src_glob)
    if not docs:
        raise ValueError(f"No matching documents found in {src_dir} with glob {src_glob}")

    logger.info("[build] found %d documents", len(docs))

    temp_dir = out_dir.parent / f"{out_dir.name}.building-{uuid.uuid4().hex[:8]}"
    try:
        logger.info("[build] building to temp dir: %s", temp_dir)
        doc_count, chunk_count = _build_temp_index(docs, temp_dir, col_name, batch_size)
        logger.info("[build] indexed %d docs into %d chunks", doc_count, chunk_count)

        _write_manifest(temp_dir, col_name, chunk_count, doc_count)
        logger.info("[build] manifest written")

        _verify_temp_index(temp_dir, col_name, chunk_count)
        logger.info("[build] temp index verified")

        _swap_index(temp_dir, out_dir)
        logger.info("[build] index build complete")

    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        logger.error("[build] build failed, temp dir cleaned up")
        raise


def check_index(output_dir: Path | None = None) -> bool:
    """仅检查索引健康，不修改磁盘。"""
    from app.rag.retriever import check_index_health

    health = check_index_health()
    if health.ready:
        logger.info(
            "[check] index ready: %d chunks, reason=%s",
            health.chunk_count,
            health.reason,
        )
        return True

    logger.warning("[check] index not ready: %s", health.reason)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Build local knowledge index")
    parser.add_argument("--source-dir", type=str, default=None)
    parser.add_argument("--source-glob", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--collection", type=str, default=None)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--check-only", action="store_true", help="Only check index health")
    args = parser.parse_args()

    if args.check_only:
        ok = check_index(Path(args.output_dir) if args.output_dir else None)
        sys.exit(0 if ok else 1)

    build_index(
        source_dir=Path(args.source_dir) if args.source_dir else None,
        source_glob=args.source_glob,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        collection=args.collection,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
