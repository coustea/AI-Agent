"""用户画像构建服务 — 从旧画像与近期原始对话生成 JSON 用户画像。

模块职责：
- 从 UserProfile 读取旧画像
- 从 ChatMessage 读取近期用户与助手原始对话
- 生成结构化文字画像 profile_json，并单独生成评分画像 profile_score_json

设计原则：
- profile_json 是文字画像权威来源
- profile_score_json 是评分画像权威来源
- 支持"随学随新"，基于近期原始对话持续更新
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from typing import Any

from pydantic import BaseModel, Field

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.memory._store import MemoryStore
from app.memory.memory_types import (
    ALL_PROFILE_DIMENSIONS,
    PROFILE_DIMENSION_NAMES,
    make_default_profile_json,
    make_default_profile_score_json,
)
from app.shared.json_utils import parse_first_json_object

logger = get_logger(__name__)

PROFILE_RECENT_DIALOGUE_LIMIT = 10
PROFILE_RECENT_DIALOGUE_CHAR_BUDGET = 5000

PROFILE_BUILDING_PROMPT = """# 角色与目标
你是一个学生画像构建器。请根据【旧画像 JSON】和【近期原始对话】，生成一份 JSON 学生画像。

这是一个"对话式学习画像自主构建"流程：从自然语言对话中自动抽取特征，构建动态学生画像，并支持画像的随学随新。

# 维度定义与信号映射（核心参考）

以下是需要提取的 8 个画像维度。即使对话是纯技术问答，仍可以从提问方式、追问方向、代码风格偏好等侧面信号中推断——不要因为没有"学生自我介绍"就留空。

## 1. knowledge_foundation（知识基础）
定义：学生当前掌握的知识范围、深度和知识结构。包括已掌握的编程语言、框架、计算机基础（算法/数据结构/网络/OS等）、数学基础、AI/ML 知识。
从哪里看：
- 提问中涉及的技术术语和概念层次（基础概念 vs 高级话题）
- 是否展现出对某个领域的系统性理解
- 代码中展示的编程习惯和工程素养
- TA 问了什么问题本身就能反映 TA 的知识边界
示例 evidence："用户询问了 Python 中 GIL 对多线程的影响，说明已掌握基本的多线程概念"

## 2. learning_goal（学习目标）
定义：学生当前或近期的学习方向、目标技能、想达到的水平。可以是短期（通过面试、完成作业）或长期（转行、深入某领域）。
从哪里看：
- 用户直接或间接表达的学习意图
- 连续多轮对话涉及的主题聚类
- 用户对某类问题的反复追问和深入
示例 evidence："用户连续询问了多个与数据库索引优化相关的问题"

## 3. cognitive_style（认知风格）
定义：学生接收、处理和组织信息的方式偏好。例如：喜欢理论先行还是实践先行，偏好图文还是纯文字，倾向系统学习还是问题驱动。
从哪里看：
- 是先问"为什么"还是先问"怎么做"
- 是要求代码示例还是要求概念解释
- 对话中展示的思维跳跃性
示例 evidence："用户要求先用示意图解释再给代码，体现了视觉+实操的学习偏好"

## 4. weakness_points（薄弱点）
定义：学生当前存在的知识盲区、理解偏差或技能短板。包括反复出错的概念、混淆的术语、不准确的直觉。
从哪里看：
- 对话中暴露的明显理解错误或概念混淆
- 用户自己承认"不太懂""一直没搞明白"的地方
- 多次追问同一主题但始终未能准确回答
示例 evidence："用户将 BFS 和 DFS 的时间复杂度混淆，说明对图搜索算法的复杂度分析存在薄弱"

## 5. mistake_preference（易错点偏好）
定义：学生在特定类型问题上容易出错的模式。与 weakness_points 不同，这侧重于"知道但容易错"的陷阱，比如边界条件疏漏、代码风格不一致、特定语言特性的误用。
从哪里看：
- 用户代码中反复出现的同类 bug 模式
- 用户对某些类型错误的敏感度
- 是否关注细节还是只关注主逻辑
示例 evidence："用户代码中多次出现 off-by-one 错误，边界处理需要强化"

## 6. practice_ability（实践能力）
定义：学生将理论知识转化为实际代码的能力。包括代码组织能力、调试能力、工程化思维、独立解决问题的能力。
从哪里看：
- 用户提供的代码质量和结构
- 是否只需要提示方向就能独立完成
- 是否关注代码可读性和工程实践
示例 evidence："用户展示了完整的项目代码结构，包含错误处理和单元测试"

## 7. interaction_preference（交互偏好）
定义：学生在对话中的沟通风格和偏好。包括喜欢直接答案还是引导式教学、偏好详细展开还是精炼回复、对纠错的态度。
从哪里看：
- 提问的具体程度（越具体说明越偏好精准回答）
- 是否追问"还有别的做法吗"（偏好多元视角）
- 被纠正后的反应（接受、抵触、深入追问）
示例 evidence："用户在被指出代码问题后主动追问根因和最佳实践"

## 8. learning_history（学习历史）
定义：学生已经完成的学习经历，包括学过的课程、做过的项目、读过的书。通常是学生自己提及的，也可以从技术对话的深度侧面推断。
从哪里看：
- 用户提及的课程、教材、项目经历
- 对话中透露的技术栈演进轨迹
- 对某些经典教材或框架的熟悉程度
示例 evidence："用户提到正在做毕业设计，使用 Spring Boot + Vue 技术栈"

# 提取原则
1. **有直接证据 > 合理推断 > 暂无信息**：优先使用对话中的直接证据；在缺少直接证据时，可以根据对话主题和提问风格做出合理推断（confidence 设为 0.3-0.5）；完全没有线索时才留空。
2. **弱信号也好过空**：即使只有一条模糊线索，也应该填入 summary 并设置较低的 confidence，而不是直接返回 null。
3. **新旧融合**：如果旧画像中已有某维度的信息，而本轮对话没有新的相关信号，可以保留旧信息（confidence 不变或略降）。
4. **每个维度独立评估**：一个维度的证据不应影响其他维度的判断。

# 输出要求（严格遵守）
1. 只输出 JSON，不要输出 Markdown。
2. 不要包裹在代码块中，不要添加解释文字。
3. 不要输出 score、overall_score、snapshot_score 或任何评分字段；评分由后端单独生成。
4. **绝对禁止**编造用户没有表达过的信息；但可以从对话中做合理推断（标注较低 confidence）。
5. 每个维度都必须有 confidence（0-1）、summary、evidence。
6. 画像只能根据旧画像 JSON 与近期原始对话更新，不要使用长期记忆或会话概要。

# JSON 结构
{{
  "dimensions": {{
    "knowledge_foundation": {{"confidence": 0-1, "summary": "string 或 null", "evidence": ["用户原话或近期对话证据"]}},
    "learning_goal": {{"confidence": 0-1, "summary": "string 或 null", "evidence": []}},
    "cognitive_style": {{"confidence": 0-1, "summary": "string 或 null", "evidence": []}},
    "weakness_points": {{"confidence": 0-1, "summary": "string 或 null", "evidence": []}},
    "mistake_preference": {{"confidence": 0-1, "summary": "string 或 null", "evidence": []}},
    "practice_ability": {{"confidence": 0-1, "summary": "string 或 null", "evidence": []}},
    "interaction_preference": {{"confidence": 0-1, "summary": "string 或 null", "evidence": []}},
    "learning_history": {{"confidence": 0-1, "summary": "string 或 null", "evidence": []}}
  }},
  "recommended_strategy": ["string"],
  "last_update_reason": "string"
}}

【旧画像 JSON】
{old_profile}

【近期原始对话】
{recent_dialogue}
"""


class ProfileDimensionOutput(BaseModel):
    """单个画像维度的 function calling 输出。"""

    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="该维度判断的置信度，0 到 1。")
    summary: str | None = Field(default=None, description="该维度画像摘要。没有证据时返回 null。")
    evidence: list[str] = Field(default_factory=list, description="近期原始对话中的证据。没有证据时返回空数组。")


class ProfileBuildingOutput(BaseModel):
    """画像构建 function calling 输出。"""

    dimensions: dict[str, ProfileDimensionOutput] = Field(default_factory=dict)
    recommended_strategy: list[str] = Field(default_factory=list)
    last_update_reason: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _render_recent_dialogue(messages: list[Any]) -> str:
    lines: list[str] = []
    used_chars = 0
    for msg in messages:
        role = getattr(msg, "role", "")
        content = (getattr(msg, "content", "") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        line = f"{role}: {content[:800]}"
        if used_chars + len(line) > PROFILE_RECENT_DIALOGUE_CHAR_BUDGET:
            break
        lines.append(line)
        used_chars += len(line)
    return "\n".join(lines) if lines else "暂无近期原始对话。"


class ProfileBuildingService:
    """画像构建服务 — 生成 JSON 用户画像和维度评分。"""

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
        recent_messages = await self.store.get_recent_messages(
            user_id,
            effective_session,
            self.module_name,
            limit=PROFILE_RECENT_DIALOGUE_LIMIT,
        )

        old_profile_json = old_profile.profile_json if old_profile and old_profile.profile_json else make_default_profile_json()
        old_profile_text = json.dumps(old_profile_json, ensure_ascii=False)
        recent_dialogue_text = _render_recent_dialogue(recent_messages)

        try:
            prompt_text = PROFILE_BUILDING_PROMPT.format(
                old_profile=old_profile_text[:3000],
                recent_dialogue=recent_dialogue_text,
            )
            response = await self.llm_manager.ainvoke_structured(
                "spark_max",
                ProfileBuildingOutput,
                prompt_text,
                function_name="update_student_profile",
                function_description="根据旧画像 JSON 和近期原始对话返回 JSON 学生画像。",
                model_kwargs=self.model_kwargs,
            )
        except Exception as exc:
            logger.error("[ProfileBuilding] 画像生成失败: %s", str(exc))
            return False, False

        profile_json = self._normalize_profile_json(response.model_dump())
        if not profile_json:
            logger.warning("[ProfileBuilding] JSON 画像为空，跳过更新")
            return True, False
        profile_score_json = self._build_profile_score_json(profile_json)

        if old_profile and old_profile.profile_json:
            if self._is_same_profile_json(profile_json, old_profile.profile_json):
                return True, False

        try:
            await self.store.update_user_profile(
                user_id=user_id,
                module=self.module_name,
                profile_json=profile_json,
                profile_score_json=profile_score_json,
                updated_reason="基于旧画像和近期原始对话生成画像",
                source_session_ids=[effective_session],
                confidence=profile_score_json["confidence"],
            )
            return True, True
        except Exception as exc:
            logger.error("[ProfileBuilding] 保存画像失败: %s", str(exc))
            return False, False

    def _normalize_profile_json(self, response_payload: str | dict[str, Any]) -> dict[str, Any]:
        parsed = response_payload if isinstance(response_payload, dict) else parse_first_json_object(response_payload)
        if not parsed:
            return {}

        profile_json = make_default_profile_json()
        profile_json["profile_version"] = 3
        profile_json["format"] = "json"
        profile_json["student_profile"] = None

        parsed_dimensions = parsed.get("dimensions") or {}
        dimensions: dict[str, dict[str, Any]] = {}
        for key in ALL_PROFILE_DIMENSIONS:
            raw_dim = parsed_dimensions.get(key) or {}
            summary = raw_dim.get("summary")
            evidence = raw_dim.get("evidence") or []
            confidence = raw_dim.get("confidence")
            has_content = bool(summary) or bool(evidence)
            dimensions[key] = {
                "name": PROFILE_DIMENSION_NAMES.get(key, key),
                "confidence": self._coerce_confidence(confidence) if has_content else 0.0,
                "summary": str(summary).strip() if summary else None,
                "evidence": [str(item).strip() for item in evidence if str(item).strip()][:5],
                "updated_at": _now_iso() if has_content else None,
            }
        profile_json["dimensions"] = dimensions

        strategies = parsed.get("recommended_strategy") or []
        profile_json["recommended_strategy"] = [str(item).strip() for item in strategies if str(item).strip()][:5]
        profile_json["last_update_reason"] = str(parsed.get("last_update_reason") or "").strip()
        profile_json["overall_confidence"] = self._calculate_overall_confidence(profile_json)
        return profile_json

    def _build_profile_score_json(self, profile_json: dict[str, Any]) -> dict[str, Any]:
        dimensions = profile_json.get("dimensions") or {}
        dimension_scores = {key: self._score_dimension(dimensions.get(key) or {}) for key in ALL_PROFILE_DIMENSIONS}
        available_scores = [score for score in dimension_scores.values() if isinstance(score, (int, float))]
        confidences = [
            float((dimensions.get(key) or {}).get("confidence") or 0)
            for key in ALL_PROFILE_DIMENSIONS
            if (dimensions.get(key) or {}).get("summary") or (dimensions.get(key) or {}).get("evidence")
        ]
        missing_sections = [key for key, score in dimension_scores.items() if score is None]
        coverage = round((len(ALL_PROFILE_DIMENSIONS) - len(missing_sections)) / len(ALL_PROFILE_DIMENSIONS) * 100)
        evidence_count = sum(len((dimensions.get(key) or {}).get("evidence") or []) for key in ALL_PROFILE_DIMENSIONS)
        evidence_score = min(100, evidence_count * 20)
        overall_score = round(sum(available_scores) / len(available_scores)) if available_scores else None
        confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
        score_json = make_default_profile_score_json()
        score_json.update({
            "overall_score": overall_score,
            "confidence": confidence,
            "dimension_scores": dimension_scores,
            "section_coverage": coverage,
            "evidence_quality": evidence_score,
            "missing_sections": missing_sections,
            "scored_at": _now_iso(),
        })
        return score_json

    def _score_dimension(self, dimension: dict[str, Any]) -> int | None:
        summary = str(dimension.get("summary") or "").strip()
        evidence = dimension.get("evidence") or []
        if not summary and not evidence:
            return None
        confidence = self._coerce_confidence(dimension.get("confidence"))
        evidence_bonus = min(25, len(evidence) * 8)
        summary_bonus = 20 if summary else 0
        return max(1, min(100, round(confidence * 55 + summary_bonus + evidence_bonus)))

    def _calculate_overall_confidence(self, profile_json: dict[str, Any]) -> float:
        dimensions = profile_json.get("dimensions") or {}
        confidences = [
            float((dimensions.get(key) or {}).get("confidence") or 0)
            for key in ALL_PROFILE_DIMENSIONS
            if (dimensions.get(key) or {}).get("summary") or (dimensions.get(key) or {}).get("evidence")
        ]
        return round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    def _coerce_confidence(self, value: Any) -> float:
        try:
            return round(max(0.0, min(1.0, float(value))), 2)
        except (TypeError, ValueError):
            return 0.0

    def _is_same_profile_json(self, new_json: dict[str, Any], old_json: dict[str, Any]) -> bool:
        def comparable(payload: dict[str, Any]) -> dict[str, Any]:
            data = deepcopy(payload)
            data.pop("overall_confidence", None)
            for dim in (data.get("dimensions") or {}).values():
                if isinstance(dim, dict):
                    dim.pop("updated_at", None)
                    dim.pop("score", None)
            return data

        return comparable(new_json) == comparable(old_json)
