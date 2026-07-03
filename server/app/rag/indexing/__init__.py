"""RAG indexing package.

This package contains modules for building and managing the knowledge index:
- build_chroma: Build and populate Chroma vector database
- embeddings: Embedding model configuration and utilities
- markdown_splitter: Markdown-aware text chunking
- semantic_splitter: Semantic-aware text chunking
- search_chroma: Search utilities for Chroma

Indexing pipeline:
1. Load documents from source files
2. Split documents into chunks (markdown_splitter / semantic_splitter)
3. Generate embeddings for chunks (embeddings)
4. Store chunks and embeddings in Chroma (build_chroma)
5. Search the index (search_chroma)
"""
from __future__ import annotations

# Re-export commonly used functions for convenience
from app.rag.indexing.build_chroma import (
    build_source_metadata,
    index_chunks,
    load_documents,
)

from app.rag.indexing.search_chroma import (
    format_result,
    get_vector_store_settings,
)

__all__ = [
    "build_source_metadata",
    "index_chunks",
    "load_documents",
    "format_result",
    "get_vector_store_settings",
]