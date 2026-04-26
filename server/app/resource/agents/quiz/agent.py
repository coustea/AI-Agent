"""
分层练习题生成 Agent。
轻量实现：直接生成结构化题库，再保存 JSON。
"""

import json
from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field, model_validator

from app.infra.llm import get_deepseek_llm
from app.infra.logging import get_logger
from app.resource.utils import append_context, format_profile_fields, load_prompt, save_to_workplace

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
    tool_names = [
        "save_to_workplace", "read_file_safe",
        "write_file", "edit_file", "append_file", "read_file_lines",
        "list_directory", "file_tree", "find_files", "get_file_info",
    ]

    def __init__(self) -> None:
        self.name = "QuizAgent"
        self.agent_dir = Path(__file__).parent
        self.prompt_template = load_prompt(self.agent_dir)
        self.llm = get_deepseek_llm(temperature=0.3)

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

    async def _generate_structured_questions(self, state: dict[str, Any]) -> QuizOutput:
        prompt = self._build_system_message(state)
        human = f"请为主题 '{state.get('topic')}' 生成一套分层练习题。"
        structured_llm = self.llm.with_structured_output(QuizOutput)
        return QuizOutput.model_validate(await structured_llm.ainvoke([HumanMessage(content=prompt), HumanMessage(content=human)]))

    async def _format_quiz_json_with_ds(
        self,
        *,
        topic: str,
        course: str,
        raw_json: str,
        parsed: list[dict[str, Any]],
    ) -> str:
        prompt = (
            "你是题库 JSON 规范化助手。\n"
            "请把输入题库转换为严格 JSON，必须满足：\n"
            "1. 仅允许 question_type 为 choice 或 short_answer。\n"
            "2. 必须同时包含这两种题型。\n"
            "3. choice 必须有 options；short_answer 不要 options。\n"
            "4. 保留并补全 stem/answer/explanation 字段。\n"
            "5. 输出将通过 Pydantic + LangChain structured_output 校验。\n\n"
            f"主题: {topic}\n"
            f"课程: {course}\n"
            f"输入 JSON:\n{raw_json}"
        )
        try:
            structured_llm = self.llm.with_structured_output(QuizOutput)
            structured = await structured_llm.ainvoke([HumanMessage(content=prompt)])
            validated = QuizOutput.model_validate(structured)
            return json.dumps(
                {"questions": [q.model_dump() for q in validated.questions]},
                ensure_ascii=False,
                indent=2,
            )
        except Exception as exc:
            logger.warning("[QuizAgent] DS JSON 规范化失败，回退本地 JSON: %s", exc)
        fallback_questions = []
        for q in parsed:
            q_type = q.get("question_type")
            if q_type not in {"choice", "short_answer"}:
                continue
            fallback_questions.append(
                {
                    "difficulty": str(q.get("difficulty", "basic")),
                    "question_type": q_type,
                    "stem": str(q.get("stem", "")),
                    "answer": str(q.get("answer", "")),
                    "explanation": str(q.get("explanation", "")),
                    "options": q.get("options") if q_type == "choice" else None,
                }
            )
        return json.dumps({"questions": fallback_questions}, ensure_ascii=False, indent=2)

    async def generate_quiz(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict | None = None,
        shared_memory: dict | None = None,
    ) -> dict[str, Any]:
        logger.info("[QuizAgent] 收到生成请求: topic=%s", topic)
        state = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
        }

        try:
            output = await self._generate_structured_questions(state)
        except Exception as exc:
            logger.error("[QuizAgent] 题库生成失败: %s", exc)
            return {"success": False, "questions": [], "raw_json": "", "error": str(exc)}

        questions = [q.model_dump() for q in output.questions]
        raw_json = json.dumps({"questions": questions}, ensure_ascii=False)
        file_path = save_to_workplace("quiz", topic, json.dumps(questions, ensure_ascii=False, indent=2), "json")
        formatted_output = await self._format_quiz_json_with_ds(
            topic=topic,
            course=course,
            raw_json=raw_json,
            parsed=questions,
        )
        formatted_file_path = save_to_workplace("quiz", topic, formatted_output, "formatted.json") if formatted_output else None
        return {
            "success": True,
            "questions": questions,
            "file_path": file_path,
            "raw_json": raw_json,
            "formatted_output": formatted_output,
            "formatted_file_path": formatted_file_path,
            "error": None,
        }
