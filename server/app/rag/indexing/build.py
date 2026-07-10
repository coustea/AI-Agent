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

管道编排，各环节委托给专门模块：
  - load.py       文档加载
  - metadata.py   元数据推断
  - splitter.py   文档分割
  - store.py      向量库 + BM25 存储
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import (
    KB_DIR,
    KB_EMBED_MODEL,
    SERVER_DIR,
)
from app.infra.logging import get_logger
from app.rag.load import load_directory
from app.rag.metadata import enrich_metadata
from app.rag.splitter import split_documents
from app.rag.store import build_store, build_bm25, verify_store
from app.rag.models import CHROMA_COLLECTION

logger = get_logger(__name__)

SCHEMA_VERSION = "1"
_MANIFEST_FILENAME = "manifest.json"

# 知识库源文档定位（锚定 server/，按课程分类目录存放）
_SOURCE_DIR = SERVER_DIR / "app/rag/data/source"


# ============ Manifest ============


# 写入索引 manifest（记录 schema 版本、模型、距离度量与数量）
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


# 读取并解析索引 manifest，失败返回 None
def _read_manifest(output_dir: Path) -> dict[str, Any] | None:
    p = output_dir / _MANIFEST_FILENAME
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


# ============ 原子替换 ============


# 原子替换正式索引目录（先备份，失败则回滚）
def _swap_index(temp_dir: Path, final_dir: Path) -> None:
    """原子替换正式索引目录。

    首次构建时 final_dir 不存在，没有 backup 可恢复；异常时仅在确有 backup 的情况下恢复，
    避免对不存在的 backup_dir 执行 rename 造成二次报错。
    """
    # 首次构建时无旧索引，仅在有备份时才重命名保留
    backup_dir = final_dir.parent / f"{final_dir.name}.backup-{uuid.uuid4().hex[:8]}"
    had_backup = final_dir.exists()

    if had_backup:
        final_dir.rename(backup_dir)

    # 用临时目录原子替换正式目录
    temp_dir.rename(final_dir)

    try:
        client = __import__("chromadb").PersistentClient(path=str(final_dir))
        col = client.get_collection(name=CHROMA_COLLECTION)
        logger.info("[build] index swapped and verified: %d chunks", col.count())
    except Exception as exc:
        logger.error("[build] verification of swapped index failed: %s", exc)

        # 验证失败则删除新目录
        if final_dir.exists():
            shutil.rmtree(final_dir)

        # 存在备份则回滚恢复
        if had_backup and backup_dir.exists():
            backup_dir.rename(final_dir)
            logger.info("[build] restored backup index")

        raise


# ============ 主构建流程 ============


# 离线索引主构建流程（加载→元数据→切分→存储→BM25→manifest→验证→替换）
def build_index(
    source_dir: Path | None = None,
    output_dir: Path | None = None,
    collection: str | None = None,
    batch_size: int = 32,
) -> None:
    """执行完整的安全构建流程。

    管道编排：加载 → 元数据 → 分割 → 重置熔断 → 存储 → BM25 → manifest → 验证 → 替换。
    """
    src_dir = source_dir or _SOURCE_DIR
    out_dir = output_dir or Path(KB_DIR)
    col_name = collection or CHROMA_COLLECTION

    # 1. 加载源文档
    logger.info("[build] loading from %s", src_dir)
    docs = load_directory(src_dir)
    if not docs:
        raise ValueError(f"No matching documents found in {src_dir}")
    logger.info("[build] found %d documents", len(docs))

    # 2. 推断文档元数据（课程/章节/标题等）
    docs = enrich_metadata(docs)

    # 3. 按文档类型切分为 chunk
    chunks = split_documents(docs)
    if not chunks:
        raise ValueError("No chunks produced from source documents")
    logger.info("[build] split into %d chunks", len(chunks))

    # 4. 重置嵌入熔断器，确保构建不受旧熔断影响
    from app.rag.embeddings import reset_breaker
    reset_breaker()

    # 5. 构建到临时目录，失败可整体丢弃
    temp_dir = out_dir.parent / f"{out_dir.name}.building-{uuid.uuid4().hex[:8]}"
    try:
        logger.info("[build] building to temp dir: %s", temp_dir)
        doc_count, chunk_count = build_store(chunks, temp_dir, col_name, batch_size)
        logger.info("[build] indexed %d docs into %d chunks", doc_count, chunk_count)

        # 6. 构建并持久化 BM25 索引
        build_bm25(chunks, temp_dir)

        # 7. 写 manifest 元数据
        _write_manifest(temp_dir, col_name, chunk_count, doc_count)
        logger.info("[build] manifest written")

        # 8. 校验向量库 chunk 数量
        verify_store(temp_dir, col_name, chunk_count)
        logger.info("[build] temp index verified")

        # 9. 原子替换正式索引目录
        _swap_index(temp_dir, out_dir)
        logger.info("[build] index build complete")

    except Exception:
        # 任一步失败则清理临时目录，正式目录保持不变
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        logger.error("[build] build failed, temp dir cleaned up")
        raise


# 仅检查索引健康状态，不修改磁盘
def check_index(output_dir: Path | None = None) -> bool:
    """仅检查索引健康，不修改磁盘。"""
    from app.rag.retriever import check_index_health

    health = check_index_health(output_dir)
    if health.ready:
        logger.info(
            "[check] index ready: %d chunks, reason=%s",
            health.chunk_count,
            health.reason,
        )
        return True

    logger.warning("[check] index not ready: %s", health.reason)
    return False


# 命令行入口：解析参数，执行构建或仅健康检查
def main() -> None:
    parser = argparse.ArgumentParser(description="Build local knowledge index")
    parser.add_argument("--source-dir", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--collection", type=str, default=None)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--check-only", action="store_true", help="Only check index health")
    args = parser.parse_args()

    # 仅健康检查模式
    if args.check_only:
        ok = check_index(Path(args.output_dir) if args.output_dir else None)
        sys.exit(0 if ok else 1)

    build_index(
        source_dir=Path(args.source_dir) if args.source_dir else None,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        collection=args.collection,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
