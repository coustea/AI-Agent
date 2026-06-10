"""Profile-owned prompt accessors."""

from __future__ import annotations

from pathlib import Path

from app.infra.prompts import ModulePromptLoader


class ProfilePromptManager:
    def __init__(self) -> None:
        self.loader = ModulePromptLoader(
            Path(__file__).with_name("prompts"),
            module_name="profile",
        )

    def load_all(self) -> None:
        self.loader.load_all()

    def render_onboarding(self, *, onboarding_data: str) -> str:
        return self.loader.render("onboarding", onboarding_data=onboarding_data)

    def render_score(self, *, profile_text: str) -> str:
        return self.loader.render("score", profile_text=profile_text)

    def render_profile(
        self,
        *,
        profile_json: str,
        recent_dialogue: str,
        long_term_memory: str,
    ) -> str:
        return self.loader.render(
            "profile",
            profile_json=profile_json,
            recent_dialogue=recent_dialogue,
            long_term_memory=long_term_memory,
        )


profile_prompts = ProfilePromptManager()

__all__ = ["profile_prompts"]
