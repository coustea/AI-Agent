from pathlib import Path
import shutil
import uuid

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_chroma import Chroma

from app.rag.markdown_splitter import MarkdownSplitter
from app.rag.rag_config import (
    CHROMA_DIR,
    CHUNK_MAX_SIZE,
    CHUNK_MIN_SIZE,
    CHUNK_OVERLAP,
    DOCS_DIR,
    DOCS_GLOB,
    EMBED_BATCH_SIZE,
    HEADING_IN_BODY,
)
from app.rag.rag_embeddings import get_embeddings


def ensure_docs_dir(docs_dir: Path) -> Path:
    if not docs_dir.exists():
        raise FileNotFoundError(f"Docs directory does not exist: {docs_dir}")
    return docs_dir


def get_loader(docs_dir: Path):
    return DirectoryLoader(
        str(docs_dir),
        glob=DOCS_GLOB,
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8", "autodetect_encoding": True},
    )


def load_documents(docs_dir: Path):
    docs_dir = ensure_docs_dir(docs_dir)
    loader = get_loader(docs_dir)
    documents = loader.load()
    if not documents:
        raise ValueError(f"No markdown files found in: {docs_dir}")
    return documents


def split_documents(raw_documents):
    splitter = MarkdownSplitter(
        max_size=CHUNK_MAX_SIZE,
        min_size=CHUNK_MIN_SIZE,
        overlap=CHUNK_OVERLAP,
        heading_in_body=HEADING_IN_BODY,
    )
    return splitter.split_documents(raw_documents)


def _strip_markdown_suffixes(name: str) -> str:
    if name.endswith(".final.md"):
        return name[: -len(".final.md")]
    if name.endswith(".md"):
        return name[: -len(".md")]
    return name


def build_source_metadata(source: str, docs_root: Path) -> dict[str, str]:
    if not source or source == "unknown":
        return {
            "source": "unknown",
            "file_name": "unknown",
            "book_name": "unknown",
            "source_stem": "unknown",
        }

    resolved_root = docs_root.resolve()
    relative_source = Path(source).resolve().relative_to(resolved_root).as_posix()
    relative_path = Path(relative_source)
    file_name = relative_path.name
    book_name = _strip_markdown_suffixes(file_name)
    source_stem = _strip_markdown_suffixes(relative_source)

    return {
        "source": relative_source,
        "file_name": file_name,
        "book_name": book_name,
        "source_stem": source_stem,
    }


def normalize_chunk_sources(chunks, docs_root: Path):
    normalized = []
    for chunk in chunks:
        source = str(chunk.metadata.get("source", "unknown") or "unknown")
        chunk.metadata.update(build_source_metadata(source, docs_root))
        normalized.append(chunk)
    return normalized


def rebuild_chroma_dir(chroma_dir: Path) -> Path:
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return chroma_dir


def batch_chunks(chunks, batch_size: int = EMBED_BATCH_SIZE):
    for index in range(0, len(chunks), batch_size):
        yield chunks[index : index + batch_size]


def index_chunks(store, chunks, batch_size: int = EMBED_BATCH_SIZE):
    for batch in batch_chunks(chunks, batch_size=batch_size):
        ids = [str(uuid.uuid4()) for _ in batch]
        store.add_documents(batch, ids=ids)
    return store


def build_vector_store(chunks, chroma_dir: Path = CHROMA_DIR, batch_size: int = EMBED_BATCH_SIZE):
    rebuild_chroma_dir(chroma_dir)
    store = Chroma(
        embedding_function=get_embeddings(),
        persist_directory=str(chroma_dir),
    )
    return index_chunks(store, chunks, batch_size=batch_size)


def main():
    raw_documents = load_documents(DOCS_DIR)
    chunks = split_documents(raw_documents)
    normalized = normalize_chunk_sources(chunks, DOCS_DIR)
    build_vector_store(normalized, CHROMA_DIR)

    sample_sources = [chunk.metadata.get("source", "unknown") for chunk in normalized[:3]]
    print(f"Indexed {len(raw_documents)} documents into {len(normalized)} chunks")
    print(f"Chroma directory: {CHROMA_DIR}")
    print(f"Sample sources: {sample_sources}")


if __name__ == "__main__":
    main()
