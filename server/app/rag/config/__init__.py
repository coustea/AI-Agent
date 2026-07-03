"""RAG configuration package.

This package contains all configuration modules for the RAG knowledge system:
- paths: Path configuration for data directories
- settings: Settings for embedding, chunking, and retrieval
- source_registry: Source registry for knowledge base sources
- knowledge_routes: Knowledge route configuration (JSON)
"""
from __future__ import annotations

from app.rag.config.paths import (
    BOOK_DATA_DIR,
    CHROMA_DIR,
    DOCS_DIR,
    DOCS_GLOB,
    PROJECT_ROOT,
    RAG_DIR,
)

from app.rag.config.settings import (
    CHUNK_MAX_SIZE,
    CHUNK_MIN_SIZE,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHUNKING_STRATEGY,
    EMBED_BATCH_SIZE,
    EMBEDDING_MODEL,
    HEADING_IN_BODY,
    HYBRID_SEMANTIC_THRESHOLD,
    OLLAMA_BASE_URL,
    PRIMARY_SPLIT_HEADING,
    SECONDARY_SPLIT_HEADING,
    SEMANTIC_BREAKPOINT_AMOUNT,
    SEMANTIC_BREAKPOINT_TYPE,
    SEMANTIC_BUFFER_SIZE,
    SEMANTIC_EMBEDDING_MODEL,
)

__all__ = [
    # Paths
    "RAG_DIR",
    "BOOK_DATA_DIR",
    "CHROMA_DIR",
    "DOCS_DIR",
    "DOCS_GLOB",
    "PROJECT_ROOT",
    # Settings
    "OLLAMA_BASE_URL",
    "EMBEDDING_MODEL",
    "EMBED_BATCH_SIZE",
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "CHUNK_MAX_SIZE",
    "CHUNK_MIN_SIZE",
    "HEADING_IN_BODY",
    "PRIMARY_SPLIT_HEADING",
    "SECONDARY_SPLIT_HEADING",
    "CHUNKING_STRATEGY",
    "SEMANTIC_EMBEDDING_MODEL",
    "SEMANTIC_BREAKPOINT_TYPE",
    "SEMANTIC_BREAKPOINT_AMOUNT",
    "SEMANTIC_BUFFER_SIZE",
    "HYBRID_SEMANTIC_THRESHOLD",
]