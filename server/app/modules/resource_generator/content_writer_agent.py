"""
内容创作 Agent：生成个性化专业课程讲解文档。

基于 LangGraph 扁平化工作流，支持在生成大纲和撰写内容时按需调用工具。
"""

import os
import json
import re
from pathlib import Path
from typing import Any, TypedDict, Optional, Annotated

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, AnyMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.utils.tools_manager import tools_manager

load_dotenv()
logger = get_logger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompt"
CONTENT_PROMPT_PATH = PROMPT_DIR / "content_write.md"

with open(CONTENT_PROMPT_PATH, "r", encoding="utf-8") as _f:
    CONTENT_PROMPT = _f.read()

# ==========================================
# State 定义
# ==========================================
class ContentState(TypedDict, total=False):
    """内容创作工作流状态。"""

    # 输入
    major: str
    course: str
    topic: str
    user_profile: str

    # 统一消息历史
    messages: Annotated[list[AnyMessage], add_messages]
    
    # 状态控制
    current_step: str  # 'outline' 或 'content'
    
    # 节点输出
    outline: str
    content: str
    
    review_passed: bool
    review_feedback: str

    # 循环控制
    retry_count: int
    max_retries: int

    # 错误
    error: Optional[str]


# ==========================================
# JSON 提取辅助
# ==========================================
_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def _extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON 对象。"""
    match = _FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {"passed": False, "feedback": "无法解析审查结果"}


# ==========================================
# 质量审查提示词
# ==========================================
_REVIEW_PROMPT = (
    "你是一位教学文档质量审查专家。请审查以下课程讲解文档的质量。\n\n"
    "## 审查标准\n"
    "1. 字数检查：文档正文应在 2000-5000 字之间\n"
    "2. 结构完整性：是否包含 概述、核心讲解、案例分析、常见误区、总结 等主要章节\n"
    "3. 内容针对性：是否围绕主题 {topic} 深入展开，而非泛泛而谈\n"
    "4. 个性化匹配：是否考虑了用户画像 {user_profile} 中描述的学习特点\n"
    "5. 案例质量：是否包含至少一个完整的实际案例\n\n"
    "## 待审查文档\n"
    "{content}\n\n"
    "## 大纲\n"
    "{outline}\n\n"
    "## 输出要求\n"
    "请严格按以下 JSON 格式输出审查结论，不要包含代码围栏：\n"
    '{{"passed": true/false, "feedback": "如果不通过，说明具体原因和改进建议"}}'
)


def _custom_tools_condition(state: ContentState) -> str:
    """判断是否调用了工具，决定下一步流向"""
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "tools"
    return "step_router"


def _step_router_condition(state: ContentState) -> str:
    """路由到下一个处理步骤"""
    step = state.get("current_step", "outline")
    if step == "outline":
        return "agent"  # 继续执行 content 步骤
    else:
        return "review_quality"


# ==========================================
# ContentWriter 类
# ==========================================
class ContentWriter:
    """内容创作智能体 (LangGraph StateGraph 模式)。"""

    # 配置当前 Agent 所需的最小权限工具与技能
    REQUIRED_TOOLS = ["read_file_safe"]
    REQUIRED_MCP = []
    REQUIRED_SKILLS = ["content-research-writer"]

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

        graph = StateGraph(ContentState)

        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self._tools))
        graph.add_node("step_router", self._step_router_node)
        graph.add_node("review_quality", self._review_quality)

        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", _custom_tools_condition)
        graph.add_edge("tools", "agent")
        
        graph.add_conditional_edges(
            "step_router",
            _step_router_condition,
            {
                "agent": "agent",
                "review_quality": "review_quality"
            }
        )

        graph.add_conditional_edges(
            "review_quality",
            self._should_retry,
            path_map={"end": END, "retry": "agent"},
        )

        self.graph = graph.compile()
        logger.info("[ContentAgent] 扁平化 StateGraph 构建完成")

    # ------------------------------------------
    # 节点：主控 LLM
    # ------------------------------------------
    async def _agent_node(self, state: ContentState) -> dict:
        messages = state.get("messages", [])
        current_step = state.get("current_step", "outline")
        retry_count = state.get("retry_count", 0)
        feedback = state.get("review_feedback", "")

        logger.info(f"[ContentAgent] _agent_node: step={current_step}, retry={retry_count}")

        # 如果是首次生成 outline
        if current_step == "outline" and not messages:
            system_msg = CONTENT_PROMPT.format(
                major=state.get("major", "通用"),
                course=state.get("course", ""),
                topic=state.get("topic", ""),
                user_profile=state.get("user_profile", "{}"),
            )
            messages = [
                SystemMessage(content=system_msg),
                HumanMessage(content="请先为这份讲解文档生成一份详细的大纲（列出各章节标题及每节要点的简短描述）。")
            ]
        elif current_step == "outline" and retry_count > 0 and feedback and len(messages) < 3:
            # 重试情况
            messages.append(HumanMessage(
                content=f"上一次文档未通过审查，原因：{feedback}\n请根据上述反馈修正大纲后重新生成。"
            ))
        elif current_step == "content" and not any("撰写完整的专业讲解文档" in str(m.content) for m in messages):
            # 准备生成 content
            outline = state.get("outline", "")
            messages.append(HumanMessage(
                content=f"请根据以上大纲撰写完整的专业讲解文档（2000-5000字），严格遵循大纲结构，每个章节都要有充实的内容。"
            ))

        llm_with_tools = self.llm.bind_tools(self._tools)
        response = await llm_with_tools.ainvoke(messages)
        
        return {"messages": [response]}

    # ------------------------------------------
    # 节点：步骤路由与结果提取
    # ------------------------------------------
    async def _step_router_node(self, state: ContentState) -> dict:
        messages = state.get("messages", [])
        current_step = state.get("current_step", "outline")
        
        last_content = ""
        if messages and isinstance(messages[-1], AIMessage):
            last_content = messages[-1].content.strip()

        if current_step == "outline":
            logger.info(f"[ContentAgent] 大纲生成完成，长度={len(last_content)}")
            return {
                "outline": last_content,
                "current_step": "content"
            }
        else:
            logger.info(f"[ContentAgent] 文档扩展完成，长度={len(last_content)}")
            return {
                "content": last_content
            }

    # ------------------------------------------
    # 节点：质量审查
    # ------------------------------------------
    async def _review_quality(self, state: ContentState) -> dict:
        content = state.get("content", "")
        outline = state.get("outline", "")
        error = state.get("error")

        if error or not content:
            return {
                "review_passed": False,
                "review_feedback": error or "未生成内容",
            }

        logger.info("[ContentAgent] _review_quality: 开始质量审查")

        # 基础字数检查
        word_count = len(content)
        if word_count < 500:
            return {
                "review_passed": False,
                "review_feedback": f"文档字数仅 {word_count} 字，远低于 2000 字的最低要求，请大幅扩展。",
            }

        prompt = _REVIEW_PROMPT.format(
            topic=state.get("topic", ""),
            user_profile=state.get("user_profile", "{}"),
            content=content[:3000],
            outline=outline[:1000],
        )

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            review = _extract_json(response.content)
            passed = review.get("passed", False)
            feedback = review.get("feedback", "")

            logger.info(f"[ContentAgent] 审查结果: passed={passed}, feedback={feedback}")
            return {
                "review_passed": passed,
                "review_feedback": feedback,
            }
        except Exception as e:
            logger.error(f"[ContentAgent] _review_quality 失败: {e}")
            return {
                "review_passed": True,
                "review_feedback": None,
            }

    # ------------------------------------------
    # 条件边
    # ------------------------------------------
    @staticmethod
    def _should_retry(state: ContentState) -> str:
        if state.get("review_passed", False):
            return "end"
        if state.get("retry_count", 0) < state.get("max_retries", 2):
            return "retry"
        return "end"

    # ------------------------------------------
    # 公共 API
    # ------------------------------------------
    async def generate_content(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        user_profile: str = "{}",
    ) -> dict[str, Any]:
        """生成个性化课程讲解文档。"""
        logger.info(f"[ContentAgent] 收到生成请求: topic={topic}")

        await self._ensure_graph()

        initial_state: ContentState = {
            "major": major,
            "course": course,
            "topic": topic,
            "user_profile": user_profile,
            "messages": [],
            "current_step": "outline",
            "outline": "",
            "content": "",
            "review_passed": False,
            "review_feedback": "",
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
        }

        try:
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 20})
        except Exception as e:
            logger.error(f"[ContentAgent] 工作流执行失败: {e}")
            return {
                "success": False,
                "content": "",
                "outline": "",
                "error": str(e),
            }

        success = bool(result.get("content"))
        content = result.get("content", "")
        outline = result.get("outline", "")

        file_path = None
        if success:
            from app.modules.resource_generator.tools.file_saver import save_to_workplace
            file_path = save_to_workplace("content", topic, content, "md")

        return {
            "success": success,
            "content": content,
            "outline": outline,
            "file_path": file_path,
            "error": result.get("error") if not success else None,
        }


# 全局实例
content_writer = ContentWriter()
