"""离线知识库索引构建器。

默认直接运行即可构建可检索知识库：
  python app/rag/build.py

常用命令：
  python app/rag/build.py
  python app/rag/build.py --check-only
  python app/rag/build.py --source-dir app/rag/data/source
  python app/rag/build.py --output-dir app/rag/data/index
  python app/rag/build.py --batch-size 16

安全构建流程：
  1. 检查源目录与文档
  2. 构建到临时目录 *.building-<uuid>
  3. 写入 ChromaDB 向量索引
  4. 构建 BM25 关键词索引
  5. 写 manifest.json
  6. 重新打开验证
  7. 全部成功后替换正式目录
  8. 任一步失败删除临时目录，正式目录不变

管道编排，各环节委托给专门模块：
  - load.py       文档加载
  - metadata.py   元数据推断
  - splitter.py   文档分割
  - store.py      向量库 + BM25 存储
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

# 允许直接执行：python app/rag/build.py
# build.py 位于 server/app/rag/build.py，parents[2] 即 server 根目录。
_SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVER_ROOT))

from app.config import (  # noqa: E402
    KB_DIR,
    KB_EMBED_BASE_URL,
    KB_EMBED_MODEL,
    SERVER_DIR,
)
from app.infra.logging import get_logger  # noqa: E402
from app.rag.load import load_directory  # noqa: E402
from app.rag.metadata import enrich_metadata  # noqa: E402
from app.rag.models import CHROMA_COLLECTION, MANIFEST_FILENAME, SCHEMA_VERSION  # noqa: E402
from app.rag.splitter import (  # noqa: E402
    CHUNK_MAX_SIZE,
    CHUNK_MIN_SIZE,
    CHUNK_OVERLAP,
    split_documents,
)
from app.rag.store import build_bm25, build_store, verify_store  # noqa: E402
from app.rag.embeddings import probe_embedding_service  # noqa: E402

logger = get_logger(__name__)

# 知识库源文档定位（锚定 server/，按课程分类目录存放）
_SOURCE_DIR = SERVER_DIR / "app/rag/data/source"

# 默认嵌入批大小。直接运行 build.py 时使用该值。
_DEFAULT_BATCH_SIZE = 16

# 构建进度阶段总数
_TOTAL_STAGES = 11

# 历史构建残留清理策略
_BUILDING_DIR_MAX_AGE_SECONDS = 24 * 60 * 60
_MAX_BACKUP_DIRS_TO_KEEP = 2


# ============ 日志与进度 ============


def _log_stage(step: int, name: str, message: str = "") -> None:
    """输出构建阶段进度日志。"""
    percent = int(step / _TOTAL_STAGES * 100)
    if message:
        logger.info("[build] [%02d/%02d %3d%%] %s - %s", step, _TOTAL_STAGES, percent, name, message)
    else:
        logger.info("[build] [%02d/%02d %3d%%] %s", step, _TOTAL_STAGES, percent, name)


def _elapsed_seconds(start_time: float) -> float:
    """计算耗时秒数。"""
    return round(time.monotonic() - start_time, 2)


# ============ 路径与源文件快照 ============


def _normalize_path(path: Path) -> Path:
    """规范化路径，不要求路径已经存在。"""
    return Path(path).expanduser()


def _build_source_snapshot(source_dir: Path, docs: list[Any]) -> dict[str, Any]:
    """根据已加载文档生成源文件快照。

    只使用 source 相对路径、文件大小和修改时间，不额外读取整份教材内容，
    避免大知识库构建前产生额外 IO 压力。
    """
    rel_sources = sorted(
        {
            str(doc.metadata.get("source", "")).strip()
            for doc in docs
            if str(doc.metadata.get("source", "")).strip()
        }
    )

    hasher = hashlib.sha256()
    total_bytes = 0
    file_count = 0

    for rel_source in rel_sources:
        path = source_dir / rel_source
        if not path.exists() or not path.is_file():
            continue

        try:
            stat = path.stat()
        except OSError:
            continue

        file_count += 1
        total_bytes += stat.st_size

        hasher.update(rel_source.encode("utf-8", errors="ignore"))
        hasher.update(b"\0")
        hasher.update(str(stat.st_size).encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(str(stat.st_mtime_ns).encode("utf-8"))
        hasher.update(b"\n")

    return {
        "source_file_count": file_count,
        "source_total_bytes": total_bytes,
        "source_fingerprint": hasher.hexdigest(),
    }


# ============ Manifest ============


def _write_manifest(
    output_dir: Path,
    collection: str,
    chunk_count: int,
    doc_count: int,
    *,
    source_dir: Path,
    source_snapshot: dict[str, Any],
    batch_size: int,
    embedding_dimension: int,
    bm25_metadata: dict[str, Any] | None,
) -> None:
    """写入索引 manifest。

    manifest 不仅用于健康检查，也用于后续排查索引是否过期：
      - 当前 embedding_model 是什么
      - 当前 chunk 数量是多少
      - 当前源文件快照是什么
      - 当前切分参数是什么
    """
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "collection": collection,
        "embedding_model": KB_EMBED_MODEL,
        "embedding_base_url": KB_EMBED_BASE_URL.rstrip("/"),
        "embedding_dimension": embedding_dimension,
        "distance_metric": "cosine",
        "document_count": doc_count,
        "chunk_count": chunk_count,
        "source_dir": str(source_dir),
        "source_file_count": source_snapshot.get("source_file_count", 0),
        "source_total_bytes": source_snapshot.get("source_total_bytes", 0),
        "source_fingerprint": source_snapshot.get("source_fingerprint", ""),
        "splitter": {
            "chunk_max_size": CHUNK_MAX_SIZE,
            "chunk_min_size": CHUNK_MIN_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
        },
        "builder": {
            "entry": "python app/rag/build.py",
            "batch_size": batch_size,
        },
        "bm25": {
            "enabled": True,
            "built": bm25_metadata is not None,
            **(bm25_metadata or {}),
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / MANIFEST_FILENAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_manifest(output_dir: Path) -> dict[str, Any] | None:
    """读取并解析索引 manifest，失败返回 None。"""
    path = output_dir / MANIFEST_FILENAME
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("[check] manifest read failed: %s", exc)
        return None


# ============ 构建残留清理 ============


def _cleanup_stale_work_dirs(final_dir: Path) -> None:
    """清理历史构建残留目录。

    清理策略：
      - 删除超过 24 小时的 *.building-* 临时目录
      - backup 只保留最近 2 个
    """
    parent = final_dir.parent
    if not parent.exists():
        return

    now = time.time()

    for path in parent.glob(f"{final_dir.name}.building-*"):
        if not path.is_dir():
            continue

        try:
            age = now - path.stat().st_mtime
            if age >= _BUILDING_DIR_MAX_AGE_SECONDS:
                shutil.rmtree(path)
                logger.info("[build] stale temp dir removed: %s", path)
        except Exception as exc:
            logger.warning("[build] failed to remove stale temp dir %s: %s", path, exc)

    backups = [p for p in parent.glob(f"{final_dir.name}.backup-*") if p.is_dir()]
    backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for old_backup in backups[_MAX_BACKUP_DIRS_TO_KEEP:]:
        try:
            shutil.rmtree(old_backup)
            logger.info("[build] old backup dir removed: %s", old_backup)
        except Exception as exc:
            logger.warning("[build] failed to remove old backup dir %s: %s", old_backup, exc)


# ============ 替换正式索引目录 ============


def _swap_index(temp_dir: Path, final_dir: Path) -> None:
    """替换正式索引目录。

    流程：
      1. 如果旧索引存在，先重命名为 backup
      2. 将 temp_dir 重命名为正式索引目录
      3. 重新打开 ChromaDB 验证
      4. 验证失败则删除新目录并回滚旧目录
      5. 成功后重置 BM25 懒加载单例
    """
    final_dir.parent.mkdir(parents=True, exist_ok=True)

    backup_dir = final_dir.parent / f"{final_dir.name}.backup-{uuid.uuid4().hex[:8]}"
    had_backup = final_dir.exists()

    if had_backup:
        logger.info("[build] old index moved to backup: %s", backup_dir)
        final_dir.rename(backup_dir)

    logger.info("[build] temp index moved to final dir: %s", final_dir)
    temp_dir.rename(final_dir)

    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(final_dir))
        collection = client.get_collection(name=CHROMA_COLLECTION)
        count = collection.count()

        logger.info("[build] final index verified: %d chunks", count)

        # 如果构建和服务在同一进程内执行，确保 BM25 下次重新加载新索引。
        try:
            from app.rag.bm25 import reset_bm25_index

            reset_bm25_index()
            logger.info("[build] bm25 cache reset")
        except Exception as exc:
            logger.warning("[build] bm25 cache reset failed: %s", exc)

    except Exception as exc:
        logger.error("[build] verification of final index failed: %s", exc)

        if final_dir.exists():
            shutil.rmtree(final_dir)

        if had_backup and backup_dir.exists():
            backup_dir.rename(final_dir)
            logger.info("[build] backup index restored: %s", final_dir)

        raise


# ============ 主构建流程 ============


def build_index(
    source_dir: Path | None = None,
    output_dir: Path | None = None,
    collection: str | None = None,
    batch_size: int = _DEFAULT_BATCH_SIZE,
) -> None:
    """执行完整的安全构建流程。

    默认行为：
      直接运行 python app/rag/build.py 即构建可检索知识库。

    管道编排：
      加载 → 元数据 → 分割 → 重置熔断 → 向量存储 → BM25 → manifest → 验证 → 替换
    """
    started_at = time.monotonic()
    stage = "init"
    temp_dir: Path | None = None

    src_dir = _normalize_path(source_dir or _SOURCE_DIR)
    out_dir = _normalize_path(output_dir or Path(KB_DIR))
    col_name = collection or CHROMA_COLLECTION

    try:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")

        out_dir.parent.mkdir(parents=True, exist_ok=True)

        logger.info("============================================================")
        logger.info("[build] RAG knowledge base build started")
        logger.info("[build] source_dir=%s", src_dir)
        logger.info("[build] output_dir=%s", out_dir)
        logger.info("[build] collection=%s", col_name)
        logger.info("[build] embedding_model=%s", KB_EMBED_MODEL)
        logger.info("[build] batch_size=%d", batch_size)
        logger.info("============================================================")

        # 1. 清理历史构建残留
        stage = "cleanup"
        _log_stage(1, "清理历史构建残留")
        _cleanup_stale_work_dirs(out_dir)

        # 2. 加载源文档
        stage = "load_documents"
        _log_stage(2, "加载源文档", str(src_dir))
        docs = load_directory(src_dir)
        if not docs:
            raise ValueError(f"No matching documents found in {src_dir}")
        logger.info("[build] loaded documents: %d", len(docs))

        # 3. 生成源文件快照
        stage = "source_snapshot"
        _log_stage(3, "生成源文件快照")
        source_snapshot = _build_source_snapshot(src_dir, docs)
        logger.info(
            "[build] source snapshot: files=%d bytes=%d fingerprint=%s",
            source_snapshot["source_file_count"],
            source_snapshot["source_total_bytes"],
            str(source_snapshot["source_fingerprint"])[:12],
        )

        # 4. 推断文档元数据
        stage = "enrich_metadata"
        _log_stage(4, "推断文档元数据")
        docs = enrich_metadata(docs)

        # 5. 文档切分
        stage = "split_documents"
        _log_stage(5, "切分文档 Chunk")
        chunks = split_documents(docs)
        if not chunks:
            raise ValueError("No chunks produced from source documents")
        logger.info("[build] split result: docs=%d chunks=%d", len(docs), len(chunks))

        # 6. 重置嵌入熔断器
        stage = "reset_embedding_breaker"
        _log_stage(6, "重置嵌入熔断器")
        from app.rag.embeddings import reset_breaker

        reset_breaker()

        # 使用与构建完全相同的 config.yaml 参数探测 embedding 服务，
        # 在创建临时索引前尽早发现 endpoint/model/key 不可用的问题。
        embedding_dimension = probe_embedding_service()
        logger.info("[build] embedding service ready: dimension=%d", embedding_dimension)

        # 7. 准备临时索引目录
        stage = "prepare_temp_dir"
        _log_stage(7, "准备临时索引目录")
        temp_dir = out_dir.parent / f"{out_dir.name}.building-{uuid.uuid4().hex[:8]}"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        logger.info("[build] temp_dir=%s", temp_dir)

        # 8. 构建 ChromaDB 向量库
        stage = "build_vector_store"
        _log_stage(8, "构建 ChromaDB 向量索引", f"chunks={len(chunks)}")
        doc_count, chunk_count = build_store(
            chunks=chunks,
            output_dir=temp_dir,
            collection=col_name,
            batch_size=batch_size,
            embedding_dimension=embedding_dimension,
        )
        logger.info("[build] vector index built: docs=%d chunks=%d", doc_count, chunk_count)

        # 9. 构建 BM25 关键词索引
        stage = "build_bm25"
        _log_stage(9, "构建 BM25 关键词索引")
        bm25_metadata = build_bm25(chunks, temp_dir)
        if bm25_metadata is None:
            raise RuntimeError("BM25 index build failed; refusing to publish a partial index")
        logger.info("[build] bm25 index built")

        # 10. 写 manifest 并校验临时索引
        stage = "write_manifest_and_verify"
        _log_stage(10, "写入 manifest 并校验临时索引")
        _write_manifest(
            output_dir=temp_dir,
            collection=col_name,
            chunk_count=chunk_count,
            doc_count=doc_count,
            source_dir=src_dir,
            source_snapshot=source_snapshot,
            batch_size=batch_size,
            embedding_dimension=embedding_dimension,
            bm25_metadata=bm25_metadata,
        )
        logger.info("[build] manifest written: %s", temp_dir / MANIFEST_FILENAME)

        verify_store(temp_dir, col_name, chunk_count)
        logger.info("[build] temp index verified")

        # 11. 替换正式索引目录
        stage = "swap_index"
        _log_stage(11, "替换正式索引目录")
        _swap_index(temp_dir, out_dir)
        temp_dir = None

        elapsed = _elapsed_seconds(started_at)

        logger.info("============================================================")
        logger.info("[build] RAG knowledge base build completed")
        logger.info("[build] status=success")
        logger.info("[build] output_dir=%s", out_dir)
        logger.info("[build] documents=%d", doc_count)
        logger.info("[build] chunks=%d", chunk_count)
        logger.info("[build] elapsed_seconds=%.2f", elapsed)
        logger.info("[build] knowledge base is ready for retrieval")
        logger.info("============================================================")

    except Exception:
        if temp_dir is not None and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.error("[build] build failed at stage=%s, temp dir cleaned: %s", stage, temp_dir)
        else:
            logger.error("[build] build failed at stage=%s", stage)

        logger.exception("[build] RAG knowledge base build failed")
        raise


# ============ 健康检查 ============


def check_index(output_dir: Path | None = None) -> bool:
    """仅检查索引健康状态，不修改磁盘。"""
    from app.rag.retriever import check_index_health

    target_dir = _normalize_path(output_dir) if output_dir else None
    health = check_index_health(target_dir)

    if health.ready:
        logger.info(
            "[check] index ready: chunks=%d reason=%s",
            health.chunk_count,
            health.reason,
        )

        manifest_dir = target_dir or Path(KB_DIR)
        manifest = _read_manifest(manifest_dir)

        if manifest:
            logger.info(
                "[check] manifest: model=%s docs=%s chunks=%s created_at=%s",
                manifest.get("embedding_model"),
                manifest.get("document_count"),
                manifest.get("chunk_count"),
                manifest.get("created_at"),
            )
            logger.info(
                "[check] source: files=%s bytes=%s fingerprint=%s",
                manifest.get("source_file_count"),
                manifest.get("source_total_bytes"),
                str(manifest.get("source_fingerprint", ""))[:12],
            )

        return True

    logger.warning("[check] index not ready: %s", health.reason)
    return False


# ============ 命令行入口 ============


def main() -> None:
    """命令行入口。

    不传任何参数时，默认完整构建知识库：
      python app/rag/build.py
    """
    parser = argparse.ArgumentParser(description="Build local RAG knowledge index")

    parser.add_argument(
        "--source-dir",
        type=str,
        default=None,
        help="Source document directory. Default: server/app/rag/data/source",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output index directory. Default: KB_DIR from config",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=None,
        help=f"Chroma collection name. Default: {CHROMA_COLLECTION}",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=_DEFAULT_BATCH_SIZE,
        help=f"Embedding batch size. Default: {_DEFAULT_BATCH_SIZE}",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check index health, do not build index",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else None

    if args.check_only:
        ok = check_index(output_dir)
        sys.exit(0 if ok else 1)

    build_index(
        source_dir=Path(args.source_dir) if args.source_dir else None,
        output_dir=output_dir,
        collection=args.collection,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
