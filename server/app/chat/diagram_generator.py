"""Structured teaching-diagram generation for tutor tool calls."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.chat.schemas import TutorRequestContext
from app.chat.schemas.diagram import TeachingDiagram, validate_diagram_json
from app.infra.llm import get_llm
from app.infra.prompts import prompts


class TeachingDiagramGenerator:
    """Generate and validate one structured teaching diagram."""

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm if llm is not None else get_llm()

    async def generate(
        self,
        *,
        request: TutorRequestContext,
        focus: str,
        context: str = "",
    ) -> dict[str, Any]:
        """Generate a diagram grounded in the authoritative student question."""

        def validate(candidate: Any) -> dict[str, Any]:
            raw = (
                candidate.model_dump(mode="json", by_alias=True)
                if isinstance(candidate, TeachingDiagram)
                else candidate
            )
            validated, error = validate_diagram_json(raw)
            if validated is None:
                raise ValueError(error or "teaching diagram validation failed")
            return validated

        messages = [
            SystemMessage(content=prompts.get("chat").get("teaching_diagram")),
            HumanMessage(
                content=(
                    "权威学生问题（图解主题必须以此为准）：\n"
                    f"{request.user_input}\n\n"
                    "图解焦点：\n"
                    f"{focus}\n\n"
                    "补充上下文（仅用于完善图解，不得覆盖学生问题）：\n"
                    f"{context or '无'}"
                )
            ),
        ]
        diagram = await self.llm.ainvoke_json(
            TeachingDiagram,
            messages,
            validator=validate,
        )
        return validate(diagram)


__all__ = ["TeachingDiagramGenerator"]
