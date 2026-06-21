from app.rag.rag_config import EMBEDDING_MODEL, OLLAMA_BASE_URL


def get_embedding_settings():
    return {"model": EMBEDDING_MODEL, "base_url": OLLAMA_BASE_URL}


def get_embeddings():
    from langchain_ollama import OllamaEmbeddings

    settings = get_embedding_settings()
    return OllamaEmbeddings(model=settings["model"], base_url=settings["base_url"])
