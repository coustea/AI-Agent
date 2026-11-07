"""学习者画像服务 — 全局画像 CRUD、LLM 推理与评分。

架构：基础信息（school/major/grade 等）存储在 User 表，由 onboarding 填写；
画像维度（7 维度）存储在 UserProfileDimension 表，由 LLM 推理；
评分汇总存储在 UserProfile 表。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from sqlalchemy.dialects.mysql import insert as mysql_insert

from pathlib import Path

from app.infra.database import session_scope
from app.infra.llm import HumanMessage, LLM, load_prompt
from app.infra.logging import get_logger
from app.infra.models import (
    School,
    User,
    UserProfile,
    UserProfileDimension,
)
from app.profile.types import (
    ALL_DIMENSIONS,
    DIMENSION_NAMES,
    KNOWLEDGE_DIMENSIONS,
    COGNITIVE_DIMENSIONS,
    DimensionValue,
    ProfileDimensionsPatch,
    ProfileScoreOutput,
)

logger = get_logger(__name__)

_PROFILE_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


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


def sanitize_score_output(raw: ProfileScoreOutput) -> dict[str, Any]:
    """对打分输出进行后置验证与清洗。"""
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


async def _synthesize_jit_dimensions(
    user_id: int,
    db: AsyncSession,
    existing_dims: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """即时装配缺失画像维度，保证前端雷达图与看板在无后台 LLM 预跑时也有真实基线数据呈现。"""
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
    """学习者画像服务 — CRUD、LLM 推理与评分。"""

    def __init__(self, *, module: str = "mentor") -> None:
        self.module = module
        self.llm = LLM(temperature=0.1)

    async def get_profile(
        self,
        *,
        user_id: int,
        db: AsyncSession | None = None,
    ) -> UserProfile:
        """获取用户画像记录，不存在则创建。"""
        logger.info("[ProfileService] get_profile — user=%d", user_id)

        async def _upsert(db: AsyncSession) -> UserProfile:
            now = datetime.now(timezone.utc)
            # 已存在则不改动任何列（ON DUPLICATE KEY UPDATE user_id = user_id 是空操作）
            stmt = mysql_insert(UserProfile).values(
                user_id=user_id,
                overall_score=0,
                scored_at=None,
                created_at=now,
                updated_at=now,
            ).on_duplicate_key_update(user_id=user_id)
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
        """获取用户画像维度明细；缺失维度由基线学情即时（JIT）装配补全。"""
        logger.info("[ProfileService] get_dimensions — user=%d", user_id)

        async def _query(db: AsyncSession) -> dict[str, dict[str, Any]]:
            rows = (
                await db.exec(
                    select(UserProfileDimension).where(
                        UserProfileDimension.user_id == user_id,
                    )
                )
            ).all()
            existing = {
                row.dimension_key: {
                    "value": row.value or "",
                    "evidence": row.evidence or [],
                    "score": row.score if row.score is not None else 0,
                }
                for row in rows
            }
            return await _synthesize_jit_dimensions(user_id, db, existing)

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

    async def build_profile_markdown(self, *, user_id: int) -> str:
        """将画像维度 + User 基础信息转为结构化 Markdown。"""
        logger.info("[ProfileService] build_profile_markdown — user=%d", user_id)
        async with session_scope() as db:
            user = (await db.exec(select(User).where(User.id == user_id))).first()
            dimensions = await self.get_dimensions(user_id=user_id, db=db)
            profile = (await db.exec(select(UserProfile).where(UserProfile.user_id == user_id))).first()

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

        strategy = profile.guidance_strategy if profile and profile.guidance_strategy else None
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
        logger.info(
            "[ProfileService] %s 写入开始: user_id=%s payload=%s",
            update_source,
            user_id,
            {k: payload.get(k) for k in (
                "school", "major", "grade", "daily_study_time",
                "global_learning_goal", "programming_languages", "courses",
                "foundational_level", "learning_style", "content_depth", "weak_points",
            )},
        )

        user = (await db.exec(select(User).where(User.id == user_id))).first()
        if not user:
            logger.error("[ProfileService] %s 写入失败，用户不存在: user_id=%s", update_source, user_id)
            raise ValueError(f"User {user_id} not found")

        school_name = payload.get("school")
        if school_name:
            school = (await db.exec(select(School).where(School.name == school_name).limit(1))).first()
            user.school_level = school.level if school and school.level else None
            logger.info(
                "[ProfileService] %s school_level 解析: user_id=%s school=%s school_level=%s",
                update_source,
                user_id, school_name, user.school_level,
            )

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

        logger.info(
            "[ProfileService] %s 基础信息已提交: user_id=%s school=%s major=%s grade=%s "
            "daily_study_time=%s goal=%s courses_count=%s languages_count=%s onboarding_completed=%s",
            update_source,
            user.id, user.school, user.major, user.grade,
            user.daily_study_time, user.global_learning_goal,
            len(user.courses or []), len(user.programming_languages or []), user.onboarding_completed,
        )

        reloaded = (await db.exec(select(User).where(User.id == user_id))).first()
        if reloaded is None:
            logger.error("[ProfileService] %s 落库校验失败，回读为空: user_id=%s", update_source, user_id)
        else:
            logger.info(
                "[ProfileService] %s 落库校验通过: user_id=%s school=%s major=%s grade=%s "
                "courses=%s programming_languages=%s onboarding_completed=%s",
                update_source,
                user_id, reloaded.school, reloaded.major, reloaded.grade,
                reloaded.courses, reloaded.programming_languages, reloaded.onboarding_completed,
            )

        await self.get_profile(user_id=user_id, db=db)

        result = {
            "user_id": user.id,
            "school": user.school,
            "major": user.major,
            "updated_at": user.updated_at,
        }
        logger.info(
            "[ProfileService] %s 写入完成: user_id=%s updated_at=%s",
            update_source,
            user.id, user.updated_at,
        )
        return result

    async def infer_profile_from_onboarding(self, *, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """从 onboarding 信息推理 7 维度画像并评分。"""
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
                prompt = load_prompt(
                    _PROFILE_PROMPTS_DIR / "onboarding.md",
                    onboarding_data=json.dumps(base_info, ensure_ascii=False),
                )
                resp = await self.llm.json(
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

    async def infer_profile_from_events(self, *, user_id: int, range_days: int = 7) -> dict[str, Any]:
        """从近期学习事件推理 7 维度文字画像并持久化。

        流程：读取近期学习事件 → to_markdown() → LLM 推理 → save_dimensions()
        """
        try:
            logger.info("[ProfileService] 事件推理开始: user_id=%s range_days=%d", user_id, range_days)

            async with session_scope() as db:
                # 1. 读取近期学习事件并转为 Markdown
                from app.evaluation.recent_events import get_recent_learning_context
                context = await get_recent_learning_context(
                    db,
                    user_id=user_id,
                    range_days=range_days,
                    event_limit=None,
                )
                events_md = context.to_markdown()
                logger.info(
                    "[ProfileService] 事件MD生成完成: user_id=%s events=%d sessions=%d md_len=%d",
                    user_id, len(context.events), len(context.sessions), len(events_md),
                )

                # 2. 构建现有画像 JSON 作为 LLM 输入（同时记录更新前的值用于对比）
                user = (await db.exec(select(User).where(User.id == user_id))).first()
                dimensions = await self.get_dimensions(user_id=user_id, db=db)
                before_values = {k: v.get("value", "")[:60] for k, v in dimensions.items()}
                base_info = _user_base_info_dict(user) if user else {}
                profile_text = json.dumps(
                    {"base_info": base_info, "dimensions": dimensions},
                    ensure_ascii=False,
                )

                # 3. 调用 LLM 推理
                logger.info("[ProfileService] 事件推理调用LLM: user_id=%s", user_id)
                prompt = load_prompt(
                    _PROFILE_PROMPTS_DIR / "events_inference.md",
                    events_md=events_md,
                    profile_text=profile_text,
                )
                resp = await self.llm.json(
                    ProfileDimensionsPatch,
                    [HumanMessage(content=prompt)],
                )

                # 记录每个维度的更新前后对比
                for dim_key, dim_value in resp.dimensions_patch.items():
                    old_val = before_values.get(dim_key, "")
                    new_val = dim_value.value[:60]
                    changed = old_val != new_val
                    logger.info(
                        "[ProfileService] 文字画像维度更新: user_id=%s dim=%s changed=%s "
                        "before='%s' after='%s' evidence_count=%d",
                        user_id, dim_key, changed, old_val, new_val, len(dim_value.evidence),
                    )

                # 4. 持久化维度更新
                await self.save_dimensions(
                    user_id=user_id,
                    dimensions_patch=resp.dimensions_patch,
                    db=db,
                )

                # 汇总：哪些维度实际发生了变化
                changed_dims = [
                    k for k, v in resp.dimensions_patch.items()
                    if before_values.get(k, "") != v.value[:60]
                ]
                unchanged_dims = [
                    k for k, v in resp.dimensions_patch.items()
                    if before_values.get(k, "") == v.value[:60]
                ]
                logger.info(
                    "[ProfileService] 文字画像推理完成: user_id=%s changed_dims=%s unchanged_dims=%s",
                    user_id, changed_dims, unchanged_dims,
                )

            return {"inference_ok": True, "updated_dimensions": list(resp.dimensions_patch.keys())}
        except Exception:
            logger.exception("[ProfileService] 事件推理失败: user_id=%s", user_id)
            return {"inference_ok": False, "reason": "llm_error"}

    async def score_profile(self, *, user_id: int) -> dict[str, Any]:
        """依据文字画像对 7 维度重新评分。"""
        logger.info("[ProfileService] 全局评分刷新开始: user_id=%s", user_id)
        async with session_scope() as db:
            profile = await self.get_profile(user_id=user_id, db=db)
            dimensions = await self.get_dimensions(user_id=user_id, db=db)
            user = (await db.exec(select(User).where(User.id == user_id))).first()
            base_info = _user_base_info_dict(user) if user else {}

            # 记录评分前的分数用于对比
            before_overall = profile.overall_score
            before_scores = {k: v.get("score", 0) for k, v in dimensions.items()}

            profile_text = json.dumps(
                {"base_info": base_info, "dimensions": dimensions},
                ensure_ascii=False,
            )
            prompt = load_prompt(
                _PROFILE_PROMPTS_DIR / "score.md",
                profile_text=profile_text,
            )

            resp = await self.llm.json(
                ProfileScoreOutput,
                [HumanMessage(content=prompt)],
            )

            scores = sanitize_score_output(resp)
            profile.overall_score = scores["overall_score"]
            profile.scored_at = datetime.now(timezone.utc)
            profile.updated_at = datetime.now(timezone.utc)

            now = datetime.now(timezone.utc)
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
                    dim_row.updated_at = now
                    db.add(dim_row)
                else:
                    # 维度行不存在时自动创建
                    new_dim = UserProfileDimension(
                        user_id=user_id,
                        dimension_key=dim_key,
                        value="",
                        evidence=[],
                        score=dim_score,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(new_dim)

            db.add(profile)
            await db.flush()

            # 记录每个维度的评分变化
            for dim_key, new_score in scores.get("dimension_scores", {}).items():
                old_score = before_scores.get(dim_key, 0)
                diff = new_score - old_score
                logger.info(
                    "[ProfileService] 分数画像维度更新: user_id=%s dim=%s before=%d after=%d diff=%+d",
                    user_id, dim_key, old_score, new_score, diff,
                )
            overall_diff = scores["overall_score"] - before_overall
            logger.info(
                "[ProfileService] 分数画像更新完成: user_id=%s overall_before=%d overall_after=%d diff=%+d",
                user_id, before_overall, scores["overall_score"], overall_diff,
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
