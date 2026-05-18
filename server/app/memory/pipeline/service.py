"""后处理流水线服务。

模块职责：
- 累加 token 计数
- 生成会话概要
- 更新长期记忆
- 构建用户画像
"""

from __future__ import annotations

from app.config import PROFILE_GATE_EVERY_N_ASSISTANT_TURNS
from app.infra.logging import get_logger
from app.memory.core.types import ModuleName
from app.memory.core.utils import estimate_token_count
from app.memory.message.store import MessageStore
from app.memory.memory.service import LongTermMemoryService
from app.memory.profile.service import ProfileService
from app.memory.session.store import SessionStore
from app.memory.summary.service import SummaryService

logger = get_logger(__name__)


class PipelineService:
    """对话后处理流水线服务。"""

    def __init__(self, module: str = ModuleName.MENTOR) -> None:
        self.module = module
        self.session_store = SessionStore()
        self.message_store = MessageStore()
        self.memory_service = LongTermMemoryService(module)
        self.profile_service = ProfileService(module)
        self.summary_service = SummaryService(module)

    async def run(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        enable_long_term_memory: bool = True,
    ) -> None:
        """运行后处理流水线。"""
        # 累加 token
        token_delta = estimate_token_count(f"{user_message}\n{assistant_reply}")
        await self.session_store.add_token_count(
            session_id=session_id,
            user_id=user_id,
            module=self.module,
            delta=token_delta,
        )

        # 生成会话概要
        if await self.summary_service.should_create(
            user_id=user_id,
            session_id=session_id,
        ):
            await self._compress_session(user_id, session_id)

        # 更新长期记忆
        if enable_long_term_memory:
            await self.memory_service.update_from_dialogue(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
                assistant_reply=assistant_reply,
            )

        # 构建画像
        await self._maybe_build_profile(user_id, session_id, user_message)

    async def _compress_session(
        self,
        user_id: int,
        session_id: str,
    ) -> bool:
        """生成会话概要并压缩旧消息。"""
        logger.info("[Pipeline] 创建会话概要")
        return await self.summary_service.compress(
            user_id=user_id,
            session_id=session_id,
            keep_recent=10,
        )

    async def _maybe_build_profile(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
    ) -> None:
        """检查并触发画像构建。"""
        msgs = await self.message_store.get_recent(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            limit=80,
        )
        assistant_turns = sum(1 for m in msgs if m.role == "assistant")
        logger.info(
            "[Pipeline] 画像检查 user=%s session=%s turns=%s gate=%s",
            user_id,
            session_id,
            assistant_turns,
            PROFILE_GATE_EVERY_N_ASSISTANT_TURNS,
        )

        should_build = False
        build_reason = ""

        if assistant_turns and assistant_turns % PROFILE_GATE_EVERY_N_ASSISTANT_TURNS == 0:
            should_build = True
            build_reason = f"定期触发（第 {assistant_turns} 轮）"
        elif self._has_profile_signal(user_message):
            should_build = True
            build_reason = "显式画像信号触发"
        elif assistant_turns == 1:
            profile = await self.profile_service.get(user_id=user_id)
            dims = (profile.profile_json or {}).get("dimensions") if profile and profile.profile_json else {}
            filled_dims = sum(
                1 for k in (dims or {})
                if ((dims or {}).get(k) or {}).get("summary") or ((dims or {}).get(k) or {}).get("evidence")
            )
            if not profile or not profile.profile_json:
                should_build = True
                build_reason = "首次对话后初始化画像"
            else:
                if filled_dims < 5:
                    should_build = True
                    build_reason = f"新用户首次对话后立即构建（当前 {filled_dims} 个维度有内容）"

        if should_build:
            logger.info(
                "[Pipeline] 触发画像构建 user=%s session=%s reason=%s",
                user_id,
                session_id,
                build_reason,
            )
            success, updated = await self.profile_service.build(user_id=user_id, session_id=session_id)
            if success and updated:
                logger.info("[Pipeline] 画像已更新 user=%s", user_id)
            elif success:
                logger.info("[Pipeline] 画像无变化 user=%s", user_id)
            else:
                logger.warning("[Pipeline] 画像构建失败 user=%s", user_id)

    def _has_profile_signal(self, message: str) -> bool:
        """识别需要立即沉淀到画像的对话信号。"""
        text = (message or "").strip()
        if not text:
            return False
        return any(
            marker in text
            for marker in (
                "以后",
                "偏好",
                "喜欢",
                "请按",
                "尽量",
                "我总是",
                "分不清",
                "不太懂",
                "正在",
                "备考",
                "准备",
                "目标",
            )
        )
