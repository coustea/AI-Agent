# Observable Chat Compression Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the observable chat compression refactor so every normal chat stream terminates correctly, compression status reflects real backend work, the frontend shows a clear transient compression state, and tests match the new lifecycle.

**Architecture:** Keep session compression in the visible SSE lifecycle after answer persistence and before final `done`. Keep long-term memory and learner profile updates in background jobs. Do not touch the unrelated `resource`, `path`, or `video-render` changes while implementing this chat-focused repair plan.

**Tech Stack:** FastAPI async generator SSE, SQLModel async sessions, pytest/pytest-asyncio, Vue 3 `<script setup lang="ts">`, TypeScript, Vite.

---

## Current Review Findings To Fix

1. `server/app/chat/service.py` only emits final `done` inside `if full_answer and turn_id is not None`, so a normal final event with an empty `final_answer` can leave the frontend waiting forever.
2. `server/tests/chat/test_turn_persistence.py` still mocks and asserts the old post-turn pipeline, including `ChatUseCases._update_learner_profile`, which no longer exists after moving compression into the visible lifecycle.
3. `server/app/chat/service.py` emits `compression_running` before it knows compression is needed, so lightweight sessions can briefly display "正在整理较早的对话上下文..." even when no compression runs.
4. `src/features/chat/views/Tutor.vue` clears `compression_done` immediately, so the user rarely sees completion feedback.
5. `npm run build` currently reports a chat-local type error at `Tutor.vue` timer assignment, plus many unrelated branch errors. Fix the chat-local type error in this plan and report remaining unrelated build failures separately.

## File Structure

- Modify `server/app/chat/service.py`
  - Owns chat SSE lifecycle.
  - Must emit exactly one final `done` for every normal stream.
  - Must return immediately after error `done`.
  - Must keep visible compression between answer persistence and final `done`.

- Modify `server/app/chat/memory/compression.py`
  - Add a read-only `needs_compression()` helper on `ChatSessionCompressor`.
  - Reuse existing `_load_dialogue()` and `_should_compress()` logic.

- Modify `server/app/chat/memory/service.py`
  - Add `should_compress_session()` wrapper that opens `session_scope()` and delegates to the compressor.

- Modify `server/tests/chat/test_observable_compression.py`
  - Add regression tests for empty final answers and no-compression lightweight sessions.
  - Strengthen event-order assertions.

- Modify `server/tests/chat/test_turn_persistence.py`
  - Remove stale `_update_learner_profile` monkeypatch.
  - Update expected post-turn behavior to visible compression plus background memory job.

- Modify `src/features/chat/views/TutorConstants.ts`
  - Type compression stage as a small union.

- Modify `src/features/chat/views/Tutor.vue`
  - Keep `compression_done` visible briefly.
  - Include compression message in `v-memo`.
  - Fix `window.setTimeout` handle typing.

---

### Task 1: Add Backend Regression Tests For Stream Termination

**Files:**
- Modify: `server/tests/chat/test_observable_compression.py`

- [ ] **Step 1: Add shared fake memory helpers**

Append this helper code after the existing imports in `server/tests/chat/test_observable_compression.py`:

```python
class _VisibleCompressionFakeMemory:
    def __init__(self, *, should_compress: bool = True, summary_block=None):
        self.should_compress = should_compress
        self.summary_block = summary_block
        self.saved_messages: list[dict] = []
        self.updated_turns: list[dict] = []
        self.compression_calls: list[dict] = []
        self.counter_calls: list[dict] = []

    async def create_turn(self, **_kwargs):
        return SimpleNamespace(id=11, turn_index=3)

    async def update_turn(self, **kwargs):
        self.updated_turns.append(kwargs)
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

    async def update_post_turn_counters(self, **kwargs):
        self.counter_calls.append(kwargs)
        return {"summary_token_count": 9999 if self.should_compress else 12, "token_delta": 9}

    async def should_compress_session(self, **_kwargs):
        return self.should_compress

    async def compress_session(self, **kwargs):
        self.compression_calls.append(kwargs)
        return self.summary_block
```

- [ ] **Step 2: Add a test for empty final answer still emitting `done`**

Append this test to `server/tests/chat/test_observable_compression.py`:

```python
@pytest.mark.asyncio
async def test_chat_stream_emits_done_when_final_answer_is_empty(monkeypatch):
    from app.chat import service as service_module
    from app.chat.schemas import ChatStreamEvent

    fake_memory = _VisibleCompressionFakeMemory(should_compress=False, summary_block=None)
    monkeypatch.setattr(service_module, "_get_chat_memory_service", lambda: fake_memory)

    async def _fake_build_messages(*_args, **_kwargs):
        return []

    monkeypatch.setattr(service_module, "build_messages", _fake_build_messages)

    def _no_background(self, coro, *, label: str = ""):
        coro.close()

    monkeypatch.setattr(service_module.ChatUseCases, "_spawn_background", _no_background)

    async def fake_agent_chat(_input):
        yield ChatStreamEvent(
            type="final",
            payload={
                "final_answer": "",
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
            session_id="session-empty-final",
            user_input="解释一下",
        )
    ]

    assert events[-1]["event"] == "done"
    assert events[-1]["data"]["session_id"] == "session-empty-final"
    assert events[-1]["data"]["full_response"] == ""
    assert not any(
        event["event"] == "status" and event["data"].get("stage") == "compression_running"
        for event in events
        if isinstance(event.get("data"), dict)
    )
    assert fake_memory.counter_calls == []
    assert fake_memory.compression_calls == []
```

- [ ] **Step 3: Add a test for lightweight sessions skipping `compression_running`**

Append this test to `server/tests/chat/test_observable_compression.py`:

```python
@pytest.mark.asyncio
async def test_chat_stream_skips_compression_running_when_not_needed(monkeypatch):
    from app.chat import service as service_module
    from app.chat.schemas import ChatStreamEvent

    fake_memory = _VisibleCompressionFakeMemory(should_compress=False, summary_block=None)
    monkeypatch.setattr(service_module, "_get_chat_memory_service", lambda: fake_memory)

    async def _fake_build_messages(*_args, **_kwargs):
        return []

    monkeypatch.setattr(service_module, "build_messages", _fake_build_messages)
    monkeypatch.setattr(
        service_module.safety_filter,
        "check",
        lambda text: asyncio.sleep(0, result=service_module.SafetyResult(False, text)),
    )

    def _no_background(self, coro, *, label: str = ""):
        coro.close()

    monkeypatch.setattr(service_module.ChatUseCases, "_spawn_background", _no_background)

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
            session_id="session-lightweight",
            user_input="解释一下",
        )
    ]

    status_stages = [
        event["data"].get("stage")
        for event in events
        if event["event"] == "status" and isinstance(event["data"], dict)
    ]

    assert events[-1]["event"] == "done"
    assert "compression_checking" in status_stages
    assert "compression_running" not in status_stages
    assert "compression_done" in status_stages
    assert events[-1]["data"]["context_compression"]["compressed"] is False
    assert fake_memory.counter_calls
    assert fake_memory.compression_calls == []
```

- [ ] **Step 4: Run tests and confirm failure**

Run:

```bash
rtk uv run pytest tests/chat/test_observable_compression.py -q
```

Expected before implementation:

```text
FAILED test_chat_stream_emits_done_when_final_answer_is_empty
FAILED test_chat_stream_skips_compression_running_when_not_needed
```

- [ ] **Step 5: Commit tests**

Commit only if the repository workflow expects commits during Claude Code execution:

```bash
rtk git add server/tests/chat/test_observable_compression.py
rtk git commit -m "test: cover observable compression stream termination"
```

---

### Task 2: Add Read-Only Compression Need Check

**Files:**
- Modify: `server/app/chat/memory/compression.py`
- Modify: `server/app/chat/memory/service.py`

- [ ] **Step 1: Add `needs_compression()` to the compressor**

In `server/app/chat/memory/compression.py`, inside `class ChatSessionCompressor`, add this method near `maybe_compress()`:

```python
    async def needs_compression(self, *, db: AsyncSession, user_id: int, session_id: str) -> bool:
        """Return whether the current session satisfies compression thresholds."""
        dialogue = await self._load_dialogue(db=db, user_id=user_id, session_id=session_id)
        return await self._should_compress(db=db, user_id=user_id, session_id=session_id, dialogue=dialogue)
```

If `AsyncSession` is not already imported in this file, add it next to the existing SQLModel imports:

```python
from sqlmodel.ext.asyncio.session import AsyncSession
```

- [ ] **Step 2: Add `should_compress_session()` to memory service**

In `server/app/chat/memory/service.py`, add this method immediately before `compress_session()`:

```python
    async def should_compress_session(
        self,
        *,
        user_id: int,
        session_id: str,
    ) -> bool:
        try:
            async with session_scope() as db:
                return await self.compressor.needs_compression(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                )
        except Exception as exc:
            logger.error("[ChatMemoryService] compression need check failed: %s", exc)
            return False
```

- [ ] **Step 3: Run the observable compression tests**

Run:

```bash
rtk uv run pytest tests/chat/test_observable_compression.py -q
```

Expected after only this task:

```text
FAILED test_chat_stream_emits_done_when_final_answer_is_empty
FAILED test_chat_stream_skips_compression_running_when_not_needed
```

The new service method should import and type-check, but service lifecycle is not fixed yet.

- [ ] **Step 4: Commit**

```bash
rtk git add server/app/chat/memory/compression.py server/app/chat/memory/service.py
rtk git commit -m "refactor: expose chat compression need check"
```

---

### Task 3: Fix Chat SSE Lifecycle And Compression Event Semantics

**Files:**
- Modify: `server/app/chat/service.py`
- Test: `server/tests/chat/test_observable_compression.py`

- [ ] **Step 1: Return immediately after agent error event**

In `server/app/chat/service.py`, replace the current `event.type == "error"` block with:

```python
            if event.type == "error":
                has_error = True
                yield {"event": "error", "data": sse_data.get("error", "未知错误")}
                yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
                return
```

- [ ] **Step 2: Replace visible compression and final done block**

In `server/app/chat/service.py`, replace the block starting at `# ── 5. 可见压缩检查/执行 ──` through the final `done` yield with this code:

```python
    # ── 5. 可见压缩检查/执行 ──
    compression_payload: dict[str, Any] = {"compressed": False}

    if not has_error and full_answer and turn_id is not None:
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

            if await svc.should_compress_session(user_id=user_id, session_id=effective_session):
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
            else:
                summary_block = None

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

    if not has_error:
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

- [ ] **Step 3: Update existing observable compression test fake**

In `server/tests/chat/test_observable_compression.py`, update the `FakeMemory` inside `test_chat_stream_emits_compression_status_before_done` by adding:

```python
        async def should_compress_session(self, **_kwargs):
            return True
```

- [ ] **Step 4: Run observable compression tests**

Run:

```bash
rtk uv run pytest tests/chat/test_observable_compression.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit**

```bash
rtk git add server/app/chat/service.py server/tests/chat/test_observable_compression.py
rtk git commit -m "fix: always complete observable chat streams"
```

---

### Task 4: Update Stale Turn Persistence Test For New Lifecycle

**Files:**
- Modify: `server/tests/chat/test_turn_persistence.py`

- [ ] **Step 1: Add new fake memory methods**

In `FakeMemoryService` inside `test_chat_creates_persisted_turn_and_binds_records`, add:

```python
        async def update_post_turn_counters(self, **kwargs):
            self.post_turn_events.append(("counter_update", kwargs))
            return {"summary_token_count": 9999, "token_delta": 128}

        async def should_compress_session(self, **kwargs):
            self.post_turn_events.append(("should_compress", kwargs))
            return True
```

Keep the existing `compress_session()` method, but ensure it accepts the `reason` argument by leaving its `**kwargs` signature unchanged.

- [ ] **Step 2: Remove stale learner profile monkeypatch**

Delete these lines from `server/tests/chat/test_turn_persistence.py`:

```python
    profile_calls: list[dict] = []

    async def fake_update_profile(self, *, user_id: int, session_id: str) -> None:
        fake_memory.post_turn_events.append(("profile_start", {"user_id": user_id, "session_id": session_id}))
        profile_calls.append({"user_id": user_id, "session_id": session_id})

    monkeypatch.setattr(service_module.ChatUseCases, "_update_learner_profile", fake_update_profile)
```

- [ ] **Step 3: Make fake agent expose background method**

Add this method to `FakeTutorAgent`:

```python
        async def run_background_memory_jobs(self, **kwargs):
            fake_memory.post_turn_events.append(("background_memory", kwargs))
```

- [ ] **Step 4: Update assertions**

Replace the final post-turn assertions with:

```python
    assert "post_turn" in background_labels
    assert "memory_pipeline" not in background_labels
    assert "profile_update" not in background_labels

    event_names = [event["event"] for event in events]
    status_stages = [
        event["data"].get("stage")
        for event in events
        if event["event"] == "status" and isinstance(event["data"], dict)
    ]

    assert event_names[-1] == "done"
    assert "compression_checking" in status_stages
    assert "compression_running" in status_stages
    assert "compression_done" in status_stages
    assert events[-1]["data"]["context_compression"]["compressed"] is False

    assert ("counter_update", {
        "user_id": 7,
        "session_id": "session-1",
        "turn_id": 901,
        "user_message": "请解释这个图",
        "assistant_reply": "最终回答",
    }) in fake_memory.post_turn_events
    assert ("should_compress", {"user_id": 7, "session_id": "session-1"}) in fake_memory.post_turn_events
    assert ("compress", {"user_id": 7, "session_id": "session-1", "reason": "post_turn_visible"}) in fake_memory.post_turn_events
    assert any(name == "background_memory" for name, _payload in fake_memory.post_turn_events)
```

This assertion intentionally expects `compressed` to be `False` because the fake `compress_session()` returns `None`. It still verifies that the visible compression path was invoked.

- [ ] **Step 5: Run chat tests**

Run:

```bash
rtk uv run pytest tests/chat/test_observable_compression.py tests/chat/test_turn_persistence.py tests/chat/test_profile_update_scheduling_v2.py -q
```

Expected:

```text
8 passed
```

- [ ] **Step 6: Commit**

```bash
rtk git add server/tests/chat/test_turn_persistence.py
rtk git commit -m "test: align chat turn persistence with visible compression"
```

---

### Task 5: Improve Frontend Compression Status UX And Fix Chat Type Error

**Files:**
- Modify: `src/features/chat/views/TutorConstants.ts`
- Modify: `src/features/chat/views/Tutor.vue`

- [ ] **Step 1: Add typed compression stage**

In `src/features/chat/views/TutorConstants.ts`, add this type near the `ChatMsg` interface:

```ts
export type ContextCompressionStage = 'compression_checking' | 'compression_running' | 'compression_done'
```

Then change the `ChatMsg` fields to:

```ts
  contextCompressionStage?: ContextCompressionStage
  contextCompressionMessage?: string
```

- [ ] **Step 2: Import the new type**

In `src/features/chat/views/Tutor.vue`, update the constants import to include `ContextCompressionStage` as a type import. Use the local import style already present in the file. The result should include:

```ts
import type { ChatMsg, ContextCompressionStage, TeachingDiagram } from './TutorConstants'
```

If `ChatMsg` and `TeachingDiagram` are already imported from the same file, merge the new type into that existing import rather than creating a second import line.

- [ ] **Step 3: Fix timer handle type**

In `src/features/chat/views/Tutor.vue`, change:

```ts
let streamFlushHandle: ReturnType<typeof setTimeout> | null = null
```

to:

```ts
let streamFlushHandle: ReturnType<typeof window.setTimeout> | null = null
```

- [ ] **Step 4: Include compression message in `v-memo`**

In the message row `v-memo` array, add:

```vue
                  msg.contextCompressionMessage,
```

right after:

```vue
                  msg.contextCompressionStage,
```

- [ ] **Step 5: Add completion title helper and clear timer map**

Near the existing `COMPRESSION_STAGES` code in `src/features/chat/views/Tutor.vue`, replace the helper block with:

```ts
const COMPRESSION_STAGES = new Set<ContextCompressionStage>([
  'compression_checking',
  'compression_running',
  'compression_done',
])

const compressionClearTimers = new Map<ChatMsg['id'], ReturnType<typeof window.setTimeout>>()

const getCompressionTitle = (msg: ChatMsg) => {
  return msg.contextCompressionStage === 'compression_done' ? '上下文整理完成' : '上下文整理中'
}

const clearCompressionStatus = (aiMsg?: ChatMsg) => {
  if (!aiMsg) return
  const timer = compressionClearTimers.get(aiMsg.id)
  if (timer != null) {
    window.clearTimeout(timer)
    compressionClearTimers.delete(aiMsg.id)
  }
  aiMsg.contextCompressionStage = undefined
  aiMsg.contextCompressionMessage = undefined
}

const scheduleCompressionClear = (aiMsg: ChatMsg) => {
  const existing = compressionClearTimers.get(aiMsg.id)
  if (existing != null) {
    window.clearTimeout(existing)
  }
  const timer = window.setTimeout(() => {
    aiMsg.contextCompressionStage = undefined
    aiMsg.contextCompressionMessage = undefined
    compressionClearTimers.delete(aiMsg.id)
  }, 1000)
  compressionClearTimers.set(aiMsg.id, timer)
}

const applyCompressionStatus = (aiMsg: ChatMsg, payload: { stage?: string; message?: string }) => {
  if (!payload.stage || !COMPRESSION_STAGES.has(payload.stage as ContextCompressionStage)) return false
  aiMsg.contextCompressionStage = payload.stage as ContextCompressionStage
  aiMsg.contextCompressionMessage = payload.message || '正在整理上下文...'
  if (aiMsg.contextCompressionStage === 'compression_done') {
    scheduleCompressionClear(aiMsg)
  }
  return true
}
```

- [ ] **Step 6: Use dynamic compression title in template**

Replace:

```vue
                    <strong>上下文整理中</strong>
```

with:

```vue
                    <strong>{{ getCompressionTitle(msg) }}</strong>
```

- [ ] **Step 7: Add done-state styling**

In the `<style scoped>` section, add:

```css
.context-compression-card:has(.compression-copy strong) {
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
```

If the project target browsers make `:has()` undesirable, use a class binding instead:

```vue
                <div
                  v-if="msg.contextCompressionStage"
                  :class="['context-compression-card', { 'is-done': msg.contextCompressionStage === 'compression_done' }]"
                >
```

and add:

```css
.context-compression-card.is-done {
  border-color: rgba(22, 163, 74, 0.45);
}
```

Prefer the class binding version because it is more predictable across embedded browsers.

- [ ] **Step 8: Clear compression timers on unmount**

Inside `onBeforeUnmount(() => { ... })`, add:

```ts
  compressionClearTimers.forEach(timer => window.clearTimeout(timer))
  compressionClearTimers.clear()
```

- [ ] **Step 9: Run frontend type check/build**

Run:

```bash
rtk npm run build
```

Expected after this chat-local fix:

```text
src/features/chat/views/Tutor.vue(1113,3): error TS2322
```

must no longer appear.

The command may still fail on unrelated current-branch files such as `src/features/auth/components/OnboardingDialog.vue`, `src/features/learning/views/LearningPathOverview.vue`, `src/features/resource/views/ResourceGenerator.vue`, and `src/video-render/**`. Capture the first 20 remaining errors in the final report instead of editing those domains in this plan.

- [ ] **Step 10: Commit**

```bash
rtk git add src/features/chat/views/TutorConstants.ts src/features/chat/views/Tutor.vue
rtk git commit -m "fix: polish visible chat compression status"
```

---

### Task 6: Verification And Final Review

**Files:**
- Read-only verification across touched files.

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
rtk uv run pytest tests/chat/test_observable_compression.py tests/chat/test_turn_persistence.py tests/chat/test_profile_update_scheduling_v2.py -q
```

Expected:

```text
8 passed
```

- [ ] **Step 2: Run frontend build**

Run:

```bash
rtk npm run build
```

Expected for the chat scope:

```text
No errors from src/features/chat/views/Tutor.vue
No errors from src/features/chat/views/TutorConstants.ts
```

If the command still fails from unrelated branch files, include those filenames in the final report and state that they were outside this chat-compression repair scope.

- [ ] **Step 3: Inspect diff scope**

Run:

```bash
rtk git diff --name-only
```

Expected touched files for this plan:

```text
server/app/chat/service.py
server/app/chat/memory/compression.py
server/app/chat/memory/service.py
server/tests/chat/test_observable_compression.py
server/tests/chat/test_turn_persistence.py
src/features/chat/views/Tutor.vue
src/features/chat/views/TutorConstants.ts
```

If other files appear because they were already dirty before implementation, do not modify them for this plan and mention them in the final report.

- [ ] **Step 4: Manual SSE contract review**

Confirm these facts by reading `server/app/chat/service.py`:

```text
1. Agent error event yields "error", then "done", then returns.
2. Normal streams always yield one final "done".
3. Empty final answer still yields "done".
4. Compression statuses occur before final "done".
5. "compression_running" is emitted only when should_compress_session() returns True.
6. Background job calls run_background_memory_jobs(), not run_post_turn_jobs().
```

- [ ] **Step 5: Final report**

Report:

```text
Implemented observable chat compression repair.

Backend:
- Final done is guaranteed for normal streams.
- Empty final answers no longer leave the frontend waiting.
- Compression checking/running/done happens before final done.
- Long-term memory/profile jobs remain background-only.

Frontend:
- Compression status card shows checking/running and keeps completion visible briefly.
- Chat-local timer type error is fixed.

Verification:
- Focused backend tests: <actual result>
- npm run build: <actual result, including unrelated remaining files if any>
```

---

## Self-Review

Spec coverage:
- Guaranteed `done` after visible compression: Task 3.
- Empty answer termination regression: Task 1 and Task 3.
- Keep compression after answer persistence and before final `done`: Task 3.
- Avoid showing running state when no compression is needed: Task 2 and Task 3.
- Frontend compression animation and completion feedback: Task 5.
- Focused verification: Task 6.

Type consistency:
- `ContextCompressionStage` is defined before it is used in `Tutor.vue`.
- `should_compress_session()` is defined on `ChatMemoryService` before `chat()` calls it.
- `needs_compression()` is defined on `ChatSessionCompressor` before `ChatMemoryService` delegates to it.

Execution boundary:
- This plan deliberately avoids unrelated `resource`, `path`, and `video-render` edits. Those changes are visible in the current worktree but are not required to satisfy the chat compression optimization requirement.
