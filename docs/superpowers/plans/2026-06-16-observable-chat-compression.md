# Observable Chat Compression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make chat session compression explicit and observable after each streamed AI answer, keep only the latest 1-2 turns as raw history, and show a frontend animation while the backend is compacting context.

**Architecture:** Move post-answer compression out of an invisible background-only path and into the chat SSE lifecycle before the final `done` event. Keep long-term memory and profile updates as background work, but make compression check/run/done visible to the active client. Remove duplicate session summary injection so the next turn receives exactly one summary context plus recent raw messages.

**Tech Stack:** FastAPI async SSE, SQLModel async sessions, Vue 3 `<script setup lang="ts">`, TypeScript, Element Plus icons/styles already used by `Tutor.vue`, pytest, `npm run build`.

---

## Current Context

Important existing files:

- `server/app/chat/service.py`
  - Owns `chat()` SSE orchestration, message persistence, `build_messages()`, and post-turn background spawning.
  - Currently emits `done` as soon as `TutorAgent` emits `final`, before assistant persistence and before compression.
  - `build_messages()` currently injects a `SystemMessage` containing session summaries.
- `server/app/chat/agent.py`
  - `TutorAgent.run_post_turn_jobs()` currently updates counters, tries compression, then long-term memory or profile jobs.
  - `_answer_node()` also injects `session_summary` into the tutor system prompt, causing duplicate summary context when `build_messages()` also injects summary.
- `server/app/chat/memory/compression.py`
  - `ChatSessionCompressor` keeps `keep_recent=8` messages by default.
  - Its delete logic only deletes old messages when `keep_recent > 0`; it needs explicit support if future config sets `keep_recent=0`.
- `server/app/chat/memory/service.py`
  - `update_post_turn_counters()` increments `summary_token_count`.
  - `compress_session()` calls the compressor in `session_scope()`.
- `server/app/config.py` and `server/config.yaml`
  - Existing config has `compress_min_messages`, `compress_min_tokens`, and `summary_context_blocks`.
- `src/features/chat/views/Tutor.vue`
  - Owns stream callbacks and message rendering.
  - Already renders status stages through `msg.searchStage` / `msg.searchMessage`.
- `src/features/chat/views/TutorConstants.ts`
  - Owns `ChatMsg`.
- `src/features/chat/model/useChatStreamManager.ts`
  - Treats SSE `done` as stream completion.
- `src/shared/api/sse.ts`
  - Calls `onDone()` immediately when event name is `done`.

Desired event timeline:

```text
token...
status: answer_done
status: persisting_turn
status: compression_checking
status: compression_running       # only when threshold is reached
status: compression_done           # only after compression succeeds or skips
done                               # final stream completion, after visible compression path
```

Next-turn prompt shape:

```text
Tutor system prompt
  includes session_summary once
Recent raw history
  latest 1-2 turns only after compression trims older messages
Current user message
```

---

## File Structure

Modify:

- `server/config.yaml`
  - Add `memory.compress_keep_recent_messages: 4`.
- `server/app/config.py`
  - Add `COMPRESS_KEEP_RECENT_MESSAGES`.
- `server/app/chat/memory/service.py`
  - Pass `COMPRESS_KEEP_RECENT_MESSAGES` into `ChatSessionCompressor`.
- `server/app/chat/memory/compression.py`
  - Make `keep_recent` deletion robust for `0`, `2`, or `4`.
  - Return a block with enough metadata already present on `ChatSessionSummaryBlock`.
- `server/app/chat/service.py`
  - Stop `build_messages()` from injecting summary.
  - Keep `session_summary` loaded once and pass it through `TutorAgentInput`.
  - Delay final SSE `done` until after assistant persistence and compression check/run.
  - Emit visible status events for compression.
  - Spawn background work for LTM/profile after compression, without compressing again.
- `server/app/chat/agent.py`
  - Refactor `run_post_turn_jobs()` to no longer perform compression.
  - Rename or split into a background-only method, for example `run_background_memory_jobs()`.
  - Keep long-term memory/profile scheduling behavior intact.
- `server/app/chat/schemas.py`
  - Add optional stream event literal values only if service chooses to emit typed internal events. If service emits plain SSE status dictionaries directly, no schema change is needed.
- `src/features/chat/views/TutorConstants.ts`
  - Add `contextCompressionStage?: string` and `contextCompressionMessage?: string` to `ChatMsg`.
- `src/features/chat/views/Tutor.vue`
  - Handle compression status stages in both normal stream and resubscribe stream callbacks.
  - Render a compact animated “上下文整理中” block after the AI answer bubble.
  - Clear compression animation on `compression_done`, `done`, or error.

Create:

- `server/tests/chat/test_observable_compression.py`
  - Focused service-level tests for SSE ordering and duplicate summary removal.

---

## Event Contract

Use existing SSE `status` events. Do not introduce a new top-level SSE event unless frontend needs separate routing later.

Status payloads:

```json
{
  "stage": "answer_done",
  "message": "回答已生成，正在保存本轮学习记录..."
}
```

```json
{
  "stage": "compression_checking",
  "message": "正在检查是否需要整理上下文..."
}
```

```json
{
  "stage": "compression_running",
  "message": "正在整理较早的对话上下文..."
}
```

```json
{
  "stage": "compression_done",
  "message": "上下文整理完成，后续回答会继续使用摘要记忆。",
  "compressed": true,
  "summary_block_id": 123,
  "summarized_message_count": 12
}
```

Skipped compression:

```json
{
  "stage": "compression_done",
  "message": "当前上下文仍然轻量，无需整理。",
  "compressed": false
}
```

Error handling:

```json
{
  "stage": "compression_done",
  "message": "上下文整理暂时失败，本轮回答已保存。",
  "compressed": false,
  "error": "..."
}
```

Do not fail the chat turn if compression fails. The user already received a valid answer.

---

### Task 1: Configure Recent Raw Message Retention

**Files:**

- Modify: `server/config.yaml`
- Modify: `server/app/config.py`
- Modify: `server/app/chat/memory/service.py`
- Modify: `server/app/chat/memory/compression.py`
- Test: `server/tests/chat/test_observable_compression.py`

- [ ] **Step 1: Add failing compressor config test**

Create `server/tests/chat/test_observable_compression.py`:

```python
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_chat_memory_service_uses_configured_recent_message_retention(monkeypatch):
    import app.chat.memory.service as memory_service_module

    monkeypatch.setattr(memory_service_module, "COMPRESS_KEEP_RECENT_MESSAGES", 4)

    service = memory_service_module.ChatMemoryService(module="mentor")

    assert service.compressor.keep_recent == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd server
uv run pytest tests/chat/test_observable_compression.py::test_chat_memory_service_uses_configured_recent_message_retention -q
```

Expected: FAIL because `COMPRESS_KEEP_RECENT_MESSAGES` does not exist or the compressor still uses the hard-coded value.

- [ ] **Step 3: Add config value**

In `server/config.yaml`, under `memory:` add:

```yaml
  compress_keep_recent_messages: 4
```

In `server/app/config.py`, near the existing memory config values add:

```python
COMPRESS_KEEP_RECENT_MESSAGES = get("memory.compress_keep_recent_messages", 4)
```

In `server/app/chat/memory/service.py`, update the config import to include `COMPRESS_KEEP_RECENT_MESSAGES`, then update compressor construction:

```python
self.compressor = ChatSessionCompressor(
    module=module,
    keep_recent=COMPRESS_KEEP_RECENT_MESSAGES,
    min_messages=COMPRESS_MIN_MESSAGES,
    min_tokens=COMPRESS_MIN_TOKENS,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd server
uv run pytest tests/chat/test_observable_compression.py::test_chat_memory_service_uses_configured_recent_message_retention -q
```

Expected: PASS.

- [ ] **Step 5: Harden compressor delete logic for zero retention**

In `server/app/chat/memory/compression.py`, replace the stale message deletion block with:

```python
if self.keep_recent > 0:
    first_kept = dialogue[-self.keep_recent].id
    stale_filter = ChatMessage.id < first_kept
else:
    stale_ids = [msg.id for msg in target if msg.id is not None]
    first_kept = None

if self.keep_recent > 0 and first_kept:
    stale_messages = list(
        (
            await db.exec(
                select(ChatMessage).where(
                    ChatMessage.user_id == user_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.module == self.module,
                    ChatMessage.id < first_kept,
                )
            )
        ).all()
    )
elif self.keep_recent == 0:
    stale_messages = list(
        (
            await db.exec(
                select(ChatMessage).where(
                    ChatMessage.user_id == user_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.module == self.module,
                    ChatMessage.id.in_(stale_ids),
                )
            )
        ).all()
    )
else:
    stale_messages = []

for msg in stale_messages:
    await db.delete(msg)
```

This preserves current behavior for `keep_recent=4`, while making future `keep_recent=0` safe.

- [ ] **Step 6: Commit**

```bash
git add server/config.yaml server/app/config.py server/app/chat/memory/service.py server/app/chat/memory/compression.py server/tests/chat/test_observable_compression.py
git commit -m "feat: configure chat compression retention"
```

---

### Task 2: Remove Duplicate Session Summary Injection

**Files:**

- Modify: `server/app/chat/service.py`
- Test: `server/tests/chat/test_observable_compression.py`

- [ ] **Step 1: Add failing `build_messages` test**

Append to `server/tests/chat/test_observable_compression.py`:

```python
import asyncio
from dataclasses import dataclass
from datetime import datetime


@dataclass
class _FakeMessage:
    id: int
    role: str
    content: str
    created_at: datetime
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


def test_build_messages_does_not_inject_summary_system_message(monkeypatch):
    from app.chat import service

    class FakeMemoryService:
        async def list_messages(self, **_kwargs):
            return [
                _FakeMessage(
                    id=1,
                    role="user",
                    content="上一轮问题",
                    created_at=datetime(2026, 6, 16, 8, 0),
                )
            ]

        async def list_tool_invocations(self, **_kwargs):
            return []

        async def get_session_summary_context(self, **_kwargs):
            raise AssertionError("build_messages must not read summary context")

    monkeypatch.setattr(service, "_get_chat_memory_service", lambda: FakeMemoryService())

    messages = asyncio.run(service.build_messages(user_id=7, session_id="session-1"))

    assert len(messages) == 1
    assert messages[0].content == "上一轮问题"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd server
uv run pytest tests/chat/test_observable_compression.py::test_build_messages_does_not_inject_summary_system_message -q
```

Expected: FAIL because `build_messages()` calls `get_session_summary_context()` and prepends a `SystemMessage`.

- [ ] **Step 3: Modify `build_messages()`**

In `server/app/chat/service.py`, remove the summary context read and final `SystemMessage` prepend from `build_messages()`.

Replace:

```python
# 注入会话压缩摘要到 SystemMessage
summary_context = await svc.get_session_summary_context(user_id=user_id, session_id=session_id)
system_content = f"以下是之前对话的压缩摘要，供你了解上下文：\n{summary_context}"

return [SystemMessage(content=system_content), *messages]
```

With:

```python
return messages
```

Also update the docstring so it says `build_messages()` only converts recent persisted messages; the session summary is loaded separately and injected once by `TutorAgent`.

- [ ] **Step 4: Run focused tests**

Run:

```bash
cd server
uv run pytest tests/chat/test_observable_compression.py::test_build_messages_does_not_inject_summary_system_message tests/chat/test_turn_persistence.py -q
```

Expected: PASS or only failures directly caused by tests asserting the old duplicate summary behavior. Update old tests only if they explicitly expected the removed `SystemMessage`.

- [ ] **Step 5: Commit**

```bash
git add server/app/chat/service.py server/tests/chat/test_observable_compression.py
git commit -m "refactor: inject chat session summary once"
```

---

### Task 3: Make Compression Visible Before Final SSE Done

**Files:**

- Modify: `server/app/chat/service.py`
- Modify: `server/app/chat/agent.py`
- Test: `server/tests/chat/test_observable_compression.py`
- Update: `server/tests/chat/test_turn_persistence.py`
- Update: `server/tests/chat/test_profile_update_scheduling_v2.py`

- [ ] **Step 1: Add failing SSE ordering test**

Append to `server/tests/chat/test_observable_compression.py`:

```python
import time
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_chat_stream_emits_compression_status_before_done(monkeypatch):
    from app.chat import service as service_module
    from app.chat.schemas import ChatStreamEvent

    class FakeMemory:
        def __init__(self):
            self.saved_messages: list[dict] = []
            self.background_labels: list[str] = []

        async def create_turn(self, **_kwargs):
            return SimpleNamespace(id=11, turn_index=3)

        async def update_turn(self, **_kwargs):
            return None

        async def save_message(self, **kwargs):
            self.saved_messages.append(kwargs)
            return SimpleNamespace(id=len(self.saved_messages))

        async def count_messages(self, **_kwargs):
            return len(self.saved_messages)

        async def generate_session_title(self, **_kwargs):
            return "title"

        async def append_turn_event(self, **_kwargs):
            return None

        async def finalize_turn_transcript(self, **_kwargs):
            return None

        async def get_session_summary_context(self, **_kwargs):
            return "历史摘要"

        async def update_post_turn_counters(self, **_kwargs):
            return {"summary_token_count": 9999, "token_delta": 4000}

        async def compress_session(self, **_kwargs):
            return SimpleNamespace(id=88, summarized_message_count=10)

    fake_memory = FakeMemory()
    monkeypatch.setattr(service_module, "_get_chat_memory_service", lambda: fake_memory)
    monkeypatch.setattr(service_module, "build_messages", lambda **_kwargs: asyncio.sleep(0, result=[]))
    monkeypatch.setattr(
        service_module.safety_filter,
        "check",
        lambda text: asyncio.sleep(0, result=service_module.SafetyResult(False, text)),
    )

    async def fake_agent_chat(_input):
        yield ChatStreamEvent(type="answer_token", payload={"token": "回答"}, sequence=1, timestamp=time.time())
        yield ChatStreamEvent(
            type="final",
            payload={
                "final_answer": "回答",
                "diagram_result": None,
                "tool_invocations": [],
                "sources": [],
                "attachment_analyses": [],
            },
            sequence=2,
            timestamp=time.time(),
        )

    class FakeTutorAgent:
        def chat(self, input):
            return fake_agent_chat(input)

        async def run_background_memory_jobs(self, **_kwargs):
            return None

    monkeypatch.setattr(service_module, "TutorAgent", FakeTutorAgent)

    events = [
        event
        async for event in service_module.chat(
            user_id=7,
            session_id="session-1",
            user_input="解释一下",
        )
    ]

    names = [event["event"] for event in events]
    status_stages = [
        event["data"].get("stage")
        for event in events
        if event["event"] == "status" and isinstance(event["data"], dict)
    ]

    assert names[-1] == "done"
    assert "compression_checking" in status_stages
    assert "compression_running" in status_stages
    assert "compression_done" in status_stages
    assert names.index("done") > max(i for i, event in enumerate(events) if event["event"] == "status")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd server
uv run pytest tests/chat/test_observable_compression.py::test_chat_stream_emits_compression_status_before_done -q
```

Expected: FAIL because current service emits `done` inside the agent event loop before compression.

- [ ] **Step 3: Delay `done` until after persistence/compression**

In `server/app/chat/service.py`, inside the `async for event in agent.chat(agent_input):` loop, change `event.type == "final"` handling:

- Keep collecting `full_answer`, diagram, tool invocations, sources, and attachment analyses.
- Still yield `diagram` if present.
- Do not yield `done` there.
- Yield a `status` event instead:

```python
yield {
    "event": "status",
    "data": {
        "stage": "answer_done",
        "message": "回答已生成，正在保存本轮学习记录...",
    },
}
continue
```

After assistant persistence and turn finalization, add visible compression orchestration before the final `done`:

```python
compression_payload: dict[str, Any] = {"compressed": False}

if full_answer and turn_id is not None:
    yield {
        "event": "status",
        "data": {
            "stage": "compression_checking",
            "message": "正在检查是否需要整理上下文...",
        },
    }
    try:
        counters = await svc.update_post_turn_counters(
            user_id=user_id,
            session_id=effective_session,
            turn_id=turn_id,
            user_message=current_message,
            assistant_reply=full_answer,
        )
        compression_payload["counters"] = counters
        yield {
            "event": "status",
            "data": {
                "stage": "compression_running",
                "message": "正在整理较早的对话上下文...",
            },
        }
        summary_block = await svc.compress_session(
            user_id=user_id,
            session_id=effective_session,
            reason="post_turn_visible",
        )
        if summary_block is not None:
            compression_payload.update(
                {
                    "compressed": True,
                    "summary_block_id": getattr(summary_block, "id", None),
                    "summarized_message_count": int(getattr(summary_block, "summarized_message_count", 0) or 0),
                }
            )
            compression_message = "上下文整理完成，后续回答会继续使用摘要记忆。"
        else:
            compression_message = "当前上下文仍然轻量，无需整理。"
    except Exception as exc:
        logger.error("[chat] visible compression failed user=%s session=%s err=%s", user_id, effective_session, exc)
        compression_payload.update({"compressed": False, "error": str(exc)})
        compression_message = "上下文整理暂时失败，本轮回答已保存。"

    yield {
        "event": "status",
        "data": {
            "stage": "compression_done",
            "message": compression_message,
            **compression_payload,
        },
    }
```

Then emit the final `done` after this block:

```python
yield {
    "event": "done",
    "data": {
        "session_id": effective_session,
        "full_response": full_answer,
        "knowledge_sources": sources,
        "teaching_diagram": diagram_result,
        "tool_calls": [
            {"id": inv.get("tool_name", ""), "name": inv.get("tool_name", ""), "args": inv.get("payload", {})}
            for inv in tool_invocations
        ],
        "attachment_analyses": attachment_analyses,
        "context_compression": compression_payload,
    },
}
```

- [ ] **Step 4: Refactor agent background jobs to avoid second compression**

In `server/app/chat/agent.py`, rename `run_post_turn_jobs()` to `run_background_memory_jobs()` or add a new method with that name.

The new method must:

- Not call `update_post_turn_counters()`.
- Not call `compress_session()`.
- Keep `should_update_long_term_memory()`, `update_long_term_memory()`, and profile update behavior.
- Persist `memory.update.start` and `memory.update.done` events as before, but use payload stage `background_post_turn`.

Keep a compatibility wrapper during the refactor:

```python
async def run_post_turn_jobs(self, **kwargs) -> None:
    await self.run_background_memory_jobs(**kwargs)
```

This prevents unrelated tests from failing immediately.

- [ ] **Step 5: Update service background spawn**

In `server/app/chat/service.py`, change `_post_turn()` to call `agent.run_background_memory_jobs(...)` instead of `agent.run_post_turn_jobs(...)`.

Pass the same arguments:

```python
await agent.run_background_memory_jobs(
    user_id=user_id,
    session_id=effective_session,
    turn_id=turn_id,
    user_message=current_message,
    assistant_reply=full_answer,
    turn_index=turn_index,
)
```

- [ ] **Step 6: Update affected tests**

In `server/tests/chat/test_turn_persistence.py`, replace old expectations that `fake_memory.post_turn_events` include token count and compression in the background task. Expected shape becomes:

```python
assert any(
    event["event"] == "status"
    and isinstance(event["data"], dict)
    and event["data"].get("stage") == "compression_done"
    for event in events
)
assert "post_turn" in background_labels
```

If the fake memory object lacks `update_post_turn_counters()`, add it with:

```python
async def update_post_turn_counters(self, **kwargs):
    self.post_turn_events.append(("token_count", kwargs))
    return {"summary_token_count": 4000}
```

If it lacks `compress_session()`, keep:

```python
async def compress_session(self, **kwargs):
    self.post_turn_events.append(("compress", kwargs))
    return None
```

In `server/tests/chat/test_profile_update_scheduling_v2.py`, update tests to call `run_background_memory_jobs()` directly, or leave them on `run_post_turn_jobs()` if the compatibility wrapper remains. Remove assertions that compression methods were called by that method.

- [ ] **Step 7: Run focused backend tests**

Run:

```bash
cd server
uv run pytest tests/chat/test_observable_compression.py tests/chat/test_turn_persistence.py tests/chat/test_profile_update_scheduling_v2.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add server/app/chat/service.py server/app/chat/agent.py server/tests/chat/test_observable_compression.py server/tests/chat/test_turn_persistence.py server/tests/chat/test_profile_update_scheduling_v2.py
git commit -m "feat: expose chat compression over stream"
```

---

### Task 4: Add Frontend Compression State and Animation

**Files:**

- Modify: `src/features/chat/views/TutorConstants.ts`
- Modify: `src/features/chat/views/Tutor.vue`

- [ ] **Step 1: Extend message state**

In `src/features/chat/views/TutorConstants.ts`, update `ChatMsg`:

```ts
export interface ChatMsg {
  id: number
  role: 'user' | 'ai'
  content: string
  time: string
  attachments?: Attachment[] | null
  teachingDiagram?: TeachingDiagram | null
  teachingDiagramGenerating?: boolean
  searchStage?: string
  searchMessage?: string
  contextCompressionStage?: string
  contextCompressionMessage?: string
}
```

- [ ] **Step 2: Add a small helper in `Tutor.vue`**

Near the existing stream helper functions in `src/features/chat/views/Tutor.vue`, add:

```ts
const COMPRESSION_STAGES = new Set([
  'compression_checking',
  'compression_running',
  'compression_done',
])

const applyCompressionStatus = (aiMsg: ChatMsg, payload: { stage?: string; message?: string }) => {
  if (!payload.stage || !COMPRESSION_STAGES.has(payload.stage)) return false
  if (payload.stage === 'compression_done') {
    aiMsg.contextCompressionStage = undefined
    aiMsg.contextCompressionMessage = undefined
    return true
  }
  aiMsg.contextCompressionStage = payload.stage
  aiMsg.contextCompressionMessage = payload.message || '正在整理上下文...'
  return true
}

const clearCompressionStatus = (aiMsg?: ChatMsg) => {
  if (!aiMsg) return
  aiMsg.contextCompressionStage = undefined
  aiMsg.contextCompressionMessage = undefined
}
```

- [ ] **Step 3: Handle compression status in both stream callbacks**

In both `onEvent` handlers in `Tutor.vue`:

```ts
if (evt.event === 'status') {
  const payload = evt.data as { stage?: string; message?: string }
  const aiMsg = messages.value.find(m => m.id === aiMsgId)
  if (!aiMsg) return

  if (applyCompressionStatus(aiMsg, payload)) {
    aiMsg.searchStage = undefined
    aiMsg.searchMessage = undefined
    scrollToBottom()
    return
  }

  // existing status-stage handling continues here
}
```

In both `onDone` handlers, before or after `teachingDiagramGenerating = false`, call:

```ts
clearCompressionStatus(aiMsg)
```

In both `onError` handlers, call:

```ts
clearCompressionStatus(aiMsg)
```

- [ ] **Step 4: Render compression animation after the AI answer**

In the message template, after the answer bubble and before attachments or teaching diagram blocks, add:

```vue
<div v-if="msg.contextCompressionStage" class="context-compression-card">
  <div class="compression-orbit" aria-hidden="true">
    <span></span>
    <span></span>
    <span></span>
  </div>
  <div class="compression-copy">
    <strong>上下文整理中</strong>
    <span>{{ msg.contextCompressionMessage || '正在整理较早的对话上下文...' }}</span>
  </div>
</div>
```

- [ ] **Step 5: Add scoped styles**

In `src/features/chat/views/Tutor.vue` `<style scoped>`, add:

```css
.context-compression-card {
  display: flex;
  align-items: center;
  gap: 10px;
  width: fit-content;
  max-width: min(520px, 100%);
  margin-top: 8px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  box-shadow: var(--shadow-sm);
}

.compression-orbit {
  position: relative;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
}

.compression-orbit span {
  position: absolute;
  inset: 6px;
  border: 2px solid transparent;
  border-top-color: #0891b2;
  border-radius: 50%;
  animation: compression-spin 1s linear infinite;
}

.compression-orbit span:nth-child(2) {
  inset: 3px;
  border-top-color: #16a34a;
  animation-duration: 1.4s;
  animation-direction: reverse;
}

.compression-orbit span:nth-child(3) {
  inset: 9px;
  border-top-color: #64748b;
  animation-duration: 0.8s;
}

.compression-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.compression-copy strong {
  font-size: 0.88rem;
  font-weight: var(--weight-semibold);
  color: var(--color-text);
  line-height: 1.35;
}

.compression-copy span {
  font-size: 0.8rem;
  line-height: 1.45;
  color: var(--color-text-secondary);
}

@keyframes compression-spin {
  to {
    transform: rotate(360deg);
  }
}
```

Do not use decorative gradient blobs. Keep the animation compact and work-focused.

- [ ] **Step 6: Run frontend type/build check**

Run:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/features/chat/views/TutorConstants.ts src/features/chat/views/Tutor.vue
git commit -m "feat: show chat compression progress"
```

---

### Task 5: End-to-End Verification and Cleanup

**Files:**

- Modify only if verification reveals issues.

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
cd server
uv run pytest tests/chat/test_observable_compression.py tests/chat/test_turn_persistence.py tests/chat/test_profile_update_scheduling_v2.py tests/chat/test_history.py -q
```

Expected: PASS, except do not spend time on the known unrelated stale tests listed in `AGENTS.md`.

- [ ] **Step 2: Run frontend build**

Run:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 3: Manual SSE smoke test**

Start backend:

```bash
cd server
uv run fastapi dev app/main.py --port 9999
```

Start frontend in a separate terminal:

```bash
npm run dev
```

Manual behavior:

1. Open the chat UI.
2. Send enough messages to exceed `memory.compress_min_messages` or lower the threshold temporarily in local config for a smoke test.
3. Observe the AI answer streaming normally.
4. After text finishes, observe the compact “上下文整理中” animation.
5. Confirm it disappears when the final SSE `done` event arrives.
6. Refresh history and confirm older raw messages were summarized/deleted while the latest 1-2 turns remain.

- [ ] **Step 4: Inspect duplicate-summary prompt path**

Run:

```bash
rtk rg -n "以下是之前对话的压缩摘要|get_session_summary_context\\(" server/app/chat -g '*.py'
```

Expected:

- `get_session_summary_context()` is called by service-level orchestration to populate `TutorAgentInput.session_summary`.
- `TutorAgent._answer_node()` injects that summary into the tutor system prompt.
- `build_messages()` does not prepend another summary `SystemMessage`.

- [ ] **Step 5: Final commit if cleanup was needed**

```bash
git status --short
git add <changed-files>
git commit -m "test: verify observable chat compression"
```

---

## Self-Review

Spec coverage:

- Visible backend compression after AI answer: covered by Task 3.
- Frontend animation while backend compresses: covered by Task 4.
- Keep latest 1-2 turns: covered by Task 1 with `compress_keep_recent_messages: 4`.
- Avoid repeated history/summary injection: covered by Task 2.
- Preserve long-term memory/profile behavior: covered by Task 3 background method refactor and focused tests.

Placeholder scan:

- No unresolved placeholder markers remain.
- Every task has concrete files, snippets, commands, and expected outcomes.

Type consistency:

- Frontend uses `contextCompressionStage` and `contextCompressionMessage` consistently.
- Backend status stages are string payloads routed through existing SSE `status` handling.
- Background method name is `run_background_memory_jobs()` with `run_post_turn_jobs()` kept as a compatibility wrapper.
