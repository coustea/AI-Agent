"""LLM client factory — lazy initialization."""

import os
from functools import lru_cache

from langchain_openai import ChatOpenAI


@lru_cache(maxsize=4)
def get_llm(
    model: str | None = None,
    temperature: float = 0.3,
    streaming: bool = False,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """Create or retrieve a cached LLM client instance."""
    return ChatOpenAI(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE"),
        temperature=temperature,
        streaming=streaming,
        max_tokens=max_tokens,
    )


def get_fast_llm(temperature: float = 0.0, max_tokens: int = 100) -> ChatOpenAI:
    """Get the fast/classifier LLM instance."""
    return ChatOpenAI(
        model=os.getenv("FAST_LLM_MODEL", "general"),
        api_key=os.getenv("FAST_LLM_API_KEY", os.getenv("OPENAI_API_KEY")),
        base_url=os.getenv("OPENAI_API_BASE"),
        temperature=temperature,
        max_tokens=max_tokens,
    )
