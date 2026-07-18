"""题库查询与 AI 答案审查服务。"""

from __future__ import annotations

import asyncio
import re

from pydantic import BaseModel, Field
from sqlalchemy import distinct, func, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import QuizQuestion
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.utils import parse_first_json_object
from app.quiz.schemas import QuizQuestionListResponse, QuizQuestionRead

# 创建模块级日志器
logger = get_logger(__name__)

# 单次 LLM 硬超时（秒）。分析题走短输出路径，不宜拖到 20s+
QUIZ_REVIEW_TIMEOUT_SECONDS = 12
# 批量评阅时限制同时进行的 LLM 调用数，避免打满上游配额
QUIZ_REVIEW_CONCURRENCY = 4
# 限制输出长度，显著降低生成时延（feedback 足够短即可）
QUIZ_REVIEW_MAX_TOKENS = 220
# 多题合并时，单次 LLM 最多评多少道分析题
QUIZ_REVIEW_MULTI_CHUNK_SIZE = 5
# 题干/答案过长时截断，降低预填时延
QUIZ_REVIEW_TEXT_LIMIT = 2500
_FILL_BLANK_TYPES = frozenset({"填空题", "fill_blank", "fill"})
# 多空分隔：不含 /|，二者保留给「同一空的多写法」
_ANSWER_PART_SPLIT = re.compile(r"[,，、;；\n]+")
_WHITESPACE_RE = re.compile(r"\s+")

# 精简评分规则（替代超长 quiz_review.md，保留关键给分口径）
_COMPACT_SCORING_RULES = """评分规则：
- 要点全覆盖 → score>=80；大部分覆盖有遗漏 → 60-79；严重偏离 → <60
- 分析题：过程正确结果有误 → 60-75
- 分析题：正确方法、关键中间结果和最终结果均正确，仅省略重复算术展开 → score>=80
- 分析题：结果与方法正确但缺少部分推导 → 70-85
- 分析题：只有孤立结论/数值，没有方法、公式或关键中间结果 → 40-55
- 不要求机械重复题干数据或逐项展开相同的算术代入
- 不得把已经给出算法顺序、公式或关键中间结果的答案认定为“仅写出最终结果”
- feedback 一句话；improvement_hints 最多 2 条，短句"""


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
    """AI 答案审查服务 — 使用 LLM 评判主观题答案质量。

    性能策略（分析题）：
    1. 精简 prompt，避免超长 system 模板
    2. 用 ainvoke_text + max_tokens 替代 ainvoke_json（去掉二次 repair）
    3. 批量接口把多道分析题合并成一次 LLM 调用
    """

    def __init__(self, concurrency: int = QUIZ_REVIEW_CONCURRENCY):
        self._concurrency = max(1, concurrency)
        # 进程内共享信号量：单题接口与批量接口共用，避免外部并发打满 LLM
        self._llm_semaphore = asyncio.Semaphore(self._concurrency)

    @staticmethod
    def _clip_text(text: str, limit: int = QUIZ_REVIEW_TEXT_LIMIT) -> str:
        raw = (text or "").strip()
        if len(raw) <= limit:
            return raw
        return raw[:limit] + "…(已截断)"

    # 构建单题精简审查 prompt（字符串，直接喂 ainvoke_text）
    def _build_messages(
        self,
        question_type: str,
        question_content: str,
        standard_answer: str,
        user_answer: str,
        knowledge_points: list[str],
    ) -> list:
        """构建轻量审查消息（短规则 + 题目输入）。

        返回 list[dict] 以兼容既有测试；真正调用时取 content 字符串。
        """
        kps = ", ".join(knowledge_points) if knowledge_points else "无"
        content = (
            "你是阅卷助手。对比标准答案给用户作答打分。\n"
            "只输出纯 JSON，不要 Markdown，不要解释：\n"
            '{"score":0,"feedback":"一句话点评","improvement_hints":["建议1"]}\n\n'
            f"{_COMPACT_SCORING_RULES}\n\n"
            f"题目类型：{question_type}\n"
            f"题目：{self._clip_text(question_content)}\n"
            f"标准答案：{self._clip_text(standard_answer)}\n"
            f"用户答案：{self._clip_text(user_answer)}\n"
            f"知识点：{kps}"
        )
        return [{"role": "user", "content": content}]

    def _build_multi_prompt(self, items: list[dict]) -> str:
        """构建多题合并审查 prompt，一次返回全部结果。"""
        blocks: list[str] = []
        for index, item in enumerate(items, start=1):
            qid = str(item.get("question_id") or f"q{index}")
            kps = item.get("knowledge_points") or []
            kps_text = ", ".join(str(x) for x in kps) if kps else "无"
            blocks.append(
                f"### 题{index}\n"
                f"question_id: {qid}\n"
                f"类型: {item.get('question_type') or '分析题'}\n"
                f"题目: {self._clip_text(str(item.get('question_content') or ''))}\n"
                f"标准答案: {self._clip_text(str(item.get('standard_answer') or ''))}\n"
                f"用户答案: {self._clip_text(str(item.get('user_answer') or ''))}\n"
                f"知识点: {kps_text}"
            )
        ids = ", ".join(str(item.get("question_id") or "") for item in items)
        return (
            "你是阅卷助手。对下列多道题分别评分。\n"
            "只输出纯 JSON，不要 Markdown：\n"
            '{"results":[{"question_id":"id","score":0,"feedback":"点评","improvement_hints":["建议"]}]}\n'
            f"results 必须包含全部题目且顺序一致，question_id 集合为：{ids}\n\n"
            f"{_COMPACT_SCORING_RULES}\n\n"
            + "\n\n".join(blocks)
        )

    @staticmethod
    def _normalize_answer_text(text: str) -> str:
        """规范化答案文本：去首尾空白、全角转半角、折叠空白、小写。"""
        if not text:
            return ""
        chars: list[str] = []
        for ch in text.strip():
            code = ord(ch)
            # 全角空格
            if code == 0x3000:
                chars.append(" ")
            # 全角 ASCII 范围
            elif 0xFF01 <= code <= 0xFF5E:
                chars.append(chr(code - 0xFEE0))
            else:
                chars.append(ch)
        normalized = "".join(chars).lower()
        return _WHITESPACE_RE.sub(" ", normalized).strip()

    @classmethod
    def _split_fill_parts(cls, text: str) -> list[str]:
        """按常见分隔符拆分多空填空答案。"""
        parts = [p.strip() for p in _ANSWER_PART_SPLIT.split(text or "") if p.strip()]
        return parts or ([text.strip()] if (text or "").strip() else [])

    @classmethod
    def _split_answer_alternatives(cls, text: str) -> list[str]:
        """拆分同一空的多种可接受写法（/ 或 |）。"""
        raw = (text or "").strip()
        if not raw:
            return []
        alts = [a.strip() for a in re.split(r"[/|]", raw) if a.strip()]
        return alts or [raw]

    @classmethod
    def _is_fill_blank_type(cls, question_type: str) -> bool:
        key = (question_type or "").strip()
        return key in _FILL_BLANK_TYPES or key.lower() in _FILL_BLANK_TYPES

    def _fill_blank_matches(self, standard_answer: str, user_answer: str) -> bool:
        """判断填空题用户答案是否与标准答案（含多空/多写法）匹配。"""
        user_norm = self._normalize_answer_text(user_answer)
        if not user_norm:
            return False

        # 整题等价（含标准答案多写法）
        for alt in self._split_answer_alternatives(standard_answer):
            if self._normalize_answer_text(alt) == user_norm:
                return True
        if self._normalize_answer_text(standard_answer) == user_norm:
            return True

        # 多空：按分隔符拆分后逐空比对（每空可有 / 多写法）
        user_parts = self._split_fill_parts(user_answer)
        std_parts = self._split_fill_parts(standard_answer)
        if len(user_parts) != len(std_parts) or len(std_parts) <= 1:
            return False

        for user_part, std_part in zip(user_parts, std_parts):
            user_part_norm = self._normalize_answer_text(user_part)
            if not any(
                self._normalize_answer_text(alt) == user_part_norm
                for alt in self._split_answer_alternatives(std_part)
            ):
                return False
        return True

    def _try_rule_review(
        self,
        *,
        question_type: str,
        standard_answer: str,
        user_answer: str,
    ) -> dict | None:
        """规则短路：空答 / 填空精确匹配可直接出分，无需调用 LLM。"""
        user_text = (user_answer or "").strip()
        if not user_text:
            return {
                "score": 0,
                "is_correct": False,
                "feedback": "本题未作答",
                "improvement_hints": ["请完成作答后再提交"],
            }

        if not self._is_fill_blank_type(question_type):
            return None

        if self._fill_blank_matches(standard_answer, user_answer):
            return {
                "score": 100,
                "is_correct": True,
                "feedback": "答案正确",
                "improvement_hints": [],
            }

        # 规范化后仍不匹配：直接判错，避免填空题占用 LLM 配额
        return {
            "score": 0,
            "is_correct": False,
            "feedback": "答案与标准答案不一致",
            "improvement_hints": ["请对照参考答案检查拼写、大小写与空格", "确认多空是否按顺序填写完整"],
        }

    def _to_result(self, output: QuizReviewOutput) -> dict:
        """将结构化输出转为 API 结果字典。"""
        return {
            "score": output.score,
            "is_correct": output.score >= 60,
            "feedback": output.feedback,
            "improvement_hints": (output.improvement_hints or [])[:2],
        }

    def _parse_review_output(self, raw: str) -> QuizReviewOutput:
        """从模型文本中解析单题评分 JSON。"""
        payload = parse_first_json_object(raw)
        # 兼容模型把单题包在 results 数组里的情况
        if isinstance(payload, dict) and "score" not in payload and isinstance(payload.get("results"), list):
            first = payload["results"][0] if payload["results"] else {}
            payload = first if isinstance(first, dict) else {}
        return QuizReviewOutput.model_validate(payload)

    async def _llm_review_one(
        self,
        *,
        question_type: str,
        question_content: str,
        standard_answer: str,
        user_answer: str,
        knowledge_points: list[str],
    ) -> QuizReviewOutput:
        """轻量 LLM 评阅：ainvoke_text + 限 max_tokens，失败走关键词 fallback。"""
        llm = get_llm()
        prompt = self._build_messages(
            question_type=question_type,
            question_content=question_content,
            standard_answer=standard_answer,
            user_answer=user_answer,
            knowledge_points=knowledge_points,
        )[0]["content"]
        try:
            async with self._llm_semaphore:
                raw = await asyncio.wait_for(
                    llm.ainvoke_text(
                        prompt,
                        temperature=0.1,
                        max_tokens=QUIZ_REVIEW_MAX_TOKENS,
                    ),
                    timeout=QUIZ_REVIEW_TIMEOUT_SECONDS,
                )
            return self._parse_review_output(raw)
        except TimeoutError:
            logger.warning(
                "[QuizReview] LLM timed out after %ss, using fallback",
                QUIZ_REVIEW_TIMEOUT_SECONDS,
            )
            return self._fallback_review(user_answer, standard_answer)
        except Exception as e:
            logger.warning("[QuizReview] LLM failed: %s, using fallback", e)
            return self._fallback_review(user_answer, standard_answer)

    async def _llm_review_multi(self, items: list[dict]) -> dict[str, dict] | None:
        """一次 LLM 评多道题。成功返回 question_id -> result；失败返回 None。"""
        if not items:
            return {}
        llm = get_llm()
        prompt = self._build_multi_prompt(items)
        # 多题输出稍放宽 token，但仍远小于默认 8192
        max_tokens = min(900, QUIZ_REVIEW_MAX_TOKENS * max(2, len(items)))
        try:
            async with self._llm_semaphore:
                raw = await asyncio.wait_for(
                    llm.ainvoke_text(
                        prompt,
                        temperature=0.1,
                        max_tokens=max_tokens,
                    ),
                    timeout=QUIZ_REVIEW_TIMEOUT_SECONDS + 4 * max(0, len(items) - 1),
                )
            payload = parse_first_json_object(raw)
            rows = payload.get("results") if isinstance(payload, dict) else None
            if not isinstance(rows, list) or not rows:
                raise ValueError("multi review missing results array")

            by_id: dict[str, dict] = {}
            for row in rows:
                if not isinstance(row, dict):
                    continue
                qid = str(row.get("question_id") or "").strip()
                if not qid:
                    continue
                output = QuizReviewOutput.model_validate(
                    {
                        "score": row.get("score", 0),
                        "feedback": row.get("feedback") or "",
                        "improvement_hints": row.get("improvement_hints") or [],
                    }
                )
                by_id[qid] = self._to_result(output)

            # 必须覆盖本批全部 id，否则降级为逐题
            expected = {str(item.get("question_id") or "") for item in items}
            if not expected.issubset(by_id.keys()):
                missing = expected - by_id.keys()
                raise ValueError(f"multi review missing ids: {missing}")
            return by_id
        except Exception as e:
            logger.warning("[QuizReview] multi review failed, fallback per-item: %s", e)
            return None

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
        """执行 AI 答案审查 — 规则短路优先，否则调用轻量 LLM 评判。"""
        logger.info("[QuizReview] 开始审查: question_type=%s", question_type)
        rule_result = self._try_rule_review(
            question_type=question_type,
            standard_answer=standard_answer,
            user_answer=user_answer,
        )
        if rule_result is not None:
            return rule_result

        output = await self._llm_review_one(
            question_type=question_type,
            question_content=question_content,
            standard_answer=standard_answer,
            user_answer=user_answer,
            knowledge_points=knowledge_points or [],
        )
        return self._to_result(output)

    async def review_batch(self, items: list[dict]) -> list[dict]:
        """批量审查主观题。

        - 空答/填空：规则短路
        - 多道分析题：优先合并成一次 LLM 调用（chunk）
        - 合并失败：退回有限并发逐题
        """
        if not items:
            return []

        logger.info("[QuizReview] 批量审查开始: item_count=%s", len(items))
        results: list[dict | None] = [None] * len(items)
        llm_jobs: list[tuple[int, dict]] = []

        for index, item in enumerate(items):
            question_type = str(item.get("question_type") or "")
            standard_answer = str(item.get("standard_answer") or "")
            user_answer = str(item.get("user_answer") or "")
            rule = self._try_rule_review(
                question_type=question_type,
                standard_answer=standard_answer,
                user_answer=user_answer,
            )
            if rule is not None:
                results[index] = {
                    "question_id": str(item.get("question_id") or ""),
                    **rule,
                }
            else:
                llm_jobs.append((index, item))

        # 多题合并：按 chunk 调用，显著减少分析题总时延
        if llm_jobs:
            chunk_size = max(1, QUIZ_REVIEW_MULTI_CHUNK_SIZE)
            pending: list[tuple[int, dict]] = []

            async def _grade_pending(batch: list[tuple[int, dict]]) -> None:
                if not batch:
                    return
                if len(batch) == 1:
                    index, item = batch[0]
                    graded = await self.review(
                        question_type=str(item.get("question_type") or ""),
                        question_content=str(item.get("question_content") or ""),
                        standard_answer=str(item.get("standard_answer") or ""),
                        user_answer=str(item.get("user_answer") or ""),
                        knowledge_points=list(item.get("knowledge_points") or []),
                    )
                    results[index] = {
                        "question_id": str(item.get("question_id") or ""),
                        **graded,
                    }
                    return

                multi = await self._llm_review_multi([item for _, item in batch])
                if multi is not None:
                    for index, item in batch:
                        qid = str(item.get("question_id") or "")
                        results[index] = {"question_id": qid, **multi[qid]}
                    return

                # 合并失败：并发逐题
                async def _one(index: int, item: dict) -> None:
                    graded = await self.review(
                        question_type=str(item.get("question_type") or ""),
                        question_content=str(item.get("question_content") or ""),
                        standard_answer=str(item.get("standard_answer") or ""),
                        user_answer=str(item.get("user_answer") or ""),
                        knowledge_points=list(item.get("knowledge_points") or []),
                    )
                    results[index] = {
                        "question_id": str(item.get("question_id") or ""),
                        **graded,
                    }

                await asyncio.gather(*[_one(i, it) for i, it in batch])

            for job in llm_jobs:
                pending.append(job)
                if len(pending) >= chunk_size:
                    await _grade_pending(pending)
                    pending = []
            if pending:
                await _grade_pending(pending)

        return [
            item
            if item is not None
            else {
                "question_id": str(items[i].get("question_id") or ""),
                "score": 0,
                "is_correct": False,
                "feedback": "评阅失败",
                "improvement_hints": [],
            }
            for i, item in enumerate(results)
        ]

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
