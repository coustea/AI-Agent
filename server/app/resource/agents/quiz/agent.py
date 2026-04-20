"""
分层练习题生成 Agent。
基于 BaseResourceAgent 实现，并使用黑板模式与用户画像。
"""

import json
from pathlib import Path
from typing import Any, Literal, Optional

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field, model_validator


from app.infra.llm import get_deepseek_chat_llm
from app.infra.logging import get_logger
from app.resource.base_agent import BaseResourceAgent, BaseAgentState
from app.resource.validation import make_validation_result

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
            # short_answer 不接受选项
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


class QuizState(BaseAgentState):
    questions_json: str
    parsed_questions: list


class QuizAgent(BaseResourceAgent):
    """分层练习题生成 Agent。"""

    # 使用 DeepSeek + with_structured_output 进行结构化输出
    structured_output_schema = QuizOutput

    tool_names = [
        "save_to_workplace", "read_file_safe",
        "write_file", "edit_file", "append_file", "read_file_lines",
        "list_directory", "file_tree", "find_files", "get_file_info",
    ]
    skill_names = []


    def __init__(self) -> None:
        super().__init__(
            name="QuizAgent",
            agent_dir=Path(__file__).parent,
            state_schema=QuizState,
            temperature=0.3,
        )
        self.llm = get_deepseek_chat_llm(temperature=0.3)

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        ctx = ""
        # 题目生成依赖正文大纲，能帮助模型围绕已讲过的结构出题。
        if "content" in shared_memory:
            outline = shared_memory["content"].get("outline", "")
            if outline:
                ctx += f"【内容大纲】\n{outline}\n"
        return ctx

    def _format_user_profile(self, profile: dict[str, Any]) -> str:
        # 这里只选择"知识水平"和"易错模式"两个最直接影响题目设计的字段。
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

    def _save_to_workplace(self, sub_dir: str, topic: str, content: str, ext: str = "md") -> str:
        from app.tools.registry import get as get_tool
        # 题目最终以 json 保存，方便前端直接渲染成练习卡片或测验页面。
        return get_tool("save_to_workplace").invoke(
            {"sub_dir": sub_dir, "topic": topic, "content": content, "ext": ext}
        )

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
            item = {
                "difficulty": str(q.get("difficulty", "basic")),
                "question_type": q_type,
                "stem": str(q.get("stem", "")),
                "answer": str(q.get("answer", "")),
                "explanation": str(q.get("explanation", "")),
                "options": q.get("options") if q_type == "choice" else None,
            }
            fallback_questions.append(item)
        return json.dumps({"questions": fallback_questions}, ensure_ascii=False, indent=2)

    async def _validate_node(self, state: Any) -> dict:
        retry_count = state.get("retry_count", 0)

        error = state.get("error")
        if error:
            return make_validation_result(
                False, retry_count, error,
                questions_json="", parsed_questions=[],
            )

        # 优先从结构化输出读取（with_structured_output 直接返回 Pydantic 对象）
        structured = state.get("_structured_output")
        if structured:
            try:
                validated = QuizOutput.model_validate(structured)
            except Exception as e:
                return make_validation_result(
                    False, retry_count, f"结构化输出校验失败: {e}",
                    questions_json="", parsed_questions=[],
                )
            questions = validated.questions
            raw = json.dumps({"questions": [q.model_dump() for q in questions]}, ensure_ascii=False)
        else:
            return make_validation_result(
                False, retry_count, "未生成题目内容",
                questions_json="", parsed_questions=[],
            )

        logger.info("[QuizAgent] _validate_node: 校验题目结构")

        # 先校验最小题量，避免生成出来只有一两道题就直接当成功。
        if len(questions) < 3:
            return make_validation_result(
                False, retry_count,
                f"题目数量不足（{len(questions)} 道），至少需要 3 道题。",
                questions_json=raw, parsed_questions=[],
            )

        q_types = {q.question_type for q in questions}
        if q_types != {"choice", "short_answer"}:
            return make_validation_result(
                False, retry_count,
                f"题型必须且仅能包含 choice 和 short_answer，当前为 {q_types}",
                questions_json=raw, parsed_questions=[],
            )

        logger.info(f"[QuizAgent] 校验通过: {len(questions)} 道题, 题型={q_types}")
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

        # 这里初始化 parsed_questions，后面校验成功后会直接覆盖成结构化列表。
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
            logger.info("[QuizAgent] 开始执行题目生成工作流")
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 15})
            logger.info(
                "[QuizAgent] 工作流完成: is_valid=%s parsed_count=%d",
                result.get("is_valid"),
                len(result.get("parsed_questions", []) or []),
            )
        except Exception as e:
            logger.error(f"[QuizAgent] 工作流执行失败: {e}")
            return {"success": False, "questions": [], "raw_json": "", "error": str(e)}

        parsed = result.get("parsed_questions", [])
        raw_json = result.get("questions_json", "")
        file_path = None
        formatted_output = ""
        formatted_file_path = None
        if parsed:
            if not raw_json:
                raw_json = json.dumps({"questions": parsed}, ensure_ascii=False)
            file_path = self._save_to_workplace("quiz", topic, json.dumps(parsed, ensure_ascii=False, indent=2), "json")
            logger.info("[QuizAgent] 题库已保存: file_path=%s question_count=%d", file_path, len(parsed))
            formatted_output = await self._format_quiz_json_with_ds(
                topic=topic,
                course=course,
                raw_json=raw_json,
                parsed=parsed,
            )
            if formatted_output:
                formatted_file_path = self._save_to_workplace("quiz", topic, formatted_output, "formatted.json")
                logger.info("[QuizAgent] 题库结构化 JSON 输出已保存: file_path=%s", formatted_file_path)

        return {
            "success": bool(parsed),
            "questions": parsed,
            "file_path": file_path,
            "raw_json": raw_json,
            "formatted_output": formatted_output,
            "formatted_file_path": formatted_file_path,
            "error": result.get("error") if not parsed else None,
        }
