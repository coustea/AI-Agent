

"""Profile 模块纯函数策略层。

提供信号检测、画像评分等纯函数，无副作用，易于测试和复用。
借鉴 app/memory/policy.py 的设计模式。
"""

from __future__ import annotations

import re
from typing import Final

from app.memory.helpers import normalize_text

# ---------------------------------------------------------------------------
# 信号检测常量（从 fact_agent.py 提取）
# ---------------------------------------------------------------------------

# 无意义的对话文本，不触发记忆提取
MEMORY_NON_SIGNIFICANT_TEXTS: Final[frozenset[str]] = frozenset({
    "谢谢", "好的", "收到", "明白了", "继续", "再来一道题", "ok", "OK"
})

# 问题标记词，用于识别用户是否在提问
MEMORY_QUESTION_MARKERS: Final[tuple[str, ...]] = (
    "什么是", "什么叫", "怎么", "如何", "为什么",
    "请解释", "解释一下", "讲讲", "介绍一下", "请问",
    "我想问", "能不能", "可不可以",
)

# 稳定信号模式：匹配这些模式的文本才值得提取为长期记忆
MEMORY_STABLE_SIGNAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"我(?:总是|经常|一直|老是|反复).*(?:出错|不会|卡住|卡在|记不住|搞不清|混淆|薄弱|边界)"),
    re.compile(r"我(?:喜欢|不喜欢|更喜欢|偏好|习惯)"),
    re.compile(r"我(?:在学|正在学|学过|以前学过|已经学过|准备|打算|想(?:学|考|准备|提高|练习))"),
    re.compile(r"我(?:下周|本学期|这学期|最近|目前|现在).*(?:学|补|复习|准备|做题|刷题|作业|实验|项目|考试)"),
    re.compile(r"(?:专业|年级|方向|课程|考试|证书|竞赛|实习|面试|项目|课设|论文)"),
)

# 标点符号清理正则
_MEMORY_SIGNAL_PUNCT_RE: Final[re.Pattern[str]] = re.compile(
    r'[。！？!?；;，,、：:…""\"\'`（）()\[\]{}<>《》\s]+'
)


# ---------------------------------------------------------------------------
# 信号检测函数
# ---------------------------------------------------------------------------

def normalize_signal_text(text: str) -> str:
    """归一化信号文本，移除标点和多余空白。"""
    cleaned = normalize_text(text)
    return _MEMORY_SIGNAL_PUNCT_RE.sub(" ", cleaned).strip()


def is_memory_worthy_text(text: str) -> bool:
    """判断单条文本是否包含值得长期记忆的稳定信号。

    规则：
    1. 如果是纯提问（含问题标记或问号）且不匹配稳定信号模式，返回 False
    2. 如果匹配任一稳定信号模式，返回 True
    """
    normalized = normalize_signal_text(text)
    if not normalized:
        return False

    has_question_shape = any(marker in normalized for marker in MEMORY_QUESTION_MARKERS)
    has_question_mark = "?" in text or "？" in text

    # 纯提问且无稳定信号 → 不值得记忆
    if (has_question_shape or has_question_mark) and not any(
        pattern.search(normalized) for pattern in MEMORY_STABLE_SIGNAL_PATTERNS
    ):
        return False

    return any(pattern.search(normalized) for pattern in MEMORY_STABLE_SIGNAL_PATTERNS)


def has_extractable_signal(texts: list[str]) -> bool:
    """判断文本列表是否包含可提取的长期记忆信号。

    用于在调用 LLM 之前快速过滤无意义的对话。
    """
    cleaned_texts = [normalize_signal_text(text) for text in texts]
    ignore = {normalize_signal_text(t) for t in MEMORY_NON_SIGNIFICANT_TEXTS}
    cleaned_texts = [text for text in cleaned_texts if text and text not in ignore]
    return any(is_memory_worthy_text(text) for text in cleaned_texts)


# ---------------------------------------------------------------------------
# 画像评分策略
# ---------------------------------------------------------------------------

# 维度评分区间定义
SCORE_RANGE_BEGINNER = (0, 30)      # 初级：了解概念，但缺乏实践或经常出错
SCORE_RANGE_INTERMEDIATE = (31, 60) # 中级：有一定基础，能应用但不够熟练
SCORE_RANGE_GOOD = (61, 80)         # 良好：掌握较好，能灵活运用
SCORE_RANGE_EXCELLENT = (81, 100)   # 优秀：深入掌握，能举一反三


def clamp_score(score: int | None) -> int | None:
    """将评分限制在 0-100 范围内。"""
    if score is None:
        return None
    return max(0, min(100, score))


def interpret_score_level(score: int | None) -> str:
    """根据评分返回等级描述。"""
    if score is None:
        return "未知"
    if score <= 30:
        return "初级"
    if score <= 60:
        return "中级"
    if score <= 80:
        return "良好"
    return "优秀"


def should_update_profile(
    current_profile: dict | None,
    extracted_features: dict,
) -> bool:
    """判断是否需要更新画像。

    规则：
    1. 如果提取结果明确标记 should_update=False，不更新
    2. 如果提取结果有非空字段且与当前画像不同，更新
    """
    if not extracted_features.get("should_update", True):
        return False

    # 移除 should_update 标记后的实际字段
    features = {k: v for k, v in extracted_features.items() if k != "should_update" and v is not None}
    if not features:
        return False

    # 新用户，需要更新
    if not current_profile:
        return True

    # 检查是否有实质性变化
    for key, value in features.items():
        current_value = current_profile.get(key)
        if current_value != value:
            return True

    return False


def merge_profile_features(
    current: dict | None,
    extracted: dict,
) -> dict:
    """合并画像特征。

    规则：
    1. 提取结果中的非空字段覆盖当前值
    2. 提取结果中的空字段保留当前值
    3. 新字段直接添加
    """
    if current is None:
        current = {}

    result = dict(current)
    for key, value in extracted.items():
        if key == "should_update":
            continue
        if value is not None:
            result[key] = value
        elif key in result:
            # 提取结果为空，保留当前值
            pass

    return result


# ---------------------------------------------------------------------------
# 画像维度常量
# ---------------------------------------------------------------------------

PROFILE_DIMENSIONS: Final[tuple[str, ...]] = (
    "knowledge_level",      # 知识基础
    "cognitive_style",      # 认知风格
    "error_pattern",        # 易错点偏好
    "learning_goal",        # 学习目标
    "learning_history",     # 学习历史
    "interest_preference",  # 兴趣偏好
    "learning_pace",        # 学习节奏
    "cognitive_level",      # 认知水平
)

PROFILE_SCORE_FIELDS: Final[tuple[str, ...]] = (
    "knowledge_level_score",
    "cognitive_style_score",
    "error_pattern_score",
    "learning_goal_score",
    "learning_history_score",
    "interest_preference_score",
    "learning_pace_score",
    "cognitive_level_score",
)
