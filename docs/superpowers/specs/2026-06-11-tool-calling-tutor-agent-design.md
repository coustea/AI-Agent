# Tool-Calling Tutor Agent Architecture Design

## Goal

Optimize the intelligent tutoring backend across architecture, performance, and answer quality by rebuilding the chat tutor around a LangChain tool-calling agent inside a deterministic orchestration shell.

The system should stop eagerly injecting every possible context into every prompt. Instead, the tutor agent should call typed tools when it needs learner profile, long-term memory, knowledge-base evidence, web search, recent evaluation data, or attachment analysis.

## Scope

This design covers the backend chat tutoring path under `server/app/chat/` and its direct integrations with profile, memory, knowledge retrieval, evaluation, attachment analysis, SSE streaming, and post-turn processing.

It does not redesign the frontend chat UI, the resource-generation agents, path planning, or the database schema beyond fields needed to record tool execution, latency, and transcript outcomes.

## Current Problems

The current tutor flow has already moved toward `ChatUseCases -> TurnOrchestrator -> ReasoningAgent`, but several responsibilities are still blurred:

- `ChatUseCases` owns too much lifecycle behavior, including persistence, SSE events, background tasks, and orchestration glue.
- `ReasoningAgent` uses local keyword routing instead of native model tool-calling.
- Profile, long-term memory, and knowledge retrieval are partly treated as context snippets instead of first-class tools.
- The `token` SSE event currently emits the complete answer at once, not true streaming chunks.
- Post-turn memory and profile updates are fire-and-forget tasks with limited status tracking.
- Answer quality is difficult to measure because tool use, evidence, and final answer policy are not captured as a coherent tutoring trace.

## Architecture

The optimized tutor uses a hybrid design:

1. Deterministic orchestration owns safety, persistence, streaming, limits, and recovery.
2. The tutor agent owns pedagogical reasoning and chooses tools through LangChain tool calling.
3. Tools are typed, observable adapters over existing domain services.
4. Post-turn updates remain controlled backend side effects, not free-form agent actions.

### Main Components

`TutorTurnService`

API-facing facade used by `chat/api.py`. It normalizes requests, creates the turn, starts SSE streaming, and delegates execution.

`TurnOrchestrator`

Deterministic state machine for one tutoring turn. It enforces max tool iterations, timeout budgets, transcript checkpoints, and failure behavior.

`TutorAgent`

LangChain-backed agent using `llm.model.bind_tools(...)` or `create_agent` after a compatibility spike. It receives the tutor system prompt, recent message history, minimal turn metadata, and available tool schemas. It returns tool calls or final answer messages.

`TutorToolRegistry`

Builds the tool list for a turn. It can expose fewer tools depending on feature flags, user permissions, attachments, and request options.

`TutorToolExecutor`

Executes model-requested tool calls, records tool latency/errors, converts outputs to `ToolMessage`, and appends structured evidence to the turn trace.

`ResponseStreamer`

Owns SSE event formatting, true token streaming for final answers, status events, final `done` payloads, and transcript projection.

`PostTurnPipeline`

Runs controlled side effects after the final answer: session compression, long-term memory update, profile update, quality metrics, and optional evaluation hooks.

## Tool Model

All tutor tools use snake_case names, typed input schemas, concise descriptions, and structured output. Tool outputs should be brief enough to fit the follow-up model call, while full raw details stay in persistence when needed.

### Required Tools

`get_learner_profile`

Reads global or course profile. Inputs include `dimension`, `course_name`, and `reason`. Returns profile markdown plus metadata about freshness and source.

`get_long_term_memory`

Reads chat-owned long-term memory. Inputs include `category` and `reason`. Categories should use existing canonical keys: `learning_background`, `long_term_goals`, `learning_preferences`, `stable_weaknesses`, `interaction_rules`, `effective_strategies`, and `corrections`.

`search_knowledge_base`

Retrieves local knowledge-base passages. Inputs include `query`, `course_name`, `top_k`, and optional filters. Returns ranked snippets with source metadata.

`web_search`

Searches current external information only when freshness matters or the user explicitly asks. It keeps the existing fallback chain but exposes it as one tool.

`get_recent_evaluation`

Reads recent quizzes, weak topics, score trend, and recommendations. The agent should call it when the question asks for study planning, remediation, or personalized practice.

`analyze_attachment`

Analyzes uploaded images or documents. For normal attachment turns, the orchestrator may pre-run a bounded analysis to avoid making the model discover obvious file needs. The same capability should still be available as a tool for follow-up inspection.

### Non-Tool Side Effects

These remain outside the agent tool list:

- Session compression.
- Long-term memory writes.
- Profile writes.
- Message persistence.
- Turn finalization.
- File writes.

The agent may propose durable facts in its answer, but backend services decide whether to persist them.

## Turn Flow

1. API receives `/chat/stream`.
2. `TutorTurnService` validates user, session, message, options, and attachments.
3. `TurnOrchestrator` creates `ChatTurn`, saves the user message, and emits `turn.started`.
4. Optional deterministic prework runs for cheap or required context:
   - attachment classification;
   - file availability validation;
   - recent raw chat history loading;
   - minimal session summary loading.
5. `TutorToolRegistry` exposes tools for the turn.
6. `TutorAgent` invokes the model with bound tools.
7. If the model returns tool calls, `TutorToolExecutor` executes them, records tool events, appends `ToolMessage`s, and loops back to the agent.
8. When the model returns a final answer, `ResponseStreamer` streams answer chunks over SSE and buffers the complete answer.
9. `TurnOrchestrator` persists assistant/tool messages, tool invocations, evidence, knowledge sources, and final transcript state.
10. `PostTurnPipeline` runs compression, long-term memory update, profile update, and quality logging asynchronously with tracked status.

## Performance Design

True streaming is a first-class requirement. The final answer path should use `Llm.astream(...)` or LangChain agent event streaming when available. The streamer must emit chunks as they arrive and still produce a complete answer for persistence.

Tool execution gets per-tool timeout budgets:

- profile and long-term memory: short timeout, degrade to empty result;
- knowledge base: short-to-medium timeout, return partial results if available;
- web search: medium timeout, opt-in unless required by agent/user;
- attachment analysis: longer timeout, status events and graceful degradation.

The orchestrator should avoid eager context fetching. Only minimal session continuity is loaded upfront. Expensive context is pulled through tools when the model needs it.

The first implementation should capture latency metrics for:

- turn total duration;
- time to first status;
- time to first answer token;
- each tool call;
- final persistence;
- post-turn jobs.

## Answer Quality Design

The tutor prompt should teach the agent when to use tools:

- use profile/memory for personalization;
- use knowledge base for domain facts and course material;
- use recent evaluation for remediation and learning plans;
- use web search for time-sensitive claims;
- avoid pretending it knows learner state if the relevant tool was not called or returned empty.

Final answers should follow a tutoring policy:

- answer the student directly first;
- explain with progressive hints when appropriate;
- cite knowledge/evidence when used;
- ask a clarifying question only when necessary;
- include a small check-for-understanding or next practice step for learning-oriented questions;
- state uncertainty instead of inventing facts.

Quality should be tested with a small regression set covering:

- direct conceptual question with no tool call;
- personalized question requiring profile;
- "之前/上次" question requiring long-term memory;
- course-material question requiring knowledge-base search;
- recent/current question requiring web search;
- weak-topic remediation requiring evaluation summary;
- attachment question requiring image/document analysis;
- tool failure fallback.

## Persistence And Observability

The existing transcript-first direction should continue. Each turn should capture:

- normalized user message;
- assistant tool-call messages;
- tool result messages;
- final assistant answer;
- structured tool invocation rows;
- evidence summaries;
- tool latency and status;
- constraint report with max loop, skipped tools, and failures;
- post-turn job status.

This makes later evaluation and debugging possible without replaying live tools.

## Error Handling

Tool failures should not crash the turn by default. The executor converts failures into tool results that the model can reason about, unless the failure is a permission or security issue.

The orchestrator enforces:

- max tool calls per turn;
- max repeated calls to the same tool with equivalent args;
- max total tool duration;
- safe fallback answer when the model cannot complete.

Post-turn failures are recorded and logged, but never block answer delivery.

## Testing Plan

Add architecture tests before implementation:

- tool registry exposes expected tool names and schemas;
- agent loop executes LangChain tool calls and feeds back `ToolMessage`;
- long-term memory uses canonical category keys;
- knowledge-base search returns evidence and sources;
- final answer streams chunks before persistence;
- tool failures are persisted and converted into non-crashing results;
- post-turn pipeline runs after answer completion.

Keep existing tests for history, transcript projection, memory architecture, and teaching diagram behavior.

## Migration Plan

Implement in narrow slices:

1. Add typed tutor tools over existing services without changing the public API.
2. Replace keyword routing in `ReasoningAgent` with LangChain tool calling behind the same orchestrator contract.
3. Introduce `ResponseStreamer` and true final-answer streaming.
4. Move post-turn background work behind `PostTurnPipeline` with tracked statuses.
5. Split large service/orchestrator responsibilities only where each slice needs the boundary.

## Open Decisions Resolved

Use a hybrid architecture, not a fully autonomous agent. The backend keeps deterministic control over persistence, streaming, side effects, and limits.

Use LangChain tool calling for reads and retrieval. Do not expose write/update memory/profile operations as agent-callable tools in the first implementation.

Do not eagerly load profile, long-term memory, knowledge-base results, and evaluation summary into every prompt. Make them tools, with only minimal session continuity loaded upfront.

Keep the current HTTP API shape for the first migration so the frontend does not need to change immediately.
