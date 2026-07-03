"""RAG path configuration.

Defines the core paths used by the RAG knowledge base system.
Paths are derived from app.config.KB_DIR for consistency with server/config.yaml.
"""
from __future__ import annotations

from pathlib import Path

# Import the canonical knowledge base directory from central config
from app.config import KB_DIR

# ---------------------------------------------------------------------------
# Path Configuration
# ---------------------------------------------------------------------------

# RAG module root directory (app/rag/)
RAG_DIR = Path(__file__).resolve().parent.parent

# Book data directory (contains the markdown source files)
# Note: KB_DIR from config points to the Chroma database directory
# Book data (markdown source files) is under app/rag/data/book/
BOOK_DATA_DIR = RAG_DIR / "data" / "book"

# Chroma vector database directory
# KB_DIR from app.config already points to the correct Chroma directory
CHROMA_DIR = KB_DIR

# Documents directory (source markdown files)
DOCS_DIR = BOOK_DATA_DIR

# Documents glob pattern for source files
DOCS_GLOB = "*.final.md"

# Legacy alias for compatibility with older code
PROJECT_ROOT = BOOK_DATA_DIR