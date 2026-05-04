"""长期记忆更新服务 — 从对话中提取并更新用户长期记忆。

模块职责：
- 判断是否需要更新长期记忆
- 从对话中提取长期稳定信息
- 更新 UserLongTermMemory 的 memory_json 和 memory_markdown

设计原则：
- 只沉淀长期稳定信息
- 不保存会话临时状态、一次性作业中间状态
- 合并相似信息，保留用户明确表达的偏好/目标/纠正
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.memory._store import MemoryStore, now

logger = get_logger(__name__)

MEMORY_UPDATE_PROMPT = """# 角色与目标
你是一个专业的长期记忆更新器。请根据【当前用户消息】【助手回复】【会话概要】和【旧长期记忆】，判断是否需要更新长期记忆，并输出更新后的内容。

# 只保存这些长期稳定信息
1. 用户明确表达的学习背景（专业、年级、学校、技术栈）
2. 用户明确表达的长期目标（考试、证书、项目、职业规划）
3. 用户反复暴露的稳定薄弱点（长期不熟悉的知识区域）
4. 用户明确表达的交互偏好（喜欢的回答风格、详细程度、语言）
5. 用户对 AI 的纠正、约束、禁忌
6. 已验证有效的辅导策略

# 不保存这些内容
1. 当前会话临时状态（进行到哪一步、当前报错）
2. 一次性作业中间状态
3. 普通问答细节
4. 会话摘要（由会话概要系统处理）

# 输出要求
1. 如果不需要更新，只输出：NO_UPDATE
2. 如果需要更新，输出 JSON 格式：
```json
{
  "need_update": true,
  "update_reason": "更新原因",
  "memory_json": {
    "learning_background": {
      "major": null,
      "grade": null,
      "description": "学习背景描述"
    },
    "long_term_goals": ["目标1", "目标2"],
    "learning_preferences": ["偏好1", "偏好2"],
    "stable_weaknesses": ["薄弱点1", "薄弱点2"],
    "project_context": ["项目背景1"],
    "interaction_rules": ["交互规则1"],
    "effective_strategies": ["有效策略1"],
    "corrections": ["用户纠正1"],
    "recent_important_changes": ["最近重要变化1"]
  }
}
```

【当前用户消息】
{user_message}

【助手回复】
{assistant_reply}

【会话概要】
{session_summary}

【旧长期记忆】
{old_memory}
"""

STABLE_SIGNAL_PATTERNS = (
    re.compile(r"我(?:总是|经常|一直|老是|反复).*(?:出错|不会|卡住|卡在|记不住|搞不清|混淆|薄弱|边界)"),
    re.compile(r"我(?:喜欢|不喜欢|更喜欢|偏好|习惯)"),
    re.compile(r"我(?:在学|正在学|学过|以前学过|已经学过|准备|打算|想(?:学|考|准备|提高|练习))"),
    re.compile(r"(?:专业|年级|方向|课程|考试|证书|竞赛|实习|面试|项目)"),
    re.compile(r"(?:你|ai|AI|助手).*(?:错了|理解错|误解|不对|遗漏|应该|不要|别|记住|以后)"),
    re.compile(r"(?:以后|下次|后续).*(?:不要|别|先|必须|应该|保持|沿用|避免)"),
)

NON_SIGNIFICANT_TEXTS = frozenset({
    "谢谢", "好的", "收到", "明白了", "继续", "再来一道题", "ok", "OK"
})


def has_stable_signal(text: str) -> bool:
    normalized = " ".join((text or "").strip().lower().split())
    if not normalized:
        return False
    if normalized in NON_SIGNIFICANT_TEXTS:
        return False
    return any(pattern.search(normalized) for pattern in STABLE_SIGNAL_PATTERNS)


class LongTermMemoryUpdateService:
    """长期记忆更新服务 — 判断并更新用户长期记忆。"""

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

    async def should_update_memory(
        self,
        user_message: str,
        assistant_reply: str,
    ) -> bool:
        if has_stable_signal(user_message):
            return True
        if has_stable_signal(assistant_reply):
            return True
        return False

    async def update_long_term_memory(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
    ) -> bool:
        if not await self.should_update_memory(user_message, assistant_reply):
            return False

        old_memory = await self.store.get_or_create_long_term_memory(user_id, self.module_name)
        session_summary = await self.store.get_latest_session_summary(user_id, session_id, self.module_name)

        summary_text = session_summary.summary_markdown if session_summary else "暂无会话概要。"
        old_memory_text = old_memory.memory_markdown if old_memory else "暂无长期记忆。"

        try:
            prompt_text = MEMORY_UPDATE_PROMPT.format(
                user_message=user_message[:1000],
                assistant_reply=assistant_reply[:1000],
                session_summary=summary_text[:2000],
                old_memory=old_memory_text[:3000],
            )
            response = await self.llm_manager.ainvoke(
                "spark_x",
                prompt_text,
                model_kwargs=self.model_kwargs,
            )
            response_text = response.content if isinstance(response.content, str) else str(response.content)
        except Exception as exc:
            logger.error("[LongTermMemory] LLM 调用失败: %s", str(exc))
            return False

        if "NO_UPDATE" in response_text.upper():
            return False

        memory_json = self._parse_memory_json(response_text)
        if not memory_json:
            return False

        from app.memory.memory_types import render_long_term_memory_markdown
        memory_markdown = render_long_term_memory_markdown(memory_json)

        try:
            await self.store.update_long_term_memory(
                user_id=user_id,
                module=self.module_name,
                memory_markdown=memory_markdown,
                memory_json=memory_json,
                updated_reason="基于对话更新长期记忆",
                source_session_ids=[session_id],
            )
            return True
        except Exception as exc:
            logger.error("[LongTermMemory] 更新长期记忆失败: %s", str(exc))
            return False

    def _parse_memory_json(self, response_text: str) -> dict[str, Any] | None:
        import json
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[len("```json"):].strip()
        if text.startswith("```"):
            text = text[3:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
        try:
            data = json.loads(text)
            if data.get("need_update") and data.get("memory_json"):
                return data["memory_json"]
        except json.JSONDecodeError:
            pass
        return None
