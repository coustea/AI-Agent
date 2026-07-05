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
    KB_COLLECTION,
    KB_DIR,
    KB_EMBED_MODEL,
    KB_OLLAMA_BASE_URL,
    KB_SOURCE_DIR,
    KB_SOURCE_GLOB,
    KB_TOP_K,
    KB_FETCH_K,
    KB_EMBED_TIMEOUT_SECONDS,
    KB_MAX_CONTEXT_CHARS,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)

SCHEMA_VERSION = "1"
_MANIFEST_FILENAME = "manifest.json"

# 切分参数
_CHUNK_MAX_SIZE = 800
_CHUNK_MIN_SIZE = 100
_CHUNK_OVERLAP = 100


# ============ 切分器 ============


def _split_markdown(text: str) -> list[str]:
    """将 Markdown 文本按标题和段落结构切分为块。

    保护代码块和表格不被拆断。
    """
    if not text or not text.strip():
        return []

    # 第一阶段：保护代码块
    code_blocks: list[str] = []
    placeholder_map: dict[str, str] = {}
    idx = 0
    while "```" in text:
        start = text.index("```")
        end_pos = text.find("```", start + 3)
        if end_pos == -1:
            break
        code_block = text[start : end_pos + 3]
        placeholder = f"<<CODE_BLOCK_{idx}>>"
        code_blocks.append(code_block)
        placeholder_map[placeholder] = code_block
        text = text[:start] + placeholder + text[end_pos + 3 :]
        idx += 1

    # 第二阶段：按标题和双换行切分
    raw_chunks: list[str] = []
    current = ""

    for line in text.split("\n"):
        stripped = line.strip()
        # 标题行切分
        if stripped.startswith("#") and " " in stripped and len(stripped) > 2:
            if current.strip():
                raw_chunks.append(current.strip())
            # 将标题文本追加到下一块中，增强语义匹配
            current = stripped + "\n"
        else:
            current += line + "\n"

    if current.strip():
        raw_chunks.append(current.strip())

    # 恢复代码块
    for i, chunk in enumerate(raw_chunks):
        for placeholder, code in placeholder_map.items():
            chunk = chunk.replace(placeholder, code)
        raw_chunks[i] = chunk

    # 第三阶段：合并短块 + 处理超长块
    merged: list[str] = []
    buffer = ""

    for chunk in raw_chunks:
        candidate = (buffer + "\n\n" + chunk).strip() if buffer else chunk.strip()

        if len(chunk) > _CHUNK_MAX_SIZE:
            # 超长块先 flush buffer，然后按句子拆分
            if buffer:
                merged.append(buffer.strip())
                buffer = ""
            merged.extend(_split_by_sentences(chunk))
        elif len(candidate) > _CHUNK_MAX_SIZE and buffer:
            merged.append(buffer.strip())
            buffer = chunk
        else:
            buffer = candidate

    if buffer.strip():
        if len(buffer) > _CHUNK_MAX_SIZE:
            merged.extend(_split_by_sentences(buffer))
        else:
            merged.append(buffer.strip())

    # 合并过短的块
    final: list[str] = []
    buf = ""
    for chunk in merged:
        candidate = (buf + "\n\n" + chunk).strip() if buf else chunk.strip()
        if len(chunk) < _CHUNK_MIN_SIZE and len(candidate) <= _CHUNK_MAX_SIZE * 1.5:
            buf = candidate
        else:
            if buf:
                final.append(buf)
            buf = chunk
    if buf.strip():
        final.append(buf)

    # 过滤空块
    return [c for c in final if c.strip()]


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


def _apply_overlap(chunks: list[str], overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """在相邻块间添加滑动窗口重叠。"""
    if overlap <= 0 or len(chunks) <= 1:
        return chunks
    result: list[str] = []
    for i, chunk in enumerate(chunks):
        if i > 0:
            prev = chunks[i - 1]
            tail = prev[-overlap:] if len(prev) > overlap else prev
            chunk = tail + "\n" + chunk
        result.append(chunk)
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
                # 源文件路径：相对路径
                try:
                    rel_path = path.relative_to(source_dir).as_posix()
                except ValueError:
                    rel_path = path.name
                docs.append({"path": rel_path, "text": text})
    return docs


# ============ Metadata ============


def _stable_chunk_id(source: str, section: str, content: str) -> str:
    """生成稳定的 chunk 哈希 ID。"""
    raw = f"{source}|{section}|{content}"
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


# ============ Embedding ============


def _embed_batch(texts: list[str]) -> list[list[float]] | None:
    """批量调用 Ollama embedding API。"""
    import httpx

    try:
        response = httpx.post(
            f"{KB_OLLAMA_BASE_URL}/api/embed",
            json={"model": KB_EMBED_MODEL, "input": texts},
            timeout=float(KB_EMBED_TIMEOUT_SECONDS),
            trust_env=False,
        )
        response.raise_for_status()
        data = response.json()
        raw = data.get("embeddings")
        if isinstance(raw, list) and raw and isinstance(raw[0], list):
            return [[float(v) for v in vec] for vec in raw]
        return None
    except Exception as exc:
        logger.warning("[build] embedding batch failed: %s", exc)
        return None


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
    total_chunks = 0
    all_ids: list[str] = []
    all_texts: list[str] = []
    all_metas: list[dict[str, Any]] = []

    for doc_idx, doc in enumerate(docs):
        source = doc["path"]
        text = doc["text"]
        title = _infer_title(source)
        chunks = _split_markdown(text)
        chunks = _apply_overlap(chunks)
        chunks = [c for c in chunks if c.strip()]  # 清理空块

        for chunk_idx, chunk in enumerate(chunks):
            section = _extract_section(chunk)
            chunk_id = _stable_chunk_id(source, section, chunk)
            course = _infer_course(title)

            meta: dict[str, Any] = {
                "chunk_id": chunk_id,
                "source": source,
                "title": title,
                "section": section,
                "course": course,
                "chunk_index": chunk_idx,
                "schema_version": SCHEMA_VERSION,
            }
            all_ids.append(chunk_id)
            all_texts.append(chunk)
            all_metas.append(meta)

    # 批量 embedding + 写入
    total_chunks = len(all_ids)
    if total_chunks == 0:
        raise ValueError("No chunks produced from source documents")

    for start in range(0, total_chunks, batch_size):
        end = min(start + batch_size, total_chunks)
        batch_texts = all_texts[start:end]
        batch_ids = all_ids[start:end]
        batch_metas = all_metas[start:end]

        embeddings = _embed_batch(batch_texts)
        if embeddings is None:
            raise RuntimeError(
                f"Embedding failed at batch starting index {start}. "
                "Cannot build index without embeddings."
            )

        col.add(ids=batch_ids, documents=batch_texts, embeddings=embeddings, metadatas=batch_metas)
        if end < total_chunks:
            time.sleep(0.1)

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

    # 验证正式索引可重新打开
    try:
        client = chromadb.PersistentClient(path=str(final_dir))
        col = client.get_collection(name=KB_COLLECTION)
        logger.info("[build] index swapped and verified: %d chunks", col.count())
    except Exception as exc:
        logger.error("[build] verification of swapped index failed: %s", exc)
        # 恢复 backup
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
    src_dir = source_dir or Path(KB_SOURCE_DIR)
    src_glob = source_glob or KB_SOURCE_GLOB
    out_dir = output_dir or Path(KB_DIR)
    col_name = collection or KB_COLLECTION

    # 1. 检查源目录
    logger.info("[build] loading from %s (glob=%s)", src_dir, src_glob)
    docs = _load_documents(src_dir, src_glob)
    if not docs:
        raise ValueError(f"No matching documents found in {src_dir} with glob {src_glob}")

    logger.info("[build] found %d documents", len(docs))

    # 2. 构建到临时目录
    temp_dir = out_dir.parent / f"{out_dir.name}.building-{uuid.uuid4().hex[:8]}"
    try:
        logger.info("[build] building to temp dir: %s", temp_dir)
        doc_count, chunk_count = _build_temp_index(docs, temp_dir, col_name, batch_size)
        logger.info("[build] indexed %d docs into %d chunks", doc_count, chunk_count)

        # 3. 写 Manifest
        _write_manifest(temp_dir, col_name, chunk_count, doc_count)
        logger.info("[build] manifest written")

        # 4. 重新打开验证
        _verify_temp_index(temp_dir, col_name, chunk_count)
        logger.info("[build] temp index verified")

        # 5. 原子替换
        _swap_index(temp_dir, out_dir)
        logger.info("[build] index build complete")

    except Exception:
        # 任一步失败，清理临时目录
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
