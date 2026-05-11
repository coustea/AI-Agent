"""记忆层公共 API — 外部模块唯一入口。

模块职责：
- 聚合所有领域服务
- 提供统一的 MemoryLayer 接口
- 保持向后兼容

设计原则：
- 外部模块只应依赖 MemoryLayer，不应直接导入内部领域模块
- 一个用户一个 module 下只有一条长期记忆
- 一个用户一个 module 下只有一条当前画像
- 会话概要不写入长期记忆
"""

from __future__ import annotations

from typing import Any

from app.memory.core.types import ModuleName
from app.memory.context.service import ContextService
from app.memory.memory.service import LongTermMemoryService
from app.memory.memory.store import LongTermMemoryStore
from app.memory.message.service import MessageService
from app.memory.message.store import MessageStore
from app.memory.profile.service import ProfileService
from app.memory.profile.store import ProfileStore
from app.memory.session.service import SessionService
from app.memory.session.store import SessionStore
from app.memory.summary.service import SummaryService
from app.memory.summary.store import SummaryStore


class MemoryLayer:
    """记忆层公共 API — 外部模块应只依赖此类。"""

    def __init__(self, *, module: str = ModuleName.MENTOR) -> None:
        self.module = module
        self.session_store = SessionStore()
        self.message_store = MessageStore()
        self.summary_store = SummaryStore()
        self.profile_store = ProfileStore()
        self.memory_store = LongTermMemoryStore()

        self.session_service = SessionService(module)
        self.message_service = MessageService(module)
        self.summary_service = SummaryService(module)
        self.profile_service = ProfileService(module)
        self.memory_service = LongTermMemoryService(module)
        self.context_service = ContextService(
            module,
            message_store=self.message_store,
            memory_store=self.memory_store,
            profile_store=self.profile_store,
            summary_store=self.summary_store,
        )

    # ------------------------------------------------------------------
    # 会话管理
    # ------------------------------------------------------------------

    async def create_session(self, *, user_id: int, title: str = "新对话"):
        """创建会话。"""
        return await self.session_service.create(user_id=user_id, title=title)

    async def get_session(self, *, session_id: str):
        """获取会话。"""
        return await self.session_store.get(session_id)

    async def list_sessions(self, *, user_id: int, limit: int = 20):
        """获取会话列表。"""
        return await self.session_service.list(user_id=user_id, limit=limit)

    async def archive_session(self, *, user_id: int, session_id: str) -> bool:
        """归档会话。"""
        return await self.session_service.archive(user_id=user_id, session_id=session_id)

    async def update_session_title(self, *, user_id: int, session_id: str, title: str) -> bool:
        """更新会话标题。"""
        return await self.session_store.update_title(session_id=session_id, user_id=user_id, title=title)

    # ------------------------------------------------------------------
    # 消息管理
    # ------------------------------------------------------------------

    async def save_message(
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        diagram: dict[str, Any] | None = None,
    ):
        """保存消息。"""
        return await self.message_service.save(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
            diagram=diagram,
        )

    async def list_messages(
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int = 50,
    ):
        """获取消息列表。"""
        return await self.message_service.list(
            user_id=user_id,
            session_id=session_id,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # 会话概要
    # ------------------------------------------------------------------

    async def get_session_summaries(
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int = 3,
    ):
        """获取会话概要列表。"""
        return await self.summary_store.list(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            limit=limit,
        )

    async def compress_session(
        self,
        *,
        user_id: int,
        session_id: str,
        keep_recent: int = 10,
    ) -> bool:
        """压缩会话。"""
        return await self.summary_service.compress(
            user_id=user_id,
            session_id=session_id,
            keep_recent=keep_recent,
        )

    # ------------------------------------------------------------------
    # 用户画像
    # ------------------------------------------------------------------

    async def get_profile(self, *, user_id: int):
        """获取用户画像。"""
        return await self.profile_service.get(user_id)

    async def get_or_create_profile(self, *, user_id: int):
        """获取或创建用户画像。"""
        return await self.profile_service.get_or_create(user_id)

    async def list_profile_history(self, *, user_id: int, limit: int = 20):
        """获取画像历史。"""
        return await self.profile_service.get_history(user_id, limit)

    async def build_profile(self, *, user_id: int, session_id: str | None = None) -> bool:
        """构建用户画像。"""
        success, _ = await self.profile_service.build(user_id=user_id, session_id=session_id)
        return success

    async def get_onboarding(self, *, user_id: int) -> dict[str, Any]:
        """获取首次登录状态。"""
        return await self.profile_service.get_onboarding(user_id)

    async def update_onboarding(
        self,
        *,
        user_id: int,
        student_profile: dict[str, Any],
    ):
        """更新首次登录数据。"""
        return await self.profile_service.update_onboarding(
            user_id=user_id,
            student_profile=student_profile,
        )

    # ------------------------------------------------------------------
    # 长期记忆
    # ------------------------------------------------------------------

    async def get_long_term_memory(self, *, user_id: int):
        """获取长期记忆。"""
        return await self.memory_service.get(user_id)

    async def get_or_create_long_term_memory(self, *, user_id: int):
        """获取或创建长期记忆。"""
        return await self.memory_service.get_or_create(user_id)

    async def update_long_term_memory(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
    ) -> bool:
        """从对话更新长期记忆。"""
        return await self.memory_service.update_from_dialogue(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
        )

    # ------------------------------------------------------------------
    # 上下文构建
    # ------------------------------------------------------------------

    async def build_context_preview(
        self,
        *,
        user_id: int,
        session_id: str,
        recent_limit: int = 10,
    ) -> str:
        """构建上下文预览。"""
        return await self.context_service.build_context_preview(
            user_id=user_id,
            session_id=session_id,
            recent_limit=recent_limit,
        )

    async def build_tutor_context(
        self,
        *,
        user_id: int,
        session_id: str,
        recent_limit: int = 10,
    ) -> str:
        """构建辅导上下文。"""
        return await self.context_service.build_tutor_context(
            user_id=user_id,
            session_id=session_id,
            recent_limit=recent_limit,
        )

    # ------------------------------------------------------------------
    # 后处理流水线
    # ------------------------------------------------------------------

    async def post_turn_pipeline(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        enable_long_term_memory: bool = True,
    ) -> None:
        """对话后处理流水线。"""
        from app.memory.pipeline.service import PipelineService

        pipeline = PipelineService(module=self.module)
        # 使用当前 layer 的 stores
        pipeline.session_store = self.session_store
        pipeline.message_store = self.message_store
        pipeline.memory_service = self.memory_service
        pipeline.profile_service = self.profile_service
        pipeline.summary_service = self.summary_service

        await pipeline.run(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
            enable_long_term_memory=enable_long_term_memory,
        )
