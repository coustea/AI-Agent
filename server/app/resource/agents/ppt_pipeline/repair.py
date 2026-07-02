from __future__ import annotations

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.resource.agents.ppt_pipeline.author import (
    html_output_token_budget,
    strip_outer_html_fence,
)
from app.resource.agents.ppt_pipeline.schemas import (
    DeckBrief,
    StaticAudit,
    StyleDecision,
    VisualAudit,
)


class RepairAgent:
    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    async def repair(
        self,
        *,
        html: str,
        brief: DeckBrief,
        style: StyleDecision,
        static_audit: StaticAudit,
        visual_audit: VisualAudit,
    ) -> str:
        prompt = prompts.get("resource").render(
            "ppt_repair",
            brief=brief.model_dump_json(indent=2),
            style=style.selected.model_dump_json(indent=2),
            static_problems="\n".join(
                f"- {problem}" for problem in static_audit.problems
            )
            or "- none",
            visual_problems="\n".join(
                "- slide "
                f"{problem.slide_index + 1} / {problem.viewport} / "
                f"{problem.problem_type}: {problem.element_summary}"
                for problem in visual_audit.problems
            )
            or "- none",
            html=html,
        )
        response = await self.llm.ainvoke(
            prompt,
            max_tokens=html_output_token_budget(brief.target_slide_count),
        )
        content = response if isinstance(response, str) else response.content
        return strip_outer_html_fence(str(content or ""))
