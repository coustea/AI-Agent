"""学习者画像服务 — 全局画像 CRUD、周度学习摘要、LLM 推理与评分。

架构：全局画像 JSON 是面向前端展示的唯一权威数据；周度学习摘要（WeeklyLearningDigest）
作为评分的缓冲证据层，先聚合本周跨系统学习行为，再由 score_profile 流程消费。
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.messages import HumanMessage
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from sqlalchemy import func as sa_func
from sqlalchemy import or_ as sa_or
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.infra.database import session_scope
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import (
    ChatLongTermMemory,
    ChatSession,
    ChatSessionSummaryBlock,
    GeneratedResource,
    GeneratedResourceItem,
    GlobalProfile,
    LearningEvent,
    LearningPath,
    LearningSession,
    PathNode,
    PathNodeQuestion,
    School,
    WeeklyLearningDigest,
)
from app.profile.types import (
    ALL_DIMENSIONS,
    DIMENSION_NAMES,
    KNOWLEDGE_DIMENSIONS,
    COGNITIVE_DIMENSIONS,
    DimensionValue,
    ProfileDimensionsPatch,
    GlobalTutoringInferenceOutput,
    ProfileScoreOutput,
    default_profile_json,
    default_score_json,
)
from app.infra.prompts import prompts

logger = get_logger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────

# 一周结束的边界 = 下周一 00:00 减去 1 微秒，即周日 23:59:59.999999 UTC。
_NEXT_MONDAY_MINUS_ONE_MICRO: timedelta = timedelta(microseconds=1)


def _utc_week_range(now: datetime | None = None) -> tuple[datetime, datetime]:
    """计算给定时间所在自然周（周一 00:00 ~ 周日 23:59:59.999999）的 UTC 范围。"""
    now = now or datetime.now(timezone.utc)
    weekday = now.weekday()  # Monday=0, Sunday=6
    week_start = (now - timedelta(days=weekday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=7) - _NEXT_MONDAY_MINUS_ONE_MICRO
    return week_start, week_end


def _format_week_label(week_start: datetime, week_end: datetime) -> str:
    """生成 week_range 标签供 prompt 使用，如 '2026-W27: 2026-07-06 ~ 2026-07-12'。"""
    iso_year, iso_week, _ = week_start.isocalendar()
    start_str = week_start.strftime("%Y-%m-%d")
    end_str = week_end.strftime("%Y-%m-%d")
    return f"{iso_year}-W{iso_week:02d}: {start_str} ~ {end_str}"


def merge_dimensions(profile_json: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """合并画像维度增量更新。只更新支持的七个维度。"""
    merged = deepcopy(profile_json) if profile_json else deepcopy(default_profile_json)
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


def sanitize_score_output(raw: ProfileScoreOutput) -> dict[str, Any]:
    """对打分输出进行后置验证与清洗。

    1. 限制分数在 0..100 之间；
    2. 如果某维度无任何证据记录，强制给该维度评分置为 0；
    3. 总体评分为 7 个维度洗净后分数的算术平均值（四舍五入到整数）；
    4. 自动记录评分时间。
    """
    scores = {}
    evidence = {}
    for key in ALL_DIMENSIONS:
        items = [str(item).strip() for item in raw.dimension_evidence.get(key, []) if str(item).strip()]
        evidence[key] = items

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

    async def get_profile(
        self,
        *,
        user_id: int,
        db: AsyncSession | None = None,
    ) -> GlobalProfile:
        """获取用户全局画像，不存在则创建。

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
                profile_json=deepcopy(default_profile_json),
                profile_score_json=deepcopy(default_score_json),
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
                    profile_json=deepcopy(default_profile_json),
                    profile_score_json=deepcopy(default_score_json),
                )
                db.add(profile)
                await db.flush()

            return profile

        if db is None:
            async with session_scope() as db:
                return await _upsert(db)
        return await _upsert(db)

    async def get_or_create_weekly_digest(
        self,
        *,
        user_id: int,
        db: AsyncSession,
        now: datetime | None = None,
    ) -> WeeklyLearningDigest:
        """获取或生成本周学习摘要（懒加载）。

        若本周摘要已存在则直接返回；否则聚合本周数据、调用 LLM 生成 Markdown、
        持久化后返回。该方法是 score_profile 的证据缓冲层。

        Args:
            user_id: 用户 ID
            db: 数据库会话（复用调用方会话，避免嵌套 session_scope）
            now: 用于确定"本周"的基准时间（测试注入），默认当前 UTC 时间
        """
        week_start, week_end = _utc_week_range(now)

        existing = (
            await db.exec(
                select(WeeklyLearningDigest).where(
                    WeeklyLearningDigest.user_id == user_id,
                    WeeklyLearningDigest.module == self.module,
                    WeeklyLearningDigest.week_start == week_start,
                )
            )
        ).first()
        if existing:
            return existing

        logger.info(
            "[ProfileService] 周摘要懒生成: user_id=%s week=%s",
            user_id, _format_week_label(week_start, week_end),
        )

        data = await self._aggregate_week_data(
            db=db, user_id=user_id, week_start=week_start, week_end=week_end,
        )

        prev_digest_row = (
            await db.exec(
                select(WeeklyLearningDigest)
                .where(
                    WeeklyLearningDigest.user_id == user_id,
                    WeeklyLearningDigest.module == self.module,
                    WeeklyLearningDigest.week_start < week_start,
                )
                .order_by(WeeklyLearningDigest.week_start.desc())
                .limit(1)
            )
        ).first()
        prev_digest = prev_digest_row.digest_markdown if prev_digest_row else "（本周为首周，无上周摘要）"

        global_profile = await self.get_profile(user_id=user_id, db=db)

        week_label = _format_week_label(week_start, week_end)
        prompt = prompts.get("profile").render(
            "weekly_digest",
            week_range=week_label,
            dialogue_summaries=data["dialogue_summaries"],
            resource_activities=data["resource_activities"],
            path_activities=data["path_activities"],
            quiz_activities=data["quiz_activities"],
            learning_events=data["learning_events"],
            prev_digest=prev_digest,
            long_term_memory=data["long_term_memory"],
            current_profile_json=json.dumps(
                global_profile.profile_json or {}, ensure_ascii=False,
            ),
        )

        resp = await self.llm.ainvoke([HumanMessage(content=prompt)])
        digest_markdown = str(resp.content or "").strip()
        if not digest_markdown:
            digest_markdown = f"# 周度学习摘要（{week_label}）\n\n本周无学习活动记录。"

        # H1: 使用 ON CONFLICT DO NOTHING 保证并发安全。
        # 两个并发 caller 可能同时穿过 lazy-cache 检查 → 都生成 digest → 都尝试 INSERT。
        # UNIQUE(user_id, module, week_start) 保证仅一行落库；后插入者被静默忽略，
        # 随后 SELECT 必然返回已存在的行（可能是自己写入的，也可能是竞争者写入的）。
        now_utc = datetime.now(timezone.utc)
        insert_stmt = pg_insert(WeeklyLearningDigest).values(
            user_id=user_id,
            module=self.module,
            week_start=week_start,
            week_end=week_end,
            digest_markdown=digest_markdown,
            courses_active=data["courses_active"],
            stats=data["stats"],
            created_at=now_utc,
            updated_at=now_utc,
        ).on_conflict_do_nothing(
            constraint="uq_weekly_digest_user_module_week",
        )
        await db.exec(insert_stmt)  # type: ignore[arg-type]
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
            # 理论不可达：INSERT ON CONFLICT + SELECT 必然返回一行。
            # 防御性兜底：回退到内存对象（不持久化），保证 score_profile 仍可继续。
            logger.warning(
                "[ProfileService] 周摘要 upsert+select 意外返回 None: user_id=%s week=%s",
                user_id, _format_week_label(week_start, week_end),
            )
            digest = WeeklyLearningDigest(
                user_id=user_id,
                module=self.module,
                week_start=week_start,
                week_end=week_end,
                digest_markdown=digest_markdown,
                courses_active=data["courses_active"],
                stats=data["stats"],
            )

        logger.info(
            "[ProfileService] 周摘要生成完成: user_id=%s stats=%s markdown长度=%s",
            user_id, digest.stats, len(digest.digest_markdown),
        )
        return digest

    async def _aggregate_week_data(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        week_start: datetime,
        week_end: datetime,
    ) -> dict[str, Any]:
        """聚合本周跨系统的学习行为数据，供 weekly_digest prompt 使用。"""
        # 1. 辅导对话摘要（需 join ChatSession 过滤 user_id）
        summary_stmt = (
            select(ChatSessionSummaryBlock.summary_markdown)
            .join(ChatSession, ChatSessionSummaryBlock.session_id == ChatSession.id)
            .where(
                ChatSession.user_id == user_id,
                ChatSessionSummaryBlock.created_at >= week_start,
                ChatSessionSummaryBlock.created_at <= week_end,
            )
            .order_by(ChatSessionSummaryBlock.created_at.asc())
        )
        summary_rows = (await db.exec(summary_stmt)).all()
        dialogue_summaries = "\n\n".join(summary_rows) if summary_rows else "本周无辅导对话记录"

        # 2. 资源生成记录
        res_stmt = (
            select(GeneratedResource)
            .where(
                GeneratedResource.user_id == user_id,
                GeneratedResource.created_at >= week_start,
                GeneratedResource.created_at <= week_end,
            )
            .order_by(GeneratedResource.created_at.asc())
        )
        resources = (await db.exec(res_stmt)).all()
        if resources:
            res_ids = [r.id for r in resources]
            item_stmt = (
                select(GeneratedResourceItem.agent_type, GeneratedResourceItem.title)
                .where(GeneratedResourceItem.resource_id.in_(res_ids))
            )
            items = (await db.exec(item_stmt)).all()
            resource_lines = [
                f"- 学习需求：{r.learning_need or '未指定'}（状态：{r.status}）"
                for r in resources
            ]
            if items:
                agent_types = [i[0] for i in items]
                resource_lines.append(f"- 生成的资源类型：{', '.join(agent_types)}")
            resource_activities = "\n".join(resource_lines)
        else:
            resource_activities = "本周无资源生成"

        # 3. 路径学习记录
        # H2: 不能使用 updated_at（任何写操作都会刷新，例如 priority/current_tutorial_id 变更）。
        # 改用 started_at/completed_at 区间，仅捕获本周有真实学习进度的节点。
        # 命中条件：本周内首次开始 OR 本周内完成（含跨周开始本周完成的情形）。
        node_stmt = (
            select(PathNode)
            .where(
                PathNode.user_id == user_id,
                sa_or(
                    PathNode.started_at.is_not(None),
                    PathNode.completed_at.is_not(None),
                ),
                sa_or(
                    PathNode.started_at.between(week_start, week_end),
                    PathNode.completed_at.between(week_start, week_end),
                ),
            )
        )
        nodes = (await db.exec(node_stmt)).all()
        if nodes:
            completed = [n for n in nodes if n.status == "completed"]
            path_lines = [
                f"- 节点「{n.title}」状态：{n.status}，难度：{n.difficulty or '未指定'}，尝试次数：{n.attempt_count}"
                for n in nodes
            ]
            if completed:
                path_lines.insert(0, f"- 本周完成节点数：{len(completed)}")
            path_activities = "\n".join(path_lines)
        else:
            path_activities = "本周无路径学习"

        # 4. 答题与错题
        quiz_stmt = (
            select(PathNodeQuestion)
            .where(
                PathNodeQuestion.user_id == user_id,
                PathNodeQuestion.submitted_at >= week_start,
                PathNodeQuestion.submitted_at <= week_end,
            )
        )
        questions = (await db.exec(quiz_stmt)).all()
        if questions:
            total = len(questions)
            correct = sum(1 for q in questions if q.is_correct)
            wrong_kps: list[str] = []
            for q in questions:
                if q.is_correct is False and q.knowledge_points:
                    wrong_kps.extend(q.knowledge_points)
            wrong_kp_str = "、".join(sorted(set(wrong_kps))) if wrong_kps else "无"
            accuracy = round(correct / total * 100) if total else 0
            quiz_activities = (
                f"- 本周答题：{total} 道，正确：{correct} 道，正确率：{accuracy}%\n"
                f"- 错题涉及知识点：{wrong_kp_str}"
            )
        else:
            quiz_activities = "本周无答题记录"

        # 5. 学习事件与时长
        event_stmt = (
            select(
                LearningEvent.event_type,
                sa_func.count(LearningEvent.id),
            )
            .where(
                LearningEvent.user_id == user_id,
                LearningEvent.created_at >= week_start,
                LearningEvent.created_at <= week_end,
            )
            .group_by(LearningEvent.event_type)
        )
        event_rows = (await db.exec(event_stmt)).all()
        session_stmt = (
            select(sa_func.sum(LearningSession.duration_seconds))
            .where(
                LearningSession.user_id == user_id,
                LearningSession.started_at >= week_start,
                LearningSession.started_at <= week_end,
            )
        )
        total_seconds = (await db.exec(session_stmt)).one_or_none() or 0
        active_minutes = int(total_seconds // 60) if total_seconds else 0
        if event_rows:
            event_lines = [f"- {et}：{cnt} 次" for et, cnt in event_rows]
            event_lines.append(f"- 本周活跃总时长：约 {active_minutes} 分钟")
            learning_events = "\n".join(event_lines)
        else:
            learning_events = f"本周无学习事件记录（活跃约 {active_minutes} 分钟）"

        # 6. 长期记忆
        ltm = (
            await db.exec(
                select(ChatLongTermMemory)
                .where(ChatLongTermMemory.user_id == user_id)
                .limit(1)
            )
        ).first()
        long_term_memory = ltm.memory_markdown if ltm and ltm.memory_markdown else "暂无长期记忆"

        # 7. 统计快照 + 活跃课程
        courses_active = sorted({
            n.title for n in nodes if n.title
        } | {
            str(r.learning_need or "")[:30]
            for r in resources
            if r.learning_need
        } - {""})

        stats = {
            "dialogue_turns": len(summary_rows),
            "resources_generated": len(resources),
            "nodes_touched": len(nodes),
            "nodes_completed": sum(1 for n in nodes if n.status == "completed"),
            "quiz_total": len(questions),
            "quiz_correct": sum(1 for q in questions if q.is_correct),
            "active_minutes": active_minutes,
        }

        return {
            "dialogue_summaries": dialogue_summaries,
            "resource_activities": resource_activities,
            "path_activities": path_activities,
            "quiz_activities": quiz_activities,
            "learning_events": learning_events,
            "long_term_memory": long_term_memory,
            "courses_active": courses_active,
            "stats": stats,
        }

    async def build_profile_markdown(self, *, user_id: int) -> str:
        """将 7 维度画像 JSON 转为结构化 Markdown，供 LLM 和智能体使用。

        Args:
            user_id: 用户 ID

        Returns:
            结构化 Markdown 文本，包含：
            - 基础信息（学校、专业、年级等）
            - 知识层维度（知识基础、易错点偏好、知识缺口模式）
            - 认知层维度（认知风格、学习目标导向、难度耐受度、自纠能力水平）
        """
        profile = await self.get_profile(user_id=user_id)
        profile_json = profile.profile_json or deepcopy(default_profile_json)

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

    async def save_onboarding_info(
        self,
        *,
        user_id: int,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """保存 onboarding 基本信息（仅数据库层写入，不执行 LLM）。

        必须传入请求作用域的 db session，确保写入在响应前提交。
        """
        logger.info("[ProfileService] onboarding 写入开始: user_id=%s school=%s major=%s",
                     user_id, payload.get("school"), payload.get("major"))

        base_info = payload.copy()
        school_name = base_info.get("school")
        if school_name:
            school = (await db.exec(select(School).where(School.name == school_name).limit(1))).first()
            base_info["school_level"] = school.level if school and school.level else None

        profile = await self.get_profile(user_id=user_id, db=db)

        profile_json = profile.profile_json or deepcopy(default_profile_json)
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

    async def infer_profile_from_onboarding(self, *, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """从 onboarding 信息推理 7 维度画像并评分。

        作为后台任务调用，内部捕获异常避免未处理错误。
        基础信息已在调用前同步保存，推理失败不影响用户正常使用。
        """
        try:
            logger.info("[ProfileService] onboarding LLM推理开始: user_id=%s", user_id)

            async with session_scope() as db:
                profile = await self.get_profile(user_id=user_id, db=db)
                profile_json = profile.profile_json or deepcopy(default_profile_json)
                base_info = profile_json.get("base_info", {})

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

                profile = await self.get_profile(user_id=user_id, db=db)

                profile_json = profile.profile_json or deepcopy(default_profile_json)
                profile_json = merge_dimensions(profile_json, resp.dimensions_patch)
                profile.profile_json = profile_json
                profile.updated_at = datetime.now(timezone.utc)

                db.add(profile)
                await db.flush()

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
            global_profile = await self.get_profile(user_id=user_id, db=db)
            profile_json = global_profile.profile_json or {}

            # 获取最近对话
            from app.chat.memory.service import get_chat_memory_service
            memory_service = get_chat_memory_service()
            recent_dialogue, _, _ = await memory_service._build_dialogue_since(
                db=db, user_id=user_id, session_id=session_id, after_message_id=0, limit=20,
            )

            if not recent_dialogue or not recent_dialogue.strip():
                logger.info("[ProfileService] 全局画像: 无对话内容可提取，跳过更新")
                return {
                    "profile_updated": False,
                    "profile_json": global_profile.profile_json or {},
                    "updated_at": global_profile.updated_at,
                    "reason": "no_dialogue",
                }

            # 获取长期记忆
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
                profile_json=json.dumps(profile_json, ensure_ascii=False),
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
                profile_json = merge_dimensions(profile_json, resp.dimensions_patch)
                global_profile.profile_json = profile_json
                global_profile.updated_at = datetime.now(timezone.utc)
                db.add(global_profile)
                await db.flush()
                updated = True
                logger.info("[ProfileService] 全局画像更新结果: updated=%s updated_dimensions=%s",
                             updated, list(dims_summary.keys()))

        if updated:
            score_result = await self.score_profile(user_id=user_id)
            logger.info("[ProfileService] 全局画像评分刷新完成: user_id=%s overall_score=%s dimension_scores=%s",
                         user_id, score_result.get("overall_score"), score_result.get("dimension_scores"))

        return {
            "profile_updated": updated,
            "profile_json": global_profile.profile_json or {},
            "updated_at": global_profile.updated_at,
        }

    async def score_profile(self, *, user_id: int) -> dict[str, Any]:
        """根据全局画像 JSON 和本周学习摘要重新计算评分。

        本周摘要作为评分的缓冲证据层：聚合本周辅导对话、资源生成、路径学习、
        答题行为等硬数据生成结构化 Markdown，注入评分 prompt 作为客观依据。
        """
        logger.info("[ProfileService] 全局评分刷新开始: user_id=%s", user_id)
        async with session_scope() as db:
            global_profile = await self.get_profile(user_id=user_id, db=db)

            digest = await self.get_or_create_weekly_digest(user_id=user_id, db=db)
            weekly_digest = digest.digest_markdown
            logger.info(
                "[ProfileService] 全局评分: week=%s digest长度=%s",
                _format_week_label(digest.week_start, digest.week_end), len(weekly_digest),
            )

            prompt = prompts.get("profile").render(
                "score",
                profile_text=json.dumps(global_profile.profile_json, ensure_ascii=False),
                weekly_digest=weekly_digest,
            )

            resp = await self.llm.ainvoke_json(
                ProfileScoreOutput,
                [HumanMessage(content=prompt)],
            )

            logger.info(
                "[ProfileService] 全局评分 LLM原始结果: dimension_scores=%s dimension_evidence_keys=%s",
                resp.dimension_scores, list(resp.dimension_evidence.keys()),
            )

            scores = sanitize_score_output(resp)
            global_profile.profile_score_json = scores
            global_profile.updated_at = datetime.now(timezone.utc)

            db.add(global_profile)
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
    "merge_dimensions",
    "sanitize_score_output",
]
