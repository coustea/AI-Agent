# Tutor Diagram Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add TutorAgent backend support for optional structured diagram JSON generation after the normal tutor answer completes.

**Architecture:** Add a focused `app.chat.diagram_schemas` boundary for Pydantic v2 diagram contracts, then add a post-answer `diagram_generate` LangGraph node in `TutorAgent`. Request plumbing carries `need_diagram: true | false` from FastAPI/FormData into `TutorState`, and the final SSE `done` payload exposes `resources.diagram`.

**Tech Stack:** FastAPI, LangGraph, LangChain `with_structured_output`, Pydantic v2, DeepSeek chat LLM, Vue/Vite TypeScript client.

---

## File Map

- Create `server/app/chat/diagram_schemas.py`: Pydantic diagram models, validators, discriminated union, and `DIAGRAM_MODEL_MAP`.
- Modify `server/app/chat/schemas.py`: add `need_diagram` request/state fields and `diagram` state fields.
- Modify `server/app/chat/runtime.py`: pass `need_diagram` into initial `TutorState`.
- Modify `server/app/chat/api.py`: accept `need_diagram` from `/chat/stream`.
- Modify `server/app/chat/service.py`: thread `need_diagram` through `ChatUseCases`.
- Modify `server/app/chat/agent.py`: add prompts, DeepSeek diagram LLM, decision/generation methods, LangGraph node, and SSE `done.resources.diagram`.
- Modify `src/api/ai.ts`: add `need_diagram?: boolean` to chat stream params and FormData.
- Test `server/tests/chat/test_diagram_schemas.py`: schema validation behavior.
- Test `server/tests/chat/test_runtime.py`: `prepare_tutor_turn` carries `need_diagram`.
- Test `server/tests/resource/test_tutor_deepagent.py`: graph and stream behavior around `diagram_generate`.

---

### Task 1: Diagram Pydantic Schema Boundary

**Files:**
- Create: `server/app/chat/diagram_schemas.py`
- Test: `server/tests/chat/test_diagram_schemas.py`

- [ ] **Step 1: Write schema tests first**

Add `server/tests/chat/test_diagram_schemas.py`:

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.chat.diagram_schemas import (
    DIAGRAM_MODEL_MAP,
    FlowDiagram,
    HierarchyDiagram,
    RelationDiagram,
    SequenceDiagram,
    StateDiagram,
)


def test_diagram_model_map_exports_all_supported_types() -> None:
    assert set(DIAGRAM_MODEL_MAP) == {
        "hierarchy",
        "flow",
        "compare",
        "relation",
        "sequence",
        "state",
    }


def test_flow_rejects_edge_referencing_unknown_step() -> None:
    with pytest.raises(ValidationError):
        FlowDiagram.model_validate(
            {
                "type": "flow",
                "title": "流程",
                "summary": "流程说明",
                "spec": {
                    "steps": [
                        {"id": "a", "label": "开始", "description": "开始执行"},
                    ],
                    "edges": [{"source": "a", "target": "missing", "label": "下一步"}],
                },
            }
        )


def test_relation_rejects_edge_referencing_unknown_node() -> None:
    with pytest.raises(ValidationError):
        RelationDiagram.model_validate(
            {
                "type": "relation",
                "title": "关系",
                "summary": "关系说明",
                "spec": {
                    "nodes": [
                        {"id": "client", "label": "客户端", "description": "发起请求"},
                    ],
                    "edges": [
                        {
                            "source": "client",
                            "target": "server",
                            "label": "请求",
                            "description": "发送请求",
                        }
                    ],
                },
            }
        )


def test_sequence_supports_from_to_alias_and_validates_actor_ids() -> None:
    diagram = SequenceDiagram.model_validate(
        {
            "type": "sequence",
            "title": "握手",
            "summary": "客户端和服务器建立连接",
            "spec": {
                "actors": [
                    {"id": "client", "label": "客户端", "description": "发起连接"},
                    {"id": "server", "label": "服务器", "description": "接受连接"},
                ],
                "messages": [
                    {
                        "from": "client",
                        "to": "server",
                        "label": "SYN",
                        "description": "请求建立连接",
                    }
                ],
            },
        }
    )

    dumped = diagram.model_dump(by_alias=True)
    assert dumped["spec"]["messages"][0]["from"] == "client"
    assert dumped["spec"]["messages"][0]["to"] == "server"

    with pytest.raises(ValidationError):
        SequenceDiagram.model_validate(
            {
                "type": "sequence",
                "title": "错误",
                "summary": "引用未知参与者",
                "spec": {
                    "actors": [
                        {"id": "client", "label": "客户端", "description": "发起连接"},
                    ],
                    "messages": [
                        {
                            "from": "client",
                            "to": "missing",
                            "label": "请求",
                            "description": "错误目标",
                        }
                    ],
                },
            }
        )


def test_state_supports_from_to_alias_and_validates_state_ids() -> None:
    diagram = StateDiagram.model_validate(
        {
            "type": "state",
            "title": "状态",
            "summary": "状态变化过程",
            "spec": {
                "states": [
                    {"id": "new", "label": "新建", "description": "刚创建"},
                    {"id": "ready", "label": "就绪", "description": "等待运行"},
                ],
                "transitions": [
                    {
                        "from": "new",
                        "to": "ready",
                        "label": "调度",
                        "description": "进入就绪队列",
                    }
                ],
            },
        }
    )

    dumped = diagram.model_dump(by_alias=True)
    assert dumped["spec"]["transitions"][0]["from"] == "new"
    assert dumped["spec"]["transitions"][0]["to"] == "ready"

    with pytest.raises(ValidationError):
        StateDiagram.model_validate(
            {
                "type": "state",
                "title": "错误",
                "summary": "未知状态引用",
                "spec": {
                    "states": [
                        {"id": "new", "label": "新建", "description": "刚创建"},
                    ],
                    "transitions": [
                        {
                            "from": "new",
                            "to": "missing",
                            "label": "错误",
                            "description": "引用不存在状态",
                        }
                    ],
                },
            }
        )


def test_extra_fields_and_length_limits_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RelationDiagram.model_validate(
            {
                "type": "relation",
                "title": "关系",
                "summary": "关系说明",
                "unexpected": True,
                "spec": {"nodes": [], "edges": []},
            }
        )

    with pytest.raises(ValidationError):
        RelationDiagram.model_validate(
            {
                "type": "relation",
                "title": "标题超过二十个字需要被模型拒绝掉",
                "summary": "关系说明",
                "spec": {"nodes": [], "edges": []},
            }
        )

    with pytest.raises(ValidationError):
        RelationDiagram.model_validate(
            {
                "type": "relation",
                "title": "关系",
                "summary": "关系说明",
                "spec": {
                    "nodes": [
                        {
                            "id": "a",
                            "label": "这个标签长度明显超过十六个字",
                            "description": "说明",
                        }
                    ],
                    "edges": [],
                },
            }
        )


def test_hierarchy_recursive_node_model_validates_children() -> None:
    diagram = HierarchyDiagram.model_validate(
        {
            "type": "hierarchy",
            "title": "知识结构",
            "summary": "展示知识点组成",
            "spec": {
                "root": {
                    "id": "root",
                    "label": "网络",
                    "description": "计算机网络",
                    "children": [
                        {
                            "id": "tcp",
                            "label": "TCP",
                            "description": "可靠传输",
                            "children": [],
                        }
                    ],
                }
            },
        }
    )

    assert diagram.spec.root.children[0].id == "tcp"
```

- [ ] **Step 2: Run schema tests to verify they fail**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation/server
uv run pytest tests/chat/test_diagram_schemas.py -q
```

Expected: FAIL because `app.chat.diagram_schemas` does not exist yet.

- [ ] **Step 3: Implement `diagram_schemas.py`**

Create `server/app/chat/diagram_schemas.py` with the schema boundary:

```python
from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


DiagramType = Literal["hierarchy", "flow", "compare", "relation", "sequence", "state"]


class BaseDiagramModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class DiagramNode(BaseDiagramModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)


class DiagramEdge(BaseDiagramModel):
    source: str = Field(min_length=1, max_length=40)
    target: str = Field(min_length=1, max_length=40)
    label: Optional[str] = Field(default=None, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)


class HierarchyNode(BaseDiagramModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)
    children: list["HierarchyNode"] = Field(default_factory=list, max_length=8)


class HierarchySpec(BaseDiagramModel):
    root: HierarchyNode


class FlowStep(BaseDiagramModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)


class FlowEdge(BaseDiagramModel):
    source: str = Field(min_length=1, max_length=40)
    target: str = Field(min_length=1, max_length=40)
    label: Optional[str] = Field(default=None, max_length=16)


class FlowSpec(BaseDiagramModel):
    steps: list[FlowStep] = Field(min_length=1, max_length=8)
    edges: list[FlowEdge] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_edges(self) -> "FlowSpec":
        ids = {step.id for step in self.steps}
        for edge in self.edges:
            if edge.source not in ids or edge.target not in ids:
                raise ValueError("flow edge source/target must reference existing step ids")
        return self


class CompareItem(BaseDiagramModel):
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)
    points: list[str] = Field(default_factory=list, max_length=6)


class CompareSpec(BaseDiagramModel):
    items: list[CompareItem] = Field(min_length=2, max_length=6)
    dimensions: list[str] = Field(default_factory=list, max_length=8)


class RelationSpec(BaseDiagramModel):
    nodes: list[DiagramNode] = Field(min_length=1, max_length=8)
    edges: list[DiagramEdge] = Field(default_factory=list, max_length=16)

    @model_validator(mode="after")
    def validate_edges(self) -> "RelationSpec":
        ids = {node.id for node in self.nodes}
        for edge in self.edges:
            if edge.source not in ids or edge.target not in ids:
                raise ValueError("relation edge source/target must reference existing node ids")
        return self


class SequenceActor(BaseDiagramModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)


class SequenceMessage(BaseDiagramModel):
    from_actor: str = Field(alias="from", min_length=1, max_length=40)
    to_actor: str = Field(alias="to", min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)


class SequenceSpec(BaseDiagramModel):
    actors: list[SequenceActor] = Field(min_length=2, max_length=6)
    messages: list[SequenceMessage] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_messages(self) -> "SequenceSpec":
        ids = {actor.id for actor in self.actors}
        for message in self.messages:
            if message.from_actor not in ids or message.to_actor not in ids:
                raise ValueError("sequence message from/to must reference existing actor ids")
        return self


class StateTransition(BaseDiagramModel):
    from_state: str = Field(alias="from", min_length=1, max_length=40)
    to_state: str = Field(alias="to", min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=16)
    description: Optional[str] = Field(default=None, max_length=40)


class StateSpec(BaseDiagramModel):
    states: list[DiagramNode] = Field(min_length=1, max_length=8)
    transitions: list[StateTransition] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_transitions(self) -> "StateSpec":
        ids = {state.id for state in self.states}
        for transition in self.transitions:
            if transition.from_state not in ids or transition.to_state not in ids:
                raise ValueError("state transition from/to must reference existing state ids")
        return self


class HierarchyDiagram(BaseDiagramModel):
    type: Literal["hierarchy"]
    title: str = Field(min_length=1, max_length=20)
    summary: Optional[str] = Field(default=None, max_length=50)
    spec: HierarchySpec


class FlowDiagram(BaseDiagramModel):
    type: Literal["flow"]
    title: str = Field(min_length=1, max_length=20)
    summary: Optional[str] = Field(default=None, max_length=50)
    spec: FlowSpec


class CompareDiagram(BaseDiagramModel):
    type: Literal["compare"]
    title: str = Field(min_length=1, max_length=20)
    summary: Optional[str] = Field(default=None, max_length=50)
    spec: CompareSpec


class RelationDiagram(BaseDiagramModel):
    type: Literal["relation"]
    title: str = Field(min_length=1, max_length=20)
    summary: Optional[str] = Field(default=None, max_length=50)
    spec: RelationSpec


class SequenceDiagram(BaseDiagramModel):
    type: Literal["sequence"]
    title: str = Field(min_length=1, max_length=20)
    summary: Optional[str] = Field(default=None, max_length=50)
    spec: SequenceSpec


class StateDiagram(BaseDiagramModel):
    type: Literal["state"]
    title: str = Field(min_length=1, max_length=20)
    summary: Optional[str] = Field(default=None, max_length=50)
    spec: StateSpec


EnabledDiagram = Annotated[
    Union[
        HierarchyDiagram,
        FlowDiagram,
        CompareDiagram,
        RelationDiagram,
        SequenceDiagram,
        StateDiagram,
    ],
    Field(discriminator="type"),
]


class DiagramDecision(BaseDiagramModel):
    need_diagram: bool
    diagram_type: Optional[DiagramType] = None
    reason: Optional[str] = Field(default=None, max_length=80)


DIAGRAM_MODEL_MAP: dict[str, type[BaseDiagramModel]] = {
    "hierarchy": HierarchyDiagram,
    "flow": FlowDiagram,
    "compare": CompareDiagram,
    "relation": RelationDiagram,
    "sequence": SequenceDiagram,
    "state": StateDiagram,
}


HierarchyNode.model_rebuild()
```

- [ ] **Step 4: Run schema tests**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation/server
uv run pytest tests/chat/test_diagram_schemas.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit schema boundary**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation
git add server/app/chat/diagram_schemas.py server/tests/chat/test_diagram_schemas.py
git commit -m "feat: add tutor diagram schemas"
```

---

### Task 2: Request and State Plumbing

**Files:**
- Modify: `server/app/chat/schemas.py`
- Modify: `server/app/chat/runtime.py`
- Modify: `server/app/chat/api.py`
- Modify: `server/app/chat/service.py`
- Modify: `src/api/ai.ts`
- Test: `server/tests/chat/test_runtime.py`

- [ ] **Step 1: Add failing runtime test**

In `server/tests/chat/test_runtime.py`, add or update a test that calls `prepare_tutor_turn(..., need_diagram=True)` and asserts:

```python
assert prepared.initial_state["need_diagram"] is True
assert prepared.initial_state["diagram"] is None
assert prepared.initial_state["diagram_error"] is None
```

If the existing fake context service test already constructs `prepare_tutor_turn`, extend that call with `need_diagram=True` and the assertions above.

- [ ] **Step 2: Run runtime test to verify it fails**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation/server
uv run pytest tests/chat/test_runtime.py -q
```

Expected: FAIL because `prepare_tutor_turn` does not accept `need_diagram`.

- [ ] **Step 3: Update chat schemas**

In `server/app/chat/schemas.py`:

```python
class MentorChatRequest(BaseModel):
    """聊天请求。"""
    message: str
    session_id: Optional[str] = None
    image_urls: Optional[list[str]] = None
    file_urls: Optional[list[str]] = None
    generate_image: Optional[bool] = False
    generate_video: Optional[bool] = False
    enable_search: Optional[bool] = False
    need_diagram: Optional[bool] = False
```

In `TutorState`, add under request/resource flags:

```python
    need_diagram: Optional[bool]
    diagram: Optional[dict[str, Any]]
    diagram_error: Optional[str]
```

- [ ] **Step 4: Update runtime preparation**

In `server/app/chat/runtime.py`, add `need_diagram: bool | None` to `prepare_tutor_turn(...)` and include:

```python
        "need_diagram": need_diagram,
        "diagram": None,
        "diagram_error": None,
```

in `initial_state`.

- [ ] **Step 5: Update FastAPI/service plumbing**

In `server/app/chat/api.py`, add:

```python
    need_diagram: bool = Form(default=False),
```

and pass `need_diagram=need_diagram` into `uc.stream_chat(...)`.

In `server/app/chat/service.py`, add `need_diagram: bool = False` to both `stream_chat_events(...)` and `stream_chat(...)`, then pass it through to the runner kwargs and the nested call:

```python
            "need_diagram": bool(need_diagram),
```

In `server/app/chat/agent.py`, add `need_diagram: bool = False` to `chat_stream(...)` and pass it into `prepare_tutor_turn(...)`.

- [ ] **Step 6: Update frontend stream params**

In `src/api/ai.ts`, add:

```ts
  need_diagram?: boolean
```

to `StreamChatParams`, and append it to `FormData`:

```ts
  if (params.need_diagram != null) {
    formData.append('need_diagram', String(Boolean(params.need_diagram)))
  }
```

- [ ] **Step 7: Run focused tests/build**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation/server
uv run pytest tests/chat/test_runtime.py -q
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation
npm run build
```

Expected: pytest PASS and frontend build PASS.

- [ ] **Step 8: Commit request plumbing**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation
git add server/app/chat/schemas.py server/app/chat/runtime.py server/app/chat/api.py server/app/chat/service.py server/app/chat/agent.py src/api/ai.ts server/tests/chat/test_runtime.py
git commit -m "feat: plumb tutor diagram request flag"
```

---

### Task 3: TutorAgent Diagram Node and Structured Generation

**Files:**
- Modify: `server/app/chat/agent.py`
- Test: `server/tests/resource/test_tutor_deepagent.py`

- [ ] **Step 1: Add graph/node tests**

In `server/tests/resource/test_tutor_deepagent.py`, add tests with fake structured LLM classes:

```python
class FakeStructuredLLM:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def ainvoke(self, messages):
        self.calls.append(messages)
        return self.payload


class FakeDiagramLLM:
    def __init__(self, outputs):
        self.outputs = outputs
        self.models = []

    def with_structured_output(self, model_cls):
        self.models.append(model_cls)
        return FakeStructuredLLM(self.outputs.pop(0))
```

Add a test for disabled diagrams:

```python
def test_diagram_generate_node_skips_when_disabled():
    from app.chat.agent import TutorAgent
    from langchain_core.messages import HumanMessage

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.diagram_llm = FakeDiagramLLM([])

    state = {
        "need_diagram": False,
        "messages": [HumanMessage(content="TCP 三次握手是什么？")],
        "answer_text": "TCP 三次握手用于建立可靠连接。",
    }

    result = asyncio.run(tutor._diagram_generate_node(state))

    assert result["diagram"] is None
    assert tutor.diagram_llm.models == []
```

Add a test for sequence generation:

```python
def test_diagram_generate_node_generates_sequence_when_requested():
    from app.chat.agent import TutorAgent
    from app.chat.diagram_schemas import DiagramDecision, SequenceDiagram
    from langchain_core.messages import HumanMessage

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.diagram_llm = FakeDiagramLLM(
        [
            DiagramDecision(need_diagram=True, diagram_type="sequence", reason="适合时序图"),
            {
                "type": "sequence",
                "title": "TCP三次握手",
                "summary": "展示连接建立过程",
                "spec": {
                    "actors": [
                        {"id": "client", "label": "客户端", "description": "发起连接"},
                        {"id": "server", "label": "服务器", "description": "接受连接"},
                    ],
                    "messages": [
                        {
                            "from": "client",
                            "to": "server",
                            "label": "SYN",
                            "description": "请求建立连接",
                        }
                    ],
                },
            },
        ]
    )

    state = {
        "need_diagram": True,
        "messages": [HumanMessage(content="TCP 三次握手是什么？请配图解释")],
        "answer_text": "TCP 三次握手包括 SYN、SYN-ACK、ACK。",
        "profile_context": "",
        "fact_context": "",
        "recent_chat_context": "",
        "attachment_analysis_context": "",
    }

    result = asyncio.run(tutor._diagram_generate_node(state))

    assert tutor.diagram_llm.models[0].__name__ == "DiagramDecision"
    assert tutor.diagram_llm.models[1] is SequenceDiagram
    assert result["diagram"]["type"] == "sequence"
    assert result["diagram"]["spec"]["messages"][0]["from"] == "client"
```

Add a test for generation failure:

```python
class RaisingStructuredLLM:
    async def ainvoke(self, messages):
        raise RuntimeError("structured output unavailable")


class RaisingDiagramLLM:
    def with_structured_output(self, model_cls):
        return RaisingStructuredLLM()


def test_diagram_generate_node_failure_does_not_raise():
    from app.chat.agent import TutorAgent
    from langchain_core.messages import HumanMessage

    tutor = TutorAgent.__new__(TutorAgent)
    tutor.diagram_llm = RaisingDiagramLLM()

    state = {
        "need_diagram": True,
        "messages": [HumanMessage(content="进程和线程有什么区别？")],
        "answer_text": "进程是资源分配单位，线程是调度单位。",
    }

    result = asyncio.run(tutor._diagram_generate_node(state))

    assert result["diagram"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation/server
uv run pytest tests/resource/test_tutor_deepagent.py -q
```

Expected: FAIL because diagram methods/node do not exist.

- [ ] **Step 3: Add imports and prompts in `agent.py`**

Add:

```python
from app.chat.diagram_schemas import DIAGRAM_MODEL_MAP, DiagramDecision
```

Add `diagram_generate` to `GRAPH_NODE_NAMES`.

Add `DIAGRAM_DECISION_SYSTEM_PROMPT` and `DIAGRAM_GENERATION_SYSTEM_PROMPT` exactly as specified in the design/request.

- [ ] **Step 4: Add diagram LLM in `TutorAgent.__init__`**

Add:

```python
        self.diagram_llm = get_deepseek_chat_llm(
            temperature=0.1,
            streaming=False,
            max_tokens=1600,
        )
```

- [ ] **Step 5: Implement decision/generation methods**

Add `_decide_diagram(...)` and `_generate_diagram_by_type(...)` to `TutorAgent` using:

```python
structured_llm = self.diagram_llm.with_structured_output(DiagramDecision)
decision = await structured_llm.ainvoke([
    SystemMessage(content=DIAGRAM_DECISION_SYSTEM_PROMPT),
    HumanMessage(content=prompt),
])
```

For concrete generation:

```python
model_cls = DIAGRAM_MODEL_MAP.get(diagram_type)
structured_llm = self.diagram_llm.with_structured_output(model_cls)
diagram = await structured_llm.ainvoke([
    SystemMessage(content=DIAGRAM_GENERATION_SYSTEM_PROMPT),
    HumanMessage(content=prompt),
])
diagram = model_cls.model_validate(diagram)
return diagram.model_dump(by_alias=True)
```

Catch exceptions with `logger.warning(...)` and return disabled/`None`.

- [ ] **Step 6: Implement `_diagram_generate_node`**

Use `@node_timer("diagram_generate")` if the project decorator supports that form. If not, follow local style with:

```python
with node_timer("diagram_generate", user=user_id, session=session_id):
    ...
```

The node must:

- extract question with `extract_question(state.get("messages") or [])`
- read answer from `final_answer`, `answer_text`, `answer`, `response`
- set `diagram=None` and `diagram_error` when question/answer is missing
- call `_decide_diagram`
- call `_generate_diagram_by_type`
- never raise diagram failures into the main answer path

- [ ] **Step 7: Wire LangGraph edges**

In `_ensure_graph`, add:

```python
graph.add_node("diagram_generate", self._diagram_generate_node)
graph.add_edge("direct_answer", "diagram_generate")
graph.add_edge("attachment_answer", "diagram_generate")
graph.add_edge("diagram_generate", END)
```

Remove the old direct `direct_answer -> END` and `attachment_answer -> END` edges.

- [ ] **Step 8: Run focused TutorAgent tests**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation/server
uv run pytest tests/resource/test_tutor_deepagent.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit TutorAgent diagram node**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation
git add server/app/chat/agent.py server/tests/resource/test_tutor_deepagent.py
git commit -m "feat: add tutor diagram generation node"
```

---

### Task 4: SSE Done Payload and End-to-End Verification

**Files:**
- Modify: `server/app/chat/agent.py`
- Test: `server/tests/resource/test_tutor_deepagent.py`

- [ ] **Step 1: Add stream test for `done.resources.diagram`**

In `server/tests/resource/test_tutor_deepagent.py`, extend the fake graph stream test or add a new one where the fake graph emits:

```python
yield {
    "event": "on_chain_end",
    "name": "diagram_generate",
    "data": {
        "output": {
            "diagram": {
                "type": "compare",
                "title": "进程和线程",
                "summary": "对比资源和调度差异",
                "spec": {
                    "items": [
                        {"label": "进程", "description": "资源分配单位", "points": ["独立地址空间"]},
                        {"label": "线程", "description": "CPU调度单位", "points": ["共享进程资源"]},
                    ],
                    "dimensions": ["资源", "调度"],
                },
            }
        }
    },
}
```

Then collect `chat_stream(...)` events and assert:

```python
done_events = [e for e in events if e["event"] == "done"]
assert done_events[0]["data"]["resources"]["diagram"]["type"] == "compare"
assert done_events[0]["data"]["resources"]["video"] is None
```

- [ ] **Step 2: Run stream test to verify it fails**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation/server
uv run pytest tests/resource/test_tutor_deepagent.py -q
```

Expected: FAIL because `done` does not include `resources.diagram`.

- [ ] **Step 3: Update `done` payload in `TutorAgent.chat_stream`**

Change the final `stream_event("done", ...)` payload to include:

```python
                "resources": {
                    "diagram": runtime_state.get("diagram"),
                    "video": None,
                },
```

Keep existing fields:

```python
                "session_id": effective_session,
                "resource_mode": "none",
                "resource": None,
```

- [ ] **Step 4: Run focused backend tests**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation/server
uv run pytest tests/chat/test_diagram_schemas.py tests/chat/test_runtime.py tests/resource/test_tutor_deepagent.py -q
```

Expected: PASS.

- [ ] **Step 5: Run frontend build**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation
npm run build
```

Expected: PASS.

- [ ] **Step 6: Run diff checks**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation
git diff --check
git status --short
```

Expected: no whitespace errors; status only contains intentional files before commit.

- [ ] **Step 7: Commit final response behavior**

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation
git add server/app/chat/agent.py server/tests/resource/test_tutor_deepagent.py
git commit -m "feat: return tutor diagram in stream done event"
```

---

## Final Verification

Run:

```bash
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation/server
uv run pytest tests/chat/test_diagram_schemas.py tests/chat/test_runtime.py tests/resource/test_tutor_deepagent.py -q
cd /Users/apple/.config/superpowers/worktrees/software/tutor-diagram-generation
npm run build
git diff --check
```

Expected:

- All focused backend tests pass.
- Frontend build passes.
- `git diff --check` reports no whitespace errors.

Manual API checks after starting backend/frontend:

1. `message="TCP 三次握手是什么？请配图解释"`, `need_diagram=true`: `done.data.resources.diagram.type` should usually be `"sequence"`.
2. `message="进程和线程有什么区别？"`, `need_diagram=true`: `done.data.resources.diagram.type` should usually be `"compare"`.
3. `message="Redis 是什么？"`, `need_diagram=false`: `done.data.resources.diagram` must be `null`, answer still streams normally.

## Plan Self-Review

- Spec coverage: schema, request flag, TutorState, DeepSeek diagram LLM, decision/generation methods, graph edge changes, SSE response, frontend FormData, and tests are all covered by tasks.
- Placeholder scan: no TBD/TODO/later placeholders remain.
- Type consistency: uses `answer_text` as the current TutorAgent final answer field, while still designing node fallback for `final_answer`, `answer`, and `response`.
