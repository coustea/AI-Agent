"""Build the local Chroma knowledge base from markdown documents."""

from __future__ import annotations

import re
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document

# Import from new locations within the RAG package
from app.rag.config import (
    CHROMA_DIR,
    CHUNKING_STRATEGY,
    CHUNK_MAX_SIZE,
    CHUNK_MIN_SIZE,
    CHUNK_OVERLAP,
    DOCS_DIR,
    DOCS_GLOB,
    EMBED_BATCH_SIZE,
    HEADING_IN_BODY,
)
from app.rag.indexing.embeddings import get_embeddings
from app.rag.optimization.ranking_support import (
    build_local_context_summary,
    extract_concept_terms,
    infer_chunk_type,
)

SUPPORTED_CHUNKING_STRATEGIES = {"markdown", "semantic", "hybrid"}
KB_SCHEMA_VERSION = "2"

_LOW_VALUE_MARKERS = (
    "前言",
    "序言",
    "目录",
    "致谢",
    "版权所有",
    "ISBN",
    "出版发行",
)
_CHAPTER_LISTING_RE = re.compile(r"(第[0-9一二三四五六七八九十百零]+章|[0-9]+\.[0-9]+)")
_COURSE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("计算机网络", ("网络", "tcp", "http", "dns")),
    ("操作系统", ("操作系统", "进程", "线程")),
    ("数据结构", ("数据结构", "二叉树", "链表")),
    ("计算机组成原理", ("组成原理", "cache", "cpu")),
    ("算法", ("算法", "动态规划", "排序")),
    ("Java", ("java", "线程", "jvm")),
)


@dataclass(slots=True)
class IndexingFailure:
    batch_index: int
    sub_batch_index: int
    chunk_count: int
    error: str


def resolve_chunking_strategy(chunking_strategy: str | None = None) -> str:
    strategy = (chunking_strategy or CHUNKING_STRATEGY).strip().lower()
    if strategy not in SUPPORTED_CHUNKING_STRATEGIES:
        supported = ", ".join(sorted(SUPPORTED_CHUNKING_STRATEGIES))
        raise ValueError(f"Unknown chunking strategy: {strategy}. Supported: {supported}")
    return strategy


def ensure_docs_dir(docs_dir: Path) -> Path:
    if not docs_dir.exists():
        raise FileNotFoundError(f"Docs directory does not exist: {docs_dir}")
    return docs_dir


def get_loader(docs_dir: Path) -> DirectoryLoader:
    return DirectoryLoader(
        str(docs_dir),
        glob=DOCS_GLOB,
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8", "autodetect_encoding": True},
    )


def load_documents(docs_dir: Path) -> list[Document]:
    docs_dir = ensure_docs_dir(docs_dir)
    loader = get_loader(docs_dir)
    documents = loader.load()
    if not documents:
        raise ValueError(f"No markdown files found in: {docs_dir}")
    return documents


def split_documents(
    raw_documents: list[Document],
    chunking_strategy: str | None = None,
) -> list[Document]:
    from app.rag.config import (
        HYBRID_SEMANTIC_THRESHOLD,
        PRIMARY_SPLIT_HEADING,
        SECONDARY_SPLIT_HEADING,
        SEMANTIC_BREAKPOINT_AMOUNT,
        SEMANTIC_BREAKPOINT_TYPE,
        SEMANTIC_EMBEDDING_MODEL,
    )

    strategy = resolve_chunking_strategy(chunking_strategy)

    if strategy == "markdown":
        from app.rag.indexing.markdown_splitter import MarkdownSplitter

        splitter = MarkdownSplitter(
            max_size=CHUNK_MAX_SIZE,
            min_size=CHUNK_MIN_SIZE,
            overlap=CHUNK_OVERLAP,
            heading_in_body=HEADING_IN_BODY,
            primary_heading=PRIMARY_SPLIT_HEADING,
            secondary_heading=SECONDARY_SPLIT_HEADING,
        )
    elif strategy == "semantic":
        from app.rag.indexing.semantic_splitter import create_splitter

        splitter = create_splitter(
            strategy="semantic",
            embedding_model=SEMANTIC_EMBEDDING_MODEL,
            breakpoint_threshold_type=SEMANTIC_BREAKPOINT_TYPE,
            breakpoint_threshold_amount=SEMANTIC_BREAKPOINT_AMOUNT,
        )
    else:
        from app.rag.indexing.semantic_splitter import create_splitter

        splitter = create_splitter(
            strategy="hybrid",
            max_size=CHUNK_MAX_SIZE,
            min_size=CHUNK_MIN_SIZE,
            overlap=CHUNK_OVERLAP,
            heading_in_body=HEADING_IN_BODY,
            primary_heading=PRIMARY_SPLIT_HEADING,
            secondary_heading=SECONDARY_SPLIT_HEADING,
            embedding_model=SEMANTIC_EMBEDDING_MODEL,
            breakpoint_threshold_type=SEMANTIC_BREAKPOINT_TYPE,
            breakpoint_threshold_amount=SEMANTIC_BREAKPOINT_AMOUNT,
            semantic_threshold=HYBRID_SEMANTIC_THRESHOLD,
        )

    print(f"Using chunking strategy: {strategy}")
    return splitter.split_documents(raw_documents)


def _strip_markdown_suffixes(name: str) -> str:
    if name.endswith(".final.md"):
        return name[: -len(".final.md")]
    if name.endswith(".md"):
        return name[: -len(".md")]
    return name


def _to_relative_source(source: str, docs_root: Path) -> str:
    source_path = Path(source)
    docs_root_resolved = docs_root.resolve()

    try:
        return source_path.resolve().relative_to(docs_root_resolved).as_posix()
    except (OSError, RuntimeError, ValueError):
        pass

    if source_path.is_absolute():
        return source_path.name or "unknown"
    return source_path.as_posix()


def build_source_metadata(source: str, docs_root: Path) -> dict[str, str]:
    if not source or source == "unknown":
        return {
            "source": "unknown",
            "file_name": "unknown",
            "book_name": "unknown",
            "source_stem": "unknown",
            "canonical_source_id": "unknown",
        }

    relative_source = _to_relative_source(source, docs_root)
    relative_path = Path(relative_source)
    file_name = relative_path.name
    book_name = _strip_markdown_suffixes(file_name)
    source_stem = _strip_markdown_suffixes(relative_source)
    return {
        "source": relative_source,
        "file_name": file_name,
        "book_name": book_name,
        "source_stem": source_stem,
        "canonical_source_id": book_name,
    }


def infer_course_name(metadata: dict[str, str], text: str) -> str:
    haystack = " ".join(
        [
            str(metadata.get("canonical_source_id") or ""),
            str(metadata.get("book_name") or ""),
            str(metadata.get("source") or ""),
            str(text or "")[:200],
        ]
    ).lower()
    for course_name, hints in _COURSE_HINTS:
        if any(hint.lower() in haystack for hint in hints):
            return course_name
    return ""


def normalize_chunk_sources(
    chunks: list[Document],
    docs_root: Path,
    *,
    chunking_strategy: str | None = None,
) -> list[Document]:
    strategy = resolve_chunking_strategy(chunking_strategy)
    normalized: list[Document] = []

    for chunk in chunks:
        source = str(chunk.metadata.get("source", "unknown") or "unknown")
        chunk.metadata.update(build_source_metadata(source, docs_root))
        heading = str(
            chunk.metadata.get("heading_path")
            or chunk.metadata.get("section")
            or chunk.metadata.get("chapter")
            or ""
        ).strip()
        chunk.metadata.setdefault("section", heading)
        chunk.metadata.setdefault("chapter", heading.split(">")[0].strip() if heading else "")
        page_content = str(chunk.page_content or "")
        chunk.metadata.setdefault("course", str(chunk.metadata.get("course") or "").strip())
        if not str(chunk.metadata.get("course") or "").strip():
            chunk.metadata["course"] = infer_course_name(chunk.metadata, page_content)
        chunk.metadata["chunk_type"] = infer_chunk_type(page_content, chunk.metadata)
        chunk.metadata["concept_tags"] = list(
            extract_concept_terms(page_content, chunk.metadata)
        )
        chunk.metadata["local_context_summary"] = build_local_context_summary(
            page_content,
            chunk.metadata,
        )
        chunk.metadata["chunking_strategy"] = strategy
        chunk.metadata["kb_schema_version"] = KB_SCHEMA_VERSION
        normalized.append(chunk)
    return normalized


def _is_low_value_chunk(chunk: Document) -> bool:
    text = str(chunk.page_content or "").strip()
    if not text:
        return True

    metadata = chunk.metadata or {}
    heading_path = str(metadata.get("heading_path", "") or "").strip()
    lowered = text.lower()
    preview = text[:300]

    if not heading_path and any(marker.lower() in lowered for marker in _LOW_VALUE_MARKERS):
        return True

    if not heading_path and len(text) < 120 and text.count("\n") <= 2:
        return True

    if any(marker in preview for marker in ("前言", "目录", "致谢")) and not heading_path:
        return True

    if "目录" in preview and len(_CHAPTER_LISTING_RE.findall(preview)) >= 2:
        return True

    book_name = str(metadata.get("book_name", "") or "")
    if book_name and preview.count(book_name) >= 2 and len(text) < 400:
        return True

    return False


def filter_low_value_chunks(chunks: list[Document]) -> list[Document]:
    return [chunk for chunk in chunks if not _is_low_value_chunk(chunk)]


def rebuild_chroma_dir(chroma_dir: Path) -> Path:
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return chroma_dir


def batch_chunks(chunks: list[Document], batch_size: int = EMBED_BATCH_SIZE):
    for index in range(0, len(chunks), batch_size):
        yield chunks[index : index + batch_size]


def index_chunks(
    store: Chroma,
    chunks: list[Document],
    batch_size: int = EMBED_BATCH_SIZE,
) -> Chroma:
    total_batches = (len(chunks) + batch_size - 1) // batch_size
    print(f"Indexing {len(chunks)} chunks in {total_batches} batches (batch_size={batch_size})")

    failures: list[IndexingFailure] = []
    indexed_chunks = 0

    for batch_index, batch in enumerate(batch_chunks(chunks, batch_size=batch_size), 1):
        ids = [str(uuid.uuid4()) for _ in batch]
        try:
            store.add_documents(batch, ids=ids)
            indexed_chunks += len(batch)
            if batch_index % 10 == 0 or batch_index == total_batches:
                print(
                    f"Progress: {batch_index}/{total_batches} batches "
                    f"({indexed_chunks} chunks indexed)"
                )
            if batch_index < total_batches:
                time.sleep(0.1)
        except Exception as exc:
            print(f"Error in batch {batch_index}: {exc}")
            print("Retrying with smaller batch...")
            half_batch = max(batch_size // 2, 1)
            for offset in range(0, len(batch), half_batch):
                sub_batch = batch[offset : offset + half_batch]
                sub_ids = [str(uuid.uuid4()) for _ in sub_batch]
                sub_batch_index = (offset // half_batch) + 1
                try:
                    store.add_documents(sub_batch, ids=sub_ids)
                    indexed_chunks += len(sub_batch)
                    time.sleep(0.2)
                except Exception as retry_exc:
                    print(f"Failed to index sub-batch {sub_batch_index}: {retry_exc}")
                    failures.append(
                        IndexingFailure(
                            batch_index=batch_index,
                            sub_batch_index=sub_batch_index,
                            chunk_count=len(sub_batch),
                            error=str(retry_exc),
                        )
                    )

    if failures:
        failure_summary = "; ".join(
            (
                f"batch={failure.batch_index},sub_batch={failure.sub_batch_index},"
                f"chunks={failure.chunk_count},error={failure.error}"
            )
            for failure in failures[:5]
        )
        raise RuntimeError(
            f"Indexing incomplete: indexed {indexed_chunks}/{len(chunks)} chunks; "
            f"{len(failures)} sub-batches failed. {failure_summary}"
        )

    return store


def build_vector_store(
    chunks: list[Document],
    chroma_dir: Path = CHROMA_DIR,
    batch_size: int = EMBED_BATCH_SIZE,
) -> Chroma:
    rebuild_chroma_dir(chroma_dir)
    store = Chroma(
        embedding_function=get_embeddings(),
        persist_directory=str(chroma_dir),
    )
    return index_chunks(store, chunks, batch_size=batch_size)


def main() -> None:
    raw_documents = load_documents(DOCS_DIR)
    chunks = split_documents(raw_documents)
    chunks = filter_low_value_chunks(chunks)
    normalized = normalize_chunk_sources(chunks, DOCS_DIR)
    build_vector_store(normalized, CHROMA_DIR)

    sample_sources = [chunk.metadata.get("source", "unknown") for chunk in normalized[:3]]
    print(f"Indexed {len(raw_documents)} documents into {len(normalized)} chunks")
    print(f"Chroma directory: {CHROMA_DIR}")
    print(f"Sample sources: {sample_sources}")


if __name__ == "__main__":
    main()
