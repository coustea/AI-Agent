"""Memory-owned prompt accessors."""

from __future__ import annotations

from pathlib import Path

from app.infra.prompts import ModulePromptLoader


class MemoryPromptManager:
    def __init__(self) -> None:
        self.loader = ModulePromptLoader(
            Path(__file__).with_name("prompts"),
            module_name="memory",
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

    def render_profile(
        self,
        *,
        base_info: str,
        learning_profile: str,
        knowledge_mastery: str,
        recent_dialogue: str,
        long_term_memory: str,
        active_course: str,
        active_topic: str,
        evidence: str,
        behavior_signals: str,
    ) -> str:
        return self.loader.render(
            "profile",
            base_info=base_info,
            learning_profile=learning_profile,
            knowledge_mastery=knowledge_mastery,
            recent_dialogue=recent_dialogue,
            long_term_memory=long_term_memory,
            active_course=active_course,
            active_topic=active_topic,
            evidence=evidence,
            behavior_signals=behavior_signals,
        )


memory_prompts = MemoryPromptManager()
