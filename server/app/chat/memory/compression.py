"""Chat 会话压缩 — 将旧消息压缩为时序摘要块。

触发条件：token 数 ≥ min_tokens 或消息数 ≥ min_messages（满足其一即可）。
压缩策略：保留最近 keep_recent 条原始消息，其余通过 LLM 生成 Markdown 摘要。
LLM 失败时降级为 extract_fallback_summary_markdown（取前 N 行拼接）。
压缩后保留完整原始历史，仅记录摘要覆盖边界并重置计数器。
"""

from __future__ import annotations

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.chat.memory.types import extract_content_text
from app.infra.llm import HumanMessage, LLM, SystemMessage
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatSession, ChatSessionSummaryBlock
from app.infra.prompts import prompts

logger = get_logger(__name__)


# ChatSessionCompressor：将会话旧消息压缩为时序摘要块，保留最近消息与原始历史
class ChatSessionCompressor:
    """会话压缩器 — 将旧的原始消息压缩为时序摘要块。

    压缩策略：
      1. 判断是否需要压缩（token 数 ≥ 阈值 或 消息数 ≥ 阈值）
      2. 保留最近 keep_recent 条消息，其余作为压缩目标
      3. 通过 LLM 生成 Markdown 格式的会话摘要
      4. LLM 失败时降级为行拼接的简易摘要
      5. 将摘要保存为 ChatSessionSummaryBlock 记录
      6. 保留原始消息，以摘要块 end_message_id 标记上下文覆盖边界
      7. 重置 summary_token_count 计数器
    """

    # 初始化压缩参数（保留条数/消息阈值/Token 阈值）与 LLM
    def __init__(
        self,
        *,
        keep_recent: int = 8,
        min_messages: int = 14,
        min_tokens: int = 3500,
    ) -> None:
        self.keep_recent = keep_recent
        self.min_messages = min_messages
        self.min_tokens = min_tokens
        self.llm = LLM(temperature=0.7)

    # 条件压缩入口：根据阈值或 force 决定是否压缩
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
        logger.info(
            "[ChatSessionCompressor] 开始检查压缩条件: user_id=%s session_id=%s force=%s reason=%s",
            user_id, session_id, force, reason,
        )
        # 强制模式直接压缩，否则检查是否达到压缩条件
        should_compress = force or await self._should_compress(
            db=db,
            user_id=user_id,
            session_id=session_id,
        )
        # 不满足阈值则跳过
        if not should_compress:
            logger.info("[ChatSessionCompressor] 不满足压缩条件，跳过: user_id=%s session_id=%s", user_id, session_id)
            return None
        logger.info("[ChatSessionCompressor] 满足压缩条件，开始压缩: user_id=%s session_id=%s", user_id, session_id)
        # 执行实际压缩
        return await self._compress(
            db=db,
            user_id=user_id,
            session_id=session_id,
            reason=reason,
        )

    # 暴露阈值判断给外部查询
    async def needs_compression(self, *, db: AsyncSession, user_id: int, session_id: str) -> bool:
        """返回当前会话是否满足压缩阈值。"""
        return await self._should_compress(db=db, user_id=user_id, session_id=session_id)

    # 判断是否需要压缩：token 或消息数任一达到阈值即触发
    async def _should_compress(self, *, db: AsyncSession, user_id: int, session_id: str) -> bool:
        """判断是否需要压缩 — 满足任一条件即触发。

        条件1: summary_token_count ≥ min_tokens（累积 token 达到阈值）
        条件2: 消息条数 ≥ min_messages（消息数量达到阈值）
        """
        # 读取当前会话的累积 token 数
        chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
        token_count = chat_session.summary_token_count if chat_session else 0
        logger.info(
            "[ChatSessionCompressor._should_compress] user_id=%s session_id=%s token_count=%s min_tokens=%s",
            user_id, session_id, token_count, self.min_tokens,
        )
        # 条件1：累积 token 达到阈值即触发
        if token_count >= self.min_tokens:
            logger.info("[ChatSessionCompressor._should_compress] token_count >= min_tokens, 触发压缩")
            return True

        # 查询最近一个摘要块的覆盖边界
        latest_block = (
            await db.exec(
                select(ChatSessionSummaryBlock)
                .join(ChatSession, ChatSession.id == ChatSessionSummaryBlock.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                )
                .order_by(ChatSessionSummaryBlock.block_index.desc())
                .limit(1)
            )
        ).first()
        last_summarized_id = int(latest_block.end_message_id or 0) if latest_block else 0

        # 仅统计上一个摘要边界之后的新消息，避免保留历史后反复压缩同一批记录。
        count_result = (
            await db.exec(
                select(func.count())
                .select_from(ChatMessage)
                .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.id > last_summarized_id,
                )
            )
        ).one()
        logger.info(
            "[ChatSessionCompressor._should_compress] user_id=%s session_id=%s message_count=%s min_messages=%s",
            user_id, session_id, count_result, self.min_messages,
        )
        # 条件2：新消息数达到阈值即触发
        return count_result >= self.min_messages

    # 执行实际压缩：提取旧消息 → 生成摘要 → 保存摘要块 → 重置计数器
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
          6. 保留原始消息，供历史回放和审计
          7. 重置 token 计数器
        """
        latest_block = (
            await db.exec(
                select(ChatSessionSummaryBlock)
                .join(ChatSession, ChatSession.id == ChatSessionSummaryBlock.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                )
                .order_by(ChatSessionSummaryBlock.block_index.desc())
                .limit(1)
            )
        ).first()
        last_summarized_id = int(latest_block.end_message_id or 0) if latest_block else 0
        filters = [
            ChatSession.user_id == user_id,
            ChatMessage.session_id == session_id,
            ChatMessage.role.in_(["user", "assistant"]),
            ChatMessage.id > last_summarized_id,
        ]
        messages = list(
            (
                await db.exec(
                    select(ChatMessage)
                    .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                    .where(*filters)
                    .order_by(ChatMessage.id.asc())
                )
            ).all()
        )
        dialogue = [msg for msg in messages if extract_content_text(msg.content)]
        logger.info(
            "[ChatSessionCompressor._compress] user_id=%s session_id=%s total_messages=%s dialogue_count=%s target_count=%s keep_recent=%s",
            user_id, session_id, len(messages), len(dialogue), max(0, len(dialogue) - self.keep_recent), self.keep_recent,
        )
        # 对话数不超过保留数则无需压缩
        if len(dialogue) <= self.keep_recent:
            logger.info("[ChatSessionCompressor._compress] dialogue_count <= keep_recent, 无需压缩")
            return None

        # 分离：目标消息 = 需要压缩的旧消息，保留消息 = 最近 keep_recent 条
        target = dialogue[:-self.keep_recent] if self.keep_recent > 0 else dialogue
        if not target:
            logger.info("[ChatSessionCompressor._compress] target为空, 无需压缩")
            return None

        # 将目标消息格式化为带时间戳的文本
        chat_text = "\n".join(
            f"[{msg.created_at:%m-%d %H:%M}] {msg.role}: {extract_content_text(msg.content)[:500]}"
            for msg in target
        )

        prompt = prompts.get("chat_memory").render("compression", dialogue_text=chat_text[:5000])
        resp = await self.llm.text(
            [
                SystemMessage(content=prompt),
                HumanMessage(content="请根据以上对话记录输出会话摘要 Markdown。"),
            ],
        )
        summary_markdown = str(resp.content or "").strip()
        if not summary_markdown:
            raise RuntimeError("LLM 生成的会话摘要为空")

        logger.info(
            "[ChatSessionCompressor._compress] LLM生成摘要成功: user_id=%s session_id=%s summary_length=%s",
            user_id, session_id, len(summary_markdown),
        )

        # 计算下一个摘要块索引
        next_block_index = (latest_block.block_index if latest_block else 0) + 1

        # 创建摘要块记录（标记覆盖的消息边界）
        summary_block = ChatSessionSummaryBlock(
            session_id=session_id,
            block_index=next_block_index,
            summary_markdown=summary_markdown,
            start_message_id=target[0].id,
            end_message_id=target[-1].id,
        )
        db.add(summary_block)
        await db.flush()
        logger.info(
            "[ChatSessionCompressor._compress] 摘要块创建成功: user_id=%s session_id=%s block_index=%s summarized_count=%s",
            user_id, session_id, next_block_index, len(target),
        )

        logger.info(
            "[ChatSessionCompressor._compress] 保留原始消息并更新摘要边界: user_id=%s session_id=%s end_message_id=%s",
            user_id, session_id, target[-1].id,
        )

        # 重置 token 计数器 — 压缩后重新开始累积
        chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
        if chat_session:
            chat_session.summary_token_count = 0
            db.add(chat_session)
            logger.info(
                "[ChatSessionCompressor._compress] 重置token计数器: user_id=%s session_id=%s",
                user_id, session_id,
            )
        # 返回新建的摘要块
        return summary_block
