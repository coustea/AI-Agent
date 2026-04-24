"""The only public entry point for the memory subsystem."""  # 记忆子系统唯一公共入口点

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


class MemoryLayer:  # 记忆层公共API：统一管理会话、短期记忆、长期记忆、用户画像
    """Public memory API for chat-like systems.  # 外部模块应只依赖此类

    External modules should depend on this class only.
    Internal memory implementation details live in `_store`, `_fact`, `_profile`.
    """

    def __init__(self, *, module_name: str) -> None:
        self.module_name = module_name
        self.store = MemoryStore()  # 底层存储
        self.profile_service = ProfileService()  # 画像服务
        self.fact_extraction = FactExtractionService(  # 事实提取服务
            module_name=module_name,
            store=self.store,
            profile_service=self.profile_service,
        )
        self.profile_builder = ProfileBuildingService(  # 画像构建服务
            module_name=module_name,
            store=self.store,
            profile_service=self.profile_service,
        )

    # ------------------------------------------------------------------
    # Session  # 会话管理
    # ------------------------------------------------------------------
    async def create_session(self, *, user_id: int, title: str = "新对话"):  # 创建新会话
        return await self.store.create_chat_session(user_id=user_id, module=self.module_name, title=title)

    async def get_session(self, *, session_id: str):  # 获取会话
        return await self.store.get_chat_session(session_id)

    async def list_sessions(self, *, user_id: int, limit: int = 20):  # 获取用户会话列表
        return await self.store.get_user_chat_sessions(user_id=user_id, module=self.module_name, limit=limit)

    async def archive_session(self, *, user_id: int, session_id: str) -> bool:  # 归档会话
        return await self.store.archive_chat_session(session_id=session_id, user_id=user_id)

    async def reset_session_counters(self, *, user_id: int, session_id: str) -> None:  # 重置会话计数器
        await self.store.reset_memory_extraction_counter(user_id=user_id, session_id=session_id, module=self.module_name)
        await self.store.reset_profile_update_counter(user_id=user_id, session_id=session_id, module=self.module_name)

    # ------------------------------------------------------------------
    # Short-term memory  # 短期记忆管理
    # ------------------------------------------------------------------
    async def create_short_term_message(  # 创建短期记忆消息
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: str | None = None,
        tool_calls: str | None = None,
    ) -> int:
        return await self.store.save_message(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
        )

    async def save_message(  # 保存消息（同create_short_term_message）
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: str | None = None,
        tool_calls: str | None = None,
    ) -> None:
        await self.create_short_term_message(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
        )

    async def list_short_term_messages(  # 获取短期记忆消息列表
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int | None = None,
        days: int = 7,
        only_unexpired: bool = True,
    ) -> list[ChatMessage]:
        return await self.store.get_recent_messages(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            limit=limit,
            days=days,
            only_unexpired=only_unexpired,
        )

    async def count_short_term_messages(self, *, user_id: int, session_id: str) -> int:  # 获取短期记忆消息数量
        return await self.store.get_message_count(user_id=user_id, session_id=session_id, module=self.module_name)

    async def delete_short_term_messages(self, *, user_id: int, session_id: str, keep_recent: int = 0) -> int:  # 删除短期记忆消息
        if keep_recent <= 0:
            return await self.store.clear_session_messages(user_id=user_id, session_id=session_id, module=self.module_name)
        return await self.store.delete_old_messages(user_id=user_id, session_id=session_id, module=self.module_name, keep_recent=keep_recent)

    # ------------------------------------------------------------------
    # Long-term memory  # 长期记忆管理
    # ------------------------------------------------------------------
    async def create_long_term_memory(  # 创建长期记忆
        self,
        *,
        user_id: int,
        session_id: str,
        content: str,
        memory_type: str,
        dimension: str | None = None,
        importance: float = 0.5,
        source: str = "conversation",
        source_message_count: int = 0,
    ) -> UserMemory:
        return await self.store.save_long_term_memory(
            user_id=user_id,
            session_id=session_id,
            content=content,
            memory_type=memory_type,
            dimension=dimension,
            importance=importance,
            source=source,
            source_message_count=source_message_count,
            module=self.module_name,
        )

    async def upsert_long_term_fact(  # 插入或更新长期事实（支持去重合并）
        self,
        *,
        user_id: int,
        content: str,
        memory_type: str,
        session_id: str | None = None,
        expires_at=None,
    ) -> UserMemory:
        return await self.store.save_user_fact(
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            session_id=session_id,
            expires_at=expires_at,
            module=self.module_name,
        )

    async def get_long_term_memory(self, *, memory_id: int, user_id: int | None = None) -> UserMemory | None:  # 根据ID获取长期记忆
        return await self.store.get_long_term_memory_by_id(memory_id, user_id=user_id, module=self.module_name)

    async def list_long_term_memories(self, *, user_id: int, limit: int = 10, only_unexpired: bool = True) -> list[UserMemory]:  # 获取长期记忆列表
        return await self.store.get_long_term_memories(
            user_id=user_id,
            module=self.module_name,
            limit=limit,
            only_unexpired=only_unexpired,
        )

    async def query_long_term_memories_by_type(  # 按类型查询长期记忆
        self,
        *,
        user_id: int,
        memory_types: list[str] | None = None,
        per_type_limits: dict[str, int] | None = None,
        only_unexpired: bool = True,
    ) -> dict[str, list[UserMemory]]:
        return await self.store.get_user_context_memories(
            user_id=user_id,
            memory_types=memory_types,
            per_type_limits=per_type_limits,
            only_unexpired=only_unexpired,
            module=self.module_name,
        )

    async def update_long_term_memory(  # 更新长期记忆
        self,
        *,
        memory_id: int,
        user_id: int | None = None,
        content: str | None = None,
        memory_type: str | None = None,
        dimension: str | None = None,
        importance: float | None = None,
        expires_at=None,
        source: str | None = None,
    ) -> UserMemory | None:
        return await self.store.update_long_term_memory(
            memory_id,
            user_id=user_id,
            module=self.module_name,
            content=content,
            memory_type=memory_type,
            dimension=dimension,
            importance=importance,
            expires_at=expires_at,
            source=source,
        )

    async def delete_long_term_memory(self, *, memory_id: int, user_id: int | None = None) -> bool:  # 删除长期记忆
        return await self.store.delete_long_term_memory(memory_id, user_id=user_id, module=self.module_name)

    # ------------------------------------------------------------------
    # Profile  # 用户画像管理
    # ------------------------------------------------------------------
    async def get_profile(self, *, user_id: int) -> UserProfile | None:  # 获取用户画像
        return await self.profile_service.get_user_profile(user_id)

    async def upsert_profile(  # 插入或更新用户画像
        self,
        *,
        user_id: int,
        features: dict,
        change_reason: str = "系统自动更新",
        source_memory_ids: list[int] | None = None,
    ) -> UserProfile:
        return await self.profile_service.update_user_profile(
            user_id=user_id,
            features=features,
            change_reason=change_reason,
            source_memory_ids=source_memory_ids,
        )

    async def update_profile(  # 更新用户画像（同upsert_profile）
        self,
        *,
        user_id: int,
        features: dict,
        change_reason: str = "系统自动更新",
        source_memory_ids: list[int] | None = None,
    ) -> UserProfile:
        return await self.upsert_profile(
            user_id=user_id,
            features=features,
            change_reason=change_reason,
            source_memory_ids=source_memory_ids,
        )

    async def list_profile_history(self, *, user_id: int, limit: int = 20) -> list[UserProfileHistory]:  # 获取画像历史版本
        return await self.profile_service.get_profile_history(user_id=user_id, limit=limit)

    async def build_profile(self, *, user_id: int, session_id: str | None = None) -> bool:  # 构建用户画像
        success, _ = await self.profile_builder.build_profile(user_id=user_id, session_id=session_id)
        return success

    async def extract_facts(self, *, user_id: int, session_id: str) -> bool:  # 提取事实
        return await self.fact_extraction.extract_and_save(user_id=user_id, session_id=session_id)

    # ------------------------------------------------------------------
    # Prompt/context assembly  # 提示词/上下文构建
    # ------------------------------------------------------------------
    async def build_profile_context(self, user_id: int) -> str:  # 构建画像上下文文本
        profile = await self.get_profile(user_id=user_id)
        if not profile:
            return "暂无画像信息（新用户），请直接开始对话。"
        profile_dict = profile.model_dump(exclude_unset=True, exclude={"updated_at", "created_at"})
        if not profile_dict:
            return "暂无画像信息（新用户），请直接开始对话。"
        return "\n".join(f"- {key}: {value}" for key, value in profile_dict.items() if value)

    async def build_long_term_memory_context(self, user_id: int) -> str:  # 构建长期记忆上下文文本
        memories_by_type = await self.query_long_term_memories_by_type(user_id=user_id)
        titles = {  # 类型到中文标题的映射
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
            chunks.append(f"### {title}\n" + "\n".join(f"- {item.content}" for item in items))
        return "\n\n".join(chunks) if chunks else "暂无特定事实记忆。"

    async def build_recent_chat_context(  # 构建最近聊天上下文（用于LLM输入）
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        image_urls: Optional[list[str]],
        file_urls: Optional[list[str]],
    ) -> tuple[list[AnyMessage], str]:
        initial_messages: list[AnyMessage] = []
        recent_lines: list[str] = []
        recent_msgs = await self.list_short_term_messages(user_id=user_id, session_id=session_id, limit=10)
        for msg in recent_msgs[:-1]:  # 排除最后一条（当前消息）
            if msg.role == "user":
                initial_messages.append(HumanMessage(content=msg.content))
                recent_lines.append(f"- 用户: {msg.content}")
            elif msg.role == "assistant":
                initial_messages.append(AIMessage(content=msg.content))
                recent_lines.append(f"- 助手: {msg.content}")

        content = user_message
        if image_urls:  # 添加图片附件标记
            content += f"\n[Attached Images: {', '.join(image_urls)}]"
        if file_urls:  # 添加文件附件标记
            content += f"\n[Attached Files: {', '.join(file_urls)}]"
        initial_messages.append(HumanMessage(content=content))
        recent_context = "\n".join(recent_lines) if recent_lines else "最近 7 天暂无历史对话。"
        return initial_messages, recent_context

    @staticmethod
    def build_file_context(image_urls: Optional[list[str]], file_urls: Optional[list[str]]) -> str:  # 构建文件上下文文本
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
    # Pipelines and audit  # 后处理流水线
    # ------------------------------------------------------------------
    async def post_turn_pipeline(  # 对话后处理流水线：累加token、触发提取、压缩
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
    ) -> None:
        await self.store.accumulate_session_tokens(  # 累加token计数
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            content=f"{user_message}\n{assistant_reply}",
        )
        if await self.store.should_trigger_memory_extraction(  # 检查是否触发事实提取
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            threshold=MEMORY_EXTRACTION_TOKEN_THRESHOLD,
        ):
            success = await self.extract_facts(user_id=user_id, session_id=session_id)
            if success:
                await self.store.reset_memory_extraction_counter(user_id=user_id, session_id=session_id, module=self.module_name)  # 重置计数器

        recent_msgs = await self.store.get_recent_messages(  # 检查是否触发画像更新
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            limit=80,
        )
        assistant_turns = sum(1 for msg in recent_msgs if getattr(msg, "role", "") == "assistant")
        if assistant_turns and assistant_turns % PROFILE_GATE_EVERY_N_ASSISTANT_TURNS == 0:  # 每N轮触发画像构建
            success, updated = await self.profile_builder.build_profile(user_id=user_id, session_id=session_id)
            if success and updated:
                await self.store.reset_profile_update_counter(user_id=user_id, session_id=session_id, module=self.module_name)

        await self.store.summarize_and_compress(  # 压缩旧消息
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            threshold=MEMORY_COMPRESSION_TOKEN_THRESHOLD,
        )

    async def persist_tool_messages(  # 持久化工具调用消息
        self,
        *,
        user_id: int,
        session_id: str,
        tool_call_records: list[ToolCallDetail],
    ) -> None:
        if not tool_call_records:
            return
        for record in tool_call_records:
            try:
                tool_name = str(record.get("tool", "unknown"))
                status = str(record.get("status", "success"))
                args = record.get("args", {})
                result = str(record.get("result", ""))
                content = (
                    f"工具调用: {tool_name}\n"
                    f"状态: {status}\n"
                    f"参数: {args}\n"
                    f"结果: {result[:2000]}"
                )
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
