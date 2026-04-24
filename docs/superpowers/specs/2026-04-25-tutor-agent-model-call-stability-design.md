# Tutor Agent Model Call Stability Design

## Purpose

The current chat API reaches the TutorAgent graph successfully, but the answer stage fails when Spark Max is used inside the deepagents runtime. The observed failure is an OpenAI-compatible Spark response:

```text
HTTP 400 invalid data code=10003
```

The fix must preserve the intended model roles:

- DeepSeek handles reasoning, tool use, RAG/search delegation, and intermediate agent work.
- Spark Max produces the final user-facing Chinese answer.

The main design goal is to make model calls stable by ensuring each provider receives only the message and parameter shapes it is known to support.

## Current Context

Backend chat runs through `server/app/chat/agent.py`.

The outer LangGraph currently routes:

```text
START -> classify -> direct_answer | attachment_answer -> END
```

Inside the answer node, the code calls a deepagents graph created with `create_deep_agent(...)`. The main deepagent currently uses Spark Max as its model, while subagents use DeepSeek. This means Spark receives deepagents middleware output and agent-shaped message payloads. The logs show the failing request is sent to:

```text
https://spark-api-open.xf-yun.com/v1/chat/completions
```

The failure happens inside the deepagents model node before a final assistant answer is produced.

## Requirements

- Keep LangGraph as the outer chat orchestration layer.
- Use DeepSeek for agent reasoning, tool selection, RAG search, web search, and intermediate answer synthesis.
- Use Spark Max only for final answer writing.
- Do not pass tool calls, tool schemas, `ToolMessage`, deepagents middleware messages, or complex content lists to Spark Max.
- If Spark Max fails, return a useful DeepSeek-generated answer instead of failing the chat request.
- If DeepSeek fails, return a clear SSE error because there is no reliable reasoning result to summarize.
- Keep logs useful for debugging without printing API keys or full large prompts at `INFO`.
- Preserve current auth, session, upload, memory, and SSE behavior.

## Proposed Architecture

Split the current answer execution into two explicit model stages.

```text
User message and prepared context
 -> LangGraph classify
 -> direct_answer or attachment_answer
 -> DeepSeek reasoning deepagent
 -> plain text reasoning_answer
 -> Spark Max final answer call
 -> final answer text
 -> SSE token + done
 -> save assistant message
```

### Reasoning Stage

Create or rename the existing deepagent cache to represent reasoning agents.

The reasoning agent uses:

- DeepSeek chat model.
- Existing RAG subagent.
- Existing researcher subagent when `enable_search=true`.
- Existing tool exclusion middleware.
- Existing recursion limit and thread id config.

The reasoning stage returns a plain text `reasoning_answer`. It should be suitable as a fallback answer and as source material for Spark Max.

### Final Answer Stage

Spark Max is called as a normal chat model, not as a deepagent.

Spark receives exactly:

- One `SystemMessage`.
- One `HumanMessage`.

The `SystemMessage` describes Spark's role as final answer writer:

```text
You are the final answer model. Answer in Chinese. Only use the provided material. Do not mention internal agents, tools, or workflow.
```

The `HumanMessage` contains compact plain text:

- User question.
- Relevant conversation/context summary already prepared by the existing runtime.
- Attachment pre-analysis context when present.
- DeepSeek reasoning answer.

Spark must not receive:

- Deepagents message history.
- Tool call metadata.
- Tool schemas.
- `ToolMessage`.
- Non-string multimodal content blocks.

## Error Handling

### DeepSeek Failure

If the reasoning deepagent raises an exception:

- Log at `ERROR` with stage, provider, model, and sanitized error code/message.
- Yield an SSE `error` event.
- Do not call Spark Max.
- Do not save an assistant message.

### Spark Failure

If Spark Max raises an exception:

- Log at `WARNING` with stage, provider, model, and sanitized error code/message.
- Use `reasoning_answer` as the final answer.
- Continue normal SSE output and assistant message persistence.

### Empty Or Invalid Spark Output

If Spark returns empty, too short, or otherwise unusable text:

- Retry Spark once with a stricter final-answer prompt.
- If still unusable, fall back to `reasoning_answer`.

## Logging

Keep these at `INFO`:

- Chat request start and end.
- Graph construction.
- Reasoning stage failure.
- Spark fallback activation.
- Final termination reason.

Keep these at `DEBUG`:

- Route decision details.
- Reasoning answer preview.
- Spark final prompt preview.
- Spark answer preview.
- LangGraph and deepagents debug output controlled by existing debug env vars.

Never log:

- API keys.
- Full prompts at `INFO`.
- Full message history by default.

## Testing Plan

Add focused backend tests around `server/app/chat/agent.py`.

Tests should verify:

- The reasoning stage uses DeepSeek/deepagents rather than Spark.
- Spark final answer call receives only `SystemMessage` and `HumanMessage`.
- Spark final answer call receives no tool calls, tool schemas, `ToolMessage`, or deepagents message history.
- Spark success returns Spark text.
- Spark failure falls back to the DeepSeek reasoning answer.
- Spark invalid output retries once, then falls back if needed.
- DeepSeek failure returns an SSE error and does not call Spark.

After unit tests, verify the real API with curl:

```text
POST /api/v1/users
POST /api/v1/users/auth
POST /api/v1/ai/chat/sessions
POST /api/v1/ai/chat/stream
GET  /api/v1/ai/chat/history
```

The chat stream is considered healthy when it emits:

- a `status` event,
- a `token` event with a usable answer,
- a `done` event,
- and chat history contains both user and assistant messages.

## Implementation Boundaries

Do not refactor unrelated auth, database, frontend, or memory code.

The implementation should stay mostly inside:

- `server/app/chat/agent.py`
- targeted tests under `server/tests/resource/`

Small helper changes in `server/app/infra/llm.py` are acceptable only if they make provider metadata or final-call construction clearer.

## Open Decisions

The user has decided:

- DeepSeek is the reasoning model.
- Spark Max is the final answer model.

The implementation should preserve that decision and make it explicit in code naming.
