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
from datetime import datetime, timezone
from typing import Any, Final

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


# 返回当前 UTC 时间（数据库写入统一用 UTC）
def now() -> datetime:
    """返回当前 UTC 时间。"""

    return datetime.now(timezone.utc)


# 估算文本 token 数：优先 tiktoken，否则中英文分段粗略估算
def estimate_token_count(text: str) -> int:
    """估算文本 token 数 — 分段策略，中英文混合更精确。

    策略：
    - 中文字符 × 1.5（中文字符平均 token 密度）
    - 非中文部分按词数估算
    - 若已安装 tiktoken，优先使用精确计数
    """
    # 空文本直接返回 0
    stripped = (text or "").strip()
    if not stripped:
        return 0

    # 优先尝试 tiktoken 精确计数
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(stripped))
    except Exception:
        pass

    # 分段估算：中文 vs 非中文
    chinese_chars = len(re.findall(r"[一-鿿]", stripped))
    non_chinese = re.sub(r"[一-鿿]", "", stripped)
    non_chinese_words = len(non_chinese.split())
    return int(chinese_chars * 1.5) + non_chinese_words


from app.chat.utils import compact_text


# LLM 不可用时的降级摘要：取前 N 行拼接为简易 Markdown 摘要
def extract_fallback_summary_markdown(chat_text: str, max_lines: int = 8, char_budget: int = 1200) -> str:
    """LLM 不可用时的降级摘要 — 取前 N 行拼接为简易 Markdown 摘要。

    作为 LLM 压缩失败时的兜底方案，确保压缩流程不会中断。
    限制最大行数和总字符数，避免生成过长的摘要。
    """

    # 清理空行，保留有效内容
    normalized_lines = [line.strip() for line in str(chat_text or "").splitlines() if line.strip()]
    # 无有效内容返回空摘要占位
    if not normalized_lines:
        return "# 会话摘要\n\n- 暂无可压缩的历史对话。"

    # 取前 max_lines 行，每行截断为140字符
    selected = normalized_lines[:max_lines]
    bullets = [f"- {compact_text(line, limit=140)}" for line in selected]
    # 如果有更多行，添加省略提示
    if len(normalized_lines) > max_lines:
        bullets.append(f"- 其余 {len(normalized_lines) - max_lines} 条对话已省略。")
    body = "\n".join(bullets)
    # 整体压缩到字符预算内返回
    return compact_text(f"# 会话摘要\n\n{body}", limit=char_budget)


# 生成空白长期记忆 Markdown 模板（含 7 个分类空占位，首次创建时使用）
def make_default_memory_markdown() -> str:
    """生成空白长期记忆 Markdown 模板 — 包含所有7个分类的空占位。

    首次为用户创建长期记忆时使用，后续由 LLM 更新具体内容。
    """

    lines = ["# 长期记忆", "", "## 学习背景", "暂无学习背景信息。"]
    # 遍历剩余6个分类，添加空的 Markdown 小节
    for key in LTM_CATEGORIES[1:]:
        lines.extend(["", f"## {LTM_CATEGORY_NAMES[key]}", "暂无信息。"])
    # 拼接为完整模板
    return "\n".join(lines)


# MemoryUpdateOutput：长期记忆更新结果（LLM 结构化输出校验模型）
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
    # 模式5: 背景信息 — 需要第一人称陈述结构，避免单纯关键词出现误触发
    re.compile(r"(我是|我的|我在|我学|我读|我准备|我打算|我考|我参加).*(专业|年级|方向|课程|考试|证书|竞赛|实习|面试|项目)"),
)

# 无意义文本集合 — 这些简短的确认性回复不包含稳定信号，应跳过检测
NON_SIGNIFICANT_TEXTS: Final[frozenset[str]] = frozenset(
    {"谢谢", "好的", "收到", "明白了", "继续", "再来一道题", "ok", "OK"}
)


# 检测文本是否包含稳定学习信号（正则匹配偏好/纠正/背景等）
def has_stable_signal(text: str) -> bool:
    """检测文本是否包含稳定的学习特征信号 — 通过正则模式匹配。

    返回 True 表示该文本包含值得持久化的学习特征（偏好、纠正、背景等）。
    用于触发长期记忆的更新流程。
    """

    # 归一化并剔除无意义短回复
    normalized = " ".join((text or "").strip().split())
    if not normalized or normalized in NON_SIGNIFICANT_TEXTS:
        return False
    # 任一稳定信号模式命中即返回 True
    return any(pattern.search(normalized) for pattern in STABLE_SIGNAL_PATTERNS)


# 从 OpenAI Content Parts 列表或纯字符串中提取文本（兼容旧格式）
def extract_content_text(content: list[dict[str, Any]] | str | None) -> str:
    """从 OpenAI Content Parts 或纯字符串中提取文本。

    ChatMessage.content 存储为 list[dict]（OpenAI Content Parts 格式），
    本函数提取 type=text 的 Part 内容，兼容旧版纯字符串格式。
    """
    if isinstance(content, list):
        return " ".join(
            p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"
        ).strip()
    return str(content or "").strip()


# 统一信号分类：返回是否触发长期记忆更新（画像改为懒加载，故仅 LTM 信号）
def classify_turn_signals(user_message: str, assistant_reply: str) -> dict[str, bool]:
    """统一信号分类 — 返回 LTM 信号。

    学习者画像不再由对话信号实时触发更新（改为 GET /profile 懒加载 + 周概要缓冲），
    故仅保留 LTM 信号。
    """
    ltm_signal = has_stable_signal(user_message) or (
        has_stable_signal(assistant_reply)
        and any(kw in assistant_reply for kw in ("以后", "下次", "记住", "偏好", "纠正"))
    )
    return {
        "ltm": ltm_signal,
    }
