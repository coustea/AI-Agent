# Dual Entry Resource Path Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the resource-agent dual-entry refactor so standalone resource generation and learning-path node generation both work through clear, separate inputs, while the frontend fully exposes and renders all supported path resources.

**Architecture:** Keep the two domains separate: resource generation calls `generate_resource(ResourceInput)` and path planning calls `generate_node(NodeInput)`. Path resource generation must use node/tutorial context, persist status/error/input data, and let the frontend render resource actions from `node.resource_policy` instead of hard-coded buttons. Remove stale compatibility shims and keep backend schema, tests, and frontend types aligned.

**Tech Stack:** FastAPI, SQLModel, Pydantic, pytest, Vue 3, TypeScript, Vite, Element Plus.

---

## Current Review Summary

The backend core direction is correct:

- `ResourceInput`, `NodeInput`, and `AgentResult` exist in `server/app/resource/schemas.py`.
- Top-level resource agents implement `generate_resource()` and `generate_node()`.
- `PathService.generate_node_resource()` calls `agent.generate_node(node_input)`.
- `PathNodeResource` now has `summary`, `status`, `error_message`, and `input_json`.
- PPT has separate `build_resource_material()` and `build_node_material()`.

Remaining gaps:

- Frontend path node UI still hard-codes `mindmap/code/ppt`.
- Frontend request type still only allows `mindmap/code/ppt`.
- Path resource detail does not render `reading` and `quiz` with dedicated components.
- Path resource history list hard-codes status to `completed`.
- Path tests still import an old module path.
- `npm run build` currently fails.
- PPT has stale `PptConfig` and small manifest/prompt/final-payload mismatches.

Use `rtk` before all shell commands, per repository instructions.

---

## File Structure

### Backend

- Modify `server/app/path/api.py`
  - Return persisted `PathNodeResource.status`, `summary`, and `error_message` in path resource list items.

- Modify `server/app/path/planner.py`
  - Make `is_usable_search_result()` the real public helper.
  - Remove wording that says it is a backward-compatibility alias.
  - Use the same helper internally.

- Modify `server/tests/path/test_path_planner_search_tools.py`
  - Import from `app.path.planner`.

- Modify or add `server/tests/path/test_path_node_resource_list.py`
  - Verify path resource list preserves failed/completed status.

- Modify `server/app/resource/agents/ppt.py`
  - Remove stale local `PptConfig`.

- Modify `server/app/resource/agents/ppt_manifest.py`
  - Align required fields with final frontend payload.

- Modify `server/app/resource/prompts/ppt_slide.md`
  - Align `Formula` and `Terminal` examples with manifest.

- Modify `server/app/resource/agents/ppt_builder.py`
  - Build `Terminal` from `command/output`, while keeping deterministic validation strict.

- Modify `server/app/resource/agents/ppt_internal.py`
  - Validate nested `Timeline.items` and `Terminal.command/output` values.

- Modify `server/tests/resource/test_ppt_internal_multi_agent.py` and `server/tests/resource/test_ppt_agent.py`
  - Update tests for the finalized PPT block contract.

### Frontend

- Modify `src/features/learning/model/path.ts`
  - Add shared `PathResourceType`.
  - Use it in request/resource interfaces.
  - Add `summary`, `status`, `error_message`, and `input_data` to path resource types.

- Modify `src/features/learning/views/LearningPathNode.vue`
  - Render resource generation actions from `workspace.node.resource_policy`.
  - Include `content`, `reading`, and `quiz`.
  - Prevent duplicate buttons.
  - Show required/optional grouping without generating resources at planning time.

- Modify `src/features/learning/views/PathResourceDetail.vue`
  - Render `reading` with `ReadingView`.
  - Render `quiz` with `QuizView`.
  - Show failure state from `status/error_message`.

- Modify `src/features/learning/views/PathResourceHistory.vue`
  - Trust backend status.
  - Keep failed resources visually distinct.

- Modify `src/features/resource/api/resource-history.ts`
  - Add path resource item fields returned by the path API.

- Create or restore `src/shims-markdown-it-katex.d.ts`
  - Declare the missing module so `vue-tsc` passes.

- Fix TypeScript errors in:
  - `src/features/auth/components/OnboardingDialog.vue`
  - `src/features/resource/components/CodeView.vue`

---

## Task 1: Backend Path Resource List Must Return Real Status

**Files:**
- Modify: `server/app/path/api.py`
- Test: `server/tests/path/test_path_node_resource_list.py`

- [ ] **Step 1: Write the failing test**

Create `server/tests/path/test_path_node_resource_list.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.infra.models import PathNode, PathNodeResource
from app.path import api as path_api


class _ExecResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Session:
    def __init__(self, resources, nodes):
        self.resources = resources
        self.nodes = nodes
        self.calls = 0

    async def exec(self, statement):
        self.calls += 1
        if self.calls == 1:
            return _ExecResult(self.resources)
        if self.calls == 2:
            return _ExecResult(self.nodes)
        return _ExecResult(self.resources)


@pytest.mark.asyncio
async def test_path_resource_list_preserves_persisted_status_and_error():
    now = datetime(2026, 6, 15, tzinfo=timezone.utc)
    node = PathNode(
        id=20,
        path_id=1,
        user_id=7,
        node_id="node-1",
        stage_id="stage-1",
        title="变量与类型",
        status="in_progress",
        priority=1,
        prerequisites=[],
    )
    failed = PathNodeResource(
        id=99,
        path_id=1,
        node_id=20,
        user_id=7,
        resource_type="ppt",
        version_no=1,
        title="变量与类型 - PPT",
        content_format="json",
        status="failed",
        error_message="PPT 页数与预期不符",
        summary="PPT 生成失败",
        created_at=now,
        updated_at=now,
    )

    response = await path_api.list_path_resources(
        limit=20,
        offset=0,
        current_user=SimpleNamespace(id=7),
        session=_Session([failed], [node]),
    )

    item = response.data["items"][0]
    assert item["status"] == "failed"
    assert item["error_message"] == "PPT 页数与预期不符"
    assert item["summary"] == "PPT 生成失败"
    assert item["resource_type"] == "ppt"
    assert item["node_title"] == "变量与类型"
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
cd server
rtk uv run pytest tests/path/test_path_node_resource_list.py -q
```

Expected before implementation: failure because list items return `"status": "completed"` and omit `summary/error_message`.

- [ ] **Step 3: Update the API response**

In `server/app/path/api.py`, replace the item dict inside `list_path_resources()` with:

```python
{
    "id": row.id,
    "learning_need": row.title,
    "status": row.status or "completed",
    "error_message": row.error_message,
    "summary": row.summary,
    "resource_types": [row.resource_type],
    "resource_type": row.resource_type,
    "title": row.title,
    "path_id": row.path_id,
    "path_node_id": row.node_id,
    "node_id": node_map.get(row.node_id).node_id if node_map.get(row.node_id) else None,
    "node_title": node_map.get(row.node_id).title if node_map.get(row.node_id) else None,
    "created_at": row.created_at.isoformat() if row.created_at else None,
    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
}
```

- [ ] **Step 4: Run path API tests**

Run:

```bash
cd server
rtk uv run pytest tests/path/test_path_node_resource_list.py tests/path/test_path_service_evaluation.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```bash
rtk git add server/app/path/api.py server/tests/path/test_path_node_resource_list.py
rtk git commit -m "fix: preserve path resource status in history"
```

---

## Task 2: Remove Old Path Planner Test Import and Compatibility Wording

**Files:**
- Modify: `server/app/path/planner.py`
- Modify: `server/tests/path/test_path_planner_search_tools.py`

- [ ] **Step 1: Update the test import**

In `server/tests/path/test_path_planner_search_tools.py`, replace:

```python
from app.path.agents.planner import PathPlannerAgent, repair_generated_plan_from_macro_stages, is_usable_search_result
```

with:

```python
from app.path.planner import PathPlannerAgent, repair_generated_plan_from_macro_stages, is_usable_search_result
```

- [ ] **Step 2: Make the public helper first-class**

In `server/app/path/planner.py`, replace `_is_usable()` and `is_usable_search_result()` with a single public helper:

```python
def is_usable_search_result(result: object) -> bool:
    """判断搜索结果是否可用（非空且不含失败标记词）。"""
    text = str(result or "").strip()
    if not text:
        return False
    return not any(marker in text for marker in _SEARCH_FAILURE_MARKERS)
```

Then replace internal calls:

```python
if is_usable_search_result(direct):
```

and:

```python
usable = [r for r in results if is_usable_search_result(r)]
```

Remove the old `_is_usable()` function entirely.

- [ ] **Step 3: Verify no old import remains**

Run:

```bash
rtk rg -n "app\\.path\\.agents\\.planner|backward compatibility|兼容旧|Public alias" server/app server/tests
```

Expected: no matches for the old planner import or alias comment.

- [ ] **Step 4: Run path planner tests**

Run:

```bash
cd server
rtk uv run pytest tests/path/test_path_planner_search_tools.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
rtk git add server/app/path/planner.py server/tests/path/test_path_planner_search_tools.py
rtk git commit -m "refactor: remove old path planner import"
```

---

## Task 3: Frontend Path Resource Types Must Match Backend

**Files:**
- Modify: `src/features/learning/model/path.ts`
- Modify: `src/features/resource/api/resource-history.ts`

- [ ] **Step 1: Replace resource type definitions**

In `src/features/learning/model/path.ts`, add this near the top:

```ts
export type PathResourceType = 'content' | 'mindmap' | 'code' | 'reading' | 'quiz' | 'ppt'
```

Update `LearningPathResource`:

```ts
export interface LearningPathResource {
  id: number
  resource_type: PathResourceType | string
  version_no: number
  title: string
  content_format: string
  content_text: string | null
  content_json: Record<string, unknown> | null
  summary: string | null
  status: string
  error_message: string | null
  input_data: Record<string, unknown> | null
  metadata: Record<string, unknown>
  created_at: string
}
```

Update `AuxiliaryResourceRequest`:

```ts
export interface AuxiliaryResourceRequest {
  resource_type: PathResourceType
}
```

Update `PathResourceDetail`:

```ts
export interface PathResourceDetail {
  id: number
  resource_type: PathResourceType | string
  version_no: number
  title: string
  content_format: string
  content_text: string | null
  content_json: Record<string, unknown> | null
  summary: string | null
  status: string
  error_message: string | null
  input_data: Record<string, unknown> | null
  metadata: Record<string, unknown>
  created_at: string
}
```

- [ ] **Step 2: Update path history item type**

In `src/features/resource/api/resource-history.ts`, update `PathGeneratedResourceItem`:

```ts
export interface PathGeneratedResourceItem extends GeneratedResourceItem {
  path_id: number | null
  node_id: string | null
  path_node_id: number | null
  node_title: string | null
  resource_type?: string | null
  title?: string | null
  summary?: string | null
  error_message?: string | null
}
```

- [ ] **Step 3: Run TypeScript check**

Run:

```bash
rtk npm run build
```

Expected: build may still fail from known `OnboardingDialog`, `CodeView`, or `markdown-it-katex` issues, but it must not fail because of `AuxiliaryResourceRequest` or path resource field types.

- [ ] **Step 4: Commit**

```bash
rtk git add src/features/learning/model/path.ts src/features/resource/api/resource-history.ts
rtk git commit -m "fix: align path resource frontend types"
```

---

## Task 4: Render Path Resource Buttons from `resource_policy`

**Files:**
- Modify: `src/features/learning/views/LearningPathNode.vue`

- [ ] **Step 1: Add imports**

Update the script imports:

```ts
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getResourceTypeLabel, getResourceUsageHint } from '@/features/resource/model/ResourceGeneratorConstants'
import type { AuxiliaryResourceRequest, LearningPathWorkspace, PathQuizRound, PathQuizSubmitResponse, PathResourceType } from '@/features/learning/model/path'
```

- [ ] **Step 2: Add policy-driven action computation**

Add below `const nodeId = Number(route.params.nodeId || 0)`:

```ts
const supportedPathResourceTypes: PathResourceType[] = ['content', 'mindmap', 'code', 'reading', 'quiz', 'ppt']

const resourceActions = computed(() => {
  const policy = workspace.value?.node.resource_policy
  const orderedTypes = [
    ...(policy?.required_resource_types || []),
    ...(policy?.optional_resource_types || []),
  ]
  const seen = new Set<string>()

  return orderedTypes
    .filter((type): type is PathResourceType => supportedPathResourceTypes.includes(type as PathResourceType))
    .filter((type) => {
      if (seen.has(type)) return false
      seen.add(type)
      return true
    })
    .map((type) => ({
      type,
      label: `生成${getResourceTypeLabel(type)}`,
      hint: getResourceUsageHint(type),
      required: Boolean(policy?.required_resource_types?.includes(type)),
    }))
})
```

- [ ] **Step 3: Replace hard-coded buttons**

Replace the current `resource-actions` block:

```vue
<div class="resource-actions">
  <button class="ghost-btn" :disabled="resourceLoading === 'mindmap'" @click="createResource('mindmap')">生成思维导图</button>
  <button class="ghost-btn" :disabled="resourceLoading === 'code'" @click="createResource('code')">生成代码示例</button>
  <button class="ghost-btn" :disabled="resourceLoading === 'ppt'" @click="createResource('ppt')">生成 PPT</button>
</div>
```

with:

```vue
<div class="resource-actions">
  <button
    v-for="action in resourceActions"
    :key="action.type"
    class="ghost-btn resource-action-btn"
    :disabled="resourceLoading === action.type"
    :title="action.hint"
    @click="createResource(action.type)"
  >
    <span>{{ action.label }}</span>
    <small>{{ action.required ? '推荐' : '可选' }}</small>
  </button>
</div>
```

- [ ] **Step 4: Add minimal button styling**

In the style block, add:

```css
.resource-action-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 42px;
}

.resource-action-btn small {
  color: #64748b;
  font-size: 12px;
}
```

- [ ] **Step 5: Run frontend build**

Run:

```bash
rtk npm run build
```

Expected: no new errors from `LearningPathNode.vue`.

- [ ] **Step 6: Commit**

```bash
rtk git add src/features/learning/views/LearningPathNode.vue
rtk git commit -m "feat: render path resource actions from policy"
```

---

## Task 5: Path Resource Detail Must Render All Supported Resource Types

**Files:**
- Modify: `src/features/learning/views/PathResourceDetail.vue`

- [ ] **Step 1: Add dedicated imports**

Add imports:

```ts
import QuizView from '@/features/resource/components/QuizView.vue'
import ReadingView from '@/features/resource/components/ReadingView.vue'
```

- [ ] **Step 2: Add failure display before render components**

Inside `<section class="detail-card">`, before `MindmapView`, add:

```vue
<div v-if="resource.status === 'failed'" class="error-box">
  <strong>生成失败</strong>
  <p>{{ resource.error_message || resource.summary || '资源生成失败，请返回节点重新生成。' }}</p>
</div>
```

- [ ] **Step 3: Render quiz and reading with existing components**

Update the component branch:

```vue
<MindmapView
  v-if="resource.resource_type === 'mindmap'"
  :result-data="resourceContent"
/>
<CodeView
  v-else-if="resource.resource_type === 'code'"
  :result-data="resourceContent"
/>
<PptView
  v-else-if="resource.resource_type === 'ppt'"
  :result-data="resourceContent"
/>
<QuizView
  v-else-if="resource.resource_type === 'quiz'"
  :result-data="resourceContent"
/>
<ReadingView
  v-else-if="resource.resource_type === 'reading'"
  :result-data="resourceContent"
/>
<MarkdownView
  v-else
  :result-data="resourceContent"
/>
```

- [ ] **Step 4: Add error style**

Add:

```css
.error-box {
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fef2f2;
  color: #991b1b;
}

.error-box p {
  margin: 6px 0 0;
  color: #7f1d1d;
}
```

- [ ] **Step 5: Run frontend build**

Run:

```bash
rtk npm run build
```

Expected: no new errors from `PathResourceDetail.vue`.

- [ ] **Step 6: Commit**

```bash
rtk git add src/features/learning/views/PathResourceDetail.vue
rtk git commit -m "feat: render all path resource detail types"
```

---

## Task 6: Remove PPT Contract Mismatches

**Files:**
- Modify: `server/app/resource/agents/ppt.py`
- Modify: `server/app/resource/agents/ppt_manifest.py`
- Modify: `server/app/resource/prompts/ppt_slide.md`
- Modify: `server/app/resource/agents/ppt_builder.py`
- Modify: `server/app/resource/agents/ppt_internal.py`
- Test: `server/tests/resource/test_ppt_internal_multi_agent.py`

- [ ] **Step 1: Remove stale `PptConfig` from `ppt.py`**

Delete this import and class from `server/app/resource/agents/ppt.py`:

```python
from pydantic import BaseModel


class PptConfig(BaseModel):
    template_id: ThemeType
    topic: str | None = None
    author: str | None = None
    date: str | None = None
```

The only PPT config model should remain `server/app/resource/schemas.py::PptConfig`.

- [ ] **Step 2: Align manifest with final payload**

In `server/app/resource/agents/ppt_manifest.py`, change:

```python
"Formula": ["latex", "description"],
"Terminal": ["commands"],
```

to:

```python
"Formula": ["latex"],
"Terminal": ["command", "output"],
```

- [ ] **Step 3: Align prompt examples**

In `server/app/resource/prompts/ppt_slide.md`, replace:

```markdown
- Formula: `{"latex": "E=mc^2", "description": "质能方程"}`
- Terminal: `{"commands": ["npm start", "echo done"]}`
```

with:

```markdown
- Formula: `{"latex": "E=mc^2"}`
- Terminal: `{"command": "npm start", "output": "server started"}`
```

- [ ] **Step 4: Update Terminal builder**

In `server/app/resource/agents/ppt_builder.py`, replace the `Terminal` case with:

```python
case "Terminal":
    return BlockTerminal(
        id=block_id,
        type="Terminal",
        command=str(self._required(rendered, "command")),
        output=str(self._required(rendered, "output")),
    )
```

- [ ] **Step 5: Add nested required-value validation**

In `server/app/resource/agents/ppt_internal.py`, add:

```python
def _validate_nested_required_value(block_type: str, field_name: str, value: Any) -> bool:
    if _is_empty_required_value(value):
        return False

    if block_type == "Timeline" and field_name == "items":
        if not isinstance(value, list):
            return False
        for item in value:
            if not isinstance(item, dict):
                return False
            if _is_empty_required_value(item.get("time")):
                return False
            if _is_empty_required_value(item.get("title")):
                return False

    return True
```

Then replace:

```python
if _is_empty_required_value(block.data[field_name]):
```

with:

```python
if not _validate_nested_required_value(block.type, field_name, block.data[field_name]):
```

- [ ] **Step 6: Update tests for Terminal and Formula**

In PPT tests that create or assert `BlockContract.required_fields`, use:

```python
BlockContract(
    block_id="formula-1",
    type="Formula",
    slot="left",
    required_fields=["latex"],
)
```

and:

```python
BlockContract(
    block_id="terminal-1",
    type="Terminal",
    slot="right",
    required_fields=["command", "output"],
)
```

Rendered terminal data should use:

```python
RenderedBlock(
    block_id="terminal-1",
    type="Terminal",
    data={"command": "python main.py", "output": "ok"},
)
```

- [ ] **Step 7: Run PPT tests**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_ppt_agent.py tests/resource/test_ppt_internal_multi_agent.py tests/resource/test_ppt_standalone.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
rtk git add server/app/resource/agents/ppt.py server/app/resource/agents/ppt_manifest.py server/app/resource/prompts/ppt_slide.md server/app/resource/agents/ppt_builder.py server/app/resource/agents/ppt_internal.py server/tests/resource/test_ppt_internal_multi_agent.py server/tests/resource/test_ppt_agent.py
rtk git commit -m "fix: align ppt block contract with frontend payload"
```

---

## Task 7: Fix Frontend Build Blockers

**Files:**
- Create: `src/shims-markdown-it-katex.d.ts`
- Modify: `src/features/auth/components/OnboardingDialog.vue`
- Modify: `src/features/resource/components/CodeView.vue`

- [ ] **Step 1: Restore katex module declaration**

Create `src/shims-markdown-it-katex.d.ts`:

```ts
declare module 'markdown-it-katex' {
  import type MarkdownIt from 'markdown-it'

  const markdownItKatex: MarkdownIt.PluginSimple
  export default markdownItKatex
}
```

- [ ] **Step 2: Fix `OnboardingDialog.vue` unused and optional-type errors**

In `src/features/auth/components/OnboardingDialog.vue`:

- Remove unused `isComplete` if it is not referenced.
- For any call passing `string | undefined` to a `string` parameter, use a local fallback:

```ts
const safeText = maybeText || ''
```

- When updating a message array item, preserve required fields:

```ts
messages.value[index] = {
  id: messages.value[index]?.id ?? Date.now(),
  role: messages.value[index]?.role ?? 'assistant',
  content: nextContent,
  time: messages.value[index]?.time ?? new Date().toLocaleTimeString(),
  streaming: messages.value[index]?.streaming,
}
```

Use the actual local variable names already present in the file.

- [ ] **Step 3: Fix `CodeView.vue` nullable computed errors**

In `src/features/resource/components/CodeView.vue`, avoid template access to possibly null `parsedData`. Add a non-null fallback computed:

```ts
const safeParsedData = computed(() => parsedData.value || {
  language: '',
  code: '',
  explanation: '',
  filename: '',
  commands: [],
})
```

Then use `safeParsedData` in the template where `parsedData` currently causes nullability errors.

For DOM copy text, replace unsafe `innerText` access with:

```ts
const text = target instanceof HTMLElement ? target.innerText : target.textContent || ''
```

- [ ] **Step 4: Run frontend build**

Run:

```bash
rtk npm run build
```

Expected: `vue-tsc -b && vite build` completes successfully.

- [ ] **Step 5: Commit**

```bash
rtk git add src/shims-markdown-it-katex.d.ts src/features/auth/components/OnboardingDialog.vue src/features/resource/components/CodeView.vue
rtk git commit -m "fix: restore frontend build"
```

---

## Task 8: Final Verification and No-Old-Runtime Audit

**Files:**
- No source edits unless verification exposes a failure.

- [ ] **Step 1: Verify old runtime types are gone**

Run:

```bash
rtk rg -n "WorkerState|WorkerResult" server/app server/tests src
```

Expected: only tests asserting absence are allowed:

```text
server/tests/resource/test_agent_dual_entry.py:65:    assert not hasattr(schemas, "WorkerState")
server/tests/resource/test_agent_dual_entry.py:66:    assert not hasattr(schemas, "WorkerResult")
```

- [ ] **Step 2: Verify old path planner import is gone**

Run:

```bash
rtk rg -n "app\\.path\\.agents\\.planner|Public alias kept|backward compatibility|兼容旧代码" server/app server/tests
```

Expected: no matches.

- [ ] **Step 3: Run backend resource and path tests**

Run:

```bash
cd server
rtk uv run pytest tests/resource tests/path -q
```

Expected: pass.

- [ ] **Step 4: Run frontend build**

Run:

```bash
rtk npm run build
```

Expected: pass.

- [ ] **Step 5: Manual code review checklist**

Check:

- `ResourceService` calls `generate_resource()` only.
- `PathService` calls `generate_node()` only.
- Path node resource buttons come from `node.resource_policy`.
- Path node resource request can send `content`, `mindmap`, `code`, `reading`, `quiz`, and `ppt`.
- Path resource detail renders `content`, `mindmap`, `code`, `reading`, `quiz`, and `ppt`.
- Failed path resources show `failed` status in list and detail.
- PPT final payload does not require unconsumed fields.

- [ ] **Step 6: Commit verification-only changes if any were needed**

If Task 8 required source edits, commit them:

```bash
rtk git add server src
rtk git commit -m "fix: complete resource path verification"
```

If no source edits were needed, do not create an empty commit.

---

## Acceptance Criteria

The refactor is complete only when all of these are true:

- `ResourceService` invokes resource agents through `generate_resource(ResourceInput)`.
- `PathService` invokes resource agents through `generate_node(NodeInput)`.
- No top-level resource agent exposes or depends on `WorkerState` or `WorkerResult`.
- Path node generation supports all six resource types: `content`, `mindmap`, `code`, `reading`, `quiz`, `ppt`.
- Frontend path node page renders generation buttons from `resource_policy`.
- Path resource detail uses dedicated viewers for `mindmap`, `code`, `ppt`, `quiz`, and `reading`; `content` uses Markdown.
- Failed path resources preserve and display `status` and `error_message`.
- PPT manifest, prompt, builder, and frontend payload schema agree on block fields.
- `cd server && rtk uv run pytest tests/resource tests/path -q` passes.
- `rtk npm run build` passes.

---

## Notes for Claude Code

- Do not add compatibility wrappers for old `WorkerState`, `WorkerResult`, or `app.path.agents.planner`.
- Do not merge standalone resource records with path node resource records.
- Do not make path planning generate resources during plan creation. It should only generate `resource_policy`; actual resources are generated from the node workspace.
- Keep function names direct:
  - `generate_resource`
  - `generate_node`
  - `build_resource_material`
  - `build_node_material`
  - `is_usable_search_result`
- Keep commits focused. If the working tree already has unrelated changes, leave them alone.
