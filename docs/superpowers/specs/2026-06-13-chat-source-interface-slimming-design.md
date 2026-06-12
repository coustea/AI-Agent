# Chat Source Interface Slimming Design

## Goal

Slim the backend chat source code while preserving the runnable chat feature. The refactor should remove old orchestration interfaces, make `TutorAgent` the only intelligent runtime, and stop eager profile and long-term-memory loading in `ChatService`.

This is a source-code interface refactor, not a test rewrite. Existing tests may fail when they assert removed legacy contracts.

## Decisions

- Do not keep compatibility with the old manual reasoning loop.
- Do not modify test files in this change.
- Keep the frontend API and SSE event shape stable.
- Allow database model and schema changes when they simplify memory/profile scheduling.
- Let `TutorAgent` call learner profile and long-term memory through tools when classification says they are needed.
- Keep code volume flat or lower; avoid adding small wrapper files unless they remove more code than they add.

## Current Problems

`server/app/chat/service.py` is doing too much: turn creation, user-message persistence, history construction, context preloading, agent invocation, SSE projection, final answer persistence, upload storage, safety filtering, and background work.

`server/app/chat/schemas.py` still contains old reasoning-loop DTOs such as `FinalAnswer`, `FinalAnswerStream`, `ReasoningResult`, and `ConstraintReport`. These no longer match the LangGraph node design.

`ChatService` currently preloads learner profile and long-term memory before invoking `TutorAgent`. That conflicts with the tool-calling design, duplicates context, and makes every turn pay for data it may not use.

`ChatSession.summary_token_count` is shared by compression and profile timing. This couples unrelated post-turn work and can cause compression, long-term memory, and profile updates to run too close together.

## Target Architecture

`ChatService.chat` remains the public callable function used by the API. It should only:

1. Resolve or create the effective session.
2. Create the chat turn.
3. Save the user message and attachment metadata.
4. Build recent history and session summary.
5. Call `TutorAgent.chat`.
6. Project agent events to the existing SSE format.
7. Save the final assistant answer and finalize the turn.

`TutorAgent` owns:

1. LangGraph node routing.
2. `classify`, `analysis_files`, `search_node`, `answer_node`, and `diagram_node`.
3. Tool selection and execution.
4. Node-level event persistence.
5. Streaming answer tokens.
6. The post-turn scheduling decision after the final answer is known.

`ChatMemoryService` owns:

1. Message, turn, transcript, upload, and tool persistence.
2. Session summary compression.
3. Long-term memory reads and writes.
4. Independent counters for compression and long-term-memory scheduling.

`ProfileService` owns:

1. Profile reads.
2. Profile inference and writes.
3. Profile update cooldown and profile-specific counters.

## Source Interface Changes

Remove from `TutorAgentInput`:

- `long_term_memory`
- `learner_profile`

Keep in `TutorAgentInput`:

- `user_id`
- `session_id`
- `turn_id`
- `user_message_id`
- `question`
- `attachments`
- `history_messages`
- `session_summary`
- `enable_web_search`
- `need_teaching_diagram`

Replace legacy tool/request names with current-purpose names:

- `TurnRequest` becomes a smaller `TutorTurnContext`.
- `ToolIntent` becomes `TutorToolCall`.

Remove old reasoning-loop types:

- `ChatHistoryMessage`
- `FinalAnswer`
- `FinalAnswerStream`
- `ReasoningResult`
- `ConstraintReport`

Keep evidence and teaching-diagram schemas because they are still used by search, diagram generation, and persistence.

## Profile And Long-Term Memory Loading

`ChatService.chat` must not call:

- `get_long_term_memory`
- `get_memory_markdown`
- `get_profile_markdown`
- `get_profile_service().get_profile_markdown`

`TutorAgent.search_node` calls tools based on `ClassificationResult`:

- `needs_profile` -> `get_learner_profile`
- `needs_long_term_memory` -> `get_long_term_memory`
- `needs_knowledge_search` -> `search_knowledge_base`
- `needs_web_search` or user-enabled web search -> `web_search`
- `needs_recent_evaluation` -> `get_recent_evaluation`

The answer prompt only receives profile or long-term memory if those tools were called and produced evidence.

## Database Changes

Keep `summary_token_count` only for compression.

Add independent scheduling fields to `chat_sessions` and `ChatSession`:

- `profile_token_count INTEGER DEFAULT 0`
- `ltm_turn_count INTEGER DEFAULT 0`
- `last_profile_updated_at TIMESTAMPTZ NULL`
- `last_ltm_updated_at TIMESTAMPTZ NULL`

These fields replace the current shared-counter behavior. `init_schema.sql` and `server/app/infra/models.py` must stay in sync.

## Post-Turn Scheduling

After the final assistant answer is persisted, the chat module updates counters from the current user/assistant texts:

- `summary_token_count` increases for compression.
- `profile_token_count` increases for profile update timing.
- `ltm_turn_count` increases for long-term-memory update timing.

Run at most one heavy post-turn LLM job by default:

1. Compression first, when message/token thresholds are met.
2. Long-term memory next, when turn count and cooldown allow it.
3. Profile update last, when profile token count and cooldown allow it.

If a higher-priority job runs, lower-priority jobs are skipped for that turn and their counters remain. This avoids compression, long-term memory, and profile update firing together.

Strong profile signals may trigger a profile update earlier, but only when no compression job ran in the same turn.

## File-Level Plan

`server/app/chat/service.py`

- Remove eager profile and long-term-memory loading.
- Remove unused `_response_streamer`.
- Keep public `chat`, session, upload, and history APIs.
- Keep existing SSE event names and final payload shape.

`server/app/chat/agent.py`

- Remove `long_term_memory` and `learner_profile` from graph state input.
- Use tool evidence as the only source of profile and long-term-memory context.
- Keep the existing graph node names.
- Keep node-level persistence for tool request/result messages.

`server/app/chat/schemas.py`

- Delete old reasoning-loop DTOs.
- Rename and shrink tool execution context types.
- Keep evidence, upload response, stream event, classification, and diagram schemas.

`server/app/chat/tool_execute.py`

- Accept `TutorToolCall` and `TutorTurnContext`.
- Keep aliases only when they help the model tool-call surface; do not preserve removed Python API names for compatibility.

`server/app/chat/stages.py`

- Update teaching-diagram generation to accept `TutorTurnContext`.
- Remove imports of deleted types.

`server/app/chat/tools/*.py`

- Update imports from `TurnRequest` to `TutorTurnContext`.
- Keep tool behavior unchanged.

`server/app/chat/memory/service.py`

- Split counter updates.
- Add one post-turn scheduling entrypoint that chooses at most one heavy job.
- Remove profile updates from chat memory internals; call `ProfileService` only from the scheduler boundary.

`server/app/infra/models.py` and `server/init_schema.sql`

- Add the independent chat session scheduling fields.
- Keep model/schema names aligned.

## Error Handling

Tool-read failures become tool evidence failures or skipped evidence; they do not crash the turn.

Post-turn failures are logged and persisted as turn events where possible. They must not block answer delivery.

If database counter updates fail, the final answer should still be delivered. The failure should be visible in logs and a turn event when the turn id is available.

## Verification

Because tests are not modified in this change, verification focuses on source behavior:

- Run targeted chat tests to see which old interface assertions fail.
- Run a syntax/import check for the changed chat modules.
- Run a minimal streaming path test or manual API call if the environment is available.
- Confirm `ChatService.chat` no longer imports or calls profile/long-term-memory preload methods.
- Confirm `TutorAgent.search_node` remains the only path that reads profile and long-term memory during answer generation.

## Non-Goals

- No frontend changes.
- No resource-agent or path-planning refactor.
- No compatibility shims for deleted schema names.
- No broad API response redesign.
- No test file edits.
