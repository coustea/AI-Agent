"""Shared learner profile service."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import session_scope
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatSession, ChatSessionSummaryBlock, ChatLongTermMemory, CourseProfile, GlobalProfile, School
from app.profile.types import (
    OnboardingInferenceOutput,
    PROFILE_MESSAGE_THRESHOLD,
    PROFILE_TOKEN_THRESHOLD,
    PROFILE_UPDATE_COOLDOWN_MINUTES,
    ProfileScoreOutput,
    TutoringInferenceOutput,
    make_default_profile_json,
    make_default_score_json,
)
from app.infra.prompts import prompts

logger = get_logger(__name__)


class ProfileService:
    """学习者画像服务 — CRUD、LLM 推理、评分。"""

    def __init__(self, *, module: str = "mentor") -> None:
        self.module = module  # 所属功能模块
        self.llm = get_llm()  # LLM 单例

    async def get_profile(
        self,
        *,
        user_id: int,
        course_name: str | None = None,
    ) -> GlobalProfile | CourseProfile | None:
        """获取用户画像（不存在返回 None）。"""
        async with session_scope() as db:
            return await self._get_profile_db(db=db, user_id=user_id, course_name=course_name)

    async def get_or_create_profile(
        self,
        *,
        user_id: int,
        course_name: str | None = None,
    ) -> GlobalProfile | CourseProfile:
        """获取或创建用户画像（不存在则自动创建默认画像）。"""
        async with session_scope() as db:
            profile = await self._get_profile_db(db=db, user_id=user_id, course_name=course_name)
            if profile:
                return profile
            return await self._upsert_profile(  # 创建默认画像
                db=db,
                user_id=user_id,
                profile_data=make_default_profile_json(),
                course_name=course_name,
            )

    async def get_onboarding(self, *, user_id: int) -> dict[str, Any]:
        """获取用户 onboarding 基础信息（学校、年级、专业等）。"""
        async with session_scope() as db:
            profile = await self._get_profile_db(db=db, user_id=user_id)
            if profile and profile.profile_json:
                return profile.profile_json.get("base_info") or {}  # 从画像中提取基础信息
            return {}

    async def get_profile_markdown(
        self,
        user_id: int,
        course_name: str | None = None,
        dimension: str | None = None,
    ) -> str:
        """将画像转为 Markdown 文本，供 LLM prompt 注入。"""
        async with session_scope() as db:
            profile = await self._get_profile_db(db=db, user_id=user_id, course_name=course_name)
            if not profile:
                return "暂无画像信息（新用户），请直接开始对话。"

            profile_json = profile.profile_json or {}
            if dimension and profile_json:
                field_data = profile_json.get(dimension, {})
                return f"```json\n{json.dumps({dimension: field_data}, ensure_ascii=False, indent=2)}\n```"
            if profile_json:
                return f"```json\n{json.dumps(profile_json, ensure_ascii=False, indent=2)}\n```"
            return "暂无画像信息。"

    async def update_from_onboarding(
        self,
        *,
        user_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """保存 onboarding 数据并立即返回（LLM 推理在后台异步执行）。"""
        async with session_scope() as db:
            base_info = payload.copy()
            school_name = base_info.get("school")
            if school_name:  # 查询学校层次信息
                school = (await db.exec(select(School).where(School.name == school_name).limit(1))).first()
                base_info["school_level"] = school.level if school and school.level else None

            profile = await self._upsert_profile(db=db, user_id=user_id, profile_data=base_info)  # 持久化基础信息

            return {
                "user_id": profile.user_id,
                "module": profile.module,
                "profile_json": profile.profile_json or {},
                "updated_at": profile.updated_at,
            }

    async def run_onboarding_inference(self, *, user_id: int, payload: dict[str, Any]) -> None:
        """后台任务：onboarding 保存后执行 LLM 推理和评分。"""
        try:
            async with session_scope() as db:
                base_info = payload.copy()
                school_name = base_info.get("school")
                if school_name:
                    school = (await db.exec(select(School).where(School.name == school_name).limit(1))).first()
                    base_info["school_level"] = school.level if school and school.level else None

                patch = await self._infer_onboarding_patch(base_info)
                base_info.update(patch)

                profile = await self._upsert_profile(db=db, user_id=user_id, profile_data=base_info)
                if profile.profile_json:
                    scores = await self.compute_scores(profile_json=profile.profile_json)
                    if scores:
                        profile.profile_score_json = scores
                        await db.flush()
        except Exception as exc:
            logger.warning("[ProfileService] background onboarding inference failed: %s", exc)

    async def process_tutoring_update(
        self,
        *,
        user_id: int,
        course_name: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """处理辅导产生的画像增量更新 — 从对话中提取学习信号并更新画像。"""
        async with session_scope() as db:
            global_profile = await self._upsert_profile(db=db, user_id=user_id, profile_data={})
            profile_json = global_profile.profile_json or {}

            recent_dialogue = ""
            if session_id:
                recent_dialogue, _ = await self._build_recent_dialogue(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                )

            long_term_memory = await self._get_long_term_memory_text(user_id=user_id)
            global_patch, course_patch = await self.infer_tutoring_patch(
                user_id=user_id,
                profile_json=profile_json,
                recent_dialogue=recent_dialogue,
                long_term_memory=long_term_memory,
            )

            if global_patch:
                await self._upsert_profile(db=db, user_id=user_id, profile_data=global_patch)

            profile = await self._upsert_profile(
                db=db,
                user_id=user_id,
                profile_data=course_patch,
                course_name=course_name,
            )
            if profile.profile_json:
                scores = await self.compute_scores(profile_json=profile.profile_json)
                if scores:
                    profile.profile_score_json = scores
                    await db.flush()

            updated = bool(global_patch or course_patch)
            logger.info("[ProfileService] 画像数据已保存: user_id=%s updated=%s", user_id, updated)
            return {
                "profile_updated": updated,
                "course_name": profile.course_name,
                "profile_json": profile.profile_json or {},
                "updated_at": profile.updated_at,
            }

    async def apply_tutoring_profile_update(
        self,
        *,
        user_id: int,
        course_name: str | None = None,
        payload: dict[str, Any],
    ) -> Any:
        """直接应用画像增量更新（来自评估事件等外部信号）。"""
        async with session_scope() as db:
            return await self._upsert_profile(
                db=db,
                user_id=user_id,
                profile_data=payload,
                course_name=course_name,
            )

    async def maybe_update_from_tutoring_turn(
        self,
        *,
        user_id: int,
        session_id: str,
    ) -> bool:
        """检查是否需要从辅导对话中更新画像（基于消息数/Token 数阈值和冷却时间）。"""
        async with session_scope() as db:
            chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
            if not chat_session:
                return False

            token_count = chat_session.profile_token_count or 0
            message_count = chat_session.profile_message_count or 0
            threshold_due = token_count >= PROFILE_TOKEN_THRESHOLD or message_count >= PROFILE_MESSAGE_THRESHOLD
            if not threshold_due:
                return False

            last_updated = chat_session.last_profile_updated_at
            now_dt = datetime.now(timezone.utc)
            if last_updated and (now_dt - last_updated).total_seconds() < PROFILE_UPDATE_COOLDOWN_MINUTES * 60:
                return False

            global_profile = await self._get_profile_db(db=db, user_id=user_id)
            profile_json = global_profile.profile_json if global_profile and global_profile.profile_json else {}

            active_courses = profile_json.get("base_info", {}).get("courses", [])
            course_name = ""
            if active_courses and isinstance(active_courses, list):
                first_course = active_courses[0]
                if isinstance(first_course, dict):
                    course_name = first_course.get("course", "")
                elif isinstance(first_course, str):
                    course_name = first_course

            after_message_id = int(chat_session.last_profile_message_id or 0)
            incremental_dialogue, latest_message_id = await self._build_recent_dialogue(
                db=db,
                user_id=user_id,
                session_id=session_id,
                after_message_id=after_message_id,
                max_messages=40,
            )
            if not incremental_dialogue or latest_message_id <= after_message_id:
                return False

            summary_context = await self._build_session_summary_context(
                db=db,
                user_id=user_id,
                session_id=session_id,
            )
            recent_dialogue = (
                f"【最近会话摘要】\n{summary_context or '暂无会话摘要。'}\n\n"
                f"【上次画像分析后新增对话】\n{incremental_dialogue}"
            )
            long_term_memory = await self._get_long_term_memory_text(user_id=user_id)

            global_patch, course_patch = await self.infer_tutoring_patch(
                user_id=user_id,
                profile_json=profile_json,
                recent_dialogue=recent_dialogue,
                long_term_memory=long_term_memory,
            )

            if global_patch:
                await self._upsert_profile(db=db, user_id=user_id, profile_data=global_patch)

            if course_patch and course_name:
                profile = await self._upsert_profile(
                    db=db,
                    user_id=user_id,
                    profile_data=course_patch,
                    course_name=course_name,
                )
                if profile.profile_json:
                    scores = await self.compute_scores(profile_json=profile.profile_json)
                    if scores:
                        profile.profile_score_json = scores
                        await db.flush()

            updated = bool(global_patch or (course_patch and course_name))
            chat_session.profile_token_count = 0
            chat_session.profile_message_count = 0
            chat_session.last_profile_message_id = latest_message_id
            chat_session.last_profile_updated_at = now_dt
            db.add(chat_session)
            return updated

    async def infer_tutoring_patch(
        self,
        *,
        user_id: int,
        profile_json: dict[str, Any],
        recent_dialogue: str,
        long_term_memory: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """使用 LLM 从对话中推断画像更新补丁（全局画像 + 课程画像）。"""
        global_patch: dict[str, Any] = {}
        course_patch: dict[str, Any] = {}
        try:
            prompt = prompts.get("profile").render(
                "profile",
                profile_json=json.dumps(profile_json, ensure_ascii=False),
                recent_dialogue=recent_dialogue,
                long_term_memory=long_term_memory,
            )
            resp = await self.llm.ainvoke_json(
                TutoringInferenceOutput,
                [HumanMessage(content=prompt)],
                temperature=0.1,
            )
            if resp.should_update:
                global_patch = resp.global_profile_patch
                if resp.course_profile_patch:
                    course_patch.update(resp.course_profile_patch)
                if resp.knowledge_mastery_patch:
                    course_patch["knowledge_mastery"] = resp.knowledge_mastery_patch
        except Exception as exc:
            logger.warning("[ProfileService] tutoring inference failed: %s", exc)
        return global_patch, course_patch

    async def compute_scores(self, *, profile_json: dict[str, Any]) -> dict[str, Any] | None:
        """使用 LLM 计算画像综合评分和维度分数。"""
        if not profile_json:
            return None
        try:
            prompt = prompts.get("profile").render(
                "score",
                profile_text=json.dumps(profile_json, ensure_ascii=False),
            )
            resp = await self.llm.ainvoke_json(
                ProfileScoreOutput,
                [HumanMessage(content=prompt)],
                temperature=0.1,
            )
            return resp.model_dump()
        except Exception as exc:
            logger.warning("[ProfileService] compute_scores failed: %s", exc)
            return None

    async def _get_profile_db(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        course_name: str | None = None,
    ) -> GlobalProfile | CourseProfile | None:
        if course_name:
            stmt = select(CourseProfile).where(
                CourseProfile.user_id == user_id,
                CourseProfile.module == self.module,
                CourseProfile.course_name == course_name,
            )
        else:
            stmt = select(GlobalProfile).where(
                GlobalProfile.user_id == user_id,
                GlobalProfile.module == self.module,
            )
        return (await db.exec(stmt)).first()

    async def _upsert_profile(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        profile_data: dict[str, Any],
        course_name: str | None = None,
    ) -> GlobalProfile | CourseProfile:
        """Upsert 画像：存在则合并更新，不存在则创建。"""
        if course_name:
            stmt = select(CourseProfile).where(
                CourseProfile.user_id == user_id,
                CourseProfile.module == self.module,
                CourseProfile.course_name == course_name,
            )
            profile = (await db.exec(stmt)).first()
            if not profile:
                profile = CourseProfile(
                    user_id=user_id,
                    module=self.module,
                    course_name=course_name,
                    profile_json={},
                    profile_score_json=make_default_score_json(),
                )
                db.add(profile)
                await db.flush()
        else:
            stmt = select(GlobalProfile).where(
                GlobalProfile.user_id == user_id,
                GlobalProfile.module == self.module,
            )
            profile = (await db.exec(stmt)).first()
            if not profile:
                profile = GlobalProfile(
                    user_id=user_id,
                    module=self.module,
                    profile_json={},
                    profile_score_json=make_default_score_json(),
                )
                db.add(profile)
                await db.flush()

        if profile_data:
            merged = deepcopy(profile.profile_json) if profile.profile_json else {}  # 深拷贝避免修改原始数据
            merged.update(profile_data)  # 合并新数据到现有画像
            profile.profile_json = merged
            profile.updated_at = datetime.now(timezone.utc)
            await db.flush()  # 刷新到数据库但不提交事务

        return profile

    async def _infer_onboarding_patch(self, base_info: dict[str, Any]) -> dict[str, Any]:
        """使用 LLM 从 onboarding 数据推断画像补丁。"""
        try:
            prompt = prompts.get("profile").render(
                "onboarding",
                onboarding_data=json.dumps(base_info, ensure_ascii=False),
            )
            resp = await self.llm.ainvoke_json(
                OnboardingInferenceOutput,
                [HumanMessage(content=prompt)],
                temperature=0.1,
            )
            return resp.global_profile_patch
        except Exception as exc:
            logger.warning("[ProfileService] onboarding inference failed: %s", exc)
            return {}

    async def _build_recent_dialogue(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        max_messages: int = 20,
        after_message_id: int = 0,
    ) -> tuple[str, int]:
        """构建最近对话文本（学生/辅导老师角色标记），用于画像推断。"""
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

    async def _build_session_summary_context(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        limit: int = 3,
    ) -> str:
        """构建会话摘要上下文（最近 N 个压缩块）。"""
        stmt = (
            select(ChatSessionSummaryBlock)
            .where(
                ChatSessionSummaryBlock.user_id == user_id,
                ChatSessionSummaryBlock.session_id == session_id,
                ChatSessionSummaryBlock.module == self.module,
            )
            .order_by(ChatSessionSummaryBlock.created_at.desc())
            .limit(limit)
        )
        blocks = list((await db.exec(stmt)).all())
        if not blocks:
            return ""
        blocks.reverse()
        return "\n\n".join(block.summary_markdown for block in blocks if block.summary_markdown)

    async def _get_long_term_memory_text(self, *, user_id: int) -> str:
        """获取用户长期记忆文本（用于画像推断的跨会话上下文）。"""
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


_profile_service_cache: dict[str, ProfileService] = {}  # 按模块缓存 ProfileService 单例


def get_profile_service(*, module: str = "mentor") -> ProfileService:
    """获取 ProfileService 单例（按模块名缓存）。"""
    if module not in _profile_service_cache:
        _profile_service_cache[module] = ProfileService(module=module)
    return _profile_service_cache[module]


__all__ = ["ProfileService", "get_profile_service"]
