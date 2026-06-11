# Tool-Calling Tutor Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the backend intelligent tutor so learner profile, long-term memory, knowledge-base retrieval, web search, recent evaluation, and attachment analysis are typed tools selected by a LangChain tool-calling agent.

**Architecture:** Keep the current deterministic `TurnOrchestrator` shell for persistence, limits, diagrams, and recovery. Replace keyword routing with native LangChain tool selection, add a request-scoped tutor tool registry/executor, make knowledge/web retrieval lazy by default, and add a streaming/post-turn boundary that can be tested independently.

**Tech Stack:** FastAPI backend, Python 3.12, LangChain core messages/tools, existing `app.infra.llm.Llm`, pytest/pytest-asyncio, existing chat memory/profile/evaluation/knowledge/search services.

---

## File Structure

- Create `server/app/chat/tutor_tools.py`
  - Request-scoped tool argument schemas, `TutorToolRegistry`, and tool output formatting helpers.
  - Exposes LangChain tools named `get_learner_profile`, `get_long_term_memory`, `search_knowledge_base`, `web_search`, `get_recent_evaluation`, and `analyze_attachment`.
- Modify `server/app/chat/agent.py`
  - Remove keyword `_decide()` routing.
  - Bind tools with `llm.model.bind_tools(...)`.
  - Convert model `tool_calls` into `ToolIntent`.
  - Keep `FinalAnswer` return contract so `TurnOrchestrator` can migrate without API changes.
- Modify `server/app/chat/orchestrator.py`
  - Replace inline `ToolExecutor` implementation with the request-scoped `TutorToolExecutor`.
  - Keep transcript projection behavior stable.
  - Stop eager search when the turn is being handled by the tool-calling agent, while preserving a compatibility flag for current tests and web-search requests.
- Modify `server/app/chat/schemas.py`
  - Add evidence type `recent_evaluation`.
- Create `server/app/chat/streaming.py`
  - `ResponseStreamer` yields deterministic chunks from a complete answer first; later switches to direct model streaming when the agent exposes a streaming final-answer method.
- Create `server/app/chat/post_turn.py`
  - `PostTurnPipeline` owns background memory/profile jobs and produces tracked statuses.
- Modify `server/app/chat/service.py`
  - Use `ResponseStreamer` for `token` SSE events.
  - Use `PostTurnPipeline` for post-answer work.
- Modify tests under `server/tests/chat/`
  - Add focused tests for tool registry schemas, agent tool-call conversion, executor evidence mapping, lazy search, streaming chunks, and post-turn pipeline.
  - Update old keyword-routing tests to assert LangChain tool-call behavior.

## Migration Principles

- Preserve `/chat/stream` request and response shape.
- Preserve existing `TurnRunResult`, `project_turn_run`, and DB transcript persistence shape unless a test requires a small additive field.
- Do not expose memory/profile write operations as agent-callable tools.
- Use canonical long-term-memory category keys from `server/app/chat/memory/types.py`.
- Make tool failures non-crashing: executor returns a failed tool result and the agent gets a chance to answer with uncertainty.
- Keep commits scoped and verify each slice.

---

### Task 1: Tutor Tool Registry And Tool Schemas

**Files:**
- Create: `server/app/chat/tutor_tools.py`
- Modify: `server/app/chat/schemas.py`
- Test: `server/tests/chat/test_tutor_tools.py`

- [ ] **Step 1: Write the failing registry/schema tests**

Create `server/tests/chat/test_tutor_tools.py`:

```python
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
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
cd server && rtk uv run pytest tests/chat/test_tutor_tools.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.chat.tutor_tools'`.

- [ ] **Step 3: Add `recent_evaluation` evidence type**

Modify `server/app/chat/schemas.py`:

```python
EvidenceType = Literal[
    "attachment",
    "web_search",
    "knowledge_base",
    "learner_profile",
    "long_term_memory",
    "recent_evaluation",
]
```

- [ ] **Step 4: Implement the registry and tool argument schemas**

Create `server/app/chat/tutor_tools.py`:

```python
"""Request-scoped tutor tools for the chat agent."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.chat.memory.service import get_chat_memory_service
from app.chat.memory.types import LTM_CATEGORIES
from app.chat.schemas import Evidence, ToolIntent, TurnRequest
from app.chat.stages import AttachmentAnalyzer, WebSearchTool
from app.chat.tools.knowledge import aformat_knowledge_context
from app.evaluation.service import evaluation_service
from app.infra.database import session_scope
from app.infra.logging import get_logger
from app.profile.service import get_profile_service

logger = get_logger(__name__)

LongTermMemoryCategory = Literal[
    "learning_background",
    "long_term_goals",
    "learning_preferences",
    "stable_weaknesses",
    "interaction_rules",
    "effective_strategies",
    "corrections",
]


class GetLearnerProfileArgs(BaseModel):
    dimension: str | None = Field(default=None, description="Profile dimension to read, such as goals or preferences.")
    course_name: str | None = Field(default=None, description="Course-specific profile scope when available.")
    reason: str = Field(default="", description="Why the tutor needs the profile.")


class GetLongTermMemoryArgs(BaseModel):
    category: LongTermMemoryCategory | None = Field(default=None, description="Canonical long-term-memory category.")
    reason: str = Field(default="", description="Why the tutor needs durable memory.")


class SearchKnowledgeBaseArgs(BaseModel):
    query: str = Field(description="Search query for local course knowledge.")
    course_name: str | None = Field(default=None, description="Course name used as a retrieval hint.")
    top_k: int = Field(default=4, ge=1, le=8, description="Maximum number of snippets to return.")


class WebSearchArgs(BaseModel):
    query: str = Field(description="Fresh external-information query.")
    reason: str = Field(default="", description="Why current web information is needed.")


class GetRecentEvaluationArgs(BaseModel):
    limit: int = Field(default=5, ge=1, le=10, description="Number of recent evaluation events to summarize.")
    reason: str = Field(default="", description="Why recent evaluation data is needed.")


class AnalyzeAttachmentArgs(BaseModel):
    reason: str = Field(default="", description="What to inspect in the uploaded attachments.")


def _compact(text: str, *, limit: int = 3500) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


class TutorToolRegistry:
    """Build LangChain tools bound to one tutoring turn."""

    def __init__(
        self,
        *,
        request: TurnRequest,
        memory_service: Any | None = None,
        web_search: Any | None = None,
        attachment_analyzer: Any | None = None,
        profile_service: Any | None = None,
    ) -> None:
        self.request = request
        self.memory_service = memory_service or get_chat_memory_service()
        self.profile_service = profile_service or get_profile_service()
        self.web_search = web_search or WebSearchTool()
        self.attachment_analyzer = attachment_analyzer or AttachmentAnalyzer()
        self._tools: list[StructuredTool] | None = None

    def tools(self) -> list[StructuredTool]:
        if self._tools is None:
            self._tools = [
                StructuredTool.from_function(
                    coroutine=self._get_learner_profile,
                    name="get_learner_profile",
                    description="Read learner profile when personalization, goals, preferences, or background matter.",
                    args_schema=GetLearnerProfileArgs,
                ),
                StructuredTool.from_function(
                    coroutine=self._get_long_term_memory,
                    name="get_long_term_memory",
                    description="Read durable learning memory for previous goals, preferences, weaknesses, strategies, or corrections.",
                    args_schema=GetLongTermMemoryArgs,
                ),
                StructuredTool.from_function(
                    coroutine=self._search_knowledge_base,
                    name="search_knowledge_base",
                    description="Search local course knowledge base for definitions, concepts, textbook facts, and course material.",
                    args_schema=SearchKnowledgeBaseArgs,
                ),
                StructuredTool.from_function(
                    coroutine=self._web_search,
                    name="web_search",
                    description="Search the web only for current, recent, or explicitly requested external information.",
                    args_schema=WebSearchArgs,
                ),
                StructuredTool.from_function(
                    coroutine=self._get_recent_evaluation,
                    name="get_recent_evaluation",
                    description="Read recent quiz/evaluation summary for remediation and study planning.",
                    args_schema=GetRecentEvaluationArgs,
                ),
                StructuredTool.from_function(
                    coroutine=self._analyze_attachment,
                    name="analyze_attachment",
                    description="Analyze uploaded images or documents for this turn.",
                    args_schema=AnalyzeAttachmentArgs,
                ),
            ]
        return self._tools

    def by_name(self, name: str) -> StructuredTool:
        for tool in self.tools():
            if tool.name == name:
                return tool
        raise KeyError(f"Unknown tutor tool: {name}")

    async def _get_learner_profile(
        self,
        dimension: str | None = None,
        course_name: str | None = None,
        reason: str = "",
    ) -> str:
        markdown = await self.profile_service.get_profile_markdown(
            self.request.user_id,
            course_name=course_name,
            dimension=dimension,
        )
        return _compact(f"画像读取原因: {reason or '未提供'}\n{markdown}")

    async def _get_long_term_memory(
        self,
        category: LongTermMemoryCategory | None = None,
        reason: str = "",
    ) -> str:
        category_value = str(category or "").strip() or None
        if category_value and category_value not in LTM_CATEGORIES:
            return f"长期记忆分类无效: {category_value}"
        markdown = await self.memory_service.get_memory_markdown(self.request.user_id, category=category_value)
        return _compact(f"长期记忆读取原因: {reason or '未提供'}\n{markdown}")

    async def _search_knowledge_base(
        self,
        query: str,
        course_name: str | None = None,
        top_k: int = 4,
    ) -> str:
        search_query = f"{course_name} {query}".strip() if course_name else query
        context, _rows = await aformat_knowledge_context(search_query, top_k=top_k)
        return _compact(context or "本地知识库没有检索到相关内容，或知识库尚未正确加载。")

    async def _web_search(self, query: str, reason: str = "") -> str:
        result_text, tool_name = await self.web_search.search(query)
        if result_text:
            return _compact(f"搜索渠道: {tool_name or 'web_search'}\n搜索原因: {reason or '未提供'}\n{result_text}")
        return "联网搜索没有返回可用结果。"

    async def _get_recent_evaluation(self, limit: int = 5, reason: str = "") -> str:
        try:
            async with session_scope() as db:
                summary = await evaluation_service.get_summary(db, user_id=self.request.user_id, limit=limit)
        except Exception as exc:
            logger.warning("[TutorToolRegistry] get_recent_evaluation failed: %s", exc)
            return "暂无近期学习测验评估记录。"
        if summary.event_count <= 0:
            return "暂无近期学习测验评估记录。"
        lines = [f"评估读取原因: {reason or '未提供'}", f"测验记录数: {summary.event_count}"]
        if summary.average_score is not None:
            lines.append(f"平均测验分: {summary.average_score}")
        if summary.weak_topics:
            lines.append(f"薄弱点: {', '.join(summary.weak_topics)}")
        if summary.recommendations:
            lines.append(f"系统建议: {', '.join(summary.recommendations)}")
        return _compact("\n".join(lines))

    async def _analyze_attachment(self, reason: str = "") -> str:
        if not self.request.attachments:
            return "本轮没有上传附件。"
        output = await self.attachment_analyzer.analyze(self.request)
        summaries = [item.summary for item in output.evidence]
        if not summaries:
            return "附件分析没有得到可用内容。"
        return _compact(f"附件分析原因: {reason or '未提供'}\n" + "\n\n".join(summaries))
```

- [ ] **Step 5: Run the focused test and verify it passes**

Run:

```bash
cd server && rtk uv run pytest tests/chat/test_tutor_tools.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

Run:

```bash
rtk git add server/app/chat/tutor_tools.py server/app/chat/schemas.py server/tests/chat/test_tutor_tools.py
rtk git commit -m "feat: add tutor tool registry"
```

---

### Task 2: Request-Scoped Tool Executor Evidence Mapping

**Files:**
- Modify: `server/app/chat/tutor_tools.py`
- Modify: `server/app/chat/orchestrator.py`
- Test: `server/tests/chat/test_tutor_tools.py`

- [ ] **Step 1: Write failing executor tests**

Append to `server/tests/chat/test_tutor_tools.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd server && rtk uv run pytest tests/chat/test_tutor_tools.py -q
```

Expected: FAIL with `ImportError` for `TutorToolExecutor`.

- [ ] **Step 3: Implement executor and evidence conversion**

Append to `server/app/chat/tutor_tools.py`:

```python
_TOOL_EVIDENCE_TYPES: dict[str, str] = {
    "get_learner_profile": "learner_profile",
    "get_long_term_memory": "long_term_memory",
    "search_knowledge_base": "knowledge_base",
    "web_search": "web_search",
    "get_recent_evaluation": "recent_evaluation",
    "analyze_attachment": "attachment",
}


class TutorToolExecutor:
    """Execute model-requested tutor tools and convert outputs to orchestrator evidence."""

    def __init__(self, *, request: TurnRequest, registry: TutorToolRegistry | None = None) -> None:
        self.request = request
        self.registry = registry or TutorToolRegistry(request=request)

    def tools(self) -> list[StructuredTool]:
        return self.registry.tools()

    async def execute(self, intent: ToolIntent, request: TurnRequest | None = None) -> dict[str, Any]:
        tool_name = str(intent.tool_name or "").strip()
        payload = intent.payload if isinstance(intent.payload, dict) else {}
        try:
            tool = self.registry.by_name(tool_name)
            result_text = str(await tool.ainvoke(payload)).strip()
        except Exception as exc:
            logger.warning("[TutorToolExecutor] tool failed: name=%s error=%s", tool_name, exc)
            return {
                "tool_name": tool_name,
                "status": "failed",
                "result_text": f"{tool_name} 调用失败: {exc}",
                "evidence": [],
            }

        evidence_type = _TOOL_EVIDENCE_TYPES.get(tool_name)
        evidence = []
        if evidence_type and result_text:
            evidence.append(
                Evidence(
                    evidence_type=evidence_type,  # type: ignore[arg-type]
                    summary=result_text,
                    details={"tool_name": tool_name, "args": payload},
                ).model_dump()
            )
        return {
            "tool_name": tool_name,
            "status": "success" if result_text else "ignored",
            "result_text": result_text,
            "evidence": evidence,
        }
```

- [ ] **Step 4: Replace inline executor construction in orchestrator**

Modify imports in `server/app/chat/orchestrator.py`:

```python
from app.chat.tutor_tools import TutorToolExecutor
```

Modify `TurnOrchestrator.__init__`:

```python
self.tools = tools
```

Modify the beginning of `_reason_until_final`:

```python
tool_executor = self.tools or TutorToolExecutor(request=request)
```

Modify tool execution:

```python
tool_result = await tool_executor.execute(normalized, request)
```

Keep the existing `ToolExecutor` class in place until Task 4 if removing it causes broad diff churn; the orchestrator must stop constructing it by default in this task.

- [ ] **Step 5: Run executor and existing loop tests**

Run:

```bash
cd server && rtk uv run pytest tests/chat/test_tutor_tools.py tests/chat/test_tool_intent_loop.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

Run:

```bash
rtk git add server/app/chat/tutor_tools.py server/app/chat/orchestrator.py server/tests/chat/test_tutor_tools.py
rtk git commit -m "feat: execute tutor tools as evidence"
```

---

### Task 3: LangChain Tool-Calling Reasoning Agent

**Files:**
- Modify: `server/app/chat/agent.py`
- Test: `server/tests/chat/test_reasoning_agent.py`

- [ ] **Step 1: Replace keyword-routing tests with tool-call tests**

Modify `server/tests/chat/test_reasoning_agent.py`:

```python
from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from app.chat.schemas import ConstraintReport, EvidenceSet, TurnRequest


@pytest.mark.asyncio
async def test_reasoning_agent_returns_tool_intent_from_model_tool_call(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat import agent as agent_module
    from app.chat.agent import ReasoningAgent

    class FakeModel:
        def bind_tools(self, tools):
            self.tools = tools
            return self

    class FakeLlm:
        def __init__(self) -> None:
            self.model = FakeModel()

        async def ainvoke(self, _messages, *, model=None, temperature: float = 0.3):
            assert model is self.model
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call-profile-1",
                        "name": "get_learner_profile",
                        "args": {"dimension": "goals", "reason": "personalize"},
                    }
                ],
            )

    async def fake_build_reasoning_messages(**_kwargs):
        return [SimpleNamespace(content="stub")]

    monkeypatch.setattr(agent_module, "build_reasoning_messages", fake_build_reasoning_messages)
    agent = ReasoningAgent(llm=FakeLlm(), tools=[SimpleNamespace(name="get_learner_profile")])

    result = await agent.reason(
        TurnRequest(user_id=7, session_id="s-1", message="结合我的目标给建议"),
        EvidenceSet(items=[]),
        ConstraintReport(),
    )

    assert result.tool_name == "get_learner_profile"
    assert result.payload == {"dimension": "goals", "reason": "personalize"}


@pytest.mark.asyncio
async def test_reasoning_agent_returns_final_answer_when_model_has_no_tool_call(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat import agent as agent_module
    from app.chat.agent import ReasoningAgent

    class FakeModel:
        def bind_tools(self, tools):
            return self

    class FakeLlm:
        def __init__(self) -> None:
            self.model = FakeModel()

        async def ainvoke(self, _messages, *, model=None, temperature: float = 0.3):
            return AIMessage(content="先从定义和例子开始理解。")

    async def fake_build_reasoning_messages(**_kwargs):
        return [SimpleNamespace(content="stub")]

    monkeypatch.setattr(agent_module, "build_reasoning_messages", fake_build_reasoning_messages)
    agent = ReasoningAgent(llm=FakeLlm(), tools=[SimpleNamespace(name="search_knowledge_base")])

    result = await agent.reason(
        TurnRequest(user_id=7, session_id="s-1", message="解释什么是函数"),
        EvidenceSet(items=[]),
        ConstraintReport(),
    )

    assert result.answer == "先从定义和例子开始理解。"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd server && rtk uv run pytest tests/chat/test_reasoning_agent.py -q
```

Expected: FAIL because `ReasoningAgent.__init__` does not accept `tools` and still uses `_decide()`.

- [ ] **Step 3: Implement tool binding in `ReasoningAgent`**

Modify `server/app/chat/agent.py`:

```python
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
```

Replace `ReasoningAgent` with:

```python
class ReasoningAgent:
    """LangChain tool-calling tutor agent.

    The orchestrator still owns actual tool execution. This agent only lets the model
    choose a typed tool and converts that tool call into the existing ToolIntent contract.
    """

    def __init__(self, llm: Any | None = None, tools: list[Any] | None = None) -> None:
        self.llm = llm or get_llm()
        self.tools = list(tools or [])

    async def reason(
        self,
        request: TurnRequest,
        evidence_set: EvidenceSet,
        constraints: ConstraintReport,
        tools: list[Any] | None = None,
    ) -> ToolIntent | FinalAnswer:
        messages = await build_reasoning_messages(
            request=request,
            evidence_set=evidence_set,
            constraint_report=constraints,
        )
        available_tools = list(tools or self.tools)
        model = self.llm.model.bind_tools(available_tools) if available_tools else None
        response = await self.llm.ainvoke(messages, model=model, temperature=0.25)
        tool_call = self._first_new_tool_call(response, constraints)
        if tool_call is not None:
            return ToolIntent(
                tool_name=str(tool_call.get("name") or ""),
                payload=tool_call.get("args") if isinstance(tool_call.get("args"), dict) else {},
            )
        return FinalAnswer(answer=normalize_message_content(getattr(response, "content", "")))

    def _first_new_tool_call(self, response: Any, constraints: ConstraintReport) -> dict[str, Any] | None:
        tool_calls = getattr(response, "tool_calls", None)
        if not isinstance(tool_calls, list):
            return None
        executed = set(constraints.executed_tools)
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            name = str(tool_call.get("name") or "").strip()
            if name and name not in executed:
                return tool_call
            if name:
                constraints.skipped_tools.append(name)
        return None
```

Remove the `_decide()` method and the `import re` line after tests pass.

- [ ] **Step 4: Update reasoning prompt tool policy**

Modify the human prompt inside `build_reasoning_messages` in `server/app/chat/agent.py` so the model receives explicit tool-use rules:

```python
question_prompt = HumanMessage(
    content=(
        "你是一个智能辅导老师。请先判断是否需要调用工具，再回答学生。\n"
        "工具使用原则：\n"
        "- 涉及学生目标、背景、偏好时，调用 get_learner_profile。\n"
        "- 涉及之前、上次、长期偏好或稳定薄弱点时，调用 get_long_term_memory。\n"
        "- 涉及课程知识、定义、教材内容时，调用 search_knowledge_base。\n"
        "- 涉及最新、今天、目前、刚刚发生的信息时，调用 web_search。\n"
        "- 涉及薄弱点补救、学习计划、练习建议时，调用 get_recent_evaluation。\n"
        "- 涉及上传的图片或文档细节时，调用 analyze_attachment。\n"
        "如果已有证据足够，就直接回答。证据不足时说明缺口，不要编造。\n\n"
        f"学生当前问题：{request.message}\n"
        f"已知证据：\n{evidence_text}\n\n"
        f"本轮已执行工具：{executed_tools}"
    )
)
```

- [ ] **Step 5: Run agent tests**

Run:

```bash
cd server && rtk uv run pytest tests/chat/test_reasoning_agent.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

Run:

```bash
rtk git add server/app/chat/agent.py server/tests/chat/test_reasoning_agent.py
rtk git commit -m "feat: use langchain tool calls in tutor agent"
```

---

### Task 4: Wire Tools Into Orchestrator And Make Retrieval Lazy

**Files:**
- Modify: `server/app/chat/orchestrator.py`
- Modify: `server/app/chat/stages.py`
- Test: `server/tests/chat/test_agent_workflow.py`
- Test: `server/tests/chat/test_tool_intent_loop.py`

- [ ] **Step 1: Add lazy-search orchestration tests**

Append to `server/tests/chat/test_agent_workflow.py`:

```python
@pytest.mark.asyncio
async def test_turn_orchestrator_does_not_eager_search_when_tool_agent_can_search() -> None:
    from app.chat.orchestrator import TurnOrchestrator
    from app.chat.schemas import TurnRequest

    calls: list[str] = []

    class FakeSearch:
        async def search(self, request, evidence_set):
            calls.append("search")
            return []

    class FakeAgent:
        async def reason(self, request, evidence_set, constraints, tools=None):
            calls.append("answer")
            assert tools is not None
            return {"kind": "final_answer", "answer": "讲解完成"}

    orchestrator = TurnOrchestrator(search=FakeSearch(), agent=FakeAgent(), eager_search_enabled=False)

    result = await orchestrator.run(
        TurnRequest(user_id=7, session_id="session-1", message="解释 TCP", search_enabled=True)
    )

    assert calls == ["answer"]
    assert result.final_answer == "讲解完成"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
cd server && rtk uv run pytest tests/chat/test_agent_workflow.py::test_turn_orchestrator_does_not_eager_search_when_tool_agent_can_search -q
```

Expected: FAIL because `TurnOrchestrator.__init__` has no `eager_search_enabled` parameter and still calls `search`.

- [ ] **Step 3: Add orchestrator flags and tool passing**

Modify `TurnOrchestrator.__init__` in `server/app/chat/orchestrator.py`:

```python
        eager_search_enabled: bool = False,
```

and:

```python
        self.eager_search_enabled = eager_search_enabled
```

Modify search stage:

```python
        if request.search_enabled and self.search is not None and self.eager_search_enabled:
```

Modify `_reason_until_final` before the loop:

```python
        tool_executor = self.tools or TutorToolExecutor(request=request)
        available_tools = tool_executor.tools() if hasattr(tool_executor, "tools") else []
```

Modify agent call:

```python
            try:
                outcome = await self.agent.reason(request, evidence_set, constraints, tools=available_tools)
            except TypeError:
                outcome = await self.agent.reason(request, evidence_set, constraints)
```

This keeps existing fake agents and tests compatible while new `ReasoningAgent` receives tool schemas.

- [ ] **Step 4: Remove stale default inline executor path**

In `server/app/chat/orchestrator.py`, delete the old `ToolExecutor` class only after the tests below pass with `TutorToolExecutor`.

If deletion causes imports to fail, replace old imports with:

```python
from app.chat.tutor_tools import TutorToolExecutor
```

- [ ] **Step 5: Run workflow tests**

Run:

```bash
cd server && rtk uv run pytest tests/chat/test_agent_workflow.py tests/chat/test_tool_intent_loop.py tests/chat/test_transcript_projections.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

Run:

```bash
rtk git add server/app/chat/orchestrator.py server/app/chat/stages.py server/tests/chat/test_agent_workflow.py server/tests/chat/test_tool_intent_loop.py
rtk git commit -m "refactor: route tutor retrieval through agent tools"
```

---

### Task 5: SSE Response Streamer Boundary

**Files:**
- Create: `server/app/chat/streaming.py`
- Modify: `server/app/chat/service.py`
- Test: `server/tests/chat/test_response_streamer.py`

- [ ] **Step 1: Write failing streamer tests**

Create `server/tests/chat/test_response_streamer.py`:

```python
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_response_streamer_chunks_answer_before_done() -> None:
    from app.chat.streaming import ResponseStreamer

    streamer = ResponseStreamer(chunk_size=4)
    events = [event async for event in streamer.stream_answer("abcdefghi")]

    assert events == [
        {"event": "token", "data": "abcd"},
        {"event": "token", "data": "efgh"},
        {"event": "token", "data": "i"},
    ]


@pytest.mark.asyncio
async def test_response_streamer_skips_empty_answer() -> None:
    from app.chat.streaming import ResponseStreamer

    streamer = ResponseStreamer(chunk_size=4)
    events = [event async for event in streamer.stream_answer("  ")]

    assert events == []
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd server && rtk uv run pytest tests/chat/test_response_streamer.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.chat.streaming'`.

- [ ] **Step 3: Implement `ResponseStreamer`**

Create `server/app/chat/streaming.py`:

```python
"""SSE response streaming helpers for chat turns."""

from __future__ import annotations

from collections.abc import AsyncIterator


class ResponseStreamer:
    """Emit stable token events from final answer text.

    This first step creates a testable boundary. A later agent streaming method can
    feed this same SSE shape with provider chunks.
    """

    def __init__(self, *, chunk_size: int = 24) -> None:
        self.chunk_size = max(1, chunk_size)

    async def stream_answer(self, answer: str) -> AsyncIterator[dict[str, str]]:
        text = str(answer or "")
        if not text.strip():
            return
        for index in range(0, len(text), self.chunk_size):
            chunk = text[index : index + self.chunk_size]
            if chunk:
                yield {"event": "token", "data": chunk}
```

- [ ] **Step 4: Use streamer in `ChatUseCases`**

Modify imports in `server/app/chat/service.py`:

```python
from app.chat.streaming import ResponseStreamer
```

Modify `ChatUseCases.__init__`:

```python
        self._response_streamer = ResponseStreamer()
```

Replace:

```python
        if full_answer:
            yield {"event": "token", "data": full_answer}
```

with:

```python
        async for event in self._response_streamer.stream_answer(full_answer):
            yield event
```

- [ ] **Step 5: Run streamer and service-adjacent tests**

Run:

```bash
cd server && rtk uv run pytest tests/chat/test_response_streamer.py tests/chat/test_turn_persistence.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 5**

Run:

```bash
rtk git add server/app/chat/streaming.py server/app/chat/service.py server/tests/chat/test_response_streamer.py
rtk git commit -m "feat: add chat response streamer"
```

---

### Task 6: Post-Turn Pipeline Boundary

**Files:**
- Create: `server/app/chat/post_turn.py`
- Modify: `server/app/chat/service.py`
- Test: `server/tests/chat/test_post_turn_pipeline.py`

- [ ] **Step 1: Write failing post-turn tests**

Create `server/tests/chat/test_post_turn_pipeline.py`:

```python
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_post_turn_pipeline_runs_memory_then_profile() -> None:
    from app.chat.post_turn import PostTurnPipeline

    calls: list[str] = []

    class FakeMemoryService:
        async def after_turn(self, **kwargs):
            calls.append(f"memory:{kwargs['assistant_reply']}")

    async def fake_profile_update(**kwargs):
        calls.append(f"profile:{kwargs['session_id']}")

    pipeline = PostTurnPipeline(
        memory_service=FakeMemoryService(),
        profile_update=fake_profile_update,
    )

    result = await pipeline.run(
        user_id=7,
        session_id="s-1",
        user_message="怎么学 TCP",
        assistant_reply="先看连接建立",
        usage_metadata=None,
    )

    assert calls == ["memory:先看连接建立", "profile:s-1"]
    assert result == {"memory_pipeline": "success", "profile_update": "success"}


@pytest.mark.asyncio
async def test_post_turn_pipeline_records_failures_without_raising() -> None:
    from app.chat.post_turn import PostTurnPipeline

    class FakeMemoryService:
        async def after_turn(self, **_kwargs):
            raise RuntimeError("memory failed")

    async def fake_profile_update(**_kwargs):
        raise RuntimeError("profile failed")

    pipeline = PostTurnPipeline(memory_service=FakeMemoryService(), profile_update=fake_profile_update)

    result = await pipeline.run(
        user_id=7,
        session_id="s-1",
        user_message="问题",
        assistant_reply="回答",
        usage_metadata=None,
    )

    assert result == {"memory_pipeline": "failed", "profile_update": "failed"}
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd server && rtk uv run pytest tests/chat/test_post_turn_pipeline.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.chat.post_turn'`.

- [ ] **Step 3: Implement `PostTurnPipeline`**

Create `server/app/chat/post_turn.py`:

```python
"""Post-answer side effects for chat turns."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.infra.logging import get_logger

logger = get_logger(__name__)

ProfileUpdate = Callable[..., Awaitable[None]]


class PostTurnPipeline:
    """Run controlled side effects after answer delivery."""

    def __init__(self, *, memory_service: Any, profile_update: ProfileUpdate) -> None:
        self.memory_service = memory_service
        self.profile_update = profile_update

    async def run(
        self,
        *,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        usage_metadata: dict[str, Any] | None,
    ) -> dict[str, str]:
        statuses: dict[str, str] = {}
        try:
            await self.memory_service.after_turn(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
                assistant_reply=assistant_reply,
                usage_metadata=usage_metadata,
            )
            statuses["memory_pipeline"] = "success"
        except Exception:
            logger.exception("[PostTurnPipeline] memory pipeline failed")
            statuses["memory_pipeline"] = "failed"

        try:
            await self.profile_update(user_id=user_id, session_id=session_id)
            statuses["profile_update"] = "success"
        except Exception:
            logger.exception("[PostTurnPipeline] profile update failed")
            statuses["profile_update"] = "failed"

        return statuses
```

- [ ] **Step 4: Wire into `ChatUseCases`**

Modify imports in `server/app/chat/service.py`:

```python
from app.chat.post_turn import PostTurnPipeline
```

Modify `ChatUseCases.__init__`:

```python
        self._post_turn_pipeline = PostTurnPipeline(
            memory_service=self._memory_service,
            profile_update=self._update_learner_profile,
        )
```

Replace the two separate background tasks:

```python
            self._spawn_background(
                self._memory_service.after_turn(
                    user_id=user_id,
                    session_id=effective_session,
                    user_message=current_message,
                    assistant_reply=full_answer,
                    usage_metadata=usage_metadata,
                ),
                label="memory_pipeline",
            )
            self._spawn_background(
                self._update_learner_profile(user_id=user_id, session_id=effective_session),
                label="profile_update",
            )
```

with:

```python
            self._spawn_background(
                self._post_turn_pipeline.run(
                    user_id=user_id,
                    session_id=effective_session,
                    user_message=current_message,
                    assistant_reply=full_answer,
                    usage_metadata=usage_metadata,
                ),
                label="post_turn_pipeline",
            )
```

- [ ] **Step 5: Run post-turn tests**

Run:

```bash
cd server && rtk uv run pytest tests/chat/test_post_turn_pipeline.py tests/chat/test_turn_persistence.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 6**

Run:

```bash
rtk git add server/app/chat/post_turn.py server/app/chat/service.py server/tests/chat/test_post_turn_pipeline.py
rtk git commit -m "refactor: isolate chat post-turn pipeline"
```

---

### Task 7: Regression Suite And Transcript Quality Check

**Files:**
- Modify: `server/tests/chat/test_transcript_projections.py`
- Modify: `server/tests/chat/test_agent_workflow.py`
- Modify: `server/tests/chat/test_tutor_tools.py`

- [ ] **Step 1: Add transcript projection assertion for new tool names**

Append to `server/tests/chat/test_transcript_projections.py`:

```python
def test_project_turn_run_preserves_tool_call_names_for_tutor_tools() -> None:
    from app.chat.orchestrator import ToolExecutionRecord, TurnRunResult, project_turn_run

    result = TurnRunResult(
        final_answer="根据你的画像，先用例子理解。",
        tool_records=[
            ToolExecutionRecord(
                tool_name="get_learner_profile",
                invoked_by="agent",
                payload={"dimension": "preferences"},
                result_text="画像: 喜欢例子",
                raw_result={"status": "success"},
            )
        ],
    )

    projection = project_turn_run(result)

    assert projection.tool_invocations[0]["tool_name"] == "get_learner_profile"
    assert projection.transcript_messages[0]["tool_calls"][0]["name"] == "get_learner_profile"
    assert projection.transcript_messages[-1]["content"] == "根据你的画像，先用例子理解。"
```

- [ ] **Step 2: Run the complete chat-focused suite**

Run:

```bash
cd server && rtk uv run pytest \
  tests/chat/test_agent_workflow.py \
  tests/chat/test_reasoning_agent.py \
  tests/chat/test_tool_intent_loop.py \
  tests/chat/test_transcript_projections.py \
  tests/chat/test_tutor_tools.py \
  tests/chat/test_response_streamer.py \
  tests/chat/test_post_turn_pipeline.py \
  tests/memory/test_memory_service_architecture.py \
  -q
```

Expected: PASS.

- [ ] **Step 3: Run all backend tests if focused suite passes**

Run:

```bash
cd server && rtk uv run pytest -q
```

Expected: PASS, or failures only in unrelated pre-existing tests. If unrelated failures appear, capture exact test names and failure messages in the final report.

- [ ] **Step 4: Commit regression updates**

Run:

```bash
rtk git add server/tests/chat/test_transcript_projections.py server/tests/chat/test_agent_workflow.py server/tests/chat/test_tutor_tools.py
rtk git commit -m "test: cover tutor tool transcript flow"
```

---

## Completion Checklist

- [ ] Tool registry exposes all six read/retrieval tools.
- [ ] `ReasoningAgent` uses `llm.model.bind_tools(...)` and no longer keyword-routes profile/memory/web decisions.
- [ ] Long-term memory tool only accepts canonical category keys.
- [ ] Knowledge-base retrieval is available through `search_knowledge_base`.
- [ ] Recent evaluation is available through `get_recent_evaluation`.
- [ ] Tool failures become non-crashing failed tool results.
- [ ] SSE token events are chunked through `ResponseStreamer`.
- [ ] Post-turn memory/profile writes are grouped behind `PostTurnPipeline`.
- [ ] Existing public `/chat/stream` response shape remains compatible.
- [ ] Focused chat regression suite passes.

## Verification Commands

```bash
cd server && rtk uv run pytest \
  tests/chat/test_agent_workflow.py \
  tests/chat/test_reasoning_agent.py \
  tests/chat/test_tool_intent_loop.py \
  tests/chat/test_transcript_projections.py \
  tests/chat/test_tutor_tools.py \
  tests/chat/test_response_streamer.py \
  tests/chat/test_post_turn_pipeline.py \
  tests/memory/test_memory_service_architecture.py \
  -q
```

```bash
cd server && rtk uv run pytest -q
```
