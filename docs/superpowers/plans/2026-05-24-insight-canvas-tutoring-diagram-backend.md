# InsightCanvas Tutoring Diagram Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the chat-side persisted knowledge graph path with a stateless `TutorAgent` teaching-diagram path that emits and saves validated `InsightCanvas` artifacts alongside textual answers.

**Architecture:** `ChatUseCases` constructs `TutorAgentContext` and owns persistence; `TutorAgent(context).chat_stream(history)` owns only routing and LLM generation. A pure `teaching_diagram_generate` node runs after the completed answer, emits an `InsightCanvas`, and degrades to text-only output when generation fails. Resource multi-agent code stays untouched.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, LangGraph, SQLModel, pytest/pytest-asyncio.

---

## File Map

- Modify `server/app/chat/schemas.py`: define `InsightCanvas` and rename chat/context/state output fields.
- Modify `server/app/chat/runtime.py`: initialize teaching diagram state from injected context.
- Modify `server/app/chat/agent.py`: replace the graph node and routes with a pure teaching diagram generator.
- Create `server/app/prompts/chat/teaching_diagram.md`: LLM structured-output quality prompt.
- Modify `server/app/prompts/chat/intent_classify.md`: classify explicit graphical-explanation requests.
- Modify `server/app/chat/service.py`: pass flags, stream diagram events, and save diagram output.
- Modify `server/app/chat/api.py`: accept the `need_teaching_diagram` form flag.
- Modify `server/app/infra/models.py`, `server/app/memory/service.py`, and `server/app/memory/store.py`: persist the renamed JSON artifact.
- Modify `server/app/avatar/bridge/manager.py`: forward its existing UI toggle to the renamed chat service flag without moving persistence into the agent.
- Create `server/tests/chat/test_teaching_diagram_contract.py`: schema and prompt contract tests.
- Replace `server/tests/chat/test_chat_knowledge_graph_agent.py` with `server/tests/chat/test_teaching_diagram_agent.py`: pure node and graceful-degradation tests.
- Modify `server/tests/chat/test_runtime.py` and `server/tests/chat/test_history.py`: runtime, service, API, and history persistence assertions.

### Task 1: Establish The InsightCanvas Contract And Persistence Name

**Files:**
- Create: `server/tests/chat/test_teaching_diagram_contract.py`
- Modify: `server/tests/chat/test_history.py`
- Modify: `server/app/chat/schemas.py`
- Modify: `server/app/infra/models.py`
- Modify: `server/app/memory/service.py`
- Modify: `server/app/memory/store.py`
- Create: `server/app/prompts/chat/teaching_diagram.md`
- Delete: `server/app/prompts/chat/knowledge_graph.md`

- [ ] **Step 1: Write failing contract tests for the four board payloads and renamed message output**

```python
from pydantic import ValidationError
import pytest

from app.chat.schemas import ChatMessageItem, InsightCanvas
from app.prompts import registry


def test_insight_canvas_accepts_a_learner_facing_contrast_board() -> None:
    canvas = InsightCanvas.model_validate({
        "type": "contrast",
        "title": "组合与聚合怎么选",
        "focus_question": "学生选课系统中的课程与班级属于哪种关系？",
        "takeaway": "生命周期绑定更强时优先考虑组合。",
        "why_it_works": "关系选择取决于部分能否脱离整体独立存在。",
        "pitfall": "不要把所有包含关系都画成组合。",
        "try_it": "判断订单和订单项删除时是否一起消失。",
        "payload": {
            "decision_rule": "先判断生命周期是否绑定",
            "left": {"label": "聚合", "definition": "可独立存在", "signals": ["可复用"], "example": "班级与学生"},
            "right": {"label": "组合", "definition": "随整体消失", "signals": ["生命周期绑定"], "example": "订单与订单项"},
            "scenario_conclusion": "订单项应建模为组合关系。",
        },
    })
    assert canvas.type == "contrast"


def test_insight_canvas_rejects_payload_that_does_not_match_type() -> None:
    with pytest.raises(ValidationError):
        InsightCanvas.model_validate({
            "type": "contrast",
            "title": "错误图板",
            "focus_question": "错误在哪里？",
            "takeaway": "类型必须匹配。",
            "why_it_works": "展示器依赖固定结构。",
            "try_it": "检查 payload。",
            "payload": {"goal": "学习", "steps": [], "result": "结束"},
        })


def test_chat_message_exposes_teaching_diagram_instead_of_knowledge_graph() -> None:
    item = ChatMessageItem(role="assistant", content="回答", teaching_diagram={"type": "contrast"})
    assert item.teaching_diagram == {"type": "contrast"}
    assert "knowledge_graph" not in ChatMessageItem.model_fields


def test_teaching_diagram_prompt_demands_explanation_quality() -> None:
    prompt = registry.get("chat/teaching_diagram")
    assert "focus_question" in prompt
    assert "takeaway" in prompt
    assert "try_it" in prompt
    assert "不要输出 Mermaid" in prompt
```

- [ ] **Step 2: Run the new contract tests and confirm RED**

Run: `cd server && rtk uv run pytest tests/chat/test_teaching_diagram_contract.py -q`

Expected: FAIL because `InsightCanvas` and `chat/teaching_diagram` do not exist and `ChatMessageItem` still exposes `knowledge_graph`.

- [ ] **Step 3: Implement focused Pydantic board models and rename chat message/context/state artifact fields**

Add models with bounded list sizes and payload/type validation in `server/app/chat/schemas.py`:

```python
TeachingDiagramType = Literal["contrast", "journey", "anatomy", "simulation"]


class TeachingDiagramModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContrastSide(TeachingDiagramModel):
    label: str = Field(min_length=1, max_length=30)
    definition: str = Field(min_length=1, max_length=160)
    signals: list[str] = Field(min_length=1, max_length=4)
    example: str = Field(min_length=1, max_length=160)


class ContrastPayload(TeachingDiagramModel):
    decision_rule: str = Field(min_length=1, max_length=240)
    left: ContrastSide
    right: ContrastSide
    scenario_conclusion: str = Field(min_length=1, max_length=240)


class JourneyStep(TeachingDiagramModel):
    title: str = Field(min_length=1, max_length=40)
    action: str = Field(min_length=1, max_length=180)
    rationale: str = Field(min_length=1, max_length=180)
    output: str = Field(min_length=1, max_length=180)
    warning: str | None = Field(default=None, max_length=160)


class JourneyPayload(TeachingDiagramModel):
    goal: str = Field(min_length=1, max_length=200)
    steps: list[JourneyStep] = Field(min_length=3, max_length=6)
    result: str = Field(min_length=1, max_length=240)


class AnatomyPart(TeachingDiagramModel):
    name: str = Field(min_length=1, max_length=40)
    responsibility: str = Field(min_length=1, max_length=180)
    detail: str = Field(min_length=1, max_length=220)
    interaction_cue: str | None = Field(default=None, max_length=160)


class AnatomyPayload(TeachingDiagramModel):
    subject: str = Field(min_length=1, max_length=80)
    parts: list[AnatomyPart] = Field(min_length=3, max_length=7)
    interaction_summary: str = Field(min_length=1, max_length=240)


class SimulationFrame(TeachingDiagramModel):
    stage: str = Field(min_length=1, max_length=40)
    state: str = Field(min_length=1, max_length=200)
    changed: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=200)
    learner_focus: str = Field(min_length=1, max_length=160)


class SimulationPayload(TeachingDiagramModel):
    scenario: str = Field(min_length=1, max_length=200)
    initial_state: str = Field(min_length=1, max_length=200)
    frames: list[SimulationFrame] = Field(min_length=2, max_length=6)
    result: str = Field(min_length=1, max_length=240)


class InsightCanvas(TeachingDiagramModel):
    type: TeachingDiagramType
    title: str = Field(min_length=1, max_length=80)
    focus_question: str = Field(min_length=1, max_length=240)
    takeaway: str = Field(min_length=1, max_length=240)
    why_it_works: str = Field(min_length=1, max_length=400)
    pitfall: str | None = Field(default=None, max_length=240)
    try_it: str = Field(min_length=1, max_length=240)
    personalization_note: str | None = Field(default=None, max_length=240)
    payload: ContrastPayload | JourneyPayload | AnatomyPayload | SimulationPayload

    @model_validator(mode="after")
    def validate_payload_type(self) -> "InsightCanvas":
        expected = {
            "contrast": ContrastPayload,
            "journey": JourneyPayload,
            "anatomy": AnatomyPayload,
            "simulation": SimulationPayload,
        }[self.type]
        if not isinstance(self.payload, expected):
            raise ValueError("teaching diagram payload must match diagram type")
        return self
```

Rename the chat fields:

```python
class ChatMessageItem(BaseModel):
    teaching_diagram: dict[str, Any] | None = None

class TutorAgentContext(BaseModel):
    need_teaching_diagram: bool = False
    diagram_mode: Literal["requested", "off"] = "off"
    preferred_diagram_type: TeachingDiagramType | None = None

class TutorState(TypedDict, total=False):
    need_teaching_diagram: bool
    teaching_diagram: dict[str, Any] | None
    teaching_diagram_error: str | None
    diagram_type: TeachingDiagramType | None
```

Delete `ChatKnowledgeGraphNode`, `ChatKnowledgeGraphEdge`, and `ChatKnowledgeGraph` from the chat schema module because no migrated chat consumer may generate or render the old node-edge payload.

- [ ] **Step 4: Rename the stored assistant artifact through the SQLModel and memory boundary**

Use the direct development-stage rename:

```python
# server/app/infra/models.py
teaching_diagram: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

# server/app/memory/service.py and server/app/memory/store.py
async def save_message(..., teaching_diagram: dict[str, Any] | None = None) -> int:
    ...
    teaching_diagram=teaching_diagram
```

Create `server/app/prompts/chat/teaching_diagram.md` with a strict JSON-only contract containing `focus_question`, `takeaway`, `why_it_works`, `pitfall`, `try_it`, the four allowed board types, prohibition on Mermaid/node networks, and the rule that personalization may only use supplied evidence. Delete the obsolete chat-only `server/app/prompts/chat/knowledge_graph.md` prompt.

- [ ] **Step 5: Run contract tests and commit the protocol boundary**

Run: `cd server && rtk uv run pytest tests/chat/test_teaching_diagram_contract.py tests/chat/test_history.py -q`

Expected: PASS.

Commit:

```bash
rtk git add server/app/chat/schemas.py server/app/infra/models.py server/app/memory/service.py server/app/memory/store.py server/app/prompts/chat/teaching_diagram.md server/app/prompts/chat/knowledge_graph.md server/tests/chat/test_teaching_diagram_contract.py server/tests/chat/test_history.py
rtk git commit -m "feat: define insight canvas chat contract"
```

### Task 2: Initialize Teaching Diagram State From The Stateless Context

**Files:**
- Modify: `server/tests/chat/test_runtime.py`
- Modify: `server/app/chat/runtime.py`

- [ ] **Step 1: Change runtime tests to require the new context-only state**

Use the existing context-initialization test with renamed expectations:

```python
context = TutorAgentContext(
    user_id=7,
    session_id="session-1",
    system_prompt="system prompt",
    profile_context="profile:7",
    long_term_memory_context="memory:7",
    session_summary_context="summary",
    recent_chat_context="recent",
    file_context="images=1 files=0",
    attachment_analysis_context="attachment ctx",
    enable_search=True,
    need_teaching_diagram=True,
    diagram_mode="requested",
    preferred_diagram_type="contrast",
)
state = prepare_tutor_state(context, history)
assert state["need_teaching_diagram"] is True
assert state["teaching_diagram"] is None
assert state["teaching_diagram_error"] is None
assert state["diagram_type"] == "contrast"
```

Update the legacy `prepare_tutor_turn` assertion to the same field names so there is no hidden second graph-state contract.

- [ ] **Step 2: Run runtime tests and confirm RED**

Run: `cd server && rtk uv run pytest tests/chat/test_runtime.py -q`

Expected: FAIL because `prepare_tutor_state` and `prepare_tutor_turn` still initialize `knowledge_graph` keys.

- [ ] **Step 3: Initialize only teaching-diagram state in both preparation paths**

Apply the matching state construction:

```python
"need_teaching_diagram": context.need_teaching_diagram,
"teaching_diagram": None,
"teaching_diagram_error": None,
"diagram_type": context.preferred_diagram_type,
```

For the legacy preparation helper, rename its optional switch to `need_teaching_diagram` and initialize the same output fields; it remains non-persistent and does not introduce a second agent API.

- [ ] **Step 4: Run runtime tests and commit**

Run: `cd server && rtk uv run pytest tests/chat/test_runtime.py -q`

Expected: PASS for runtime contract tests after downstream assertions are updated in later tasks or selected with the new runtime test names.

Commit:

```bash
rtk git add server/app/chat/runtime.py server/tests/chat/test_runtime.py
rtk git commit -m "refactor: initialize teaching diagram tutor state"
```

### Task 3: Replace The Persistent Knowledge Graph Node With Pure Diagram Generation

**Files:**
- Create: `server/tests/chat/test_teaching_diagram_agent.py`
- Delete: `server/tests/chat/test_chat_knowledge_graph_agent.py`
- Modify: `server/app/chat/agent.py`
- Modify: `server/app/prompts/chat/intent_classify.md`

- [ ] **Step 1: Write failing tests for structured generation and non-blocking failure**

```python
@pytest.mark.asyncio
async def test_teaching_diagram_node_generates_insight_canvas_without_storage() -> None:
    tutor = TutorAgent.__new__(TutorAgent)
    tutor.llm = FakeDiagramLLM(valid_contrast_payload)
    result = await tutor._teaching_diagram_generate_node({
        "need_teaching_diagram": True,
        "messages": [HumanMessage(content="聚合和组合怎么区分？")],
        "answer_text": "用生命周期是否绑定进行判断。",
    })
    assert result["teaching_diagram"]["type"] == "contrast"
    assert result["diagram_type"] == "contrast"
    assert result["teaching_diagram_error"] is None


@pytest.mark.asyncio
async def test_teaching_diagram_failure_keeps_answer_and_returns_no_diagram() -> None:
    tutor = TutorAgent.__new__(TutorAgent)
    tutor.llm = RaisingDiagramLLM()
    result = await tutor._teaching_diagram_generate_node({
        "need_teaching_diagram": True,
        "messages": [HumanMessage(content="画图说明递归")],
        "answer_text": "递归通过调用栈保存状态。",
    })
    assert result["answer_text"] == "递归通过调用栈保存状态。"
    assert result["teaching_diagram"] is None
    assert result["teaching_diagram_error"]
```

Add a graph-build assertion that `GRAPH_NODE_NAMES` contains `teaching_diagram_generate` and not `knowledge_graph_generate`.

- [ ] **Step 2: Run node tests and confirm RED**

Run: `cd server && rtk uv run pytest tests/chat/test_teaching_diagram_agent.py -q`

Expected: FAIL because `_teaching_diagram_generate_node` is absent.

- [ ] **Step 3: Replace the LangGraph route and generation node**

In `server/app/chat/agent.py`:

```python
from app.chat.schemas import InsightCanvas, TutorAgentContext, TutorState

class Intent(BaseModel):
    search: bool
    diagram: bool

GRAPH_NODE_NAMES = {
    "classify", "direct_answer", "search_node", "spark_summary",
    "attachment_answer", "teaching_diagram_generate",
}
```

Build routes so text always exists before diagram output:

```python
graph.add_node("teaching_diagram_generate", self._teaching_diagram_generate_node)
graph.add_conditional_edges("direct_answer", self._route_after_answer, {"diagram": "teaching_diagram_generate", "end": END})
graph.add_edge("search_node", "spark_summary")
graph.add_conditional_edges("spark_summary", self._route_after_answer, {"diagram": "teaching_diagram_generate", "end": END})
graph.add_conditional_edges("attachment_answer", self._route_after_answer, {"diagram": "teaching_diagram_generate", "end": END})
graph.add_edge("teaching_diagram_generate", END)
```

Use a pure generator with a single retry for structured validation failure:

```python
async def _teaching_diagram_generate_node(self, state: TutorState) -> TutorState:
    if not state.get("need_teaching_diagram", False):
        return state
    question = extract_question(state.get("messages") or [])
    answer = str(state.get("answer_text", "")).strip()
    if not question or not answer:
        state["teaching_diagram"] = None
        state["teaching_diagram_error"] = "缺少问题或文字回答，跳过图解说明生成"
        return state
    try:
        canvas = await self._generate_teaching_diagram(question=question, answer=answer, state=state)
        state["teaching_diagram"] = canvas.model_dump(mode="json")
        state["diagram_type"] = canvas.type
        state["teaching_diagram_error"] = None
    except Exception as exc:
        state["teaching_diagram"] = None
        state["teaching_diagram_error"] = str(exc)
    return state
```

`_generate_teaching_diagram` invokes `self.llm.ainvoke_json(InsightCanvas, ...)` up to two times, uses `chat/teaching_diagram`, and never imports graph storage or normalization.

- [ ] **Step 4: Update classification wording and stream output**

Replace `graph` classification with `diagram`, describe only explicit “图解说明/画图解释” requests in `server/app/prompts/chat/intent_classify.md`, and emit:

```python
yield stream_event("status", {"stage": "teaching_diagram_generate", "message": "正在生成图解说明..."})
yield stream_event("diagram", runtime_state.get("teaching_diagram"))
yield stream_event("done", {
    "session_id": context.session_id,
    "full_response": full_reply,
    "teaching_diagram": runtime_state.get("teaching_diagram"),
})
```

- [ ] **Step 5: Run agent tests and commit**

Run: `cd server && rtk uv run pytest tests/chat/test_teaching_diagram_agent.py -q`

Expected: PASS.

Commit:

```bash
rtk git add server/app/chat/agent.py server/app/prompts/chat/intent_classify.md server/tests/chat/test_teaching_diagram_agent.py server/tests/chat/test_chat_knowledge_graph_agent.py
rtk git commit -m "refactor: generate insight canvas in tutor agent"
```

### Task 4: Carry Diagram Requests And Results Through Service And API

**Files:**
- Modify: `server/tests/chat/test_runtime.py`
- Modify: `server/tests/chat/test_history.py`
- Modify: `server/app/chat/service.py`
- Modify: `server/app/chat/api.py`
- Modify: `server/app/avatar/bridge/manager.py`

- [ ] **Step 1: Write failing service/API assertions for diagram transport and persistence**

Extend the existing fake-runner tests:

```python
async def fake_runner(**kwargs: Any):
    yield {"event": "token", "data": "回答"}
    yield {"event": "diagram", "data": {"type": "contrast", "title": "判断图板"}}
    yield {"event": "done", "data": {
        "session_id": kwargs["context"].session_id,
        "full_response": "回答",
        "teaching_diagram": {"type": "contrast", "title": "判断图板"},
    }}

assert captured["context"].need_teaching_diagram is True
assert captured["context"].diagram_mode == "requested"
assert memory.saved[1]["teaching_diagram"]["type"] == "contrast"
```

Change API invocation and captured argument assertions:

```python
response = asyncio.run(api.mentor_chat_stream(..., need_teaching_diagram=True, ...))
assert captured["need_teaching_diagram"] is True
```

In history tests use a fake stored message with `teaching_diagram` and assert returned `ChatMessageItem.teaching_diagram`.

- [ ] **Step 2: Run service/API/history tests and confirm RED**

Run: `cd server && rtk uv run pytest tests/chat/test_runtime.py tests/chat/test_history.py -q`

Expected: FAIL because service and API still expose/save `knowledge_graph`.

- [ ] **Step 3: Rename service and API arguments and persist diagram events**

Update signatures and data flow:

```python
async def stream_chat_events(..., need_teaching_diagram: bool = False, ...):
    ...
    agent_context = await self.build_tutor_agent_context(
        ...,
        need_teaching_diagram=need_teaching_diagram,
    )
    teaching_diagram: dict[str, Any] | None = None
    ...
    if event_name == "diagram" and isinstance(payload, dict):
        teaching_diagram = payload
        yield normalized_event
        continue
    if event_name == "done" and isinstance(payload, dict):
        if isinstance(payload.get("teaching_diagram"), dict):
            teaching_diagram = payload["teaching_diagram"]
    ...
    await memory_layer.save_message(..., teaching_diagram=teaching_diagram)
```

In `build_tutor_agent_context` set:

```python
need_teaching_diagram=need_teaching_diagram,
diagram_mode="requested" if need_teaching_diagram else "off",
```

Change FastAPI form input to `need_teaching_diagram`. Remove the chat service `store_knowledge_graph` function and export because persistence is now only the assistant message JSON artifact.

- [ ] **Step 4: Align the digital-human bridge call without changing its UI contract**

The bridge may keep its incoming `need_diagram` toggle, but it must invoke chat correctly:

```python
async for event in chat_uc.stream_chat_events(
    ...,
    need_teaching_diagram=need_diagram,
    persist=False,
):
    ...
    diagram_payload = resources.get("teaching_diagram") if isinstance(resources, dict) else None
```

The bridge still saves its own messages because it intentionally calls chat with `persist=False`; `TutorAgent` remains side-effect free.

- [ ] **Step 5: Run transport tests and commit**

Run: `cd server && rtk uv run pytest tests/chat/test_runtime.py tests/chat/test_history.py -q`

Expected: PASS.

Commit:

```bash
rtk git add server/app/chat/service.py server/app/chat/api.py server/app/avatar/bridge/manager.py server/tests/chat/test_runtime.py server/tests/chat/test_history.py
rtk git commit -m "refactor: stream and persist teaching diagrams"
```

### Task 5: Remove Chat Knowledge-Graph Leakage And Run Regression Verification

**Files:**
- Modify only files already owned by Tasks 1-4 if verification finds a remaining chat-side reference.

- [ ] **Step 1: Assert chat-side production code no longer uses the old contract**

Run:

```bash
rtk rg -n "need_knowledge_graph|knowledge_graph_generate|store_knowledge_graph|ChatKnowledgeGraph" server/app/chat server/app/memory server/app/infra/models.py
```

Expected: no chat-side matches. Resource module matches are allowed and must not be edited.

- [ ] **Step 2: Run the targeted backend regression suite**

Run:

```bash
cd server && rtk uv run pytest tests/chat -q
```

Expected: PASS.

- [ ] **Step 3: Run backend-adjacent regression checks for memory and avatar imports**

Run:

```bash
cd server && rtk uv run pytest tests/memory tests/chat -q
cd server && rtk uv run python -c "from app.avatar.bridge.manager import AvatarBridge; from app.chat.service import ChatUseCases; print('imports ok')"
```

Expected: tests pass and the import check prints `imports ok`. If `tests/memory` does not exist, run `rtk uv run pytest tests/chat -q` plus the import check and record the missing test directory.

- [ ] **Step 4: Document the development database reset requirement in the delivery note**

No compatibility column or production migration is introduced in this phase. Manual persisted-chat verification requires recreating the development database because the SQLModel field changes from `knowledge_graph` to `teaching_diagram`.

- [ ] **Step 5: Commit final verification-only fixes if required**

If Steps 1-3 required a small owned-file repair, commit only that repair:

```bash
rtk git add <owned repaired files>
rtk git commit -m "test: complete teaching diagram backend regression"
```

If no repair was required, do not create an empty commit.
