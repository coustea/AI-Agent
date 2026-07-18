"""题库查询与 AI 答案审查服务。"""

from __future__ import annotations

import asyncio
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

# 创建模块级日志器
logger = get_logger(__name__)

QUIZ_REVIEW_TIMEOUT_SECONDS = 20


# 题库查询服务：题目列表、筛选与 LaTeX 公式修复
class QuizBankService:
    """题库查询服务 — 题目列表、筛选、LaTeX 修复。"""

    # 中文题型标签 → 数据库英文键 的反向映射
    _TYPE_LABEL_TO_KEY: dict[str, str] = {
        "单选题": "single_choice",
        "判断题": "judge",
        "填空题": "fill_blank",
        "分析题": "analysis",
        "选择题": "single_choice",  # 兼容旧标签
    }

    # 匹配未转义的 LaTeX 命令（缺少 \ 前缀）的正则
    _MATH_COMMAND_PATTERN = re.compile(  # 匹配未转义的 LaTeX 命令（缺少 \ 前缀）
        r"(^|[^\\a-zA-Z])(int_|iint_|iiint_|oint_|sum_|prod_|lim_|frac|sqrt|sin|cos|tan|cot|sec|csc|ln|log|exp|to|rightarrow|infty|cdots|ldots|mathrm|mathbf|boldsymbol|operatorname\*?|left|right)\b"
    )

    # 为缺失反斜杠的 LaTeX 命令补全反斜杠
    def _repair_missing_latex_commands(self, text: str) -> str:
        """修复缺失反斜杠的 LaTeX 命令（如 frac → \frac）。"""
        return self._MATH_COMMAND_PATTERN.sub(r"\1\\\2", text)

    # 修复孤立的 $ 符号块（LMS 渲染常见问题）
    def _repair_isolated_dollar_blocks(self, text: str) -> str:
        """修复孤立的 $ 符号块（LMS 渲染常见问题）。"""
        # 按行拆分文本并初始化修复结果
        lines = text.splitlines()
        repaired: list[str] = []
        index = 0

        # 逐行扫描修复孤立 $ 块
        while index < len(lines):
            current = lines[index].strip()
            # 非孤立 $ 行直接保留
            if current != "$":
                repaired.append(lines[index])
                index += 1
                continue

            # 向后查找下一行非空内容
            probe = index + 1
            while probe < len(lines) and not lines[probe].strip():
                probe += 1

            # 未找到配对内容，保留原始行
            if probe >= len(lines):
                repaired.append(lines[index])
                index += 1
                continue

            # 继续查找闭合的孤立 $ 行
            closing = probe + 1
            while closing < len(lines) and not lines[closing].strip():
                closing += 1

            # 缺少闭合 $，保留原始行
            if closing >= len(lines) or lines[closing].strip() != "$":
                repaired.append(lines[index])
                index += 1
                continue

            # 提取块内公式内容并剥离多余 $
            content = lines[probe].strip()
            if content.startswith("$") and content.endswith("$") and len(content) > 2:
                content = content[1:-1].strip()
            elif content.startswith("$") and len(content) > 1:
                content = content[1:].strip()
            elif content.endswith("$") and len(content) > 1:
                content = content[:-1].strip()

            # 修复块内缺失 LaTeX 命令并判断是否为块级公式
            content = self._repair_missing_latex_commands(content)
            is_display_math = bool(re.search(r"\\(?:int_|iint_|iiint_|oint_|sum_|prod_|lim_|frac|sqrt|begin|left|right)", content))

            # 按公式级别包裹 $$ 或 $
            repaired.append("$$" if is_display_math else "$")
            repaired.append(content)
            repaired.append("$$" if is_display_math else "$")
            index = closing + 1

        # 拼接修复后文本
        return "\n".join(repaired)

    # 统一规范化 LaTeX 公式文本（换行、转义、块级公式等）
    def _normalize_math_text(self, text: str | None) -> str:
        """统一修复 LaTeX 公式文本（换行符、转义、块级公式等）。"""
        # 空文本直接返回空串
        if not text:
            return ""

        # 归一化换行符与空白字符，去除转义的 $
        normalized = (
            text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\u00a0", " ")
            .replace("\\$", "$")
        )
        # 修复孤立的 $ 块
        normalized = self._repair_isolated_dollar_blocks(normalized)
        # 将 \[ \] 与 \( \) 转换为标准块级/行内公式
        normalized = re.sub(r"\\\[((?:.|\n)*?)\\\]", lambda match: f"\n$$\n{match.group(1).strip()}\n$$\n", normalized)
        normalized = re.sub(r"\\\(((?:.|\n)*?)\\\)", lambda match: f"${match.group(1).strip()}$", normalized)
        # 补全缺失 LaTeX 命令并修正常见转义写法
        normalized = self._repair_missing_latex_commands(normalized)
        normalized = normalized.replace("\\left{", "\\left\\{")
        normalized = normalized.replace("\\right\\", "\\right\\}")
        normalized = normalized.replace("\\right}", "\\right\\}")
        normalized = normalized.replace("\\mathrm{ln}", "\\ln")
        # 将行内积分等公式提升为块级公式
        normalized = re.sub(r"\$(\\int_[^\n$]+)\$", lambda match: f"$$\n{match.group(1).strip()}\n$$", normalized)
        normalized = re.sub(r"\$\s*\n\s*([^\n].*?)\n\s*\$", lambda match: f"$$\n{match.group(1).strip()}\n$$", normalized, flags=re.S)
        # 修正块级公式分隔符的间距
        normalized = re.sub(r"\$\$(?=\S)", "$$\n", normalized)
        normalized = re.sub(r"(?<=\S)\$\$", "\n$$", normalized)
        normalized = normalized.replace("$$$", "$$")
        # 压缩多余空行并去除首尾空白
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    # 规范化题目选项中的 LaTeX 公式文本
    def _normalize_options(self, options: dict | None) -> dict[str, str] | None:
        """规范化题目选项中的 LaTeX 公式文本。"""
        # 非字典类型直接返回 None
        if not isinstance(options, dict):
            return None

        # 逐选项规范化文本
        normalized: dict[str, str] = {}
        for key, value in options.items():
            if isinstance(value, str):
                normalized[str(key)] = self._normalize_math_text(value)
            elif value is not None:
                normalized[str(key)] = str(value)
        return normalized

    # 查询题库题目列表：支持关键词/科目/难度/题型筛选与分页
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
        # 收集查询过滤条件
        filters = []
        if query:
            # 关键词模糊匹配题干、科目与解析
            keyword = f"%{query.strip()}%"
            filters.append(
                or_(
                    QuizQuestion.content.ilike(keyword),
                    QuizQuestion.subject.ilike(keyword),
                    QuizQuestion.analysis.ilike(keyword),
                )
            )
        if subject:
            # 按单个科目精确筛选
            filters.append(QuizQuestion.subject == subject)
        if subjects:
            # 按科目列表批量筛选，先去除空白项
            normalized_subjects = [value.strip() for value in subjects if value and value.strip()]
            if normalized_subjects:
                filters.append(QuizQuestion.subject.in_(normalized_subjects))
        if difficulty:
            # 按难度筛选
            filters.append(QuizQuestion.difficulty == difficulty)
        if question_type:
            # 前端传中文标签（如"单选题"），需转换为数据库英文键（如"single_choice"）
            db_type = self._TYPE_LABEL_TO_KEY.get(question_type, question_type)
            filters.append(QuizQuestion.question_type == db_type)

        # 约束分页参数并换算偏移量
        safe_page = max(1, page)
        safe_page_size = max(1, min(page_size, 200))
        offset = (safe_page - 1) * safe_page_size

        # 构建分页查询与计数语句
        stmt = (
            select(QuizQuestion)
            .order_by(QuizQuestion.id.asc())
            .offset(offset)
            .limit(safe_page_size)
        )
        count_stmt = select(func.count()).select_from(QuizQuestion)

        # 应用所有过滤条件
        for condition in filters:
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        # 执行查询并转换为响应 DTO
        result = await session.exec(stmt)
        items = [self._to_read(item) for item in result.all()]
        # 统计符合条件的总数
        total = int((await session.exec(count_stmt)).one())

        # 查询可用的科目/难度/题型筛选选项
        subjects = await self._list_distinct_values(session, QuizQuestion.subject)
        difficulties = await self._list_distinct_values(session, QuizQuestion.difficulty)
        types = await self._list_distinct_values(session, QuizQuestion.question_type)

        # 返回分页结果与筛选选项
        return QuizQuestionListResponse(
            items=items,
            total=total,
            page=safe_page,
            page_size=safe_page_size,
            subjects=subjects,
            difficulties=difficulties,
            types=types,
        )

    # 查询指定列的去重非空值，用于构建筛选下拉项
    async def _list_distinct_values(self, session: AsyncSession, column) -> list[str]:
        """查询指定列的所有去重非空值。"""
        # 按列去重并升序排序
        stmt = select(distinct(column)).where(column.is_not(None)).order_by(column.asc())
        result = await session.exec(stmt)
        # 返回去空白后的字符串列表
        return [str(value).strip() for value in result.all() if str(value).strip()]

    # 将 ORM 对象转换为 API 响应 DTO，并规范化其中的 LaTeX 公式
    def _to_read(self, item: QuizQuestion) -> QuizQuestionRead:
        """将 ORM 对象转换为 API 响应 DTO，同时规范化 LaTeX 公式。"""
        # 逐字段映射并修复公式文本
        return QuizQuestionRead(
            id=item.question_id,
            subject=item.subject,
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


# LLM 审查结构化输出模型
class QuizReviewOutput(BaseModel):
    """LLM 审查输出结构"""
    score: int = Field(ge=0, le=100)
    feedback: str
    improvement_hints: list[str] = Field(default_factory=list)


# AI 答案审查服务：使用 LLM 评判主观题答案质量
class QuizReviewService:
    """AI 答案审查服务 — 使用 LLM 评判主观题答案质量。"""

    # 审查 prompt 模板路径
    _PROMPT_PATH = Path(__file__).parent / "prompts" / "quiz_review.md"  # 审查 prompt 模板路径

    def __init__(self):
        # 延迟加载模板，先置为 None
        self._prompt_template: str | None = None

    # 加载审查 prompt 模板，文件缺失时降级为内置模板
    def _load_prompt(self) -> str:
        """加载审查 prompt 模板，文件不存在时使用内置降级模板。"""
        # 仅首次加载，缓存模板内容
        if self._prompt_template is None:
            try:
                self._prompt_template = self._PROMPT_PATH.read_text(encoding="utf-8")
            except FileNotFoundError:
                # 模板文件不存在则使用降级 prompt 并记录告警
                logger.warning("[QuizReview] Prompt file not found, using fallback")
                self._prompt_template = self._fallback_prompt()
        return self._prompt_template

    # 返回内置降级审查 prompt 模板
    def _fallback_prompt(self) -> str:
        """返回内置降级审查 prompt 模板。"""
        # 内置模板文本（模板占位符由 _build_messages 填充）
        return """# 任务
评判用户答案质量。

# 输入
- 题目类型: {{question_type}}
- 题目: {{question_content}}
- 标准答案: {{standard_answer}}
- 用户答案: {{user_answer}}
- 相关知识点: {{knowledge_points}}

# 评分规则
- 完全覆盖标准答案要点 → score >= 80
- 覆盖大部分要点但有遗漏 → score 60-79
- 严重偏离标准答案 → score < 60
- 分析题：过程正确但结果有误 → score 60-75
- 分析题：正确方法、关键中间结果和最终结果均正确，仅省略重复算术展开 → score >= 80
- 只有孤立结论且没有方法、公式或关键中间结果，才视为“仅写最终结果”

# 输出格式
JSON: {score: 0-100, feedback: "点评", improvement_hints: ["建议"]}"""

    # 将审查参数填充进 prompt 模板，构建 LLM 消息列表
    def _build_messages(
        self,
        question_type: str,
        question_content: str,
        standard_answer: str,
        user_answer: str,
        knowledge_points: list[str],
    ) -> list:
        """将审查参数填充到 prompt 模板中，构建 LLM 消息列表。"""
        # 加载模板并替换全部占位符
        prompt = self._load_prompt()
        filled = prompt.replace("{{question_type}}", question_type).replace(
            "{{question_content}}", question_content
        ).replace("{{standard_answer}}", standard_answer).replace(
            "{{user_answer}}", user_answer
        ).replace("{{knowledge_points}}", ", ".join(knowledge_points) if knowledge_points else "无")
        # 以 system 角色返回消息
        return [{"role": "system", "content": filled}]

    # 执行 AI 答案审查：调用 LLM 并返回评分与反馈
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

        # 调用 LLM 获取结构化审查结果，失败则降级
        try:
            result = await asyncio.wait_for(
                llm.ainvoke_json(  # 调用 LLM 结构化输出
                    QuizReviewOutput,
                    messages,
                ),
                timeout=QUIZ_REVIEW_TIMEOUT_SECONDS,
            )
            output = QuizReviewOutput.model_validate(result)  # Pydantic 校验
        except TimeoutError:
            logger.warning(
                "[QuizReview] LLM call timed out after %ss, using fallback",
                QUIZ_REVIEW_TIMEOUT_SECONDS,
            )
            output = self._fallback_review(user_answer, standard_answer)
        except Exception as e:
            logger.warning("[QuizReview] LLM call failed: %s, using fallback", e)
            output = self._fallback_review(user_answer, standard_answer)  # LLM 失败时降级为关键词匹配

        # 60 分以上判定为正确
        is_correct = output.score >= 60  # 60 分以上视为正确
        # 返回评分、正确性与前三条建议
        return {
            "score": output.score,
            "is_correct": is_correct,
            "feedback": output.feedback,
            "improvement_hints": output.improvement_hints[:3],
        }

    # LLM 失败时的关键词匹配降级判定
    def _fallback_review(self, user_answer: str, standard_answer: str) -> QuizReviewOutput:
        """LLM 失败时的 fallback 判定"""
        # 统一大小写并去除空白
        user_text = (user_answer or "").strip().upper()
        standard_text = (standard_answer or "").strip().upper()

        # 答案为空或过短直接判 0 分
        if not user_text or len(user_text) < 3:
            return QuizReviewOutput(
                score=0,
                feedback="答案内容过短或为空",
                improvement_hints=["请认真阅读题目并作答"],
            )

        # 按标准答案关键词计算覆盖率
        keywords = [k.strip() for k in standard_text.split(",") if k.strip()]
        covered = sum(1 for k in keywords if k in user_text)
        coverage = covered / max(len(keywords), 1)

        # 由覆盖率换算得分
        score = min(100, int(coverage * 80 + 20))
        if score >= 60:
            # 覆盖率达标：基本正确，提示核对细节
            feedback = "答案基本正确，但建议对照参考答案确认细节"
            hints = ["对照标准答案检查遗漏点"]
        else:
            # 覆盖率不足：明显不足，建议重做
            feedback = "答案存在明显不足，请参考标准答案"
            hints = ["仔细阅读题目要求", "参考标准答案重新作答"]

        # 返回降级判定结果
        return QuizReviewOutput(score=score, feedback=feedback, improvement_hints=hints)


# 题库与审查服务单例
quiz_bank_service = QuizBankService()
quiz_review_service = QuizReviewService()
