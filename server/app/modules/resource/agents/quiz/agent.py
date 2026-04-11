"""
分层练习题生成 Agent。
基于 BaseResourceAgent 实现，并使用黑板模式与用户画像。
"""

import json
import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage

from app.core.logging import get_logger
from app.modules.resource.base_agent import BaseResourceAgent, BaseAgentState

logger = get_logger(__name__)


class QuizQuestion(BaseModel):
    difficulty: str = Field(description="basic | intermediate | challenge")
    question_type: str = Field(description="choice | short_answer | true_false")
    stem: str = Field(description="题干")
    options: list[str] | None = Field(default=None, description="选择题选项")
    answer: str = Field(description="正确答案")
    explanation: str = Field(description="解析")


class QuizOutput(BaseModel):
    questions: list[QuizQuestion]


class QuizState(BaseAgentState):
    questions_json: str
    parsed_questions: list


_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)


def _extract_json_text(text: str) -> str:
    text = text.strip()
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return text[start:end]
    return text


class QuizAgent(BaseResourceAgent):
    """分层练习题生成 Agent。

    生成多难度层级的练习题（basic/intermediate/challenge），
    支持选择题、简答题和判断题，通过 Pydantic 校验题目结构合法性。

    Attributes:
        name:           "QuizAgent"
        agent_dir:      agents/quiz/，包含 prompt.md
        state_schema:   QuizState，包含 questions_json/parsed_questions
        method:         generate_quiz() — 对外入口
        output:         {success, questions, file_path, raw_json, error}

    工作流: agent → validate(解析JSON + 校验题数/难度分布) → retry/end
    DAG 阶段: enrichment（依赖 mindmap、content、code）
    黑板记忆: 读取 content.outline（内容大纲）
    用户画像: 读取 error_pattern（易错模式）和 knowledge_level（知识水平）
    """
    def __init__(self) -> None:
        super().__init__(
            name="QuizAgent",
            agent_dir=Path(__file__).parent,
            state_schema=QuizState,
            temperature=0.3,
        )

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        ctx = ""
        if "content" in shared_memory:
            outline = shared_memory["content"].get("outline", "")
            if outline:
                ctx += f"【内容大纲】\n{outline}\n"
        return ctx

    def _format_user_profile(self, profile: dict[str, Any]) -> str:
        if not profile: return ""
        parts = []
        if profile.get("error_pattern"):
            parts.append(f"- 易错模式: {profile['error_pattern']}")
        if profile.get("knowledge_level"):
            parts.append(f"- 知识水平: {profile['knowledge_level']}")
        return "\n".join(parts)

    def _build_system_message(self, state: Any) -> str:
        user_profile = state.get("user_profile", {})
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            gap=state.get("gap", ""),
            knowledge_level=user_profile.get("knowledge_level", "中等"),
            error_pattern=user_profile.get("error_pattern", ""),
        )
        return self._append_context_to_prompt(system_prompt, state)

    def _build_initial_human_message(self, state: Any) -> str:
        return f"请为主题 '{state.get('topic')}' 生成一套分层练习题。"

    async def _validate_node(self, state: Any) -> dict:
        messages = state.get("messages", [])
        raw = ""
        if messages and isinstance(messages[-1], AIMessage):
            raw = messages[-1].content.strip()

        error = state.get("error")
        if error or not raw:
            return {
                "questions_json": raw,
                "is_valid": False,
                "validation_feedback": error or "未生成题目内容",
                "parsed_questions": [],
                "retry_count": state.get("retry_count", 0) + 1,
            }

        logger.info("[QuizAgent] _validate_node: 校验题目结构")
        json_text = _extract_json_text(raw)

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            feedback = f"JSON 解析失败: {e}。请确保输出合法 JSON。"
            logger.warning(f"[QuizAgent] {feedback}")
            return {
                "questions_json": raw,
                "is_valid": False,
                "validation_feedback": feedback,
                "parsed_questions": [],
                "retry_count": state.get("retry_count", 0) + 1,
            }

        try:
            quiz_output = QuizOutput.model_validate(data)
        except Exception as e:
            feedback = f"题目结构不合法: {e}"
            logger.warning(f"[QuizAgent] {feedback}")
            return {
                "questions_json": raw,
                "is_valid": False,
                "validation_feedback": feedback,
                "parsed_questions": [],
                "retry_count": state.get("retry_count", 0) + 1,
            }

        questions = quiz_output.questions
        if len(questions) < 3:
            return {
                "questions_json": raw,
                "is_valid": False,
                "validation_feedback": f"题目数量不足（{len(questions)} 道），至少需要 6 道题。",
                "parsed_questions": [],
                "retry_count": state.get("retry_count", 0) + 1,
            }

        difficulties = {q.difficulty for q in questions}
        if len(difficulties) < 2:
            return {
                "questions_json": raw,
                "is_valid": False,
                "validation_feedback": f"难度分布单一（仅 {difficulties}），需要至少覆盖 2 个难度层级。",
                "parsed_questions": [],
                "retry_count": state.get("retry_count", 0) + 1,
            }

        logger.info(f"[QuizAgent] 校验通过: {len(questions)} 道题, 难度分布={difficulties}")
        return {
            "questions_json": raw,
            "is_valid": True,
            "validation_feedback": "",
            "parsed_questions": [q.model_dump() for q in questions],
        }

    async def generate_quiz(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict = None,
        shared_memory: dict = None,
    ) -> dict[str, Any]:
        logger.info(f"[QuizAgent] 收到生成请求: topic={topic}")
        await self._ensure_graph()

        initial_state: QuizState = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
            "messages": [],
            "questions_json": "",
            "is_valid": False,
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
            return {"success": False, "questions": [], "raw_json": "", "error": str(e)}

        parsed = result.get("parsed_questions", [])
        raw_json = result.get("questions_json", "")
        file_path = None
        if parsed:
            from .tools.file_saver import save_to_workplace
            file_path = save_to_workplace("quiz", topic, json.dumps(parsed, ensure_ascii=False, indent=2), "json")

        return {
            "success": bool(parsed),
            "questions": parsed,
            "file_path": file_path,
            "raw_json": raw_json,
            "error": result.get("error") if not parsed else None,
        }
