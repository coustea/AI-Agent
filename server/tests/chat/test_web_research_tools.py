from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from pydantic import BaseModel

from app.chat.tools.web_research import (
    ResearchToolStep,
    UnsafeWebUrl,
    WebAccessLimits,
    WebAccessPolicy,
    WebResearchRunner,
    WebResearchSession,
)
from app.infra.tool_excute import Tool, ToolExcute


PUBLIC_IP = "93.184.216.34"


@pytest.mark.asyncio
async def test_research_runner_owns_model_call_and_tool_excute_only_supplies_schemas() -> None:
    class SearchArgs(BaseModel):
        query: str

    async def search(query: str) -> str:
        return query

    class FakeModel:
        def __init__(self) -> None:
            self.bound_tools: list[dict] = []
            self.responses = iter([
                SimpleNamespace(
                    content="",
                    tool_calls=[{
                        "id": "call-1",
                        "name": "search",
                        "args": {"query": "FCFS"},
                    }],
                ),
                SimpleNamespace(content="done", tool_calls=[]),
            ])

        def bind_tools(self, tools: list[dict]):
            self.bound_tools = tools
            return self

        async def ainvoke(self, messages, **kwargs):
            return next(self.responses)

    model = FakeModel()
    runner = WebResearchRunner(
        model=model,
        tool_excute=ToolExcute(tools=[
            Tool("search", "Search the web.", SearchArgs, search),
        ]),
    )

    async def execute(tool_name: str, payload: dict, call_id: str) -> ResearchToolStep:
        return ResearchToolStep(
            tool_call_id=call_id,
            tool_name=tool_name,
            payload=payload,
            status="done",
            result_text="result",
        )

    steps = await runner.run("讲解 FCFS", execute=execute)

    assert [step.tool_name for step in steps] == ["search"]
    assert model.bound_tools[0]["function"]["name"] == "search"


@pytest.mark.asyncio
async def test_url_policy_rejects_private_destination() -> None:
    policy = WebAccessPolicy(resolver=lambda _host: ["127.0.0.1"])

    with pytest.raises(UnsafeWebUrl, match="public"):
        await policy.validate("https://example.test/secret")


@pytest.mark.asyncio
async def test_open_page_extracts_readable_text_and_resolves_links() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://example.test/article")
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="""
                <html>
                  <head><title>TCP Guide</title></head>
                  <body>
                    <nav>Navigation noise</nav>
                    <main>
                      <h1>TCP Guide</h1>
                      <p>The three-way handshake establishes a connection.</p>
                      <a href="/details">Read the details</a>
                    </main>
                    <script>ignore_me()</script>
                  </body>
                </html>
            """,
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        session = WebResearchSession(
            http_client=client,
            policy=WebAccessPolicy(resolver=lambda _host: [PUBLIC_IP]),
        )
        result = await session.open_page("https://example.test/article")

    assert result["title"] == "TCP Guide"
    assert "three-way handshake" in result["text"]
    assert "Navigation noise" not in result["text"]
    assert "ignore_me" not in result["text"]
    assert result["url"] == "https://example.test/article"
    assert result["page_id"]

    links = await session.extract_links(result["page_id"])
    assert links["links"] == [
        {
            "text": "Read the details",
            "url": "https://example.test/details",
            "same_site": True,
        }
    ]


@pytest.mark.asyncio
async def test_find_in_page_returns_bounded_matching_excerpt() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text=f"<main>{'prefix ' * 100}target phrase{' suffix' * 100}</main>",
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        session = WebResearchSession(
            http_client=client,
            policy=WebAccessPolicy(resolver=lambda _host: [PUBLIC_IP]),
        )
        page = await session.open_page("https://example.test/long")

    result = await session.find_in_page(page["page_id"], "target phrase")

    assert result["match_count"] == 1
    assert "target phrase" in result["text"]
    assert len(result["text"]) <= 700


@pytest.mark.asyncio
async def test_redirect_target_is_revalidated() -> None:
    resolutions = {
        "public.example": [PUBLIC_IP],
        "internal.example": ["10.0.0.8"],
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"location": "http://internal.example/admin"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        session = WebResearchSession(
            http_client=client,
            policy=WebAccessPolicy(resolver=lambda host: resolutions[host]),
        )

        with pytest.raises(UnsafeWebUrl):
            await session.open_page("https://public.example/start")


@pytest.mark.asyncio
async def test_open_page_rejects_oversized_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"x" * 65,
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        session = WebResearchSession(
            http_client=client,
            policy=WebAccessPolicy(resolver=lambda _host: [PUBLIC_IP]),
            limits=WebAccessLimits(max_response_bytes=64),
        )

        with pytest.raises(ValueError, match="large"):
            await session.open_page("https://example.test/large")
