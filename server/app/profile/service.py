"""学习者画像服务 — 用户基础信息、JIT 维度合成与 Markdown 构建。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import session_scope
from app.infra.llm import LLM
from app.infra.logging import get_logger
from app.infra.models import School, User
from app.profile.types import (
    COGNITIVE_DIMENSIONS,
    DIMENSION_NAMES,
    KNOWLEDGE_DIMENSIONS,
)

logger = get_logger(__name__)


def _user_base_info_dict(user: User) -> dict[str, Any]:
    """从 User ORM 对象提取基础信息字典。"""
    return {
        "school": user.school or "",
        "school_level": user.school_level or "",
        "major": user.major or "",
        "grade": user.grade or "",
        "daily_study_time": user.daily_study_time or "",
        "global_learning_goal": user.global_learning_goal or "",
        "programming_languages": user.programming_languages or [],
        "courses": user.courses or [],
        "foundational_level": user.foundational_level or "",
        "learning_style": user.learning_style or "",
        "content_depth": user.content_depth or "",
        "weak_points": user.weak_points or [],
    }


async def _synthesize_jit_dimensions(
    user_id: int,
    db: AsyncSession,
    existing_dims: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """即时装配画像维度，保证前端雷达图与看板具备实时基线数据。"""
    user = (await db.exec(select(User).where(User.id == user_id))).first()
    if not user:
        return existing_dims

    result = dict(existing_dims)

    # 1. 基础水平映射 (knowledge_level)
    if "knowledge_level" not in result:
        level_map = {
            "beginner": ("初学基础阶段，正在系统建立学科知识体系", 45),
            "entry": ("入门提升阶段，具备常用概念基础与实践兴趣", 60),
            "proficient": ("熟练进阶阶段，能独立分析并解决复合技术问题", 80),
            "master": ("精通阶段，具备深厚理论底蕴与敏锐架构认知", 95),
        }
        val, sc = level_map.get(user.foundational_level or "", ("基础掌握阶段，正在推进各知识板块学习", 55))
        evidence = []
        if user.foundational_level:
            evidence.append(f"学员自评基础水平：{user.foundational_level}")
        if user.major:
            evidence.append(f"专业学科：{user.major} ({user.grade or '在读'})")
        if user.programming_languages:
            evidence.append(f"掌握语言：{'、'.join(user.programming_languages)}")
        result["knowledge_level"] = {"value": val, "evidence": evidence, "score": sc}

    # 2. 认知风格 (cognitive_style)
    if "cognitive_style" not in result:
        style_map = {
            "theory_first": "偏好概念推导与理论先行，重视系统化逻辑完整性",
            "practice_first": "实践优先，偏好从动手代码与实操中反推原理",
            "case_driven": "案例驱动，偏好结合经典业务场景与实战工程理解",
        }
        val = style_map.get(user.learning_style or "", "理论与实践并重，偏好结合案例循序渐进")
        evidence = []
        if user.learning_style:
            evidence.append(f"学员偏好风格：{user.learning_style}")
        if user.content_depth:
            evidence.append(f"内容深度期望：{user.content_depth}")
        result["cognitive_style"] = {"value": val, "evidence": evidence, "score": 70}

    # 3. 薄弱知识点 (weak_knowledge_points)
    if "weak_knowledge_points" not in result:
        weaks = list(user.weak_points or [])
        val = f"重点攻坚薄弱项：{'、'.join(weaks)}" if weaks else "当前暂无显著记录的薄弱知识点"
        evidence = [f"自评待攻关知识点：{w}" for w in weaks]
        sc = 50 if weaks else 80
        result["weak_knowledge_points"] = {"value": val, "evidence": evidence, "score": sc}

    # 4. 目标导向 (learning_goal_type)
    if "learning_goal_type" not in result:
        val = user.global_learning_goal or "系统化专业能力提升"
        evidence = [f"设定全局目标：{val}"] if user.global_learning_goal else []
        result["learning_goal_type"] = {"value": val, "evidence": evidence, "score": 75}

    # 5. 知识缺口模式 (knowledge_gap_pattern)
    if "knowledge_gap_pattern" not in result:
        val = "基础概念掌握良好，复杂场景与综合变体需强化" if user.weak_points else "知识结构完整，保持稳步进阶"
        result["knowledge_gap_pattern"] = {"value": val, "evidence": ["基于初始学情基准分析"], "score": 68}

    # 6. 难题耐受度 (difficulty_tolerance)
    if "difficulty_tolerance" not in result:
        sc = 75 if user.content_depth == "systematic_deep" else 65
        val = "对深度复杂主题具有较好探索意愿" if sc >= 70 else "建议以循序渐进梯级难度推进"
        result["difficulty_tolerance"] = {"value": val, "evidence": [f"内容深度偏好：{user.content_depth or '适中'}"], "score": sc}

    # 7. 自主纠错能力 (self_correction_ability)
    if "self_correction_ability" not in result:
        result["self_correction_ability"] = {
            "value": "在答题与互动中能结合解析快速纠偏",
            "evidence": ["日常自适应学习基线"],
            "score": 72,
        }

    return result


class ProfileService:
    """学习者画像服务 — 用户基础信息、JIT 维度合成与 Markdown 构建。"""

    def __init__(self, *, module: str = "mentor") -> None:
        self.module = module
        self.llm = LLM(temperature=0.1)

    async def get_profile(
        self,
        *,
        user_id: int,
        db: AsyncSession | None = None,
    ) -> User:
        """获取用户对象，不存在则抛出异常。"""
        logger.info("[ProfileService] get_profile — user={}", user_id)

        async def _query(session: AsyncSession) -> User:
            user = await session.get(User, user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            return user

        if db is None:
            async with session_scope() as session:
                return await _query(session)
        return await _query(db)

    async def get_dimensions(
        self,
        *,
        user_id: int,
        db: AsyncSession | None = None,
    ) -> dict[str, dict[str, Any]]:
        """即时装配用户画像维度明细。"""
        logger.info("[ProfileService] get_dimensions — user={}", user_id)

        async def _query(session: AsyncSession) -> dict[str, dict[str, Any]]:
            return await _synthesize_jit_dimensions(user_id, session, {})

        if db is None:
            async with session_scope() as session:
                return await _query(session)
        return await _query(db)

    async def build_profile_markdown(self, *, user_id: int) -> str:
        """将画像维度 + User 基础信息转为结构化 Markdown。"""
        logger.info("[ProfileService] build_profile_markdown — user={}", user_id)
        async with session_scope() as db:
            user = (await db.exec(select(User).where(User.id == user_id))).first()
            dimensions = await self.get_dimensions(user_id=user_id, db=db)

        base_info = _user_base_info_dict(user) if user else {}
        lines: list[str] = ["# 学习者画像"]

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

        lines.append("\n## 知识层维度")
        for dim_key in KNOWLEDGE_DIMENSIONS:
            dim_data = dimensions.get(dim_key, {})
            dim_name = DIMENSION_NAMES.get(dim_key, dim_key)
            value = dim_data.get("value", "")
            lines.append(f"\n### {dim_name}")
            lines.append(value if value else "暂无明确画像")

        lines.append("\n## 认知层维度")
        for dim_key in COGNITIVE_DIMENSIONS:
            dim_data = dimensions.get(dim_key, {})
            dim_name = DIMENSION_NAMES.get(dim_key, dim_key)
            value = dim_data.get("value", "")
            lines.append(f"\n### {dim_name}")
            lines.append(value if value else "暂无明确画像")

        strategy = user.guidance_strategy if user and user.guidance_strategy else None
        if not strategy:
            from app.evaluation.guidance import DEFAULT_GUIDANCE_STRATEGY
            strategy = DEFAULT_GUIDANCE_STRATEGY
        lines.append("\n## 当前自适应辅导策略")
        lines.append(f"- 本期结论：{strategy.get('conclusion')}")
        lines.append(f"- 建议单次学习时长：{strategy.get('recommended_session_minutes')} 分钟")
        lines.append(f"- 推荐辅导风格：{strategy.get('tutoring_style')}")

        focus_topics = strategy.get("focus_topics", [])
        topics_str = "、".join(focus_topics) if focus_topics else "暂无"
        lines.append(f"- 重点学习主题：{topics_str}")
        lines.append(f"- 策略制定依据：{strategy.get('reason')}")

        return "\n".join(lines)

    async def save_onboarding_info(
        self,
        *,
        user_id: int,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """保存首次 onboarding 的完整资料，并将该用户标记为已完成引导。"""
        return await self._save_base_info(
            user_id=user_id,
            payload=payload,
            db=db,
            complete_onboarding=True,
        )

    async def save_profile_info(
        self,
        *,
        user_id: int,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """保存个人中心展示的基础资料，不覆盖首次引导偏好。"""
        return await self._save_base_info(
            user_id=user_id,
            payload=payload,
            db=db,
            complete_onboarding=False,
        )

    async def _save_base_info(
        self,
        *,
        user_id: int,
        payload: dict[str, Any],
        db: AsyncSession,
        complete_onboarding: bool,
    ) -> dict[str, Any]:
        """写入基础资料；只有首次 onboarding 可以写偏好并完成引导。"""
        update_source = "onboarding" if complete_onboarding else "profile"
        logger.info("[ProfileService] {} 写入开始: user_id={}", update_source, user_id)

        user = (await db.exec(select(User).where(User.id == user_id))).first()
        if not user:
            logger.error("[ProfileService] {} 写入失败，用户不存在: user_id={}", update_source, user_id)
            raise ValueError(f"User {user_id} not found")

        school_name = payload.get("school")
        if school_name:
            school = (await db.exec(select(School).where(School.name == school_name).limit(1))).first()
            user.school_level = school.level if school and school.level else None

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
        if complete_onboarding:
            if payload.get("foundational_level") is not None:
                user.foundational_level = payload["foundational_level"] or None
            if payload.get("learning_style") is not None:
                user.learning_style = payload["learning_style"] or None
            if payload.get("content_depth") is not None:
                user.content_depth = payload["content_depth"] or None
            if payload.get("weak_points") is not None:
                user.weak_points = payload["weak_points"]
            user.onboarding_completed = True
        user.updated_at = datetime.now(timezone.utc)

        db.add(user)
        await db.flush()
        await db.commit()
        await db.refresh(user)

        return {
            "user_id": user.id,
            "school": user.school,
            "major": user.major,
            "updated_at": user.updated_at,
        }


_profile_service_cache: dict[str, ProfileService] = {}


def get_profile_service(*, module: str = "mentor") -> ProfileService:
    """获取指定模块的画像服务单例（带缓存）。"""
    if module not in _profile_service_cache:
        _profile_service_cache[module] = ProfileService(module=module)
    return _profile_service_cache[module]


__all__ = [
    "ProfileService",
    "get_profile_service",
    "_user_base_info_dict",
]
