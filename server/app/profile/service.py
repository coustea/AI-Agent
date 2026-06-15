"""Shared learner profile service."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import ProgrammingError

from app.infra.database import session_scope
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import (
    ChatMessage,
    ChatSession,
    ChatSessionSummaryBlock,
    ChatLongTermMemory,
    CourseProfile,
    GlobalProfile,
    School,
)
from app.profile.types import (
    GLOBAL_DIMENSIONS,
    SCORE_DIMENSIONS,
    ALL_DIMENSIONS,
    DIMENSION_NAMES,
    GlobalDimensionValue,
    OnboardingGlobalInferenceOutput,
    GlobalTutoringInferenceOutput,
    ProfileScoreOutput,
    make_default_profile_json,
    make_default_score_json,
    PROFILE_MESSAGE_THRESHOLD,
    PROFILE_TOKEN_THRESHOLD,
    PROFILE_UPDATE_COOLDOWN_MINUTES,
)
from app.infra.prompts import prompts

logger = get_logger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────

def normalize_course_key(course_name: str) -> str:
    """标准化课程名称为 Key：去除所有空白字符，并统一转为小写。"""
    return re.sub(r"\s+", "", course_name.strip().lower())


def make_default_course_markdown(course_name: str) -> str:
    """生成默认空白课程画像 Markdown 文本。"""
    return (
        f"# {course_name}\n\n"
        "## 课程范围\n"
        "暂无明确画像。\n\n"
        "## 当前学习状态\n"
        "暂无明确画像。\n\n"
        "## 薄弱点\n"
        "暂无明确画像。\n\n"
        "## 知识掌握线索\n"
        "暂无明确画像。\n\n"
        "## 辅导建议\n"
        "暂无明确画像。"
    )


REQUIRED_COURSE_MARKDOWN_SECTIONS = (
    "## 课程范围",
    "## 当前学习状态",
    "## 薄弱点",
    "## 知识掌握线索",
    "## 辅导建议",
)


def validate_course_markdown(markdown_text: str, course_name: str) -> str:
    """Validate and normalize LLM-generated course profile Markdown."""
    text = (markdown_text or "").strip()
    if not text:
        raise ValueError("课程画像 Markdown 为空")
    if "```json" in text.lower() or "``` json" in text.lower():
        raise ValueError("课程画像 Markdown 不允许包含 JSON 代码块")
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    if first_line != f"# {course_name}":
        raise ValueError(f"课程画像 Markdown 必须以 '# {course_name}' 开头")
    for section in REQUIRED_COURSE_MARKDOWN_SECTIONS:
        if section not in text:
            raise ValueError(f"课程画像 Markdown 缺少必要章节: {section.replace('## ', '')}")
    return text


def merge_global_dimensions(profile_json: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """合并全局画像维度增量更新。只更新支持的七个全局维度。"""
    merged = deepcopy(profile_json) if profile_json else make_default_profile_json()
    dimensions = merged.setdefault("dimensions", {})
    for key, val in patch.items():
        if key in GLOBAL_DIMENSIONS:
            if isinstance(val, dict):
                dimensions[key] = {
                    "value": str(val.get("value", "")).strip(),
                    "evidence": [str(item).strip() for item in val.get("evidence", []) if str(item).strip()],
                }
            elif isinstance(val, GlobalDimensionValue):
                dimensions[key] = {
                    "value": val.value.strip(),
                    "evidence": [item.strip() for item in val.evidence if item.strip()],
                }
    return merged


def validate_score_output(raw: ProfileScoreOutput) -> dict[str, Any]:
    """对打分输出进行后置验证与清洗：
    1. 限制分数在 0..100 之间；
    2. 如果某维度无任何证据记录（为空列表），强制给该维度评分置为 0；
    3. 总体评分为 10 个维度洗净后分数的算术平均值（四舍五入到整数）；
    4. 自动记录评分时间。
    """
    scores = {}
    evidence = {}
    for key in SCORE_DIMENSIONS:
        # 提取并清洗证据
        items = [str(item).strip() for item in raw.dimension_evidence.get(key, []) if str(item).strip()]
        evidence[key] = items

        # 无证据强制 0 分
        if not items:
            scores[key] = 0
            continue

        raw_score = raw.dimension_scores.get(key, 0)
        if not isinstance(raw_score, (int, float)):
            try:
                raw_score = float(raw_score)
            except (ValueError, TypeError):
                raw_score = 0.0

        scores[key] = max(0, min(100, round(float(raw_score))))

    overall = round(sum(scores.values()) / len(SCORE_DIMENSIONS))

    return {
        "overall_score": overall,
        "dimension_scores": scores,
        "dimension_evidence": evidence,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


# ── ProfileService ────────────────────────────────────────────────────

class ProfileService:
    """学习者画像服务 V2 — CRUD、LLM 异步推理、全局评分。"""

    def __init__(self, *, module: str = "mentor") -> None:
        self.module = module
        self.llm = get_llm()

    async def get_profile(self, *, user_id: int) -> GlobalProfile | None:
        """获取用户的全局画像（不存在返回 None）。"""
        async with session_scope() as db:
            return (
                await db.exec(
                    select(GlobalProfile).where(
                        GlobalProfile.user_id == user_id,
                        GlobalProfile.module == self.module,
                    )
                )
            ).first()

    async def get_or_create_global_profile(self, *, user_id: int) -> GlobalProfile:
        """获取或创建用户的全局画像。"""
        async with session_scope() as db:
            stmt = select(GlobalProfile).where(
                GlobalProfile.user_id == user_id,
                GlobalProfile.module == self.module,
            )
            profile = (await db.exec(stmt)).first()
            if not profile:
                profile = GlobalProfile(
                    user_id=user_id,
                    module=self.module,
                    profile_json=make_default_profile_json(),
                    profile_score_json=make_default_score_json(),
                )
                db.add(profile)
                await db.flush()
            return profile

    async def get_course_profiles(self, *, user_id: int) -> list[CourseProfile]:
        """获取用户的所有课程子画像。"""
        async with session_scope() as db:
            stmt = select(CourseProfile).where(
                CourseProfile.user_id == user_id,
                CourseProfile.module == self.module,
            )
            return list((await db.exec(stmt)).all())

    async def get_onboarding(self, *, user_id: int) -> dict[str, Any]:
        """获取用户 onboarding 基础信息。"""
        profile = await self.get_profile(user_id=user_id)
        if profile and profile.profile_json:
            return profile.profile_json.get("base_info") or {}
        return {}

    async def get_profile_markdown(
        self,
        user_id: int,
        course_name: str | None = None,
        dimension: str | None = None,
    ) -> str:
        """将画像转为 Markdown 文本，供 LLM prompt 注入。"""
        global_profile = await self.get_or_create_global_profile(user_id=user_id)
        profile_json = global_profile.profile_json or {}

        if not course_name:
            if dimension and profile_json:
                field_data = profile_json.get("dimensions", {}).get(dimension, {})
                if not field_data and dimension == "base_info":
                    field_data = profile_json.get("base_info", {})
                return f"```json\n{json.dumps({dimension: field_data}, ensure_ascii=False, indent=2)}\n```"
            return f"```json\n{json.dumps(profile_json, ensure_ascii=False, indent=2)}\n```"

        # 包含特定课程子画像
        course_profiles = await self.get_course_profiles(user_id=user_id)
        target_key = normalize_course_key(course_name)
        target_profile = None
        for cp in course_profiles:
            if cp.course_key == target_key or cp.course_name == course_name or course_name in cp.aliases:
                target_profile = cp
                break

        course_md = target_profile.profile_markdown if target_profile else make_default_course_markdown(course_name)
        global_summary = json.dumps(profile_json, ensure_ascii=False, indent=2)

        return (
            f"【全局画像信息】\n```json\n{global_summary}\n```\n\n"
            f"【{course_name} 课程画像】\n{course_md}"
        )

    async def update_from_onboarding(
        self,
        *,
        user_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """更新 onboarding 基本信息（仅数据库层写入，不执行 LLM）。"""
        async with session_scope() as db:
            base_info = payload.copy()
            school_name = base_info.get("school")
            if school_name:
                school = (await db.exec(select(School).where(School.name == school_name).limit(1))).first()
                base_info["school_level"] = school.level if school and school.level else None

            profile = await self.get_or_create_global_profile(user_id=user_id)
            profile = await db.merge(profile)

            profile_json = profile.profile_json or make_default_profile_json()
            profile_json["base_info"] = base_info
            profile.profile_json = profile_json
            profile.updated_at = datetime.now(timezone.utc)

            db.add(profile)
            await db.flush()

            return {
                "user_id": profile.user_id,
                "module": profile.module,
                "profile_json": profile.profile_json or {},
                "updated_at": profile.updated_at,
            }

    async def run_onboarding_inference(self, *, user_id: int, payload: dict[str, Any]) -> None:
        """后台任务：onboarding 推理和首次评分。"""
        try:
            async with session_scope() as db:
                base_info = payload.copy()
                school_name = base_info.get("school")
                if school_name:
                    school = (await db.exec(select(School).where(School.name == school_name).limit(1))).first()
                    base_info["school_level"] = school.level if school and school.level else None

                # LLM 推理增量
                prompt = prompts.get("profile").render(
                    "onboarding",
                    onboarding_data=json.dumps(base_info, ensure_ascii=False),
                )
                resp = await self.llm.ainvoke_json(
                    OnboardingGlobalInferenceOutput,
                    [HumanMessage(content=prompt)],
                    temperature=0.1,
                )

                profile = await self.get_or_create_global_profile(user_id=user_id)
                profile = await db.merge(profile)

                profile_json = profile.profile_json or make_default_profile_json()
                profile_json["base_info"] = base_info
                profile_json = merge_global_dimensions(profile_json, resp.dimensions_patch)
                profile.profile_json = profile_json
                profile.updated_at = datetime.now(timezone.utc)

                db.add(profile)
                await db.flush()

            # 刷新全局评分
            await self.refresh_global_profile_score(user_id=user_id)
        except Exception as exc:
            logger.warning("[ProfileService] background onboarding inference failed: %s", exc)

    async def update_global_from_tutoring(self, *, user_id: int, session_id: str) -> dict[str, Any]:
        """从会话中推理更新全局稳定画像特征。"""
        async with session_scope() as db:
            global_profile = await self.get_or_create_global_profile(user_id=user_id)
            global_profile = await db.merge(global_profile)
            profile_json = global_profile.profile_json or {}

            recent_dialogue = ""
            recent_dialogue, _ = await self._build_recent_dialogue(
                db=db,
                user_id=user_id,
                session_id=session_id,
            )

            long_term_memory = await self._get_long_term_memory_text(user_id=user_id)

            prompt = prompts.get("profile").render(
                "global_update",
                profile_json=json.dumps(profile_json, ensure_ascii=False),
                recent_dialogue=recent_dialogue,
                long_term_memory=long_term_memory,
            )
            resp = await self.llm.ainvoke_json(
                GlobalTutoringInferenceOutput,
                [HumanMessage(content=prompt)],
                temperature=0.1,
            )

            updated = False
            if resp.should_update and resp.dimensions_patch:
                profile_json = merge_global_dimensions(profile_json, resp.dimensions_patch)
                global_profile.profile_json = profile_json
                global_profile.updated_at = datetime.now(timezone.utc)
                db.add(global_profile)
                await db.flush()
                updated = True

        if updated:
            await self.refresh_global_profile_score(user_id=user_id)

        return {
            "profile_updated": updated,
            "profile_json": global_profile.profile_json or {},
            "updated_at": global_profile.updated_at,
        }

    async def update_course_from_tutoring(
        self,
        *,
        user_id: int,
        session_id: str,
        course_name: str,
        active_topic: str | None = None,
    ) -> dict[str, Any]:
        """从会话中推理并重写单一课程子画像 Markdown。"""
        async with session_scope() as db:
            global_profile = await self.get_or_create_global_profile(user_id=user_id)
            global_profile = await db.merge(global_profile)
            global_profile_id = global_profile.id

            course_profiles = await self.get_course_profiles(user_id=user_id)
            target_key = normalize_course_key(course_name)

            target_profile = None
            for cp in course_profiles:
                if cp.course_key == target_key or cp.course_name == course_name or course_name in cp.aliases:
                    target_profile = cp
                    break

            if not target_profile:
                target_profile = CourseProfile(
                    global_profile_id=global_profile_id,
                    user_id=user_id,
                    module=self.module,
                    course_key=target_key,
                    course_name=course_name,
                    aliases=[],
                    profile_markdown=make_default_course_markdown(course_name),
                )
                db.add(target_profile)
                await db.flush()
            else:
                target_profile = await db.merge(target_profile)

            # 整理已有课程简要列表，避免 LLM 起重名重复课程
            course_list = [
                {
                    "course_name": cp.course_name,
                    "course_key": cp.course_key,
                    "aliases": cp.aliases,
                    "preview": cp.profile_markdown[:200]
                }
                for cp in course_profiles
            ]

            recent_dialogue, _ = await self._build_recent_dialogue(
                db=db,
                user_id=user_id,
                session_id=session_id,
            )
            long_term_memory = await self._get_long_term_memory_text(user_id=user_id)

            prompt = prompts.get("profile").render(
                "course_update",
                profile_json=json.dumps(global_profile.profile_json, ensure_ascii=False),
                course_list=json.dumps(course_list, ensure_ascii=False),
                target_course=course_name,
                old_markdown=target_profile.profile_markdown,
                recent_dialogue=recent_dialogue,
                long_term_memory=long_term_memory,
                active_topic=active_topic or "无",
            )

            resp = await self.llm.ainvoke(
                [HumanMessage(content=prompt)],
                temperature=0.1,
            )

            markdown_text = validate_course_markdown(str(resp.content or ""), course_name)
            updated = False
            if markdown_text and markdown_text != target_profile.profile_markdown:
                target_profile.profile_markdown = markdown_text
                target_profile.updated_at = datetime.now(timezone.utc)
                db.add(target_profile)
                await db.flush()
                updated = True

        if updated:
            await self.refresh_global_profile_score(user_id=user_id)

        return {
            "profile_updated": updated,
            "course_name": course_name,
            "profile_markdown": target_profile.profile_markdown,
            "updated_at": target_profile.updated_at,
        }

    async def refresh_global_profile_score(self, *, user_id: int) -> dict[str, Any]:
        """重新计算并刷新用户的全局打分。打分输入 = 全局画像 JSON + 课程画像 Markdown 拼接。"""
        async with session_scope() as db:
            global_profile = await self.get_or_create_global_profile(user_id=user_id)
            global_profile = await db.merge(global_profile)

            course_profiles = await self.get_course_profiles(user_id=user_id)
            course_markdown_list = []
            for cp in course_profiles:
                course_markdown_list.append(cp.profile_markdown)

            concatenated_markdown = "\n\n---\n\n".join(course_markdown_list)

            prompt = prompts.get("profile").render(
                "score",
                profile_text=json.dumps(global_profile.profile_json, ensure_ascii=False),
                course_markdown=concatenated_markdown,
            )

            resp = await self.llm.ainvoke_json(
                ProfileScoreOutput,
                [HumanMessage(content=prompt)],
                temperature=0.1,
            )

            scores = validate_score_output(resp)
            global_profile.profile_score_json = scores
            global_profile.updated_at = datetime.now(timezone.utc)

            db.add(global_profile)
            await db.flush()

            return scores



    # ── Private Helpers ───────────────────────────────────────────────────

    async def _build_recent_dialogue(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        max_messages: int = 20,
        after_message_id: int = 0,
    ) -> tuple[str, int]:
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == self.module,
                ChatMessage.role.in_(["user", "assistant"]),
                ChatMessage.id > after_message_id,
            )
            .order_by(ChatMessage.id.desc())
            .limit(max_messages)
        )
        messages = list((await db.exec(stmt)).all())
        if not messages:
            return "", after_message_id
        lines: list[str] = []
        latest_message_id = after_message_id
        for msg in reversed(messages):
            latest_message_id = max(latest_message_id, int(msg.id or 0))
            role_label = "学生" if msg.role == "user" else "辅导老师"
            content = (msg.content or "").strip()
            if content:
                lines.append(f"{role_label}：{content[:500]}")
        return "\n".join(lines), latest_message_id

    async def _get_long_term_memory_text(self, *, user_id: int) -> str:
        async with session_scope() as db:
            ltm = (
                await db.exec(
                    select(ChatLongTermMemory).where(
                        ChatLongTermMemory.user_id == user_id,
                        ChatLongTermMemory.module == self.module,
                    )
                )
            ).first()
            if ltm and ltm.memory_markdown:
                return ltm.memory_markdown
        return ""


_profile_service_cache: dict[str, ProfileService] = {}


def get_profile_service(*, module: str = "mentor") -> ProfileService:
    if module not in _profile_service_cache:
        _profile_service_cache[module] = ProfileService(module=module)
    return _profile_service_cache[module]


__all__ = [
    "ProfileService",
    "get_profile_service",
    "normalize_course_key",
    "merge_global_dimensions",
    "validate_score_output",
    "validate_course_markdown",
]
