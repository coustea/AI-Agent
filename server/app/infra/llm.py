"""LLM client factory — 懒初始化，按需创建 LLM 客户端实例。

提供工厂函数：
  - get_spark_llm(): 星火大模型（主力 LLM）
  - get_deepseek_llm(): DeepSeek 快速模型，用于分类、路由等任务
  - get_deepseek_reasoner_llm(): DeepSeek 推理模型
  - get_glm_vision_llm(): GLM 视觉理解模型
"""

from functools import lru_cache

from langchain_community.chat_models import ChatSparkLLM
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI

from app.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    DEEPSEEK_REASONER_MODEL,
    GLM_API_KEY,
    GLM_VISION_MODEL,
    SPARK_APP_ID,
    SPARK_API_KEY,
    SPARK_API_SECRET,
    SPARK_X_API_PASSWORD,
    SPARK_X_API_BASE,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=4)
def get_spark_llm(
    model: str = "generalv3.5",
    temperature: float = 0.3,
    streaming: bool = False,
) -> ChatSparkLLM:
    """创建或返回缓存的星火 LLM 实例。
    使用 langchain-community 的 ChatSparkLLM，通过 WebSocket API 调用。

    Args:
        model: 模型域名，如 generalv3.5, generalv2, general
        temperature: 温度参数
        streaming: 是否流式输出
    """
    logger.debug(
        "[LLM] 创建星火 LLM 实例: model=%s, temp=%.2f, streaming=%s",
        model, temperature, streaming,
    )
    return ChatSparkLLM(
        spark_app_id=SPARK_APP_ID,
        spark_api_key=SPARK_API_KEY,
        spark_api_secret=SPARK_API_SECRET,
        spark_llm_domain=model,
        temperature=temperature,
        streaming=streaming,
    )


@lru_cache(maxsize=2)
def get_deepseek_llm(
    model: str | None = None,
    temperature: float = 0.3,
    streaming: bool = False,
    max_tokens: int | None = None,
    max_retries: int = 2,
    timeout: float | None = None,
) -> ChatDeepSeek:
    """创建或返回缓存的 DeepSeek 文本 LLM 实例。
    使用官方 langchain-deepseek SDK，支持 DeepSeek 原生 API。"""
    resolved_model = model or DEEPSEEK_MODEL
    logger.debug(
        "[LLM] 创建 DeepSeek LLM 实例: model=%s, temp=%.2f, streaming=%s, max_tokens=%s",
        resolved_model, temperature, streaming, max_tokens,
    )
    return ChatDeepSeek(
        model=resolved_model,
        api_key=DEEPSEEK_API_KEY,
        temperature=temperature,
        streaming=streaming,
        max_tokens=max_tokens,
        max_retries=max_retries,
        timeout=timeout,
    )


@lru_cache(maxsize=2)
def get_deepseek_reasoner_llm(
    streaming: bool = False,
    max_tokens: int | None = None,
) -> ChatDeepSeek:
    """获取 DeepSeek Reasoner 模型实例 (deepseek-v4-pro)。
    注意：推理模型通常建议使用默认 temperature (1.0) 或固定值，此处不开放 temp 调整。"""
    return get_deepseek_llm(
        model=DEEPSEEK_REASONER_MODEL,
        temperature=1.0,
        streaming=streaming,
        max_tokens=max_tokens,
    )


@lru_cache(maxsize=2)
def get_glm_vision_llm(
    model: str | None = None,
    temperature: float = 0.7,
) -> ChatOpenAI:
    """创建或返回缓存的 GLM 视觉理解 LLM 实例。
    使用智谱 BigModel API，用于图片理解等多模态任务。"""
    resolved_model = model or GLM_VISION_MODEL
    logger.debug("[LLM] 创建 GLM 视觉 LLM 实例: model=%s, temp=%.2f",
                 resolved_model, temperature)
    return ChatOpenAI(
        model=resolved_model,
        api_key=GLM_API_KEY,
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        temperature=temperature,
    )


@lru_cache(maxsize=2)
def get_spark_x_llm(
    model: str = "spark-x",
    temperature: float = 0.3,
    streaming: bool = False,
) -> ChatOpenAI:
    """创建或返回缓存的星火X LLM 实例。
    使用 OpenAI 兼容 API 调用讯飞星火X模型。

    Args:
        model: 模型名称，默认 spark-x
        temperature: 温度参数
        streaming: 是否流式输出
    """
    logger.debug(
        "[LLM] 创建星火X LLM 实例: model=%s, temp=%.2f, streaming=%s",
        model, temperature, streaming,
    )
    return ChatOpenAI(
        model=model,
        api_key=SPARK_X_API_PASSWORD,
        base_url=SPARK_X_API_BASE,
        temperature=temperature,
        streaming=streaming,
    )