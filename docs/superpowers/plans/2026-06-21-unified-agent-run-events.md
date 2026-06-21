# Unified Agent Run Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the separate chat, resource, and path event streams with one persisted run identity, one `AgentEvent` schema, one event bus, and one `/agent-runs/{run_id}/events` SSE endpoint.

**Architecture:** Every asynchronous agent invocation creates an `AgentRun` row owned by one user and identified by a UUID `run_id`. All modules publish the same `AgentEvent` objects through `AgentEventEmitter`; a bounded in-memory bus replays active-run events and the database preserves ownership and terminal state. The frontend creates a run through the relevant business API, then uses one shared subscriber for status, tools, artifacts, answer deltas, and terminal events.

**Tech Stack:** FastAPI, SQLModel, PostgreSQL, asyncio, Pydantic, Server-Sent Events, Vue 3, TypeScript.

**Repository constraints:** Modify source files only. Do not create or edit test files. Keep resource and path records, detail pages, and persistence models separate. Remove old event protocols without compatibility aliases.

---

## File map

- Create `server/app/infra/agent_events.py`: global event schema, run lifecycle service, bounded event bus, emitter, and SSE encoder.
- Create `server/app/infra/agent_events_api.py`: the single authenticated SSE subscription route.
- Modify `server/app/infra/models.py` and `server/init_schema.sql`: persist global run ownership and terminal state.
- Modify `server/app/routes.py`: install the one global event router.
- Modify chat agent/service/router files: create chat runs, publish global events, and remove the POST response stream.
- Modify resource runner/orchestrator/agent files and `server/app/resource/api.py`: publish through the global emitter and remove the resource event endpoint.
- Delete `server/app/resource/events.py` after all imports are migrated.
- Modify `server/app/path/service.py` and `server/app/path/api.py`: publish through the global emitter and remove the path event endpoint.
- Create `src/shared/agent-events/model.ts` and `src/shared/agent-events/api.ts`: the only frontend event type and subscriber.
- Modify the chat, resource, and learning-path frontend consumers to use `run_id` and the shared subscriber.
- Remove module-specific frontend stream types and subscription functions.

### Task 1: Persist global Agent runs

**Files:**
- Modify: `server/app/infra/models.py`
- Modify: `server/init_schema.sql`

- [ ] **Step 1: Add the global run model**

Add a table model near the shared infrastructure records in `models.py`:

```python
class AgentRun(SQLModel, table=True):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_user_created", "user_id", "created_at"),
        Index("ix_agent_runs_business", "module", "business_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(max_length=36, unique=True, index=True)
    user_id: int = Field(index=True)
    module: str = Field(max_length=32, index=True)
    business_id: str = Field(max_length=128, index=True)
    status: str = Field(default="pending", max_length=32, index=True)
    sequence: int = Field(default=0, ge=0)
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(TIMESTAMP(timezone=True)))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(TIMESTAMP(timezone=True), onupdate=func.now()))
    completed_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True)))
```

Add `AgentRun` to `REGISTERED_MODELS` exactly once.

- [ ] **Step 2: Add matching bootstrap SQL**

Add `agent_runs` to `server/init_schema.sql` with the same columns, unique `run_id`, ownership index, and `(module, business_id)` index. Do not add foreign keys from `agent_runs` to resource, path, or chat tables because `business_id` is intentionally polymorphic.

- [ ] **Step 3: Verify schema imports**

Run:

```bash
cd server
uv run python -c "from app.infra.models import AgentRun, REGISTERED_MODELS; assert AgentRun in REGISTERED_MODELS"
```

Expected: exit code 0.

- [ ] **Step 4: Commit the schema unit**

```bash
git add server/app/infra/models.py server/init_schema.sql
git commit -m "feat: persist global agent runs"
```

### Task 2: Implement the one global event infrastructure

**Files:**
- Create: `server/app/infra/agent_events.py`

- [ ] **Step 1: Define the only public event schema**

Define literals and the Pydantic model in `agent_events.py`:

```python
AgentModule = Literal["chat", "resource", "path"]
AgentEventType = Literal[
    "run.started",
    "agent.status",
    "tool.status",
    "artifact.ready",
    "content.delta",
    "run.completed",
    "run.failed",
]
AgentRunStatus = Literal["pending", "running", "completed", "failed", "skipped"]

class AgentEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    sequence: int = 0
    module: AgentModule
    business_id: str
    type: AgentEventType
    status: AgentRunStatus
    activity_id: str | None = None
    agent_id: str | None = None
    title: str = ""
    summary: str = ""
    progress: int | None = Field(default=None, ge=0, le=100)
    detail: dict[str, Any] = Field(default_factory=dict)
    elapsed_ms: int | None = Field(default=None, ge=0)
    timestamp: float = Field(default_factory=time.time)
```

Heartbeat remains an SSE comment (`: heartbeat`) rather than a second data shape. Every data-bearing SSE frame must be an `AgentEvent`.

- [ ] **Step 2: Implement a bounded run-scoped bus**

Implement `AgentEventBus` with four concrete coroutine methods:

```python
class AgentEventBus:
    def __init__(self, *, queue_size: int = 256, replay_size: int = 256) -> None:
        self._queue_size = queue_size
        self._replay_size = replay_size
        self._buffers: dict[str, deque[AgentEvent]] = {}
        self._subscribers: dict[str, list[asyncio.Queue[AgentEvent]]] = {}
        self._sequences: dict[str, int] = {}
        self._terminal_runs: set[str] = set()
        self._lock = asyncio.Lock()
```

Add `publish(event) -> AgentEvent`, `subscribe(run_id, after_sequence=0) -> tuple[Queue, list[AgentEvent]]`, `unsubscribe(run_id, queue) -> None`, and `close_run(run_id) -> None`. Do not expose the internal dictionaries outside this class.

Inside `publish`, allocate a strictly increasing sequence under `_lock`, append to a bounded `deque`, and use `put_nowait`. If a subscriber queue is full, remove its oldest queued event before inserting the newest event and log the drop. Reject events after `run.completed` or `run.failed`.

- [ ] **Step 3: Implement run creation and terminal persistence**

Expose four functions using `session_scope()`: `create_agent_run(user_id, module, business_id) -> AgentRun`, `get_owned_agent_run(run_id, user_id) -> AgentRun | None`, `mark_agent_run_started(run_id) -> None`, and `mark_agent_run_terminal(run_id, status, error="") -> None`. The terminal status argument accepts only `"completed"` or `"failed"`.

`create_agent_run` generates `str(uuid4())`. Terminal mutation must be idempotent and must never change a completed run into failed or a failed run into completed.

- [ ] **Step 4: Implement the emitter and encoder**

Implement `AgentEventEmitter` initialized with `run_id`, `module`, and `business_id`. Provide explicit methods `started`, `agent_status`, `tool_status`, `artifact_ready`, `content_delta`, `completed`, and `failed`. `content_delta` stores the token in `detail={"delta": text}`. `completed` and `failed` update the database before publishing the terminal event.

Use one wire event name for every frame:

```python
def encode_sse_event(event: AgentEvent) -> str:
    return f"event: agent.event\ndata: {event.model_dump_json()}\n\n"
```

Export one singleton:

```python
agent_event_bus = AgentEventBus()
```

- [ ] **Step 5: Verify the module compiles**

Run:

```bash
cd server
uv run python -m compileall -q -f app/infra/agent_events.py app/infra/models.py
```

Expected: exit code 0.

- [ ] **Step 6: Commit the infrastructure unit**

```bash
git add server/app/infra/agent_events.py
git commit -m "feat: add unified agent event infrastructure"
```

### Task 3: Expose the single subscription endpoint

**Files:**
- Create: `server/app/infra/agent_events_api.py`
- Modify: `server/app/routes.py`

- [ ] **Step 1: Add the authenticated SSE route**

Create an `APIRouter(prefix="/agent-runs", tags=["agent-runs"])` and implement:

```python
@router.get("/{run_id}/events")
async def stream_agent_run_events(
    run_id: str,
    after_sequence: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user_flexible),
):
    run = await get_owned_agent_run(run_id=run_id, user_id=current_user.id)
    if run is None:
        return HttpResponse.error(code=404, message="Agent 运行不存在或无权限")

    async def event_stream():
        queue, replay = await agent_event_bus.subscribe(run_id, after_sequence)
        try:
            for event in replay:
                yield encode_sse_event(event)
            if run.status in {"completed", "failed"} and not replay:
                yield encode_sse_event(build_terminal_event(run))
                return
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                yield encode_sse_event(event)
                if event.type in {"run.completed", "run.failed"}:
                    return
        finally:
            await agent_event_bus.unsubscribe(run_id, queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=SSE_HEADERS)
```

`build_terminal_event` must use the persisted run status and error summary, so a terminal run is still observable after process restart.

- [ ] **Step 2: Install the router once**

Import the new router in `server/app/routes.py` and include it once under `/api/v1/ai`.

- [ ] **Step 3: Verify route registration**

Run:

```bash
cd server
uv run python -c "from app.main import create_app; assert any('/api/v1/ai/agent-runs/{run_id}/events' == r.path for r in create_app().routes)"
```

Expected: exit code 0.

- [ ] **Step 4: Commit the endpoint unit**

```bash
git add server/app/infra/agent_events_api.py server/app/routes.py
git commit -m "feat: expose unified agent event stream"
```

### Task 4: Migrate intelligent tutoring to run creation plus global events

**Files:**
- Modify: `server/app/chat/routers/chat_router.py`
- Modify: `server/app/chat/service.py`
- Modify: `server/app/chat/agent/__init__.py`
- Modify: `server/app/chat/agent/nodes.py`
- Modify: `server/app/chat/schemas/agent.py`
- Modify: `server/app/chat/events.py`
- Modify: `server/app/infra/tool_excute.py`

- [ ] **Step 1: Change chat initiation from streaming response to run creation**

Replace `POST /chat/stream` with `POST /chat/runs`. Validate the same form input, create an `AgentRun(module="chat", business_id=effective_session)`, enqueue `run_chat_agent` as a background task with all validated arguments, and return:

```python
return HttpResponse.success(
    data={"run_id": run.run_id, "session_id": effective_session, "status": "pending"},
    status_code=202,
)
```

Delete `_sse_wrap`, the route-local `StreamingResponse`, and JSON SSE assembly.

- [ ] **Step 2: Make the chat service publish global events**

Add a background entry point with a request-scoped emitter:

```python
async def run_chat_agent(*, run_id: str, user_id: int, session_id: str, user_input: str, attachments: list[str], enable_web_search: bool, need_teaching_diagram: bool) -> None:
    emitter = AgentEventEmitter(run_id=run_id, module="chat", business_id=session_id)
    await emitter.started(title="智能辅导已开始")
    try:
        events = chat(
            user_id=user_id,
            session_id=session_id,
            user_input=user_input,
            attachments=attachments or None,
            enable_web_search=enable_web_search,
            need_teaching_diagram=need_teaching_diagram,
        )
        async for event in events:
            await publish_chat_event(emitter, event)
        await emitter.completed(title="回答完成")
    except Exception as exc:
        logger.exception("chat_agent_run_failed: run_id=%s", run_id)
        await emitter.failed(title="回答失败", summary="智能辅导暂时无法完成本次回答")
```

`publish_chat_event` maps answer tokens to `content.delta`, tool lifecycle to `tool.status`, attachment/workflow status to `agent.status`, diagrams to `artifact.ready`, and never sends raw exceptions or unsanitized tool output.

- [ ] **Step 3: Collapse chat's external event shape**

Remove `ChatStreamEventType` and `ChatStreamEvent` from `server/app/chat/schemas/agent.py`. Update the agent runner and nodes to accept an `AgentEventEmitter` or a narrow async callback that receives global `AgentEvent` fields. Preserve the existing database writes for UserMessage, AIMessage with tool calls, ToolMessage, attachment analysis, and tool invocation records.

- [ ] **Step 4: Reuse the existing safe activity builders**

Keep `server/app/chat/events.py` only as chat-specific presentation mapping. Its builders should return keyword arguments suitable for `AgentEventEmitter.tool_status` or `AgentEventEmitter.agent_status`; they must not define another event envelope.

Pass `run_id`/`activity_id` through `ToolExcute.execute` callbacks and emit `tool.status` with `running`, `completed`, or `failed` status. Do not add a second tool event bus.

- [ ] **Step 5: Verify chat compiles and existing focused checks pass**

Run:

```bash
cd server
uv run python -m compileall -q -f app/chat app/infra/tool_excute.py
uv run pytest -q tests/chat/test_tool_excute.py tests/chat/test_web_research_tools.py
```

Expected: compile succeeds and the focused existing tests pass.

- [ ] **Step 6: Commit the chat migration**

```bash
git add server/app/chat server/app/infra/tool_excute.py
git commit -m "refactor: route chat through global agent events"
```

### Task 5: Migrate resource generation and delete its event system

**Files:**
- Modify: `server/app/resource/api.py`
- Modify: `server/app/resource/orchestrator.py`
- Modify: `server/app/resource/runner.py`
- Modify: `server/app/resource/agents/base.py`
- Modify: `server/app/resource/workflow/execution.py`
- Modify: every `server/app/resource/**/*.py` importing `app.resource.events`
- Delete: `server/app/resource/events.py`

- [ ] **Step 1: Create a global run at each standalone resource entry point**

After creating the existing `GeneratedResource`, create `AgentRun(module="resource", business_id=str(resource_id))`. Pass its `run_id` into `run_multi_agent_generation` and return it alongside the resource ID:

```python
data={"resource_id": resource_id, "run_id": run.run_id, "status": "generating"}
```

Apply this to both multi-agent and single-agent resource creation endpoints.

- [ ] **Step 2: Replace the resource emitter**

Construct the global emitter in `orchestrator.py`:

```python
emitter = AgentEventEmitter(run_id=run_id, module="resource", business_id=str(resource_id))
```

Map existing semantics as follows:

- `agent.status`, `agent.snapshot`, and `agent.step` call `AgentEventEmitter.agent_status`.
- `agent.artifact_ready` calls `AgentEventEmitter.artifact_ready`.
- resource success calls `AgentEventEmitter.completed`.
- resource failure calls `AgentEventEmitter.failed`.
- heartbeat is owned only by the unified SSE endpoint.

Keep resource-specific metrics, dependency, phase, and artifact ID inside `detail`; preserve progress, agent ID, activity ID, and elapsed time in their common fields.

- [ ] **Step 3: Remove the old resource endpoint and implementation**

Delete `GET /resources/{resource_id}/events` from `server/app/resource/api.py`. Migrate all type-only imports to `app.infra.agent_events`, then delete `server/app/resource/events.py`. Do not move or merge `GeneratedResource`, `GeneratedResourceItem`, or `GeneratedResourceAgentRun` records.

- [ ] **Step 4: Verify no resource event infrastructure remains**

Run:

```bash
cd server
! rg -n "app\.resource\.events|ResourceEventBus|resource_event_bus|resource\.done" app/resource
uv run python -m compileall -q -f app/resource
```

Expected: no matches and compile succeeds.

- [ ] **Step 5: Commit the resource migration**

```bash
git add server/app/resource
git commit -m "refactor: route resource agents through global events"
```

### Task 6: Migrate path planning and delete its event system

**Files:**
- Modify: `server/app/path/api.py`
- Modify: `server/app/path/service.py`

- [ ] **Step 1: Create and return a path Agent run**

After `init_path_task`, create `AgentRun(module="path", business_id=str(path_id))`, pass `run_id` to `_run_generation_bg` and `PathService.run_generation`, and return:

```python
data={"id": path_id, "run_id": run.run_id, "status": "generating"}
```

- [ ] **Step 2: Publish planning progress through the global emitter**

Initialize one emitter per path generation. Replace every `path_event_bus.publish` call with `AgentEventEmitter.agent_status`. Use a stable activity ID such as `f"path-plan:{path_id}"`, `agent_id="path_planner"`, the existing message, and existing progress. Finish with `AgentEventEmitter.completed`; on exception update the existing `LearningPath.status` and call `AgentEventEmitter.failed` with a safe summary.

- [ ] **Step 3: Delete path-specific streaming code**

Remove `PathEventType`, `PathStatus`, `PathEvent`, `PathEventBus`, `path_event_bus`, and `GET /path-plan/{path_id}/events`. Remove now-unused `asyncio`, `Literal`, `BaseModel`, `Field`, and `StreamingResponse` imports. Do not modify path records, nodes, detail endpoints, or persistence relationships.

- [ ] **Step 4: Verify no path event infrastructure remains**

Run:

```bash
cd server
! rg -n "PathEvent|PathEventBus|path_event_bus|path\.done|path\.step" app/path
uv run python -m compileall -q -f app/path
```

Expected: no matches and compile succeeds.

- [ ] **Step 5: Commit the path migration**

```bash
git add server/app/path
git commit -m "refactor: route path planner through global events"
```

### Task 7: Add one frontend event type and subscriber

**Files:**
- Create: `src/shared/agent-events/model.ts`
- Create: `src/shared/agent-events/api.ts`

- [ ] **Step 1: Define the shared TypeScript contract**

Mirror the backend schema exactly:

```typescript
export type AgentModule = 'chat' | 'resource' | 'path'
export type AgentEventType =
  | 'run.started'
  | 'agent.status'
  | 'tool.status'
  | 'artifact.ready'
  | 'content.delta'
  | 'run.completed'
  | 'run.failed'

export type AgentRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped'

export interface AgentEvent {
  event_id: string
  run_id: string
  sequence: number
  module: AgentModule
  business_id: string
  type: AgentEventType
  status: AgentRunStatus
  activity_id: string | null
  agent_id: string | null
  title: string
  summary: string
  progress: number | null
  detail: Record<string, unknown>
  elapsed_ms: number | null
  timestamp: number
}
```

- [ ] **Step 2: Implement the only subscriber**

Implement `subscribeAgentRun` with `EventSource`, authentication query token, one `agent.event` listener, sequence de-duplication, and terminal close:

```typescript
export function subscribeAgentRun(
  runId: string,
  handlers: {
    onEvent: (event: AgentEvent) => void
    onError: (error: Event) => void
  },
): EventSource {
  let lastSequence = 0
  const token = getAuthToken()
  const query = new URLSearchParams()
  if (token) query.set('token', token)
  const source = new EventSource(`/api/v1/ai/agent-runs/${runId}/events?${query}`)
  source.addEventListener('agent.event', (message) => {
    const event = JSON.parse((message as MessageEvent).data) as AgentEvent
    if (event.sequence <= lastSequence) return
    lastSequence = event.sequence
    handlers.onEvent(event)
    if (event.type === 'run.completed' || event.type === 'run.failed') source.close()
  })
  source.onerror = handlers.onError
  return source
}
```

- [ ] **Step 3: Build-check the shared client**

Run `npm run build` from the repository root.

Expected: build succeeds after consumers are migrated in Tasks 8–10; temporary unused exports are acceptable until then.

- [ ] **Step 4: Commit the shared frontend unit**

```bash
git add src/shared/agent-events
git commit -m "feat: add shared agent run subscriber"
```

### Task 8: Migrate the intelligent tutoring frontend

**Files:**
- Modify: `src/features/chat/api/chat.ts`
- Modify: `src/features/chat/model/chat.ts`
- Modify: `src/features/chat/model/useChatStreamManager.ts`
- Modify: `src/features/chat/views/Tutor.vue`

- [ ] **Step 1: Replace `streamChat` with run creation**

Submit the same `FormData` to `/ai/chat/runs` through the normal HTTP client and return:

```typescript
ApiResponse<{ run_id: string; session_id: string; status: string }>
```

Remove chat's direct use of `createSseStream`, `StreamChatEvent`, and the old POST stream callbacks.

- [ ] **Step 2: Subscribe after the run is created**

In the chat send flow, call `subscribeAgentRun` with the returned `run_id` and concrete `onEvent` and `onError` handlers. Map:

- `content.delta`: append `String(event.detail.delta ?? '')` to the answer.
- `tool.status` and attachment/workflow `agent.status`: update `AgentActivityCard` by `activity_id`.
- `artifact.ready`: attach the diagram or artifact detail.
- `run.completed`: finalize the pending answer and reload any required history.
- `run.failed`: mark the activity failed and show the safe summary.

Keep the existing behavior where the activity card auto-collapses when the first answer delta arrives and remains expandable afterwards.

- [ ] **Step 3: Remove legacy event handlers**

Delete branches for `token`, `done`, `agent_status`, `diagram`, and status events from the old stream manager and `Tutor.vue`. Preserve message/history rendering and the persisted `agent_activities` restoration path.

- [ ] **Step 4: Commit the chat frontend migration**

```bash
git add src/features/chat
git commit -m "refactor: consume unified chat agent events"
```

### Task 9: Migrate the resource frontend

**Files:**
- Modify: `src/features/resource/api/resource.ts`
- Modify: `src/features/resource/model/resource.ts`
- Modify: `src/features/resource/views/ResourceGenerator.vue`
- Modify: other source files importing `ResourceStreamEvent`

- [ ] **Step 1: Return and subscribe by `run_id`**

Change resource creation response types to include `run_id`. Remove `streamResourceEvents` and use `subscribeAgentRun(run_id)` after creation.

- [ ] **Step 2: Map global events to the existing resource DAG UI**

Use `event.agent_id`, `event.status`, `event.progress`, `event.title`, `event.summary`, `event.elapsed_ms`, and `event.detail` to update existing DAG nodes and logs. Handle `artifact.ready` as the prior artifact-ready animation. Handle `run.completed` by loading the generated resource and `run.failed` by showing the existing failure state.

- [ ] **Step 3: Delete the resource event envelope**

Remove `ResourceStreamEventName` and `ResourceStreamEvent` from `src/features/resource/model/resource.ts`. Where UI helpers need a type, accept the global `AgentEvent`; do not create a resource alias reproducing the envelope.

- [ ] **Step 4: Commit the resource frontend migration**

```bash
git add src/features/resource
git commit -m "refactor: consume unified resource agent events"
```

### Task 10: Migrate the path-planning frontend

**Files:**
- Modify: `src/features/learning-path/api/path.ts`
- Modify: `src/features/learning-path/model/path.ts`
- Modify: `src/features/learning-path/views/LearningPathOverview.vue`

- [ ] **Step 1: Include `run_id` in the creation response**

Update `CreateLearningPathResponse` to contain `run_id: string` alongside the existing path ID and status.

- [ ] **Step 2: Replace the path EventSource**

Delete the direct `/path-plan/{pathId}/events` connection and event-name listeners. Subscribe using the returned `run_id`. For `agent.status`, update progress and append the title/summary message. For `run.completed`, set progress to 100 and reload the path. For `run.failed`, show the safe summary and reload the failed path state.

- [ ] **Step 3: Commit the path frontend migration**

```bash
git add src/features/learning-path
git commit -m "refactor: consume unified path agent events"
```

### Task 11: Remove legacy protocols and verify the complete source migration

**Files:**
- Modify only source files reported by the scans below.

- [ ] **Step 1: Remove all legacy backend references**

Run:

```bash
cd server
rg -n "ResourceEventBus|resource_event_bus|PathEventBus|path_event_bus|ChatStreamEvent|_sse_wrap|/resources/\{resource_id\}/events|/path-plan/\{path_id\}/events" app
```

Expected: no output. Remove source references if any remain; do not edit tests.

- [ ] **Step 2: Assert one backend event type, bus, encoder, and route**

Run:

```bash
cd server
test "$(rg -l '^class AgentEvent\(' app --glob '*.py' | wc -l | tr -d ' ')" = "1"
test "$(rg -l '^class AgentEventBus' app --glob '*.py' | wc -l | tr -d ' ')" = "1"
test "$(rg -l '^def encode_sse_event' app --glob '*.py' | wc -l | tr -d ' ')" = "1"
test "$(rg -n 'agent-runs/.+events' app --glob '*.py' | wc -l | tr -d ' ')" = "1"
```

Expected: all commands exit 0.

- [ ] **Step 3: Remove all legacy frontend references**

Run from the repository root:

```bash
rg -n "ResourceStreamEvent|StreamChatEvent|createSseStream|resources/.+/events|path-plan/.+/events" src
```

Expected: no module-specific agent stream references. `createSseStream` may remain only if used by an unrelated non-Agent feature; chat must not import it.

- [ ] **Step 4: Run backend source and focused regression checks**

```bash
cd server
uv run python -m compileall -q -f app
uv run pytest -q tests/chat/test_tool_excute.py tests/chat/test_web_research_tools.py
```

Expected: compile succeeds and focused existing tests pass. Do not claim the full backend suite passes unless it is separately run; the repository documents three unrelated pre-existing failures.

- [ ] **Step 5: Run the only frontend check**

```bash
cd ../
npm run build
```

Expected: `vue-tsc` and Vite build succeed; Vite chunk-size warnings are non-fatal.

- [ ] **Step 6: Check whitespace and accidental test edits**

```bash
git diff --check
git diff --name-only -- server/tests src -- ':!src/**/*.ts' ':!src/**/*.vue'
```

Expected: no whitespace errors and no test files newly modified by this implementation.

- [ ] **Step 7: Commit final cleanup if needed**

```bash
git add server/app server/init_schema.sql src
git commit -m "refactor: complete unified agent event migration"
```

Only create this commit when Task 11 produced cleanup changes not already included in earlier focused commits.
