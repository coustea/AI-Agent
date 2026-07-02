"""Repair agent — fixes HTML based on static audit results."""

from __future__ import annotations

import re

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.shared.cartoon.schemas import (
    StaticAudit,
    StyleDecision,
    VideoBrief,
)


_HTML_FENCE = re.compile(
    r"\A\s*```(?:html)?\s*(?P<html>.*?)\s*```\s*\Z",
    flags=re.DOTALL | re.IGNORECASE,
)


def strip_outer_html_fence(content: str) -> str:
    match = _HTML_FENCE.fullmatch(content)
    return (match.group("html") if match else content).strip()


class RepairAgent:
    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    async def repair(
        self,
        *,
        html: str,
        brief: VideoBrief,
        style: StyleDecision,
        audit: StaticAudit,
    ) -> str:
        prompt = prompts.get("cartoon").render(
            "repair",
            brief=brief.model_dump_json(indent=2),
            style=style.selected.model_dump_json(indent=2),
            problems="\n".join(f"- {p}" for p in audit.problems),
            html=html,
        )
        response = await self.llm.ainvoke(
            prompt,
            max_tokens=32_768,
        )
        content = response if isinstance(response, str) else response.content
        return strip_outer_html_fence(str(content or ""))
