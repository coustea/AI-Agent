import app.rag.rag_config as rag_config

from app.rag.rag_embeddings import get_embedding_settings


def test_embedding_model_is_configured_once():
    assert rag_config.EMBEDDING_MODEL == "bge-m3"
    assert rag_config.OLLAMA_BASE_URL.startswith("http")


def test_get_embedding_settings_reuses_shared_config():
    settings = get_embedding_settings()

    assert settings["model"] == "bge-m3"
    assert settings["base_url"].startswith("http")
