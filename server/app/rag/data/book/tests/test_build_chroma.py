from pathlib import Path
from types import SimpleNamespace
import shutil

import pytest

from app.rag.build_chroma import (
    batch_chunks,
    ensure_docs_dir,
    get_loader,
    index_chunks,
    load_documents,
    normalize_chunk_sources,
)


def test_normalize_chunk_sources_uses_posix_relative_paths():
    docs_root = Path("C:/repo/docs_md")
    chunk = SimpleNamespace(metadata={"source": str(docs_root / "a" / "b" / "file.md")})

    normalized = normalize_chunk_sources([chunk], docs_root)

    assert normalized[0].metadata["source"] == "a/b/file.md"


def test_normalize_chunk_sources_falls_back_to_unknown_for_missing_source():
    chunk = SimpleNamespace(metadata={})

    normalized = normalize_chunk_sources([chunk], Path("C:/repo/docs_md"))

    assert normalized[0].metadata["source"] == "unknown"


def test_ensure_docs_dir_raises_for_missing_directory():
    missing = Path(__file__).resolve().parent / "_tmp_missing_docs"
    if missing.exists():
        raise AssertionError(f"Expected missing path for test setup, found: {missing}")

    with pytest.raises(FileNotFoundError):
        ensure_docs_dir(missing)


def test_load_documents_reads_utf8_markdown():
    docs_dir = Path(__file__).resolve().parent / "_tmp_utf8_docs"
    if docs_dir.exists():
        shutil.rmtree(docs_dir)
    docs_dir.mkdir(parents=True)

    try:
        doc_path = docs_dir / "sample.final.md"
        doc_path.write_text("# 标题\n\n这是 UTF-8 内容。\n", encoding="utf-8")

        documents = load_documents(docs_dir)

        assert len(documents) == 1
        assert "UTF-8 内容" in documents[0].page_content
    finally:
        shutil.rmtree(docs_dir)


def test_batch_chunks_splits_input_by_batch_size():
    chunks = [SimpleNamespace(metadata={"source": f"{i}.md"}, page_content=str(i)) for i in range(5)]

    batches = list(batch_chunks(chunks, batch_size=2))

    assert [len(batch) for batch in batches] == [2, 2, 1]


def test_index_chunks_adds_documents_in_batches():
    class FakeStore:
        def __init__(self):
            self.calls = []

        def add_documents(self, docs, ids):
            self.calls.append((docs, ids))

    chunks = [SimpleNamespace(metadata={"source": f"{i}.md"}, page_content=str(i)) for i in range(5)]
    store = FakeStore()

    index_chunks(store, chunks, batch_size=2)

    assert [len(call[0]) for call in store.calls] == [2, 2, 1]
    assert all(len(call[0]) == len(call[1]) for call in store.calls)
    assert all(isinstance(item, str) and item for call in store.calls for item in call[1])


def test_normalize_chunk_sources_adds_relative_source_metadata_fields():
    docs_root = Path("C:/repo/docs_md")
    chunk = SimpleNamespace(
        metadata={"source": str(docs_root / "408" / "计算机网络（第7版）.final.md")}
    )

    normalized = normalize_chunk_sources([chunk], docs_root)
    metadata = normalized[0].metadata

    assert metadata["source"] == "408/计算机网络（第7版）.final.md"
    assert metadata["file_name"] == "计算机网络（第7版）.final.md"
    assert metadata["book_name"] == "计算机网络（第7版）"
    assert metadata["source_stem"] == "408/计算机网络（第7版）"


def test_normalize_chunk_sources_sets_unknown_metadata_for_missing_source():
    chunk = SimpleNamespace(metadata={})

    normalized = normalize_chunk_sources([chunk], Path("C:/repo/docs_md"))
    metadata = normalized[0].metadata

    assert metadata["source"] == "unknown"
    assert metadata["file_name"] == "unknown"
    assert metadata["book_name"] == "unknown"
    assert metadata["source_stem"] == "unknown"


def test_get_loader_targets_top_level_final_markdown_only():
    loader = get_loader(Path("C:/repo/book"))

    assert loader.glob == "*.final.md"
    assert Path(loader.path) == Path("C:/repo/book")
