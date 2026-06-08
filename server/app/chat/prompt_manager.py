"""Chat-owned prompt accessors."""

from __future__ import annotations

from pathlib import Path

from app.infra.prompts import ModulePromptLoader


def _parse_markdown_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_header: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            if current_header:
                sections[current_header] = "\n".join(current_lines).strip()
            current_header = line.lstrip("#").strip()
            current_lines = []
            continue
        if current_header is not None:
            current_lines.append(line)
    if current_header:
        sections[current_header] = "\n".join(current_lines).strip()
    return sections


class ChatPromptManager:
    def __init__(self) -> None:
        self.loader = ModulePromptLoader(
            Path(__file__).with_name("prompts"),
            module_name="chat",
        )
        self._answer_policy_sections: dict[str, str] | None = None

    def load_all(self) -> None:
        self.loader.load_all()
        self._answer_policy_sections = None

    def render_tutor_system(
        self,
        *,
        session_summary_context: str,
        file_context: str,
        attachment_analysis_context: str,
        evaluation_summary_context: str,
    ) -> str:
        return self.loader.render(
            "tutor_system",
            session_summary_context=session_summary_context,
            file_context=file_context,
            attachment_analysis_context=attachment_analysis_context,
            evaluation_summary_context=evaluation_summary_context,
        )

    def render_search_instruction(self, *, attachment_context_section: str) -> str:
        return self.loader.render(
            "search_instruction",
            attachment_context_section=attachment_context_section,
        )

    def answer_policy_sections(self) -> dict[str, str]:
        if self._answer_policy_sections is None:
            self._answer_policy_sections = _parse_markdown_sections(
                self.loader.get("answer_policy")
            )
        return dict(self._answer_policy_sections)

    def render_answer_policy_section(self, section_name: str, **kwargs: str) -> str:
        template = self.answer_policy_sections().get(section_name, "")
        return self.loader.render_text(
            template,
            prompt_key=f"answer_policy#{section_name}",
            **kwargs,
        )

    def teaching_diagram_system(self) -> str:
        return self.loader.get("teaching_diagram")


chat_prompts = ChatPromptManager()
