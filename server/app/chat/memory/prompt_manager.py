"""Chat-memory-owned prompt accessors."""

from __future__ import annotations

from pathlib import Path

from app.infra.prompts import ModulePromptLoader


class ChatMemoryPromptManager:
    def __init__(self) -> None:
        self.loader = ModulePromptLoader(
            Path(__file__).with_name("prompts"),
            module_name="chat_memory",
        )

    def load_all(self) -> None:
        self.loader.load_all()

    def render_compression(self, *, dialogue_text: str) -> str:
        return self.loader.render("compression", dialogue_text=dialogue_text)

    def render_ltm_update(
        self,
        *,
        user_message: str,
        assistant_reply: str,
        session_summary: str,
        old_memory: str,
    ) -> str:
        return self.loader.render(
            "ltm_update",
            user_message=user_message,
            assistant_reply=assistant_reply,
            session_summary=session_summary,
            old_memory=old_memory,
        )


chat_memory_prompts = ChatMemoryPromptManager()
