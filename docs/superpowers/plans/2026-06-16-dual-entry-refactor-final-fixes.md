# Dual Entry Refactor Final Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the remaining cleanup for the dual-entry resource/path refactor so backend path/resource tests pass, frontend remains buildable, and no stale path planner compatibility imports or old contract fields remain.

**Architecture:** Keep standalone resource generation and learning-path node generation separate. Resource generation must call `generate_resource(ResourceInput)`, while path node resources must call `generate_node(NodeInput)` with node/tutorial context. Do not add compatibility modules such as `app.path.agents.planner`; update stale tests and contracts to the new code instead.

**Tech Stack:** FastAPI, SQLModel, Pydantic, pytest, Vue 3, TypeScript, Vite.

---

## Current State

Frontend validation currently passes:

```bash
rtk npm run build
```

Backend focused validation currently fails:

```bash
cd server
rtk uv run pytest tests/resource tests/path -q
```

Observed result:

```text
5 failed, 181 passed, 1 skipped
```

The failing areas are:

- stale imports from `app.path.agents.planner`
- stale `adjustment_rationale` path plan contract expectation
- stale `strategy_report` parameter in planner repair test
- missing startup repair for required `generated_resources.source` database column
- stale PPT test fixture using `commands` instead of `command/output`

---

## File Structure

### Backend Tests

- Modify `server/tests/resource/test_resource_refactoring.py`
  - Replace stale `app.path.agents.planner` import with `app.path.planner`.
  - Change the old `adjustment_rationale` assertion into an assertion that the new plan contract excludes legacy rationale fields.

- Modify `server/tests/path/test_resource_policy.py`
  - Replace stale `app.path.agents.planner` import with `app.path.planner`.

- Modify `server/tests/path/test_path_planner_search_tools.py`
  - Remove stale `strategy_report=` argument from `repair_generated_plan_from_macro_stages()`.

- Modify `server/tests/resource/test_ppt_internal_multi_agent.py`
  - Replace stale Terminal fixture field `commands` with manifest fields `command/output`.

### Backend Source

- Modify `server/app/infra/database.py`
  - Add one focused current-schema repair function for `generated_resources.source`.
  - Call it during `init_db()` after connection validation and before seed imports.
  - This is a current required column repair, not an old API compatibility shim.

### Frontend Source

- Modify `src/features/learning/views/LearningPathNode.vue`
  - Include `primary_resource_type` before required and optional resource lists.
  - Use all supported path resource types as fallback when policy is absent or empty.

- Modify `src/features/learning/views/PathResourceHistory.vue`
  - Show failed resource error text in resource history cards.
  - Show summary for completed resources when available.

---

## Task 1: Synchronize Path Planner Tests With New Module Path

**Files:**
- Modify: `server/tests/resource/test_resource_refactoring.py`
- Modify: `server/tests/path/test_resource_policy.py`

- [ ] **Step 1: Replace stale imports**

In `server/tests/resource/test_resource_refactoring.py`, replace:

```python
from app.path.agents.planner import PathPlannerAgent
```

with:

```python
from app.path.planner import PathPlannerAgent
```

In `server/tests/path/test_resource_policy.py`, replace:

```python
from app.path.agents.planner import PathPlannerAgent
```

with:

```python
from app.path.planner import PathPlannerAgent
```

- [ ] **Step 2: Verify no stale planner package import remains**

Run:

```bash
rtk rg -n "app\.path\.agents\.planner" server/tests server/app
```

Expected output: no matches.

- [ ] **Step 3: Run the affected tests**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_resource_refactoring.py::test_path_planner_uses_request_knowledge_preferences_and_plans_all_stages tests/path/test_resource_policy.py::test_path_planner_agent_no_longer_exposes_adjust_plan -q
```

Expected output:

```text
2 passed
```

- [ ] **Step 4: Commit**

```bash
rtk git add server/tests/resource/test_resource_refactoring.py server/tests/path/test_resource_policy.py
rtk git commit -m "test: update path planner imports"
```

---

## Task 2: Remove Legacy `adjustment_rationale` From Path Plan Tests

**Files:**
- Modify: `server/tests/resource/test_resource_refactoring.py`

- [ ] **Step 1: Replace the stale contract test**

In `server/tests/resource/test_resource_refactoring.py`, replace the whole test currently named:

```python
def test_path_plan_contract_persists_percentage_confidence_and_rationale_items():
```

with:

```python
def test_path_plan_contract_keeps_percentage_confidence_and_excludes_legacy_rationale():
    from app.path.schemas import AgentLearningPathPlan, AgentStage, AgentPathNode

    plan = AgentLearningPathPlan(
        title="操作系统进阶路径",
        confidence=82,
        stages=[AgentStage(stage_id="stage-1", title="基础", description="基础阶段")],
        nodes=[AgentPathNode(node_id="n1", stage_id="stage-1", title="节点1")],
    )

    assert plan.confidence == 82
    assert not hasattr(plan, "adjustment_rationale")
```

Do not add `adjustment_rationale` back to `AgentLearningPathPlan`. The current planner prompt explicitly forbids that field, so the test must match the new contract.

- [ ] **Step 2: Run the specific test**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_resource_refactoring.py::test_path_plan_contract_keeps_percentage_confidence_and_excludes_legacy_rationale -q
```

Expected output:

```text
1 passed
```

- [ ] **Step 3: Check prompt/schema alignment**

Run:

```bash
rtk rg -n "adjustment_rationale" server/app/path server/tests
```

Expected remaining matches:

```text
server/app/path/prompts/planner_system.md:... - adjustment_rationale
```

No test should require this field to exist.

- [ ] **Step 4: Commit**

```bash
rtk git add server/tests/resource/test_resource_refactoring.py
rtk git commit -m "test: align path plan contract with current schema"
```

---

## Task 3: Remove Legacy `strategy_report` Argument From Planner Repair Test

**Files:**
- Modify: `server/tests/path/test_path_planner_search_tools.py`

- [ ] **Step 1: Update the repair call**

In `server/tests/path/test_path_planner_search_tools.py`, replace:

```python
repaired = repair_generated_plan_from_macro_stages(
    plan=plan,
    macro_stages=stages,
    request=CreateLearningPathRequest(goal="系统学习 Python 编程", topic="Python"),
    strategy_report="基于画像判断需要循序渐进学习",
)
```

with:

```python
repaired = repair_generated_plan_from_macro_stages(
    plan=plan,
    macro_stages=stages,
    request=CreateLearningPathRequest(goal="系统学习 Python 编程", topic="Python"),
)
```

- [ ] **Step 2: Run the affected test**

Run:

```bash
cd server
rtk uv run pytest tests/path/test_path_planner_search_tools.py::test_repair_generated_plan_recovers_empty_final_output_from_macro_stages -q
```

Expected output:

```text
1 passed
```

- [ ] **Step 3: Verify no stale parameter remains**

Run:

```bash
rtk rg -n "strategy_report=" server/tests server/app/path
```

Expected output: no matches.

- [ ] **Step 4: Commit**

```bash
rtk git add server/tests/path/test_path_planner_search_tools.py
rtk git commit -m "test: update path plan repair contract"
```

---

## Task 4: Restore Current-Schema Database Repair For `generated_resources.source`

**Files:**
- Modify: `server/app/infra/database.py`
- Test: `server/tests/resource/test_database_session_resilience.py`

**Decision:** Keep this repair. `generated_resources.source` is part of the current source/model contract and is required to separate standalone resource history from path resources. This is not a legacy API compatibility shim; it is a startup safeguard for the current schema in environments without a migration runner.

- [ ] **Step 1: Add the repair function**

In `server/app/infra/database.py`, after `check_all()` and before `init_db()`, add:

```python
async def _repair_generated_resource_source_column() -> None:
    """Ensure generated_resources.source exists for current resource-domain queries."""
    async with engine.begin() as conn:
        exists = await conn.execute(text("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'generated_resources'
              AND column_name = 'source'
        """))
        if exists.scalar():
            return

        await conn.execute(text(
            "ALTER TABLE generated_resources ADD COLUMN source VARCHAR(255)"
        ))
        await conn.execute(text("""
            UPDATE generated_resources
            SET source = 'path_node'
            WHERE id IN (
                SELECT DISTINCT resource_id
                FROM generated_resource_items
                WHERE path_node_id IS NOT NULL
            )
        """))
        await conn.execute(text("""
            UPDATE generated_resources
            SET source = 'standalone'
            WHERE source IS NULL
        """))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_generated_resources_source "
            "ON generated_resources (source)"
        ))
```

- [ ] **Step 2: Call the repair during startup**

In `init_db()`, after the connection validation log and before school/quiz seed imports, add:

```python
    try:
        await _repair_generated_resource_source_column()
    except Exception as exc:
        logger.warning("[Database] generated_resources.source 修复失败（非致命）: %s", exc)
```

The top of `init_db()` should now look like:

```python
async def init_db() -> None:
    """初始化数据库：验证连接 + 按需导入种子数据。

    表结构和扩展由外部管理（init_schema.sql），后端仅负责 CRUD。
    """
    if not await _test_connection():
        logger.error(
            "[Database] 无法建立数据库连接，请检查数据库服务是否运行: url=%s",
            engine.url.render_as_string(hide_password=True),
        )
        raise OperationalError("数据库连接失败", {}, None)

    logger.info("[Database] 数据库连接验证通过: url=%s debug=%s",
                engine.url.render_as_string(hide_password=True), DEBUG)

    try:
        await _repair_generated_resource_source_column()
    except Exception as exc:
        logger.warning("[Database] generated_resources.source 修复失败（非致命）: %s", exc)

    # 按需导入学校数据（表为空时才导入）
```

- [ ] **Step 3: Run the failing database test**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_database_session_resilience.py::test_init_db_repairs_generated_resource_source_column -q
```

Expected output:

```text
1 passed
```

- [ ] **Step 4: Run database resilience tests**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_database_session_resilience.py -q
```

Expected output: all tests pass.

- [ ] **Step 5: Commit**

```bash
rtk git add server/app/infra/database.py
rtk git commit -m "fix: repair resource source column on startup"
```

---

## Task 5: Update PPT Terminal Test Fixture To Current Contract

**Files:**
- Modify: `server/tests/resource/test_ppt_internal_multi_agent.py`

- [ ] **Step 1: Replace stale `commands` fixture**

In `server/tests/resource/test_ppt_internal_multi_agent.py`, in `test_fails_for_unsupported_block_type_in_slot`, replace:

```python
required_fields=["commands"],
```

with:

```python
required_fields=["command", "output"],
```

This keeps the test focused on the actual violation: `Terminal` is not allowed in the `FocusTitle.main` slot.

- [ ] **Step 2: Verify no stale PPT terminal field remains**

Run:

```bash
rtk rg -n "required_fields=\\[\"commands\"\\]|commands" server/app/resource server/tests/resource/test_ppt_internal_multi_agent.py server/app/resource/prompts
```

Expected output: no matches related to PPT Terminal contract. If unrelated prose appears, update it to `command/output`.

- [ ] **Step 3: Run PPT tests**

Run:

```bash
cd server
rtk uv run pytest tests/resource/test_ppt_internal_multi_agent.py tests/resource/test_ppt_agent.py tests/resource/test_ppt_standalone.py -q
```

Expected output: all selected tests pass.

- [ ] **Step 4: Commit**

```bash
rtk git add server/tests/resource/test_ppt_internal_multi_agent.py
rtk git commit -m "test: align ppt terminal contract"
```

---

## Task 6: Improve Path Node Resource Action Ordering

**Files:**
- Modify: `src/features/learning/views/LearningPathNode.vue`

**Reason:** Current UI uses required + optional resources, but ignores `primary_resource_type`. The backend policy includes `primary_resource_type`, so the frontend should prioritize it. If policy is missing or empty, fallback should expose all supported path resource types, not only `mindmap/code/ppt`.

- [ ] **Step 1: Update fallback list and ordering**

In `src/features/learning/views/LearningPathNode.vue`, replace the current `resourceActions` computed block with:

```ts
const supportedPathResourceTypes: PathResourceType[] = ['content', 'mindmap', 'code', 'reading', 'quiz', 'ppt']

const resourceActions = computed(() => {
  const policy = workspace.value?.node?.resource_policy
  const fallback: PathResourceType[] = supportedPathResourceTypes
  const orderedTypes = policy
    ? [
        policy.primary_resource_type,
        ...policy.required_resource_types,
        ...policy.optional_resource_types,
      ].filter(Boolean)
    : fallback
  const seen = new Set<string>()

  return (orderedTypes.length ? orderedTypes : fallback)
    .filter((type): type is PathResourceType => supportedPathResourceTypes.includes(type as PathResourceType))
    .filter((type) => {
      if (seen.has(type)) return false
      seen.add(type)
      return true
    })
    .map((type) => ({
      type,
      label: resourceTypeLabel(type),
      required: Boolean(
        type === policy?.primary_resource_type ||
        policy?.required_resource_types?.includes(type),
      ),
    }))
})
```

- [ ] **Step 2: Build frontend**

Run:

```bash
rtk npm run build
```

Expected output:

```text
✓ built
```

- [ ] **Step 3: Commit**

```bash
rtk git add src/features/learning/views/LearningPathNode.vue
rtk git commit -m "fix: prioritize path resource policy actions"
```

---

## Task 7: Show Failed Path Resource Error In History

**Files:**
- Modify: `src/features/learning/views/PathResourceHistory.vue`

**Reason:** Backend now preserves `status`, `summary`, and `error_message`. The history page should surface failed generation reasons instead of only showing a status tag.

- [ ] **Step 1: Add summary/error text to card body**

In `src/features/learning/views/PathResourceHistory.vue`, inside the resource history card template after the title/meta block and before the resource type tags, add:

```vue
<p v-if="item.status === 'failed' && item.error_message" class="resource-card-error">
  {{ item.error_message }}
</p>
<p v-else-if="item.summary" class="resource-card-summary">
  {{ item.summary }}
</p>
```

- [ ] **Step 2: Add scoped styles**

In the same file style block, add:

```css
.resource-card-summary,
.resource-card-error {
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.5;
}

.resource-card-summary {
  color: #64748b;
}

.resource-card-error {
  color: #b91c1c;
}
```

- [ ] **Step 3: Build frontend**

Run:

```bash
rtk npm run build
```

Expected output:

```text
✓ built
```

- [ ] **Step 4: Commit**

```bash
rtk git add src/features/learning/views/PathResourceHistory.vue
rtk git commit -m "fix: show path resource generation errors"
```

---

## Task 8: Final Verification

**Files:**
- No source changes unless verification exposes a new issue.

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
cd server
rtk uv run pytest tests/resource tests/path -q
```

Expected output:

```text
passed
```

The exact count may change, but there must be zero failures and zero collection errors.

- [ ] **Step 2: Run frontend build**

Run from repo root:

```bash
rtk npm run build
```

Expected output:

```text
✓ built
```

- [ ] **Step 3: Audit stale contract names**

Run:

```bash
rtk rg -n "app\.path\.agents\.planner|WorkerState|WorkerResult|PathNodeResourceRequest|GeneratePathRequest|AgentCoursePathPlan|strategy_report=|required_fields=\\[\"commands\"\\]" server/app server/tests src
```

Expected output:

```text
server/tests/resource/test_agent_dual_entry.py:... assert not hasattr(schemas, "WorkerState")
server/tests/resource/test_agent_dual_entry.py:... assert not hasattr(schemas, "WorkerResult")
server/tests/resource/test_resource_refactoring.py:... assert not hasattr(schemas, "PathNodeResourceRequest")
server/tests/path/test_resource_policy.py:... assert not hasattr(schemas, "AgentCoursePathPlan")
server/tests/path/test_resource_policy.py:... assert not hasattr(schemas, "GeneratePathRequest")
server/tests/path/test_resource_policy.py:... assert not hasattr(schemas, "PathNodeResourceRequest")
```

Only negative assertion tests should remain. There must be no source imports, no source schema exports, and no compatibility shim.

- [ ] **Step 4: Commit any final verification-only test updates**

If Task 8 required no changes, do not commit.

If Task 8 exposed and fixed a small issue, commit with:

```bash
rtk git add <changed-files>
rtk git commit -m "fix: complete dual entry refactor cleanup"
```

---

## Completion Criteria

The refactor is complete only when all of the following are true:

- `cd server && rtk uv run pytest tests/resource tests/path -q` has zero failures.
- `rtk npm run build` succeeds.
- No app code imports `app.path.agents.planner`.
- No compatibility module is added under `server/app/path/agents/`.
- `AgentLearningPathPlan` does not expose `adjustment_rationale`.
- `repair_generated_plan_from_macro_stages()` is called without `strategy_report`.
- `generated_resources.source` exists in model, init schema, and startup repair.
- PPT Terminal contract consistently uses `command/output`, not `commands`.
- Path node UI exposes `content/mindmap/code/reading/quiz/ppt` through `resource_policy`.
- Path resource history and detail both show failed resource status and error message.

