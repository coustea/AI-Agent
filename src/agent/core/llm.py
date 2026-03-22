import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from dotenv import load_dotenv

load_dotenv()


class LLM:
    """
    利用各大模型厂商兼容 OpenAI 协议的特性，使用单一 ChatOpenAI 类接入所有模型。
    """

    @staticmethod
    def create(
            model: Optional[str] = None,
            temperature: float = 0.7,
            api_key: Optional[str] = None,
            base_url: Optional[str] = None,
            max_tokens: Optional[int] = None,
    ) -> BaseChatModel:
        """
        创建模型实例。
        对于非 OpenAI 模型，只需在调用时传入该厂商的 base_url 和 api_key 即可。
        """
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
        )