"""
记忆压缩服务。

从 MemoryService 拆分：短期→长期记忆压缩（LLM 摘要）。
"""

import os

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.infra.database import engine
from app.infra.logging import get_logger
from app.memory.short_term import short_term_service
from app.memory.long_term import long_term_service

logger = get_logger(__name__)


class CompressionService:
    """短期→长期记忆压缩：当短期消息达到阈值时，调用 LLM 总结并清理。"""

    def __init__(self) -> None:
        self.engine = engine

    async def summarize_and_compress(
        self,
        user_id: int,
        session_id: str,
        module: str,
        threshold: int = 30,
        keep_recent: int = 10,
    ) -> None:
        """如果短期消息达到阈值，调用 LLM 总结为长期记忆并清理旧消息。"""
        if not await short_term_service.should_summarize(user_id, session_id, module, threshold):
            return

        recent_msgs = await short_term_service.get_recent_messages(user_id, session_id, module)
        if not recent_msgs:
            return

        chat_text = "\n".join(
            f"[{m.created_at.strftime('%m-%d %H:%M')}] {m.role}: {m.content}"
            for m in recent_msgs[:-keep_recent]
        )
        if not chat_text.strip():
            return

        summarize_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个记忆压缩引擎。请将以下对话记录提炼为若干条关键知识点和结论。\n"
                "每条用一行表示，格式：`类别|内容`，类别包括 knowledge/error/behavior/interest/question/answer。\n"
                "只输出有价值的条目，忽略闲聊。"
            )),
            ("human", "{chat_text}"),
        ])

        try:
            llm = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL"),
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_API_BASE"),
                temperature=0.1,
            )
            prompt = summarize_prompt.invoke({"chat_text": chat_text})
            result = await llm.ainvoke(prompt)

            summarized_ids = [m.id for m in recent_msgs[:-keep_recent]]
            await long_term_service.save_long_term_memory(
                user_id=user_id,
                session_id=session_id,
                content=result.content,
                memory_type="summary",
                source=module,
                source_message_count=len(summarized_ids),
            )

            deleted = await short_term_service.delete_old_messages(user_id, session_id, module, keep_recent)
            logger.info(f"[Compression] 压缩完成: user={user_id}, summarized={len(summarized_ids)}, deleted={deleted}")
        except Exception as e:
            logger.error(f"[Compression] 短期→长期压缩失败: {e}")


compression_service = CompressionService()
