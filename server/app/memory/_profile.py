"""用户画像构建服务。

从旧画像与近期对话生成 8 维度 JSON 画像 + 评分快照。
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.memory._store import MemoryStore
from app.memory.memory_types import (
    ALL_PROFILE_DIMENSIONS,
    PROFILE_DIMENSION_NAMES,
    PROFILE_DIMENSION_KNOWLEDGE_FOUNDATION,
    PROFILE_DIMENSION_LEARNING_GOAL,
    PROFILE_DIMENSION_LEARNING_HISTORY,
    make_default_profile_json,
    make_default_profile_score_json,
)
from app.shared.json_utils import parse_first_json_object

logger = get_logger(__name__)

# 近期对话配置
DIALOGUE_LIMIT = 10          # 最多取 10 条消息
DIALOGUE_CHAR_BUDGET = 5000  # 字符预算

# 首次登录必填字段
ONBOARDING_FIELDS = ("education_level", "grade", "major", "courses", "learning_goal")
ONBOARDING_OPTIONAL_FIELDS = ("school", "school_level", "preferred_language")

# 画像构建提示词
BUILD_PROMPT = """# 角色与目标
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


# ---------------------------------------------------------------------------
# LLM 输出模型（用于 function calling）
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
# 工具函数
# ---------------------------------------------------------------------------

def _now() -> str:
    """当前 ISO 时间戳。"""
    return datetime.now(timezone.utc).isoformat()


def _render_dialogue(messages: list[Any]) -> str:
    """将消息列表渲染为对话文本，受字符预算限制。"""
    lines: list[str] = []
    used = 0
    for msg in messages:
        role = getattr(msg, "role", "")
        content = (getattr(msg, "content", "") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        line = f"{role}: {content[:800]}"
        if used + len(line) > DIALOGUE_CHAR_BUDGET:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines) if lines else "暂无近期原始对话。"


def _clean_text(value: Any) -> str | None:
    """清理文本，空转 None。"""
    text = str(value or "").strip()
    return text or None


def _clean_courses(value: Any) -> list[str]:
    """清理课程列表，去重。"""
    raw = [value] if isinstance(value, str) else (value if isinstance(value, list) else [])
    courses: list[str] = []
    seen: set[str] = set()
    for item in raw:
        course = str(item or "").strip()
        if course and course not in seen:
            seen.add(course)
            courses.append(course)
    return courses


def _clamp_confidence(value: Any) -> float:
    """将任意值转为 0-1 置信度。"""
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except (TypeError, ValueError):
        return 0.0


def _avg_confidence(profile_json: dict[str, Any]) -> float:
    """计算所有有内容维度的平均置信度。"""
    dims = profile_json.get("dimensions") or {}
    values = [
        float((dims.get(k) or {}).get("confidence") or 0)
        for k in ALL_PROFILE_DIMENSIONS
        if (dims.get(k) or {}).get("summary") or (dims.get(k) or {}).get("evidence")
    ]
    return round(sum(values) / len(values), 2) if values else 0.0


# ---------------------------------------------------------------------------
# 首次登录画像
# ---------------------------------------------------------------------------

def normalize_onboarding(payload: dict[str, Any] | None) -> dict[str, Any]:
    """标准化首次登录表单数据。"""
    src = payload or {}
    result = {f: _clean_text(src.get(f)) for f in ONBOARDING_FIELDS + ONBOARDING_OPTIONAL_FIELDS if f != "courses"}
    result["courses"] = _clean_courses(src.get("courses"))
    return result


def is_onboarding_complete(profile: dict[str, Any] | None) -> bool:
    """检查首次登录必填字段是否完整。"""
    norm = normalize_onboarding(profile)
    return all(bool(norm.get(f)) if f != "courses" else bool(norm["courses"]) for f in ONBOARDING_FIELDS)


def build_onboarding_profile(
    onboarding: dict[str, Any],
    old_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """从首次登录表单构建画像 JSON。"""
    norm = normalize_onboarding(onboarding)
    profile = deepcopy(old_json) if old_json else make_default_profile_json()
    if not isinstance(profile, dict):
        profile = make_default_profile_json()

    dims = profile.get("dimensions")
    if not isinstance(dims, dict):
        dims = make_default_profile_json()["dimensions"]

    # 拼接描述文本
    courses_text = "、".join(norm["courses"])
    lang_text = f"，常用编程语言为 {norm['preferred_language']}" if norm.get("preferred_language") else ""
    school_parts = [norm.get(f) for f in ("school", "school_level", "education_level", "grade", "major") if norm.get(f)]
    school_text = "，".join(school_parts)

    # 填充三个维度
    dims[PROFILE_DIMENSION_KNOWLEDGE_FOUNDATION] = _make_dim(
        PROFILE_DIMENSION_NAMES[PROFILE_DIMENSION_KNOWLEDGE_FOUNDATION],
        f"{norm.get('education_level')} {norm.get('major')} 学生，正在学习 {courses_text}{lang_text}。",
        ["来自首次登录学习资料"],
    )
    dims[PROFILE_DIMENSION_LEARNING_GOAL] = _make_dim(
        PROFILE_DIMENSION_NAMES[PROFILE_DIMENSION_LEARNING_GOAL],
        f"围绕 {courses_text} 的当前目标是：{norm.get('learning_goal')}。",
        ["来自首次登录学习资料"],
    )
    dims[PROFILE_DIMENSION_LEARNING_HISTORY] = _make_dim(
        PROFILE_DIMENSION_NAMES[PROFILE_DIMENSION_LEARNING_HISTORY],
        school_text or None,
        ["来自首次登录学习资料"] if school_text else [],
    )

    profile["profile_version"] = 3
    profile["format"] = "json"
    profile["student_profile"] = norm
    profile["dimensions"] = dims
    profile["recommended_strategy"] = [
        f"优先围绕 {courses_text} 生成学习资源",
        f"资源难度参考 {norm.get('education_level')} / {norm.get('grade')} 阶段",
        f"学习活动聚焦：{norm.get('learning_goal')}",
    ]
    profile["last_update_reason"] = "基于首次登录学习资料初始化画像"
    profile["overall_confidence"] = _avg_confidence(profile)
    return profile


def _make_dim(name: str, summary: str | None, evidence: list[str], confidence: float = 0.85) -> dict[str, Any]:
    """构建单个维度字典。"""
    has_content = bool(summary) or bool(evidence)
    return {
        "name": name,
        "confidence": confidence if has_content else 0.0,
        "summary": summary,
        "evidence": evidence[:5],
        "updated_at": _now() if has_content else None,
    }


# ---------------------------------------------------------------------------
# 评分快照
# ---------------------------------------------------------------------------

def _score_dim(dim: dict[str, Any]) -> int | None:
    """计算单维度评分（1-100），无内容返回 None。"""
    summary = str(dim.get("summary") or "").strip()
    evidence = dim.get("evidence") or []
    if not summary and not evidence:
        return None
    conf = _clamp_confidence(dim.get("confidence"))
    # 评分公式：置信度 55% + 摘要 20% + 证据 25%
    evidence_bonus = min(25, len(evidence) * 8)
    summary_bonus = 20 if summary else 0
    return max(1, min(100, round(conf * 55 + summary_bonus + evidence_bonus)))


def build_score_json(profile_json: dict[str, Any]) -> dict[str, Any]:
    """构建评分快照。"""
    dims = profile_json.get("dimensions") or {}

    # 各维度评分
    dim_scores = {k: _score_dim(dims.get(k) or {}) for k in ALL_PROFILE_DIMENSIONS}
    valid_scores = [s for s in dim_scores.values() if s is not None]

    # 缺失维度
    missing = [k for k, s in dim_scores.items() if s is None]

    # 覆盖率
    coverage = round((len(ALL_PROFILE_DIMENSIONS) - len(missing)) / len(ALL_PROFILE_DIMENSIONS) * 100)

    # 证据质量
    evidence_count = sum(len((dims.get(k) or {}).get("evidence") or []) for k in ALL_PROFILE_DIMENSIONS)
    evidence_score = min(100, evidence_count * 20)

    # 总分
    overall = round(sum(valid_scores) / len(valid_scores)) if valid_scores else None
    confidence = _avg_confidence(profile_json)

    result = make_default_profile_score_json()
    result.update({
        "overall_score": overall,
        "confidence": confidence,
        "dimension_scores": dim_scores,
        "section_coverage": coverage,
        "evidence_quality": evidence_score,
        "missing_sections": missing,
        "scored_at": _now(),
    })
    return result


# ---------------------------------------------------------------------------
# 画像构建服务
# ---------------------------------------------------------------------------

class ProfileBuilder:
    """画像构建服务：从对话生成 8 维度画像。"""

    def __init__(self, module: str = "mentor", store: MemoryStore | None = None) -> None:
        self.module = module
        self.store = store or MemoryStore()
        self.llm = get_llm_manager()
        self.llm_kwargs = {"temperature": 0.1, "streaming": False}

    async def build(self, user_id: int, session_id: str | None = None) -> tuple[bool, bool]:
        """构建画像。

        Returns:
            (success, updated): 是否成功、是否有更新
        """
        logger.info("[ProfileBuilder] 开始 user=%s session=%s", user_id, session_id)

        # 确定会话
        sid = session_id
        if sid is None:
            sessions = await self.store.get_user_chat_sessions(user_id=user_id, module=self.module, limit=1)
            sid = sessions[0].id if sessions else f"user-{user_id}-default-{self.module}"

        # 查询数据
        old = await self.store.get_user_profile(user_id, self.module)
        msgs = await self.store.get_recent_messages(user_id, sid, self.module, limit=DIALOGUE_LIMIT)
        logger.info("[ProfileBuilder] 数据就绪 old=%s msgs=%s", "yes" if old else "no", len(msgs))

        # 准备上下文
        old_json = old.profile_json if old and old.profile_json else make_default_profile_json()
        old_text = json.dumps(old_json, ensure_ascii=False)
        dialogue_text = _render_dialogue(msgs)
        logger.info("[ProfileBuilder] 上下文 old_len=%s dialogue_len=%s", len(old_text), len(dialogue_text))

        # 调用 LLM
        try:
            prompt = BUILD_PROMPT.format(old_profile=old_text[:3000], recent_dialogue=dialogue_text)
            logger.debug("[ProfileBuilder] 调用 LLM")
            resp = await self.llm.ainvoke_structured(
                "spark_max",
                ProfileOutput,
                prompt,
                function_name="update_student_profile",
                function_description="根据旧画像和近期对话返回学生画像。",
                model_kwargs=self.llm_kwargs,
            )
            logger.info("[ProfileBuilder] LLM 成功")
        except Exception as e:
            logger.error("[ProfileBuilder] LLM 失败: %s", e)
            return False, False

        # 解析结果
        new_json = self._parse_response(resp.model_dump())
        if not new_json:
            logger.warning("[ProfileBuilder] 解析结果为空")
            return True, False

        # 保留首次登录数据
        if old_json.get("student_profile"):
            new_json["student_profile"] = normalize_onboarding(old_json["student_profile"])

        score_json = build_score_json(new_json)
        logger.info("[ProfileBuilder] 解析完成 dims=%s conf=%.2f", len(new_json.get("dimensions", {})), score_json["confidence"])

        # 检查是否有变化
        if old and old.profile_json and self._is_same(new_json, old.profile_json):
            logger.info("[ProfileBuilder] 无变化")
            return True, False

        # 保存
        try:
            await self.store.update_user_profile(
                user_id=user_id,
                module=self.module,
                profile_json=new_json,
                profile_score_json=score_json,
                updated_reason="基于旧画像和近期对话生成画像",
                source_session_ids=[sid],
                confidence=score_json["confidence"],
            )
            logger.info("[ProfileBuilder] 保存成功 user=%s", user_id)
            return True, True
        except Exception as e:
            logger.error("[ProfileBuilder] 保存失败: %s", e)
            return False, False

    def _parse_response(self, payload: str | dict[str, Any]) -> dict[str, Any]:
        """解析 LLM 响应为画像 JSON。"""
        parsed = payload if isinstance(payload, dict) else parse_first_json_object(payload)
        if not parsed:
            return {}

        profile = make_default_profile_json()
        profile["profile_version"] = 3
        profile["format"] = "json"
        profile["student_profile"] = None

        # 解析各维度
        raw_dims = parsed.get("dimensions") or {}
        dims: dict[str, dict[str, Any]] = {}
        for key in ALL_PROFILE_DIMENSIONS:
            raw = raw_dims.get(key) or {}
            summary = raw.get("summary")
            evidence = raw.get("evidence") or []
            conf = raw.get("confidence")
            has = bool(summary) or bool(evidence)
            dims[key] = {
                "name": PROFILE_DIMENSION_NAMES.get(key, key),
                "confidence": _clamp_confidence(conf) if has else 0.0,
                "summary": str(summary).strip() if summary else None,
                "evidence": [str(i).strip() for i in evidence if str(i).strip()][:5],
                "updated_at": _now() if has else None,
            }
        profile["dimensions"] = dims

        # 策略和原因
        strategies = parsed.get("recommended_strategy") or []
        profile["recommended_strategy"] = [str(s).strip() for s in strategies if str(s).strip()][:5]
        profile["last_update_reason"] = str(parsed.get("last_update_reason") or "").strip()
        profile["overall_confidence"] = _avg_confidence(profile)
        return profile

    def _is_same(self, new: dict[str, Any], old: dict[str, Any]) -> bool:
        """比较两个画像是否相同（忽略时间戳）。"""
        def strip(data: dict[str, Any]) -> dict[str, Any]:
            d = deepcopy(data)
            d.pop("overall_confidence", None)
            for dim in (d.get("dimensions") or {}).values():
                if isinstance(dim, dict):
                    dim.pop("updated_at", None)
                    dim.pop("score", None)
            return d
        return strip(new) == strip(old)
