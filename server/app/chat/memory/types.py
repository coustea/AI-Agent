"""Chat 私有记忆类型与辅助工具。

核心常量：
  DIALOGUE_ROLES — 压缩时只保留 user/assistant 对话
  MESSAGE_EXPIRE_DAYS — 短期消息过期天数（默认 7 天）
  LTM_CATEGORIES / LTM_CATEGORY_NAMES — 长期记忆的 7 个分类及中文名

辅助函数：
  now() — UTC 时间（数据库写入统一用 UTC）
  estimate_token_count() — 粗略估算（max(len//4, word_count)），用于触发阈值判断
  has_stable_signal() — 正则检测文本是否包含值得持久化的学习特征
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Final

from pydantic import BaseModel


# 压缩时保留的角色 — 仅 user 和 assistant 的对话会被压缩，系统消息等被过滤
DIALOGUE_ROLES: Final[frozenset[str]] = frozenset({"user", "assistant"})
# 短期消息过期天数 — 超过此天数的消息会被清理
MESSAGE_EXPIRE_DAYS: Final[int] = 7
# 新建会话的默认标题
DEFAULT_SESSION_TITLE: Final[str] = "新对话"
# 会话标题的最大字符数
TITLE_MAX_LENGTH: Final[int] = 100

# 长期记忆的7个分类 — 覆盖学习者画像的各个维度
LTM_CATEGORIES: Final[tuple[str, ...]] = (
    "learning_background",     # 学习背景：专业、年级、已有知识基础
    "long_term_goals",         # 长期目标：学习方向、考试目标、职业规划
    "learning_preferences",    # 学习偏好：喜欢的教学方式、节奏、难度
    "stable_weaknesses",       # 稳定薄弱点：反复出错的知识点和概念
    "interaction_rules",       # 交互规则：用户偏好的沟通方式和回复风格
    "effective_strategies",    # 有效辅导策略：对该用户特别有效的教学方法
    "corrections",             # 用户纠正记录：用户明确纠正过的错误理解
)

# 长期记忆分类的中文名称 — 用于 Markdown 模板生成和显示
LTM_CATEGORY_NAMES: Final[dict[str, str]] = {
    "learning_background": "学习背景",
    "long_term_goals": "长期目标",
    "learning_preferences": "学习偏好",
    "stable_weaknesses": "稳定薄弱点",
    "interaction_rules": "交互规则",
    "effective_strategies": "有效辅导策略",
    "corrections": "用户纠正记录",
}


def now() -> datetime:
    """返回当前 UTC 时间。"""

    return datetime.now(timezone.utc)


def estimate_token_count(text: str) -> int:
    """粗略估算文本 token 数 — 取字符数/4 和词数的较大值。

    这是一个快速估算，用于触发压缩阈值判断，不需要精确计数。
    中文场景下字符数/4 更接近实际 token 数，英文场景下词数更准确。
    """

    stripped = (text or "").strip()
    if not stripped:
        return 0
    # 取两个估算值的较大值：字符数/4（适合中文）和词数（适合英文）
    return max(max(1, len(stripped) // 4), len(stripped.split()))


def truncate_text(text: str, char_budget: int, suffix: str = "...") -> str:
    """按字符预算截断文本 — 超出部分用后缀替代。

    用于限制输入到 LLM 或存储的文本长度，避免超出 token 限制。
    """

    if len(text) <= char_budget:
        return text
    # 截断时预留后缀空间，并移除尾部空白避免截断在单词中间
    return text[: max(char_budget - len(suffix), 0)].rstrip() + suffix


def extract_fallback_summary_markdown(chat_text: str, max_lines: int = 8, char_budget: int = 1200) -> str:
    """LLM 不可用时的降级摘要 — 取前 N 行拼接为简易 Markdown 摘要。

    作为 LLM 压缩失败时的兜底方案，确保压缩流程不会中断。
    限制最大行数和总字符数，避免生成过长的摘要。
    """

    # 清理空行，保留有效内容
    normalized_lines = [line.strip() for line in str(chat_text or "").splitlines() if line.strip()]
    if not normalized_lines:
        return "# 会话摘要\n\n- 暂无可压缩的历史对话。"

    # 取前 max_lines 行，每行截断为140字符
    selected = normalized_lines[:max_lines]
    bullets = [f"- {truncate_text(line, 140)}" for line in selected]
    # 如果有更多行，添加省略提示
    if len(normalized_lines) > max_lines:
        bullets.append(f"- 其余 {len(normalized_lines) - max_lines} 条对话已省略。")
    body = "\n".join(bullets)
    return truncate_text(f"# 会话摘要\n\n{body}", char_budget)


def make_default_memory_markdown() -> str:
    """生成空白长期记忆 Markdown 模板 — 包含所有7个分类的空占位。

    首次为用户创建长期记忆时使用，后续由 LLM 更新具体内容。
    """

    lines = ["# 长期记忆", "", "## 学习背景", "暂无学习背景信息。"]
    # 遍历剩余6个分类，添加空的 Markdown 小节
    for key in LTM_CATEGORIES[1:]:
        lines.extend(["", f"## {LTM_CATEGORY_NAMES[key]}", "暂无信息。"])
    return "\n".join(lines)


class MemoryUpdateOutput(BaseModel):
    """长期记忆更新结果 — LLM 结构化输出的 Pydantic 模型。

    用于 ainvoke_json 的输出校验，确保 LLM 返回符合预期格式的结果。
    """

    # 是否需要更新记忆 — False 表示当前对话不包含值得持久化的内容
    need_update: bool = False
    # 更新后的完整记忆 Markdown — 仅在 need_update=True 时返回
    memory_markdown: str | None = None
    # 更新置信度 — 必须 ≥ min_confidence（默认0.75）才实际写入
    confidence: float = 0.75
    # 更新原因说明 — 供日志和调试使用
    update_reason: str = ""


# 稳定学习信号的正则模式 — 用于检测对话中值得持久化的学习特征
# 每个模式匹配一类特定的学习信号，匹配任一即认为存在稳定信号
STABLE_SIGNAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    # 模式1: 反复出现的问题 — "总是出错"、"经常记不住"等，表示稳定薄弱点
    re.compile(r"(总是|经常|一直|老是|反复).*(出错|不会|卡住|记不住|搞不清|混淆|薄弱|边界)"),
    # 模式2: 用户的明确指示 — "以后希望..."、"下次请..."等，表示交互规则偏好
    re.compile(r"(以后|下次|后续).*(希望|想|请|先|多|少|给|讲|不要|必须|应该|保持|沿用|避免|记住)"),
    # 模式3: 偏好表达 — "喜欢"、"不喜欢"、"偏好"等，表示学习偏好
    re.compile(r"(喜欢|不喜欢|更喜欢|偏好|习惯)"),
    # 模式4: 学习目标 — "在学考研"、"准备提高"等，表示长期目标
    re.compile(r"(在学|正在学|学过|准备|打算|想要).*(考研|提高|练习|项目)"),
    # 模式5: 背景信息 — "专业是..."、"准备面试"等，表示学习背景
    re.compile(r"(专业|年级|方向|课程|考试|证书|竞赛|实习|面试|项目)"),
)

# 无意义文本集合 — 这些简短的确认性回复不包含稳定信号，应跳过检测
NON_SIGNIFICANT_TEXTS: Final[frozenset[str]] = frozenset(
    {"谢谢", "好的", "收到", "明白了", "继续", "再来一道题", "ok", "OK"}
)


def has_stable_signal(text: str) -> bool:
    """检测文本是否包含稳定的学习特征信号 — 通过正则模式匹配。

    返回 True 表示该文本包含值得持久化的学习特征（偏好、纠正、背景等）。
    用于触发长期记忆的更新流程。
    """

    # 归一化文本：去除多余空白，统一为单空格分隔
    normalized = " ".join((text or "").strip().split())
    # 空文本或确认性回复（"好的"、"收到"等）直接返回 False
    if not normalized or normalized in NON_SIGNIFICANT_TEXTS:
        return False
    # 遍历所有正则模式，任一匹配即返回 True
    return any(pattern.search(normalized) for pattern in STABLE_SIGNAL_PATTERNS)
