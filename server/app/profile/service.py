"""共享学习者画像服务 — 全局画像 CRUD、课程画像管理、LLM 推理与评分。"""

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

from sqlalchemy.dialects.postgresql import insert as pg_insert

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
    ALL_DIMENSIONS,
    DIMENSION_NAMES,
    KNOWLEDGE_DIMENSIONS,
    COGNITIVE_DIMENSIONS,
    DimensionValue,
    OnboardingGlobalInferenceOutput,
    GlobalTutoringInferenceOutput,
    ProfileScoreOutput,
    make_default_profile_json,
    make_default_score_json,
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
    """校验并规范化 LLM 生成的课程画像 Markdown 文本。"""
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
    """合并全局画像维度增量更新。只更新支持的七个维度。"""
    merged = deepcopy(profile_json) if profile_json else make_default_profile_json()
    dimensions = merged.setdefault("dimensions", {})
    for key, val in patch.items():
        if key in ALL_DIMENSIONS:
            if isinstance(val, dict):
                dimensions[key] = {
                    "value": str(val.get("value", "")).strip(),
                    "evidence": [str(item).strip() for item in val.get("evidence", []) if str(item).strip()],
                }
            elif isinstance(val, DimensionValue):
                dimensions[key] = {
                    "value": val.value.strip(),
                    "evidence": [item.strip() for item in val.evidence if item.strip()],
                }
    return merged


def validate_score_output(raw: ProfileScoreOutput) -> dict[str, Any]:
    """对打分输出进行后置验证与清洗：
    1. 限制分数在 0..100 之间；
    2. 如果某维度无任何证据记录（为空列表），强制给该维度评分置为 0；
    3. 总体评分为 7 个维度洗净后分数的算术平均值（四舍五入到整数）；
    4. 自动记录评分时间。
    """
    scores = {}
    evidence = {}
    for key in ALL_DIMENSIONS:
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

    overall = round(sum(scores.values()) / len(ALL_DIMENSIONS))

    return {
        "overall_score": overall,
        "dimension_scores": scores,
        "dimension_evidence": evidence,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


# ── ProfileService ────────────────────────────────────────────────────

class ProfileService:
    """学习者画像服务 — CRUD、LLM 推理与评分。"""

    def __init__(self, *, module: str = "mentor") -> None:
        self.module = module
        self.llm = get_llm()

    async def get_or_create_global_profile(
        self,
        *,
        user_id: int,
        db: AsyncSession | None = None,
    ) -> GlobalProfile:
        """获取或创建用户的全局画像。

        使用 INSERT ... ON CONFLICT DO NOTHING 保证并发安全。

        Args:
            user_id: 用户 ID。
            db: 可选的已有数据库会话。传入时复用该会话，不传时自动创建短生命周期会话。
        """
        async def _upsert(db: AsyncSession) -> GlobalProfile:
            now = datetime.now(timezone.utc)
            stmt = pg_insert(GlobalProfile).values(
                user_id=user_id,
                module=self.module,
                profile_json=make_default_profile_json(),
                profile_score_json=make_default_score_json(),
                created_at=now,
                updated_at=now,
            ).on_conflict_do_nothing(
                constraint="uq_global_profile_user_module",
            )
            await db.exec(stmt)  # type: ignore[arg-type]
            await db.flush()

            profile = (
                await db.exec(
                    select(GlobalProfile).where(
                        GlobalProfile.user_id == user_id,
                        GlobalProfile.module == self.module,
                    )
                )
            ).first()

            if profile is None:
                profile = GlobalProfile(
                    user_id=user_id,
                    module=self.module,
                    profile_json=make_default_profile_json(),
                    profile_score_json=make_default_score_json(),
                )
                db.add(profile)
                await db.flush()

            return profile

        if db is None:
            async with session_scope() as db:
                return await _upsert(db)
        return await _upsert(db)

    async def get_course_profiles(self, *, user_id: int) -> list[CourseProfile]:
        """获取用户的所有课程子画像。"""
        async with session_scope() as db:
            stmt = select(CourseProfile).where(
                CourseProfile.user_id == user_id,
                CourseProfile.module == self.module,
            )
            return list((await db.exec(stmt)).all())

    async def get_profile_for_agents(self, *, user_id: int) -> str:
        """获取用户画像 Markdown，供多智能体资源生成、路径规划和智能辅导使用。

        将 profile_json 中的 base_info 和 7 个维度转换为结构化 Markdown 文本，
        便于 LLM 理解和下游智能体使用。

        Args:
            user_id: 用户 ID

        Returns:
            结构化 Markdown 文本，包含：
            - 基础信息（学校、专业、年级等）
            - 知识层维度（知识基础、易错点偏好、知识缺口模式）
            - 认知层维度（认知风格、学习目标导向、难度耐受度、自纠能力水平）
        """
        global_profile = await self.get_or_create_global_profile(user_id=user_id)
        profile_json = global_profile.profile_json or make_default_profile_json()

        lines: list[str] = ["# 学习者画像"]

        # 1. 基础信息
        base_info = profile_json.get("base_info", {})
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
        dimensions = profile_json.get("dimensions", {})
        lines.append("\n## 知识层维度")

        for dim_key in KNOWLEDGE_DIMENSIONS:
            dim_data = dimensions.get(dim_key, {})
            dim_name = DIMENSION_NAMES.get(dim_key, dim_key)
            value = dim_data.get("value", "")

            lines.append(f"\n### {dim_name}")
            if value:
                lines.append(value)
            else:
                lines.append("暂无明确画像")

        # 3. 认知层维度
        lines.append("\n## 认知层维度")

        for dim_key in COGNITIVE_DIMENSIONS:
            dim_data = dimensions.get(dim_key, {})
            dim_name = DIMENSION_NAMES.get(dim_key, dim_key)
            value = dim_data.get("value", "")

            lines.append(f"\n### {dim_name}")
            if value:
                lines.append(value)
            else:
                lines.append("暂无明确画像")

        return "\n".join(lines)

    async def update_from_onboarding(
        self,
        *,
        user_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """更新 onboarding 基本信息（仅数据库层写入，不执行 LLM）。"""
        logger.info("[ProfileService] onboarding 写入开始: user_id=%s school=%s major=%s",
                     user_id, payload.get("school"), payload.get("major"))
        async with session_scope() as db:
            base_info = payload.copy()
            school_name = base_info.get("school")
            if school_name:
                school = (await db.exec(select(School).where(School.name == school_name).limit(1))).first()
                base_info["school_level"] = school.level if school and school.level else None

            profile = await self.get_or_create_global_profile(user_id=user_id, db=db)

            profile_json = profile.profile_json or make_default_profile_json()
            profile_json["base_info"] = base_info
            profile.profile_json = profile_json
            profile.updated_at = datetime.now(timezone.utc)

            db.add(profile)
            await db.flush()

            result = {
                "user_id": profile.user_id,
                "module": profile.module,
                "profile_json": profile.profile_json or {},
                "updated_at": profile.updated_at,
            }
            logger.info("[ProfileService] onboarding 写入完成: user_id=%s updated_at=%s",
                         profile.user_id, profile.updated_at)
            return result

    async def run_onboarding_inference(self, *, user_id: int, payload: dict[str, Any]) -> None:
        """后台任务：onboarding 推理和首次评分。"""
        logger.info("[ProfileService] onboarding LLM推理开始: user_id=%s", user_id)
        try:
            async with session_scope() as db:
                base_info = payload.copy()
                school_name = base_info.get("school")
                if school_name:
                    school = (await db.exec(select(School).where(School.name == school_name).limit(1))).first()
                    base_info["school_level"] = school.level if school and school.level else None

                # LLM 推理增量
                logger.info("[ProfileService] onboarding 调用LLM推理: user_id=%s", user_id)
                prompt = prompts.get("profile").render(
                    "onboarding",
                    onboarding_data=json.dumps(base_info, ensure_ascii=False),
                )
                resp = await self.llm.ainvoke_json(
                    OnboardingGlobalInferenceOutput,
                    [HumanMessage(content=prompt)],
                    temperature=0.1,
                )

                # 精简输出维度推理结果
                dims_summary = {k: v.value[:50] if isinstance(v, DimensionValue) else str(v)[:50]
                                for k, v in resp.dimensions_patch.items()}
                logger.info("[ProfileService] onboarding LLM推理结果: user_id=%s dimensions_patch=%s",
                            user_id, dims_summary)

                profile = await self.get_or_create_global_profile(user_id=user_id, db=db)

                profile_json = profile.profile_json or make_default_profile_json()
                profile_json["base_info"] = base_info
                profile_json = merge_global_dimensions(profile_json, resp.dimensions_patch)
                profile.profile_json = profile_json
                profile.updated_at = datetime.now(timezone.utc)

                db.add(profile)
                await db.flush()

            # 刷新全局评分
            score_result = await self.refresh_global_profile_score(user_id=user_id)
            logger.info("[ProfileService] onboarding 推理+评分完成: user_id=%s dimensions_updated=%s overall_score=%s",
                         user_id, list(dims_summary.keys()), score_result.get("overall_score"))
        except Exception as exc:
            logger.error("[ProfileService] background onboarding inference failed: user_id=%s err=%s", user_id, exc)

    async def update_global_from_tutoring(self, *, user_id: int, session_id: str) -> dict[str, Any]:
        """从会话中推理更新全局稳定画像特征。"""
        logger.info("[ProfileService] 全局画像更新开始: user_id=%s session_id=%s", user_id, session_id)
        async with session_scope() as db:
            global_profile = await self.get_or_create_global_profile(user_id=user_id, db=db)
            profile_json = global_profile.profile_json or {}

            recent_dialogue = ""
            recent_dialogue, _ = await self._build_recent_dialogue(
                db=db,
                user_id=user_id,
                session_id=session_id,
            )

            long_term_memory = await self._get_long_term_memory_text(user_id=user_id)
            logger.info("[ProfileService] 全局画像: recent_dialogue长度=%s long_term_memory长度=%s",
                         len(recent_dialogue), len(long_term_memory))

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

            # 精简输出推理结果
            dims_summary = {k: v.value[:50] if isinstance(v, DimensionValue) else str(v)[:50]
                            for k, v in resp.dimensions_patch.items()}
            logger.info("[ProfileService] 全局画像 LLM推理结果: should_update=%s dimensions_patch=%s",
                         resp.should_update, dims_summary)

            updated = False
            if resp.should_update and resp.dimensions_patch:
                profile_json = merge_global_dimensions(profile_json, resp.dimensions_patch)
                global_profile.profile_json = profile_json
                global_profile.updated_at = datetime.now(timezone.utc)
                db.add(global_profile)
                await db.flush()
                updated = True
                logger.info("[ProfileService] 全局画像更新结果: updated=%s updated_dimensions=%s",
                             updated, list(dims_summary.keys()))

        if updated:
            score_result = await self.refresh_global_profile_score(user_id=user_id)
            logger.info("[ProfileService] 全局画像评分刷新完成: user_id=%s overall_score=%s dimension_scores=%s",
                         user_id, score_result.get("overall_score"), score_result.get("dimension_scores"))

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
        logger.info("[ProfileService] 课程画像更新开始: user_id=%s session_id=%s course_name=%s active_topic=%s",
                     user_id, session_id, course_name, active_topic)
        async with session_scope() as db:
            global_profile = await self.get_or_create_global_profile(user_id=user_id, db=db)
            global_profile_id = global_profile.id

            course_profiles = await self.get_course_profiles(user_id=user_id)
            target_key = normalize_course_key(course_name)

            target_profile = None
            for cp in course_profiles:
                if cp.course_key == target_key or cp.course_name == course_name or course_name in cp.aliases:
                    target_profile = cp
                    break

            is_new_course = target_profile is None
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
                logger.info("[ProfileService] 课程画像新建: course_key=%s course_name=%s", target_key, course_name)
            else:
                target_profile = await db.merge(target_profile)
                logger.info("[ProfileService] 课程画像已存在: course_key=%s course_name=%s", target_key, course_name)

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
            logger.info("[ProfileService] 课程画像: recent_dialogue长度=%s long_term_memory长度=%s",
                         len(recent_dialogue), len(long_term_memory))

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

            raw_content = str(resp.content or "")
            logger.info("[ProfileService] 课程画像 LLM生成Markdown: 长度=%s 前200字=%s",
                         len(raw_content), raw_content[:200])

            markdown_text = validate_course_markdown(raw_content, course_name)
            logger.info("[ProfileService] 课程画像Markdown验证通过: course_name=%s", course_name)

            updated = False
            if markdown_text and markdown_text != target_profile.profile_markdown:
                target_profile.profile_markdown = markdown_text
                target_profile.updated_at = datetime.now(timezone.utc)
                db.add(target_profile)
                await db.flush()
                updated = True

            logger.info("[ProfileService] 课程画像更新结果: updated=%s markdown长度=%s",
                         updated, len(target_profile.profile_markdown or ""))

        if updated:
            score_result = await self.refresh_global_profile_score(user_id=user_id)
            logger.info("[ProfileService] 课程画像评分刷新完成: user_id=%s overall_score=%s",
                         user_id, score_result.get("overall_score"))

        return {
            "profile_updated": updated,
            "course_name": course_name,
            "profile_markdown": target_profile.profile_markdown,
            "updated_at": target_profile.updated_at,
        }

    async def refresh_global_profile_score(self, *, user_id: int) -> dict[str, Any]:
        """重新计算并刷新用户的全局打分。打分输入 = 全局画像 JSON + 课程画像 Markdown 拼接。"""
        logger.info("[ProfileService] 全局评分刷新开始: user_id=%s", user_id)
        async with session_scope() as db:
            global_profile = await self.get_or_create_global_profile(user_id=user_id, db=db)

            course_profiles = await self.get_course_profiles(user_id=user_id)
            course_markdown_list = []
            for cp in course_profiles:
                course_markdown_list.append(cp.profile_markdown)

            concatenated_markdown = "\n\n---\n\n".join(course_markdown_list)
            logger.info("[ProfileService] 全局评分: course_profiles数量=%s markdown总长度=%s",
                         len(course_profiles), len(concatenated_markdown))

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

            logger.info("[ProfileService] 全局评分 LLM原始结果: dimension_scores=%s dimension_evidence_keys=%s",
                         resp.dimension_scores, list(resp.dimension_evidence.keys()))

            scores = validate_score_output(resp)
            global_profile.profile_score_json = scores
            global_profile.updated_at = datetime.now(timezone.utc)

            db.add(global_profile)
            await db.flush()

            logger.info("[ProfileService] 全局评分刷新完成: user_id=%s overall_score=%s dimension_scores=%s",
                         user_id, scores.get("overall_score"), scores.get("dimension_scores"))

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
        """构建最近对话文本，用于画像推理上下文注入。"""
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
        """获取用户的长期记忆 Markdown 文本。"""
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
    """获取指定模块的画像服务单例（带缓存）。"""
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
