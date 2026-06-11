from __future__ import annotations

import pytest

from app.chat.schemas import TurnRequest


def test_tutor_tool_registry_exposes_expected_names() -> None:
    from app.chat.tutor_tools import TutorToolRegistry

    request = TurnRequest(user_id=7, session_id="s-1", message="结合我的情况讲一下 TCP")
    registry = TutorToolRegistry(request=request)

    tool_names = [tool.name for tool in registry.tools()]

    assert tool_names == [
        "get_learner_profile",
        "get_long_term_memory",
        "search_knowledge_base",
        "web_search",
        "get_recent_evaluation",
        "analyze_attachment",
    ]


def test_long_term_memory_categories_are_canonical() -> None:
    from app.chat.memory.types import LTM_CATEGORIES
    from app.chat.tutor_tools import GetLongTermMemoryArgs

    schema = GetLongTermMemoryArgs.model_json_schema()
    category_schema = schema["properties"]["category"]
    enum_values = next(item["enum"] for item in category_schema["anyOf"] if "enum" in item)

    assert enum_values == list(LTM_CATEGORIES)


@pytest.mark.asyncio
async def test_registry_profile_tool_uses_bound_request(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat import tutor_tools
    from app.chat.tutor_tools import TutorToolRegistry

    calls: list[tuple[int, str | None, str | None]] = []

    class FakeProfileService:
        async def get_profile_markdown(
            self,
            user_id: int,
            course_name: str | None = None,
            dimension: str | None = None,
        ) -> str:
            calls.append((user_id, dimension, course_name))
            return "画像: 目标是考研"

    monkeypatch.setattr(tutor_tools, "get_profile_service", lambda: FakeProfileService())

    request = TurnRequest(user_id=7, session_id="s-1", message="按我的目标讲")
    registry = TutorToolRegistry(request=request)
    profile_tool = registry.by_name("get_learner_profile")

    result = await profile_tool.ainvoke(
        {"dimension": "goals", "course_name": "计算机网络", "reason": "personalize answer"}
    )

    assert "画像: 目标是考研" in result
    assert calls == [(7, "goals", "计算机网络")]
