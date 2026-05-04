"""用户画像构建服务 — 从长期记忆、会话概要、学习事件生成 Markdown 用户画像。

模块职责：
- 从 UserLongTermMemory 提取画像维度信息
- 从 ChatSessionSummary 提取当前学习状态
- 从 LearningEvent 提取学习行为证据
- 生成 profile_markdown，并为画像快照生成轻量评分 JSON

设计原则：
- 画像正文以 Markdown 为准，便于直接注入辅导上下文
- profile_json 只保存快照评分与元信息，不作为画像正文来源
- 支持"随学随新"，只在有明显变化时更新
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.memory._store import MemoryStore, normalize_text
from app.memory.memory_types import (
    PROFILE_MARKDOWN_SECTIONS,
)

logger = get_logger(__name__)

PROFILE_BUILDING_PROMPT = """# 角色与目标
你是一个学生画像构建器。请根据【旧画像】【长期记忆】【会话概要】【学习事件】，生成一份 Markdown 学生画像。

这是一个"对话式学习画像自主构建"流程：不要要求学生填写传统繁琐表单，而是从自然语言对话中自动抽取特征，构建动态学生画像，并支持画像的随学随新。

# 输出要求（严格遵守）
1. 直接输出 Markdown，不要输出 JSON。
2. 不要包裹在代码块中，不要添加 ```markdown 标记。
3. 第一行必须是：# 学生画像
4. 信息不足的地方要写入"不确定信息"，不要编造用户没有表达过的信息。
5. 每个判断尽量写出证据来源，例如长期记忆、会话概要、学习事件或用户原话。
6. 画像快照评分由系统根据 Markdown 自动生成，你不要输出评分 JSON。

# Markdown 结构（尽量按此顺序）
## 基础信息与专业背景
## 学习目标
## 学习历史
## 知识基础
## 认知风格
## 学习偏好
## 易错点与薄弱点
## 交互偏好与禁忌
## AI 纠正记录
## 当前学习状态
## 推荐辅导策略
## 最近变化
## 不确定信息

【旧画像】
{old_profile}

【长期记忆】
{long_term_memory}

【会话概要】
{session_summaries}

【学习事件】
{learning_events}
"""


def _strip_markdown_fence(content: str) -> str:
    text = (content or "").strip()
    if text.startswith("```markdown"):
        text = text[len("```markdown"):].strip()
    if text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProfileBuildingService:
    """画像构建服务 — 生成 Markdown 用户画像和快照评分。"""

    def __init__(
        self,
        *,
        module_name: str = "mentor",
        store: MemoryStore | None = None,
    ) -> None:
        self.module_name = module_name
        self.store = store or MemoryStore()
        self.llm_manager = get_llm_manager()
        self.model_kwargs = {"temperature": 0.1, "streaming": False}

    async def build_profile(
        self,
        user_id: int,
        session_id: str | None = None,
    ) -> tuple[bool, bool]:
        effective_session = session_id
        if effective_session is None:
            sessions = await self.store.get_user_chat_sessions(user_id=user_id, module=self.module_name, limit=1)
            effective_session = sessions[0].id if sessions else f"user-{user_id}-default-{self.module_name}"

        old_profile = await self.store.get_user_profile(user_id, self.module_name)
        long_term_memory = await self.store.get_or_create_long_term_memory(user_id, self.module_name)
        session_summaries = await self.store.list_session_summaries(user_id, effective_session, self.module_name, limit=3)

        old_profile_text = old_profile.profile_markdown if old_profile else "暂无原有画像（新用户）"
        long_term_memory_text = long_term_memory.memory_markdown if long_term_memory else "暂无长期记忆。"
        summaries_text = "\n\n".join(s.summary_markdown for s in session_summaries) if session_summaries else "暂无会话概要。"

        try:
            prompt_text = PROFILE_BUILDING_PROMPT.format(
                old_profile=old_profile_text[:3000],
                long_term_memory=long_term_memory_text[:2000],
                session_summaries=summaries_text[:2000],
                learning_events="暂无学习事件数据。",
            )
            response = await self.llm_manager.ainvoke(
                "spark_x",
                prompt_text,
                model_kwargs=self.model_kwargs,
            )
            response_text = response.content if isinstance(response.content, str) else str(response.content)
        except Exception as exc:
            logger.error("[ProfileBuilding] 画像生成失败: %s", str(exc))
            return False, False

        profile_markdown = self._normalize_profile_markdown(response_text)
        if not profile_markdown:
            logger.warning("[ProfileBuilding] Markdown 画像为空，跳过更新")
            return True, False

        if old_profile and old_profile.profile_markdown:
            if self._is_same_profile_markdown(profile_markdown, old_profile.profile_markdown):
                return True, False

        profile_json = self._build_profile_snapshot(profile_markdown)

        try:
            await self.store.update_user_profile(
                user_id=user_id,
                module=self.module_name,
                profile_markdown=profile_markdown,
                profile_json=profile_json,
                updated_reason="基于长期记忆和会话概要生成画像",
                source_session_ids=[effective_session],
                confidence=profile_json["snapshot_score"]["confidence"],
            )
            return True, True
        except Exception as exc:
            logger.error("[ProfileBuilding] 保存画像失败: %s", str(exc))
            return False, False

    def _normalize_profile_markdown(self, response_text: str) -> str:
        text = _strip_markdown_fence(response_text)
        if not text:
            return ""
        if not text.startswith("# 学生画像"):
            text = "# 学生画像\n\n" + text.lstrip("# \n")
        return text

    def _build_profile_snapshot(self, profile_markdown: str) -> dict[str, Any]:
        normalized = normalize_text(profile_markdown)
        sections = [section for section in PROFILE_MARKDOWN_SECTIONS if f"## {section}" in profile_markdown]
        section_score = round(len(sections) / len(PROFILE_MARKDOWN_SECTIONS) * 100)
        evidence_keywords = ("证据", "用户原话", "长期记忆", "会话概要", "学习事件", "纠正")
        evidence_score = min(100, sum(profile_markdown.count(keyword) for keyword in evidence_keywords) * 20)
        uncertainty_score = 100 if "不确定信息" in profile_markdown else 60
        length_score = min(100, max(20, len(normalized) // 8))
        overall_score = round(section_score * 0.45 + evidence_score * 0.25 + uncertainty_score * 0.15 + length_score * 0.15)
        confidence = round(max(0.1, min(0.95, overall_score / 100)), 2)
        missing_sections = [section for section in PROFILE_MARKDOWN_SECTIONS if section not in sections]
        return {
            "profile_version": 2,
            "format": "markdown",
            "snapshot_score": {
                "overall_score": overall_score,
                "confidence": confidence,
                "section_coverage": section_score,
                "evidence_quality": evidence_score,
                "uncertainty_handling": uncertainty_score,
                "content_richness": length_score,
                "missing_sections": missing_sections,
                "scored_at": _now_iso(),
            },
        }

    def _is_same_profile_markdown(self, new_markdown: str, old_markdown: str) -> bool:
        return normalize_text(new_markdown) == normalize_text(old_markdown)
