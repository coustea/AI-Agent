# Resource Agent Failure Isolation and No-Fallback Design

**Date:** 2026-06-19

**Status:** Proposed

## 1. Objective

Change standalone resource generation so that Planning remains the only fatal shared stage, while every resource-producing Agent is isolated from sibling failures.

The system must persist each valid Agent artifact immediately after that Agent finishes. A failed Agent must produce a structured backend log and a failed execution event, but must not create a resource item, placeholder card, repaired payload, default payload, or fallback rendering. Other independent Agents continue running.

This design preserves the hard boundary between standalone `resource` records and learning-path `path` records. It changes only the standalone resource workflow and shared rendering components used to display standalone PPT artifacts. It does not merge persistence models or detail pages.

## 2. Explicit Scope

### Included

- Fatal Planning failure behavior.
- Failure isolation for base resource Agents.
- Failure isolation for PPT and Video aggregation Agents.
- Immediate persistence of each successful Agent artifact.
- Strict success contracts before persistence.
- Accurate `completed`, `partial_completed`, and `failed` terminal states.
- Structured error logging.
- Event behavior for successful and failed Agents.
- Hiding failed Agent cards by ensuring they have no persisted artifact.
- Removal of frontend layout and block fallback rendering.
- Removal of backend content fallback, placeholder, and synthesized handoff behavior.
- Removal of dead legacy PPT renderer files encountered in this scope.

### Excluded

- LLM JSON output strategy.
- `response_format`, JSON-mode retry, prompt fallback, or model-provider behavior.
- Review or repair Agents.
- Changes to test files.
- Video content-quality redesign beyond removing fallback values.
- Any merge between `resource` and `path` storage or APIs.

## 3. Non-Negotiable Invariants

1. Planning is mandatory. Planning failure terminates the complete run.
2. A resource Agent is successful only after generation, contract validation, and database persistence all succeed.
3. One non-Planning Agent failure cannot terminate sibling Agents.
4. Failed Agents never create `GeneratedResourceItem` rows.
5. Successful Agents are persisted immediately; the workflow does not wait for every Agent to finish.
6. No layer may invent replacement content after an Agent failure.
7. Missing `downstream_context` from a successful base Agent is a contract failure, not a reason to synthesize context.
8. Aggregation Agents consume the TeachingPlan and only the handoffs produced by successful base Agents.
9. An aggregation Agent may run with zero handoffs because TeachingPlan is its required baseline input. It must fail itself if its own output contract cannot be satisfied.
10. Unknown PPT templates, themes, layouts, slots, or blocks are rejected. They are never rendered through a replacement component.
11. Failed Agent information is observable through logs and execution status, not through fake resource cards.
12. Standalone resources remain stored only in `GeneratedResource` and `GeneratedResourceItem`; path resources remain untouched.

## 4. Target Workflow

```text
create GeneratedResource(status=pending)
  -> set status=generating
  -> PlanningAgent
       failure -> log -> status=failed -> done.failed -> END
       success -> TeachingPlan
  -> base Agents fan out in parallel
       each Agent:
         generate
         validate AgentResult
         validate downstream_context when required
         save GeneratedResourceItem immediately
         emit artifact_ready
       failure at any step:
         log AgentFailure
         emit agent.failed
         return failure record only
       siblings continue
  -> merge base outcomes
  -> PPT and Video fan out in parallel when selected
       input = TeachingPlan + successful persisted handoffs
       each aggregation Agent follows the same isolated lifecycle
  -> merge aggregation outcomes
  -> finalize GeneratedResource status and failure metadata
  -> emit done
```

The LangGraph topology remains recognizable. The implementation does not introduce a separate workflow framework or an additional service layer.

## 5. Failure Model

### 5.1 Fatal Failure

Only these conditions terminate the complete run:

- Planning Agent raises an exception.
- Planning Agent returns `success=False`.
- Planning metadata does not contain a valid `TeachingPlan`.
- The parent `GeneratedResource` cannot be read or updated.
- The workflow cannot finalize its terminal status.

Fatal failures set the parent resource to `failed`, emit one terminal failed event, log the full traceback, and stop all downstream scheduling.

### 5.2 Isolated Agent Failure

These failures affect only the current non-Planning Agent:

- LLM call exception inside the Agent.
- Agent returns `success=False`.
- Agent returns empty content.
- Base Agent omits `downstream_context`.
- Output contract validation fails.
- Immediate persistence fails.

Artifact-ready publication failure is not an Agent failure because the artifact has already committed. It is logged as an observation failure, while the persisted Agent remains successful.

Event publication is observational. If the artifact has already committed, an event failure is logged but does not turn the persisted artifact into a failed artifact. The terminal status endpoint remains the source of truth.

### 5.3 Failure Representation

Do not create fake `AgentResult(success=False)` objects and mix them with successful content results. Add a small workflow-only failure value:

```python
class AgentFailure(TypedDict):
    agent_id: str
    stage: Literal["generation", "validation", "persistence", "event"]
    error_type: str
    message: str
```

`ParentState.results` contains only successful, persisted `AgentResult` values. `ParentState.failures` contains `AgentFailure` values merged by Agent ID.

This separation prevents downstream code from accidentally treating a failed result as reusable content.

## 6. Per-Agent Execution Boundary

Use one orchestration helper in `workflow/nodes.py`; do not create a hierarchy of executor, lifecycle, result, and persistence wrapper classes.

The helper owns this exact sequence:

1. Emit Agent running event.
2. Invoke the Agent.
3. Reject `success=False`.
4. Reject empty content.
5. For base Agents, reject missing `downstream_context`.
6. Persist the artifact immediately.
7. Add the successful result to workflow state.
8. Return the persisted result as a successful workflow result.
9. Attempt to emit `artifact_ready` after the commit in a separate observation-only `try` block.
10. Log an artifact event failure without changing the successful result.
11. Catch generation, validation, and persistence exceptions within the non-Planning Agent boundary.
12. Log the Agent failure with traceback.
13. Emit Agent failed event.
14. Return an `AgentFailure` without a resource item.

Planning does not use this isolated helper. Its exceptions continue to escape the node and terminate the graph.

## 7. Immediate Persistence

### 7.1 Success Commit

`ResourceRepository.save_agent_result()` remains the single persistence operation for an Agent artifact. It must:

- accept only `success=True` with non-empty content;
- require a non-empty registered `agent_id`;
- create exactly one `GeneratedResourceItem` for `(resource_id, agent_type)`;
- commit and refresh before returning;
- roll back and re-raise on failure;
- never write a failed or placeholder item.

The existing non-unique `(resource_id, agent_type)` index must become a unique constraint in both SQLModel metadata and `init_schema.sql`. A repeated execution is an error rather than an upsert or compatibility path.

### 7.2 Artifact Availability

Once `save_agent_result()` commits, that artifact may immediately appear in status/detail responses. This is intentional. A later sibling failure does not remove a successful artifact.

### 7.3 Finalization

Rename or simplify `save_generation_results()` so that it only finalizes the parent resource. It must not resave Agent items.

Terminal status rules:

```text
Planning failed                                  -> failed
Planning succeeded, zero selected artifacts saved -> failed
Planning succeeded, all selected Agents saved     -> completed
Planning succeeded, some saved and some failed     -> partial_completed
```

`failed_agents` contains only selected non-Planning Agent IDs that failed. Coverage metadata remains diagnostic and must not create fake Agent IDs such as `_coverage_gap`.

## 8. Base and Aggregation Dependencies

### 8.1 Base Agents

Content, Mindmap, Quiz, Code, and Reading run independently after Planning. A failure in one does not cancel or delay the successful persistence of another.

### 8.2 Handoffs

Delete synthesized downstream context. `collect_successful_handoffs()` must read only `ParentState.results`, which by design contains persisted successes.

Invalid outline IDs inside an otherwise valid handoff are a contract failure for that Agent. Do not silently filter them out. This ensures aggregation Agents never receive data that was quietly rewritten.

### 8.3 PPT and Video

PPT and Video run independently after the base barrier. Both receive:

- the mandatory TeachingPlan;
- the learner profile;
- their explicit Agent configuration;
- zero or more valid handoffs from successful base Agents.

If PPT fails, Video continues. If Video fails, PPT continues. Each successful aggregation artifact is persisted immediately.

PPT and Video must not generate a simplified replacement when material is insufficient. They either satisfy their current strict output contract or return an isolated failure.

## 9. No-Fallback Rules

### Backend

Delete or replace all behavior that:

- synthesizes `DownstreamContext`;
- replaces an Agent topic with `learning_need` after material extraction fails;
- substitutes planned Video duration for missing generated duration;
- catches persistence errors and stores them only in metadata;
- treats malformed content as text and persists it anyway;
- continues an Agent after its required contract validation fails;
- constructs placeholder resources for failed Agents.

Fallback is different from isolation. Catching an Agent exception and allowing siblings to continue is required isolation. Inventing substitute output for that failed Agent is prohibited fallback.

### Frontend

- `resolveLayoutComponent()` must return a component or throw an explicit protocol error.
- `resolveBlock()` must return a component or throw an explicit protocol error.
- `PptPlayer.vue` must remove all fallback-slide branches and styles.
- `PptView.vue` must not render a simplified presentation for invalid content.
- Resource card lists must be derived only from persisted `GeneratedResourceItem` records.
- Failed snapshots and `failed_agents` must never be converted into cards.
- Invalid historical PPT artifacts are omitted from card lists and logged as protocol errors; they are not normalized or converted.

The task-level page may display a general failed state when no artifacts succeeded. This is a workflow status, not degraded resource rendering.

## 10. Logging Contract

Every isolated failure log must include:

```text
event=resource_agent_failed
run_id
resource_id
user_id
agent_id
stage
error_type
error_message
elapsed_ms
```

Fatal Planning logs use `event=resource_planning_failed`. Finalization failures use `event=resource_finalize_failed`.

Use `logger.error(..., exc_info=True)` at the point where the exception is caught. Do not log full prompts, generated content, API keys, authorization headers, profile payloads, or raw user attachments.

The public SSE message is a short safe message such as `quiz 生成失败，其他资源继续生成`. Full diagnostics remain server-side.

## 11. Event Semantics

The event stream represents execution; persisted items represent displayable artifacts.

- `agent running`: Agent started.
- `agent finished`: generation and validation succeeded.
- `agent failed`: this Agent failed and siblings continue.
- `artifact_ready`: database commit succeeded; the card may be fetched.
- `done success=true`: terminal status is `completed` or `partial_completed`.
- `done success=false`: Planning failed, all selected Agents failed, or finalization failed.

Do not emit `artifact_ready` before persistence. Do not emit a fake artifact ID for a failure. Remove event aliases retained only for older frontend consumers; backend and frontend must use the same current event contract.

## 12. Frontend Presentation

### Generating View

A failed Agent node may remain visible in the live execution graph as a failed execution status. It is not a resource card and contains no preview action.

### Result View

Only persisted items become cards. A partial run therefore naturally shows successful cards only. Do not create a failed card, placeholder card, disabled preview card, or fallback renderer.

The page may show one non-card summary message for `partial_completed`, for example: `部分资源未生成，已完成内容可以正常使用。` It must not expose stack traces or provider errors.

### Detail and History

`partial_completed` remains a valid readable terminal state. Detail and history pages show only saved items. An item whose strict renderer rejects its payload is omitted and logged; it is not rendered through Markdown or a generic key/value preview.

## 13. Code Changes

### Backend workflow

- Modify `server/app/resource/workflow/state.py`
  - add `AgentFailure` and failure reducer;
  - make `results` mean persisted successes only.
- Modify `server/app/resource/workflow/nodes.py`
  - remove synthesized handoff logic;
  - add the single isolated non-Planning Agent execution helper;
  - persist immediately inside the Agent boundary;
  - return failures separately;
  - validate handoffs without filtering or rewriting;
  - finalize status without treating failure as content.
- Modify `server/app/resource/workflow/graph.py`
  - retain topology;
  - isolate non-Planning Agent exceptions while allowing Planning and orchestration failures to escape globally.
- Modify `server/app/resource/orchestrator.py`
  - keep fatal exception handling for Planning/graph/finalization;
  - calculate terminal success from finalized status.
- Delete `server/app/resource/workflow/audit.py` if it remains only a constants wrapper; move the four current Agent IDs into `nodes.py` or the existing canonical constants module.

### Backend persistence

- Modify `server/app/resource/persistence/repository.py`
  - enforce one successful item per resource and Agent;
  - keep immediate commit/rollback;
  - replace partial-result inference from mixed `AgentResult` values with explicit successful IDs and failure IDs;
  - remove `_coverage_gap` pseudo-Agent.
- Modify `server/app/infra/models.py`
  - add unique `(resource_id, agent_type)` constraint.
- Modify `server/init_schema.sql`
  - add the matching unique constraint/index.

### Agent cleanup

- Modify `server/app/resource/agents/video.py`
  - remove fallback topic and duration behavior;
  - propagate required-stage errors to the Agent boundary.
- Modify base resource Agents only where they currently catch a required-stage error and manufacture substitute output.
- Do not modify `server/app/infra/llm.py` for this work.

### Frontend

- Modify `src/features/resource/components/ppt-engine/components/layouts/registry.ts`
  - throw on unknown layout.
- Modify `src/features/resource/components/ppt-engine/components/blocks/registry.ts`
  - throw on unknown block.
- Modify `src/features/resource/components/ppt-engine/PptPlayer.vue`
  - remove fallback branches and styles.
- Modify `src/features/resource/components/PptView.vue`
  - render only a validated document;
  - do not create a fallback presentation.
- Modify `src/features/resource/views/ResourceResult.vue`
  - build cards only from persisted artifacts;
  - never materialize failed Agents as cards.
- Modify `src/features/resource/views/ResourceDetail.vue`
  - omit strictly invalid artifacts rather than using another renderer.
- Modify `src/features/resource/views/ResourceGenerator.vue`
  - treat `partial_completed` as readable completion;
  - retain a non-card summary warning only.
- Delete unused legacy layouts:
  - `LayoutBentoGrid.vue`
  - `LayoutFocusTitle.vue`
  - `LayoutLayerStack.vue`
  - `LayoutSplitScreen.vue`

## 14. Source-Only Verification

Do not modify files under `server/tests/`.

Required verification:

1. `npm run build` succeeds.
2. Python compile succeeds for `server/app/resource`.
3. `git diff --check` succeeds.
4. Static search finds no PPT fallback layout or block branches.
5. Static search finds no synthesized `DownstreamContext`.
6. Static search finds no Video topic or duration fallback.
7. A source-only smoke script demonstrates Planning failure produces no items and parent `failed`.
8. A source-only smoke script demonstrates one base Agent failure does not prevent sibling persistence.
9. A source-only smoke script demonstrates PPT failure does not prevent Video persistence.
10. A source-only smoke script demonstrates failed Agents have no `GeneratedResourceItem` row.
11. A source-only smoke script demonstrates `partial_completed` when some selected Agents succeed.
12. A source-only smoke script demonstrates all non-Planning Agents failing produces parent `failed`.
13. Existing stale old-contract test failures are reported, not fixed through compatibility code.

## 15. Acceptance Criteria

- Planning failure stops the run before any resource Agent is scheduled.
- A non-Planning Agent exception never cancels a sibling Agent.
- Every successful Agent artifact is visible after its own database commit.
- Failed Agents create no resource item and no result card.
- A later failure never deletes an earlier successful artifact.
- PPT and Video independently consume only successful handoffs.
- No synthesized handoff, placeholder content, substitute Video value, generic renderer, or fallback layout remains.
- `partial_completed` accurately represents mixed success and failure.
- Full traceback and structured context appear in server logs.
- Public events expose safe summaries only.
- Resource and path persistence remain separate.
- No test file is changed.
