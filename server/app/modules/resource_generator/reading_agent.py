"""
拓展阅读推荐 Agent。

基于 LangGraph 扁平化工作流，使得 Agent 可以自主调用文件读取等工具辅助推荐。
"""

import os
import json
import re
from pathlib import Path
from typing import Any, TypedDict, Optional, Annotated

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, AnyMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.utils.tools_manager import tools_manager

load_dotenv()
logger = get_logger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompt"
READING_PROMPT_PATH = PROMPT_DIR / "reading.md"

with open(READING_PROMPT_PATH, "r", encoding="utf-8") as _f:
    READING_PROMPT = _f.read()

# ==========================================
# Pydantic 模型
# ==========================================

class ReadingItem(BaseModel):
    """单条阅读推荐。"""
    title: str
    author_or_source: str
    abstract: str
    relevance: str
    type: str  # paper | book | blog | documentation | video


class ReadingOutput(BaseModel):
    """阅读推荐输出。"""
    recommendations: list[ReadingItem]


# ==========================================
# State 定义
# ==========================================
class ReadingState(TypedDict, total=False):
    """阅读推荐工作流状态。"""

    # 输入
    major: str
    course: str
    topic: str
    interest_preference: str
    cognitive_style: str

    # 统一消息历史
    messages: Annotated[list[AnyMessage], add_messages]

    # 输出
    recommendations_json: str
    critique_passed: bool
    critique_feedback: str
    parsed_recommendations: list

    # 循环控制
    retry_count: int
    max_retries: int

    # 错误
    error: Optional[str]


# ==========================================
# JSON 提取辅助
# ==========================================
_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def _extract_json_text(text: str) -> str:
    """从 LLM 输出中提取 JSON。"""
    text = text.strip()
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return text[start:end]
    return text


def _custom_tools_condition(state: ReadingState) -> str:
    """判断是否调用了工具，决定下一步流向"""
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "tools"
    return "critique_quality"


# ==========================================
# ReadingAgent 类
# ==========================================
class ReadingAgent:
    """拓展阅读推荐智能体 (LangGraph StateGraph 模式)。"""

    # 配置当前 Agent 所需的最小权限工具与技能
    REQUIRED_TOOLS = ["read_file_safe"]
    REQUIRED_MCP = []
    REQUIRED_SKILLS = []

    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.3,
        )
        self.graph = None
        self._tools = None

    async def _ensure_graph(self):
        """延迟构建图，异步获取工具"""
        if self.graph is not None:
            return

        self._tools = await tools_manager.get_agent_tools(
            tool_names=self.REQUIRED_TOOLS, 
            mcp_services=self.REQUIRED_MCP
        )

        graph = StateGraph(ReadingState)

        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self._tools))
        graph.add_node("critique_quality", self._critique_quality)

        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", _custom_tools_condition)
        graph.add_edge("tools", "agent")
        
        graph.add_conditional_edges(
            "critique_quality",
            self._should_retry,
            path_map={"end": END, "retry": "agent"},
        )

        self.graph = graph.compile()
        logger.info("[ReadingAgent] 扁平化 StateGraph 构建完成")

    # ------------------------------------------
    # 节点：主控 LLM
    # ------------------------------------------
    async def _agent_node(self, state: ReadingState) -> dict:
        messages = state.get("messages", [])
        retry_count = state.get("retry_count", 0)
        feedback = state.get("critique_feedback", "")

        logger.info(f"[ReadingAgent] _agent_node: retry={retry_count}")

        if not messages:
            system_prompt = READING_PROMPT.format(
                major=state.get("major", "通用"),
                course=state.get("course", ""),
                topic=state.get("topic", ""),
                interest_preference=state.get("interest_preference", ""),
                cognitive_style=state.get("cognitive_style", ""),
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"请为主题 '{state.get('topic')}' 生成推荐阅读清单。")
            ]
        elif retry_count > 0 and feedback and len(messages) < 3:
            messages.append(HumanMessage(
                content=f"上一次推荐未通过审核，原因：{feedback}\n请根据上述反馈修正后重新生成。"
            ))

        llm_with_tools = self.llm.bind_tools(self._tools)
        response = await llm_with_tools.ainvoke(messages)
        
        return {"messages": [response]}

    # ------------------------------------------
    # 节点：质量评审
    # ------------------------------------------
    async def _critique_quality(self, state: ReadingState) -> dict:
        messages = state.get("messages", [])
        raw = ""

        if messages and isinstance(messages[-1], AIMessage):
            raw = messages[-1].content.strip()

        error = state.get("error")

        if error or not raw:
            return {
                "recommendations_json": raw,
                "critique_passed": False,
                "critique_feedback": error or "未生成推荐内容",
                "parsed_recommendations": [],
            }

        logger.info("[ReadingAgent] _critique_quality: 评审推荐质量")

        json_text = _extract_json_text(raw)

        # 1. JSON 解析
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            feedback = f"JSON 解析失败: {e}"
            logger.warning(f"[ReadingAgent] {feedback}")
            return {
                "recommendations_json": raw,
                "critique_passed": False,
                "critique_feedback": feedback,
                "parsed_recommendations": [],
            }

        # 2. Pydantic 校验
        try:
            reading_output = ReadingOutput.model_validate(data)
        except Exception as e:
            feedback = f"推荐结构不合法: {e}"
            logger.warning(f"[ReadingAgent] {feedback}")
            return {
                "recommendations_json": raw,
                "critique_passed": False,
                "critique_feedback": feedback,
                "parsed_recommendations": [],
            }

        items = reading_output.recommendations

        # 3. 数量检查
        if len(items) < 3:
            return {
                "recommendations_json": raw,
                "critique_passed": False,
                "critique_feedback": f"推荐数量不足（{len(items)} 条），至少需要 5 条。",
                "parsed_recommendations": [],
            }

        # 4. 内容质量检查
        for i, item in enumerate(items):
            if len(item.abstract) < 20:
                return {
                    "recommendations_json": raw,
                    "critique_passed": False,
                    "critique_feedback": f"第 {i + 1} 条推荐摘要过短（'{item.title}'），请补充实质性内容。",
                    "parsed_recommendations": [],
                }

        # 5. 类型多样性检查
        types = {item.type for item in items}
        if len(types) < 2:
            return {
                "recommendations_json": raw,
                "critique_passed": False,
                "critique_feedback": f"推荐类型单一（仅 {types}），请混合不同类型的资源。",
                "parsed_recommendations": [],
            }

        logger.info(
            f"[ReadingAgent] 评审通过: {len(items)} 条推荐, 类型={types}"
        )
        return {
            "recommendations_json": raw,
            "critique_passed": True,
            "critique_feedback": "",
            "parsed_recommendations": [item.model_dump() for item in items],
        }

    # ------------------------------------------
    # 条件边
    # ------------------------------------------
    @staticmethod
    def _should_retry(state: ReadingState) -> str:
        if state.get("critique_passed", False):
            return "end"
        if state.get("retry_count", 0) < state.get("max_retries", 2):
            return "retry"
        return "end"

    # ------------------------------------------
    # 公共 API
    # ------------------------------------------
    async def generate_reading(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        interest_preference: str = "",
        cognitive_style: str = "",
    ) -> dict[str, Any]:
        """生成拓展阅读推荐。"""
        logger.info(f"[ReadingAgent] 收到生成请求: topic={topic}")

        await self._ensure_graph()

        initial_state: ReadingState = {
            "major": major,
            "course": course,
            "topic": topic,
            "interest_preference": interest_preference,
            "cognitive_style": cognitive_style,
            "messages": [],
            "recommendations_json": "",
            "critique_passed": False,
            "critique_feedback": "",
            "parsed_recommendations": [],
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
        }

        try:
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 15})
        except Exception as e:
            logger.error(f"[ReadingAgent] 工作流执行失败: {e}")
            return {
                "success": False,
                "recommendations": [],
                "raw_json": "",
                "error": str(e),
            }

        parsed = result.get("parsed_recommendations", [])
        raw_json = result.get("recommendations_json", "")

        file_path = None
        if parsed:
            from app.modules.resource_generator.tools.file_saver import save_to_workplace
            import json
            file_path = save_to_workplace("reading", topic, json.dumps(parsed, ensure_ascii=False, indent=2), "json")

        return {
            "success": bool(parsed),
            "recommendations": parsed,
            "file_path": file_path,
            "raw_json": raw_json,
            "error": result.get("error") if not parsed else None,
        }


# 全局实例
reading_agent = ReadingAgent()
