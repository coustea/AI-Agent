"""Visual director — selects style and animation strategy."""

from __future__ import annotations

import json

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.shared.cartoon.schemas import StyleDecision, VideoBrief, CartoonVideoRequest


class VisualDirector:
    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    async def direct(self, brief: VideoBrief, request: CartoonVideoRequest) -> StyleDecision:
        safe_presets = [
            {
                "name": "Chalkboard Sketch",
                "source": "preset",
                "mood": "hand-drawn, educational",
                "colors": "slate gray canvas, white sketch lines, mint green accent",
                "recipe": "Comic Neue & Space Mono; chalk-like border boxes; hand-drawn style arrow vectors.",
            },
            {
                "name": "Cyber Tech Grid",
                "source": "preset",
                "mood": "futuristic, structural",
                "colors": "near-black canvas, cyan and hot magenta neon glow",
                "recipe": "JetBrains Mono & Clash Display; glowing cards; structural grid lines; terminal blinking caret.",
            },
            {
                "name": "Modern Swiss Print",
                "source": "preset",
                "mood": "precise, minimalistic",
                "colors": "off-white canvas, bold charcoal borders, red accent line",
                "recipe": "Archivo & Space Grotesk; high scale contrast; rigid grid layout; clear segment markers.",
            },
        ]
        prompt = prompts.get("cartoon").render(
            "style",
            brief=brief.model_dump_json(indent=2),
            request=request.model_dump_json(indent=2),
            safe_presets=json.dumps(safe_presets, ensure_ascii=False, indent=2),
        )
        return await self.llm.ainvoke_json(StyleDecision, prompt)
