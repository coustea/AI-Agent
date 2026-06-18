# Resource Persistence and Video Contract Design

## Goal

Simplify standalone multi-agent resource generation so the database stores only the generation task and each agent's final user-facing output. Make the Remotion template contract the only accepted video JSON shape, remove legacy compatibility, and delete code that no longer participates in the generation path.

## Scope and Boundary

This change applies to `server/app/resource/` and the standalone Remotion renderer in `video-render/`.

The `resource` and `path` domains may continue sharing agent registration and result types, but their task records, resource records, detail APIs, and persistence models remain separate. This change must not migrate or merge `PathNodeResource` data.

## Persistence Design

`GeneratedResource` remains the standalone generation task record. It stores the request identity, selected agents, lifecycle status, top-level error information, and timestamps needed by create/list/detail/SSE APIs.

`GeneratedResourceItem` becomes a final-output record. It stores only:

- ownership and task linkage;
- agent type and generated-by identity;
- content format;
- title and summary;
- one canonical content payload (`content_json` for structured output or `content_text` for text output);
- success or failure status and error message;
- creation and update timestamps.

The item model and repository will remove persisted planning and collaboration data, including metrics, downstream context, agent dependencies, source item identifiers, knowledge-coverage diagnostics, recommendations, execution reports, and duplicated metadata envelopes.

Planning decisions, handoffs, intermediate drafts, timing metrics, and dependency results live only in the LangGraph state for the active run. Persistence happens once per selected agent after that agent reaches its terminal result. A failed selected agent may create a failure item without generated content so task detail can explain the failure.

No migration adapter, old-column reader, dual-write path, or fallback deserializer will be added. Bootstrap SQL and SQLModel definitions will be changed together to the new schema.

## Multi-Agent Generation Design

The planner produces the execution selection and shared teaching intent. Independent base agents run concurrently and return typed in-memory `AgentResult` values. Aggregate agents such as PPT and Video consume only results from the current workflow state.

Each selected agent has exactly one terminal outcome:

- success: persist one final resource item;
- failure: persist one failure item and continue unrelated branches;
- dependency failure: do not fabricate content; return a clear failure for that aggregate agent.

The workflow must not reload persisted items to construct downstream prompts. This keeps orchestration state separate from the final resource store and prevents persistence fields from becoming an implicit agent protocol.

## Canonical Video JSON

The backend video agent will emit the renderer's `RichVideoPlan` directly. The only top-level keys are:

- `meta`: video identity, title, subject, topic, difficulty, target audience, estimated duration in seconds, and language;
- `global_style`: renderer-wide visual tokens supported by the template;
- `render_config`: dimensions, frame rate, and renderer configuration supported by the template;
- optional `audio`: global audio configuration when used by the renderer;
- `scenes`: ordered scene definitions.

Each scene uses exactly:

- `id`;
- `type`, restricted to the renderer's declared scene types;
- `duration_seconds`;
- `title`;
- `narration`;
- `visual`, shaped for the selected scene template;
- optional `audio_src`;
- `transition`;
- optional `caption_words`.

The backend will remove the parallel `video/v1` schema and fields such as `scene_id`, `index`, `role`, `start_ms`, `duration_ms`, `visual_type`, `captions`, `on_screen_text`, `visual_prompt`, `interaction_prompt`, duplicated assets, and generic metadata.

The renderer schema becomes strict. It will no longer accept root-level meta fields, backend aliases, millisecond durations, `id`/`scene_id` alternatives, `type`/`visual_type` alternatives, or catch-all scene objects. The legacy normalization layer will be deleted; validation errors fail rendering instead of silently manufacturing defaults.

## API and Error Behavior

Existing standalone resource endpoints and response envelopes remain, but their item payloads expose only the new persisted fields. This is an intentional breaking response change.

Video plans are validated before persistence and before render invocation. Invalid plans fail the Video agent with a concise validation error. Aggregate-agent failures do not overwrite successful outputs from independent agents. The parent task is `completed` when all selected agents succeed and `partial_failed` or `failed` according to the existing task-level terminal rules.

No old event names, payload aliases, or deprecated imports are retained solely for compatibility. Current callers and tests must be updated atomically.

## Dead-Code Removal Rules

Deletion is evidence-based: a symbol or file must have no production reference, no route registration, and no required test contract after the new design is in place. Primary candidates include the unwired tutor video adapter, legacy video normalization and schemas, compatibility re-exports, deprecated event aliases, duplicated video payload builders, and unused prompts.

The refactor should prefer direct functions and existing domain objects. New wrappers, factories, protocol layers, or compatibility facades are out of scope unless a test demonstrates a concrete need.

## Verification

Implementation follows red-green-refactor:

1. Add failing backend tests for minimal item persistence and runtime-only handoffs.
2. Add failing contract tests proving Video emits only `RichVideoPlan` and rejects legacy keys.
3. Add failing workflow tests for one terminal item per selected agent and aggregate dependency failures.
4. Make the smallest production changes needed to pass each group.
5. Delete dead code only after reference searches and focused tests are green.
6. Run resource tests, renderer type/build checks, the backend suite while excluding the documented pre-existing chat failures, and the root frontend build if shared API types change.

## Non-Goals

- Merging `resource` and `path` persistence or detail pages.
- Preserving old database rows or old Video JSON.
- Adding a generalized orchestration framework.
- Redesigning unrelated chat, dashboard, authentication, or path behavior.
