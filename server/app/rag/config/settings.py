"""RAG settings configuration.

Defines the core settings for embedding, chunking, and retrieval.
Runtime configuration is imported from app.config to avoid dual-source drift.
"""
from __future__ import annotations

# Import runtime configuration from the central app.config
# This ensures settings stay synchronized with server/config.yaml
from app.config import (
    KB_EMBED_MODEL,
    KB_OLLAMA_BASE_URL,
)

# ---------------------------------------------------------------------------
# Ollama Embedding Model Configuration
# ---------------------------------------------------------------------------
# Re-export with local aliases for backward compatibility
OLLAMA_BASE_URL = KB_OLLAMA_BASE_URL
EMBEDDING_MODEL = KB_EMBED_MODEL

# Batch size for embedding operations (not configurable via config.yaml)
EMBED_BATCH_SIZE = 32

# ---------------------------------------------------------------------------
# Chunking Configuration
# ---------------------------------------------------------------------------
# Chunking parameters are RAG-specific defaults, not runtime configurable
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
CHUNK_MAX_SIZE = 1100
CHUNK_MIN_SIZE = 180
HEADING_IN_BODY = True
PRIMARY_SPLIT_HEADING = "##"
SECONDARY_SPLIT_HEADING = "###"

# ---------------------------------------------------------------------------
# Semantic Chunking Configuration
# ---------------------------------------------------------------------------
# Chunking strategy: markdown / semantic / hybrid
# - markdown: structured chunking only (protects code blocks and tables)
# - semantic: pure semantic chunking (based on semantic similarity)
# - hybrid: mixed strategy (structured splitting + semantic optimization)
CHUNKING_STRATEGY = "markdown"

# Semantic chunking parameters
SEMANTIC_EMBEDDING_MODEL = KB_EMBED_MODEL  # Use same model as knowledge base
SEMANTIC_BREAKPOINT_TYPE = "percentile"  # Breakpoint detection: percentile / standard_deviation / interquartile / gradient
SEMANTIC_BREAKPOINT_AMOUNT = 92  # Percentile threshold (top 8% as breakpoints)
SEMANTIC_BUFFER_SIZE = 1  # Context window size (N sentences before and after)

# Hybrid strategy parameters
HYBRID_SEMANTIC_THRESHOLD = 1.2  # Apply semantic re-chunking only when exceeding max_size * threshold