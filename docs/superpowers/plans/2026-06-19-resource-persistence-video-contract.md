# Resource Persistence and Video Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist only standalone generation tasks and agents' terminal outputs, make `RichVideoPlan` the sole backend-to-Remotion contract, strengthen multi-agent terminal behavior, and remove obsolete compatibility code.

**Architecture:** LangGraph keeps teaching plans, handoffs, metrics, and dependency data in `ParentState`; the repository writes only minimal task state and one terminal item per selected agent. The Video agent emits the renderer's strict schema directly, and Remotion validates and consumes it without normalization or legacy aliases. `resource` and `path` continue to share agent infrastructure but retain separate persistence and APIs.

**Tech Stack:** Python 3.13, FastAPI, SQLModel, Pydantic v2, LangGraph, pytest/pytest-asyncio, TypeScript, React, Remotion, Zod.

---

## File Map

- `server/app/infra/models.py`: minimal standalone task and resource-item columns.
- `server/init_schema.sql`: bootstrap schema matching the SQLModel definitions.
- `server/app/resource/persistence/repository.py`: terminal-result persistence without collaboration fields.
- `server/app/resource/persistence/mappers.py`: direct JSON/text mapping and response DTO conversion.
- `server/app/resource/persistence/__init__.py`: export only live mapper functions.
- `server/app/resource/schemas/response.py`: public item shape without runtime collaboration data.
- `server/app/resource/service.py`: minimal task detail response and terminal status update.
- `server/app/resource/workflow/nodes.py`: runtime-only handoffs and exactly-once terminal persistence.
- `server/app/resource/agents/video.py`: canonical `RichVideoPlan` models and builder.
- `video-render/src/schema/videoPlanSchema.ts`: strict renderer schema.
- `video-render/src/MainVideo.tsx`: consume parsed plans directly.
- `video-render/src/Root.tsx`: validate metadata input without compatibility fallbacks.
- `video-render/src/utils/normalizePlan.ts`: delete after all callers are removed.
- `server/tests/resource/`: backend contract and workflow regression tests.
- `video-render/src/schema/videoPlanSchema.test.ts`: contract test executed with Node's test runner after adding a lightweight test script.

### Task 1: Lock the Minimal Persistence Schema

**Files:**
- Modify: `server/tests/resource/test_resource_contract.py`
- Modify: `server/app/infra/models.py`
- Modify: `server/init_schema.sql`

- [ ] **Step 1: Replace the old persistence assertions with failing minimal-column tests**

```python
def test_generated_resource_has_only_task_columns():
    assert set(GeneratedResource.__table__.columns.keys()) == {
        "id", "user_id", "learning_need", "selected_agents", "source",
        "status", "error_message", "created_at", "updated_at",
    }


def test_generated_resource_item_has_only_terminal_output_columns():
    expected = {
        "id", "resource_id", "user_id", "agent_type", "content_format",
        "title", "summary", "generated_by", "content_json", "content_text",
        "status", "error_message", "created_at", "updated_at",
    }
    assert set(GeneratedResourceItem.__table__.columns.keys()) == expected
    assert set(GeneratedResourceItem.__table__.columns.keys()) == set(
        _table_columns("generated_resource_items")
    )
```

Add `_table_columns()` beside `_table_sql()` to parse the table definition and compare exact column names, rather than checking only that model columns appear somewhere in SQL.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd server && uv run pytest tests/resource/test_resource_contract.py -q`

Expected: failures list `teaching_plan`, `review_result`, `metrics`, `downstream_context`, and the other obsolete columns.

- [ ] **Step 3: Remove runtime and compatibility columns from both schema sources**

Keep these SQLModel fields only:

```python
class GeneratedResource(SQLModel, table=True):
    id: int | None
    user_id: int
    learning_need: str | None
    selected_agents: list[str] | None
    source: str | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class GeneratedResourceItem(SQLModel, table=True):
    id: int | None
    resource_id: int
    user_id: int
    agent_type: str
    content_format: str
    title: str | None
    summary: str | None
    generated_by: str | None
    content_json: dict[str, Any] | list[Any] | None
    content_text: str | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime
```

Retain only the content GIN index and the `(resource_id, agent_type)` and `(user_id, created_at)` indexes. Apply the same exact fields, indexes, and comments in `server/init_schema.sql`; do not add `ALTER TABLE`, legacy readers, or migration fallbacks.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `cd server && uv run pytest tests/resource/test_resource_contract.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit the schema slice**

```bash
git add server/app/infra/models.py server/init_schema.sql server/tests/resource/test_resource_contract.py
git commit -m "refactor: shrink resource persistence schema"
```

### Task 2: Persist Raw Agent Content and Terminal Failures

**Files:**
- Modify: `server/tests/resource/test_resource_refactoring.py`
- Modify: `server/app/resource/persistence/repository.py`
- Modify: `server/app/resource/persistence/mappers.py`
- Modify: `server/app/resource/persistence/__init__.py`

- [ ] **Step 1: Add failing tests for direct content storage**

```python
def test_content_fields_store_only_generated_content():
    structured = AgentResult(
        success=True, content='{"scenes": []}', file_type="json",
        title="视频", summary="摘要", metadata={"agent_id": "video", "trace": "drop"},
    )
    text = AgentResult(
        success=True, content="# 正文", file_type="markdown",
        title="讲义", metadata={"agent_id": "content"},
    )

    assert content_fields(structured) == ({"scenes": []}, None)
    assert content_fields(text) == (None, "# 正文")
```

Add an async repository test using the existing fake session fixture which asserts that a saved success row has no metadata/runtime attributes, and a failed `AgentResult` creates `status="failed"`, `error_message=result.error`, and no content.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `cd server && uv run pytest tests/resource/test_resource_refactoring.py -q`

Expected: `content_fields` is missing and `save_agent_result()` rejects failures.

- [ ] **Step 3: Replace envelope persistence with a direct mapper**

```python
def content_fields(result: AgentResult) -> tuple[Any | None, str | None]:
    if result.file_type.lower() in {"markdown", "mermaid", "text", "code"}:
        return None, result.content if isinstance(result.content, str) else json.dumps(result.content, ensure_ascii=False)
    if isinstance(result.content, str):
        try:
            return json.loads(result.content), None
        except json.JSONDecodeError:
            return None, result.content
    return result.content, None
```

Change `save_agent_result()` to derive `agent_id` from `result.metadata["agent_id"]`, map success content with `content_fields()`, and persist failures with empty content. Remove `depends_on_agents` from its signature. Delete `db_item_to_agent_result()` because aggregate agents consume `state["results"]`, not database rows.

- [ ] **Step 4: Map database rows without envelope or runtime fallbacks**

```python
def db_item_to_resource_item(item: GeneratedResourceItemModel) -> GeneratedResourceItem:
    return GeneratedResourceItem(
        id=str(item.id),
        type=item.agent_type,
        title=item.title or f"学习资源 - {item.agent_type}",
        format=item.content_format,
        content=item.content_json if item.content_json is not None else item.content_text,
        summary=item.summary or "",
        status=item.status,
        error_message=item.error_message,
        created_at=item.created_at.isoformat() if item.created_at else None,
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )
```

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run: `cd server && uv run pytest tests/resource/test_resource_refactoring.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit the repository slice**

```bash
git add server/app/resource/persistence server/tests/resource/test_resource_refactoring.py
git commit -m "refactor: persist only agent terminal content"
```

### Task 3: Remove Runtime Fields from Public History Responses

**Files:**
- Modify: `server/tests/resource/test_public_service_surface.py`
- Modify: `server/app/resource/schemas/response.py`
- Modify: `server/app/resource/service.py`
- Modify: `src/features/resource/api/resource-history.ts`
- Modify: `src/features/resource/views/ResourceResult.vue`

- [ ] **Step 1: Add a failing DTO contract test**

```python
def test_generated_resource_item_dto_exposes_only_terminal_output():
    assert set(GeneratedResourceItem.model_fields) == {
        "id", "type", "title", "format", "content", "summary", "status",
        "error_message", "created_at", "updated_at",
    }
```

Add a service-detail assertion that the parent payload contains `id`, `learning_need`, `selected_agents`, `source`, `status`, `error_message`, timestamps, and `resources`, but not `teaching_plan`, `failed_agents`, `review_result`, or workflow metadata.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd server && uv run pytest tests/resource/test_public_service_surface.py -q`

Expected: obsolete DTO fields and task response fields are reported.

- [ ] **Step 3: Shrink backend DTO and detail response**

Remove `metrics`, `downstream_context`, `execution_report`, and `metadata` from `GeneratedResourceItem`. In `ResourceService`, stop reading removed model attributes and derive failed agent IDs from terminal items whose status is `failed` only if the current UI still needs a failure summary.

- [ ] **Step 4: Update frontend history types and rendering atomically**

Remove `review_result`, persisted metrics, handoffs, execution report, and persisted metadata from history types. `ResourceResult.vue` must render failure state from item `status/error_message` and parent `status/error_message`, not from removed response aliases.

- [ ] **Step 5: Verify backend and frontend GREEN**

Run: `cd server && uv run pytest tests/resource/test_public_service_surface.py -q`

Run: `npm run build`

Expected: both commands pass.

- [ ] **Step 6: Commit the API slice**

```bash
git add server/app/resource/schemas/response.py server/app/resource/service.py server/tests/resource/test_public_service_surface.py src/features/resource/api/resource-history.ts src/features/resource/views/ResourceResult.vue
git commit -m "refactor: expose minimal resource history contract"
```

### Task 4: Make Multi-Agent Terminal Persistence Exactly Once

**Files:**
- Modify: `server/tests/resource/test_agent_integration.py`
- Modify: `server/tests/resource/test_handoff_coverage.py`
- Modify: `server/app/resource/workflow/nodes.py`
- Modify: `server/app/resource/service.py`

- [ ] **Step 1: Add failing workflow behavior tests**

```python
@pytest.mark.asyncio
async def test_aggregate_agents_use_state_results_without_database_reload(monkeypatch):
    monkeypatch.setattr(ResourceRepository, "list_resource_items", forbidden_call)
    result = await _run_aggregation_agent(state_with_successful_base_results(), agent_id="video", running_message="video")
    assert result["results"]["video"].success is True


@pytest.mark.asyncio
async def test_each_selected_agent_persists_one_terminal_item():
    saved = await run_workflow_with_one_success_and_one_failure()
    assert [(item.agent_type, item.status) for item in saved] == [
        ("content", "finished"), ("video", "failed")
    ]
```

Use existing workflow fixtures and fake emitters; do not mock `AgentResult` behavior.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `cd server && uv run pytest tests/resource/test_agent_integration.py tests/resource/test_handoff_coverage.py -q`

Expected: database reconstruction is still imported or failure results are not persisted.

- [ ] **Step 3: Keep collaboration state in LangGraph and persist only at terminal nodes**

Remove the `db_item_to_agent_result` import. Pass `state["results"]` and `collect_successful_handoffs()` directly to PPT/Video. Change `persist_result_and_emit_artifact()` to persist both success and failure terminal results and ensure each node owns exactly one persistence call. Remove `depends_on_agents` from workflow calls.

When an aggregate agent has no successful required handoff, return:

```python
AgentResult(
    success=False,
    content="",
    file_type="json",
    title=f"{agent_id} 生成失败",
    error="缺少可用的上游 Agent 结果",
    metadata={"agent_id": agent_id},
)
```

- [ ] **Step 4: Store only parent terminal status**

Update task completion without persisting `TeachingPlan`, coverage reports, failed-agent arrays, or workflow metrics. Preserve the current status decision: all success → `completed`; mixed → `partial_failed`; none success → `failed`.

- [ ] **Step 5: Run resource workflow tests and verify GREEN**

Run: `cd server && uv run pytest tests/resource/test_agent_integration.py tests/resource/test_handoff_coverage.py tests/resource/test_video_service_orchestration.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit the workflow slice**

```bash
git add server/app/resource/workflow/nodes.py server/app/resource/service.py server/tests/resource/test_agent_integration.py server/tests/resource/test_handoff_coverage.py
git commit -m "refactor: keep agent handoffs in workflow state"
```

### Task 5: Emit the Canonical RichVideoPlan from Python

**Files:**
- Modify: `server/tests/resource/test_video_agent.py`
- Modify: `server/app/resource/agents/video.py`
- Modify: `server/app/resource/prompts/video_outline.md`
- Modify: `server/app/resource/prompts/video_scene.md`

- [ ] **Step 1: Replace `video/v1` tests with strict canonical-contract tests**

```python
def test_video_plan_rejects_legacy_keys():
    with pytest.raises(ValidationError):
        RichVideoPlan.model_validate({"schema_version": "video/v1", "scenes": []})


def test_video_plan_has_renderer_top_level_shape():
    plan = RichVideoPlan.model_validate(_valid_rich_video_plan())
    assert set(plan.model_dump(mode="json")) == {
        "meta", "global_style", "render_config", "audio", "scenes"
    }
    assert set(plan.scenes[0].model_dump(mode="json", exclude_none=True)) <= {
        "id", "type", "duration_seconds", "title", "narration", "visual",
        "audio_src", "transition", "caption_words",
    }
```

The fixture must use one of the renderer's declared scene types and seconds, not milliseconds.

- [ ] **Step 2: Run the video tests and verify RED**

Run: `cd server && uv run pytest tests/resource/test_video_agent.py -q`

Expected: `RichVideoPlan` is absent and legacy `VideoPayload` still validates.

- [ ] **Step 3: Replace backend output models with strict renderer models**

Define Pydantic models with `model_config = ConfigDict(extra="forbid")` for `VideoMeta`, `GlobalStyle`, `RenderConfig`, `BgmConfig`, `CaptionWord`, `RichVideoScene`, and `RichVideoPlan`. Use a `Literal` union for the 13 renderer scene types and five transition types. Keep internal material digest and outline types only where they directly support generation.

- [ ] **Step 4: Build scenes directly in seconds**

Convert TTS timing once when constructing `RichVideoScene`:

```python
scene = RichVideoScene(
    id=draft.id,
    type=draft.type,
    duration_seconds=round(tts_duration + 0.5, 3),
    title=draft.title,
    narration=draft.narration,
    visual=draft.visual,
    audio_src=audio_src,
    transition=draft.transition,
    caption_words=caption_words or None,
)
```

Return `json.dumps(plan.model_dump(mode="json", exclude_none=True), ensure_ascii=False)` as `AgentResult.content`. Set only `metadata={"agent_id": "video"}`; do not persist or advertise a schema-version alias.

- [ ] **Step 5: Tighten prompts to request only canonical scene fields**

Remove instructions for `scene_id`, `index`, `role`, `visual_type`, captions arrays, screen text, visual prompt, interaction prompt, source agents, start offsets, and millisecond durations. Require `id`, declared `type`, title, narration, template-specific `visual`, transition, and seconds.

- [ ] **Step 6: Run video tests and verify GREEN**

Run: `cd server && uv run pytest tests/resource/test_video_agent.py tests/resource/test_video_tts.py -q`

Expected: all tests pass with no `video/v1` assertions.

- [ ] **Step 7: Commit the backend video slice**

```bash
git add server/app/resource/agents/video.py server/app/resource/prompts/video_outline.md server/app/resource/prompts/video_scene.md server/tests/resource/test_video_agent.py
git commit -m "refactor: emit canonical rich video plans"
```

### Task 6: Enforce the Same Strict Contract in Remotion

**Files:**
- Create: `video-render/src/schema/videoPlanSchema.test.ts`
- Modify: `video-render/src/schema/videoPlanSchema.ts`
- Modify: `video-render/src/MainVideo.tsx`
- Modify: `video-render/src/Root.tsx`
- Modify: `video-render/package.json`
- Delete: `video-render/src/utils/normalizePlan.ts`

- [ ] **Step 1: Add a failing schema test and test command**

```typescript
import assert from 'node:assert/strict'
import test from 'node:test'
import { richVideoPlanSchema } from './videoPlanSchema'

test('rejects backend legacy aliases', () => {
  const result = richVideoPlanSchema.safeParse({
    schema_version: 'video/v1',
    scenes: [{ scene_id: 's1', visual_type: 'card', duration_ms: 1000 }],
  })
  assert.equal(result.success, false)
})

test('accepts the canonical renderer contract', () => {
  assert.equal(richVideoPlanSchema.safeParse(validPlan).success, true)
})
```

Add `"test": "tsx --test src/schema/videoPlanSchema.test.ts"` and `tsx` as a dev dependency.

- [ ] **Step 2: Install the declared dependency and verify RED**

Run: `cd video-render && npm install`

Run: `cd video-render && npm test`

Expected: the legacy payload passes because the current schemas are optional and catch-all.

- [ ] **Step 3: Make every required field required and every object strict**

Use `z.strictObject()` and the existing enums. Add strict caption-word and BGM schemas. Export the inferred type:

```typescript
export const richVideoPlanSchema = z.strictObject({
  meta: videoMetaSchema,
  global_style: globalStyleSchema,
  render_config: renderConfigSchema,
  audio: bgmConfigSchema.optional(),
  scenes: z.array(richVideoSceneSchema).min(1),
})

export type RichVideoPlanInput = z.infer<typeof richVideoPlanSchema>
```

- [ ] **Step 4: Remove normalization and consume parsed values directly**

In `MainVideo.tsx`, replace `normalizePlan(result.data)` with `result.data`. In `Root.tsx`, parse either input props or `defaultPlan` with `richVideoPlanSchema.parse()` and calculate metadata directly. Do not catch validation errors with fabricated dimensions or durations; invalid input must fail the render.

- [ ] **Step 5: Delete the compatibility module and verify no references remain**

Run: `rtk rg -n "normalizePlan|scene_id|visual_type|duration_ms|schema_version" video-render/src`

Expected: no production matches; test fixtures may mention aliases only to assert rejection.

- [ ] **Step 6: Verify renderer GREEN**

Run: `cd video-render && npm test && npm run lint && npm run build`

Expected: tests, TypeScript/ESLint, and Remotion bundle pass.

- [ ] **Step 7: Commit the renderer slice**

```bash
git add video-render/package.json video-render/package-lock.json video-render/src
git commit -m "refactor: remove legacy video normalization"
```

### Task 7: Delete Dead Resource Compatibility Code

**Files:**
- Modify: `server/app/resource/schemas/__init__.py`
- Modify: `server/app/resource/events.py`
- Modify: `server/app/resource/api.py`
- Modify: `src/features/resource/model/resource.ts`
- Modify: `src/features/resource/api/resource.ts`
- Delete: `server/app/resource/prompts/review.md`
- Modify: affected tests under `server/tests/resource/`

- [ ] **Step 1: Establish deletion candidates with production reference searches**

Run:

```bash
rtk rg -n "generate_from_tutor_context|db_item_to_agent_result|content_envelope|review\.md|legacy|兼容" server/app server/tests/resource
rtk rg -n "from app\.resource\.schemas import|app\.resource\.schemas\." server/app server/tests/resource
```

Record each candidate's live callers before deletion. Do not delete a shared schema used by `path`.

- [ ] **Step 2: Add or update import-surface tests first**

```python
def test_resource_public_exports_do_not_include_legacy_adapters():
    import app.resource.persistence as persistence
    assert not hasattr(persistence, "content_envelope")
    assert not hasattr(persistence, "db_item_to_agent_result")
```

Update event tests to assert `agent.status` and `resource.done`, alongside `agent.snapshot`, `agent.step`, `agent.heartbeat`, and `agent.artifact_ready`.

- [ ] **Step 3: Run tests and verify RED**

Run: `cd server && uv run pytest tests/resource/test_public_service_surface.py tests/resource/test_events.py tests/resource/test_resource_request_schema.py -q`

Expected: compatibility exports or event aliases remain.

- [ ] **Step 4: Delete only confirmed dead code**

Delete the unwired `VideoAgent.generate_from_tutor_context`, obsolete persistence exports, and `server/app/resource/prompts/review.md`. Rename `agent` to `agent.status` and `done` to `resource.done` in `events.py`, the SSE endpoint, frontend stream types, and EventSource listeners in one change. Keep code used by `NodeInput` or path generation even when standalone resource no longer calls it.

- [ ] **Step 5: Verify references and focused tests GREEN**

Run: `rtk rg -n 'generate_from_tutor_context|db_item_to_agent_result|content_envelope|normalizePlan|video/v1|event_type="agent"|event_type="done"' server/app video-render/src`

Expected: no production matches.

Run: `cd server && uv run pytest tests/resource/ -q`

Run: `npm run build`

Expected: all resource tests and the frontend build pass.

- [ ] **Step 6: Commit dead-code removal**

```bash
git add server/app/resource server/tests/resource src/features/resource/model/resource.ts src/features/resource/api/resource.ts
git commit -m "refactor: remove obsolete resource compatibility code"
```

### Task 8: Full Verification and Contract Audit

**Files:**
- Verify only; corrections belong to the task that introduced the regression

- [ ] **Step 1: Verify standalone/path separation**

Run: `cd server && uv run pytest tests/resource/test_resource_source_separation.py tests/resource/test_agent_dual_entry.py -q`

Expected: all tests pass and no `PathNodeResource` assertion changes.

- [ ] **Step 2: Run the complete resource suite**

Run: `cd server && uv run pytest tests/resource/ -q`

Expected: all tests pass.

- [ ] **Step 3: Run backend suite and classify only documented failures**

Run: `cd server && uv run pytest -q`

Expected: no new failures. The only permitted failures are the documented pre-existing chat tests in `AGENTS.md`.

- [ ] **Step 4: Run both builds**

Run: `npm run build`

Run: `cd video-render && npm test && npm run lint && npm run build`

Expected: all commands pass.

- [ ] **Step 5: Audit forbidden compatibility and persistence fields**

Run:

```bash
rtk rg -n "metadata_json|downstream_context|depends_on_agents|execution_report|schema_version|scene_id|visual_type|duration_ms|normalizePlan" server/app/resource server/app/infra/models.py server/init_schema.sql video-render/src
```

Expected: runtime-only `downstream_context` remains in AgentResult/workflow/agent code; removed persistence and legacy Video names have no production matches.

- [ ] **Step 6: Check for accidental changes and whitespace errors**

```bash
rtk git status --short
rtk git diff --check
```

Expected: only pre-existing unrelated user changes are listed, and `git diff --check` reports no whitespace errors.
