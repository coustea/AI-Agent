"""教学图解生成器 — 基于学生问题和回答，让 LLM 生成结构化图解 JSON。"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.chat.schemas import EvidenceSet, TeachingDiagram, TutorTurnContext
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts

logger = get_logger(__name__)


class TeachingDiagramGenerator:
    """教学图解生成器：基于学生问题和回答，让 LLM 生成结构化图解 JSON。"""

    def __init__(self, llm=None) -> None:
        self.llm = llm or get_llm()

    async def generate(
        self,
        request: TutorTurnContext,
        answer: str,
        evidence_set: EvidenceSet,
    ) -> dict:
        attachment_context = "\n".join(
            item.summary for item in evidence_set.items if item.evidence_type == "attachment"
        ).strip()
        context_text = attachment_context or "无额外上下文。"
        prompt = (
            f"学生问题：\n{request.user_input}\n\n"
            f"最终回答：\n{answer}\n\n"
            f"上下文：\n{context_text}\n\n"
            "请生成一张能辅助学生理解答案的教学图解 JSON。"
        )
        diagram = await self.llm.ainvoke_json(
            TeachingDiagram,
            [
                SystemMessage(content=prompts.get("chat").get("teaching_diagram")),
                HumanMessage(content=prompt),
            ],
            temperature=0.1,
        )
        return diagram.model_dump(mode="json")
