"""记忆系统唯一公共入口。"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.memory.compression import SessionCompressor
from app.memory.context import MemoryContextBuilder
from app.memory.long_term import LongTermMemoryExtractor
from app.memory.profile import ProfileBuilder
from app.memory.store import MemoryStore
from app.memory.workflow import MemoryWorkflow

logger = get_logger(__name__)


class MemoryService:
    """记忆系统门面：前端/API/Agent 只依赖这个类。"""

    def __init__(self, *, module: str = "mentor") -> None:
        self.module = module
        self.store = MemoryStore()
        self.profile = ProfileBuilder(module=module, store=self.store)
        self.compressor = SessionCompressor(module=module, store=self.store)
        self.long_term = LongTermMemoryExtractor(module=module, store=self.store)
        self.context = MemoryContextBuilder(module=module, store=self.store)
        self.workflow = MemoryWorkflow(
            module=module,
            store=self.store,
            compressor=self.compressor,
            long_term=self.long_term,
            profile=self.profile,
        )
        self.llm = get_llm()

    async def create_session(self, *, user_id: int, title: str = "新对话"):
        return await self.store.create_session(user_id=user_id, module=self.module, title=title)

    async def get_session(self, *, session_id: str):
        return await self.store.get_session(session_id)

    async def list_sessions(self, *, user_id: int, limit: int = 20):
        return await self.store.list_sessions(user_id=user_id, module=self.module, limit=limit)

    async def archive_session(self, *, user_id: int, session_id: str) -> bool:
        return await self.store.archive_session(user_id=user_id, session_id=session_id)

    async def update_session_title(self, *, user_id: int, session_id: str, title: str) -> bool:
        return await self.store.update_session_title(user_id=user_id, session_id=session_id, title=title)

    async def generate_session_title(self, *, user_id: int, session_id: str, first_message: str) -> str | None:
        if not (first_message or "").strip():
            return None
        prompt = f"""请根据用户的第一条消息生成一个简短的会话标题（10字以内）。

用户消息：{first_message[:200]}

只输出标题，不要解释。"""
        try:
            response = await self.llm.ainvoke(
                [SystemMessage(content="你是一个会话标题生成助手。"), HumanMessage(content=prompt)],
                temperature=0.3,
                max_tokens=20,
            )
            title = str(response.content or "").strip().strip("`\"'""''")
            if not title:
                return None
            title = title[:15]
            await self.update_session_title(user_id=user_id, session_id=session_id, title=title)
            return title
        except Exception as exc:
            logger.warning("[MemoryService] 生成会话标题失败 user=%s session=%s err=%s", user_id, session_id, exc)
            return None

    async def save_message(
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: list[dict] | None = None,
        tool_calls: list[dict] | None = None,
        knowledge_graph: dict | None = None,
    ) -> int:
        return await self.store.save_message(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
            knowledge_graph=knowledge_graph,
        )

    async def list_messages(
        self,
        *,
        user_id: int,
        session_id: str,
        limit: int = 50,
        only_unexpired: bool = True,
    ):
        return await self.store.list_messages(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            limit=limit,
            only_unexpired=only_unexpired,
        )

    async def delete_short_term_messages(self, *, user_id: int, session_id: str) -> int:
        return await self.store.delete_session_messages(user_id=user_id, session_id=session_id, module=self.module)

    async def reset_session_counters(self, *, user_id: int, session_id: str) -> None:
        await self.store.reset_session_token_count(session_id)

    async def get_session_summaries(self, *, user_id: int, session_id: str, limit: int = 3):
        return await self.store.list_summaries(user_id=user_id, session_id=session_id, module=self.module, limit=limit)

    async def compress_session(self, *, user_id: int, session_id: str, keep_recent: int = 10) -> bool:
        return await self.compressor.maybe_compress(
            user_id=user_id,
            session_id=session_id,
            keep_recent=keep_recent,
            force=True,
            reason="manual",
        ) is not None

    async def get_profile(self, *, user_id: int):
        return await self.store.get_profile(user_id=user_id, module=self.module)

    async def get_or_create_profile(self, *, user_id: int):
        return await self.store.get_or_create_profile(user_id=user_id, module=self.module)

    async def list_profile_history(self, *, user_id: int, limit: int = 20):
        return await self.store.list_profile_history(user_id=user_id, module=self.module, limit=limit)

    async def get_onboarding(self, *, user_id: int) -> dict:
        return await self.profile.get_onboarding(user_id)

    async def upsert_profile(self, *, user_id: int, session_id: str | None = None, onboarding: dict | None = None, reason: str = "manual"):
        return await self.profile.upsert(user_id=user_id, session_id=session_id, onboarding=onboarding, reason=reason)

    async def get_long_term_memory(self, *, user_id: int):
        return await self.store.get_long_term_memory(user_id=user_id, module=self.module)

    async def get_or_create_long_term_memory(self, *, user_id: int):
        return await self.store.get_or_create_long_term_memory(user_id=user_id, module=self.module)

    async def update_long_term_memory(self, *, user_id: int, session_id: str, user_message: str, assistant_reply: str) -> bool:
        return await self.long_term.maybe_update(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
        )

    async def build_profile_context(self, user_id: int) -> str:
        return await self.context.build_profile_context(user_id)

    async def build_memory_context(self, user_id: int) -> str:
        return await self.context.build_memory_context(user_id)

    def build_file_context(self, image_urls: list[str], file_urls: list[str]) -> str:
        return self.context.build_file_context(image_urls, file_urls)

    async def build_recent_chat_context(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
    ):
        return await self.context.build_recent_chat_context(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            image_urls=image_urls,
            file_urls=file_urls,
        )

    async def build_context_preview(self, *, user_id: int, session_id: str, recent_limit: int = 10) -> str:
        return await self.context.build_context_preview(user_id=user_id, session_id=session_id, recent_limit=recent_limit)

    async def build_tutor_context(self, *, user_id: int, session_id: str, recent_limit: int = 10) -> str:
        return await self.context.build_tutor_context(user_id=user_id, session_id=session_id, recent_limit=recent_limit)

    async def after_turn(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        enable_long_term_memory: bool = True,
    ) -> None:
        await self.workflow.after_turn(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
            enable_long_term_memory=enable_long_term_memory,
        )
