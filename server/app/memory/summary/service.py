"""概要服务层。

模块职责：
- 概要业务逻辑
- 会话压缩
"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.memory.message.store import MessageStore
from app.memory.message.types import DIALOGUE_ROLES
from app.memory.session.store import SessionStore
from app.memory.summary.store import SummaryStore
from app.memory.summary.types import SUMMARY_TOKEN_THRESHOLD, SummaryLLMOutput, make_default_summary_json, render_summary_markdown

logger = get_logger(__name__)


class SummaryService:
    """概要服务。"""

    def __init__(self, module: str = "mentor") -> None:
        self.module = module
        self.summary_store = SummaryStore()
        self.message_store = MessageStore()
        self.session_store = SessionStore()
        self.llm = get_llm()

    async def should_create(self, user_id: int, session_id: str) -> bool:
        """判断是否需要生成概要。"""
        count = await self.session_store.get_token_count(session_id)
        return count >= SUMMARY_TOKEN_THRESHOLD

    async def compress(
        self,
        user_id: int,
        session_id: str,
        keep_recent: int = 10,
    ) -> bool:
        """生成概要并压缩旧消息。优先调用 LLM 生成结构化概要，失败时降级为文本拼接。"""
        # 获取对话消息
        messages = await self.message_store.get_recent(
            user_id, session_id, self.module, limit=50
        )
        dialogue = [
            m for m in messages
            if m.role in DIALOGUE_ROLES and m.content.strip()
        ]
        if not dialogue:
            return False

        # 构建对话文本
        chat_text = "\n".join(
            f"[{m.created_at.strftime('%m-%d %H:%M')}] {m.role}: {m.content[:500]}"
            for m in dialogue
        )

        # 优先 LLM 生成结构化概要
        summary_json = None
        try:
            prompt = (
                "请分析以下学习对话记录，提取结构化概要信息。\n\n"
                "要求：\n"
                "- current_learning_task: 学生当前正在学习的主题或任务\n"
                "- original_user_questions: 学生提出的原始问题列表\n"
                "- explained_content: 教师/系统已解释的知识点列表\n"
                "- current_understanding: 学生当前对知识点的理解状态\n"
                "- current_confusions: 学生当前仍存在的困惑或误解\n"
                "- teaching_methods_used: 对话中使用过的教学方法或策略\n"
                "- conversation_position: 对话当前进度\n"
                "- next_action: 建议的下一步教学行动\n"
                "- references: 对话中提到的参考资料或资源\n\n"
                f"对话记录：\n{chat_text[:4000]}"
            )
            resp = await self.llm.ainvoke_json(
                SummaryLLMOutput,
                prompt,
                function_name="generate_session_summary",
                function_description="分析学习对话记录，提取结构化概要信息。",
                temperature=0.1,
            )
            summary_json = resp.model_dump()
            logger.info("[SummaryService] LLM 结构化概要生成成功")
        except Exception as e:
            logger.warning("[SummaryService] LLM 概要生成失败，降级为文本拼接: %s", e)

        # 降级：文本拼接概要
        if summary_json is None:
            summary_json = make_default_summary_json()
            summary_json["current_learning_task"] = "对话概要（LLM 不可用，降级为文本拼接）"
            summary_json["original_user_questions"] = [chat_text[:500]]

        # 渲染 Markdown
        summary_markdown = render_summary_markdown(summary_json)

        # 获取当前话题和目标
        current_topic = summary_json.get("current_learning_task", "")
        current_goal = summary_json.get("next_action", "")

        await self.summary_store.create(
            user_id=user_id,
            session_id=session_id,
            module=self.module,
            summary_markdown=summary_markdown,
            summary_json=summary_json,
            summarized_message_count=len(dialogue),
            current_topic=current_topic[:200] if current_topic else None,
            current_goal=current_goal[:200] if current_goal else None,
        )

        # 清理旧消息
        if keep_recent > 0:
            await self.message_store.delete_old(
                user_id, session_id, self.module, keep_recent
            )

        # 重置计数
        await self.session_store.reset_token_count(session_id)
        return True

    async def list(
        self,
        user_id: int,
        session_id: str,
        limit: int = 3,
    ) -> list:
        """获取概要列表。"""
        return await self.summary_store.list(user_id, session_id, self.module, limit)

    async def get_latest(self, user_id: int, session_id: str):
        """获取最新概要。"""
        return await self.summary_store.get_latest(user_id, session_id, self.module)