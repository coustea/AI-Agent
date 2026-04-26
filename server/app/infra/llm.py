"""LLM client factory — 懒初始化，按需创建 LLM 客户端实例。

提供工厂函数：
  - get_spark_llm(): 星火大模型（主力 LLM），用于 chat/avatar 直接回答
  - get_spark_x_llm(): 星火X模型，用于其他模块内容生成
  - get_deepseek_llm(): DeepSeek 快速模型，用于工具调用、结构化输出等
  - get_deepseek_reasoner_llm(): DeepSeek 思考模式（同一 chat 模型 + thinking enabled）
  - get_glm_vision_llm(): GLM 视觉理解模型

并发控制：
  - Spark MAX 并发上限: 10
  - Spark X 并发上限: 20
  - 超时等待 10 秒后抛出 LLMConcurrencyBusyError
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any, Callable

from langchain_community.chat_models import ChatSparkLLM
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI

from app.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_CHAT_MODEL,
    DEEPSEEK_MODEL,
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


# =============================================================================
# 并发控制
# =============================================================================

class LLMConcurrencyBusyError(Exception):
    """LLM 并发繁忙异常。

    当 Spark 模型调用等待超过超时时间时抛出，表示系统繁忙。
    业务层可捕获此异常并返回友好提示"系统繁忙，请稍后重试"。
    """
    pass


class SparkConcurrencyManager:
    """Spark 系列模型并发控制器。

    使用信号量控制 Spark MAX 和 Spark X 的并发调用数：
    - Spark MAX: 上限 10
    - Spark X: 上限 20

    超过并发限制的请求会排队等待，等待超过 10 秒抛出 LLMConcurrencyBusyError。
    """

    # 并发限制常量
    SPARK_MAX_LIMIT = 10
    SPARK_X_LIMIT = 20
    TIMEOUT_SECONDS = 10.0

    # 信号量实例（延迟初始化）
    _spark_max_semaphore: asyncio.Semaphore | None = None
    _spark_x_semaphore: asyncio.Semaphore | None = None
    _init_lock: asyncio.Lock | None = None

    @classmethod
    def _get_init_lock(cls) -> asyncio.Lock:
        """获取初始化锁（延迟创建）。"""
        if cls._init_lock is None:
            cls._init_lock = asyncio.Lock()
        return cls._init_lock

    @classmethod
    async def _ensure_semaphores(cls) -> None:
        """确保信号量已初始化。"""
        async with cls._get_init_lock():
            if cls._spark_max_semaphore is None:
                cls._spark_max_semaphore = asyncio.Semaphore(cls.SPARK_MAX_LIMIT)
            if cls._spark_x_semaphore is None:
                cls._spark_x_semaphore = asyncio.Semaphore(cls.SPARK_X_LIMIT)

    @classmethod
    async def acquire_spark_max(cls, timeout: float | None = None) -> None:
        """获取 Spark MAX 调用名额。

        Args:
            timeout: 超时时间（秒），None 使用默认值 10 秒

        Raises:
            LLMConcurrencyBusyError: 等待超时
        """
        await cls._ensure_semaphores()
        assert cls._spark_max_semaphore is not None
        effective_timeout = timeout if timeout is not None else cls.TIMEOUT_SECONDS
        try:
            await asyncio.wait_for(
                cls._spark_max_semaphore.acquire(),
                timeout=effective_timeout,
            )
        except asyncio.TimeoutError:
            raise LLMConcurrencyBusyError(
                f"Spark MAX 并发繁忙，等待超过 {effective_timeout} 秒"
            ) from None

    @classmethod
    def release_spark_max(cls) -> None:
        """释放 Spark MAX 调用名额。"""
        if cls._spark_max_semaphore is not None:
            cls._spark_max_semaphore.release()

    @classmethod
    async def acquire_spark_x(cls, timeout: float | None = None) -> None:
        """获取 Spark X 调用名额。

        Args:
            timeout: 超时时间（秒），None 使用默认值 10 秒

        Raises:
            LLMConcurrencyBusyError: 等待超时
        """
        await cls._ensure_semaphores()
        assert cls._spark_x_semaphore is not None
        effective_timeout = timeout if timeout is not None else cls.TIMEOUT_SECONDS
        try:
            await asyncio.wait_for(
                cls._spark_x_semaphore.acquire(),
                timeout=effective_timeout,
            )
        except asyncio.TimeoutError:
            raise LLMConcurrencyBusyError(
                f"Spark X 并发繁忙，等待超过 {effective_timeout} 秒"
            ) from None

    @classmethod
    def release_spark_x(cls) -> None:
        """释放 Spark X 调用名额。"""
        if cls._spark_x_semaphore is not None:
            cls._spark_x_semaphore.release()


class RateLimitedSparkLLMWrapper:
    """带并发控制的 Spark LLM 包装器。

    包装 ChatSparkLLM 实例，拦截 ainvoke/invoke/astream/stream 调用，
    在调用前获取信号量，调用后释放。
    """

    def __init__(self, llm: ChatSparkLLM, model_type: str) -> None:
        """初始化包装器。

        Args:
            llm: 原始 ChatSparkLLM 实例
            model_type: 模型类型，"spark_max" 或 "spark_x"
        """
        self._llm = llm
        self._model_type = model_type

    def _get_acquire_fn(self) -> Callable[..., Any]:
        """获取对应模型类型的 acquire 函数。"""
        if self._model_type == "spark_max":
            return SparkConcurrencyManager.acquire_spark_max
        return SparkConcurrencyManager.acquire_spark_x

    def _get_release_fn(self) -> Callable[[], None]:
        """获取对应模型类型的 release 函数。"""
        if self._model_type == "spark_max":
            return SparkConcurrencyManager.release_spark_max
        return SparkConcurrencyManager.release_spark_x

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        """异步调用，带并发控制。"""
        await self._get_acquire_fn()()
        try:
            return await self._llm.ainvoke(*args, **kwargs)
        finally:
            self._get_release_fn()()

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        """同步调用，带并发控制（通过 asyncio.run 包装）。"""
        # 同步调用需要在线程中运行异步代码
        import concurrent.futures
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.ainvoke(*args, **kwargs))
        finally:
            loop.close()

    async def astream(self, *args: Any, **kwargs: Any) -> Any:
        """异步流式调用，带并发控制。"""
        await self._get_acquire_fn()()
        try:
            async for chunk in self._llm.astream(*args, **kwargs):
                yield chunk
        finally:
            self._get_release_fn()()

    def stream(self, *args: Any, **kwargs: Any) -> Any:
        """同步流式调用，带并发控制。"""
        # 同步流式调用需要特殊处理
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._get_acquire_fn()())
            try:
                for chunk in self._llm.stream(*args, **kwargs):
                    yield chunk
            finally:
                self._get_release_fn()()
        finally:
            loop.close()

    # 代理其他属性和方法到原始 LLM
    def __getattr__(self, name: str) -> Any:
        """代理未拦截的属性到原始 LLM。"""
        return getattr(self._llm, name)

    def __repr__(self) -> str:
        return f"RateLimitedSparkLLMWrapper({self._llm!r}, type={self._model_type})"


class RateLimitedSparkXLLMWrapper:
    """带并发控制的 Spark X LLM 包装器（ChatOpenAI 兼容）。"""

    def __init__(self, llm: ChatOpenAI) -> None:
        """初始化包装器。

        Args:
            llm: 原始 ChatOpenAI 实例（Spark X）
        """
        self._llm = llm

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        """异步调用，带并发控制。"""
        await SparkConcurrencyManager.acquire_spark_x()
        try:
            return await self._llm.ainvoke(*args, **kwargs)
        finally:
            SparkConcurrencyManager.release_spark_x()

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        """同步调用，带并发控制。"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.ainvoke(*args, **kwargs))
        finally:
            loop.close()

    async def astream(self, *args: Any, **kwargs: Any) -> Any:
        """异步流式调用，带并发控制。"""
        await SparkConcurrencyManager.acquire_spark_x()
        try:
            async for chunk in self._llm.astream(*args, **kwargs):
                yield chunk
        finally:
            SparkConcurrencyManager.release_spark_x()

    def stream(self, *args: Any, **kwargs: Any) -> Any:
        """同步流式调用，带并发控制。"""
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(SparkConcurrencyManager.acquire_spark_x())
            try:
                for chunk in self._llm.stream(*args, **kwargs):
                    yield chunk
            finally:
                SparkConcurrencyManager.release_spark_x()
        finally:
            loop.close()

    # 代理其他属性和方法到原始 LLM
    def __getattr__(self, name: str) -> Any:
        """代理未拦截的属性到原始 LLM。"""
        return getattr(self._llm, name)

    def __repr__(self) -> str:
        return f"RateLimitedSparkXLLMWrapper({self._llm!r})"


# =============================================================================
# LLM 工厂函数
# =============================================================================

DEEPSEEK_THINKING_ENABLED_BODY = {"thinking": {"type": "enabled"}}
DEEPSEEK_THINKING_DISABLED_BODY = {"thinking": {"type": "disabled"}}


@lru_cache(maxsize=4)
def get_spark_llm(
    model: str = "generalv3.5",
    temperature: float = 0.3,
    streaming: bool = False,
) -> RateLimitedSparkLLMWrapper:
    """创建或返回缓存的星火 LLM 实例（带并发控制）。

    使用 langchain-community 的 ChatSparkLLM，通过 WebSocket API 调用。
    返回带并发控制的包装器，Spark MAX 并发上限 10。

    Args:
        model: 模型域名，如 generalv3.5, generalv2, general
        temperature: 温度参数
        streaming: 是否流式输出

    Returns:
        带并发控制的 Spark MAX LLM 包装器
    """
    logger.debug(
        "[LLM] 创建星火 LLM 实例: model=%s, temp=%.2f, streaming=%s",
        model, temperature, streaming,
    )
    raw_llm = ChatSparkLLM(
        spark_app_id=SPARK_APP_ID,
        spark_api_key=SPARK_API_KEY,
        spark_api_secret=SPARK_API_SECRET,
        spark_llm_domain=model,
        temperature=temperature,
        streaming=streaming,
    )
    return RateLimitedSparkLLMWrapper(raw_llm, model_type="spark_max")


@lru_cache(maxsize=2)
def get_deepseek_llm(
    model: str | None = None,
    temperature: float = 0.3,
    streaming: bool = False,
    max_tokens: int | None = None,
    max_retries: int = 2,
    timeout: float | None = None,
    thinking: bool = False,
) -> ChatDeepSeek:
    """创建或返回缓存的 DeepSeek 文本 LLM 实例。
    使用官方 langchain-deepseek SDK，默认关闭思考模式。"""
    resolved_model = model or DEEPSEEK_MODEL
    thinking_body = DEEPSEEK_THINKING_ENABLED_BODY if thinking else DEEPSEEK_THINKING_DISABLED_BODY
    logger.debug(
        "[LLM] 创建 DeepSeek LLM 实例: model=%s, temp=%.2f, streaming=%s, max_tokens=%s, thinking=%s",
        resolved_model, temperature, streaming, max_tokens, thinking,
    )
    return ChatDeepSeek(
        model=resolved_model,
        api_key=DEEPSEEK_API_KEY,
        temperature=temperature,
        streaming=streaming,
        max_tokens=max_tokens,
        max_retries=max_retries,
        timeout=timeout,
        extra_body=thinking_body,
    )


@lru_cache(maxsize=2)
def get_deepseek_reasoner_llm(
    streaming: bool = False,
    max_tokens: int | None = None,
) -> ChatDeepSeek:
    """获取 DeepSeek 思考模式实例。

    系统不再通过 deepseek-v4-pro 区分推理模型，而是在 DEEPSEEK_CHAT_MODEL
    上显式开启 thinking 模式。普通 get_deepseek_llm() 保持非思考模式。
    """
    return get_deepseek_llm(
        model=DEEPSEEK_CHAT_MODEL,
        temperature=1.0,
        streaming=streaming,
        max_tokens=max_tokens,
        thinking=True,
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
) -> RateLimitedSparkXLLMWrapper:
    """创建或返回缓存的星火X LLM 实例（带并发控制）。

    使用 OpenAI 兼容 API 调用讯飞星火X模型。
    返回带并发控制的包装器，Spark X 并发上限 20。

    Args:
        model: 模型名称，默认 spark-x
        temperature: 温度参数
        streaming: 是否流式输出

    Returns:
        带并发控制的 Spark X LLM 包装器
    """
    logger.debug(
        "[LLM] 创建星火X LLM 实例: model=%s, temp=%.2f, streaming=%s",
        model, temperature, streaming,
    )
    raw_llm = ChatOpenAI(
        model=model,
        api_key=SPARK_X_API_PASSWORD,
        base_url=SPARK_X_API_BASE,
        temperature=temperature,
        streaming=streaming,
    )
    return RateLimitedSparkXLLMWrapper(raw_llm)
