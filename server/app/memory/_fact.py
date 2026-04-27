from __future__ import annotations

from datetime import timedelta

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.memory.memory_types import FactAgentMemoryType
from app.memory._profile import (
    build_chat_history_text,
    build_memory_context_text,
    has_extractable_signal,
    normalize_signal_text,
    select_dialogue_messages,
    MEMORY_NON_SIGNIFICANT_TEXTS,
)
from app.memory._store import MemoryStore, now

logger = get_logger(__name__)

# 长期记忆提取提示词：让大模型输出 Markdown 格式的记忆
FACT_EXTRACTION_PROMPT = """# 角色与目标
你是一个专业的长期记忆提取器。你只负责提取长期记忆，不负责总结对话、生成画像、规划学习路径、评价用户或回答用户问题。
你的唯一任务是从用户的【最新导师对话记录】中，提取值得写入【长期记忆池】的长期记忆候选。

# 只提取这些长期记忆
1. 用户明确表达的稳定偏好。
2. 用户明确提出的长期或阶段性目标。
3. 用户自身相关、后续对话可复用的稳定事实或背景。
4. 用户反复暴露或明确承认的稳定薄弱点。

# 不提取这些内容
1. 不提取助手的建议、解释、评价、计划或总结。
2. 不提取普通闲聊、寒暄、临时情绪、一次性问题或当前轮任务请求。
3. 不根据对话推断画像，不输出学习风格、能力评估、性格判断等非长期记忆内容。
4. 不重复已有长期记忆；只有更具体、更准确或明显更新时才输出。

# 输出格式
如果没有值得保存的信息，请只输出：NO_MEMORY

如果有记忆，请按以下格式输出一条或多条（最多 3 条）：

---MEMORY---
TITLE: 记忆标题
TYPE: preference | goal | weakness | fact | background | summary
DIMENSION: 可选维度，没有则写 none
IMPORTANCE: 0.0 到 1.0
CONTENT:
# 记忆标题

## 内容

这里写完整的 Markdown 记忆内容。

## 适用场景

说明这条记忆在后续什么场景下应该被使用。

## 证据

用简短自然语言说明这条记忆来自最近哪些对话表现，不要复制大段原文。
---END---

# 已有长期记忆：
{memory_context}

# 最新对话记录：
{chat_history}
"""


class FactExtractionService:
    """事实提取服务。  # 从会话消息中抽取长期事实，并写入 MemoryStore 的用户事实池

    职责：
    - 从最近对话中提取可长期复用的用户信息
    - 使用启发式门控避免无意义的 LLM 调用
    - 将 Markdown 结果写入长期记忆池

    调用入口：
    - extract_and_save(user_id, session_id) -> bool

    设计原则：
    - module_name 参与存储分区键，决定读写哪个模块的长期记忆池
    - 使用 DeepSeek 模型做抽取，低温度减少发散
    - 尽力而为处理：大多数"无事可做"返回 True，只有真正异常才返回 False
    """

    def __init__(self, *, module_name: str = "mentor",
                 store: MemoryStore | None = None,
                 profile_service: object | None = None) -> None:
        """初始化事实提取服务。

        参数：
        - module_name: 模块名，参与存储分区键
        - store: 存储层实例，None 时使用默认 MemoryStore
        - profile_service: 画像服务实例（当前未使用）
        """
        self.module_name = module_name  # module_name 会参与存储分区键：它决定读写哪个"模块/场景"的长期记忆池
        self.store = store or MemoryStore()
        self.llm_manager = get_llm_manager()
        self.model_kwargs = {"temperature": 0.1, "streaming": False}

    async def extract_and_save(self, user_id: int, session_id: str) -> bool:
        """从会话中提取事实并保存。

        参数：
        - user_id: 用户ID
        - session_id: 会话ID

        返回：
        - True: 提取成功或无内容可提取
        - False: 出现异常

        流程：
        1. 获取最近 20 条消息
        2. 筛选可用对话消息
        3. 启发式门控检查是否有可提取信号
        4. 构建上下文并调用 LLM
        5. 解析 Markdown 输出并写入存储
        """
        #  获取最近 20 条消息作为抽取窗口
        recent_msgs = await self.store.get_recent_messages(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            limit=20,
        )
        if not recent_msgs:
            return True

        dialogue_msgs = select_dialogue_messages(recent_msgs)  # 筛选"可用于抽取"的对话消息
        if not dialogue_msgs:
            return True

        user_texts = self._collect_user_texts(dialogue_msgs)  # 收集用户侧文本片段，用于后续"是否值得抽取"的门控
        # 先做一个廉价的启发式门控：当用户没说任何稳定/可复用信息时，避免触发昂贵的大模型调用。
        if not has_extractable_signal(user_texts):  # 检查是否存在可长期记忆的信号；没有则直接返回
            return True

        chat_history = build_chat_history_text(dialogue_msgs)  # 构建对话历史文本：提供给模型作为"最新对话记录"上下文
        memory_context = await build_memory_context_text(self.store, user_id, self.module_name)  # 构建已有长期记忆文本：指导模型避免重复输出

        try:
            prompt_text = FACT_EXTRACTION_PROMPT.format(
                memory_context=memory_context,
                chat_history=chat_history,
            )
            response = await self.llm_manager.ainvoke(  # 调用大模型进行抽取
                "deepseek",
                prompt_text,
                model_kwargs=self.model_kwargs,
            )
            # 获取响应文本
            response_text = response.content if isinstance(response.content, str) else str(response.content)
            # 解析并保存记忆
            memories = self._parse_memory_output(response_text)
            if not memories:
                return True  # 无记忆可保存
            for memory_data in memories[:3]:  # 最多保存 3 条
                expires_at = None
                if memory_data.get("is_time_sensitive") and memory_data.get("expires_in_days"):
                    try:
                        expires_at = now() + timedelta(days=int(memory_data["expires_in_days"]))
                    except (ValueError, TypeError):
                        pass
                try:
                    await self.store.save_user_fact(
                        user_id=user_id,
                        content=memory_data["content_markdown"],
                        memory_type=memory_data["memory_type"],
                        session_id=session_id,
                        expires_at=expires_at,
                        module=self.module_name,
                    )
                except ValueError:
                    # 存储层校验/唯一性冲突等 ValueError 不应导致整次抽取失败：跳过该条，继续处理其它事实。
                    continue
            return True
        except Exception as exc:
            logger.error("[FactExtraction] 事实提炼失败: %s", str(exc))
            return False

    def _collect_user_texts(self, messages: list) -> list[str]:
        """收集用户文本。  # 仅保留最近若干条 user 消息，并过滤可预期的无意义短语

        参数：
        - messages: 消息列表

        返回：
        - 清理后的用户文本列表

        设计原则：
        - 只看最近 6 条，控制噪声与上下文长度
        - 过滤预置的无意义短语（如"谢谢"、"好的"）
        - 使用 getattr 保持消息对象类型兼容性
        """
        user_texts: list[str] = []
        ignore = {normalize_signal_text(text) for text in MEMORY_NON_SIGNIFICANT_TEXTS}  # 预置无意义短语集合（先做同样的归一化，便于快速命中过滤）
        # 只看最近 6 条：控制噪声与上下文长度，优先抓取最新的用户陈述；更早的内容通常已在长期记忆上下文里体现。
        for msg in messages[-6:]:
            if getattr(msg, "role", "") != "user":
                continue
            cleaned = normalize_signal_text(getattr(msg, "content", ""))
            if not cleaned or cleaned in ignore:
                continue
            user_texts.append(cleaned)
        return user_texts

    def _parse_memory_output(self, response_text: str) -> list[dict]:
        """解析 LLM 输出的记忆内容。

        参数：
        - response_text: LLM 响应文本

        返回：
        - 解析出的记忆列表，每条记忆包含 title、content_markdown、memory_type、dimension、importance 等字段
        """
        if not response_text or not response_text.strip():
            return []
        # 检查是否为 NO_MEMORY
        if "NO_MEMORY" in response_text.upper():
            return []
        memories = []
        # 按 ---MEMORY--- 分割
        blocks = response_text.split("---MEMORY---")
        for block in blocks:
            if "---END---" not in block:
                continue
            # 提取 ---MEMORY--- 到 ---END--- 之间的内容
            memory_content = block.split("---END---")[0].strip()
            if not memory_content:
                continue
            memory_data = self._parse_single_memory(memory_content)
            if memory_data:
                memories.append(memory_data)
        return memories

    def _parse_single_memory(self, memory_text: str) -> dict | None:
        """解析单条记忆。

        参数：
        - memory_text: 单条记忆文本

        返回：
        - 解析出的记忆字典，或 None（解析失败）
        """
        lines = memory_text.strip().split("\n")
        title = None
        memory_type = "fact"
        dimension = None
        importance = 0.5
        content_start_idx = -1
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("TITLE:"):
                title = line[6:].strip()
            elif line.startswith("TYPE:"):
                type_str = line[5:].strip().lower()
                if type_str in {"preference", "goal", "weakness", "fact", "background", "summary"}:
                    memory_type = type_str
            elif line.startswith("DIMENSION:"):
                dim_str = line[9:].strip().lower()
                if dim_str != "none":
                    dimension = dim_str
            elif line.startswith("IMPORTANCE:"):
                try:
                    importance = float(line[11:].strip())
                    importance = max(0.0, min(1.0, importance))
                except (ValueError, TypeError):
                    importance = 0.5
            elif line.startswith("CONTENT:"):
                content_start_idx = i + 1
                break
        if content_start_idx < 0:
            return None
        # 提取 CONTENT 后的所有内容作为 Markdown
        content_lines = lines[content_start_idx:]
        content_markdown = "\n".join(content_lines).strip()
        if not content_markdown:
            return None
        # 如果没有标题，尝试从 Markdown 中提取第一个标题
        if not title:
            for line in content_lines:
                line = line.strip()
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        return {
            "title": title,
            "content_markdown": content_markdown,
            "memory_type": memory_type,
            "dimension": dimension,
            "importance": importance,
        }
