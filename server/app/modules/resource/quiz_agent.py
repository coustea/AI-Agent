"""
分层练习题生成 Agent。

基于 LangGraph 扁平化工作流，使得 Agent 可以自主调用文件读取等工具辅助出题。
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
from app.utils.skills_manager import skills_manager

load_dotenv()
logger = get_logger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompt"
QUIZ_PROMPT_PATH = PROMPT_DIR / "quiz.md"

with open(QUIZ_PROMPT_PATH, "r", encoding="utf-8") as _f:
    QUIZ_PROMPT = _f.read()

# ==========================================
# Pydantic 模型（用于结构化校验）
# ==========================================

class QuizQuestion(BaseModel):
    """单道练习题。"""
    difficulty: str = Field(description="basic | intermediate | challenge")
    question_type: str = Field(description="choice | short_answer | true_false")
    stem: str = Field(description="题干")
    options: list[str] | None = Field(default=None, description="选择题选项")
    answer: str = Field(description="正确答案")
    explanation: str = Field(description="解析")


class QuizOutput(BaseModel):
    """练习题输出。"""
    questions: list[QuizQuestion]


# ==========================================
# State 定义
# ==========================================
class QuizState(TypedDict, total=False):
    """练习题生成工作流状态。"""

    # 输入
    major: str
    course: str
    topic: str
    gap: str
    knowledge_level: str
    error_pattern: str

    # 上游 Agent 传递的上下文（DAG 编排）
    upstream_context: str

    # 统一消息历史
    messages: Annotated[list[AnyMessage], add_messages]

    # 输出
    questions_json: str
    validation_passed: bool
    validation_feedback: str
    parsed_questions: list

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
    """从 LLM 输出中提取 JSON 文本。"""
    text = text.strip()
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return text[start:end]
    return text


def _custom_tools_condition(state: QuizState) -> str:
    """判断是否调用了工具，决定下一步流向"""
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "tools"
    return "validate_structure"


# ==========================================
# QuizAgent 类
# ==========================================
class QuizAgent:
    """分层练习题生成智能体 (LangGraph StateGraph 模式)。"""

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

        graph = StateGraph(QuizState)

        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self._tools))
        graph.add_node("validate_structure", self._validate_structure)

        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", _custom_tools_condition)
        graph.add_edge("tools", "agent")
        
        graph.add_conditional_edges(
            "validate_structure",
            self._should_retry,
            path_map={"end": END, "retry": "agent"},
        )

        self.graph = graph.compile()
        logger.info("[QuizAgent] 扁平化 StateGraph 构建完成")

    # ------------------------------------------
    # 节点：主控 LLM
    # ------------------------------------------
    async def _agent_node(self, state: QuizState) -> dict:
        messages = state.get("messages", [])
        retry_count = state.get("retry_count", 0)
        feedback = state.get("validation_feedback", "")

        logger.info(f"[QuizAgent] _agent_node: retry={retry_count}")

        if not messages:
            system_prompt = QUIZ_PROMPT.format(
                major=state.get("major", "通用"),
                course=state.get("course", ""),
                topic=state.get("topic", ""),
                gap=state.get("gap", ""),
                knowledge_level=state.get("knowledge_level", "中等"),
                error_pattern=state.get("error_pattern", ""),
            )

            # 注入上游 Agent 上下文（DAG 编排）
            upstream_ctx = state.get("upstream_context", "")
            if upstream_ctx:
                system_prompt += (
                    "\n\n## [上游智能体协作上下文]\n"
                    "以下是同一任务中其他智能体已生成的输出，供你参考以保持题目与讲解内容的一致性。\n"
                    + upstream_ctx
                )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"请为主题 '{state.get('topic')}' 生成一套分层练习题。")
            ]
        elif retry_count > 0 and feedback and len(messages) < 3:
            messages.append(HumanMessage(
                content=f"上一次生成的题目未通过校验，原因：{feedback}\n请根据上述反馈修正后重新生成。"
            ))

        llm_with_tools = self.llm.bind_tools(self._tools)
        response = await llm_with_tools.ainvoke(messages)
        
        return {"messages": [response]}

    # ------------------------------------------
    # 节点：校验结构
    # ------------------------------------------
    async def _validate_structure(self, state: QuizState) -> dict:
        messages = state.get("messages", [])
        raw = ""

        if messages and isinstance(messages[-1], AIMessage):
            raw = messages[-1].content.strip()

        error = state.get("error")

        if error or not raw:
            return {
                "questions_json": raw,
                "validation_passed": False,
                "validation_feedback": error or "未生成题目内容",
                "parsed_questions": [],
            }

        logger.info("[QuizAgent] _validate_structure: 校验题目结构")

        json_text = _extract_json_text(raw)

        # 1. JSON 解析
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            feedback = f"JSON 解析失败: {e}。请确保输出合法 JSON。"
            logger.warning(f"[QuizAgent] {feedback}")
            return {
                "questions_json": raw,
                "validation_passed": False,
                "validation_feedback": feedback,
                "parsed_questions": [],
            }

        # 2. Pydantic 结构校验
        try:
            quiz_output = QuizOutput.model_validate(data)
        except Exception as e:
            feedback = f"题目结构不合法: {e}"
            logger.warning(f"[QuizAgent] {feedback}")
            return {
                "questions_json": raw,
                "validation_passed": False,
                "validation_feedback": feedback,
                "parsed_questions": [],
            }

        questions = quiz_output.questions

        # 3. 数量检查
        if len(questions) < 3:
            return {
                "questions_json": raw,
                "validation_passed": False,
                "validation_feedback": f"题目数量不足（{len(questions)} 道），至少需要 6 道题。",
                "parsed_questions": [],
            }

        # 4. 难度分布检查
        difficulties = {q.difficulty for q in questions}
        if len(difficulties) < 2:
            return {
                "questions_json": raw,
                "validation_passed": False,
                "validation_feedback": f"难度分布单一（仅 {difficulties}），需要至少覆盖 2 个难度层级。",
                "parsed_questions": [],
            }

        logger.info(
            f"[QuizAgent] 校验通过: {len(questions)} 道题, 难度分布={difficulties}"
        )
        return {
            "questions_json": raw,
            "validation_passed": True,
            "validation_feedback": "",
            "parsed_questions": [q.model_dump() for q in questions],
        }

    # ------------------------------------------
    # 条件边
    # ------------------------------------------
    @staticmethod
    def _should_retry(state: QuizState) -> str:
        if state.get("validation_passed", False):
            return "end"
        if state.get("retry_count", 0) < state.get("max_retries", 2):
            return "retry"
        return "end"

    # ------------------------------------------
    # 公共 API
    # ------------------------------------------
    async def generate_quiz(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        knowledge_level: str = "中等",
        error_pattern: str = "",
        upstream_context: str = "",
    ) -> dict[str, Any]:
        """生成分层练习题。"""
        logger.info(f"[QuizAgent] 收到生成请求: topic={topic}")

        await self._ensure_graph()

        initial_state: QuizState = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "knowledge_level": knowledge_level,
            "error_pattern": error_pattern,
            "upstream_context": upstream_context,
            "messages": [],
            "questions_json": "",
            "validation_passed": False,
            "validation_feedback": "",
            "parsed_questions": [],
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
        }

        try:
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 15})
        except Exception as e:
            logger.error(f"[QuizAgent] 工作流执行失败: {e}")
            return {
                "success": False,
                "questions": [],
                "raw_json": "",
                "error": str(e),
            }

        parsed = result.get("parsed_questions", [])
        raw_json = result.get("questions_json", "")

        file_path = None
        if parsed:
            from app.modules.resource.tools.file_saver import save_to_workplace
            import json
            file_path = save_to_workplace("quiz", topic, json.dumps(parsed, ensure_ascii=False, indent=2), "json")

        return {
            "success": bool(parsed),
            "questions": parsed,
            "file_path": file_path,
            "raw_json": raw_json,
            "error": result.get("error") if not parsed else None,
        }


# 全局实例
quiz_agent = QuizAgent()
