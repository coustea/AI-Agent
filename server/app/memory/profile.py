"""Profile building and update logic."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, UserLongTermMemory, UserProfile, UserProfileHistory
from app.memory.types import (
    ALL_DIMENSIONS,
    ConcurrentUpdateError,
    DAILY_STUDY_TIME_TO_PACE,
    DIALOGUE_ROLES,
    DIMENSION_NAMES,
    FOUNDATION_LEVEL_TO_KNOWLEDGE_LEVEL,
    GOAL_TO_PROFILE_GOAL,
    MESSAGE_EXPIRE_DAYS,
    ONBOARDING_OPTIONAL_FIELDS,
    ONBOARDING_REQUIRED_COURSE_FIELDS,
    ONBOARDING_REQUIRED_FIELDS,
    OPTIONAL_COURSE_FIELDS,
    PROFILE_MIN_COVERAGE,
    PROFILE_UPDATE_INTERVALS,
    RESOURCE_PREFERENCE_TO_WEIGHT_KEY,
    RESOURCE_WEIGHT_DEFAULTS,
    TutoringInferenceOutput,
    confidence_label,
    days_ago,
    dedupe_strings,
    has_profile_signal,
    make_default_profile_json,
    make_default_score_json,
    now,
    slugify,
)
from app.prompts import registry

logger = get_logger(__name__)


def normalize_onboarding(data: dict[str, Any] | None) -> dict[str, Any]:
    src = data or {}
    result: dict[str, Any] = {}

    for field in ONBOARDING_REQUIRED_FIELDS + ONBOARDING_OPTIONAL_FIELDS:
        if field == "courses":
            result["courses"] = _normalize_courses(src.get("courses"))
            continue
        if field in {"resource_preference", "programming_languages"}:
            raw = src.get(field, [])
            values = raw if isinstance(raw, list) else [raw]
            result[field] = dedupe_strings([str(item) for item in values])
            continue
        text = str(src.get(field) or "").strip()
        result[field] = text or None

    result.setdefault("school_level", str(src.get("school_level") or "").strip() or None)
    return result


def _normalize_courses(raw_courses: Any) -> list[dict[str, Any]]:
    values = raw_courses if isinstance(raw_courses, list) else []
    courses: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in values[:3]:
        if not isinstance(item, dict):
            continue
        course_name = str(item.get("course") or "").strip()
        if not course_name or course_name in seen:
            continue
        seen.add(course_name)
        course_data: dict[str, Any] = {}
        for field in ONBOARDING_REQUIRED_COURSE_FIELDS + OPTIONAL_COURSE_FIELDS:
            if field == "weak_points":
                raw_points = item.get("weak_points", [])
                points = raw_points if isinstance(raw_points, list) else [raw_points]
                course_data["weak_points"] = dedupe_strings([str(point) for point in points])
            else:
                text = str(item.get(field) or "").strip()
                course_data[field] = text or None
        course_data["course"] = course_name
        courses.append(course_data)
    return courses


def is_onboarding_complete(data: dict[str, Any] | None) -> bool:
    normalized = normalize_onboarding(data)
    for field in ONBOARDING_REQUIRED_FIELDS:
        if field == "courses":
            if not normalized.get("courses"):
                return False
        elif not normalized.get(field):
            return False
    return all(
        course.get("course") and course.get("foundation_level")
        for course in normalized.get("courses", [])
    )


def _now_iso() -> str:
    return now().isoformat()


def _clamp_confidence(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except (TypeError, ValueError):
        return 0.0


def _avg_confidence(profile_json: dict[str, Any]) -> float:
    values: list[float] = []
    global_profile = ((profile_json.get("learning_profile") or {}).get("global_profile") or {})
    course_profiles = ((profile_json.get("learning_profile") or {}).get("course_profiles") or [])

    for key in ALL_DIMENSIONS:
        field = global_profile.get(key)
        if isinstance(field, dict) and field.get("value") is not None:
            values.append(float(field.get("confidence") or 0))

    for profile in course_profiles:
        for field in (profile or {}).values():
            if isinstance(field, dict) and field.get("value") is not None:
                values.append(float(field.get("confidence") or 0))

    return round(sum(values) / len(values), 2) if values else 0.0


def _compute_coverage(profile_json: dict[str, Any]) -> int:
    coverage_units = 0
    target_units = len(ALL_DIMENSIONS)
    global_profile = ((profile_json.get("learning_profile") or {}).get("global_profile") or {})
    for key in (
        "major_background",
        "student_stage",
        "learning_pace",
        "cognitive_style",
        "resource_preference_weight",
        "practice_profile",
    ):
        field = global_profile.get(key)
        if isinstance(field, dict) and field.get("value") not in (None, [], {}):
            coverage_units += 1

    first_course = (((profile_json.get("learning_profile") or {}).get("course_profiles") or []) or [None])[0]
    if first_course:
        for key in (
            "course_context",
            "knowledge_level",
            "learning_goal_type",
            "weak_knowledge_points",
        ):
            field = first_course.get(key)
            if isinstance(field, dict) and field.get("value") not in (None, [], {}):
                coverage_units += 1

    return round(coverage_units / target_units * 100) if target_units else 0


def _make_field(value: Any, source: str, confidence: float, evidence: list[str] | None = None) -> dict[str, Any]:
    return {
        "value": value,
        "source": source,
        "confidence": _clamp_confidence(confidence),
        "evidence": dedupe_strings(evidence or []),
        "updated_at": _now_iso(),
    }


def _summarize_field(field: dict[str, Any] | None) -> tuple[str | None, list[str], float]:
    if not isinstance(field, dict):
        return None, [], 0.0
    value = field.get("value")
    if value in (None, [], {}):
        return None, [], 0.0
    if isinstance(value, list):
        if value and isinstance(value[0], dict):
            summary = "；".join(str(item.get("name") or item.get("course") or item) for item in value[:3])
        else:
            summary = "、".join(str(item) for item in value[:3])
    elif isinstance(value, dict):
        if "course" in value and "topic" in value:
            topic = value.get("topic")
            summary = f"{value.get('course')} / {topic}" if topic else str(value.get("course"))
        elif "preferred_languages" in value:
            langs = value.get("preferred_languages") or []
            summary = "、".join(str(lang) for lang in langs[:3]) or json.dumps(value, ensure_ascii=False)
        else:
            summary = json.dumps(value, ensure_ascii=False)
    else:
        summary = str(value)
    return summary, dedupe_strings(field.get("evidence") or []), _clamp_confidence(field.get("confidence"))


def render_profile_markdown(profile_json: dict[str, Any]) -> str:
    lines = ["# 用户画像"]
    base_info = profile_json.get("base_info") or {}
    learning_profile = profile_json.get("learning_profile") or {}
    global_profile = learning_profile.get("global_profile") or {}
    course_profiles = learning_profile.get("course_profiles") or []
    profile_meta = profile_json.get("profile_meta") or {}

    if base_info:
        lines.extend(
            [
                "",
                "## 冷启动基础信息",
                f"- 学校: {base_info.get('school') or '未填写'}",
                f"- 专业 / 年级: {(base_info.get('major') or '未填写')} / {(base_info.get('grade') or '未填写')}",
                f"- 每日学习时长: {base_info.get('daily_study_time') or '未填写'}",
                f"- 当前目标: {base_info.get('global_learning_goal') or '未填写'}",
            ]
        )

    lines.append("")
    lines.append("## 全局画像")
    for key in (
        "major_background",
        "student_stage",
        "learning_pace",
        "cognitive_style",
        "resource_preference_weight",
        "practice_profile",
    ):
        summary, evidence, confidence = _summarize_field(global_profile.get(key))
        if not summary:
            continue
        lines.append(f"- {DIMENSION_NAMES.get(key, key)} ({confidence_label(confidence)}): {summary}")
        for item in evidence[:2]:
            lines.append(f"  - {item}")

    for profile in course_profiles:
        context = ((profile or {}).get("course_context") or {}).get("value") or {}
        course_name = context.get("course") or "未命名课程"
        lines.extend(["", f"## 课程画像: {course_name}"])
        for key in (
            "course_context",
            "knowledge_level",
            "learning_goal_type",
            "weak_knowledge_points",
        ):
            summary, evidence, confidence = _summarize_field((profile or {}).get(key))
            if not summary:
                continue
            lines.append(f"- {DIMENSION_NAMES.get(key, key)} ({confidence_label(confidence)}): {summary}")
            for item in evidence[:2]:
                lines.append(f"  - {item}")

    strategy_summary = (profile_json.get("initial_strategy") or {}).get("strategy_summary")
    if strategy_summary:
        lines.extend(["", "## 初始策略", strategy_summary])

    if profile_meta.get("last_update_reason"):
        lines.extend(["", "## 最近更新", str(profile_meta["last_update_reason"])])

    return "\n".join(lines)


def render_profile_dimension(profile_json: dict[str, Any], dimension: str) -> str:
    learning_profile = profile_json.get("learning_profile") or {}
    global_profile = learning_profile.get("global_profile") or {}
    for key, value in global_profile.items():
        if key == dimension:
            summary, evidence, confidence = _summarize_field(value)
            if not summary:
                return f"画像中暂无 {dimension} 信息。"
            lines = [f"## {DIMENSION_NAMES.get(key, key)} ({confidence_label(confidence)})", summary]
            lines.extend(f"- {item}" for item in evidence[:3])
            return "\n".join(lines)

    for course_profile in learning_profile.get("course_profiles") or []:
        if dimension in course_profile:
            summary, evidence, confidence = _summarize_field(course_profile[dimension])
            if not summary:
                continue
            context = (course_profile.get("course_context") or {}).get("value") or {}
            lines = [
                f"## {DIMENSION_NAMES.get(dimension, dimension)} ({confidence_label(confidence)})",
                f"课程: {context.get('course') or '未知课程'}",
                summary,
            ]
            lines.extend(f"- {item}" for item in evidence[:3])
            return "\n".join(lines)

    return f"画像中暂无指定维度 {dimension} 信息。"


def calculate_score(profile_json: dict[str, Any]) -> dict[str, Any]:
    learning_profile = profile_json.get("learning_profile") or {}
    global_profile = learning_profile.get("global_profile") or {}
    course_profiles = learning_profile.get("course_profiles") or []
    first_course = course_profiles[0] if course_profiles else {}

    source_map: dict[str, dict[str, Any]] = {
        "major_background": global_profile.get("major_background") or {},
        "student_stage": global_profile.get("student_stage") or {},
        "course_context": first_course.get("course_context") or {},
        "knowledge_level": first_course.get("knowledge_level") or {},
        "learning_goal_type": first_course.get("learning_goal_type") or {},
        "weak_knowledge_points": first_course.get("weak_knowledge_points") or {},
        "cognitive_style": global_profile.get("cognitive_style") or {},
        "resource_preference_weight": global_profile.get("resource_preference_weight") or {},
        "learning_pace": global_profile.get("learning_pace") or {},
        "practice_profile": global_profile.get("practice_profile") or {},
    }

    dim_scores: dict[str, int | None] = {}
    missing: list[str] = []
    total_evidence = 0

    for key in ALL_DIMENSIONS:
        field = source_map.get(key) or {}
        value = field.get("value")
        evidence = dedupe_strings(field.get("evidence") or [])
        if value in (None, [], {}):
            dim_scores[key] = None
            missing.append(key)
            continue
        score = round(_clamp_confidence(field.get("confidence")) * 70 + min(30, len(evidence) * 10))
        dim_scores[key] = max(1, min(100, score))
        total_evidence += len(evidence)

    valid_scores = [score for score in dim_scores.values() if score is not None]
    score_json = make_default_score_json()
    score_json.update(
        {
            "overall_score": round(sum(valid_scores) / len(valid_scores)) if valid_scores else None,
            "confidence": _avg_confidence(profile_json),
            "dimension_scores": dim_scores,
            "section_coverage": _compute_coverage(profile_json),
            "evidence_quality": min(100, total_evidence * 10),
            "missing_sections": missing,
            "scored_at": _now_iso(),
        }
    )
    return score_json


def _get_update_interval(coverage: float) -> int:
    for tier_info in PROFILE_UPDATE_INTERVALS.values():
        if coverage <= tier_info["max_coverage"]:
            return tier_info["interval"]
    return PROFILE_UPDATE_INTERVALS["high"]["interval"]


class ProfileBuilder:
    """Builds onboarding and tutoring-driven user profiles."""

    def __init__(self, *, module: str = "mentor") -> None:
        self.module = module
        self.llm = get_llm()

    async def get_onboarding(self, *, db: AsyncSession, user_id: int) -> dict[str, Any]:
        profile = (
            await db.exec(select(UserProfile).where(UserProfile.user_id == user_id, UserProfile.module == self.module))
        ).first()
        profile_json = profile.profile_json if profile and profile.profile_json else {}
        base_info = normalize_onboarding(profile_json.get("base_info"))
        return {"base_info": base_info, "profile_initialized": is_onboarding_complete(base_info)}

    async def upsert(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str | None = None,
        onboarding: dict[str, Any] | None = None,
        reason: str = "manual",
    ):
        old = (
            await db.exec(select(UserProfile).where(UserProfile.user_id == user_id, UserProfile.module == self.module))
        ).first()
        old_json = old.profile_json if old and old.profile_json else make_default_profile_json()

        if onboarding is not None:
            normalized = normalize_onboarding(onboarding)
            profile_json = self._build_onboarding_profile(normalized, old_json)
            updated_reason = "cold_start_onboarding"
            logger.info("[ProfileBuilder] cold start profile generated: user_id=%s", user_id)
        else:
            success, updated, profile_json = await self._build_from_dialogue(
                db=db,
                user_id=user_id,
                session_id=session_id,
                old_json=old_json,
            )
            if not success or not updated:
                return None
            updated_reason = "dialogue_profile_update"

        score_json = calculate_score(profile_json)
        profile_markdown = render_profile_markdown(profile_json)
        profile_json.setdefault("profile_meta", {})
        profile_json["profile_meta"].update(
            {
                "coverage": score_json["section_coverage"],
                "last_update_reason": reason if reason != "manual" else updated_reason,
                "updated_at": _now_iso(),
            }
        )
        return await self._update_profile_db(
            db=db,
            user_id=user_id,
            profile_json=profile_json,
            score_json=score_json,
            profile_markdown=profile_markdown,
            updated_reason=reason if reason != "manual" else updated_reason,
            source_session_ids=[session_id] if session_id else None,
            confidence=score_json["confidence"],
            expected_version=old.version if old and onboarding is not None else None,
        )

    async def apply_tutoring_update(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        payload: dict[str, Any],
    ) -> UserProfile | None:
        profile = (
            await db.exec(select(UserProfile).where(UserProfile.user_id == user_id, UserProfile.module == self.module))
        ).first()
        old_json = profile.profile_json if profile and profile.profile_json else make_default_profile_json()
        patch = await self._build_tutoring_patch(db=db, user_id=user_id, payload=payload, old_json=old_json)
        if not patch.get("should_update"):
            return profile

        merged = self._merge_tutoring_patch(old_json, patch)
        score_json = calculate_score(merged)
        profile_markdown = render_profile_markdown(merged)
        merged.setdefault("profile_meta", {})
        merged["profile_meta"].update(
            {
                "coverage": score_json["section_coverage"],
                "last_update_reason": patch.get("update_reason") or "tutoring_inference",
                "updated_at": _now_iso(),
            }
        )
        return await self._update_profile_db(
            db=db,
            user_id=user_id,
            profile_json=merged,
            score_json=score_json,
            profile_markdown=profile_markdown,
            updated_reason=patch.get("update_reason") or "tutoring_inference",
            source_session_ids=[payload.get("session_id")] if payload.get("session_id") else None,
            confidence=score_json["confidence"],
        )

    async def maybe_upsert(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        turn_count: int = 0,
    ) -> bool:
        try:
            if not await self._should_update(
                db=db,
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
                turn_count=turn_count,
            ):
                return False
            return await self.upsert(db=db, user_id=user_id, session_id=session_id, reason="post_turn") is not None
        except Exception as exc:
            logger.error("[MemoryProfile] update failed user=%s session=%s err=%s", user_id, session_id, exc)
            return False

    async def _should_update(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        user_message: str,
        turn_count: int,
    ) -> bool:
        profile = (
            await db.exec(select(UserProfile).where(UserProfile.user_id == user_id, UserProfile.module == self.module))
        ).first()
        score = profile.profile_score_json if profile and profile.profile_score_json else {}
        coverage = int(score.get("section_coverage") or 0)

        if profile is None or coverage < PROFILE_MIN_COVERAGE:
            return True
        if has_profile_signal(user_message):
            return True

        interval = _get_update_interval(coverage / 100.0)
        return turn_count > 0 and turn_count % interval == 0

    def _build_onboarding_profile(self, onboarding: dict[str, Any], old_json: dict[str, Any] | None) -> dict[str, Any]:
        profile = deepcopy(old_json) if old_json else make_default_profile_json()
        base_info = deepcopy(profile.get("base_info") or {})
        learning_profile = deepcopy(profile.get("learning_profile") or {})
        global_profile = deepcopy(learning_profile.get("global_profile") or {})
        course_profiles = deepcopy(learning_profile.get("course_profiles") or [])

        base_info.update(onboarding)

        school = onboarding.get("school")
        school_level = onboarding.get("school_level")
        major = onboarding.get("major")
        grade = onboarding.get("grade")
        daily_study_time = onboarding.get("daily_study_time")
        global_goal = onboarding.get("global_learning_goal")
        programming_languages = onboarding.get("programming_languages") or []
        resource_preference = onboarding.get("resource_preference") or []

        global_profile["major_background"] = _make_field(slugify(major), "user_onboarding", 0.95, [f"专业: {major}"])
        global_profile["student_stage"] = _make_field(slugify(grade), "user_onboarding", 0.95, [f"年级: {grade}"])
        global_profile["learning_pace"] = _make_field(
            DAILY_STUDY_TIME_TO_PACE.get(str(daily_study_time), "medium"),
            "rule_mapping",
            0.8,
            [f"每日学习时长: {daily_study_time}"],
        )
        global_profile["practice_profile"] = _make_field(
            {
                "preferred_languages": programming_languages,
                "practice_level": "basic",
                "project_preference": "small_cases",
            },
            "user_onboarding",
            0.75,
            [f"编程语言偏好: {'、'.join(programming_languages)}"] if programming_languages else [],
        )
        global_profile["resource_preference_weight"] = _make_field(
            self._build_resource_weights(resource_preference),
            "rule_mapping",
            0.75,
            [f"资源偏好: {'、'.join(resource_preference)}"] if resource_preference else [],
        )

        if school_level:
            global_profile["school_level"] = _make_field(
                school_level,
                "school_mapping",
                0.7,
                [f"学校: {school}"],
            )

        generated_courses: list[dict[str, Any]] = []
        weak_mastery: list[dict[str, Any]] = []
        for course in onboarding.get("courses", []):
            course_name = course.get("course")
            foundation_level = course.get("foundation_level")
            weak_points = course.get("weak_points") or []
            current_topic = course.get("current_topic")
            course_goal = course.get("course_learning_goal") or global_goal
            course_profile = {
                "course_key": slugify(course_name),
                "course_context": _make_field(
                    {
                        "course": course_name,
                        "topic": current_topic,
                    },
                    "user_onboarding",
                    0.95,
                    [f"课程: {course_name}"],
                ),
                "knowledge_level": _make_field(
                    FOUNDATION_LEVEL_TO_KNOWLEDGE_LEVEL.get(str(foundation_level), "medium_low"),
                    "rule_mapping",
                    0.9,
                    [f"课程基础: {foundation_level}"],
                ),
                "learning_goal_type": _make_field(
                    dedupe_strings([GOAL_TO_PROFILE_GOAL.get(str(course_goal), slugify(course_goal) or "exam_oriented")]),
                    "rule_mapping",
                    0.8,
                    [f"课程目标: {course_goal}"] if course_goal else [],
                ),
                "weak_knowledge_points": _make_field(
                    [{"name": point, "mastery_score": 30, "reason": "用户首登填写"} for point in weak_points],
                    "user_onboarding",
                    0.65 if weak_points else 0.0,
                    [f"薄弱点: {point}" for point in weak_points],
                ),
                "recommended_difficulty": _make_field(
                    "basic_to_medium" if foundation_level in {"薄弱", "一般"} else "medium_to_advanced",
                    "rule_mapping",
                    0.7,
                    [f"课程基础: {foundation_level}"],
                ),
                "declared_course_goal": _make_field(
                    course_goal,
                    "user_onboarding",
                    0.85,
                    [f"课程目标: {course_goal}"] if course_goal else [],
                ),
            }
            generated_courses.append(course_profile)
            for point in weak_points:
                weak_mastery.append(
                    {
                        "course": course_name,
                        "knowledge_point": point,
                        "mastery_score": 30,
                        "status": "weak",
                        "source": "user_onboarding",
                        "updated_at": _now_iso(),
                    }
                )

        existing_mastery = profile.get("knowledge_mastery") or []
        profile["knowledge_mastery"] = self._merge_knowledge_mastery(existing_mastery, weak_mastery)
        learning_profile["global_profile"] = global_profile
        learning_profile["course_profiles"] = generated_courses

        goal_type = GOAL_TO_PROFILE_GOAL.get(str(global_goal), slugify(global_goal) or "exam_oriented")
        global_profile["declared_global_goal"] = _make_field(global_goal, "user_onboarding", 0.95, [f"学习目标: {global_goal}"])
        global_profile["inferred_current_goal"] = _make_field(goal_type, "rule_mapping", 0.8, [f"学习目标: {global_goal}"])

        initial_strategy = self._build_initial_strategy(onboarding, generated_courses, school_level)

        profile["base_info"] = base_info
        profile["learning_profile"] = learning_profile
        profile["initial_strategy"] = initial_strategy
        profile["evidence"] = profile.get("evidence") or []
        profile.setdefault("profile_meta", {})
        profile["profile_meta"].update(
            {
                "coverage": _compute_coverage(profile),
                "last_update_reason": "onboarding_init",
                "updated_at": _now_iso(),
            }
        )
        return profile

    async def _build_from_dialogue(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str | None,
        old_json: dict[str, Any],
    ) -> tuple[bool, bool, dict[str, Any]]:
        long_term = (
            await db.exec(select(UserLongTermMemory).where(UserLongTermMemory.user_id == user_id, UserLongTermMemory.module == self.module))
        ).first()
        recent_dialogue = await self._build_recent_dialogue(db=db, user_id=user_id, session_id=session_id)
        prompt = registry.render(
            "memory/profile",
            base_info=json.dumps(old_json.get("base_info") or {}, ensure_ascii=False, indent=2),
            learning_profile=json.dumps(old_json.get("learning_profile") or {}, ensure_ascii=False, indent=2),
            knowledge_mastery=json.dumps(old_json.get("knowledge_mastery") or [], ensure_ascii=False, indent=2),
            recent_dialogue=recent_dialogue,
            long_term_memory=(long_term.memory_markdown if long_term and long_term.memory_markdown else "暂无长期记忆。")[:3000],
        )
        try:
            resp = await self.llm.ainvoke_json(
                TutoringInferenceOutput,
                prompt,
                function_name="update_learning_profile",
                function_description="基于最近对话提取画像增量更新。",
                temperature=0.1,
            )
        except Exception as exc:
            logger.error("[MemoryProfile] dialogue inference failed: %s", exc)
            return False, False, old_json

        patch = resp.model_dump()
        if not patch.get("should_update"):
            return True, False, old_json
        merged = self._merge_tutoring_patch(old_json, patch)
        if merged == old_json:
            return True, False, old_json
        logger.info("[ProfileBuilder] dialogue profile updated: user_id=%s", user_id)
        return True, True, merged

    async def _build_tutoring_patch(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        payload: dict[str, Any],
        old_json: dict[str, Any],
    ) -> dict[str, Any]:
        long_term = (
            await db.exec(select(UserLongTermMemory).where(UserLongTermMemory.user_id == user_id, UserLongTermMemory.module == self.module))
        ).first()
        prompt = registry.render(
            "memory/profile",
            base_info=json.dumps(old_json.get("base_info") or {}, ensure_ascii=False, indent=2),
            learning_profile=json.dumps(old_json.get("learning_profile") or {}, ensure_ascii=False, indent=2),
            knowledge_mastery=json.dumps(old_json.get("knowledge_mastery") or [], ensure_ascii=False, indent=2),
            recent_dialogue=str(payload.get("dialogue_excerpt") or ""),
            long_term_memory=(long_term.memory_markdown if long_term and long_term.memory_markdown else "暂无长期记忆。")[:3000],
            active_course=payload.get("active_course") or "",
            active_topic=payload.get("active_topic") or "",
            evidence=json.dumps(payload.get("evidence") or [], ensure_ascii=False, indent=2),
            behavior_signals=json.dumps(payload.get("behavior_signals") or {}, ensure_ascii=False, indent=2),
        )
        try:
            resp = await self.llm.ainvoke_json(
                TutoringInferenceOutput,
                prompt,
                function_name="infer_profile_patch",
                function_description="根据辅导过程提取画像 patch 与掌握度 patch。",
                temperature=0.1,
            )
            patch = resp.model_dump()
        except Exception as exc:
            logger.error("[MemoryProfile] tutoring patch inference failed: %s", exc)
            patch = {
                "should_update": bool(payload.get("evidence")),
                "global_profile_patch": {},
                "course_profile_patch": {},
                "knowledge_mastery_patch": [],
                "initial_strategy_patch": {},
                "evidence": payload.get("evidence") or [],
                "update_reason": payload.get("update_reason") or "tutoring_inference",
            }

        if payload.get("evidence"):
            patch.setdefault("evidence", [])
            patch["evidence"].extend(payload["evidence"])
        patch["update_reason"] = payload.get("update_reason") or patch.get("update_reason") or "tutoring_inference"
        return patch

    async def _build_recent_dialogue(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str | None,
        limit: int = 40,
    ) -> str:
        if not session_id:
            return "暂无近期原始对话。"
        filters = [
            ChatMessage.user_id == user_id,
            ChatMessage.session_id == session_id,
            ChatMessage.module == self.module,
            ChatMessage.created_at >= days_ago(MESSAGE_EXPIRE_DAYS),
        ]
        total = (await db.exec(select(func.count()).where(*filters))).one()
        stmt = select(ChatMessage).where(*filters).order_by(ChatMessage.created_at.asc())
        if total > limit:
            stmt = stmt.offset(total - limit)
        messages = list((await db.exec(stmt)).all())
        lines: list[str] = []
        for msg in messages:
            if msg.role not in DIALOGUE_ROLES:
                continue
            content = str(msg.content or "").strip()
            if content:
                role = "用户" if msg.role == "user" else "助手"
                lines.append(f"{role}: {content[:1200]}")
        return "\n".join(lines)[-6000:] or "暂无近期原始对话。"

    def _build_resource_weights(self, preferences: list[str]) -> dict[str, float]:
        weights = deepcopy(RESOURCE_WEIGHT_DEFAULTS)
        for item in preferences:
            key = RESOURCE_PREFERENCE_TO_WEIGHT_KEY.get(str(item))
            if key:
                weights[key] = min(1.0, round(weights.get(key, 0.55) + 0.25, 2))
        return weights

    def _build_initial_strategy(
        self,
        onboarding: dict[str, Any],
        course_profiles: list[dict[str, Any]],
        school_level: str | None,
    ) -> dict[str, Any]:
        priorities = ["document", "exercise"]
        preferences = onboarding.get("resource_preference") or []
        for item in preferences:
            key = RESOURCE_PREFERENCE_TO_WEIGHT_KEY.get(str(item))
            if key and key not in priorities:
                priorities.insert(0, key)

        first_course_name = None
        if course_profiles:
            first_course_name = (((course_profiles[0].get("course_context") or {}).get("value") or {}).get("course"))

        difficulty = "basic_to_medium"
        if school_level and any(tag in school_level for tag in ("985", "211", "双一流")):
            difficulty = "medium"

        strategy_summary = (
            f"先围绕 {first_course_name or '当前课程'} 建立基础理解，再按薄弱点生成练习与专项资源。"
        )
        return {
            "strategy_summary": strategy_summary,
            "resource_generation_priority": priorities,
            "path_planning_strategy": "先基础概念，再核心知识点，最后专项巩固。",
            "tutor_strategy": "优先结合例子、图解和小步提问推进理解。",
            "difficulty_control": difficulty,
        }

    def _merge_tutoring_patch(self, old_json: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(old_json)
        merged.setdefault("learning_profile", {})
        merged["learning_profile"].setdefault("global_profile", {})
        merged["learning_profile"].setdefault("course_profiles", [])
        merged.setdefault("knowledge_mastery", [])
        merged.setdefault("initial_strategy", {})
        merged.setdefault("evidence", [])

        for key, value in (patch.get("global_profile_patch") or {}).items():
            existing = merged["learning_profile"]["global_profile"].get(key)
            merged["learning_profile"]["global_profile"][key] = self._merge_field(existing, value)

        course_patch = patch.get("course_profile_patch") or {}
        if course_patch:
            target_course = None
            context = (course_patch.get("course_context") or {}).get("value") if isinstance(course_patch.get("course_context"), dict) else None
            course_name = None
            if isinstance(context, dict):
                course_name = context.get("course")
            if not course_name:
                course_name = course_patch.get("course")
            if course_name:
                target_course = self._find_course_profile(merged["learning_profile"]["course_profiles"], course_name)
            if target_course is None:
                target_course = {"course_key": slugify(course_name)}
                merged["learning_profile"]["course_profiles"].append(target_course)
            for key, value in course_patch.items():
                if key == "course":
                    continue
                target_course[key] = self._merge_field(target_course.get(key), value)

        merged["knowledge_mastery"] = self._merge_knowledge_mastery(
            merged.get("knowledge_mastery") or [],
            patch.get("knowledge_mastery_patch") or [],
        )

        for key, value in (patch.get("initial_strategy_patch") or {}).items():
            if value not in (None, "", [], {}):
                merged["initial_strategy"][key] = value

        merged["evidence"] = self._merge_evidence(merged.get("evidence") or [], patch.get("evidence") or [])
        merged.setdefault("profile_meta", {})
        merged["profile_meta"].update(
            {
                "coverage": _compute_coverage(merged),
                "last_update_reason": patch.get("update_reason") or "tutoring_inference",
                "updated_at": _now_iso(),
            }
        )
        return merged

    def _merge_field(self, existing: Any, incoming: Any) -> Any:
        if incoming in (None, "", [], {}):
            return existing
        if not isinstance(incoming, dict):
            return incoming
        if not isinstance(existing, dict):
            return incoming

        incoming_conf = _clamp_confidence(incoming.get("confidence"))
        existing_conf = _clamp_confidence(existing.get("confidence"))
        if incoming_conf > existing_conf or existing.get("value") in (None, [], {}):
            merged = deepcopy(existing)
            merged.update(incoming)
            merged["evidence"] = dedupe_strings((existing.get("evidence") or []) + (incoming.get("evidence") or []))
            merged["updated_at"] = _now_iso()
            return merged

        merged = deepcopy(existing)
        merged["evidence"] = dedupe_strings((existing.get("evidence") or []) + (incoming.get("evidence") or []))
        merged["updated_at"] = _now_iso()
        return merged

    def _find_course_profile(self, course_profiles: list[dict[str, Any]], course_name: str) -> dict[str, Any] | None:
        for course_profile in course_profiles:
            context = ((course_profile.get("course_context") or {}).get("value") or {})
            if context.get("course") == course_name:
                return course_profile
        return None

    def _merge_knowledge_mastery(
        self,
        existing: list[dict[str, Any]],
        incoming: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        index: dict[tuple[str, str], dict[str, Any]] = {}
        for item in existing:
            key = (str(item.get("course") or ""), str(item.get("knowledge_point") or ""))
            index[key] = deepcopy(item)

        for item in incoming:
            key = (str(item.get("course") or ""), str(item.get("knowledge_point") or ""))
            if not key[0] or not key[1]:
                continue
            if key not in index:
                new_item = deepcopy(item)
                new_item.setdefault("updated_at", _now_iso())
                index[key] = new_item
                continue

            current = index[key]
            current_score = int(current.get("mastery_score") or 0)
            incoming_score = int(item.get("mastery_score") or current_score)
            current["mastery_score"] = incoming_score if abs(incoming_score - current_score) >= 5 else max(current_score, incoming_score)
            current["status"] = item.get("status") or current.get("status")
            current["source"] = item.get("source") or current.get("source")
            current["updated_at"] = _now_iso()
        return list(index.values())

    def _merge_evidence(self, existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged = deepcopy(existing)
        for item in incoming:
            if item not in merged:
                merged.append(item)
        return merged[-50:]

    async def _update_profile_db(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        profile_json: dict[str, Any],
        score_json: dict[str, Any],
        profile_markdown: str | None = None,
        updated_reason: str,
        source_session_ids: list[str] | None = None,
        source_summary_ids: list[int] | None = None,
        confidence: float = 0.7,
        expected_version: int | None = None,
    ) -> UserProfile:
        profile = (
            await db.exec(select(UserProfile).where(UserProfile.user_id == user_id, UserProfile.module == self.module))
        ).first()
        if not profile:
            profile = UserProfile(user_id=user_id, module=self.module)
        elif expected_version is not None and profile.version != expected_version:
            raise ConcurrentUpdateError(f"profile version conflict: expected {expected_version}, got {profile.version}")
        else:
            profile.version = (profile.version or 1) + 1

        profile.profile_json = profile_json
        profile.profile_score_json = score_json
        profile.profile_markdown = profile_markdown
        profile.updated_reason = updated_reason
        profile.source_session_ids = source_session_ids
        profile.source_summary_ids = source_summary_ids
        profile.confidence = confidence
        profile.updated_at = now()
        db.add(profile)
        await db.flush()

        latest_version = (
            await db.exec(
                select(func.max(UserProfileHistory.version)).where(
                    UserProfileHistory.user_id == user_id,
                    UserProfileHistory.module == self.module,
                )
            )
        ).one()
        db.add(
            UserProfileHistory(
                user_id=user_id,
                module=self.module,
                version=0 if latest_version is None else int(latest_version) + 1,
                profile_json=profile_json,
                profile_score_json=score_json,
                profile_markdown=profile_markdown,
                change_reason=updated_reason,
                source_session_ids=source_session_ids,
                source_summary_ids=source_summary_ids,
            )
        )
        return profile
