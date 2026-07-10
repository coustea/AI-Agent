"""Chat 长期记忆提取 — 跨会话稳定学习特征的增量更新。

两种触发机制：
  1. 信号触发：当轮对话中检测到稳定学习信号（正则匹配偏好/纠正/背景等关键词）
  2. 批量触发：上层按新增消息/token 阈值调度，并用冷却时间防频繁更新
更新策略：LLM 判断是否 need_update + confidence ≥ min_confidence 才写入，
  避免低质量对话污染长期记忆。记忆格式为分类 Markdown。
"""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.prompts import prompts
from app.chat.memory.types import (
    MemoryUpdateOutput,
    has_stable_signal,
    make_default_memory_markdown,
    now,
)
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import ChatLongTermMemory, ChatSession, ChatSessionSummaryBlock

logger = get_logger(__name__)


# ChatLongTermMemoryService：跨会话提取与增量更新稳定的学习特征
class ChatLongTermMemoryService:
    """长期记忆服务 — 跨会话提取和更新稳定的学习特征。

    两种触发机制：
      1. 信号触发：当轮对话中检测到稳定学习信号（正则匹配偏好/纠正/背景等关键词）
      2. 批量触发：上层按新增消息/token 阈值调度，并用冷却时间防频繁更新

    更新策略：LLM 判断是否 need_update + confidence ≥ min_confidence 才写入，
    避免低质量对话污染长期记忆。记忆格式为分类 Markdown。
    """

    # 初始化置信度阈值、冷却时间与 LLM
    def __init__(
        self,
        *,
        min_confidence: float = 0.75,
    ) -> None:
        self.min_confidence = min_confidence
        self.cooldown_seconds = 0  # 冷却时间由外层 evaluate_post_turn_jobs 控制
        self.llm = get_llm()

    # 判断当前轮次是否含值得持久化的稳定学习信号（用户或助手触发）
    def should_consider_update(
        self,
        *,
        user_message: str,
        assistant_reply: str,
    ) -> bool:
        """判断当前轮次是否包含值得持久化的稳定学习信号。

        信号检测逻辑：
          - 用户消息直接包含稳定信号（如偏好表达、纠正内容）→ 触发
          - 助手回复包含稳定信号且包含关键指示词（"以后"、"下次"等）→ 触发
          - 其他情况 → 不触发
        """
        # 用户消息中直接检测到稳定信号（如偏好、纠正、背景信息）
        if has_stable_signal(user_message):
            return True
        # 助手回复中检测到稳定信号，且包含明确的持久化指示词
        return has_stable_signal(assistant_reply) and any(
            keyword in assistant_reply for keyword in ("以后", "下次", "记住", "偏好", "纠正")
        )

    # 条件更新长期记忆：信号/周期触发 → LLM 判断 → 置信度校验 → 写入
    async def maybe_update(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        new_dialogue: str = "",
        turn_count: int = 0,
        signal_detected: bool | None = None,
    ) -> dict[str, bool]:
        """条件更新长期记忆 — 根据信号或周期触发判断是否需要更新。

        更新流程：
          1. 检测是否触发更新（信号触发 或 周期触发）
          2. 加载或创建现有的长期记忆记录
          3. 检查冷却时间（仅周期触发时生效）
          4. 获取最新的会话摘要块作为上下文
          5. 调用 LLM 判断是否需要更新并生成新记忆
          6. 校验置信度后写入数据库

        Returns:
            是否成功更新了长期记忆
        """
        # 检测信号触发和周期触发
        signal_detected = self.should_consider_update(
            user_message=user_message,
            assistant_reply=assistant_reply,
        ) if signal_detected is None else signal_detected
        periodic_trigger = bool((new_dialogue or "").strip()) and turn_count > 0
        logger.info(
            "[ChatLongTermMemoryService.maybe_update] user_id=%s session_id=%s signal_detected=%s periodic_trigger=%s",
            user_id, session_id, signal_detected, periodic_trigger,
        )
        # 两种触发方式都未满足，直接返回
        if not signal_detected and not periodic_trigger:
            logger.info("[ChatLongTermMemoryService.maybe_update] 未触发更新，跳过")
            return {"updated": False, "analyzed": False}

        # 检查是否有新对话内容可以提取 — 无内容则跳过
        if not new_dialogue or not new_dialogue.strip():
            logger.info("[ChatLongTermMemoryService.maybe_update] 无新对话内容可提取，跳过")
            return {"updated": False, "analyzed": False, "reason": "no_dialogue"}

        # 加载现有的长期记忆记录，不存在则创建空白模板
        existing = (
            await db.exec(
                select(ChatLongTermMemory).where(
                    ChatLongTermMemory.user_id == user_id,
                )
            )
        ).first()

        if existing:
            old_memory = existing
        else:
            # 首次创建：使用空白模板初始化长期记忆
            old_memory = ChatLongTermMemory(
                user_id=user_id,
                memory_markdown=make_default_memory_markdown(),
            )
            db.add(old_memory)
            await db.flush()
            logger.info("[ChatLongTermMemoryService.maybe_update] 首次创建长期记忆: user_id=%s", user_id)

        # 冷却时间检查 — 周期触发时，如果距上次更新时间不足 cooldown 则跳过
        # 信号触发不受冷却限制（用户明确表达偏好/纠正应立即响应）
        if (
            not signal_detected
            and periodic_trigger
            and old_memory.updated_at
            and (now() - old_memory.updated_at).total_seconds() < self.cooldown_seconds
        ):
            logger.info(
                "[ChatLongTermMemoryService.maybe_update] 冷却期内，跳过更新: user_id=%s cooldown=%ss",
                user_id, self.cooldown_seconds,
            )
            return {"updated": False, "analyzed": False}

        # 获取最新的会话摘要块 — 作为 LLM 判断的上下文
        latest_summary_block = (
            await db.exec(
                select(ChatSessionSummaryBlock)
                .join(ChatSession, ChatSession.id == ChatSessionSummaryBlock.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                )
                .order_by(ChatSessionSummaryBlock.created_at.desc())
                .limit(1)
            )
        ).first()

        # 构建 LLM 提示词 — 包含当前对话、会话摘要和旧记忆，让 LLM 判断是否需要更新
        prompt = prompts.get("chat_memory").render(
            "ltm_update",
            new_dialogue=(new_dialogue or "").strip()[:4000],
            user_message=user_message[:1000],
            assistant_reply=assistant_reply[:1000],
            session_summary=latest_summary_block.summary_markdown if latest_summary_block else "暂无会话概要。",
            old_memory=old_memory.memory_markdown if old_memory else "暂无长期记忆。",
        )

        # 调用 LLM 结构化输出 — 返回 need_update、memory_markdown、confidence
        resp = await self.llm.ainvoke_json(
            MemoryUpdateOutput,
            prompt,
        )
        logger.info(
            "[ChatLongTermMemoryService.maybe_update] LLM判断结果: user_id=%s need_update=%s confidence=%s",
            user_id, resp.need_update, getattr(resp, "confidence", self.min_confidence),
        )

        # 双重校验：LLM 判断不需要更新 → 跳过；置信度不足 → 跳过
        if not resp.need_update or not resp.memory_markdown:
            logger.info("[ChatLongTermMemoryService.maybe_update] LLM判断不需要更新或memory_markdown为空")
            return {"updated": False, "analyzed": True}
        if getattr(resp, "confidence", self.min_confidence) < self.min_confidence:
            logger.info(
                "[ChatLongTermMemoryService.maybe_update] 置信度不足，跳过: confidence=%s min_confidence=%s",
                getattr(resp, "confidence", self.min_confidence), self.min_confidence,
            )
            return {"updated": False, "analyzed": True}

        # 写入更新后的长期记忆并刷新更新时间
        memory = existing or old_memory
        memory.memory_markdown = resp.memory_markdown
        memory.updated_at = now()
        db.add(memory)
        logger.info(
            "[ChatLongTermMemoryService.maybe_update] 长期记忆更新成功: user_id=%s trigger=%s",
            user_id,
            "signal" if signal_detected else "periodic",
        )
        return {"updated": True, "analyzed": True}
