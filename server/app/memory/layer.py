"""The only public entry point for the memory subsystem.  # 记忆子系统唯一对外入口

模块职责：
- 提供统一的记忆层 API，封装底层存储/提取/画像实现
- 管理会话、短期记忆、长期记忆、用户画像的完整生命周期
- 提供上下文构建能力，将记忆转换为 LLM 可用的输入

核心类：
- MemoryLayer: 记忆层公共 API，外部模块应只依赖此类
- PostChatMemoryOrchestrator: 对话后处理流水线包装器

设计原则：
- 外部模块只应依赖 MemoryLayer，不应直接导入 _store/_fact/_profile
- 所有记忆操作通过此层统一入口
- 后处理流水线按固定顺序执行：累加 token → 事实提取 → 画像更新 → 摘要压缩

调用示例：
    memory_layer = MemoryLayer(module_name="mentor")
    await memory_layer.save_message(user_id=1, session_id="xxx", role="user", content="...")
    profile = await memory_layer.get_profile(user_id=1)
"""

from __future__ import annotations

import json
from typing import Optional

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from app.chat.schemas import ToolCallDetail
from app.chat.utils import truncate
from app.config import PROFILE_GATE_EVERY_N_ASSISTANT_TURNS
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, UserMemory, UserProfile, UserProfileHistory
from app.memory._fact import FactExtractionService
from app.memory.memory_types import (
    MEMORY_TYPE_BACKGROUND,
    MEMORY_TYPE_FACT,
    MEMORY_TYPE_GOAL,
    MEMORY_TYPE_PREFERENCE,
    MEMORY_TYPE_WEAKNESS,
)
from app.memory._profile import ProfileBuildingService, ProfileService
from app.memory._store import (
    MEMORY_COMPRESSION_TOKEN_THRESHOLD,
    MEMORY_EXTRACTION_TOKEN_THRESHOLD,
    MemoryStore,
)
from app.shared.file_service import resolve_uploaded_path

logger = get_logger(__name__)


class PostChatMemoryOrchestrator:
    """对话后处理流水线包装器。  # 提供向后兼容的流水线入口

    职责：
    - 封装 MemoryLayer.post_turn_pipeline 调用
    - 提供简单的构造器注入点用于测试

    使用场景：
    - 对话结束后触发记忆提取和画像更新
    """

    def __init__(
        self,
        *,
        module_name: str,
        memory: MemoryStore | None = None,
        fact_extraction: FactExtractionService | None = None,
        profile_building: ProfileBuildingService | None = None,
    ) -> None:
        """初始化流水线包装器。

        参数：
        - module_name: 模块名
        - memory: 存储层实例（用于测试注入）
        - fact_extraction: 事实提取服务实例（用于测试注入）
        - profile_building: 画像构建服务实例（用于测试注入）
        """
        self.layer = MemoryLayer(module_name=module_name)
        if memory is not None:
            self.layer.store = memory
        if fact_extraction is not None:
            self.layer.fact_extraction = fact_extraction
        if profile_building is not None:
            self.layer.profile_builder = profile_building

    async def run(self, *, user_id: int, session_id: str, user_message: str, assistant_reply: str) -> None:
        """执行对话后处理流水线。  # 触发记忆提取、画像更新和摘要压缩

        参数：
        - user_id: 用户ID
        - session_id: 会话ID
        - user_message: 用户消息内容
        - assistant_reply: 助手回复内容
        """
        await self.layer.post_turn_pipeline(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
        )


class MemoryLayer:
    """记忆层公共 API。  # 外部模块应只依赖此类，不应直接导入内部实现

    职责：
    - 会话管理：创建/查询/列举/归档会话
    - 短期记忆：消息的写入/读取/统计/清理
    - 长期记忆：事实的增删改查与类型化查询
    - 用户画像：读取/更新/历史追踪
    - 上下文构建：将记忆转换为 LLM 可用的输入
    - 后处理流水线：对话后的记忆提取、画像更新、摘要压缩

    设计原则：
    - 统一封装底层存储/提取/画像服务
    - 提供清晰的分层接口
    - 后处理流水线按固定顺序执行
    """

    def __init__(self, *, module_name: str) -> None:
        """初始化记忆层。

        参数：
        - module_name: 模块名，参与存储分区键
        """
        self.module_name = module_name
        self.store = MemoryStore()  # 底层存储：负责会话/短期消息/长期记忆的持久化读写，以及各类计数器与阈值相关状态
        self.profile_service = ProfileService()  # 画像服务：负责用户画像与画像历史的读取/写入/版本记录
        self.fact_extraction = FactExtractionService(  # 事实提取服务：从短期对话中抽取可沉淀的事实/偏好等并写入长期记忆
            module_name=module_name,
            store=self.store,
        )
        self.profile_builder = ProfileBuildingService(  # 画像构建服务：基于对话与长期事实聚合/更新用户画像特征（可产生历史版本）
            module_name=module_name,
            store=self.store,
            profile_service=self.profile_service,
        )

    # ------------------------------------------------------------------
    # 会话管理  # 会话 CRUD：创建/查询/列举/归档会话，以及会话内计数器的集中重置入口
    # ------------------------------------------------------------------

    async def create_session(self, *, user_id: int, title: str = "新对话"):
        """创建新会话。  # 初始化会话元数据（标题/模块），用于后续消息与记忆的归属

        参数：
        - user_id: 用户ID
        - title: 会话标题，默认"新对话"

        返回：
        - ChatSession 实例
        """
        return await self.store.create_chat_session(user_id=user_id, module=self.module_name, title=title)

    async def get_session(self, *, session_id: str):
        """获取会话。  # 按会话ID读取会话信息（含状态/标题等）

        参数：
        - session_id: 会话ID

        返回：
        - ChatSession 实例或 None
        """
        return await self.store.get_chat_session(session_id)

    async def list_sessions(self, *, user_id: int, limit: int = 20):
        """获取用户会话列表。  # 按用户与模块列出最近会话（用于会话切换/回显）

        参数：
        - user_id: 用户ID
        - limit: 返回数量上限

        返回：
        - ChatSession 列表
        """
        return await self.store.get_user_chat_sessions(user_id=user_id, module=self.module_name, limit=limit)

    async def archive_session(self, *, user_id: int, session_id: str) -> bool:
        """归档会话。  # 标记会话为归档（不再作为活跃会话出现在默认列表）

        参数：
        - user_id: 用户ID
        - session_id: 会话ID

        返回：
        - True: 归档成功
        - False: 会话不存在
        """
        return await self.store.archive_chat_session(session_id=session_id, user_id=user_id)

    async def reset_session_counters(self, *, user_id: int, session_id: str) -> None:
        """重置会话计数器。  # 清空事实提取/画像更新的门控计数，便于重新建立触发节奏

        参数：
        - user_id: 用户ID
        - session_id: 会话ID
        """
        await self.store.reset_memory_extraction_counter(user_id=user_id, session_id=session_id, module=self.module_name)
        await self.store.reset_profile_update_counter(user_id=user_id, session_id=session_id, module=self.module_name)

    # ------------------------------------------------------------------
    # 短期记忆管理  # 会话内消息的写入/读取/统计/清理（用于上下文拼装与后处理）
    # ------------------------------------------------------------------

    async def create_short_term_message(
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: str | None = None,
        tool_calls: str | None = None,
        diagram: dict | None = None,
    ) -> int:
        """写入短期记忆消息。  # 保存一条会话消息（可附带附件/工具调用元数据），供后续上下文与审计使用

        参数：
        - user_id: 用户ID
        - session_id: 会话ID
        - role: 消息角色（user/assistant/system/tool）
        - content: 消息内容
        - attachments: 附件信息（JSON 字符串）
        - tool_calls: 工具调用记录（JSON 字符串）
        - diagram: 图解数据（Mermaid 源码等）

        返回：
        - 会话当前消息总数
        """
        return await self.store.save_message(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
            diagram=diagram,
        )

    async def save_message(
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: str | None = None,
        tool_calls: str | None = None,
        diagram: dict | None = None,
    ) -> None:
        """保存消息。  # 历史兼容别名（内部仍落到 create_short_term_message，避免重复实现）

        参数：
        - user_id: 用户ID
        - session_id: 会话ID
        - role: 消息角色
        - content: 消息内容
        - attachments: 附件信息
        - tool_calls: 工具调用记录
        - diagram: 图解数据
        """
        await self.create_short_term_message(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
            diagram=diagram,
        )

    async def list_short_term_messages(
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int | None = None,
        days: int = 7,
        only_unexpired: bool = True,
    ) -> list[ChatMessage]:
        """获取短期记忆消息列表。  # 用于构建最近上下文（可按天数/过期状态过滤，limit 控制条数）

        参数：
        - user_id: 用户ID
        - session_id: 会话ID
        - limit: 返回数量上限
        - days: 过期天数阈值
        - only_unexpired: 是否只返回未过期消息

        返回：
        - ChatMessage 列表
        """
        return await self.store.get_recent_messages(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            limit=limit,
            days=days,
            only_unexpired=only_unexpired,
        )

    async def count_short_term_messages(self, *, user_id: int, session_id: str) -> int:
        """获取短期记忆消息数量。  # 用于统计与触发门控的外部观测

        参数：
        - user_id: 用户ID
        - session_id: 会话ID

        返回：
        - 消息总数
        """
        return await self.store.get_message_count(user_id=user_id, session_id=session_id, module=self.module_name)

    async def delete_short_term_messages(self, *, user_id: int, session_id: str, keep_recent: int = 0) -> int:
        """删除短期记忆消息。  # 支持全量清空或仅保留最近 N 条

        参数：
        - user_id: 用户ID
        - session_id: 会话ID
        - keep_recent: 保留最近 N 条，0 表示全量删除

        返回：
        - 删除的消息数量
        """
        if keep_recent <= 0:
            return await self.store.clear_session_messages(user_id=user_id, session_id=session_id, module=self.module_name)
        return await self.store.delete_old_messages(user_id=user_id, session_id=session_id, module=self.module_name, keep_recent=keep_recent)

    # ------------------------------------------------------------------
    # 长期记忆管理  # 对"用户事实/偏好/目标"等可沉淀信息的增删改查与类型化查询
    # ------------------------------------------------------------------

    async def create_long_term_memory(
        self,
        *,
        user_id: int,
        session_id: str,
        content_markdown: str,
        memory_type: str,
        dimension: str | None = None,
        importance: float = 0.5,
        source: str = "conversation",
        source_message_count: int = 0,
        title: str | None = None,
    ) -> UserMemory:
        """创建长期记忆。  # 写入一条长期记忆记录（含类型/维度/重要度/来源等元数据）

        参数：
        - user_id: 用户ID
        - session_id: 会话ID
        - content_markdown: 记忆内容（Markdown）
        - memory_type: 记忆类型
        - dimension: 维度标签
        - importance: 重要度（0-1）
        - source: 来源标识
        - source_message_count: 来源消息数量
        - title: 记忆标题

        返回：
        - UserMemory 实例
        """
        return await self.store.save_long_term_memory(
            user_id=user_id,
            session_id=session_id,
            content_markdown=content_markdown,
            memory_type=memory_type,
            dimension=dimension,
            importance=importance,
            source=source,
            source_message_count=source_message_count,
            module=self.module_name,
            title=title,
        )

    async def upsert_long_term_fact(
        self,
        *,
        user_id: int,
        content_markdown: str,
        memory_type: str,
        session_id: str | None = None,
        expires_at=None,
    ) -> UserMemory:
        """插入或更新长期事实。  # 对同类事实做去重/合并，避免长期记忆无限膨胀

        参数：
        - user_id: 用户ID
        - content_markdown: 事实内容（Markdown）
        - memory_type: 记忆类型
        - session_id: 会话ID
        - expires_at: 过期时间

        返回：
        - UserMemory 实例
        """
        return await self.store.save_user_fact(
            user_id=user_id,
            content_markdown=content_markdown,
            memory_type=memory_type,
            session_id=session_id,
            expires_at=expires_at,
            module=self.module_name,
        )

    async def get_long_term_memory(self, *, memory_id: int, user_id: int | None = None) -> UserMemory | None:
        """根据ID获取长期记忆。  # 可选按 user_id 做额外范围约束

        参数：
        - memory_id: 记忆ID
        - user_id: 用户ID（用于权限约束）

        返回：
        - UserMemory 实例或 None
        """
        return await self.store.get_long_term_memory_by_id(memory_id, user_id=user_id, module=self.module_name)

    async def list_long_term_memories(self, *, user_id: int, limit: int = 10, only_unexpired: bool = True) -> list[UserMemory]:
        """获取长期记忆列表。  # 默认只返回未过期内容，limit 控制输出规模

        参数：
        - user_id: 用户ID
        - limit: 返回数量上限
        - only_unexpired: 是否只返回未过期记忆

        返回：
        - UserMemory 列表
        """
        return await self.store.get_long_term_memories(
            user_id=user_id,
            module=self.module_name,
            limit=limit,
            only_unexpired=only_unexpired,
        )

    async def query_long_term_memories_by_type(
        self,
        *,
        user_id: int,
        memory_types: list[str] | None = None,
        per_type_limits: dict[str, int] | None = None,
        only_unexpired: bool = True,
    ) -> dict[str, list[UserMemory]]:
        """按类型查询长期记忆。  # 支持指定类型集合与每类上限，用于上下文拼装与画像构建

        参数：
        - user_id: 用户ID
        - memory_types: 要查询的类型列表
        - per_type_limits: 每类返回上限
        - only_unexpired: 是否只返回未过期记忆

        返回：
        - 按类型分组的记忆字典
        """
        return await self.store.get_user_context_memories(
            user_id=user_id,
            memory_types=memory_types,
            per_type_limits=per_type_limits,
            only_unexpired=only_unexpired,
            module=self.module_name,
        )

    async def update_long_term_memory(
        self,
        *,
        memory_id: int,
        user_id: int | None = None,
        content_markdown: str | None = None,
        memory_type: str | None = None,
        dimension: str | None = None,
        importance: float | None = None,
        expires_at=None,
        source: str | None = None,
        title: str | None = None,
    ) -> UserMemory | None:
        """更新长期记忆。  # 允许按字段部分更新（内容/类型/维度/重要度/过期时间等）

        参数：
        - memory_id: 记忆ID
        - user_id: 用户ID（用于权限约束）
        - content_markdown: 新内容（Markdown）
        - memory_type: 新类型
        - dimension: 新维度
        - importance: 新重要度
        - expires_at: 新过期时间
        - source: 新来源
        - title: 新标题

        返回：
        - 更新后的 UserMemory 实例或 None
        """
        return await self.store.update_long_term_memory(
            memory_id,
            user_id=user_id,
            module=self.module_name,
            content_markdown=content_markdown,
            memory_type=memory_type,
            dimension=dimension,
            importance=importance,
            expires_at=expires_at,
            source=source,
        )

    async def delete_long_term_memory(self, *, memory_id: int, user_id: int | None = None) -> bool:
        """删除长期记忆。  # 按ID删除（可选按 user_id 做安全范围约束）

        参数：
        - memory_id: 记忆ID
        - user_id: 用户ID（用于权限约束）

        返回：
        - True: 删除成功
        - False: 记忆不存在或无权限
        """
        return await self.store.delete_long_term_memory(memory_id, user_id=user_id, module=self.module_name)

    # ------------------------------------------------------------------
    # 用户画像管理  # 画像读取/更新/历史追踪，以及主动触发画像构建与事实提取的入口
    # ------------------------------------------------------------------

    async def get_profile(self, *, user_id: int) -> UserProfile | None:
        """获取用户画像。  # 读取当前最新画像快照

        参数：
        - user_id: 用户ID

        返回：
        - UserProfile 实例或 None
        """
        return await self.profile_service.get_user_profile(user_id)

    async def upsert_profile(
        self,
        *,
        user_id: int,
        profile_markdown: str,
        change_reason: str = "系统自动更新",
        source_session_ids: list[str] | None = None,
        source_memory_ids: list[int] | None = None,
        confidence: float = 0.7,
    ) -> UserProfile:
        """插入或更新用户画像。  # 写入画像 Markdown 并记录变更原因/来源记忆，便于审计与回溯

        参数：
        - user_id: 用户ID
        - profile_markdown: 画像 Markdown 内容
        - change_reason: 变更原因
        - source_session_ids: 来源会话ID列表
        - source_memory_ids: 来源记忆ID列表
        - confidence: 画像置信度

        返回：
        - UserProfile 实例
        """
        return await self.profile_service.update_user_profile(
            user_id=user_id,
            profile_markdown=profile_markdown,
            change_reason=change_reason,
            source_session_ids=source_session_ids,
            source_memory_ids=source_memory_ids,
            confidence=confidence,
        )

    async def update_profile(
        self,
        *,
        user_id: int,
        profile_markdown: str,
        change_reason: str = "系统自动更新",
        source_session_ids: list[str] | None = None,
        source_memory_ids: list[int] | None = None,
        confidence: float = 0.7,
    ) -> UserProfile:
        """更新用户画像。  # 历史兼容别名（同 upsert_profile，避免重复实现）

        参数：
        - user_id: 用户ID
        - profile_markdown: 画像 Markdown 内容
        - change_reason: 变更原因
        - source_session_ids: 来源会话ID列表
        - source_memory_ids: 来源记忆ID列表
        - confidence: 画像置信度

        返回：
        - UserProfile 实例
        """
        return await self.upsert_profile(
            user_id=user_id,
            profile_markdown=profile_markdown,
            change_reason=change_reason,
            source_session_ids=source_session_ids,
            source_memory_ids=source_memory_ids,
            confidence=confidence,
        )

    async def list_profile_history(self, *, user_id: int, limit: int = 20) -> list[UserProfileHistory]:
        """获取画像历史版本。  # 用于回溯画像随时间的变化

        参数：
        - user_id: 用户ID
        - limit: 返回数量上限

        返回：
        - UserProfileHistory 列表
        """
        return await self.profile_service.get_profile_history(user_id=user_id, limit=limit)

    async def build_profile(self, *, user_id: int, session_id: str | None = None) -> bool:
        """构建用户画像。  # 主动触发画像构建流程（通常由门控策略周期性调用）

        参数：
        - user_id: 用户ID
        - session_id: 会话ID

        返回：
        - True: 构建成功
        - False: 构建失败
        """
        success, _ = await self.profile_builder.build_profile(user_id=user_id, session_id=session_id)
        return success

    async def extract_facts(self, *, user_id: int, session_id: str) -> bool:
        """提取事实。  # 主动触发事实提取并写入长期记忆（通常由 token 阈值门控触发）

        参数：
        - user_id: 用户ID
        - session_id: 会话ID

        返回：
        - True: 提取成功或无内容可提取
        - False: 提取失败
        """
        return await self.fact_extraction.extract_and_save(user_id=user_id, session_id=session_id)

    # ------------------------------------------------------------------
    # 提示词/上下文构建  # 将画像/长期记忆/近期对话/附件转为大模型可用的输入片段
    # ------------------------------------------------------------------

    async def build_profile_context(self, user_id: int) -> str:
        """构建画像上下文文本。  # 直接返回画像 Markdown

        参数：
        - user_id: 用户ID

        返回：
        - 画像 Markdown 文本
        """
        profile = await self.get_profile(user_id=user_id)
        if not profile or not profile.profile_markdown:
            return "暂无画像信息（新用户），请直接开始对话。"
        return profile.profile_markdown

    async def build_long_term_memory_context(self, user_id: int) -> str:
        """构建长期记忆上下文文本。  # 按记忆类型分组输出 Markdown 内容

        参数：
        - user_id: 用户ID

        返回：
        - 格式化的长期记忆文本
        """
        memories_by_type = await self.query_long_term_memories_by_type(user_id=user_id)
        titles = {  # 长期记忆类型到展示标题的映射：决定输出分组顺序与标题文案
            MEMORY_TYPE_PREFERENCE: "偏好",
            MEMORY_TYPE_GOAL: "目标",
            MEMORY_TYPE_WEAKNESS: "薄弱点",
            MEMORY_TYPE_FACT: "稳定事实",
            MEMORY_TYPE_BACKGROUND: "背景信息",
        }
        chunks: list[str] = []
        for memory_type, title in titles.items():
            items = memories_by_type.get(memory_type, [])
            if not items:
                continue
            # 使用 content_markdown 字段
            chunks.append(f"### {title}\n" + "\n".join(f"- {item.content_markdown}" for item in items))
        return "\n\n".join(chunks) if chunks else "暂无特定事实记忆。"

    async def build_recent_chat_context(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        image_urls: Optional[list[str]],
        file_urls: Optional[list[str]],
    ) -> tuple[list[AnyMessage], str]:
        """构建最近聊天上下文。  # 同时输出 langchain 消息序列与人类可读摘要（用于调试/可视化）

        参数：
        - user_id: 用户ID
        - session_id: 会话ID
        - user_message: 当前用户消息
        - image_urls: 图片附件URL列表
        - file_urls: 文件附件URL列表

        返回：
        - tuple[list[AnyMessage], str]: (langchain 消息列表, 人类可读的近期上下文文本)

        设计原则：
        - 仅包含 user/assistant 两类角色，tool 等消息不参与上下文组装
        - 最后一条消息视为"当前轮消息"，组装历史时排除它避免重复
        - 附件不作为独立消息插入，而是以行内标记追加到当前用户消息末尾
        """
        initial_messages: list[AnyMessage] = []
        recent_lines: list[str] = []
        recent_msgs = await self.list_short_term_messages(user_id=user_id, session_id=session_id, limit=10)
        # 注意：短期消息列表里最后一条按约定视为"当前轮消息"（通常刚写入），为避免重复拼装，这里组装历史时先排除它。
        for msg in recent_msgs[:-1]:  # 遍历历史时排除最后一条：最后一条会在下方以"当前用户消息（含附件标记）"形式重新加入
            if msg.role == "user":
                initial_messages.append(HumanMessage(content=msg.content))
                recent_lines.append(f"- 用户: {msg.content}")
            elif msg.role == "assistant":
                initial_messages.append(AIMessage(content=msg.content))
                recent_lines.append(f"- 助手: {msg.content}")

        content = user_message
        # 附件不作为独立消息插入，而是以行内标记追加到"当前用户消息"末尾，确保模型把附件信息视为同一轮输入的一部分。
        if image_urls:  # 若有图片附件，则在当前用户消息末尾追加图片列表标记（不新增独立消息）
            content += f"\n[Attached Images: {', '.join(image_urls)}]"
        if file_urls:  # 若有文件附件，则在当前用户消息末尾追加文件列表标记（不新增独立消息）
            content += f"\n[Attached Files: {', '.join(file_urls)}]"
        initial_messages.append(HumanMessage(content=content))
        recent_context = "\n".join(recent_lines) if recent_lines else "最近 7 天暂无历史对话。"
        return initial_messages, recent_context

    @staticmethod
    def build_file_context(image_urls: Optional[list[str]], file_urls: Optional[list[str]]) -> str:
        """构建文件上下文文本。  # 将上传URL解析为本地路径并输出为可读清单（供提示词/日志使用）

        参数：
        - image_urls: 图片URL列表
        - file_urls: 文件URL列表

        返回：
        - 格式化的文件清单文本
        """
        lines: list[str] = []
        if image_urls:
            for url in image_urls:
                resolved = resolve_uploaded_path(url)
                local_path = resolved[1] if resolved else ""
                lines.append(f"- 图片: URL={url}, 本地路径={local_path}" if local_path else f"- 图片: {url}")
        if file_urls:
            for url in file_urls:
                resolved = resolve_uploaded_path(url)
                local_path = resolved[1] if resolved else ""
                filename = url.split("/")[-1]
                lines.append(
                    f"- 文件名: {filename}, URL: {url}, 本地路径={local_path}"
                    if local_path
                    else f"- 文件名: {filename}, URL: {url}"
                )
        if not lines:
            return "用户未上传文件。"
        return "用户上传了以下附件:\n" + "\n".join(lines)

    # ------------------------------------------------------------------
    # 后处理流水线  # 对话后处理：按固定顺序维护计数器、触发提取/画像更新，并在最后做摘要压缩
    # ------------------------------------------------------------------

    async def post_turn_pipeline(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
    ) -> None:
        """对话后处理流水线。  # 严格按顺序累加 token → 条件触发提取/画像更新 → 最后压缩，避免门控与上下文观察口径出错

        参数：
        - user_id: 用户ID
        - session_id: 会话ID
        - user_message: 用户消息内容
        - assistant_reply: 助手回复内容

        流程：
        1. 累加 token 计数器
        2. 检查是否触发事实提取（基于 token 阈值）
        3. 检查是否触发画像更新（基于 assistant 轮次周期）
        4. 执行摘要压缩（基于 token 阈值）

        设计原则：
        - 调用顺序有强依赖：必须先累加 token，后续门控判断才能使用最新计数
        - 摘要压缩放在最后：保证事实提取/画像构建能观察到未压缩的最近一轮内容
        """
        # 调用顺序有强依赖：必须先累加 token，后续基于阈值的门控判断才能使用"最新计数"做出是否触发的决策。
        await self.store.accumulate_session_tokens(  # 累加本轮 user+assistant 文本的 token 计数（为阈值门控提供依据）
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            content=f"{user_message}\n{assistant_reply}",
        )
        if await self.store.should_trigger_memory_extraction(  # 检查是否触发事实提取：基于 token 计数阈值做门控
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            threshold=MEMORY_EXTRACTION_TOKEN_THRESHOLD,
        ):
            success = await self.extract_facts(user_id=user_id, session_id=session_id)
            if success:
                # 仅在提取成功时才重置计数器：失败时保留触发信号，避免"该触发但信号被清掉"导致长时间不再触发。
                await self.store.reset_memory_extraction_counter(user_id=user_id, session_id=session_id, module=self.module_name)  # 成功提取后重置事实提取计数器（失败不重置）

        recent_msgs = await self.store.get_recent_messages(  # 检查是否触发画像更新：按近期 assistant 轮次数做周期性门控
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            limit=80,
        )
        # 以 assistant 角色消息数作为"轮次"口径（忽略 tool 等角色），用于决定是否到达画像更新的触发周期。
        assistant_turns = sum(1 for msg in recent_msgs if getattr(msg, "role", "") == "assistant")
        if assistant_turns and assistant_turns % PROFILE_GATE_EVERY_N_ASSISTANT_TURNS == 0:  # 每 N 轮 assistant 回复触发一次画像构建评估
            success, updated = await self.profile_builder.build_profile(user_id=user_id, session_id=session_id)
            if success and updated:
                # 仅当画像确实发生变化才重置计数器：这样"无变化的评估"不会打乱既定的周期性触发节奏。
                await self.store.reset_profile_update_counter(user_id=user_id, session_id=session_id, module=self.module_name)

        # 摘要压缩刻意放在最后：保证事实提取/画像构建能观察到未压缩的最近一轮内容，避免信息提前被摘要吞掉而影响抽取质量。
        await self.store.summarize_and_compress(  # 对旧消息做摘要压缩：在不丢失关键语义的前提下降低上下文与存储规模
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            threshold=MEMORY_COMPRESSION_TOKEN_THRESHOLD,
        )

    async def persist_tool_messages(
        self,
        *,
        user_id: int,
        session_id: str,
        tool_call_records: list[ToolCallDetail],
    ) -> None:
        """持久化工具调用消息。  # 将工具调用记录写入短期消息（摘要+原始记录），用于回放/审计/排障

        参数：
        - user_id: 用户ID
        - session_id: 会话ID
        - tool_call_records: 工具调用记录列表

        设计原则：
        - 同时保存可读摘要（content）与原始记录（tool_calls），兼顾界面展示与问题排查
        - 工具返回结果截断到 2000 字符，避免短期消息内容无限膨胀
        """
        if not tool_call_records:
            return
        for record in tool_call_records:
            try:
                # ToolCallDetail 是字典样式对象：这里同时保存可读摘要（content）与原始记录（tool_calls），兼顾界面展示与问题排查。
                tool_name = str(record.get("tool", "unknown"))
                status = str(record.get("status", "success"))
                args = record.get("args", {})
                result = str(record.get("result", ""))
                # 工具返回结果可能很长：摘要里只保留前 2000 字符，避免短期消息内容无限膨胀。
                content = (
                    f"工具调用: {tool_name}\n"
                    f"状态: {status}\n"
                    f"参数: {args}\n"
                    f"结果: {result[:2000]}"
                )
                # 为兼容既有存储结构：将"单条 record"包一层列表后再 JSON 序列化写入 tool_calls；ensure_ascii=False 保留中文可读性。
                payload = json.dumps([record], ensure_ascii=False)
                await self.create_short_term_message(
                    user_id=user_id,
                    session_id=session_id,
                    role="tool",
                    content=content,
                    tool_calls=payload,
                )
            except Exception:
                logger.exception(
                    "[%s] persistence.tool_record.failed user=%s session=%s record=%s",
                    self.module_name, user_id, session_id, truncate(record, 300),
                )
