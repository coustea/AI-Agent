from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy import distinct, func, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import QuizQuestion
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.quiz.schemas import QuizQuestionListResponse, QuizQuestionRead

logger = get_logger(__name__)


class QuizBankService:
    """题库查询服务 — 题目列表、筛选、LaTeX 修复。"""

    _MATH_COMMAND_PATTERN = re.compile(  # 匹配未转义的 LaTeX 命令（缺少 \ 前缀）
        r"(^|[^\\a-zA-Z])(int_|iint_|iiint_|oint_|sum_|prod_|lim_|frac|sqrt|sin|cos|tan|cot|sec|csc|ln|log|exp|to|rightarrow|infty|cdots|ldots|mathrm|mathbf|boldsymbol|operatorname\*?|left|right)\b"
    )

    def _repair_missing_latex_commands(self, text: str) -> str:
        """修复缺失反斜杠的 LaTeX 命令（如 frac → \frac）。"""
        return self._MATH_COMMAND_PATTERN.sub(r"\1\\\2", text)

    def _repair_isolated_dollar_blocks(self, text: str) -> str:
        """修复孤立的 $ 符号块（LMS 渲染常见问题）。"""
        lines = text.splitlines()
        repaired: list[str] = []
        index = 0

        while index < len(lines):
            current = lines[index].strip()
            if current != "$":
                repaired.append(lines[index])
                index += 1
                continue

            probe = index + 1
            while probe < len(lines) and not lines[probe].strip():
                probe += 1

            if probe >= len(lines):
                repaired.append(lines[index])
                index += 1
                continue

            closing = probe + 1
            while closing < len(lines) and not lines[closing].strip():
                closing += 1

            if closing >= len(lines) or lines[closing].strip() != "$":
                repaired.append(lines[index])
                index += 1
                continue

            content = lines[probe].strip()
            if content.startswith("$") and content.endswith("$") and len(content) > 2:
                content = content[1:-1].strip()
            elif content.startswith("$") and len(content) > 1:
                content = content[1:].strip()
            elif content.endswith("$") and len(content) > 1:
                content = content[:-1].strip()

            content = self._repair_missing_latex_commands(content)
            is_display_math = bool(re.search(r"\\(?:int_|iint_|iiint_|oint_|sum_|prod_|lim_|frac|sqrt|begin|left|right)", content))

            repaired.append("$$" if is_display_math else "$")
            repaired.append(content)
            repaired.append("$$" if is_display_math else "$")
            index = closing + 1

        return "\n".join(repaired)

    def _normalize_math_text(self, text: str | None) -> str:
        """统一修复 LaTeX 公式文本（换行符、转义、块级公式等）。"""
        if not text:
            return ""

        normalized = (
            text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\u00a0", " ")
            .replace("\\$", "$")
        )
        normalized = self._repair_isolated_dollar_blocks(normalized)
        normalized = re.sub(r"\\\[((?:.|\n)*?)\\\]", lambda match: f"\n$$\n{match.group(1).strip()}\n$$\n", normalized)
        normalized = re.sub(r"\\\(((?:.|\n)*?)\\\)", lambda match: f"${match.group(1).strip()}$", normalized)
        normalized = self._repair_missing_latex_commands(normalized)
        normalized = normalized.replace("\\left{", "\\left\\{")
        normalized = normalized.replace("\\right\\", "\\right\\}")
        normalized = normalized.replace("\\right}", "\\right\\}")
        normalized = normalized.replace("\\mathrm{ln}", "\\ln")
        normalized = re.sub(r"\$(\\int_[^\n$]+)\$", lambda match: f"$$\n{match.group(1).strip()}\n$$", normalized)
        normalized = re.sub(r"\$\s*\n\s*([^\n].*?)\n\s*\$", lambda match: f"$$\n{match.group(1).strip()}\n$$", normalized, flags=re.S)
        normalized = re.sub(r"\$\$(?=\S)", "$$\n", normalized)
        normalized = re.sub(r"(?<=\S)\$\$", "\n$$", normalized)
        normalized = normalized.replace("$$$", "$$")
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _normalize_options(self, options: dict | None) -> dict[str, str] | None:
        if not isinstance(options, dict):
            return None

        normalized: dict[str, str] = {}
        for key, value in options.items():
            if isinstance(value, str):
                normalized[str(key)] = self._normalize_math_text(value)
            elif value is not None:
                normalized[str(key)] = str(value)
        return normalized

    async def list_questions(
        self,
        session: AsyncSession,
        *,
        query: str | None = None,
        subject: str | None = None,
        subjects: list[str] | None = None,
        difficulty: str | None = None,
        question_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> QuizQuestionListResponse:
        """查询题库题目列表，支持关键词/科目/难度/题型筛选。"""
        filters = []
        if query:
            keyword = f"%{query.strip()}%"
            filters.append(
                or_(
                    QuizQuestion.content.ilike(keyword),
                    QuizQuestion.subject.ilike(keyword),
                    QuizQuestion.analysis.ilike(keyword),
                )
            )
        if subject:
            filters.append(QuizQuestion.subject == subject)
        if subjects:
            normalized_subjects = [value.strip() for value in subjects if value and value.strip()]
            if normalized_subjects:
                filters.append(QuizQuestion.subject.in_(normalized_subjects))
        if difficulty:
            filters.append(QuizQuestion.difficulty == difficulty)
        if question_type:
            filters.append(QuizQuestion.question_type == question_type)

        safe_page = max(1, page)
        safe_page_size = max(1, min(page_size, 200))
        offset = (safe_page - 1) * safe_page_size

        stmt = (
            select(QuizQuestion)
            .order_by(QuizQuestion.id.asc())
            .offset(offset)
            .limit(safe_page_size)
        )
        count_stmt = select(func.count()).select_from(QuizQuestion)

        for condition in filters:
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        result = await session.exec(stmt)
        items = [self._to_read(item) for item in result.all()]
        total = int((await session.exec(count_stmt)).one())

        subjects = await self._list_distinct_values(session, QuizQuestion.subject)
        difficulties = await self._list_distinct_values(session, QuizQuestion.difficulty)
        types = await self._list_distinct_values(session, QuizQuestion.question_type)

        return QuizQuestionListResponse(
            items=items,
            total=total,
            page=safe_page,
            page_size=safe_page_size,
            subjects=subjects,
            difficulties=difficulties,
            types=types,
        )

    async def _list_distinct_values(self, session: AsyncSession, column) -> list[str]:
        stmt = select(distinct(column)).where(column.is_not(None)).order_by(column.asc())
        result = await session.exec(stmt)
        return [str(value).strip() for value in result.all() if str(value).strip()]

    def _to_read(self, item: QuizQuestion) -> QuizQuestionRead:
        return QuizQuestionRead(
            id=item.question_id,
            subject=item.subject,
            subject_en=item.subject_en,
            type=item.question_type,
            difficulty=item.difficulty,
            content=self._normalize_math_text(item.content),
            options=self._normalize_options(item.options_json),
            answer=self._normalize_math_text(item.answer),
            analysis=self._normalize_math_text(item.analysis),
            knowledge_points=item.knowledge_points or [],
            tags=item.tags or [],
            language=item.language,
            split=item.split,
        )


class QuizReviewOutput(BaseModel):
    """LLM 审查输出结构"""
    score: int = Field(ge=0, le=100)
    feedback: str
    improvement_hints: list[str] = Field(default_factory=list)


class QuizReviewService:
    """AI 答案审查服务 — 使用 LLM 评判主观题答案质量。"""

    _PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "quiz" / "review.md"  # 审查 prompt 模板路径

    def __init__(self):
        self._prompt_template: str | None = None

    def _load_prompt(self) -> str:
        if self._prompt_template is None:
            try:
                self._prompt_template = self._PROMPT_PATH.read_text(encoding="utf-8")
            except FileNotFoundError:
                logger.warning("[QuizReview] Prompt file not found, using fallback")
                self._prompt_template = self._fallback_prompt()
        return self._prompt_template

    def _fallback_prompt(self) -> str:
        return """# 任务
评判用户答案质量。

# 输入
- 题目: {{question_content}}
- 标准答案: {{standard_answer}}
- 用户答案: {{user_answer}}

# 输出格式
JSON: {score: 0-100, feedback: "点评", improvement_hints: ["建议"]}"""

    def _build_messages(
        self,
        question_type: str,
        question_content: str,
        standard_answer: str,
        user_answer: str,
        knowledge_points: list[str],
    ) -> list:
        prompt = self._load_prompt()
        filled = prompt.replace("{{question_type}}", question_type).replace(
            "{{question_content}}", question_content
        ).replace("{{standard_answer}}", standard_answer).replace(
            "{{user_answer}}", user_answer
        ).replace("{{knowledge_points}}", ", ".join(knowledge_points) if knowledge_points else "无")
        return [{"role": "system", "content": filled}]

    async def review(
        self,
        *,
        question_type: str,
        question_content: str,
        standard_answer: str,
        user_answer: str,
        knowledge_points: list[str] | None = None,
    ) -> dict:
        """执行 AI 答案审查 — 调用 LLM 评判并返回评分和反馈。"""
        llm = get_llm()  # 获取 LLM 单例
        messages = self._build_messages(  # 构建审查 prompt
            question_type=question_type,
            question_content=question_content,
            standard_answer=standard_answer,
            user_answer=user_answer,
            knowledge_points=knowledge_points or [],
        )

        try:
            result = await llm.ainvoke_json(  # 调用 LLM 结构化输出
                QuizReviewOutput,
                messages,
                function_name="quiz_review",
                function_description="评判主观题答案质量",
            )
            output = QuizReviewOutput.model_validate(result)  # Pydantic 校验
        except Exception as e:
            logger.warning("[QuizReview] LLM call failed: %s, using fallback", e)
            output = self._fallback_review(user_answer, standard_answer)  # LLM 失败时降级为关键词匹配

        is_correct = output.score >= 60  # 60 分以上视为正确
        return {
            "score": output.score,
            "is_correct": is_correct,
            "feedback": output.feedback,
            "improvement_hints": output.improvement_hints[:3],
        }

    def _fallback_review(self, user_answer: str, standard_answer: str) -> QuizReviewOutput:
        """LLM 失败时的 fallback 判定"""
        user_text = (user_answer or "").strip().upper()
        standard_text = (standard_answer or "").strip().upper()

        if not user_text or len(user_text) < 3:
            return QuizReviewOutput(
                score=0,
                feedback="答案内容过短或为空",
                improvement_hints=["请认真阅读题目并作答"],
            )

        keywords = [k.strip() for k in standard_text.split(",") if k.strip()]
        covered = sum(1 for k in keywords if k in user_text)
        coverage = covered / max(len(keywords), 1)

        score = min(100, int(coverage * 80 + 20))
        if score >= 60:
            feedback = "答案基本正确，但建议对照参考答案确认细节"
            hints = ["对照标准答案检查遗漏点"]
        else:
            feedback = "答案存在明显不足，请参考标准答案"
            hints = ["仔细阅读题目要求", "参考标准答案重新作答"]

        return QuizReviewOutput(score=score, feedback=feedback, improvement_hints=hints)


quiz_bank_service = QuizBankService()
quiz_review_service = QuizReviewService()
