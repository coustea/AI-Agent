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


@pytest.mark.asyncio
async def test_registry_profile_tool_returns_fallback_on_service_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.chat import tutor_tools
    from app.chat.tutor_tools import TutorToolRegistry

    class FailingProfileService:
        async def get_profile_markdown(
            self,
            user_id: int,
            course_name: str | None = None,
            dimension: str | None = None,
        ) -> str:
            raise RuntimeError("profile db unavailable")

    monkeypatch.setattr(tutor_tools, "get_profile_service", lambda: FailingProfileService())

    request = TurnRequest(user_id=7, session_id="s-1", message="按我的目标讲")
    registry = TutorToolRegistry(request=request)
    profile_tool = registry.by_name("get_learner_profile")

    result = await profile_tool.ainvoke({"dimension": "goals"})

    assert result == "暂时无法读取学习者画像。"


@pytest.mark.asyncio
async def test_tool_executor_maps_profile_result_to_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat import tutor_tools
    from app.chat.schemas import ToolIntent
    from app.chat.tutor_tools import TutorToolExecutor

    class FakeProfileService:
        async def get_profile_markdown(self, user_id: int, **_kwargs) -> str:
            assert user_id == 7
            return "画像: 喜欢先看例子"

    monkeypatch.setattr(tutor_tools, "get_profile_service", lambda: FakeProfileService())

    request = TurnRequest(user_id=7, session_id="s-1", message="结合我的情况讲")
    executor = TutorToolExecutor(request=request)
    result = await executor.execute(ToolIntent(tool_name="get_learner_profile", payload={"dimension": "preferences"}))

    assert result["tool_name"] == "get_learner_profile"
    assert result["status"] == "success"
    assert result["result_text"].startswith("画像读取原因")
    assert result["evidence"][0]["evidence_type"] == "learner_profile"


@pytest.mark.asyncio
async def test_tool_executor_converts_tool_failure_to_non_crashing_result() -> None:
    from app.chat.schemas import ToolIntent
    from app.chat.tutor_tools import TutorToolExecutor, TutorToolRegistry

    class FakeTool:
        name = "web_search"

        async def ainvoke(self, _payload):
            raise RuntimeError("provider down")

    class FakeRegistry(TutorToolRegistry):
        def by_name(self, name: str):
            assert name == "web_search"
            return FakeTool()

    request = TurnRequest(user_id=7, session_id="s-1", message="查一下最新资料")
    executor = TutorToolExecutor(request=request, registry=FakeRegistry(request=request))

    result = await executor.execute(ToolIntent(tool_name="web_search", payload={"query": "最新资料"}))

    assert result["status"] == "failed"
    assert "provider down" in result["result_text"]
    assert result["evidence"] == []
