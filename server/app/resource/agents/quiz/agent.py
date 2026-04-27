"""
分层练习题生成 Agent。
轻量实现：直接生成结构化题库，再保存 JSON。
"""

import json
import re
from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field, model_validator

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.utils import append_context, format_profile_fields, load_prompt, save_resource_file

logger = get_logger(__name__)


class QuizQuestion(BaseModel):
    difficulty: str = Field(description="basic | intermediate | challenge")
    question_type: Literal["choice", "short_answer"] = Field(description="choice | short_answer")
    stem: str = Field(description="题干")
    options: list[str] | None = Field(default=None, description="选择题选项")
    answer: str = Field(description="正确答案")
    explanation: str = Field(description="解析")

    @model_validator(mode="after")
    def _validate_question(self) -> "QuizQuestion":
        if not self.stem.strip():
            raise ValueError("stem 不能为空")
        if not self.answer.strip():
            raise ValueError("answer 不能为空")
        if not self.explanation.strip():
            raise ValueError("explanation 不能为空")
        if self.question_type == "choice":
            options = [opt.strip() for opt in (self.options or []) if str(opt).strip()]
            if len(options) < 2:
                raise ValueError("choice 题型至少需要 2 个选项")
            self.options = options
        else:
            self.options = None
        return self


class QuizOutput(BaseModel):
    questions: list[QuizQuestion]

    @model_validator(mode="after")
    def _validate_mix(self) -> "QuizOutput":
        if len(self.questions) < 2:
            raise ValueError("至少需要 2 道题")
        q_types = {q.question_type for q in self.questions}
        if "choice" not in q_types or "short_answer" not in q_types:
            raise ValueError("题目必须同时包含 choice 和 short_answer 两种题型")
        return self


class QuizAgent:
    def __init__(self) -> None:
        self.name = "QuizAgent"
        self.agent_dir = Path(__file__).parent
        self.prompt_template = load_prompt(self.agent_dir)
        self.llm_manager = get_llm_manager()
        self.model_kwargs = {"temperature": 0.3}

    @staticmethod
    def _extract_memory(shared_memory: dict[str, Any]) -> str:
        outline = ((shared_memory or {}).get("content") or {}).get("outline", "")
        return f"【内容大纲】\n{outline}\n" if outline else ""

    @staticmethod
    def _format_user_profile(profile: dict[str, Any]) -> str:
        return format_profile_fields(
            profile,
            [
                ("error_pattern", "易错模式"),
                ("knowledge_level", "知识水平"),
            ],
        )

    def _build_system_message(self, state: dict[str, Any]) -> str:
        user_profile = state.get("user_profile", {})
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            gap=state.get("gap", ""),
            knowledge_level=user_profile.get("knowledge_level", "中等"),
            error_pattern=user_profile.get("error_pattern", ""),
        )
        return append_context(
            system_prompt,
            state=state,
            format_user_profile=self._format_user_profile,
            extract_memory=self._extract_memory,
        )

    def _extract_json(self, text: str) -> dict | None:
        """从文本中提取 JSON。"""
        def _normalize_payload(value: Any) -> dict | None:
            if isinstance(value, dict):
                return value
            if isinstance(value, list):
                return {"questions": value}
            return None

        # 尝试直接解析
        try:
            return _normalize_payload(json.loads(text))
        except json.JSONDecodeError:
            pass

        # 尝试提取代码块中的 JSON
        json_block = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        if json_block:
            try:
                return _normalize_payload(json.loads(json_block.group(1)))
            except json.JSONDecodeError:
                pass

        # 有些模型会直接输出数组形式的题目列表，前后还可能带说明文字。
        array_match = re.search(r"\[.*\]", text, re.DOTALL)
        if array_match:
            try:
                return _normalize_payload(json.loads(array_match.group(0)))
            except json.JSONDecodeError:
                pass

        # 尝试提取 { } 包裹的内容
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return _normalize_payload(json.loads(brace_match.group(0)))
            except json.JSONDecodeError:
                pass

        return None

    async def _generate_questions(self, state: dict[str, Any]) -> QuizOutput:
        """生成题目，使用普通 JSON 输出方式。"""
        prompt = self._build_system_message(state)

        json_format = '''
{
  "questions": [
    {
      "difficulty": "basic",
      "question_type": "choice",
      "stem": "题干内容",
      "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
      "answer": "B",
      "explanation": "解析说明"
    },
    {
      "difficulty": "intermediate",
      "question_type": "short_answer",
      "stem": "题干内容",
      "answer": "答案内容",
      "explanation": "解析说明"
    }
  ]
}
'''
        human = f"""请为主题 '{state.get("topic")}' 生成一套分层练习题。

要求：
1. 至少生成 4 道题
2. 必须同时包含 choice（选择题）和 short_answer（简答题）两种题型
3. difficulty 可选：basic、intermediate、challenge
4. 选择题必须有 options 字段（至少2个选项），简答题不要 options 字段
5. 只输出 JSON，不要其他内容

JSON 格式示例：
{json_format}"""

        response = await self.llm_manager.ainvoke(
            "deepseek",
            [
                HumanMessage(content=prompt),
                HumanMessage(content=human),
            ],
            model_kwargs=self.model_kwargs,
        )

        # 提取并解析 JSON
        parsed = self._extract_json(response.content)
        if not parsed:
            raise ValueError("无法从响应中提取有效的 JSON")

        # 验证并转换为 QuizOutput
        return QuizOutput.model_validate(parsed)

    async def generate_quiz(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict | None = None,
        shared_memory: dict | None = None,
        user_id: int = 0,
        resource_id: int = 0,
    ) -> dict[str, Any]:
        logger.info("[QuizAgent] 收到生成请求: topic=%s user_id=%s resource_id=%s", topic, user_id, resource_id)
        state = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
        }

        try:
            output = await self._generate_questions(state)
        except Exception as exc:
            logger.error("[QuizAgent] 题库生成失败: %s", exc)
            return {"success": False, "questions": [], "content": None, "error": str(exc)}

        questions = [q.model_dump() for q in output.questions]
        content = json.dumps({"questions": questions}, ensure_ascii=False, indent=2)

        # 保存文件到统一路径
        file_path = None
        if user_id and resource_id:
            file_path = save_resource_file(topic, content, user_id, resource_id, "json", prefix="quiz")
            logger.info("[QuizAgent] 文件已保存: %s", file_path)

        return {
            "success": True,
            "questions": questions,
            "content": content,
            "file_path": file_path,
            "error": None,
        }
