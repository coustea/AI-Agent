"""Chat 会话压缩 — 将旧消息压缩为时序摘要块。

触发条件：token 数 ≥ min_tokens 或消息数 ≥ min_messages（满足其一即可）。
压缩策略：保留最近 keep_recent 条原始消息，其余通过 LLM 生成 Markdown 摘要。
LLM 失败时降级为 extract_fallback_summary_markdown（取前 N 行拼接）。
压缩后物理删除已摘要的旧消息，重置 summary_token_count 计数器。
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.prompts import prompts
from app.chat.memory.types import DIALOGUE_ROLES, extract_fallback_summary_markdown
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatSession, ChatSessionSummaryBlock

logger = get_logger(__name__)


class ChatSessionCompressor:
    """会话压缩器 — 将旧的原始消息压缩为时序摘要块。

    压缩策略：
      1. 判断是否需要压缩（token 数 ≥ 阈值 或 消息数 ≥ 阈值）
      2. 保留最近 keep_recent 条消息，其余作为压缩目标
      3. 通过 LLM 生成 Markdown 格式的会话摘要
      4. LLM 失败时降级为行拼接的简易摘要
      5. 将摘要保存为 ChatSessionSummaryBlock 记录
      6. 物理删除已被摘要的旧消息
      7. 重置 summary_token_count 计数器
    """

    def __init__(
        self,
        *,
        module: str = "mentor",
        keep_recent: int = 8,
        min_messages: int = 14,
        min_tokens: int = 3500,
    ) -> None:
        # 模块名 — 用于隔离不同对话模块的消息（如 mentor、quiz 等）
        self.module = module
        # 压缩后保留的最近消息条数（这些消息不会被删除）
        self.keep_recent = keep_recent
        # 触发压缩的消息数阈值（满足即压缩）
        self.min_messages = min_messages
        # 触发压缩的 token 数阈值（满足即压缩）
        self.min_tokens = min_tokens
        # LLM 实例 — 用于生成对话摘要
        self.llm = get_llm()

    async def maybe_compress(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        force: bool = False,
        reason: str = "post_turn",
    ):
        """条件压缩 — 根据阈值判断是否需要压缩，或强制压缩。

        Args:
            db: 数据库会话
            user_id: 用户ID
            session_id: 会话ID
            force: 是否强制压缩（跳过阈值检查）
            reason: 压缩原因（用于日志和追踪）

        Returns:
            压缩后的 ChatSessionSummaryBlock，或 None（无需压缩）
        """
        # 强制模式直接压缩，否则检查是否达到压缩条件
        should_compress = force or await self._should_compress(
            db=db,
            user_id=user_id,
            session_id=session_id,
        )
        if not should_compress:
            return None
        return await self._compress(
            db=db,
            user_id=user_id,
            session_id=session_id,
            reason=reason,
        )

    async def _should_compress(self, *, db: AsyncSession, user_id: int, session_id: str) -> bool:
        """判断是否需要压缩 — 满足任一条件即触发。

        条件1: summary_token_count ≥ min_tokens（累积 token 达到阈值）
        条件2: 消息条数 ≥ min_messages（消息数量达到阈值）
        """
        chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
        token_count = chat_session.summary_token_count if chat_session else 0
        if token_count >= self.min_tokens:
            return True

        # 统计当前模块的消息条数
        count_result = (
            await db.exec(
                select(func.count()).where(
                    ChatMessage.user_id == user_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.module == self.module,
                )
            )
        ).one()
        return count_result >= self.min_messages

    async def _compress(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        reason: str = "manual",
    ):
        """执行实际压缩 — 提取旧消息、生成摘要、保存并清理。

        压缩流程：
          1. 查询所有消息并过滤为有效对话（user/assistant 角色、非空内容）
          2. 分离出需要压缩的目标消息和需要保留的最近消息
          3. 将目标消息格式化为带时间戳的文本
          4. 调用 LLM 生成摘要（失败时降级为行拼接）
          5. 创建新的 summary_block 记录
          6. 物理删除已被摘要的旧消息
          7. 重置 token 计数器
        """
        # 构建消息查询条件 — 限定用户、会话、模块
        filters = [
            ChatMessage.user_id == user_id,
            ChatMessage.session_id == session_id,
            ChatMessage.module == self.module,
        ]
        # 按时间升序获取所有消息
        messages = list((await db.exec(select(ChatMessage).where(*filters).order_by(ChatMessage.created_at.asc()))).all())
        # 过滤：仅保留 user/assistant 角色且内容非空的消息
        dialogue = [msg for msg in messages if msg.role in DIALOGUE_ROLES and str(msg.content or "").strip()]
        if len(dialogue) <= self.keep_recent:
            return None

        # 分离：目标消息 = 需要压缩的旧消息，保留消息 = 最近 keep_recent 条
        target = dialogue[:-self.keep_recent] if self.keep_recent > 0 else dialogue
        if not target:
            return None

        # 格式化为带时间戳的对话文本，每条消息截取前500字符
        chat_text = "\n".join(
            f"[{msg.created_at:%m-%d %H:%M}] {msg.role}: {msg.content[:500]}"
            for msg in target
        )

        # 尝试通过 LLM 生成摘要（截取前5000字符作为输入）
        summary_markdown = None
        try:
            prompt = prompts.get("chat_memory").render("compression", dialogue_text=chat_text[:5000])

            resp = await self.llm.ainvoke(
                [
                    SystemMessage(content=prompt),
                    HumanMessage(content="请根据以上对话记录输出会话摘要 Markdown。"),
                ],
                temperature=0.1,
            )
            summary_markdown = str(resp.content or "").strip()
        except Exception as exc:
            logger.warning("[ChatMemoryCompression] LLM compression failed: %s", exc)

        # LLM 失败或返回空结果时，降级为简易行拼接摘要
        if not summary_markdown or not summary_markdown.strip():
            summary_markdown = extract_fallback_summary_markdown(chat_text)

        # 查找最新的摘要块，确定下一个 block_index（用于时序编号）
        latest_block = (
            await db.exec(
                select(ChatSessionSummaryBlock)
                .where(
                    ChatSessionSummaryBlock.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                    ChatSessionSummaryBlock.module == self.module,
                )
                .order_by(ChatSessionSummaryBlock.block_index.desc())
                .limit(1)
            )
        ).first()
        next_block_index = (latest_block.block_index if latest_block else 0) + 1

        # 创建新的摘要块记录 — 记录压缩的起止消息ID、时间范围和消息数量
        summary_block = ChatSessionSummaryBlock(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            block_index=next_block_index,
            summary_markdown=summary_markdown,
            start_message_id=target[0].id,
            end_message_id=target[-1].id,
            start_at=target[0].created_at,
            end_at=target[-1].created_at,
            summarized_message_count=len(target),
            topics=[],
            keywords=[],
        )
        db.add(summary_block)
        await db.flush()

        # 物理删除已被摘要覆盖的旧消息 — 只删除 ID < first_kept 的消息
        first_kept = dialogue[-self.keep_recent].id if self.keep_recent > 0 else None
        if first_kept:
            stale_messages = list(
                (
                    await db.exec(
                        select(ChatMessage).where(
                            ChatMessage.user_id == user_id,
                            ChatMessage.session_id == session_id,
                            ChatMessage.module == self.module,
                            ChatMessage.id < first_kept,
                        )
                    )
                ).all()
            )
            for msg in stale_messages:
                await db.delete(msg)

        # 重置 token 计数器 — 压缩后重新开始累积
        chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
        if chat_session:
            chat_session.summary_token_count = 0
            db.add(chat_session)
        return summary_block
