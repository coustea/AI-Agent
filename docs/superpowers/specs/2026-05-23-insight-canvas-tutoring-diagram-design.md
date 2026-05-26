# InsightCanvas Intelligent Tutoring Diagram Backend Design

## Purpose

Replace the chat-side knowledge graph demo output with a learner-facing graphical explanation artifact named `InsightCanvas`. The backend must produce structured teaching diagrams that explain the current question, while preserving the already established stateless `TutorAgent` architecture.

This document covers the backend delivery only. Frontend rendering for `InsightCanvas` is a subsequent design and implementation phase. The resource multi-agent module and its graph experiences are outside this scope.

## Product Outcome

When a learner requests a graphical explanation during intelligent tutoring, the chat response contains:

- A normal detailed textual answer.
- One structured `InsightCanvas` that visualizes the reasoning most useful for the question.
- A memorable conclusion, misconception warning, and fast comprehension check.

The output is not a force-directed term network and is not intended to display generic related concepts. It is a teaching aid anchored to the current answer.

## Architecture Boundary

### Decision Layer: `TutorAgent`

`TutorAgent` remains a context-initialized, stateless decision layer:

```python
context = await build_tutor_agent_context(...)
agent = TutorAgent(context)

async for event in agent.chat_stream(history):
    ...
```

`chat_stream(history)` is the sole per-call business input. The agent may read injected context and the supplied history, then generate answer and diagram output. It must not:

- Query or persist chat messages.
- Read or update learner profiles or long-term memory.
- Persist diagram artifacts.
- Write to Neo4j.
- Load conversation history using `session_id`.
- Invoke the resource multi-agent pipeline.

### Service Layer

The chat service owns request preparation and side effects:

1. Parse and normalize `history`.
2. Save the current user message.
3. Read memory-backed profile, long-term facts, and session summary when building `TutorAgentContext`.
4. Instantiate `TutorAgent(context)` and call `chat_stream(history)`.
5. Collect response text and optional `InsightCanvas`.
6. Save the assistant message together with its `teaching_diagram`.
7. Trigger post-turn memory processing after the answer completes.

### API Layer

The HTTP/SSE API accepts the diagram request flag and streams answer and diagram events. It contains no diagram-generation logic.

## Context and State Contract

Chat-side graph switches are removed from `TutorAgentContext` and `TutorState`.

### `TutorAgentContext`

Replace:

```python
need_knowledge_graph: bool
```

With:

```python
need_teaching_diagram: bool = False
diagram_mode: Literal["requested", "off"] = "off"
preferred_diagram_type: Literal[
    "contrast",
    "journey",
    "anatomy",
    "simulation",
] | None = None
```

The first delivery supports explicit request behavior only. `diagram_mode="requested"` means a caller intentionally asks for graphical explanation. Automatic diagram generation is excluded from this phase to control latency and avoid cluttering ordinary tutoring replies.

### `TutorState`

Replace:

```python
need_knowledge_graph: bool
knowledge_graph: ChatKnowledgeGraph | None
knowledge_graph_error: str | None
```

With:

```python
need_teaching_diagram: bool
teaching_diagram: InsightCanvas | None
teaching_diagram_error: str | None
diagram_type: TeachingDiagramType | None
```

History, prompt, profile, memory, file, and attachment data continue to be initialized from `TutorAgentContext` by `prepare_tutor_state(context, history)`.

## InsightCanvas Protocol

### Shared Output Model

```python
TeachingDiagramType = Literal["contrast", "journey", "anatomy", "simulation"]

class InsightCanvas(BaseModel):
    type: TeachingDiagramType
    title: str
    focus_question: str
    takeaway: str
    why_it_works: str
    pitfall: str | None = None
    try_it: str
    personalization_note: str | None = None
    payload: ContrastPayload | JourneyPayload | AnatomyPayload | SimulationPayload
```

The payload is a discriminated union keyed by `type`. Each output represents one coherent board for one learner question.

### `contrast`: Judgment and Distinction

Used when a learner must distinguish concepts or choose between alternatives.

```python
class ContrastSide(BaseModel):
    label: str
    definition: str
    signals: list[str]
    example: str

class ContrastPayload(BaseModel):
    decision_rule: str
    left: ContrastSide
    right: ContrastSide
    scenario_conclusion: str
```

### `journey`: Process and Procedure

Used for ordered procedures, mechanism paths, or learning workflows.

```python
class JourneyStep(BaseModel):
    title: str
    action: str
    rationale: str
    output: str
    warning: str | None = None

class JourneyPayload(BaseModel):
    goal: str
    steps: list[JourneyStep]
    result: str
```

The generated board contains three to six meaningful steps, rather than an unbounded flowchart.

### `anatomy`: Structure and Responsibility

Used when explaining a system, object, model, or component composition.

```python
class AnatomyPart(BaseModel):
    name: str
    responsibility: str
    detail: str
    interaction_cue: str | None = None

class AnatomyPayload(BaseModel):
    subject: str
    parts: list[AnatomyPart]
    interaction_summary: str
```

The generated board contains three to seven parts with learning-relevant responsibilities, not unrelated keyword nodes.

### `simulation`: Dynamic Reasoning

Used for algorithms, calculations, state transitions, or explaining why an output occurs.

```python
class SimulationFrame(BaseModel):
    stage: str
    state: str
    changed: str
    reason: str
    learner_focus: str

class SimulationPayload(BaseModel):
    scenario: str
    initial_state: str
    frames: list[SimulationFrame]
    result: str
```

The generated board contains two to six frames to preserve readability.

## LangGraph Flow

The chat graph removes the `knowledge_graph_generate` and `graph_only` paths. It adds a pure generation node:

```python
async def _teaching_diagram_generate_node(self, state: TutorState) -> TutorState:
    ...
```

Routing is:

```text
direct_answer      -> teaching_diagram_generate when requested -> END
search_answer      -> teaching_diagram_generate when requested -> END
attachment_answer  -> teaching_diagram_generate when requested -> END
```

If a learner asks only for a drawing, the system still first creates an explanatory textual answer and then creates the diagram from that answer. This ensures the diagram is factually anchored and remains useful if rendering is not available.

### Node Inputs

The diagram node reads:

- The current learner question from `state.messages`.
- The completed textual answer from the selected answer node.
- Injected profile, long-term memory, session summary, recent chat, file, and attachment contexts.
- Optional preferred diagram type from context.

### Node Outputs

The node sets:

- `teaching_diagram` when valid structured generation succeeds.
- `diagram_type` to the generated board type.
- `teaching_diagram_error` when diagram generation fails without breaking the answer flow.

It never invokes persistence functions.

## Generation Quality Rules

The prompt and validation contract require every accepted `InsightCanvas` to:

- Answer a precise `focus_question`.
- Provide a concise, memorable `takeaway`.
- Explain mechanism or judgment logic in `why_it_works`.
- Include a relevant misconception or boundary condition when one exists.
- Include a checkable activity in `try_it` that a learner can attempt quickly.
- Use `personalization_note` only when supported by injected learner context.
- Avoid claims about learner weakness, mastery, or preference when no supporting context exists.
- Select the visualization type that best explains the answer, rather than filling a requested type with low-quality content.

The node validates the structured response. If the first structured result is invalid, it may retry generation once. If it is still invalid or the LLM fails, the node records an error and the text answer continues without a diagram.

## Persistence and Streaming

### Stored Assistant Message

The assistant message stores:

```python
content: str
teaching_diagram: InsightCanvas | None
```

The chat-side `knowledge_graph` message field and chat-side Neo4j persistence are removed rather than retained as compatibility aliases.

### SSE Events

The stream exposes:

```text
status: 正在组织解答...
token: <answer text fragment>
status: 正在生成图解说明...
diagram: <InsightCanvas JSON>
done: <complete reply payload including teaching_diagram>
```

If diagram generation fails, text tokens and the final completion event still succeed with `teaching_diagram=null`. The failure does not transform a valid tutoring answer into an HTTP or SSE error.

## Files in Backend Phase

Expected modifications are limited to:

- `server/app/chat/schemas.py`: replace chat graph models/fields with the `InsightCanvas` contract and diagram state fields.
- `server/app/chat/runtime.py`: initialize teaching diagram state from `TutorAgentContext`.
- `server/app/chat/agent.py`: replace graph routing and persistent graph generation with a pure diagram node.
- `server/app/chat/service.py`: build the new context flag, gather diagram output, and persist it with assistant content.
- `server/app/chat/api.py`: replace the chat request flag and outward payload naming.
- `server/app/prompts/chat/intent_classify.md`: classify explicit requests for graphical explanations rather than knowledge graphs.
- `server/app/prompts/chat/teaching_diagram.md`: provide the structured generation and teaching-quality contract.
- `server/app/infra/models.py`: rename the chat message JSON artifact column to `teaching_diagram`.
- `server/app/memory/service.py` and `server/app/memory/store.py`: carry the renamed assistant artifact through message persistence.
- `server/app/avatar/bridge/manager.py`: forward its existing graphical-explanation toggle to `need_teaching_diagram` and consume the new diagram payload key while remaining `persist=False`.
- `server/tests/chat/`: verify schemas, stateless node generation, service persistence, streaming, and API input behavior.

The backend phase does not modify:

- `server/app/resource/` or resource tests.
- Chat frontend rendering components.
- Path-planning or resource graph user experiences.

### Development Database Reset

This repository creates tables through SQLModel `create_all` and does not currently contain a schema migration pipeline. Because this refactor intentionally provides no chat `knowledge_graph` compatibility alias, an existing development database must be recreated before manually exercising persisted chat diagram data. Adding a production data migration is outside this development-stage backend phase.

## Verification Criteria

Backend delivery is complete when:

1. `TutorAgent.chat_stream(history)` remains the only per-turn decision-layer input.
2. No chat agent code calls chat graph persistence or Neo4j writing.
3. A requested diagram produces validated `InsightCanvas` output paired with a text response.
4. Invalid diagram output does not prevent the text response from completing.
5. Service persistence saves `teaching_diagram` with the assistant reply and performs memory updates outside the agent.
6. API/SSE payloads use `teaching_diagram`/`diagram` naming and no longer expose chat-side `knowledge_graph`.
7. Targeted chat tests pass without touching unrelated in-progress resource changes.

## Deferred Work

Frontend redesign is explicitly deferred to a subsequent phase. That phase will replace the nested knowledge-graph modal with a single-surface learner-facing visual board and four purpose-built renderers for the `InsightCanvas` payload types.
