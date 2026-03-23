"""ChatAgent 模块，用于 AI 对话管理。"""
import logging
import os
import sys
from typing import Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.agents import create_agent
from serpapi import GoogleSearch

# 将父目录添加到 sys.path，以便作为脚本运行时能够导入 utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.logger import setup_logging
except ImportError:
    # 如果未找到 utils（尽管使用 sys.path hack 应该不会出现），提供后备的 setup_logging 实现
    def setup_logging():
        pass

load_dotenv()
logger = logging.getLogger(__name__)

@tool
def search(query: str) -> str:
    """
    基于 SerpApi 的网页搜索工具。
    智能解析搜索结果，优先返回直接答案或知识图谱信息。
    """
    logger.info(f"正在执行 [SerpApi] 网页搜索: {query}")
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "错误: SERPAPI_API_KEY 未在 .env 文件中配置。"

        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "gl": "cn",    # 国家/地区代码
            "hl": "zh-cn", # 语言代码
        }

        client = GoogleSearch(params)
        results = client.get_dict()

        # 智能解析：优先寻找最直接的答案
        if "answer_box_list" in results:
            return "\n".join(results["answer_box_list"])
        if "answer_box" in results and "answer" in results["answer_box"]:
            return results["answer_box"]["answer"]
        if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
            return results["knowledge_graph"]["description"]
        if "organic_results" in results and results["organic_results"]:
            # 若无直接答案，则返回前三个有机结果的摘要
            snippets = [
                f"[{i + 1}] {res.get('title', '')}\n{res.get('snippet', '')}"
                for i, res in enumerate(results["organic_results"][:3])
            ]
            return "\n\n".join(snippets)

        return f"对不起，未能找到关于 '{query}' 的信息。"

    except Exception as e:
        return f"搜索时发生错误: {e}"

class ChatAgent:
    """用于管理 AI 聊天会话的 Agent。"""

    def __init__(
        self,
        model: str = "qwen-max",
        temperature: float = 0.7,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """使用模型配置初始化 ChatAgent。

        参数:
            model: 模型标识（默认: "qwen-max"）。
            temperature: 采样温度，范围 0.0 到 2.0。
            api_key: API 密钥（可覆盖环境变量）。
            base_url: API 基础 URL（可覆盖环境变量）。
            **kwargs: 传递给 ChatOpenAI 的额外参数。
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("BASE_URL")

        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=self.api_key,
            base_url=self.base_url,
            **kwargs,
        )
        self.model = model
        self.temperature = temperature
        
        # 工具列表
        self.tools = [search]
        
        # 初始化 ReAct agent
        self.agent = create_agent(self.llm, self.tools)

    def add_tools(self, tools: list) -> None:
        """向 agent 添加工具并重新初始化。

        参数:
            tools: 要添加的工具列表。
        """
        self.tools.extend(tools)
        self.agent = create_agent(self.llm, self.tools)

    def chat(self, messages: list) -> str:
        """从聊天模型生成回复。

        参数:
            messages: 会话的消息字典列表。
        返回:
            生成的回复字符串。
        """
        # 输入包含 "messages" 键的字典
        inputs = {"messages": messages}
        
        # 调用 agent 执行推理
        result = self.agent.invoke(inputs)
        
        # 提取最后一条消息的内容
        # result["messages"] 是 BaseMessage 对象的列表
        last_message = result["messages"][-1]
        logger.info(f"生成的回复: {last_message.content}")
        return last_message.content

    def stream(self, messages: list):
        """流式生成回复。

        参数:
            messages: 会话的消息字典列表。
        Yields:
            生成的文本片段。
        """
        inputs = {"messages": messages}
        
        for chunk in self.agent.stream(inputs, stream_mode="messages"):
            # chunk 是 (message, metadata) 元组
            message, metadata = chunk
            # 只输出 AI 生成的内容片段
            if hasattr(message, "content") and message.content:
                yield message.content