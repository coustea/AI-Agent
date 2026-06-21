from types import SimpleNamespace

from app.rag.search_chroma import format_result, get_vector_store_settings


def test_get_vector_store_settings_uses_shared_chroma_dir():
    settings = get_vector_store_settings()

    assert settings["persist_directory"].endswith("my_chroma_db")
    assert settings["embedding_model"] == "bge-m3"


def test_format_result_includes_relative_source():
    doc = SimpleNamespace(
        page_content="chunk body",
        metadata={"source": "a/b/file.md"},
    )

    formatted = format_result(doc)

    assert formatted["source"] == "a/b/file.md"
    assert formatted["content"] == "chunk body"


def test_format_result_includes_book_name_for_smoke_checks():
    doc = SimpleNamespace(
        page_content="chunk body",
        metadata={"source": "408/os.final.md", "book_name": "计算机操作系统"},
    )

    formatted = format_result(doc)

    assert formatted["source"] == "408/os.final.md"
    assert formatted["book_name"] == "计算机操作系统"
    assert formatted["content"] == "chunk body"
