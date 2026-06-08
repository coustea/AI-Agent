"""Resource-owned prompt accessors."""

from __future__ import annotations

from pathlib import Path

from app.infra.prompts import ModulePromptLoader


class ResourcePromptManager:
    def __init__(self) -> None:
        self.loader = ModulePromptLoader(
            Path(__file__).with_name("prompts"),
            module_name="resource",
        )

    def load_all(self) -> None:
        self.loader.load_all()

    def get(self, prompt_name: str) -> str:
        return self.loader.get(prompt_name)

    def render(self, prompt_name: str, **kwargs: str) -> str:
        return self.loader.render(prompt_name, **kwargs)


resource_prompts = ResourcePromptManager()
