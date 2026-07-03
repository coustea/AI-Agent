"""嵌入模型配置和实例创建。

提供统一的嵌入模型配置管理和实例创建接口，
支持本地 Ollama 嵌入模型（如 bge-m3）。

使用示例：
    embeddings = get_embeddings()
    vectors = embeddings.embed_query("什么是进程调度")
"""

from __future__ import annotations

from langchain_ollama import OllamaEmbeddings

# Import from the new config module (which re-exports from app.config)
from app.rag.config import EMBEDDING_MODEL, OLLAMA_BASE_URL


def get_ollama_client_options() -> dict[str, dict[str, bool]]:
    """Return Ollama client options that keep localhost calls off system proxies."""
    proxy_safe = {"trust_env": False}
    return {
        "client_kwargs": dict(proxy_safe),
        "sync_client_kwargs": dict(proxy_safe),
        "async_client_kwargs": dict(proxy_safe),
    }


def create_ollama_embeddings(model: str, base_url: str) -> OllamaEmbeddings:
    """Create an OllamaEmbeddings client that talks directly to the local server."""
    return OllamaEmbeddings(
        model=model,
        base_url=base_url,
        **get_ollama_client_options(),
    )


def get_embedding_settings() -> dict[str, str]:
    """获取嵌入模型配置。

    返回本地 Ollama 嵌入模型的配置参数，
    包括模型名称和 API 基础 URL。

    Returns:
        包含以下键的配置字典：
        - model: 嵌入模型名称（如 "bge-m3"）
        - base_url: Ollama API 地址
    """
    return {"model": EMBEDDING_MODEL, "base_url": OLLAMA_BASE_URL}


def get_embeddings() -> OllamaEmbeddings:
    """创建并返回 Ollama 嵌入模型实例。

    根据配置参数初始化 OllamaEmbeddings，
    用于生成文本向量表示。

    Returns:
        配置好的 OllamaEmbeddings 实例。
    """
    settings = get_embedding_settings()
    return create_ollama_embeddings(settings["model"], settings["base_url"])
