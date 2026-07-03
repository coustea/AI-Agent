"""Search Chroma vector store for knowledge retrieval."""

import sys

from langchain_chroma import Chroma

# Import from new locations within the RAG package
from app.rag.config import CHROMA_DIR
from app.rag.indexing.embeddings import get_embedding_settings, get_embeddings


def get_vector_store_settings():
    settings = get_embedding_settings()
    return {
        "persist_directory": str(CHROMA_DIR),
        "embedding_model": settings["model"],
    }


def get_vector_store():
    return Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=get_embeddings(),
    )


def format_result(doc):
    return {
        "source": doc.metadata.get("source", "unknown"),
        "book_name": doc.metadata.get("book_name", "unknown"),
        "content": doc.page_content,
    }


def search(query: str, k: int = 4):
    store = get_vector_store()
    results = store.similarity_search(query, k=k)
    return [format_result(doc) for doc in results]


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python search_chroma.py <query>")

    query = sys.argv[1]
    for item in search(query):
        print(f"source: {item['source']}")
        print(f"book_name: {item['book_name']}")
        print(item["content"])
        print("-" * 40)


if __name__ == "__main__":
    main()