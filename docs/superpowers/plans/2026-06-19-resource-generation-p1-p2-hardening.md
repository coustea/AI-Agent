# Resource Generation P1/P2 Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不处理 P0 配置凭据、不修改测试文件、不恢复旧协议兼容的前提下，使独立资源多智能体生成满足“Planning 致命、其他 Agent 隔离、成功立即持久化、事件仅观测、PPT 严格生成、前端只展示有效持久化卡片”。

**Architecture:** 保留现有 LangGraph 外部编排和 PPT 内部 Director + 并行 Chapter Writer 两阶段结构。用一个函数统一非 Planning Agent 生命周期；数据库作为最终成功状态的唯一事实来源；SSE 事件不参与业务成败；PPT 从配置、来源、模板、预算到前端渲染都执行同一套严格契约。

**Tech Stack:** Python 3.13、FastAPI、LangGraph、SQLModel、PostgreSQL、Pydantic v2、Vue 3、TypeScript、Vite。

---

## 0. 不可变边界

- 不修改 `server/config.yaml` 中本次审核标记的 P0 项。
- 不修改 `server/tests/**`；现有测试变更也不回退、不覆盖，只在交付报告中说明。
- 不增加 `PptPayload`、`PPT_TEMPLATE_MANIFEST` 等旧名称，不让旧测试驱动兼容层回归。
- 不修改 LLM JSON 模式、重试次数、prompt fallback 策略；`server/app/infra/llm.py` 只删除重复空构造函数。
- 不合并 `resource` 与 `path` 的表、记录、API、详情页或持久化模型。
- 不增加 Review/Repair Agent，不做生成后的补漏。
- 不使用默认内容、占位资源、替代来源、通用布局、旧格式转换或降级渲染。
- 不为减少文件而把 PPT contract、Agent 和 Vue renderer 塞回单个大文件；减少的是无意义包装和重复生命周期代码。

## 1. 修改内容总览

| 顺序 | 修改内容 | 核心结果 |
|---|---|---|
| 1 | SSE 事件改为纯观测并统一新事件名 | 事件失败永不改变 Agent/任务结果 |
| 2 | 收敛非 Planning Agent 生命周期 | 基础 Agent、PPT、Video 使用同一失败隔离规则 |
| 3 | 加固即时持久化与最终状态不变量 | 只有验证并提交成功的 Agent 才算成功 |
| 4 | 对齐 SQLModel、初始化 SQL、一次性迁移 | 唯一约束无重复索引、无自动清理和兼容逻辑 |
| 5 | 收紧 PPT 配置、来源与模板选择 | 非法输入立即使 PPT Agent 失败，不替换默认值 |
| 6 | 执行 PPT block 预算 | 模板预算真正约束 Chapter Writer 输出 |
| 7 | 前端仅展示有效持久化资源 | 不再虚构学习路径、时间、卡片类型或无效 PPT 卡片 |
| 8 | 删除资源模块死代码和兼容残留 | 代码更短，调用方向更清晰 |
| 9 | 完整验收 | 能明确判断每条业务规则是否成立 |

---

### Task 1: 让事件彻底脱离业务成败，并原子替换旧事件名

**Files:**
- Modify: `server/app/resource/events.py`
- Modify: `server/app/resource/api.py`
- Modify: `server/app/resource/service.py`
- Modify: `server/app/resource/orchestrator.py`
- Modify: `src/features/resource/api/resource.ts`
- Modify: `src/features/resource/model/resource.ts`
- Modify: `src/features/resource/views/ResourceGenerator.vue`

- [ ] **Step 1: 将粗粒度事件名一次性改成新协议**

只保留以下事件：

```text
agent.status
agent.snapshot
agent.step
agent.heartbeat
agent.artifact_ready
resource.done
```

`AgentEventType` 改成上述 Literal；`emit_agent()` 生成 `agent.status`；`emit_done()` 生成 `resource.done`。后端 SSE 和前端 EventSource 同一个提交内完成替换，禁止双发、双监听和别名映射。

- [ ] **Step 2: SSE 直接复用正式认证依赖并校验资源归属**

`stream_resource_events()` 不再自行调用 `decode_token()`。签名改为注入现有认证和请求级会话：

```python
async def stream_resource_events(
    resource_id: int,
    current_user: User = Depends(get_current_user_flexible),
    session: AsyncSession = Depends(get_session),
):
    service = ResourceService(session)
    resource = await service.get_resource(
        current_user.id,
        resource_id,
        allowed_sources=STANDALONE_RESOURCE_SOURCES,
    )
    if resource is None:
        return HttpResponse.error(code=404, message="资源不存在或无权限")
```

必须使用 `get_current_user_flexible`，让 query token 也经过 `ActiveToken` 白名单、过期检查和用户查询。禁止只解码 JWT，也禁止在认证依赖内部使用 `session_scope()`。

- [ ] **Step 3: 修正快照回放和终态竞态**

资源归属验证成功后先订阅 EventBus，再读取快照。回放时只复制字段并覆盖为新事件名，不能同时通过位置参数和 `**snapshot` 重复传入 `event_type`：

```python
queue = resource_event_bus.subscribe(resource_id)
snapshot_data = {
    key: value
    for key, value in agent_snapshot.items()
    if key in AgentEvent.model_fields and key != "event_type"
}
snapshot_event = AgentEvent(event_type="agent.snapshot", **snapshot_data)
```

删除“只有 `current_message` 时伪造无 agent_id 事件”的分支。订阅成功后必须 `await session.refresh(resource)` 或重新按 user/resource 查询一次父资源，不能使用订阅前鉴权查询得到的旧 status。若刷新后的状态是 `completed`、`partial_completed` 或 `failed`，回放快照后立即发送一次 `resource.done` 并结束；否则消费订阅队列，并且只在收到 `resource.done` 时退出。由于队列在终态刷新前已经建立，终态切换不会丢事件。所有返回路径都在 `finally` 中 unsubscribe。

- [ ] **Step 4: 在事件发射边界吞掉观测异常并记录日志**

`AgentEventEmitter.emit()` 的业务语义改成：

```python
async def emit(self, event: AgentEvent) -> None:
    if event.run_id is None:
        event.run_id = self.run_id
    try:
        await resource_event_bus.publish(self.resource_id, event)
    except Exception:
        logger.exception(
            "resource_event_publish_failed: resource_id=%s event_type=%s agent_id=%s",
            self.resource_id,
            event.event_type,
            event.agent_id,
        )
    if self._event_sink:
        try:
            await self._event_sink(event)
        except Exception:
            logger.exception(
                "resource_event_sink_failed: resource_id=%s event_type=%s agent_id=%s",
                self.resource_id,
                event.event_type,
                event.agent_id,
            )
```

不得重新抛出事件异常。这样 AgentRunTracker、artifact_ready 和 done 都不会污染业务状态，也不需要在每个节点重复套安全包装器。

- [ ] **Step 5: 清理事件兼容描述和旧分支**

删除 `agent/done`、兼容旧前端、旧 `event_type` 默认值相关注释和代码。`ResourceEventBus.publish()` 的完成清理条件改为 `resource.done`。

- [ ] **Step 6: 验证事件名只剩新协议**

Run:

```bash
rtk rg -n 'event_type="agent"|event_type="done"|addEventListener\(.agent.|addEventListener\(.done.|兼容旧' server/app/resource src/features/resource
```

Expected: 无资源模块匹配结果。

再执行：

```bash
rtk rg -n 'decode_token\(token\)|event.event_type == "done"|event_type="agent"|event: agent' server/app/resource/api.py
```

Expected: 无匹配结果。

---

### Task 2: 用一个函数统一所有非 Planning Agent 的生命周期

**Files:**
- Modify: `server/app/resource/workflow/nodes.py`
- Modify: `server/app/resource/workflow/state.py`

- [ ] **Step 1: 保留 Planning 独立节点和致命语义**

`planning_node()` 不进入通用 helper。以下情况直接抛异常：

- Planning 调用异常；
- `success=False`；
- metadata 没有 `teaching_plan`；
- `TeachingPlan.model_validate()` 失败。

异常由 orchestrator 将整个任务置为 `failed`，不调度任何 Worker/PPT/Video。

- [ ] **Step 2: 提取一个非 Planning 执行函数，不引入类层级**

在 `nodes.py` 内保留一个私有函数：

```python
async def _execute_non_planning_agent(
    *,
    agent_id: str,
    user_id: int,
    resource_id: int,
    resource_input: ResourceInput,
    emitter: AgentEventEmitter,
    require_downstream_context: bool,
    depends_on_agents: list[str] | None = None,
) -> dict[str, Any]:
    ...
```

函数固定执行顺序：生成 → `success/content/downstream_context` 校验 → 持久化 → 返回成功 result。每一阶段异常都写结构化日志并返回 `failures`，不抛给兄弟 Agent。

失败 stage 只允许：

```python
Literal["generation", "validation", "persistence"]
```

禁止增加 `event` stage。

- [ ] **Step 3: Worker 和聚合节点只负责组装输入**

`worker_node()` 调用 helper，`require_downstream_context=True`。

`ppt_node()`、`video_node()` 各自组装成功 handoff 后调用同一 helper，`require_downstream_context=False`。删除当前 Worker/aggregation 两套重复的 generation、validation、persistence 异常分支。

- [ ] **Step 4: 保证 PPT 与 Video 并行且互不依赖**

`route_after_merge()` 继续同时返回 `ppt_node` 和 `video_node`。两者都只读取基础 Agent 已成功并持久化的 handoff；PPT 失败不能取消 Video，Video 失败也不能取消 PPT。

- [ ] **Step 5: 检查重复生命周期代码已消失**

Run:

```bash
rtk rg -n 'stage=generation|stage=persistence|MissingDownstreamContext' server/app/resource/workflow/nodes.py
```

Expected: 每类阶段日志只在通用 helper 中存在一套。

- [ ] **Step 6: Reducer 禁止同一 Agent 被静默覆盖**

`merge_results_dict()` 和 `merge_failures_dict()` 在合并前检查 key 交集；同一 `agent_id` 出现两个结果时抛出工作流不变量错误，不能使用 `{**left, **right}` 静默保留后者。最终状态仍由 Task 3 的数据库集合校验兜底。

---

### Task 3: 让数据库提交成为 Agent 成功的唯一事实

**Files:**
- Modify: `server/app/resource/persistence/repository.py`
- Modify: `server/app/resource/persistence/__init__.py`
- Modify: `server/app/resource/service.py`
- Modify: `server/app/resource/workflow/nodes.py`
- Modify: `server/app/resource/orchestrator.py`

- [ ] **Step 1: 持久化接口显式接收调度 Agent ID**

签名改为：

```python
async def save_agent_result(
    self,
    *,
    resource_id: int,
    user_id: int,
    agent_id: str,
    result: AgentResult,
    depends_on_agents: list[str] | None = None,
) -> GeneratedResourceItemModel:
```

保存前按顺序验证：

1. 父资源存在且 `resource.user_id == user_id`；
2. `agent_id` 在父资源的 `selected_agents` 中；
3. `result.success is True` 且 content 非空；
4. `result.metadata["agent_id"] == agent_id`；
5. `depends_on_agents` 只含已成功入库的基础 Agent。

数据库字段 `agent_type`、`generated_by` 必须使用显式 `agent_id`，禁止从模型输出推断身份。

- [ ] **Step 2: 严格区分提交和 artifact 事件**

`persist_result_and_emit_artifact()` 先得到已提交的 item，再发送事件。由于 Task 1 已保证事件不抛异常，helper 只有数据库提交失败时才返回 `persistence` 失败。

- [ ] **Step 3: 删除无效的 repository 实例锁**

删除 `_write_locks`、`_get_write_lock()`、`release_write_lock()` 以及 service/orchestrator 对应调用。每次 `session_scope()` 都创建新 Repository，当前实例锁不能协调并发；正确性由数据库事务和唯一约束负责。

- [ ] **Step 4: 最终状态使用集合不变量计算**

finalizer 不再接收未使用的 `results`。输入只包含 selected、failed 和 coverage primitives；从数据库读取成功 Agent：

```python
expected = set(request.enabled_agent_ids())
successful = {item.agent_type for item in saved_items}
failed = set(failed_agent_ids)
overlap = successful & failed
unexpected = (successful | failed) - expected
unresolved = expected - successful - failed

if overlap or unexpected or unresolved:
    raise RuntimeError(
        f"resource finalization invariant violated: "
        f"overlap={sorted(overlap)} unexpected={sorted(unexpected)} "
        f"unresolved={sorted(unresolved)}"
    )

if not expected or not successful:
    status = "failed"
elif successful == expected:
    status = "completed"
else:
    status = "partial_completed"
```

不得使用“数据库有一条记录且 failures 为空”直接判 completed。

- [ ] **Step 5: 删除坏掉且无调用者的 service 包装**

删除 `ResourceService.save_generation_results()`；若 `ResourceService.save_agent_result()` 也无 API/兄弟模块调用者，一并删除。不要保留转发一行的死包装。

- [ ] **Step 6: 处理最终事件时不得回写失败状态**

orchestrator 只在图执行异常或 finalizer 明确失败时更新 `failed`。`resource.done` 发送失败已由 Task 1 内部记录，不能进入 orchestrator 的业务异常分支。

---

### Task 4: 对齐数据库唯一约束与一次性迁移

**Files:**
- Modify: `server/app/infra/models.py`
- Modify: `server/init_schema.sql`
- Modify: `server/migrations/20260619_resource_agent_unique.sql`

- [ ] **Step 1: SQLModel 只保留唯一约束**

保留：

```python
UniqueConstraint(
    "resource_id",
    "agent_type",
    name="uq_generated_resource_items_resource_agent",
)
```

删除相同字段的 `Index("ix_generated_resource_items_resource_agent", ...)`，避免重复索引和元数据漂移。

- [ ] **Step 2: 初始化 SQL 使用与 SQLModel 完全相同的表约束**

把唯一性写入 `CREATE TABLE generated_resource_items`：

```sql
CONSTRAINT uq_generated_resource_items_resource_agent
    UNIQUE (resource_id, agent_type)
```

删除后置的 `CREATE UNIQUE INDEX uq_generated_resource_items_resource_agent` 和普通 `ix_generated_resource_items_resource_agent`。新数据库只通过这一个表约束获得 constraint-backed unique index。

- [ ] **Step 3: 一次性迁移显式采用当前旧唯一索引**

迁移保持事务和重复数据预检；发现重复时输出前 10 个 `resource_id/agent_type/count` 并终止。禁止自动删除、保留最新、upsert、`ON CONFLICT` 或兼容旧数据。

当前基线已经通过同名 unique index 保证唯一性，因此迁移必须先验证：

- `uq_generated_resource_items_resource_agent` 是 `(resource_id, agent_type)` 的 unique index；
- 它尚未被 `pg_constraint` 绑定；
- 已存在的普通 `ix_generated_resource_items_resource_agent` 只是冗余索引。

验证通过后使用：

```sql
ALTER TABLE generated_resource_items
ADD CONSTRAINT uq_generated_resource_items_resource_agent
UNIQUE USING INDEX uq_generated_resource_items_resource_agent;

DROP INDEX ix_generated_resource_items_resource_agent;
```

这样不会创建第二个 unique index，也不会出现“同名 index 已存在导致 ADD CONSTRAINT 失败”。任一前置条件不满足都 `RAISE EXCEPTION` 并回滚；不用 `IF NOT EXISTS` 将错误基线伪装成成功。

- [ ] **Step 4: 验证三个来源一致**

检查 SQLModel、`init_schema.sql`、migration 的约束名称和字段顺序完全相同；普通复合索引不应再出现。

Fresh bootstrap 验证 constraint 和 backing index 各一条；旧库迁移后验证同一 index 已被该 constraint 持有。

---

### Task 5: 收紧 PPT 配置、来源和模板契约

**Files:**
- Modify: `server/app/resource/agents/ppt.py`
- Modify: `server/app/resource/ppt_contract.py`
- Modify: `server/app/resource/templates/ppt_manifest.json`
- Modify: `server/app/resource/prompts/ppt_director.md`
- Modify: `server/app/resource/prompts/ppt_chapter.md`

- [ ] **Step 1: 只允许“缺失配置”采用唯一默认值**

把 `_validate_literal(value, allowed, default)` 改为严格解析：

```python
def _resolve_literal(
    config: dict[str, Any],
    key: str,
    *,
    default: str,
    allowed: set[str],
) -> str:
    if key not in config or config[key] is None:
        return default
    value = str(config[key]).strip()
    if value not in allowed:
        raise ValueError(f"invalid PPT config {key}={value!r}")
    return value
```

`lesson_kind=auto` 只解析一次并传给 Director、compiler。显式非法值不得回退到 `concept`。

- [ ] **Step 2: 编程语言不再静默使用 Python**

资源和 path node 两种 SourcePack 都要求读取并验证明确语言；若产品契约将语言定义为可选，则只在配置键缺失时使用一个文档化默认值，空字符串和非法值必须报错。禁止 `value or "python"`。

- [ ] **Step 3: compiler 同时验证课型和真实来源**

签名改成：

```python
def compile_deck(
    blueprint: DeckBlueprint,
    *,
    expected_lesson_kind: LessonKind,
    available_source_ids: set[SourceAgentId],
) -> CompiledDeck:
```

验证：

- `blueprint.template_id` 对应 manifest template 的 `lesson_kind` 等于 `expected_lesson_kind`；
- 每个 slide 的 `source_refs` 非空；
- `set(source_refs) <= available_source_ids`；
- 没有 handoff 时可以启动 PPT，但任何虚构 source ref 都会使 PPT 自身失败，不影响其他 Agent。

- [ ] **Step 4: 删除章节素材的全量回退**

`select_chapter_sources()` 必须精确匹配 source refs：

```python
missing = requested_ids - available_ids
if missing:
    raise ValueError(f"chapter references unavailable sources: {sorted(missing)}")
return [
    artifact.model_dump(mode="json")
    for artifact in source_pack.artifacts
    if artifact.agent_id in requested_ids
]
```

删除“没有选中则返回全部 artifacts”。

- [ ] **Step 5: 保持 PPT 内部仅两阶段多智能体**

保留：

```text
DeckDirectorAgent
  -> compile strict deck
  -> ChapterWriterAgent × N (TaskGroup 并行)
  -> assemble strict document
```

任何 Chapter Writer 失败，由 TaskGroup 终止 PPT Agent；不得返回半套 PPT、替代章节或调用审核修复 Agent。

---

### Task 6: 让模板预算真正约束 PPT 内容

**Files:**
- Modify: `server/app/resource/ppt_contract.py`
- Modify: `server/app/resource/templates/ppt_manifest.json`
- Modify: `server/app/resource/prompts/ppt_chapter.md`

- [ ] **Step 1: 为每种 block 定义明确预算度量**

新增一个普通函数 `_validate_block_budget(expected: CompiledBlock, actual: SlideBlock)`，使用显式 `match actual.type`，不要创建 validator 类层级。

度量规则：

| Block | max_chars | max_lines | min/max_items | min/max_columns | min/max_rows |
|---|---|---|---|---|---|
| Text/Callout/Formula/KeyPoint | 内容字符数 | 文本行数 | 不适用 | 不适用 | 不适用 |
| Code | 代码字符数 | 非空代码行 | 不适用 | 不适用 | 不适用 |
| Terminal | command + output 字符数 | output 非空行 | 不适用 | 不适用 | 不适用 |
| Diagram | labels 总字符数 | 不适用 | nodes 数量 | 不适用 | 不适用 |
| CardList | cards 内容总字符数 | 不适用 | cards 数量 | 不适用 | 不适用 |
| CodeAnnotation | annotations 内容总字符数 | 不适用 | items 数量 | 不适用 | 不适用 |
| TraceStep | steps 内容总字符数 | 不适用 | steps 数量 | 不适用 | 不适用 |
| Practice | question+hints+checkpoint 字符数 | 不适用 | hints 数量 | 不适用 | 不适用 |
| Table | cells 总字符数 | 不适用 | 不适用 | columns | rows |

- [ ] **Step 2: assemble 时对每个 block 执行预算校验**

在 block ID 和 type 匹配之后、放入 slot 之前调用 `_validate_block_budget()`。超限或不足直接抛出包含 slide ID、block ID、字段、实际值和限制值的 `ValueError`。

- [ ] **Step 3: manifest 每个 budget 字段都必须被执行**

扫描 manifest 使用到的 `max_chars/max_lines/min_items/max_items/min_columns/max_columns/min_rows/max_rows`，确保没有“配置了但代码忽略”的字段。

- [ ] **Step 4: prompt 明确要求按 compiled budget 输出**

Chapter Writer prompt 说明预算是硬约束，不得依赖后处理截断。禁止添加自动裁剪，因为裁剪会掩盖生成缺陷。

---

### Task 7: 前端只展示数据库中有效的成功卡片

**Files:**
- Modify: `src/features/resource/views/ResourceResult.vue`
- Modify: `src/features/resource/views/ResourceGenerator.vue`
- Modify: `src/features/resource/views/ResourceDetail.vue`
- Modify: `src/features/resource/components/PptView.vue`
- Modify: `src/features/resource/components/ppt-engine/types/ppt.ts`
- Modify: `src/features/resource/model/resource.ts`
- Modify: `src/features/resource/model/ResourceGeneratorConstants.ts`

- [ ] **Step 1: 结果页只读取最终 bundle resources**

`ResourceResult` 删除 `generatedResources` 兜底。任务完成后必须重新请求 bundle；只将 bundle 中 `status=finished/completed`、类型在允许集合内、content 非空的记录变成卡片。

允许类型固定为：

```ts
const RESOURCE_TYPES = new Set(['content', 'mindmap', 'quiz', 'code', 'reading', 'ppt', 'video'])
```

未知类型执行 `console.error` 后过滤，禁止映射成 `content`。

- [ ] **Step 2: 独立资源页删除虚构学习路径**

删除 `buildStudyPathFromCards()`、`getStudyPathReason()`、`getStudyPathFocusPoints()` 及“默认 45 分钟”。独立 `resource` 不是 `path`；若 bundle 没有真实持久化 study path，就不展示学习路径模块。

预计时长仅在后端 metadata/metrics 提供有效值时展示；没有值则隐藏字段，不造默认分钟数。

- [ ] **Step 3: 卡片内容只使用真实字段**

标题、摘要、格式、metrics、tags 均来自持久化资源；没有摘要或 tag 就不显示对应区域。删除固定题数、固定 Python、固定 highlights 等展示性补值。

- [ ] **Step 4: PPT 在创建卡片前完成严格解析**

结果页和详情页在卡片集合构造阶段调用 `parsePptDocument()`。解析失败：

```ts
console.error('Invalid persisted PPT artifact omitted', {
  resourceId: resource.id,
  reason: parsed.reason,
  details: parsed.details,
})
```

随后过滤该 PPT。`PptView.vue` 删除 invalid-state；它只接收已经验证的 document，不承担降级或错误占位展示。

- [ ] **Step 5: 校验前端没有旧兜底**

Run:

```bash
rtk rg -n "buildStudyPathFromCards|return value \|\| 'content'|return total \|\| 45|invalid-state|generatedResources" src/features/resource
```

Expected: 与结果页兜底相关的匹配为零。

---

### Task 8: 删除资源模块死代码与多余封装

**Files:**
- Modify: `server/app/resource/service.py`
- Modify: `server/app/resource/persistence/repository.py`
- Modify: `server/app/resource/persistence/__init__.py`
- Modify: `server/app/resource/workflow/nodes.py`
- Modify: `server/app/infra/llm.py`
- Modify: `server/app/infra/models.py`
- Modify: `server/init_schema.sql`
- Create: `server/migrations/20260619_remove_resource_review_result.sql`
- Modify: `src/features/resource/views/ResourceGenerating.vue`
- Modify: `src/features/resource/views/ResourceResult.vue`
- Modify: `src/features/resource/views/ResourcePersonalize.vue`

- [ ] **Step 1: 删除已确认无调用者的包装和锁代码**

删除坏掉的 finalizer service wrapper、无意义 `release_write_lock`、每实例锁、无调用的 DB item → AgentResult 反向构造函数。删除前用 `rtk rg` 确认没有源代码调用者。

- [ ] **Step 2: 删除资源域 Review 遗留**

删除资源模型中仅为旧 Review Agent 存在且没有读取者的 `review_result`；同步更新 `init_schema.sql`。新增一次性、非幂等迁移：

```sql
BEGIN;

ALTER TABLE generated_resources
DROP COLUMN review_result;

COMMIT;
```

列不存在时迁移应失败，禁止 `IF EXISTS` 掩盖数据库基线错误。删除资源前端 reviewer/QUALITY REVIEW/旧 review station 语义和无引用 CSS。

不要删除 quiz 答题判定等其他业务域中真正使用的“review”概念。

- [ ] **Step 3: 删除重复 Llm 构造函数**

只删除 [server/app/infra/llm.py] 中第一个空 `__init__`，保留实际加载模型配置的构造函数。不得趁机修改 JSON 模式、重试和 prompt fallback。

- [ ] **Step 4: 删除资源模块兼容措辞与旧符号**

删除旧 event、PPT payload、旧 layout/block 的 export、注释和别名。若某旧符号只被测试引用，不恢复兼容导出。

明确处理本轮审核发现：

- 删除 `ReadingConfig.normalize_language_preference()` 对旧值 `bilingual` 的转换；
- 将 `schemas/__init__.py` 描述改为当前公共导出，不再声明“向后兼容”；
- 删除 `VideoView.vue` 对旧 envelope 的归一化分支，调用方统一传递当前 `ResourceItemDetail.content`；
- `CodeView.vue` 中语言别名、Markdown fenced-code 解析若属于当前正式内容协议则保留，但删除“兼容旧格式”分支和措辞；
- 删除 `review_result`、review station、reviewer 过滤等只服务旧 Review Agent 的字段、模板和样式。

不得按关键词机械删除其他业务域的正常“审核/复习/review”文案，也不得修改 `path` 的记录、API、详情页或持久化模型。

- [ ] **Step 5: 控制封装数量**

完成后资源主链只保留这些核心边界：

```text
orchestrator -> graph/nodes -> agents -> repository
                         \-> event emitter (observation only)
PPT agent -> ppt_contract -> manifest
```

不新增 manager/facade/coordinator class。Service 只保留 API 确实调用的 CRUD 用例。

---

### Task 9: 最终验收——最后怎么看

**Files:**
- Do not modify: `server/tests/**`
- Verify source files only

- [ ] **Step 1: 启动与导入检查**

Run from `server/`:

```bash
rtk uv run python -c 'from app.main import app; print(type(app).__name__)'
rtk uv run python -c 'from app.resource.service import ResourceService; print(ResourceService.__name__)'
rtk uv run python -m compileall -q app/resource app/infra/llm.py
```

Expected: 输出 `FastAPI`、`ResourceService`，compileall 无错误。

- [ ] **Step 2: 前端类型与生产构建**

Run from repository root:

```bash
rtk npm run build
```

Expected: `vue-tsc` 与 Vite build 成功；chunk size warning 可以记录，但不是本次失败条件。

- [ ] **Step 3: 运行旧测试但不修改它们**

Run from `server/`:

```bash
rtk uv run pytest tests/resource -q
```

如果仍因 `PptPayload` 或 `PPT_TEMPLATE_MANIFEST` 旧导入在 collection 阶段失败，记录为“测试仍绑定旧协议”；不得在源代码中恢复兼容符号，也不得修改测试文件。

- [ ] **Step 4: 验证关键运行场景**

使用源代码 smoke 或开发环境任务逐项观察数据库和日志：

1. Planning 失败：任务 `failed`，零资源项，Worker/PPT/Video 未启动。
2. content 成功、quiz 失败：content 立即存在于 DB；其他 Agent 继续；最终 `partial_completed`；无 quiz 卡片。
3. artifact 事件 sink 抛异常：数据库项仍成功，Agent 仍在 success 集合，最终状态不受影响，日志出现 `resource_event_*_failed`。
4. 所有非 Planning Agent 失败：零资源卡片，最终 `failed`。
5. PPT source ref 指向失败 Agent：PPT 失败并记录日志；Video 和基础成功资源不受影响。
6. PPT block 超出 manifest budget：PPT 失败，不裁剪、不渲染占位卡。
7. 持久化 PPT JSON 非法：前端记录错误并省略 PPT 卡片，其余卡片正常展示。
8. 重复 `(resource_id, agent_type)`：数据库唯一约束拒绝第二次提交，该 Agent 记录 persistence failure。
9. SSE 使用已登出 token：认证失败，不能订阅；有效用户订阅他人 resource ID：返回 404，不泄露快照。
10. SSE 在生成中连接：收到新事件并在 `resource.done` 后关闭；任务完成后重连：回放快照、发送一次 `resource.done` 后关闭，不出现重复 `event_type` 异常。
11. finalizer 收到 successful/failed 重叠、unexpected 或 unresolved Agent：记录集合详情并使父任务失败，不允许标记 completed。
12. PPT Director 选择与 `lesson_kind` 不符的模板、引用未成功 Agent 或输出任一超预算 block：PPT Agent 失败且不创建 PPT item。

- [ ] **Step 5: 禁止模式扫描**

Run:

```bash
rtk rg -n '兼容旧|backward compatibility|PptPayload|PPT_TEMPLATE_MANIFEST|agent/done|event_type="agent"|event_type="done"' server/app/resource src/features/resource
rtk rg -n 'buildStudyPathFromCards|using fallback|fallback to|降级|占位' server/app/resource src/features/resource
rtk rg -n 'class .*Review|review_result|repair_agent|review_agent' server/app/resource src/features/resource
```

Expected: 不存在资源生成旧兼容、降级内容或 Review/Repair Agent；命中正常英文 UI fallback 等非业务词时逐条人工确认，不能只按单词机械删除。

- [ ] **Step 6: 工作区完整性检查**

Run:

```bash
rtk git diff --check
rtk git diff --name-only
```

Expected:

- `git diff --check` 无输出；
- 本轮没有新增或修改 `server/tests/**`；
- P0 配置项保持不动；
- `resource` 与 `path` 的表、API、详情页仍相互独立。
- 当前工作区已有的 `server/tests/dashboard/test_home_api.py` 修改必须在报告中单独标记；本方案执行者不得继续编辑、暂存或用它证明本次优化完成。

## 验收判定

只有以下条件全部满足才能认为优化完成：

- Planning 的任何失败会终止整个资源任务；
- 每个其他 Agent 失败只影响自己的卡片；
- 成功 Agent 在返回工作流 success 前已经提交数据库；
- 事件异常只写日志，永不改变持久化状态；
- `completed/partial_completed/failed` 由 expected/success/failed 集合严格计算；
- PPT 没有来源回退、配置纠正、内容裁剪、旧格式转换和无效卡片；
- PPT 仍由 Director + 并行 Chapter Writers 提升速度和内容量；
- 前端只展示数据库中的成功且协议有效的资源；
- SSE 只允许资源所有者使用有效白名单 token 订阅，生成中和终态重连都能可靠结束；
- 源代码不存在资源旧事件、Review/Repair Agent 和无调用包装；
- 后端导入、compileall、前端 build、diff check 通过；
- 没有修改测试文件，也没有为旧测试恢复兼容代码。
