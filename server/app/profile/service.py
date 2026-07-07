"""学习者画像服务 — 全局画像 CRUD、周度学习摘要、LLM 推理与评分。

架构：基础信息（school/major/grade 等）存储在 User 表，由 onboarding 填写；
画像维度（7 维度）存储在 UserProfileDimension 表，由 LLM 推理；
评分汇总存储在 UserProfile 表。
周度学习摘要（WeeklyLearningDigest）作为评分的缓冲证据层。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.messages import HumanMessage
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.infra.database import session_scope
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import (
    ChatLongTermMemory,
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

_NEXT_MONDAY_MINUS_ONE_MICRO: timedelta = timedelta(microseconds=1)


def _utc_week_range(now: datetime | None = None) -> tuple[datetime, datetime]:
    """计算给定时间所在自然周（周一 00:00 ~ 周日 23:59:59.999999）的 UTC 范围。"""
    now = now or datetime.now(timezone.utc)
    weekday = now.weekday()
    week_start = (now - timedelta(days=weekday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=7) - _NEXT_MONDAY_MINUS_ONE_MICRO
    return week_start, week_end


def _format_week_label(week_start: datetime, week_end: datetime) -> str:
    iso_year, iso_week, _ = week_start.isocalendar()
    start_str = week_start.strftime("%Y-%m-%d")
    end_str = week_end.strftime("%Y-%m-%d")
    return f"{iso_year}-W{iso_week:02d}: {start_str} ~ {end_str}"


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


# ── ProfileService ────────────────────────────────────────────────────

class ProfileService:
    """学习者画像服务 — CRUD、LLM 推理与评分。

    基础信息存储在 User 表，画像维度存储在 UserProfileDimension 表，
    评分汇总存储在 UserProfile 表。
    """

    def __init__(self, *, module: str = "mentor") -> None:
        self.module = module
        self.llm = get_llm()

    async def get_profile(
        self,
        *,
        user_id: int,
        db: AsyncSession | None = None,
    ) -> UserProfile:
        """获取用户画像记录，不存在则创建。"""
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

        if db is None:
            async with session_scope() as db:
                return await _upsert(db)
        return await _upsert(db)

    async def get_dimensions(
        self,
        *,
        user_id: int,
        db: AsyncSession | None = None,
    ) -> dict[str, dict[str, Any]]:
        """获取用户画像维度明细，返回 {dimension_key: {value, evidence}} 字典。"""
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

        await db.flush()
        await db.commit()
        logger.info(
            "[ProfileService] 画像维度持久化完成: user_id=%s 写入维度数=%s keys=%s",
            user_id, len(dimensions_patch), list(dimensions_patch.keys()),
        )

    async def get_or_create_weekly_digest(
        self,
        *,
        user_id: int,
        db: AsyncSession,
        now: datetime | None = None,
    ) -> WeeklyLearningDigest:
        """获取或生成本周学习摘要（总是重新生成）。"""
        week_start, week_end = _utc_week_range(now)

        user_row = (await db.exec(select(User).where(User.id == user_id))).first()
        username = user_row.username if user_row and user_row.username else "用户"

        logger.info(
            "[ProfileService] 周摘要构建: user_id=%s week=%s",
            user_id, _format_week_label(week_start, week_end),
        )

        result = await build_digest(
            db=db,
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            username=username,
        )

        now_utc = datetime.now(timezone.utc)
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

        digest = (
            await db.exec(
                select(WeeklyLearningDigest).where(
                    WeeklyLearningDigest.user_id == user_id,
                    WeeklyLearningDigest.module == self.module,
                    WeeklyLearningDigest.week_start == week_start,
                )
            )
        ).first()

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

    async def build_profile_markdown(self, *, user_id: int) -> str:
        """将画像维度 + User 基础信息转为结构化 Markdown。"""
        async with session_scope() as db:
            user = (await db.exec(select(User).where(User.id == user_id))).first()
            dimensions = await self.get_dimensions(user_id=user_id, db=db)

        base_info = _user_base_info_dict(user) if user else {}
        lines: list[str] = ["# 学习者画像"]

        # 1. 基础信息
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

        # 2. 知识层维度
        lines.append("\n## 知识层维度")
        for dim_key in KNOWLEDGE_DIMENSIONS:
            dim_data = dimensions.get(dim_key, {})
            dim_name = DIMENSION_NAMES.get(dim_key, dim_key)
            value = dim_data.get("value", "")
            lines.append(f"\n### {dim_name}")
            lines.append(value if value else "暂无明确画像")

        # 3. 认知层维度
        lines.append("\n## 认知层维度")
        for dim_key in COGNITIVE_DIMENSIONS:
            dim_data = dimensions.get(dim_key, {})
            dim_name = DIMENSION_NAMES.get(dim_key, dim_key)
            value = dim_data.get("value", "")
            lines.append(f"\n### {dim_name}")
            lines.append(value if value else "暂无明确画像")

        return "\n".join(lines)

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

        # 查询 school_level（根据学校名反查院校层次）
        school_name = payload.get("school")
        if school_name:
            school = (await db.exec(select(School).where(School.name == school_name).limit(1))).first()
            user.school_level = school.level if school and school.level else None
            logger.info(
                "[ProfileService] onboarding school_level 解析: user_id=%s school=%s school_level=%s",
                user_id, school_name, user.school_level,
            )

        # 写入 base_info 字段到 User 表
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

        # 标记 onboarding 已完成
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

        # 确保画像记录存在
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

                logger.info("[ProfileService] onboarding 调用LLM推理: user_id=%s", user_id)
                prompt = prompts.get("profile").render(
                    "onboarding",
                    onboarding_data=json.dumps(base_info, ensure_ascii=False),
                )
                resp = await self.llm.ainvoke_json(
                    ProfileDimensionsPatch,
                    [HumanMessage(content=prompt)],
                )

                dims_summary = {k: v.value[:50] if isinstance(v, DimensionValue) else str(v)[:50]
                                for k, v in resp.dimensions_patch.items()}
                logger.info("[ProfileService] onboarding LLM推理结果: user_id=%s dimensions_patch=%s",
                            user_id, dims_summary)

                await self.save_dimensions(
                    user_id=user_id,
                    dimensions_patch=resp.dimensions_patch,
                    db=db,
                )
                logger.info(
                    "[ProfileService] onboarding 画像维度已落库: user_id=%s 维度数=%s keys=%s",
                    user_id, len(resp.dimensions_patch), list(resp.dimensions_patch.keys()),
                )

            score_result = await self.score_profile(user_id=user_id)
            logger.info("[ProfileService] onboarding 推理+评分完成: user_id=%s dimensions_updated=%s overall_score=%s",
                         user_id, list(dims_summary.keys()), score_result.get("overall_score"))

            return score_result
        except Exception:
            logger.exception("[ProfileService] onboarding 推理+评分失败: user_id=%s", user_id)
            return {"inference_ok": False, "reason": "llm_error"}

    async def infer_profile_from_tutoring(self, *, user_id: int, session_id: str) -> dict[str, Any]:
        """从辅导对话推理更新全局画像。"""
        logger.info("[ProfileService] 全局画像更新开始: user_id=%s session_id=%s", user_id, session_id)
        async with session_scope() as db:
            dimensions = await self.get_dimensions(user_id=user_id, db=db)

            from app.chat.memory.service import get_chat_memory_service
            memory_service = get_chat_memory_service()
            recent_dialogue, _, _ = await memory_service._build_dialogue_since(
                db=db, user_id=user_id, session_id=session_id, after_message_id=0, limit=20,
            )

            if not recent_dialogue or not recent_dialogue.strip():
                logger.info("[ProfileService] 全局画像: 无对话内容可提取，跳过更新")
                profile = await self.get_profile(user_id=user_id, db=db)
                return {
                    "profile_updated": False,
                    "updated_at": profile.updated_at,
                    "reason": "no_dialogue",
                }

            ltm = (
                await db.exec(
                    select(ChatLongTermMemory).where(
                        ChatLongTermMemory.user_id == user_id,
                    )
                )
            ).first()
            long_term_memory = ltm.memory_markdown if ltm and ltm.memory_markdown else ""

            logger.info("[ProfileService] 全局画像: recent_dialogue长度=%s long_term_memory长度=%s",
                         len(recent_dialogue), len(long_term_memory))

            prompt = prompts.get("profile").render(
                "global_update",
                profile_json=json.dumps(dimensions, ensure_ascii=False),
                recent_dialogue=recent_dialogue,
                long_term_memory=long_term_memory,
            )
            resp = await self.llm.ainvoke_json(
                GlobalTutoringInferenceOutput,
                [HumanMessage(content=prompt)],
            )

            dims_summary = {k: v.value[:50] if isinstance(v, DimensionValue) else str(v)[:50]
                            for k, v in resp.dimensions_patch.items()}
            logger.info("[ProfileService] 全局画像 LLM推理结果: should_update=%s dimensions_patch=%s",
                         resp.should_update, dims_summary)

            updated = False
            if resp.should_update and resp.dimensions_patch:
                await self.save_dimensions(
                    user_id=user_id,
                    dimensions_patch=resp.dimensions_patch,
                    db=db,
                )
                updated = True

        if updated:
            score_result = await self.score_profile(user_id=user_id)
            logger.info("[ProfileService] 全局画像评分刷新完成: user_id=%s overall_score=%s",
                         user_id, score_result.get("overall_score"))

        profile = await self.get_profile(user_id=user_id)
        return {
            "profile_updated": updated,
            "updated_at": profile.updated_at,
        }

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

            # score 模板仅依据文字画像（base_info + dimensions）打分
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

            scores = sanitize_score_output(resp)
            profile.overall_score = scores["overall_score"]
            profile.scored_at = datetime.now(timezone.utc)
            profile.updated_at = datetime.now(timezone.utc)

            # 同步维度得分到 UserProfileDimension
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


_profile_service_cache: dict[str, ProfileService] = {}


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
