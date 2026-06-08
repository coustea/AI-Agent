"""Path-owned prompt accessors."""

from __future__ import annotations

from pathlib import Path

from app.infra.prompts import ModulePromptLoader


class PathPromptManager:
    def __init__(self) -> None:
        self.loader = ModulePromptLoader(
            Path(__file__).with_name("prompts"),
            module_name="path",
        )

    def load_all(self) -> None:
        self.loader.load_all()

    def planner_system(self) -> str:
        return self.loader.get("planner_system")

    def search_research_system(self) -> str:
        return self.loader.get("search_research_system")

    def render_search_research_user(
        self,
        *,
        request_context: str,
        profile_context: str,
    ) -> str:
        return self.loader.render(
            "search_research_user",
            request_context=request_context,
            profile_context=profile_context,
        )

    def render_tutorial(
        self,
        *,
        path_goal: str,
        node_title: str,
        mastery_target: str,
        tutorial_type: str,
        weak_points_section: str,
    ) -> str:
        return self.loader.render(
            "tutorial",
            path_goal=path_goal,
            node_title=node_title,
            mastery_target=mastery_target,
            tutorial_type=tutorial_type,
            weak_points_section=weak_points_section,
        )

    def render_question_generation(
        self,
        *,
        path_goal: str,
        node_title: str,
        mastery_target: str,
        tutorial_title: str,
        tutorial_summary: str,
        round_no: int,
    ) -> str:
        return self.loader.render(
            "question_generation",
            path_goal=path_goal,
            node_title=node_title,
            mastery_target=mastery_target,
            tutorial_title=tutorial_title,
            tutorial_summary=tutorial_summary,
            round_no=round_no,
        )


path_prompts = PathPromptManager()
