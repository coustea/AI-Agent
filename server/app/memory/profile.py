"""用户画像构建与更新。"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.memory.store import MemoryStore
from app.memory.types import (
    ALL_DIMENSIONS,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    DIMENSION_NAMES,
    DIALOGUE_ROLES,
    ONBOARDING_OPTIONAL_FIELDS,
    ONBOARDING_REQUIRED_FIELDS,
    PROFILE_MIN_COVERAGE,
    PROFILE_UPDATE_INTERVALS,
    ProfileOutput,
    confidence_label,
    has_profile_signal,
    make_default_profile_json,
    make_default_score_json,
    now,
)
from app.prompts import registry

logger = get_logger(__name__)


def normalize_onboarding(data: dict[str, Any] | None) -> dict[str, Any]:
    src = data or {}
    result: dict[str, Any] = {}
    for field in ONBOARDING_REQUIRED_FIELDS + ONBOARDING_OPTIONAL_FIELDS:
        if field == "courses":
            raw = src.get("courses", [])
            values = raw if isinstance(raw, list) else [raw]
            courses: list[str] = []
            seen: set[str] = set()
            for item in values:
                course = str(item or "").strip()
                if course and course not in seen:
                    seen.add(course)
                    courses.append(course)
            result["courses"] = courses
        elif field == "weakness_points":
            raw = src.get("weakness_points")
            if isinstance(raw, list):
                result[field] = [str(item).strip() for item in raw if str(item).strip()]
            else:
                text = str(raw or "").strip()
                result[field] = [text] if text else []
        else:
            text = str(src.get(field) or "").strip()
            result[field] = text or None
    return result


def is_onboarding_complete(data: dict[str, Any] | None) -> bool:
    normalized = normalize_onboarding(data)
    for field in ONBOARDING_REQUIRED_FIELDS:
        if field == "courses":
            if not normalized.get("courses"):
                return False
        elif not normalized.get(field):
            return False
    return True


def _now_iso() -> str:
    return now().isoformat()


def _clamp_confidence(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except (TypeError, ValueError):
        return 0.0


def _avg_confidence(profile_json: dict[str, Any]) -> float:
    dims = profile_json.get("dimensions") or {}
    values = [
        float((dims.get(key) or {}).get("confidence") or 0)
        for key in ALL_DIMENSIONS
        if (dims.get(key) or {}).get("summary") or (dims.get(key) or {}).get("evidence")
    ]
    return round(sum(values) / len(values), 2) if values else 0.0


def render_profile_markdown(profile_json: dict[str, Any]) -> str:
    """将画像 JSON 渲染为 Markdown，供 LLM 上下文使用。"""
    dims = profile_json.get("dimensions") or {}
    lines = ["# 用户画像"]
    for key in ALL_DIMENSIONS:
        dim = dims.get(key) or {}
        summary = dim.get("summary")
        evidence = dim.get("evidence") or []
        if not summary and not evidence:
            continue
        title = DIMENSION_NAMES.get(key, key)
        conf = _clamp_confidence(dim.get("confidence"))
        label = confidence_label(conf)
        lines.append(f"\n## {title}（{label}）")
        if summary:
            lines.append(str(summary))
        for item in evidence[:3]:
            lines.append(f"- {item}")
    strategies = profile_json.get("recommended_strategy") or []
    if strategies:
        lines.append("\n## 推荐策略")
        for s in strategies[:5]:
            lines.append(f"- {s}")
    return "\n".join(lines) if len(lines) > 1 else "# 用户画像\n\n暂无画像信息。"


def calculate_score(profile_json: dict[str, Any]) -> dict[str, Any]:
    dims = profile_json.get("dimensions") or {}
    dim_scores: dict[str, int | None] = {}
    for key in ALL_DIMENSIONS:
        dim = dims.get(key) or {}
        summary = str(dim.get("summary") or "").strip()
        evidence = dim.get("evidence") or []
        if not summary and not evidence:
            dim_scores[key] = None
            continue
        dim_scores[key] = max(1, min(100, round(_clamp_confidence(dim.get("confidence")) * 55 + (20 if summary else 0) + min(25, len(evidence) * 8))))
    valid_scores = [score for score in dim_scores.values() if score is not None]
    missing = [key for key, score in dim_scores.items() if score is None]
    score_json = make_default_score_json()
    score_json.update(
        {
            "overall_score": round(sum(valid_scores) / len(valid_scores)) if valid_scores else None,
            "confidence": _avg_confidence(profile_json),
            "dimension_scores": dim_scores,
            "section_coverage": round((len(ALL_DIMENSIONS) - len(missing)) / len(ALL_DIMENSIONS) * 100),
            "evidence_quality": min(100, sum(len((dims.get(key) or {}).get("evidence") or []) for key in ALL_DIMENSIONS) * 20),
            "missing_sections": missing,
            "scored_at": _now_iso(),
        }
    )
    return score_json


def _get_update_interval(coverage: float) -> int:
    """根据覆盖率返回更新间隔轮次。"""
    for tier_info in PROFILE_UPDATE_INTERVALS.values():
        if coverage <= tier_info["max_coverage"]:
            return tier_info["interval"]
    return PROFILE_UPDATE_INTERVALS["high"]["interval"]


class ProfileBuilder:
    """统一处理首次登录画像与对话画像更新。"""

    def __init__(self, *, module: str = "mentor", store: MemoryStore | None = None) -> None:
        self.module = module
        self.store = store or MemoryStore()
        self.llm = get_llm()

    async def get_onboarding(self, user_id: int) -> dict[str, Any]:
        profile = await self.store.get_profile(user_id=user_id, module=self.module)
        profile_json = profile.profile_json if profile and profile.profile_json else {}
        student = normalize_onboarding(profile_json.get("student_profile"))
        return {"student_profile": student, "profile_initialized": is_onboarding_complete(student)}

    async def upsert(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        onboarding: dict[str, Any] | None = None,
        reason: str = "manual",
    ):
        old = await self.store.get_profile(user_id=user_id, module=self.module)
        old_json = old.profile_json if old and old.profile_json else make_default_profile_json()

        if onboarding is not None:
            normalized = normalize_onboarding(onboarding)
            profile_json = self._build_onboarding_profile(normalized, old_json)
            updated_reason = "基于首次登录学习资料生成画像"
        else:
            success, updated, profile_json = await self._build_from_dialogue(user_id=user_id, session_id=session_id, old_json=old_json)
            if not success or not updated:
                return None
            updated_reason = "基于近期对话更新画像"

        score_json = calculate_score(profile_json)
        profile_markdown = render_profile_markdown(profile_json)
        return await self.store.update_profile(
            user_id=user_id,
            module=self.module,
            profile_json=profile_json,
            score_json=score_json,
            profile_markdown=profile_markdown,
            updated_reason=updated_reason if reason == "onboarding" else f"{updated_reason}（{reason}）",
            source_session_ids=[session_id] if session_id else None,
            confidence=score_json["confidence"],
            expected_version=old.version if old and onboarding is not None else None,
        )

    async def maybe_upsert(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        turn_count: int = 0,
    ) -> bool:
        try:
            if not await self._should_update(user_id, session_id, user_message, turn_count):
                return False
            return await self.upsert(user_id=user_id, session_id=session_id, reason="post_turn") is not None
        except Exception as exc:
            logger.error("[MemoryProfile] 更新画像失败 user=%s session=%s err=%s", user_id, session_id, exc)
            return False

    async def _should_update(self, user_id: int, session_id: str, user_message: str, turn_count: int) -> bool:
        profile = await self.store.get_profile(user_id=user_id, module=self.module)
        score = profile.profile_score_json if profile and profile.profile_score_json else {}
        coverage = int(score.get("section_coverage") or 0)

        if profile is None or coverage < PROFILE_MIN_COVERAGE:
            return True
        if has_profile_signal(user_message):
            return True

        interval = _get_update_interval(coverage / 100.0)
        if turn_count > 0 and turn_count % interval == 0:
            return True

        return False

    def _build_onboarding_profile(self, onboarding: dict[str, Any], old_json: dict[str, Any] | None) -> dict[str, Any]:
        profile = deepcopy(old_json) if old_json else make_default_profile_json()
        dims = profile.get("dimensions")
        if not isinstance(dims, dict):
            dims = make_default_profile_json()["dimensions"]
        courses_text = "、".join(onboarding.get("courses", []))
        lang_text = f"，常用编程语言为 {onboarding['preferred_language']}" if onboarding.get("preferred_language") else ""

        # 提取学校及层次信息并写入画像的知识基础维度
        school = onboarding.get("school")
        school_level = onboarding.get("school_level")
        school_info = ""
        if school:
            level_suffix = f"（{school_level}）" if school_level else ""
            school_info = f"就读于 {school}{level_suffix}，"

        dims["knowledge_foundation"] = {
            "name": "知识基础",
            "confidence": 0.85,
            "summary": f"{school_info}{onboarding.get('education_level')} {onboarding.get('major')} 学生，正在学习 {courses_text}{lang_text}。",
            "evidence": ["来自首次登录学习资料"],
            "updated_at": _now_iso(),
        }
        dims["learning_goal"] = {
            "name": "学习目标",
            "confidence": 0.85,
            "summary": f"围绕 {courses_text} 的当前目标是：{onboarding.get('learning_goal')}。",
            "evidence": ["来自首次登录学习资料"],
            "updated_at": _now_iso(),
        }
        if onboarding.get("cognitive_style"):
            dims["cognitive_style"] = {
                "name": "认知风格",
                "confidence": 0.75,
                "summary": onboarding["cognitive_style"],
                "evidence": ["来自首次登录学习资料"],
                "updated_at": _now_iso(),
            }
        if onboarding.get("interaction_preference"):
            dims["interaction_preference"] = {
                "name": "交互偏好",
                "confidence": 0.75,
                "summary": onboarding["interaction_preference"],
                "evidence": ["来自首次登录学习资料"],
                "updated_at": _now_iso(),
            }
        profile["student_profile"] = onboarding
        profile["dimensions"] = dims

        # 动态设计推荐辅导策略
        strategy = [
            f"优先围绕 {courses_text} 生成学习资源",
            f"资源难度参考 {onboarding.get('education_level')} / {onboarding.get('grade')} 阶段",
        ]

        # 判断是否为顶尖高校（好学校）并定制辅导策略
        is_top_school = False
        if school_level:
            top_tags = {"985", "211", "双一流", "一流大学", "一流学科"}
            if any(tag in str(school_level) for tag in top_tags):
                is_top_school = True

        if is_top_school:
            strategy.append(
                f"该生就读于顶尖高校（{school}），基础与基本素养优良。辅导策略上应提供深度底层原理解析（如源码剖析、高并发高性能挑战），多设计启发式与边界条件的探讨，提高辅导难度，避免浅显描述。"
            )
        else:
            if school:
                level_desc = f"（{school_level}）" if school_level else ""
                strategy.append(
                    f"该生就读于普通院校（{school}{level_desc}），辅导时应注重夯实核心基础，多提供直观生动的比喻、实际应用场景及循序渐进的代码推演引导。"
                )
            else:
                strategy.append("根据院校基础与认知偏好，采取常规引导式、循序渐进的辅导难度。")

        profile["recommended_strategy"] = strategy
        profile["last_update_reason"] = "基于首次登录学习资料生成画像"
        profile["overall_confidence"] = _avg_confidence(profile)
        return profile

    async def _build_from_dialogue(self, *, user_id: int, session_id: str | None, old_json: dict[str, Any]) -> tuple[bool, bool, dict[str, Any]]:
        long_term = await self.store.get_long_term_memory(user_id=user_id, module=self.module)
        recent_dialogue = await self._build_recent_dialogue(user_id=user_id, session_id=session_id)
        prompt = registry.render(
            "memory/profile",
            student_profile=json.dumps(old_json.get("student_profile") or {}, ensure_ascii=False, indent=2),
            old_profile=json.dumps(old_json, ensure_ascii=False, indent=2),
            recent_dialogue=recent_dialogue,
            long_term_memory=(long_term.memory_markdown if long_term and long_term.memory_markdown else "暂无长期记忆。")[:3000],
        )
        try:
            resp = await self.llm.ainvoke_json(
                ProfileOutput,
                prompt,
                function_name="update_student_profile",
                function_description="根据旧画像和近期对话返回学生画像。",
                temperature=0.1,
            )
        except Exception as exc:
            logger.error("[MemoryProfile] LLM 构建画像失败: %s", exc)
            return False, False, old_json
        new_json = self._merge_with_old_profile(self._parse_response(resp.model_dump()), old_json)
        if self._is_same(new_json, old_json):
            return True, False, old_json
        return True, True, new_json

    async def _build_recent_dialogue(self, *, user_id: int, session_id: str | None, limit: int = 40) -> str:
        if not session_id:
            return "暂无近期原始对话。"
        messages = await self.store.list_messages(user_id=user_id, session_id=session_id, module=self.module, limit=limit)
        lines: list[str] = []
        for msg in messages:
            if msg.role not in DIALOGUE_ROLES:
                continue
            content = str(msg.content or "").strip()
            if content:
                lines.append(f"{'用户' if msg.role == 'user' else '助手'}: {content[:1200]}")
        return "\n".join(lines)[-6000:] or "暂无近期原始对话。"

    def _parse_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile = make_default_profile_json()
        raw_dims = payload.get("dimensions") or {}
        dims: dict[str, Any] = {}
        for key in ALL_DIMENSIONS:
            raw = raw_dims.get(key) or {}
            summary = raw.get("summary")
            evidence = raw.get("evidence") or []
            has_signal = bool(summary) or bool(evidence)
            dims[key] = {
                "name": DIMENSION_NAMES.get(key, key),
                "confidence": _clamp_confidence(raw.get("confidence")) if has_signal else 0.0,
                "summary": str(summary).strip() if summary else None,
                "evidence": [str(item).strip() for item in evidence if str(item).strip()][:5],
                "updated_at": _now_iso() if has_signal else None,
            }
        profile["dimensions"] = dims
        profile["recommended_strategy"] = payload.get("recommended_strategy", [])[:5]
        profile["last_update_reason"] = str(payload.get("last_update_reason") or "").strip()
        profile["overall_confidence"] = _avg_confidence(profile)
        return profile

    def _merge_with_old_profile(self, new_json: dict[str, Any], old_json: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(new_json)
        if old_json.get("student_profile"):
            merged["student_profile"] = deepcopy(old_json["student_profile"])
        old_dims = old_json.get("dimensions") or {}
        merged_dims = merged.get("dimensions") or {}
        for key in ALL_DIMENSIONS:
            new_dim = merged_dims.get(key) or {}
            old_dim = old_dims.get(key) or {}
            if not (new_dim.get("summary") or new_dim.get("evidence")) and (old_dim.get("summary") or old_dim.get("evidence")):
                merged_dims[key] = deepcopy(old_dim)
        merged["dimensions"] = merged_dims
        if not merged.get("recommended_strategy") and old_json.get("recommended_strategy"):
            merged["recommended_strategy"] = deepcopy(old_json["recommended_strategy"])
        merged["overall_confidence"] = _avg_confidence(merged)
        return merged

    def _is_same(self, new: dict[str, Any], old: dict[str, Any]) -> bool:
        def strip(data: dict[str, Any]) -> dict[str, Any]:
            value = deepcopy(data)
            value.pop("overall_confidence", None)
            for dim in (value.get("dimensions") or {}).values():
                if isinstance(dim, dict):
                    dim.pop("updated_at", None)
            return value

        return strip(new) == strip(old)
