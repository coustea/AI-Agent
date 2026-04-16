"""LLM client factory — 懒初始化，按需创建 LLM 客户端实例。

提供两个工厂函数：
  - get_llm(): 主力 LLM，@lru_cache 缓存，用于对话生成、记忆压缩等核心任务
  - get_fast_llm(): 轻量快速 LLM，不缓存，用于意图分类、路由判断等低延迟任务
"""

import os
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.infra.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=4)  # 最多缓存 4 组不同参数组合的实例
def get_llm(
    model: str | None = None,
    temperature: float = 0.3,
    streaming: bool = False,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """创建或返回缓存的 LLM 客户端实例。
    缓存 key = (model, temperature, streaming, max_tokens)，相同参数复用同一实例。
    默认使用 OPENAI_MODEL 环境变量指定的模型。"""
    resolved_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    logger.debug("[LLM] 创建主力 LLM 实例: model=%s, temp=%.2f, streaming=%s, max_tokens=%s",
                 resolved_model, temperature, streaming, max_tokens)
    return ChatOpenAI(
        model=resolved_model,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE"),  # OpenAI 兼容 API 端点
        temperature=temperature,
        streaming=streaming,
        max_tokens=max_tokens,
    )


def get_fast_llm(temperature: float = 0.0, max_tokens: int = 100) -> ChatOpenAI:
    """获取快速/分类 LLM 实例（不缓存，每次创建新实例）。
    使用 FAST_LLM_MODEL 环境变量指定的模型，默认 temperature=0 确保分类结果稳定。
    典型用途：消息路由分类、意图识别、模式判断等低延迟任务。"""
    model = os.getenv("FAST_LLM_MODEL", "general")
    logger.debug("[LLM] 创建快速 LLM 实例: model=%s, temp=%.2f, max_tokens=%d",
                 model, temperature, max_tokens)
    return ChatOpenAI(
        model=model,
        api_key=os.getenv("FAST_LLM_API_KEY", os.getenv("OPENAI_API_KEY")),  # 回退到主 API key
        base_url=os.getenv("OPENAI_API_BASE"),
        temperature=temperature,
        max_tokens=max_tokens,
    )