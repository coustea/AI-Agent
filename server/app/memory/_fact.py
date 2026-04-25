"""Long-term fact extraction and long-term memory helpers.  # 长期事实提取与长期记忆辅助

模块职责：
- 从对话中抽取可稳定复用的用户事实/偏好/目标等
- 将抽取结果写入长期记忆池供后续检索使用
- 提供结构化输出模型确保 LLM 输出格式一致

核心类：
- FactExtractionService: 事实提取服务主入口
- FactExtraction: LLM 结构化输出的顶层容器
- ExtractedFactItem: 单条事实条目模型

设计原则：
- 使用 Pydantic 的 extra="forbid" 严格约束输出字段
- 先做廉价启发式门控，避免无意义的 LLM 调用
- 提取结果上限 3 条，控制写入量
- 时效性事实自动计算 expires_at

调用链：
chat/agent.py → MemoryLayer.post_turn_pipeline() → FactExtractionService.extract_and_save()
"""

from __future__ import annotations

from datetime import timedelta

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.infra.llm import get_deepseek_llm
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

# 提示词文本会通过 PydanticOutputParser 的 format_instructions 与 FactExtraction 的 Pydantic 数据模型（字段约束）强绑定；改动字段/含义时必须同步更新提示词，否则容易解析失败或持久化脏数据。
FACT_EXTRACTION_PROMPT = """  # 长期记忆提取提示词模板：只注入已有长期记忆/最新对话，并强制模型按解析器要求输出结构化结果（最多 3 条）
# 角色与目标
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

# 输出约束
1. 每条 content 必须是独立、简洁、可长期复用的用户相关记忆。
2. 如记忆与时间节点相关，请标记时效性并估算过期天数。
3. 如果没有值得写入长期记忆池的内容，has_fact=false 且 facts=[]。
4. 最多输出 3 条。

# 已有长期记忆：
{memory_context}

# 最新对话记录：
{chat_history}

# 输出格式要求
{format_instructions}
"""


class ExtractedFactItem(BaseModel):
    """单条长期事实条目模型。  # 描述一条可写入长期记忆池的事实/偏好/目标等

    字段说明：
    - content: 事实文本内容，必须非空
    - memory_type: 长期记忆类型，用于下游分类/检索策略
    - is_time_sensitive: 是否具备时效性，True 时需配合过期策略
    - expires_in_days: 时效过期天数，仅 is_time_sensitive=True 时有意义

    设计原则：
    - 使用 extra="forbid" 禁止额外字段，防止提示词漂移导致脏数据
    - content 必须经过 strip() 清理，不能为空
    """
    model_config = ConfigDict(extra="forbid")  # 禁止额外字段：一旦模型输出出现未定义键就立即失败，避免提示词漂移/解析偏差把未知字段悄悄写入存储。

    content: str = Field(min_length=1)  # 事实文本内容
    memory_type: FactAgentMemoryType  # 长期记忆类型（用于下游分类/检索策略，不同类型可能对应不同展示或更新规则）
    is_time_sensitive: bool = False  # 是否具备时效性：True 表示该事实可能随时间过期，需要配合过期策略处理
    expires_in_days: int | None = Field(default=None, gt=0)  # 时效过期天数（>0）；用于计算存储层 expires_at。仅在 is_time_sensitive=True 时才有意义；None 表示模型未提供有效的过期信息。

    @field_validator("content")
    @classmethod
    def _clean_content(cls, value: str) -> str:
        """清理 content 字段：去除首尾空白，确保非空。"""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content 不能为空")
        return cleaned


class FactExtraction(BaseModel):
    """事实提取结果容器。  # LLM 结构化输出的顶层对象

    字段说明：
    - has_fact: 是否发现值得写入长期记忆的事实信号
    - facts: 提取到的事实条目列表

    设计原则：
    - 使用 extra="forbid" 保持解析严格
    - has_fact=False 时调用方应忽略 facts
    - 写入前仍会做数量上限与存储层校验
    """
    model_config = ConfigDict(extra="forbid")  # 保持解析严格：出现未知字段通常意味着提示词与数据模型不一致或模型幻觉，应直接失败而不是吞掉。

    has_fact: bool  # 是否发现值得写入长期记忆的事实信号；为 False 时调用方应忽略 facts
    facts: list[ExtractedFactItem] = Field(default_factory=list)  # 提取到的事实条目列表（默认空；写入前仍会做数量上限与存储层校验）


class FactExtractionService:
    """事实提取服务。  # 从会话消息中抽取长期事实，并写入 MemoryStore 的用户事实池

    职责：
    - 从最近对话中提取可长期复用的用户信息
    - 使用启发式门控避免无意义的 LLM 调用
    - 将结构化结果写入长期记忆池

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
        self.llm = get_deepseek_llm(temperature=0.1, streaming=False)  # 使用 DeepSeek 做事实抽取：低温度减少发散，非流式便于结构化解析
        self.output_parser = PydanticOutputParser(pydantic_object=FactExtraction)  # 结构化输出解析器：把模型文本解析为 FactExtraction
        self.prompt_template = ChatPromptTemplate.from_messages([("human", "{prompt_text}")])

    async def extract_and_save(self, user_id: int, session_id: str) -> bool:
        """从会话中提取事实并保存。  # 主入口：从对话中抽取长期记忆并写入存储

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
        5. 解析结构化输出并写入存储
        """
        # 抽取按"尽力而为"处理：大多数"无事可做"的路径返回 True；只有出现真正异常时才返回 False，便于调用方做告警/降级。
        recent_msgs = await self.store.get_recent_messages(  # 获取最近 20 条消息作为抽取窗口：兼顾近期性与上下文长度开销
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            limit=20,
        )
        if not recent_msgs:
            return True

        dialogue_msgs = select_dialogue_messages(recent_msgs)  # 筛选"可用于抽取"的对话消息（通常会排除系统/工具类噪声）
        if not dialogue_msgs:
            return True

        user_texts = self._collect_user_texts(dialogue_msgs)  # 收集用户侧文本片段（过滤无意义短语），用于后续"是否值得抽取"的门控
        # 先做一个廉价的启发式门控：当用户没说任何稳定/可复用信息时，避免触发昂贵的大模型调用。
        if not has_extractable_signal(user_texts):  # 检查是否存在可长期记忆的信号；没有则直接返回
            return True

        chat_history = build_chat_history_text(dialogue_msgs)  # 构建对话历史文本：提供给模型作为"最新对话记录"上下文
        memory_context = await build_memory_context_text(self.store, user_id, self.module_name)  # 构建已有长期记忆文本：指导模型避免重复输出

        try:
            prompt_text = FACT_EXTRACTION_PROMPT.format(  # 组装最终提示词：把上下文与解析器格式要求（format_instructions）一起注入
                memory_context=memory_context,
                chat_history=chat_history,
                format_instructions=self.output_parser.get_format_instructions(),
            )
            response = await self.llm.ainvoke(self.prompt_template.format_messages(prompt_text=prompt_text))  # 调用大模型进行结构化抽取
            # 不同大模型实现的 response.content 可能是 str 或其他对象；这里统一转成字符串再交给解析器。
            extracted = self.output_parser.parse(response.content if isinstance(response.content, str) else str(response.content))  # 严格解析结构化输出（不符合数据模型约束会抛错）
            if extracted.has_fact and extracted.facts:  # 仅当模型明确标记"有事实"且列表非空时才写入存储，避免空写入/误触发
                for item in extracted.facts[:3]:  # 再做一次上限裁剪（最多 3 条）：与提示约束保持一致，防止越界输出导致写入过多
                    expires_at = None
                    if item.is_time_sensitive and item.expires_in_days and item.expires_in_days > 0:  # 若为时效事实且提供了过期天数，则计算 expires_at
                        expires_at = now() + timedelta(days=item.expires_in_days)
                    try:
                        await self.store.save_user_fact(
                            user_id=user_id,
                            content=item.content,
                            memory_type=item.memory_type,
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
