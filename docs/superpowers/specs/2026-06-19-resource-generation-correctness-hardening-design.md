# Resource Generation Correctness Hardening Design

**Date:** 2026-06-19

**Status:** Approved for implementation planning

## 1. Objective

Repair the current standalone resource-generation implementation so that it starts reliably, preserves successful Agent artifacts, rejects invalid PPT output before persistence, and contains no legacy compatibility, fabricated review output, placeholder content, or fallback rendering.

Planning remains the only fatal Agent stage. Every selected non-Planning Agent is independently generated, validated, committed, and reported. A successful database commit is the business success boundary; event publication is observational and can never reverse a committed success.

The change keeps standalone `resource` and learning-path `path` records, detail pages, and persistence models separate. Shared Agent classes may remain dual-entry, but this work must not merge the two domains.

## 2. Confirmed Constraints

1. Modify source code and source-owned SQL/docs only. Do not modify files under `server/tests/`.
2. Do not add compatibility readers, aliases, converters, dual event names, upserts, fallback renderers, default content, review Agents, or repair Agents.
3. Do not redesign LLM JSON mode, retry policy, prompt fallback, or provider behavior in `server/app/infra/llm.py`.
4. The only permitted failure recovery is orchestration isolation: a non-Planning Agent may fail without cancelling its siblings.
5. Planning generation or TeachingPlan validation failure terminates the complete run.
6. Every valid Agent artifact is saved immediately after that Agent finishes.
7. Failed Agents create no `GeneratedResourceItem` row and no result card.
8. PPT and Video run independently using TeachingPlan plus the successful base-Agent handoffs that actually exist.
9. Existing databases receive the new uniqueness rule through one explicit one-time SQL migration. Startup performs no schema repair.
10. Resource and path persistence remain separate.

## 3. Selected Architecture

Three repair strategies were considered:

- Patch individual exceptions in place. This is fast but preserves duplicated execution logic and leaves future state divergence likely.
- Introduce executor, lifecycle, event, persistence, and result service classes. This makes boundaries explicit but over-engineers a small workflow.
- Keep the current LangGraph topology and add one small non-Planning execution boundary, strict contract functions, and a narrow repository finalizer.

The third strategy is selected. It fixes the lifecycle without introducing a new framework or class hierarchy.

The dependency direction is:

```text
schemas/constants
      ↓
agents     persistence
      \     /
       workflow
          ↓
     orchestrator/API
```

Persistence must not import `app.resource.workflow`. Workflow may import persistence. This rule removes the current circular import and prevents it from returning.

## 4. Workstream Order

Implementation must proceed in this order because later stages depend on earlier correctness:

1. Restore application imports and remove invalid source APIs.
2. Correct Agent commit, event, and finalization semantics.
3. apply the database uniqueness migration and align both schema sources.
4. Enforce the complete PPT template contract.
5. Remove frontend review, fallback, compatibility, and invalid-card behavior.
6. Remove scoped dead code and duplicated definitions.
7. Run source-only verification without editing tests.

## 5. Dependency and Startup Repair

### 5.1 Circular import

`ResourceRepository` must not import `AgentFailure` from `workflow.state`. The repository does not need failure details; it only needs the final list of failed Agent IDs and the set of expected selected Agent IDs.

Keep `AgentFailure` in `workflow/state.py` as workflow-only data. Change the repository finalizer to accept primitives such as:

```python
async def finalize_generation(
    *,
    user_id: int,
    resource_id: int,
    selected_agent_ids: list[str],
    successful_agent_ids: set[str],
    failed_agent_ids: set[str],
    teaching_plan: TeachingPlan,
    coverage_report: CoverageReport | None,
) -> str:
    ...
```

`CoverageReport` must be represented at the repository boundary as `dict[str, list[str]] | None`; persistence must not import its workflow type.

Delete the unused `db_item_to_agent_result` import from `workflow/nodes.py`. Aggregation consumes `ParentState.results`, never reconstructed database rows.

### 5.2 Invalid public service method

Delete `ResourceService.save_generation_results()` if production reference search confirms no caller. Do not repair an unused wrapper merely to preserve an obsolete API. The workflow calls `ResourceRepository.finalize_generation()` directly.

### 5.3 Startup acceptance

Before any behavioral work proceeds, both imports must succeed:

```bash
rtk env UV_CACHE_DIR=/tmp/codex-uv-cache uv run python -c "from app.main import app; print(type(app).__name__)"
rtk env UV_CACHE_DIR=/tmp/codex-uv-cache uv run python -c "from app.resource.service import ResourceService; print(ResourceService.__name__)"
```

## 6. Workflow State and Agent Lifecycle

### 6.1 State separation

`ParentState.results` contains only successful, validated, committed `AgentResult` objects. `ParentState.failures` contains only failures from selected non-Planning Agents:

```python
class AgentFailure(TypedDict):
    agent_id: str
    stage: Literal["generation", "validation", "persistence"]
    error_type: str
    message: str
```

Remove `event` from the failure-stage literal because event publication cannot make an Agent fail.

Reducers merge values by Agent ID. A reducer must reject or log duplicate outcomes instead of silently allowing a later branch to overwrite an earlier outcome.

### 6.2 Planning boundary

Planning runs outside the isolated non-Planning helper. It must:

1. invoke the Planning Agent;
2. reject `success=False`;
3. require a valid `TeachingPlan`;
4. return the TeachingPlan;
5. allow generation and validation exceptions to escape to the orchestrator.

Planning events are observational. A failed event sink is logged but does not replace a valid Planning result with a Planning failure.

### 6.3 Non-Planning execution helper

Use one small helper in `workflow/nodes.py` rather than duplicated worker and aggregation lifecycle code. Its business sequence is:

```text
invoke Agent
  -> validate AgentResult
  -> validate Agent-specific contract
  -> commit GeneratedResourceItem
  -> return successful result to LangGraph
  -> publish artifact_ready observationally
```

Generation, validation, and persistence exceptions are caught at this boundary and converted to `AgentFailure`. Sibling branches continue.

The helper must not catch `BaseException`, cancellation, or graph-control exceptions. It catches ordinary `Exception` from the current Agent only.

### 6.4 Validation before persistence

Every non-Planning Agent must satisfy:

- `result.success is True`;
- `result.content` is non-empty;
- `result.metadata["agent_id"]` exactly equals the scheduled Agent ID;
- `agent_id` belongs to the registered selected Agent set;
- base Agents contain a valid `downstream_context`;
- every `covered_outline_id` exists in the current TeachingPlan;
- PPT and Video satisfy their strict artifact contracts.

No validation function may filter, coerce, replace, or synthesize invalid values.

### 6.5 Event isolation

All event calls use a single observation-only function that catches an event-sink exception, logs it with `event=resource_event_publish_failed`, and returns. Event failure never changes `results`, `failures`, persistence, parent status, or sibling scheduling.

Database commit and `artifact_ready` publication must be two separate `try` boundaries:

```text
try database commit
except -> Agent persistence failure
else -> Agent business success

try artifact_ready
except -> log observation failure only
```

This rule applies to base Agents, PPT, Video, final Agent status events, and the terminal event.

## 7. Persistence and Terminal State

### 7.1 Immediate artifact persistence

`save_agent_result()` must:

- require successful, non-empty content;
- require the exact scheduled `agent_id` as an explicit argument instead of trusting metadata alone;
- verify the parent resource belongs to `user_id` before inserting;
- insert exactly one row for `(resource_id, agent_type)`;
- commit and refresh;
- roll back and re-raise on failure;
- never upsert, replace, or create a failed row.

Application-level `asyncio.Lock` objects are not correctness controls because repository instances are session-scoped. Keep no misleading per-instance write-lock abstraction. Database transactions and the unique constraint provide the real guarantee.

### 7.2 Finalization invariant

Finalization computes:

```text
expected = selected non-Planning Agent IDs
successful = committed item Agent IDs intersect expected
failed = explicit workflow failure Agent IDs intersect expected
unresolved = expected - successful - failed
```

`unresolved` is a workflow invariant violation. It must raise and cause fatal finalization failure; it must not be interpreted as success or silently added to `failed_agents`.

Terminal status is:

```text
expected empty                         -> failed (invalid request invariant)
successful empty                      -> failed
successful == expected                -> completed
successful non-empty and failed non-empty -> partial_completed
unresolved non-empty                  -> fatal finalization error
```

`failed_agents` contains only real selected non-Planning Agent IDs. Coverage gaps remain diagnostic metadata, never pseudo-Agent IDs.

### 7.3 Parent commit and terminal event

The repository finalizer updates only the parent TeachingPlan, failure IDs, workflow metadata, terminal status, and timestamp. It does not resave artifacts.

The orchestrator reads the committed parent status after graph completion. `completed` and `partial_completed` produce `resource.done(success=true)`; `failed` produces `resource.done(success=false)`.

If finalization fails, the orchestrator attempts to mark the parent `failed`, logs the original error and any status-update error separately, and sends a best-effort terminal event. It never hides the original exception behind an event exception.

## 8. One-Time Database Migration

### 8.1 Source-of-truth alignment

Keep the exact named unique constraint in both:

- `server/app/infra/models.py`
- `server/init_schema.sql`

The constraint is:

```sql
CONSTRAINT uq_generated_resource_items_resource_agent
UNIQUE (resource_id, agent_type)
```

Do not retain a separate redundant non-unique index with the same leading columns unless query analysis demonstrates a different ordering requirement.

### 8.2 Existing database migration

Create:

`server/migrations/20260619_resource_agent_unique.sql`

The migration runs in one transaction and performs:

1. a duplicate preflight grouped by `(resource_id, agent_type)`;
2. an explicit exception containing only IDs and counts when duplicates exist;
3. verification that the current same-named object is an unowned unique index on exactly `(resource_id, agent_type)`;
4. adoption of that index with `ALTER TABLE ... ADD CONSTRAINT ... UNIQUE USING INDEX`;
5. removal of the redundant non-unique composite index;
6. transaction commit.

Fresh bootstrap SQL defines the named unique constraint inside `CREATE TABLE`; it does not separately create a same-named unique index. Existing databases use the one-time migration to turn the current unique index into the constraint-backed index. This avoids both duplicate indexes and an `ADD CONSTRAINT` failure caused by a pre-existing same-named relation.

The migration must not delete duplicates, keep the newest row, merge content, rename old data, or use `ON CONFLICT`. Duplicate cleanup requires an explicit operator decision because automatic cleanup would be a compatibility policy.

The migration is intentionally one-time and non-idempotent. Re-running it fails because the named constraint already exists, making deployment mistakes visible.

### 8.3 Deployment order

1. Back up `generated_resource_items`.
2. Execute the duplicate preflight.
3. Resolve any reported duplicates manually outside this change.
4. Run the migration.
5. Deploy application source.
6. Verify the named constraint through PostgreSQL catalog inspection.

## 9. PPT Contract Hardening

### 9.1 Required inputs

PPT generation requires:

- a valid TeachingPlan;
- the resolved `lesson_kind`, `lesson_depth`, difficulty, focus, and programming language;
- at least one actual successful source artifact referenced by the generated blueprint.

PPT may be scheduled when no base artifact succeeded, but its own validation must then fail. It must not generate source citations from nonexistent Agents or substitute TeachingPlan text for missing source artifacts.

### 9.2 Configuration rules

Missing optional configuration may use one documented canonical product default. An explicitly supplied invalid value must raise `ValueError`; `_validate_literal(..., default)` must not silently replace it.

`lesson_kind="auto"` is a current product mode, not legacy compatibility. It resolves once before the director call. The resolved value is passed into compilation and validated against the selected template.

Programming language must be taken from the resolved Agent configuration. Invalid or unsupported values fail validation rather than becoming Python.

### 9.3 Blueprint compilation

Change compilation to receive expected runtime facts:

```python
compile_deck(
    blueprint,
    *,
    expected_lesson_kind=resolved["lesson_kind"],
    available_source_ids={artifact.agent_id for artifact in source_pack.artifacts},
)
```

Compilation must reject:

- template `lesson_kind` differing from the resolved lesson kind;
- missing required roles;
- a composition not allowed by the template;
- a role not allowed by its composition;
- unknown compositions or layouts;
- repeated layout/composition violations;
- any slide `source_refs` not contained in `available_source_ids`;
- empty effective source references.

`select_chapter_sources()` must return the exact referenced artifacts. If any reference is missing, raise a contract error. Delete the current “return all artifacts” fallback.

### 9.4 Manifest budget enforcement

`assemble_document()` must validate every produced block against its `CompiledBlock.budget` before constructing `PptDocument`.

Use one direct `validate_block_budget(block, budget)` function with explicit type branches:

- `Text`, `Callout`, `KeyPoint`, `Formula`: enforce applicable character limits.
- `Code`: enforce non-empty line count and applicable character/line limits.
- `Terminal`: enforce output line and character limits.
- `CardList`: enforce card count and per-card content limit.
- `CodeAnnotation`: enforce annotation count.
- `TraceStep`: enforce step count.
- `Practice`: enforce hint count and question/checkpoint limits.
- `Table`: enforce column and row counts plus row width equality.
- `Diagram`: enforce node count and valid edge endpoints.

Unsupported budget/type combinations raise a developer contract error. They are not ignored.

The final document must also validate:

- exact chapter IDs, slide IDs, block IDs, types, and slots;
- no empty slot;
- unique slide and block IDs;
- page-count range for the selected depth;
- title, takeaway, and speaker-note length constraints;
- all layouts, blocks, themes, and templates are present in the same manifest used by the frontend alias.

### 9.5 Internal multi-Agent behavior

Keep the two-stage PPT architecture:

1. one Deck Director creates the immutable blueprint;
2. Chapter Writers generate chapters concurrently.

There is no review or repair Agent. A Chapter Writer failure cancels the remaining chapter tasks for that PPT Agent and causes PPT to fail as one isolated external Agent. Other external Agents continue.

## 10. Frontend Strictness and Presentation

### 10.1 Canonical event protocol

Replace the legacy coarse event names atomically across backend and frontend:

```text
agent          -> agent.status
done           -> resource.done
```

Retain current fine-grained names:

```text
agent.snapshot
agent.step
agent.heartbeat
agent.artifact_ready
```

Update the Pydantic literal, emitter methods, SSE endpoint termination check, TypeScript event union, EventSource listeners, and generator dispatch in one slice. Do not dual-emit or listen to old names.

The SSE endpoint uses `get_current_user_flexible` so query-string tokens pass the same `ActiveToken` whitelist, expiry, and user checks as normal authenticated requests. Before subscribing, it verifies the standalone resource belongs to the authenticated user. It must not call `decode_token()` directly or open a detached auth session.

After authorization, the endpoint subscribes and then refreshes/re-queries the parent status before checking/replaying terminal state, so a completion event cannot be lost between the authorization read and queue registration. Snapshot replay replaces the stored event type with `agent.snapshot`; it never passes `event_type` twice through explicit and expanded keyword arguments. A refreshed terminal parent status produces exactly one `resource.done` replay and immediate stream closure. A live stream closes only on `resource.done`, and every path unsubscribes in `finally`.

### 10.2 Resource cards

Result, detail, and history cards come only from persisted item responses. Snapshot state, selected Agent IDs, `failed_agents`, and Agent errors are never transformed into resource cards.

Unknown resource types are logged and omitted. They must not normalize to `content` or use a generic renderer.

For `partial_completed`, show one task-level warning and the successful persisted cards. Do not show failed cards or disabled placeholders.

### 10.3 Remove fabricated review UI

Delete from `ResourceResult.vue` and related types/styles:

- `QUALITY REVIEW` sections;
- `review_result` reads;
- fabricated `96/72` scores;
- review issues and review-passed calculations;
- review scrolling controls;
- fallback study-path generation;
- invented focus points, reasons, and estimated durations used as generated facts.

If there is no persisted/generated study-path contract for standalone resources, omit the learning-path section entirely. Do not manufacture one in the browser.

### 10.4 Strict PPT display

Keep registries throwing on missing layout/block. Replace the result parser API with a strict parsing function that either returns `PPTDocument` or throws a protocol error.

Before creating a PPT card, validate the persisted payload. On failure:

- log one structured client protocol error with resource item ID and validation details;
- omit the invalid PPT item from the card list;
- do not mount `PptView`;
- do not display an “invalid PPT” resource card;
- do not render Markdown, JSON, a generic preview, or a replacement layout.

The same filtering rule applies to generation results, detail, and history pages.

`PptView.vue` assumes validated input and contains no invalid-state presentation. `PptPlayer.vue` contains no fallback branches.

## 11. Compatibility and Dead-Code Removal

Delete only code proven unused by production reference search. Required deletion candidates in this scope are:

- the obsolete `ResourceService.save_generation_results()` wrapper;
- the unused `db_item_to_agent_result` import and export if no path caller exists;
- legacy `agent` and `done` event names and comments;
- review-result frontend fields and UI;
- the unused `generated_resources.review_result` model/bootstrap column through a separate one-time non-idempotent `DROP COLUMN` migration;
- fallback study-path helpers;
- invalid PPT placeholder UI;
- the duplicate empty `Llm.__init__` definition;
- obsolete PPT layouts/blocks already removed from registries;
- comments claiming compatibility with old payloads.
- the `bilingual` to `both` request-value conversion;
- old resource envelope normalization in `VideoView` after callers pass the current canonical content field.

Current protocol parsing such as supported language aliases or fenced-code extraction is not automatically legacy compatibility. Keep it only when it is part of the documented current payload, and remove branches whose sole purpose is accepting an obsolete shape.

Do not delete shared Agent entry points used by `path`. Every deletion requires an `rtk rg` check across `server/app` and `src` first.

Removing the duplicate `Llm.__init__` is the only `infra/llm.py` change permitted. It changes no JSON-output behavior.

## 12. Configuration Scope

The reviewed P0 credential/configuration finding is explicitly outside this implementation scope. Do not modify `server/config.yaml`, introduce `.env`, add environment-variable compatibility, or create an alternate configuration loader as part of this change. Never copy credentials into plans, logs, errors, fixtures, or commit messages.

## 13. Logging Contract

Business failure logs include:

```text
event
run_id
resource_id
user_id
agent_id
stage
error_type
error_message
elapsed_ms
```

Use these event names:

- `resource_planning_failed`
- `resource_agent_failed`
- `resource_agent_persist_failed`
- `resource_event_publish_failed`
- `resource_finalize_failed`
- `resource_ppt_contract_failed`

Exception logs use `exc_info=True` at the catch boundary. Do not log prompts, full generated content, learner profiles, credentials, authorization headers, or raw attachments.

Public SSE messages remain short and safe.

## 14. File-Level Change Map

### Backend

- `server/app/resource/persistence/repository.py`
  - remove workflow import;
  - validate parent ownership and exact Agent ID;
  - remove ineffective per-instance lock abstraction;
  - narrow finalization to primitive outcome sets.
- `server/app/resource/persistence/__init__.py`
  - remove exports confirmed dead.
- `server/app/resource/workflow/state.py`
  - keep workflow-only failure type;
  - strengthen reducers against conflicting outcomes.
- `server/app/resource/workflow/nodes.py`
  - remove database-result reconstruction import;
  - centralize non-Planning lifecycle;
  - separate commit success from event publication;
  - strictly validate handoffs and final outcomes.
- `server/app/resource/workflow/graph.py`
  - retain topology and fatal Planning edge.
- `server/app/resource/workflow/__init__.py`
  - retain only the canonical graph exports after the dependency cycle is removed.
- `server/app/resource/orchestrator.py`
  - make final status the terminal truth;
  - isolate event errors from fatal business errors.
- `server/app/resource/service.py`
  - delete the unused broken wrapper;
  - expose only persisted resource items.
- `server/app/resource/events.py`
  - adopt canonical event names;
  - make publication observation-only;
  - delete legacy compatibility text.
- `server/app/resource/api.py`
  - terminate SSE on `resource.done` only.
- `server/app/resource/ppt_contract.py`
  - validate lesson kind, actual sources, layout contract, and every budget.
- `server/app/resource/agents/ppt.py`
  - reject invalid config;
  - delete all-source fallback;
  - pass expected lesson kind and available sources into compilation.
- `server/app/resource/agents/video.py`
  - retain existing no-content-fallback behavior;
  - remove any remaining duration substitution after confirming it is generated-content fallback rather than an explicit contract calculation.
- `server/app/infra/models.py`
  - retain the named unique constraint.
- `server/init_schema.sql`
  - retain the same named unique constraint and remove redundant indexing if applicable.
- `server/migrations/20260619_resource_agent_unique.sql`
  - add explicit one-time migration.
- `server/app/infra/llm.py`
  - remove only the duplicate empty constructor.
- `server/config.yaml`
  - out of scope; leave unchanged.

### Frontend

- `src/features/resource/model/resource.ts`
  - use only canonical event names.
- `src/features/resource/api/resource.ts`
  - listen for only canonical event names.
- `src/features/resource/api/resource-history.ts`
  - remove review-result compatibility fields.
- `src/features/resource/views/ResourceGenerator.vue`
  - dispatch canonical events and show partial completion without failed cards.
- `src/features/resource/views/ResourceResult.vue`
  - remove review UI, fake scores, fallback paths, invented metrics, and unknown-type normalization;
  - filter strict PPT payloads before card creation.
- `src/features/resource/views/ResourceDetail.vue`
  - show only valid persisted artifacts;
  - omit strict-renderer failures.
- `src/features/resource/components/PptView.vue`
  - accept validated PPT only; remove invalid placeholder card.
- `src/features/resource/components/ppt-engine/types/ppt.ts`
  - expose strict parse-or-throw behavior.
- `src/features/resource/components/ppt-engine/PptPlayer.vue`
  - retain strict registry rendering without fallback branches.
- `src/features/resource/components/ppt-engine/components/layouts/registry.ts`
  - retain throw-on-unknown behavior.
- `src/features/resource/components/ppt-engine/components/blocks/registry.ts`
  - retain throw-on-unknown behavior.

### Tests

Do not edit any file under `server/tests/`. The existing modification to `server/tests/dashboard/test_home_api.py` is outside this plan and must remain untouched by Claude Code. Report it in the final worktree status rather than reverting or extending it.

## 15. Verification Strategy

All commands must use the repository-required `rtk` prefix.

### 15.1 Static and import checks

```bash
rtk env UV_CACHE_DIR=/tmp/codex-uv-cache uv run python -c "from app.main import app; print(type(app).__name__)"
rtk env UV_CACHE_DIR=/tmp/codex-uv-cache uv run python -c "from app.resource.service import ResourceService; print(ResourceService.__name__)"
rtk env UV_CACHE_DIR=/tmp/codex-uv-cache uv run python -m compileall -q app/resource app/infra/llm.py
rtk git diff --check
```

### 15.2 Frontend check

```bash
rtk npm run build
```

### 15.3 Existing tests, read-only

Run existing tests without editing them:

```bash
rtk env UV_CACHE_DIR=/tmp/codex-uv-cache uv run pytest tests/resource -q
```

Old PPT symbol failures are expected until the repository's tests are separately rewritten under explicit user authorization. Compatibility symbols must not be restored to make them pass. Any new production import or runtime error is not expected and must be fixed in source.

### 15.4 Source-only smoke verification

Use short `python -c` or existing callable entry points without creating files under `server/tests/` to verify:

1. Planning failure schedules no downstream Agent and parent becomes `failed`.
2. One base Agent failure does not cancel a successful sibling commit.
3. An event-sink exception after commit leaves the Agent successful and item persisted.
4. PPT failure does not cancel Video, and Video failure does not cancel PPT.
5. A failed Agent has no item row.
6. Mixed outcomes produce `partial_completed`.
7. All selected non-Planning Agents failing produces `failed`.
8. An unresolved selected Agent causes fatal finalization error.
9. PPT rejects an unavailable `source_ref`.
10. PPT rejects template/lesson-kind mismatch.
11. PPT rejects every manifest budget violation category.

### 15.5 Forbidden-pattern audit

Search production code for:

```bash
rtk rg -n "兼容旧|legacy|review_result|QUALITY REVIEW|buildFallbackStudyPath|persist_error|db_item_to_agent_result" server/app/resource src/features/resource
rtk rg -n 'event_type="agent"|event_type="done"|addEventListener\("agent"|addEventListener\("done"' server/app/resource src/features/resource
rtk rg -n "return \[artifact.*source_pack\.artifacts|synthesiz|fallback_topic" server/app/resource
```

Every production match must be removed or explicitly proven unrelated to compatibility/content fallback. Geometry variable names used only for drawing are not content fallback and need not be renamed.

## 16. Acceptance Criteria

The change is complete only when all conditions hold:

- `app.main` and `ResourceService` import successfully.
- Persistence has no dependency on workflow modules.
- Planning failure terminates the run.
- Non-Planning failures do not cancel siblings.
- Every successful Agent is committed immediately.
- Event failure after commit does not change Agent success.
- Failed Agents create no database rows and no cards.
- Final status is derived from the complete selected-Agent outcome set.
- Existing databases have the named uniqueness constraint after the explicit migration.
- PPT rejects wrong templates, missing actual sources, invalid slots/types, and every manifest budget violation.
- PPT retains Director plus concurrent Chapter Writers, with no review or repair Agent.
- Frontend contains no fabricated review score, fallback study path, failed card, invalid PPT card, generic PPT renderer, or old event listener.
- No old event alias is emitted or consumed.
- No API key introduced by this change remains in comments, plans, logs, or fixtures.
- Resource and path persistence remain separate.
- No test file is modified by the implementation.
- Frontend build, Python imports, compile check, and whitespace check pass.
- Existing stale tests are reported honestly instead of satisfied through compatibility code.

## 17. Explicit Non-Goals

- No LLM structured-output redesign.
- No model-provider tuning or JSON retry redesign.
- No Video content redesign beyond removal of confirmed content substitution.
- No review or repair Agent.
- No automatic duplicate cleanup.
- No startup schema reconciliation.
- No Alembic introduction.
- No resource/path record or detail-page merge.
- No test-source modification.
