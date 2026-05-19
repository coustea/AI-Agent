"""画像服务层。

模块职责：
- 画像构建
- 评分计算
- 首次登录处理
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from pydantic import BaseModel, Field

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.memory.message.types import DIALOGUE_ROLES
from app.memory.message.store import MessageStore
from app.memory.memory.store import LongTermMemoryStore
from app.memory.prompts import render_prompt
from app.memory.profile.store import ProfileStore
from app.memory.profile.types import (
    ALL_DIMENSIONS,
    DIMENSION_NAMES,
    ONBOARDING_OPTIONAL_FIELDS,
    ONBOARDING_REQUIRED_FIELDS,
    make_default_profile_json,
    make_default_score_json,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# LLM 输出模型
# ---------------------------------------------------------------------------

class DimensionOutput(BaseModel):
    """单维度输出。"""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str | None = None
    evidence: list[str] = Field(default_factory=list)


class ProfileOutput(BaseModel):
    """画像构建输出。"""
    dimensions: dict[str, DimensionOutput] = Field(default_factory=dict)
    recommended_strategy: list[str] = Field(default_factory=list)
    last_update_reason: str = ""


# ---------------------------------------------------------------------------
# 首次登录处理
# ---------------------------------------------------------------------------

def normalize_onboarding(data: dict[str, Any] | None) -> dict[str, Any]:
    """标准化首次登录数据。"""
    src = data or {}
    result = {}
    for f in ONBOARDING_REQUIRED_FIELDS + ONBOARDING_OPTIONAL_FIELDS:
        if f == "courses":
            raw = src.get("courses", [])
            courses = []
            seen = set()
            for item in (raw if isinstance(raw, list) else [raw]):
                course = str(item or "").strip()
                if course and course not in seen:
                    seen.add(course)
                    courses.append(course)
            result["courses"] = courses
        else:
            text = str(src.get(f) or "").strip()
            result[f] = text or None
    return result


def is_onboarding_complete(data: dict[str, Any] | None) -> bool:
    """检查首次登录是否完整。"""
    norm = normalize_onboarding(data)
    for f in ONBOARDING_REQUIRED_FIELDS:
        if f == "courses":
            if not norm.get("courses"):
                return False
        elif not norm.get(f):
            return False
    return True


# ---------------------------------------------------------------------------
# 评分计算
# ---------------------------------------------------------------------------

def calculate_score(profile_json: dict[str, Any]) -> dict[str, Any]:
    """计算画像评分。"""
    dims = profile_json.get("dimensions") or {}

    # 各维度评分
    dim_scores = {}
    for key in ALL_DIMENSIONS:
        dim = dims.get(key) or {}
        summary = str(dim.get("summary") or "").strip()
        evidence = dim.get("evidence") or []
        if not summary and not evidence:
            dim_scores[key] = None
            continue
        conf = _clamp_confidence(dim.get("confidence"))
        evidence_bonus = min(25, len(evidence) * 8)
        summary_bonus = 20 if summary else 0
        dim_scores[key] = max(1, min(100, round(conf * 55 + summary_bonus + evidence_bonus)))

    valid_scores = [s for s in dim_scores.values() if s is not None]
    missing = [k for k, s in dim_scores.items() if s is None]
    coverage = round((len(ALL_DIMENSIONS) - len(missing)) / len(ALL_DIMENSIONS) * 100)
    evidence_count = sum(len((dims.get(k) or {}).get("evidence") or []) for k in ALL_DIMENSIONS)
    evidence_score = min(100, evidence_count * 20)
    overall = round(sum(valid_scores) / len(valid_scores)) if valid_scores else None
    confidence = _avg_confidence(profile_json)

    result = make_default_score_json()
    result.update({
        "overall_score": overall,
        "confidence": confidence,
        "dimension_scores": dim_scores,
        "section_coverage": coverage,
        "evidence_quality": evidence_score,
        "missing_sections": missing,
        "scored_at": _now_iso(),
    })
    return result


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _clamp_confidence(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except (TypeError, ValueError):
        return 0.0


def _avg_confidence(profile_json: dict[str, Any]) -> float:
    dims = profile_json.get("dimensions") or {}
    values = [
        float((dims.get(k) or {}).get("confidence") or 0)
        for k in ALL_DIMENSIONS
        if (dims.get(k) or {}).get("summary") or (dims.get(k) or {}).get("evidence")
    ]
    return round(sum(values) / len(values), 2) if values else 0.0


# ---------------------------------------------------------------------------
# 画像服务
# ---------------------------------------------------------------------------

class ProfileService:
    """画像服务。"""

    def __init__(self, module: str = "mentor") -> None:
        self.module = module
        self.store = ProfileStore()
        self.message_store = MessageStore()
        self.memory_store = LongTermMemoryStore()
        self.llm = get_llm_manager()

    async def get(self, user_id: int):
        """获取画像。"""
        return await self.store.get(user_id, self.module)

    async def get_or_create(self, user_id: int):
        """获取或创建画像。"""
        return await self.store.get_or_create(user_id, self.module)

    async def get_history(self, user_id: int, limit: int = 20):
        """获取画像历史。"""
        return await self.store.get_history(user_id, self.module, limit)

    async def get_onboarding(self, user_id: int) -> dict[str, Any]:
        """获取首次登录状态。"""
        profile = await self.get(user_id)
        profile_json = profile.profile_json if profile and profile.profile_json else {}
        student = normalize_onboarding(profile_json.get("student_profile"))
        return {
            "student_profile": student,
            "profile_initialized": is_onboarding_complete(student),
        }

    async def update_onboarding(
        self,
        user_id: int,
        student_profile: dict[str, Any],
    ):
        """更新首次登录数据。"""
        normalized = normalize_onboarding(student_profile)
        if not is_onboarding_complete(normalized):
            raise ValueError("首次登录必填字段不完整")

        old = await self.get(user_id)
        old_json = old.profile_json if old and old.profile_json else None
        profile_json = self._build_onboarding_profile(normalized, old_json)
        score_json = calculate_score(profile_json)

        return await self.store.update(
            user_id=user_id,
            module=self.module,
            profile_json=profile_json,
            score_json=score_json,
            updated_reason="基于首次登录学习资料初始化画像",
            confidence=score_json["confidence"],
        )

    async def build(self, user_id: int, session_id: str | None = None) -> tuple[bool, bool]:
        """构建画像。返回 (success, updated)。"""
        logger.info("[ProfileService] 开始构建 user=%s", user_id)

        # 获取数据
        old = await self.store.get(user_id, self.module)
        if session_id is None:
            sessions = await self.message_store.get_recent(user_id, "", self.module, limit=1)
            # 这里需要从 session store 获取
            session_id = "default"

        old_json = old.profile_json if old and old.profile_json else make_default_profile_json()

        # 获取长期记忆作为补充上下文
        long_term_text = "暂无长期记忆。"
        try:
            ltm = await self.memory_store.get(user_id, self.module)
            if ltm and ltm.memory_markdown:
                long_term_text = ltm.memory_markdown[:3000]
        except Exception as e:
            logger.warning("[ProfileService] 获取长期记忆失败: %s", e)

        # 调用 LLM 构建画像
        try:
            recent_dialogue = await self._build_recent_dialogue(user_id, session_id)
            prompt = self._build_prompt(old_json, recent_dialogue, long_term_text)
            resp = await self.llm.generate_json(
                ProfileOutput,
                prompt,
                function_name="update_student_profile",
                function_description="根据旧画像和近期对话返回学生画像。",
                model_kwargs={"temperature": 0.1, "streaming": False},
            )
        except Exception as e:
            logger.error("[ProfileService] LLM 失败: %s", e)
            return False, False

        new_json = self._parse_response(resp.model_dump())
        if not new_json:
            return True, False
        new_json = self._merge_with_old_profile(new_json, old_json)

        score_json = calculate_score(new_json)

        # 检查变化
        if old and old.profile_json and self._is_same(new_json, old.profile_json):
            return True, False

        # 保存
        try:
            await self.store.update(
                user_id=user_id,
                module=self.module,
                profile_json=new_json,
                score_json=score_json,
                updated_reason="基于旧画像和近期对话生成画像",
                source_session_ids=[session_id] if session_id else None,
                confidence=score_json["confidence"],
            )
            return True, True
        except Exception as e:
            logger.error("[ProfileService] 保存失败: %s", e)
            return False, False

    def _build_onboarding_profile(
        self,
        onboarding: dict[str, Any],
        old_json: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """从首次登录构建画像。"""
        profile = deepcopy(old_json) if old_json else make_default_profile_json()
        dims = profile.get("dimensions")
        if not isinstance(dims, dict):
            dims = make_default_profile_json()["dimensions"]

        courses_text = "、".join(onboarding.get("courses", []))
        lang_text = f"，常用编程语言为 {onboarding['preferred_language']}" if onboarding.get("preferred_language") else ""

        dims["knowledge_foundation"] = {
            "name": "知识基础",
            "confidence": 0.85,
            "summary": f"{onboarding.get('education_level')} {onboarding.get('major')} 学生，正在学习 {courses_text}{lang_text}。",
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

        profile["student_profile"] = onboarding
        profile["dimensions"] = dims
        profile["recommended_strategy"] = [
            f"优先围绕 {courses_text} 生成学习资源",
            f"资源难度参考 {onboarding.get('education_level')} / {onboarding.get('grade')} 阶段",
        ]
        profile["last_update_reason"] = "基于首次登录学习资料初始化画像"
        profile["overall_confidence"] = _avg_confidence(profile)
        return profile

    async def _build_recent_dialogue(
        self,
        user_id: int,
        session_id: str | None,
        limit: int = 40,
    ) -> str:
        """构建画像使用的近期原始对话。"""
        if not session_id:
            return "暂无近期原始对话。"

        messages = await self.message_store.get_recent(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            limit=limit,
        )
        lines: list[str] = []
        for msg in messages:
            if msg.role not in DIALOGUE_ROLES:
                continue
            content = str(msg.content or "").strip()
            if not content:
                continue
            role = "用户" if msg.role == "user" else "助手"
            lines.append(f"{role}: {content[:1200]}")
        return "\n".join(lines)[-6000:] or "暂无近期原始对话。"

    def _build_prompt(self, old_json: dict[str, Any], recent_dialogue: str, long_term_memory: str = "暂无长期记忆。") -> str:
        """构建 LLM prompt。"""
        return render_prompt(
            "profile_builder.md",
            student_profile=json.dumps(
                old_json.get("student_profile") or {},
                ensure_ascii=False,
                indent=2,
            ),
            old_profile=json.dumps(old_json, ensure_ascii=False, indent=2),
            recent_dialogue=recent_dialogue,
            long_term_memory=long_term_memory,
        )

    def _parse_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        """解析 LLM 响应。"""
        profile = make_default_profile_json()
        raw_dims = payload.get("dimensions") or {}
        dims = {}
        for key in ALL_DIMENSIONS:
            raw = raw_dims.get(key) or {}
            summary = raw.get("summary")
            evidence = raw.get("evidence") or []
            conf = raw.get("confidence")
            has = bool(summary) or bool(evidence)
            dims[key] = {
                "name": DIMENSION_NAMES.get(key, key),
                "confidence": _clamp_confidence(conf) if has else 0.0,
                "summary": str(summary).strip() if summary else None,
                "evidence": [str(i).strip() for i in evidence if str(i).strip()][:5],
                "updated_at": _now_iso() if has else None,
            }
        profile["dimensions"] = dims
        profile["recommended_strategy"] = payload.get("recommended_strategy", [])[:5]
        profile["last_update_reason"] = str(payload.get("last_update_reason") or "").strip()
        profile["overall_confidence"] = _avg_confidence(profile)
        return profile

    def _merge_with_old_profile(
        self,
        new_json: dict[str, Any],
        old_json: dict[str, Any],
    ) -> dict[str, Any]:
        """保留旧画像中的稳定事实，并用新对话补充更新。"""
        merged = deepcopy(new_json)
        if old_json.get("student_profile"):
            merged["student_profile"] = deepcopy(old_json["student_profile"])

        old_dims = old_json.get("dimensions") or {}
        merged_dims = merged.get("dimensions") or {}
        for key in ALL_DIMENSIONS:
            new_dim = merged_dims.get(key) or {}
            old_dim = old_dims.get(key) or {}
            has_new_signal = bool(new_dim.get("summary")) or bool(new_dim.get("evidence"))
            has_old_signal = bool(old_dim.get("summary")) or bool(old_dim.get("evidence"))
            if not has_new_signal and has_old_signal:
                restored = deepcopy(old_dim)
                restored.setdefault("name", DIMENSION_NAMES.get(key, key))
                restored.setdefault("confidence", 0.0)
                restored.setdefault("summary", None)
                restored.setdefault("evidence", [])
                restored.setdefault("updated_at", None)
                merged_dims[key] = restored

        merged["dimensions"] = merged_dims
        if not merged.get("recommended_strategy") and old_json.get("recommended_strategy"):
            merged["recommended_strategy"] = deepcopy(old_json["recommended_strategy"])
        if not merged.get("last_update_reason") and old_json.get("last_update_reason"):
            merged["last_update_reason"] = old_json["last_update_reason"]
        merged["overall_confidence"] = _avg_confidence(merged)
        return merged

    def _is_same(self, new: dict[str, Any], old: dict[str, Any]) -> bool:
        """比较画像是否相同。"""
        def strip(data: dict[str, Any]) -> dict[str, Any]:
            d = deepcopy(data)
            d.pop("overall_confidence", None)
            for dim in (d.get("dimensions") or {}).values():
                if isinstance(dim, dict):
                    dim.pop("updated_at", None)
            return d
        return strip(new) == strip(old)
