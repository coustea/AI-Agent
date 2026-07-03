from app.rag.indexing.embeddings import create_ollama_embeddings
from app.rag.rag_config import EMBEDDING_MODEL, OLLAMA_BASE_URL


def get_embedding_settings():
    return {"model": EMBEDDING_MODEL, "base_url": OLLAMA_BASE_URL}


def get_embeddings():
    settings = get_embedding_settings()
    return create_ollama_embeddings(settings["model"], settings["base_url"])


__all__ = ["create_ollama_embeddings", "get_embedding_settings", "get_embeddings"]
