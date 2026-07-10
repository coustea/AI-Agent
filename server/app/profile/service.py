"""学习者画像服务 — 全局画像 CRUD、周度学习摘要、LLM 推理与评分。

架构：基础信息（school/major/grade 等）存储在 User 表，由 onboarding 填写；
画像维度（7 维度）存储在 UserProfileDimension 表，由 LLM 推理；
评分汇总存储在 UserProfile 表。
周度学习摘要（WeeklyLearningDigest）作为文字画像更新的缓冲层：由
infer_profile_from_digest 消费——GET /profile 懒加载触发时构建本周摘要，
再据此推理更新文字画像，避免逐事件频繁更新导致画像失准。
"""

# 画像服务：基础信息/维度/评分的持久化、周摘要缓冲与 LLM 推理
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.messages import HumanMessage
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from sqlalchemy import case, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.infra.database import session_scope
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import (
    LearningEvent,
    School,
    User,
    UserProfile,
    UserProfileDimension,
    WeeklyLearningDigest,
)
from app.profile.weekly import build_digest
from app.profile.types import (
    ALL_DIMENSIONS,
    DIMENSION_NAMES,
    KNOWLEDGE_DIMENSIONS,
    COGNITIVE_DIMENSIONS,
    DimensionValue,
    ProfileDimensionsPatch,
    GlobalTutoringInferenceOutput,
    ProfileScoreOutput,
)
from app.infra.prompts import prompts

logger = get_logger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────

# 用于计算周结束时刻（周日 23:59:59.999999）的微小偏移量
_NEXT_MONDAY_MINUS_ONE_MICRO: timedelta = timedelta(microseconds=1)


# 计算给定时间所在自然周（周一~周日）的 UTC 起止范围
def _utc_week_range(now: datetime | None = None) -> tuple[datetime, datetime]:
    """计算给定时间所在自然周（周一 00:00 ~ 周日 23:59:59.999999）的 UTC 范围。"""
    now = now or datetime.now(timezone.utc)
    weekday = now.weekday()
    week_start = (now - timedelta(days=weekday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=7) - _NEXT_MONDAY_MINUS_ONE_MICRO
    return week_start, week_end


# 将周起止时间格式化为可读的周标签（ISO 周 + 日期区间）
def _format_week_label(week_start: datetime, week_end: datetime) -> str:
    iso_year, iso_week, _ = week_start.isocalendar()
    start_str = week_start.strftime("%Y-%m-%d")
    end_str = week_end.strftime("%Y-%m-%d")
    return f"{iso_year}-W{iso_week:02d}: {start_str} ~ {end_str}"


# 从 User ORM 提取基础信息字典，供 prompt 与响应使用
def _user_base_info_dict(user: User) -> dict[str, Any]:
    """从 User ORM 对象提取基础信息字典，供 LLM prompt 和 API 响应使用。"""
    return {
        "school": user.school or "",
        "school_level": user.school_level or "",
        "major": user.major or "",
        "grade": user.grade or "",
        "daily_study_time": user.daily_study_time or "",
        "global_learning_goal": user.global_learning_goal or "",
        "programming_languages": user.programming_languages or [],
        "courses": user.courses or [],
    }


# 对 LLM 评分输出做清洗：截断到 0~100 并取均值计算总分
def sanitize_score_output(raw: ProfileScoreOutput) -> dict[str, Any]:
    """对打分输出进行后置验证与清洗 — 仅处理 7 维度分数，overall_score 取均值。"""
    scores = {}
    for key in ALL_DIMENSIONS:
        raw_score = raw.dimension_scores.get(key, 0)
        if not isinstance(raw_score, (int, float)):
            try:
                raw_score = float(raw_score)
            except (ValueError, TypeError):
                raw_score = 0.0
        scores[key] = max(0, min(100, round(float(raw_score))))

    overall = round(sum(scores.values()) / len(ALL_DIMENSIONS))

    return {
        "overall_score": overall,
        "dimension_scores": scores,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


# ── 懒加载触发阈值 ─────────────────────────────────────────────────────

# 文字画像懒加载刷新的加权事件点数阈值
PROFILE_REFRESH_EVENT_THRESHOLD = 10
"""文字画像懒加载刷新的加权事件阈值（点）。

加权规则：quiz_submitted / path_node_completed / path_quiz_answered = 3，
resource_generated = 2，其他 = 1。强信号事件少但权重大，弱信号事件多但权重小。
"""

# 权重为 3 的强信号事件类型（测验、路径节点完成、路径测验）
_WEIGHT_3_EVENTS: tuple[str, ...] = (
    "quiz_submitted",
    "path_node_completed",
    "path_quiz_answered",
)


# 计算 since 之后新增学习事件的加权点数（用于懒加载刷新判据）
async def weighted_new_event_points(
    db: AsyncSession, user_id: int, since: datetime
) -> int:
    """计算 ``since`` 之后新增学习事件的加权点数。

    用于 GET /profile 懒加载触发判据：当点数 ≥ PROFILE_REFRESH_EVENT_THRESHOLD
    或 profile.updated_at 早于本周周一时，后台触发 infer_profile_from_digest。
    """
    weight_expr = case(
        (LearningEvent.event_type.in_(_WEIGHT_3_EVENTS), 3),
        (LearningEvent.event_type == "resource_generated", 2),
        else_=1,
    )
    # 按事件权重求和得到加权点数
    stmt = select(func.coalesce(func.sum(weight_expr), 0)).where(
        LearningEvent.user_id == user_id,
        LearningEvent.created_at > since,
    )
    result = (await db.exec(stmt)).one()
    return int(result)


# ── ProfileService ────────────────────────────────────────────────────

# 学习者画像服务：CRUD、周摘要与 LLM 推理评分
class ProfileService:
    """学习者画像服务 — CRUD、LLM 推理与评分。

    基础信息存储在 User 表，画像维度存储在 UserProfileDimension 表，
    评分汇总存储在 UserProfile 表。
    """

    def __init__(self, *, module: str = "mentor") -> None:
        self.module = module
        self.llm = get_llm()

    # 获取用户画像记录，不存在则创建
    async def get_profile(
        self,
        *,
        user_id: int,
        db: AsyncSession | None = None,
    ) -> UserProfile:
        """获取用户画像记录，不存在则创建。"""
        logger.info("[ProfileService] get_profile — user=%d", user_id)
        # 内层 upsert：无记录时插入默认画像，否则读取现有记录
        async def _upsert(db: AsyncSession) -> UserProfile:
            now = datetime.now(timezone.utc)
            stmt = pg_insert(UserProfile).values(
                user_id=user_id,
                overall_score=0,
                scored_at=None,
                created_at=now,
                updated_at=now,
            ).on_conflict_do_nothing(
                constraint="uq_user_profiles_user",
            )
            await db.exec(stmt)  # type: ignore[arg-type]
            await db.flush()

            profile = (
                await db.exec(
                    select(UserProfile).where(
                        UserProfile.user_id == user_id,
                    )
                )
            ).first()

            if profile is None:
                profile = UserProfile(
                    user_id=user_id,
                    overall_score=0,
                )
                db.add(profile)
                await db.flush()

            await db.commit()
            return profile

        # 未传入会话则使用独立事务上下文
        if db is None:
            async with session_scope() as db:
                return await _upsert(db)
        return await _upsert(db)

    # 获取用户画像维度明细（key → {value, evidence, score}）
    async def get_dimensions(
        self,
        *,
        user_id: int,
        db: AsyncSession | None = None,
    ) -> dict[str, dict[str, Any]]:
        """获取用户画像维度明细，返回 {dimension_key: {value, evidence}} 字典。"""
        logger.info("[ProfileService] get_dimensions — user=%d", user_id)
        # 内层查询：读取全部维度行并组装为字典
        async def _query(db: AsyncSession) -> dict[str, dict[str, Any]]:
            rows = (
                await db.exec(
                    select(UserProfileDimension).where(
                        UserProfileDimension.user_id == user_id,
                    )
                )
            ).all()
            return {
                row.dimension_key: {
                    "value": row.value or "",
                    "evidence": row.evidence or [],
                    "score": row.score if row.score is not None else 0,
                }
                for row in rows
            }

        if db is None:
            async with session_scope() as db:
                return await _query(db)
        return await _query(db)

    # 保存画像维度增量更新（已存在则更新，否则插入）
    async def save_dimensions(
        self,
        *,
        user_id: int,
        dimensions_patch: dict[str, DimensionValue],
        db: AsyncSession,
    ) -> None:
        """保存画像维度增量更新到 UserProfileDimension 表。"""
        now = datetime.now(timezone.utc)
        for dim_key, dim_value in dimensions_patch.items():
            # 仅处理合法的 7 维度键
            if dim_key not in ALL_DIMENSIONS:
                continue

            existing = (
                await db.exec(
                    select(UserProfileDimension).where(
                        UserProfileDimension.user_id == user_id,
                        UserProfileDimension.dimension_key == dim_key,
                    )
                )
            ).first()

            # 已存在则就地更新，否则新建维度行
            if existing:
                existing.value = dim_value.value.strip()
                existing.evidence = [item.strip() for item in dim_value.evidence if item.strip()]
                existing.updated_at = now
                db.add(existing)
            else:
                new_dim = UserProfileDimension(
                    user_id=user_id,
                    dimension_key=dim_key,
                    value=dim_value.value.strip(),
                    evidence=[item.strip() for item in dim_value.evidence if item.strip()],
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_dim)

        # 批量刷新并提交维度变更
        await db.flush()
        await db.commit()
        logger.info(
            "[ProfileService] 画像维度持久化完成: user_id=%s 写入维度数=%s keys=%s",
            user_id, len(dimensions_patch), list(dimensions_patch.keys()),
        )

    # 获取或生成本周学习摘要（已存在且无新事件则复用）
    async def get_or_create_weekly_digest(
        self,
        *,
        user_id: int,
        db: AsyncSession,
        now: datetime | None = None,
    ) -> WeeklyLearningDigest:
        """获取或生成本周学习摘要。

        优化：当本周摘要已存在且无新增 LearningEvent 时直接复用，
        避免每次触发都重新聚合 5 个模块的数据。
        """
        week_start, week_end = _utc_week_range(now)

        # 1) 尝试复用已存在的摘要
        existing = (
            await db.exec(
                select(WeeklyLearningDigest).where(
                    WeeklyLearningDigest.user_id == user_id,
                    WeeklyLearningDigest.module == self.module,
                    WeeklyLearningDigest.week_start == week_start,
                )
            )
        ).first()

        if existing is not None:
            # 检查自摘要更新后是否有新增学习事件
            has_new = (
                await db.exec(
                    select(func.count())
                    .select_from(LearningEvent)
                    .where(
                        LearningEvent.user_id == user_id,
                        LearningEvent.created_at > existing.updated_at,
                    )
                )
            ).one()
            # 无新事件则直接复用，避免重复聚合
            if has_new == 0:
                logger.info(
                    "[ProfileService] 复用现有周摘要: user_id=%s week=%s updated_at=%s",
                    user_id, _format_week_label(week_start, week_end), existing.updated_at,
                )
                return existing
            logger.info(
                "[ProfileService] 有新事件，重建周摘要: user_id=%s week=%s",
                user_id, _format_week_label(week_start, week_end),
            )

        # 2) 无可用摘要或有新事件 → 重建
        user_row = (await db.exec(select(User).where(User.id == user_id))).first()
        username = user_row.username if user_row and user_row.username else "用户"

        logger.info(
            "[ProfileService] 周摘要构建: user_id=%s week=%s",
            user_id, _format_week_label(week_start, week_end),
        )

        # 调用周摘要构建器聚合 5 个模块数据
        result = await build_digest(
            db=db,
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            username=username,
        )

        now_utc = datetime.now(timezone.utc)
        # 以 user+module+week 为主键 upsert 周摘要
        upsert_stmt = pg_insert(WeeklyLearningDigest).values(
            user_id=user_id,
            module=self.module,
            week_start=week_start,
            week_end=week_end,
            digest_markdown=result.markdown,
            courses_active=result.courses_active,
            stats=result.stats,
            created_at=now_utc,
            updated_at=now_utc,
        ).on_conflict_do_update(
            constraint="uq_weekly_digest_user_module_week",
            set_={
                "digest_markdown": result.markdown,
                "courses_active": result.courses_active,
                "stats": result.stats,
                "updated_at": now_utc,
            },
        )
        await db.exec(upsert_stmt)  # type: ignore[arg-type]
        await db.flush()

        # upsert 后回读确认落库
        digest = (
            await db.exec(
                select(WeeklyLearningDigest).where(
                    WeeklyLearningDigest.user_id == user_id,
                    WeeklyLearningDigest.module == self.module,
                    WeeklyLearningDigest.week_start == week_start,
                )
            )
        ).first()

        # 兜底：回读为空时以内存对象返回
        if digest is None:
            logger.warning(
                "[ProfileService] 周摘要 upsert+select 意外返回 None: user_id=%s week=%s",
                user_id, _format_week_label(week_start, week_end),
            )
            digest = WeeklyLearningDigest(
                user_id=user_id,
                module=self.module,
                week_start=week_start,
                week_end=week_end,
                digest_markdown=result.markdown,
                courses_active=result.courses_active,
                stats=result.stats,
            )

        logger.info(
            "[ProfileService] 周摘要构建完成: user_id=%s stats=%s markdown长度=%s",
            user_id, digest.stats, len(digest.digest_markdown),
        )
        return digest

    # 将画像维度 + 基础信息转为结构化 Markdown 文本
    async def build_profile_markdown(self, *, user_id: int) -> str:
        """将画像维度 + User 基础信息转为结构化 Markdown。"""
        logger.info("[ProfileService] build_profile_markdown — user=%d", user_id)
        async with session_scope() as db:
            user = (await db.exec(select(User).where(User.id == user_id))).first()
            dimensions = await self.get_dimensions(user_id=user_id, db=db)

        base_info = _user_base_info_dict(user) if user else {}
        lines: list[str] = ["# 学习者画像"]

        # 1. 基础信息段落
        if base_info:
            lines.append("\n## 基础信息")
            info_items: list[str] = []
            if base_info.get("school"):
                info_items.append(f"- 学校：{base_info['school']}")
            if base_info.get("school_level"):
                info_items.append(f"- 学校层次：{base_info['school_level']}")
            if base_info.get("major"):
                info_items.append(f"- 专业：{base_info['major']}")
            if base_info.get("grade"):
                info_items.append(f"- 年级：{base_info['grade']}")
            if base_info.get("daily_study_time"):
                info_items.append(f"- 每日学习时长：{base_info['daily_study_time']}")
            if base_info.get("global_learning_goal"):
                info_items.append(f"- 全局学习目标：{base_info['global_learning_goal']}")
            if base_info.get("programming_languages"):
                langs = "、".join(base_info["programming_languages"])
                info_items.append(f"- 掌握的编程语言：{langs}")
            if base_info.get("courses"):
                courses = "、".join(base_info["courses"])
                info_items.append(f"- 学习的课程：{courses}")
            if info_items:
                lines.extend(info_items)
            else:
                lines.append("- 暂无基础信息")

        # 2. 知识层维度段落
        lines.append("\n## 知识层维度")
        for dim_key in KNOWLEDGE_DIMENSIONS:
            dim_data = dimensions.get(dim_key, {})
            dim_name = DIMENSION_NAMES.get(dim_key, dim_key)
            value = dim_data.get("value", "")
            lines.append(f"\n### {dim_name}")
            lines.append(value if value else "暂无明确画像")

        # 3. 认知层维度段落
        lines.append("\n## 认知层维度")
        for dim_key in COGNITIVE_DIMENSIONS:
            dim_data = dimensions.get(dim_key, {})
            dim_name = DIMENSION_NAMES.get(dim_key, dim_key)
            value = dim_data.get("value", "")
            lines.append(f"\n### {dim_name}")
            lines.append(value if value else "暂无明确画像")

        return "\n".join(lines)

    # 保存 onboarding 基本信息到 User 表（同步提交并回读校验）
    async def save_onboarding_info(
        self,
        *,
        user_id: int,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """保存 onboarding 基本信息 — 直接写入 User 表（同步提交）。"""
        logger.info(
            "[ProfileService] onboarding 写入开始: user_id=%s payload=%s",
            user_id,
            {k: payload.get(k) for k in (
                "school", "major", "grade", "daily_study_time",
                "global_learning_goal", "programming_languages", "courses",
            )},
        )

        user = (await db.exec(select(User).where(User.id == user_id))).first()
        if not user:
            logger.error("[ProfileService] onboarding 写入失败，用户不存在: user_id=%s", user_id)
            raise ValueError(f"User {user_id} not found")

        # 根据学校名反查院校层次（school_level）
        school_name = payload.get("school")
        if school_name:
            school = (await db.exec(select(School).where(School.name == school_name).limit(1))).first()
            user.school_level = school.level if school and school.level else None
            logger.info(
                "[ProfileService] onboarding school_level 解析: user_id=%s school=%s school_level=%s",
                user_id, school_name, user.school_level,
            )

        # 将 base_info 各字段写入 User 表
        if payload.get("school") is not None:
            user.school = payload["school"]
        if payload.get("major") is not None:
            user.major = payload["major"]
        if payload.get("grade") is not None:
            user.grade = payload["grade"]
        if payload.get("daily_study_time") is not None:
            user.daily_study_time = payload["daily_study_time"]
        if payload.get("global_learning_goal") is not None:
            user.global_learning_goal = payload["global_learning_goal"]
        if payload.get("programming_languages") is not None:
            user.programming_languages = payload["programming_languages"]
        if payload.get("courses") is not None:
            user.courses = payload["courses"]

        # 标记 onboarding 已完成并更新时间戳
        user.is_first_login = True
        user.updated_at = datetime.now(timezone.utc)

        db.add(user)
        await db.flush()
        await db.commit()
        await db.refresh(user)

        logger.info(
            "[ProfileService] onboarding 基础信息已提交: user_id=%s school=%s major=%s grade=%s "
            "daily_study_time=%s goal=%s courses_count=%s languages_count=%s is_first_login=%s",
            user.id, user.school, user.major, user.grade,
            user.daily_study_time, user.global_learning_goal,
            len(user.courses or []), len(user.programming_languages or []), user.is_first_login,
        )

        # 提交后回读校验，确认真正落库（便于排查“没存进数据库”的问题）
        reloaded = (await db.exec(select(User).where(User.id == user_id))).first()
        if reloaded is None:
            logger.error("[ProfileService] onboarding 落库校验失败，回读为空: user_id=%s", user_id)
        else:
            logger.info(
                "[ProfileService] onboarding 落库校验通过: user_id=%s school=%s major=%s grade=%s "
                "courses=%s programming_languages=%s is_first_login=%s",
                user_id, reloaded.school, reloaded.major, reloaded.grade,
                reloaded.courses, reloaded.programming_languages, reloaded.is_first_login,
            )

        # 确保对应画像记录存在
        await self.get_profile(user_id=user_id, db=db)

        result = {
            "user_id": user.id,
            "school": user.school,
            "major": user.major,
            "updated_at": user.updated_at,
        }
        logger.info(
            "[ProfileService] onboarding 写入完成: user_id=%s updated_at=%s",
            user.id, user.updated_at,
        )
        return result

    # 从 onboarding 信息推理 7 维度画像并评分（后台异步任务）
    async def infer_profile_from_onboarding(self, *, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """从 onboarding 信息推理 7 维度画像并评分（后台异步任务）。"""
        try:
            logger.info("[ProfileService] onboarding LLM推理开始: user_id=%s", user_id)

            async with session_scope() as db:
                user = (await db.exec(select(User).where(User.id == user_id))).first()
                base_info = _user_base_info_dict(user) if user else payload.copy()
                logger.info(
                    "[ProfileService] onboarding 推理输入: user_id=%s school=%s major=%s "
                    "courses_count=%s languages_count=%s",
                    user_id, base_info.get("school"), base_info.get("major"),
                    len(base_info.get("courses", [])), len(base_info.get("programming_languages", [])),
                )

                # 调用 LLM 根据 onboarding 信息推理画像维度补丁
                logger.info("[ProfileService] onboarding 调用LLM推理: user_id=%s", user_id)
                prompt = prompts.get("profile").render(
                    "onboarding",
                    onboarding_data=json.dumps(base_info, ensure_ascii=False),
                )
                resp = await self.llm.ainvoke_json(
                    ProfileDimensionsPatch,
                    [HumanMessage(content=prompt)],
                )

                # 仅取前 50 字符用于日志摘要，避免过长
                dims_summary = {k: v.value[:50] if isinstance(v, DimensionValue) else str(v)[:50]
                                for k, v in resp.dimensions_patch.items()}
                logger.info("[ProfileService] onboarding LLM推理结果: user_id=%s dimensions_patch=%s",
                            user_id, dims_summary)

                # 保存推理出的维度补丁
                await self.save_dimensions(
                    user_id=user_id,
                    dimensions_patch=resp.dimensions_patch,
                    db=db,
                )
                logger.info(
                    "[ProfileService] onboarding 画像维度已落库: user_id=%s 维度数=%s keys=%s",
                    user_id, len(resp.dimensions_patch), list(resp.dimensions_patch.keys()),
                )

            # 维度落库后触发评分
            score_result = await self.score_profile(user_id=user_id)
            logger.info("[ProfileService] onboarding 推理+评分完成: user_id=%s dimensions_updated=%s overall_score=%s",
                         user_id, list(dims_summary.keys()), score_result.get("overall_score"))

            return score_result
        except Exception:
            logger.exception("[ProfileService] onboarding 推理+评分失败: user_id=%s", user_id)
            return {"inference_ok": False, "reason": "llm_error"}

    # 从本周周概要推理更新文字画像（GET /profile 懒加载触发）
    async def infer_profile_from_digest(self, *, user_id: int) -> dict[str, Any]:
        """从本周周概要推理更新文字画像（懒加载触发）。

        流程：获取当前 profile → 构建/复用本周摘要 →
        若摘要未变更（digest.updated_at <= profile.updated_at）则跳过 LLM，
        否则 LLM 推理（digest_update）→
        若 should_update 则 save_dimensions + score_profile（唯一评分通道之一）；
        否则轻量 bump updated_at 避免重复触发，不动 scored_at 以保持不变式。
        """
        try:
            logger.info("[ProfileService] 周概要画像推理开始: user_id=%s", user_id)
            should_update = False
            async with session_scope() as db:
                profile = await self.get_profile(user_id=user_id, db=db)
                digest = await self.get_or_create_weekly_digest(user_id=user_id, db=db)

                # 摘要未变更 → 跳过 LLM，仅刷新 updated_at 避免重复触发
                if digest.updated_at <= profile.updated_at:
                    logger.info(
                        "[ProfileService] 摘要未变更，跳过 LLM: user_id=%s digest_updated=%s profile_updated=%s",
                        user_id, digest.updated_at, profile.updated_at,
                    )
                    profile.updated_at = datetime.now(timezone.utc)
                    db.add(profile)
                    await db.commit()
                    return {"profile_updated": False, "reason": "digest_unchanged"}

                # 读取现有维度，与周摘要一起交给 LLM 判断是否更新
                dimensions = await self.get_dimensions(user_id=user_id, db=db)

                prompt = prompts.get("profile").render(
                    "digest_update",
                    current_profile_json=json.dumps(dimensions, ensure_ascii=False),
                    weekly_digest_markdown=digest.digest_markdown,
                )
                resp = await self.llm.ainvoke_json(
                    GlobalTutoringInferenceOutput,
                    [HumanMessage(content=prompt)],
                )
                logger.info(
                    "[ProfileService] 周概要推理结果: should_update=%s",
                    resp.should_update,
                )

                # LLM 判定需要更新则保存维度补丁
                if resp.should_update and resp.dimensions_patch:
                    await self.save_dimensions(
                        user_id=user_id,
                        dimensions_patch=resp.dimensions_patch,
                        db=db,
                    )
                    should_update = True

            # 维度有更新则重新评分
            if should_update:
                score_result = await self.score_profile(user_id=user_id)
                logger.info(
                    "[ProfileService] 周概要推理+评分完成: user_id=%s overall_score=%s",
                    user_id, score_result.get("overall_score"),
                )
            else:
                # 无变更：仅刷新 updated_at 避免重复触发（不动 scored_at）
                async with session_scope() as db:
                    profile_bump = await self.get_profile(user_id=user_id, db=db)
                    profile_bump.updated_at = datetime.now(timezone.utc)
                    db.add(profile_bump)
                    await db.commit()
                logger.info(
                    "[ProfileService] 周概要推理无变更，已 bump updated_at: user_id=%s",
                    user_id,
                )

            return {"profile_updated": should_update}
        except Exception:
            logger.exception("[ProfileService] 周概要推理失败: user_id=%s", user_id)
            return {"profile_updated": False, "reason": "error"}

    # 仅依据文字画像（base_info + dimensions）对 7 维度重新评分
    async def score_profile(self, *, user_id: int) -> dict[str, Any]:
        """仅依据文字画像（base_info + dimensions）对 7 维度重新评分。"""
        logger.info("[ProfileService] 全局评分刷新开始: user_id=%s", user_id)
        async with session_scope() as db:
            profile = await self.get_profile(user_id=user_id, db=db)
            dimensions = await self.get_dimensions(user_id=user_id, db=db)
            user = (await db.exec(select(User).where(User.id == user_id))).first()
            base_info = _user_base_info_dict(user) if user else {}

            logger.info(
                "[ProfileService] 全局评分: dimensions数=%s",
                len(dimensions),
            )

            # 将文字画像拼接为 prompt，调用 LLM 打分
            profile_text = json.dumps(
                {"base_info": base_info, "dimensions": dimensions},
                ensure_ascii=False,
            )
            prompt = prompts.get("profile").render(
                "score",
                profile_text=profile_text,
            )

            resp = await self.llm.ainvoke_json(
                ProfileScoreOutput,
                [HumanMessage(content=prompt)],
            )

            logger.info(
                "[ProfileService] 全局评分 LLM原始结果: dimension_scores=%s",
                resp.dimension_scores,
            )

            # 清洗 LLM 结果并写回总体分与评分时间
            scores = sanitize_score_output(resp)
            profile.overall_score = scores["overall_score"]
            profile.scored_at = datetime.now(timezone.utc)
            profile.updated_at = datetime.now(timezone.utc)

            # 同步各维度得分到维度表
            for dim_key, dim_score in scores.get("dimension_scores", {}).items():
                dim_row = (
                    await db.exec(
                        select(UserProfileDimension).where(
                            UserProfileDimension.user_id == user_id,
                            UserProfileDimension.dimension_key == dim_key,
                        )
                    )
                ).first()
                if dim_row:
                    dim_row.score = dim_score
                    dim_row.updated_at = datetime.now(timezone.utc)
                    db.add(dim_row)

            db.add(profile)
            await db.flush()

            logger.info(
                "[ProfileService] 全局评分刷新完成: user_id=%s overall_score=%s dimension_scores=%s",
                user_id, scores.get("overall_score"), scores.get("dimension_scores"),
            )

            return scores


# 模块级画像服务单例缓存
_profile_service_cache: dict[str, ProfileService] = {}


# 获取指定模块的画像服务单例（带缓存，避免重复构建 LLM 客户端）
def get_profile_service(*, module: str = "mentor") -> ProfileService:
    """获取指定模块的画像服务单例（带缓存）。"""
    if module not in _profile_service_cache:
        _profile_service_cache[module] = ProfileService(module=module)
    return _profile_service_cache[module]


__all__ = [
    "ProfileService",
    "get_profile_service",
    "sanitize_score_output",
    "_user_base_info_dict",
]
