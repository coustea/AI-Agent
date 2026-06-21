# Resource Teaching Plan And Handoff Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 standalone resource 多智能体生成链路：PlanningAgent 只输出总体教学方向与大纲，基础 agent 在完整资源外同时输出下游交接摘要，PPT/Video 只消费 teaching plan 与交接摘要，不读取上游完整正文。

**Architecture:** 采用破坏式接口变更，不保留 `LearningBlueprint`、`AgentInstruction`、`ExecutionPlan`、`ResourceInput.previous_results`、`summary_data` 的 standalone resource 旧契约。新契约为 `TeachingPlan`、`DownstreamContext`、`ResourceInput.upstream_handoffs`、`AgentResult.metrics`，数据库新增一等字段 `generated_resources.teaching_plan` 与 `generated_resource_items.downstream_context`。基础 agent 并行生成完整资源和交接摘要，聚合 agent `ppt/video` 基于 plan 定叙事结构，基于 handoff 定讲解素材。

**Tech Stack:** FastAPI + SQLModel + PostgreSQL JSONB；Pydantic v2；pytest；Vue 3 + TypeScript；Element Plus；`rtk uv run pytest`；`rtk npm run build`。

---

## Execution Rules For Claude Code

- 所有 shell 命令必须带 `rtk` 前缀。
- 后端命令从 `/Users/apple/Code/software/server` 执行，前端命令从 `/Users/apple/Code/software` 执行。
- 不保留 standalone resource 旧字段读取路径：不再读取 `blueprint`、`instruction`、`previous_results`、`metadata.downstream_context` 的旧嵌套位置、`personalization.execution_plan`、`summary_data`。
- `path` 域仍可继续使用同一个 `AgentResult`，但必须迁移到 `metrics` 字段；不要把 standalone resource 的 plan/handoff 持久化逻辑混入 path 表。
- `video` 和 `ppt` 仍是 standalone resource 聚合 agent，与 `content/mindmap/quiz/code/reading` 同属 resource 域，不接入 path 节点生成。
- 不新增 video 专表，不新增 handoff 专表；使用 `generated_resources` 和 `generated_resource_items`。
- `server/app/resource/agents/video.py` 保持单文件实现。
- 每个任务结束后运行该任务指定测试，再进入下个任务。

---

## Target Runtime Flow

```text
ResourceGenerationRequest
  ↓
PlanningAgent
  输出 TeachingPlan: 总体方向 + 结构化大纲 + 教学边界
  ↓
content / mindmap / quiz / code / reading 并行
  输入 TeachingPlan + agent_config
  输出完整资源 content
  同时输出 AgentResult.downstream_context
  ↓
ppt / video 并行
  输入 TeachingPlan + upstream_handoffs + 自身 agent_config
  不读取上游完整 content
  ↓
review / bundle / persist
```

---

## File Map

- Modify: `server/app/resource/schemas.py`  
  删除旧 plan/instruction 类型，新增 `TeachingPlan`、`TeachingOutlineItem`、`DownstreamContext`、`DownstreamMaterial`、`ReusableAssets`，替换 `ResourceInput` 与 `AgentResult` 字段。
- Modify: `server/app/resource/agents/planning.py`  
  PlanningAgent 只生成 `TeachingPlan`，不生成 per-agent instruction。
- Modify: `server/app/resource/prompts/planning.md`  
  prompt 改成总体教学方向、大纲、边界输出，不提 agent 分工。
- Modify: `server/app/resource/agents/common.py`  
  resource prompt 上下文只包含 learning_need、scenario、profile、teaching_plan、upstream_handoffs。
- Modify: `server/app/resource/agents/content.py`
- Modify: `server/app/resource/agents/mindmap.py`
- Modify: `server/app/resource/agents/quiz.py`
- Modify: `server/app/resource/agents/code.py`
- Modify: `server/app/resource/agents/reading.py`  
  每个基础 agent 生成完整资源后构造 `DownstreamContext`。
- Modify: `server/app/resource/agents/ppt.py`
- Modify: `server/app/resource/agents/video.py`  
  只消费 `input_data.upstream_handoffs`，不读取上游完整正文。
- Modify: `server/app/resource/service.py`  
  改造 DAG 数据流、持久化、进度 metrics 字段、review 输入。
- Modify: `server/app/resource/items.py`  
  序列化 `metrics` 和 `downstream_context` 到一等 DB 字段。
- Modify: `server/app/resource/review.py`  
  审核输入读取 `teaching_plan` 与 `downstream_context`，检查聚合资源是否覆盖大纲。
- Modify: `server/app/infra/models.py`
- Modify: `server/init_schema.sql`  
  数据库模型和初始化 SQL 同步。
- Modify: `server/tests/resource/test_teaching_plan_handoff_contract.py`
- Modify: `server/tests/resource/test_resource_contract.py`
- Modify: `server/tests/resource/test_video_agent.py`
- Modify: `server/tests/resource/test_ppt_internal_multi_agent.py`
- Modify: `server/tests/resource/test_video_service_orchestration.py`
- Modify: `server/tests/resource/test_agent_integration.py`  
  后端契约和编排测试。
- Modify: `src/features/resource/model/resource.ts`
- Modify: `src/features/resource/views/ResourceGenerator.vue`
- Modify: `src/features/resource/views/ResourceResult.vue`
- Modify: `src/features/resource/components/VideoView.vue`  
  前端 DTO 字段从 `summary_data` 迁移到 `metrics`，展示 metadata 中的 plan/review 改为一等字段来源。

---

## Task 1: Replace Resource Schema Contracts

**Files:**
- Modify: `server/app/resource/schemas.py`
- Create: `server/tests/resource/test_teaching_plan_handoff_contract.py`

- [ ] **Step 1: Add failing schema tests**

Create `server/tests/resource/test_teaching_plan_handoff_contract.py`:

```python
import pytest
from pydantic import ValidationError

from app.resource.schemas import (
    AgentResult,
    DownstreamContext,
    DownstreamMaterial,
    ResourceInput,
    ReusableAssets,
    TeachingOutlineItem,
    TeachingPlan,
)


def test_teaching_plan_has_only_global_direction_and_outline():
    plan = TeachingPlan(
        topic="TCP 三次握手",
        learning_goal="理解三次握手的目的、流程和常见误区",
        audience="有基础网络概念的学习者",
        difficulty="intermediate",
        teaching_strategy="问题引入 -> 流程讲解 -> 误区辨析 -> 练习巩固",
        summary="围绕连接建立过程讲清 SYN、SYN-ACK、ACK 的必要性。",
        outline=[
            TeachingOutlineItem(
                id="o1",
                title="为什么需要三次握手",
                goal="理解连接建立前双方需要确认通信能力和初始状态",
                key_points=["确认客户端发送能力", "确认服务端接收和发送能力"],
                common_misconceptions=["三次握手不是身份认证"],
                suggested_examples=["打电话确认双方能听能说"],
                suggested_visuals=["时序图"],
                must_not_miss=True,
            )
        ],
        boundaries=["不要把三次握手解释成加密认证"],
    )

    dumped = plan.model_dump(mode="json")

    assert "agent_instructions" not in dumped
    assert "resource_guidance" not in dumped
    assert dumped["outline"][0]["id"] == "o1"


def test_downstream_context_is_bounded_and_outline_mapped():
    ctx = DownstreamContext(
        source_agent="content",
        title="TCP 三次握手讲解",
        one_sentence_summary="解释三次握手的目的、流程和常见误区。",
        covered_outline_ids=["o1", "o2"],
        materials=[
            DownstreamMaterial(
                outline_id="o1",
                type="explanation",
                summary="三次握手用于确认双方收发能力并同步初始序列号。",
                key_points=["确认客户端发送能力", "同步初始序列号"],
                evidence_excerpt="核心不是认证身份，而是建立双方可靠通信的初始状态。",
                priority=1,
            )
        ],
        reusable_assets=ReusableAssets(
            examples=["打电话确认双方能听能说"],
            misconceptions=["三次握手不是身份认证"],
            visual_ideas=["客户端和服务端时序图"],
            practice_refs=[],
            code_refs=[],
        ),
        cautions=["不要把三次握手解释成加密认证过程"],
    )

    assert ctx.schema_version == "resource_handoff/v1"
    assert ctx.materials[0].outline_id == "o1"


def test_downstream_context_rejects_oversized_excerpt():
    with pytest.raises(ValidationError):
        DownstreamMaterial(
            outline_id="o1",
            type="explanation",
            summary="摘要",
            evidence_excerpt="x" * 181,
            priority=1,
        )


def test_resource_input_uses_teaching_plan_and_handoffs_only():
    plan = TeachingPlan(topic="TCP", learning_goal="理解 TCP", outline=[])
    handoff = DownstreamContext(source_agent="content", title="内容", one_sentence_summary="讲解 TCP")
    resource_input = ResourceInput(
        resource_id=1,
        learning_need="学习 TCP",
        agent_name="video",
        teaching_plan=plan,
        upstream_handoffs={"content": handoff},
    )

    dumped = resource_input.model_dump(mode="json")

    assert dumped["teaching_plan"]["topic"] == "TCP"
    assert set(dumped["upstream_handoffs"].keys()) == {"content"}
    assert "blueprint" not in dumped
    assert "instruction" not in dumped
    assert "previous_results" not in dumped


def test_agent_result_uses_metrics_and_downstream_context():
    handoff = DownstreamContext(source_agent="content", title="内容", one_sentence_summary="讲解 TCP")
    result = AgentResult(
        success=True,
        content="# TCP",
        file_type="markdown",
        title="TCP 内容",
        summary="生成内容",
        metrics={"char_count": 5},
        downstream_context=handoff,
        metadata={"agent_id": "content"},
    )

    dumped = result.model_dump(mode="json")

    assert dumped["metrics"]["char_count"] == 5
    assert dumped["downstream_context"]["source_agent"] == "content"
    assert "summary_data" not in dumped
```

- [ ] **Step 2: Run the failing schema tests**

From `server/`:

```bash
rtk uv run pytest tests/resource/test_teaching_plan_handoff_contract.py -q
```

Expected before implementation: import errors for the new schema classes and assertions failing because old fields still exist.

- [ ] **Step 3: Replace the resource schema block**

In `server/app/resource/schemas.py`, replace `LearningBlueprint`, `AgentInstruction`, `ExecutionPlan`, `AgentResult`, and `ResourceInput` with:

```python
class TeachingOutlineItem(BaseModel):
    """PlanningAgent 生成的全局教学大纲项，不绑定具体 agent。"""

    id: str = Field(pattern=r"^o[0-9]+$", description="稳定大纲 ID，如 o1、o2")
    title: str
    goal: str = ""
    key_points: list[str] = Field(default_factory=list)
    common_misconceptions: list[str] = Field(default_factory=list)
    suggested_examples: list[str] = Field(default_factory=list)
    suggested_visuals: list[str] = Field(default_factory=list)
    must_not_miss: bool = True


class TeachingPlan(BaseModel):
    """PlanningAgent 的唯一输出：总体方向、概要、大纲和边界。"""

    topic: str
    learning_goal: str = ""
    audience: str = ""
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    teaching_strategy: str = ""
    summary: str = ""
    outline: list[TeachingOutlineItem] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)


class ReusableAssets(BaseModel):
    examples: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    visual_ideas: list[str] = Field(default_factory=list)
    practice_refs: list[str] = Field(default_factory=list)
    code_refs: list[str] = Field(default_factory=list)


class DownstreamMaterial(BaseModel):
    outline_id: str = ""
    type: Literal["explanation", "structure", "practice", "code", "reading", "example", "visual"] = "explanation"
    summary: str = Field(default="", max_length=500)
    key_points: list[str] = Field(default_factory=list, max_length=8)
    evidence_excerpt: str = Field(default="", max_length=180)
    priority: int = Field(default=3, ge=1, le=5)


class DownstreamContext(BaseModel):
    """基础 agent 给 PPT/Video/Review 的短交接摘要。"""

    schema_version: Literal["resource_handoff/v1"] = "resource_handoff/v1"
    source_agent: str
    title: str = ""
    one_sentence_summary: str = Field(default="", max_length=180)
    covered_outline_ids: list[str] = Field(default_factory=list)
    materials: list[DownstreamMaterial] = Field(default_factory=list, max_length=8)
    reusable_assets: ReusableAssets = Field(default_factory=ReusableAssets)
    cautions: list[str] = Field(default_factory=list, max_length=6)


class AgentResult(BaseModel):
    """统一 Agent 输出结果，用于 standalone resource 和 path node resource。"""

    success: bool = True
    content: str = ""
    file_type: str = "markdown"
    title: str = ""
    summary: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    downstream_context: DownstreamContext | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class ResourceInput(BaseModel):
    """standalone 多智能体资源生成输入。"""

    resource_id: int | None = None
    learning_need: str
    learning_scenario: LearningScenario = "self_study"
    agent_name: str = ""
    agent_config: dict[str, Any] = Field(default_factory=dict)
    teaching_plan: TeachingPlan | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    upstream_handoffs: dict[str, DownstreamContext] = Field(default_factory=dict)
```

In the same file, update `GeneratedResourceItem`:

```python
class GeneratedResourceItem(BaseModel):
    """生成的资源项，作为后端存储和前端 SSE 的统一资源契约。"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ResourceAgentId
    title: str
    format: str
    content: Any
    summary: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    downstream_context: DownstreamContext | None = None
    execution_report: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"
    error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
```

Update `ResourceBundle.metadata` consumers later in Task 5; keep the field itself as generic `metadata`.

- [ ] **Step 4: Update exports**

In `server/app/resource/schemas.py` `__all__`, remove `LearningBlueprint`, `AgentInstruction`, and `ExecutionPlan`. Add:

```python
"TeachingOutlineItem",
"TeachingPlan",
"ReusableAssets",
"DownstreamMaterial",
"DownstreamContext",
```

- [ ] **Step 5: Run schema tests**

From `server/`:

```bash
rtk uv run pytest tests/resource/test_teaching_plan_handoff_contract.py -q
```

Expected after implementation: all tests pass.

- [ ] **Step 6: Commit**

```bash
rtk git add server/app/resource/schemas.py server/tests/resource/test_teaching_plan_handoff_contract.py
rtk git commit -m "refactor: replace resource plan and handoff schemas"
```

---

## Task 2: Update Database Contract

**Files:**
- Modify: `server/app/infra/models.py`
- Modify: `server/init_schema.sql`
- Modify: `server/tests/resource/test_resource_contract.py`

- [ ] **Step 1: Add failing database contract tests**

Append to `server/tests/resource/test_resource_contract.py`:

```python
def test_generated_resources_has_teaching_plan_columns():
    table_sql = _table_sql("generated_resources")

    assert "teaching_plan       JSONB" in table_sql
    assert "review_result       JSONB" in table_sql
    assert "failed_agents       JSONB" in table_sql
    assert "personalization" not in table_sql


def test_generated_resource_items_has_downstream_context_and_metrics():
    table_sql = _table_sql("generated_resource_items")

    assert "metrics                         JSONB" in table_sql
    assert "downstream_context              JSONB" in table_sql
    assert "summary_data" not in table_sql


def test_generated_resource_item_model_has_single_status_and_error_fields():
    import inspect
    from app.infra import models

    source = inspect.getsource(models.GeneratedResourceItem)

    assert source.count("status: str = Field") == 1
    assert source.count("error_message: str | None = Field") == 1
```

- [ ] **Step 2: Run the failing contract tests**

From `server/`:

```bash
rtk uv run pytest tests/resource/test_resource_contract.py -q
```

Expected before implementation: SQL/model assertions fail.

- [ ] **Step 3: Modify `GeneratedResource` model**

In `server/app/infra/models.py`, inside `GeneratedResource`, remove:

```python
personalization: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
```

Add these fields in the same semantic area:

```python
teaching_plan: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
review_result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
failed_agents: list[str] | None = Field(default=None, sa_column=Column(JSONB))
workflow_metadata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
```

- [ ] **Step 4: Modify `GeneratedResourceItem` model**

In `server/app/infra/models.py`, inside `GeneratedResourceItem`, keep one `status` block only. Add `metrics` and `downstream_context` after `metadata_json`:

```python
metadata_json: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
metrics: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
downstream_context: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
status: str = Field(default="pending", max_length=50)
error_message: str | None = Field(default=None, sa_column=Column(Text))
```

Remove the later duplicated status block:

```python
# 状态
status: str = Field(default="pending", max_length=50)
error_message: str | None = Field(default=None, sa_column=Column(Text))
```

Add indexes to `__table_args__`:

```python
Index("ix_generated_resource_items_metrics", "metrics", postgresql_using="gin"),
Index("ix_generated_resource_items_downstream_context", "downstream_context", postgresql_using="gin"),
```

- [ ] **Step 5: Modify `server/init_schema.sql`**

In the `generated_resources` table definition, replace:

```sql
    personalization     JSONB,
```

with:

```sql
    teaching_plan       JSONB,
    review_result       JSONB,
    failed_agents       JSONB,
    workflow_metadata   JSONB,
```

In the `generated_resource_items` table definition, add after `metadata_json JSONB`:

```sql
    metrics                         JSONB,
    downstream_context              JSONB,
```

Add indexes near the existing GIN indexes:

```sql
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_metrics
    ON generated_resource_items USING GIN (metrics);
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_downstream_context
    ON generated_resource_items USING GIN (downstream_context);
```

- [ ] **Step 6: Add live database migration SQL to docs**

Create `server/docs/resource_teaching_plan_handoff_migration.sql` with:

```sql
BEGIN;

ALTER TABLE generated_resources
    DROP COLUMN IF EXISTS personalization,
    ADD COLUMN IF NOT EXISTS teaching_plan JSONB,
    ADD COLUMN IF NOT EXISTS review_result JSONB,
    ADD COLUMN IF NOT EXISTS failed_agents JSONB,
    ADD COLUMN IF NOT EXISTS workflow_metadata JSONB;

ALTER TABLE generated_resource_items
    ADD COLUMN IF NOT EXISTS metrics JSONB,
    ADD COLUMN IF NOT EXISTS downstream_context JSONB;

CREATE INDEX IF NOT EXISTS ix_generated_resource_items_metrics
    ON generated_resource_items USING GIN (metrics);
CREATE INDEX IF NOT EXISTS ix_generated_resource_items_downstream_context
    ON generated_resource_items USING GIN (downstream_context);

COMMIT;
```

This migration intentionally does not copy old execution plan data.

- [ ] **Step 7: Run contract tests**

From `server/`:

```bash
rtk uv run pytest tests/resource/test_resource_contract.py -q
```

Expected after implementation: all resource contract tests pass.

- [ ] **Step 8: Commit**

```bash
rtk git add server/app/infra/models.py server/init_schema.sql server/tests/resource/test_resource_contract.py server/docs/resource_teaching_plan_handoff_migration.sql
rtk git commit -m "refactor: persist teaching plan and handoff contracts"
```

---

## Task 3: Refactor PlanningAgent To Produce Global TeachingPlan

**Files:**
- Modify: `server/app/resource/agents/planning.py`
- Modify: `server/app/resource/prompts/planning.md`
- Modify: `server/tests/resource/test_teaching_plan_handoff_contract.py`

- [ ] **Step 1: Add PlanningAgent behavior test**

Append to `server/tests/resource/test_teaching_plan_handoff_contract.py`:

```python
import json

import pytest

from app.resource.agents.planning import PlanningAgent
from app.resource.schemas import ResourceInput, TeachingPlan


@pytest.mark.asyncio
async def test_planning_agent_returns_teaching_plan_without_agent_instructions(monkeypatch):
    class FakeLlm:
        async def ainvoke_json(self, model, message, **kwargs):
            assert model is TeachingPlan
            assert "为每个启用的资源 Agent" not in message
            return TeachingPlan(
                topic="TCP 三次握手",
                learning_goal="理解三次握手",
                summary="围绕目的、流程和误区组织学习。",
                outline=[],
            )

    agent = PlanningAgent()
    agent.llm = FakeLlm()

    result = await agent.generate_resource(
        ResourceInput(
            resource_id=1,
            learning_need="学习 TCP 三次握手",
            agent_config={"enabled_agents": ["content", "mindmap", "ppt", "video"]},
        )
    )

    payload = json.loads(result.content)

    assert result.success is True
    assert result.downstream_context is None
    assert result.metadata["agent_id"] == "planning"
    assert result.metadata["teaching_plan"]["topic"] == "TCP 三次握手"
    assert "agent_instructions" not in payload
```

- [ ] **Step 2: Run the failing PlanningAgent test**

From `server/`:

```bash
rtk uv run pytest tests/resource/test_teaching_plan_handoff_contract.py::test_planning_agent_returns_teaching_plan_without_agent_instructions -q
```

Expected before implementation: PlanningAgent still calls `ExecutionPlan`.

- [ ] **Step 3: Replace PlanningAgent output type**

In `server/app/resource/agents/planning.py`, change imports:

```python
from app.resource.schemas import AgentResult, NodeInput, ResourceInput, TeachingPlan
```

Replace the LLM call and result construction in `generate_resource()`:

```python
plan = await self.llm.ainvoke_json(
    TeachingPlan,
    f"{prompt}\n\n{input_text}",
    temperature=INFERENCE_TEMPERATURE,
)

await self.emit_start("教学方向与大纲已生成", progress=85)

result = AgentResult(
    success=True,
    content=plan.model_dump_json(indent=2),
    file_type="json",
    title="教学方向与大纲",
    summary="PlanningAgent 生成了总体教学方向、概要和大纲",
    metrics={"outline_count": len(plan.outline)},
    metadata={
        "agent_id": "planning",
        "teaching_plan": plan.model_dump(mode="json"),
    },
)
```

Update the module docstring to describe `TeachingPlan` only.

- [ ] **Step 4: Replace planning prompt**

Replace `server/app/resource/prompts/planning.md` with this content:

~~~markdown
# 规划智能体 (PlanningAgent)

你是一位学习资源总编排师。你的产出是本次资源包共同遵循的总体教学方向和大纲，不为任何具体 Agent 分配任务。

## 输入格式

你将收到以下内容：

- `## 学习需求`：用户想学习的主题、目标或问题
- `## 学习场景`：exam_prep / daily_review / project_practice / self_study / path_learning
- `## 学习者画像`：知识水平、薄弱点、偏好，可为空
- `## 需要生成的资源类型`：本次用户选择的资源类型，只用于判断大纲深度和表达形态

## 输出格式

仅输出 JSON，严格匹配以下结构：

```json
{
  "topic": "精确学习主题",
  "learning_goal": "学完本轮资源后学习者能完成的动作",
  "audience": "目标学习者描述",
  "difficulty": "beginner | intermediate | advanced",
  "teaching_strategy": "整体讲解策略，例如：问题引入 -> 流程讲解 -> 误区辨析 -> 练习巩固",
  "summary": "本轮资源包的总体概要",
  "outline": [
    {
      "id": "o1",
      "title": "大纲标题",
      "goal": "该部分帮助学习者达成的目标",
      "key_points": ["必须覆盖的关键点"],
      "common_misconceptions": ["常见误区"],
      "suggested_examples": ["可用例子"],
      "suggested_visuals": ["适合视觉化表达的形式"],
      "must_not_miss": true
    }
  ],
  "boundaries": ["本轮资源不应偏离或不应误讲的边界"]
}
```

## 生成要求

1. `outline` 必须是全局课程大纲，不绑定 content、mindmap、quiz、code、reading、ppt、video 中任何一个具体资源类型。
2. `outline.id` 必须从 `o1` 开始连续递增。
3. `key_points` 只写支撑学习目标的关键概念、步骤、辨析点。
4. `common_misconceptions` 写具体误区，不写泛化提醒。
5. `suggested_examples` 和 `suggested_visuals` 是全局建议，供所有资源类型按自身形态使用。
6. `boundaries` 用来防止下游资源跑偏和误讲。
7. 不输出任何 agent 分工、agent 指令、agent 优先级、agent 专属约束。
~~~

- [ ] **Step 5: Run PlanningAgent tests**

From `server/`:

```bash
rtk uv run pytest tests/resource/test_teaching_plan_handoff_contract.py -q
```

Expected after implementation: all tests pass.

- [ ] **Step 6: Commit**

```bash
rtk git add server/app/resource/agents/planning.py server/app/resource/prompts/planning.md server/tests/resource/test_teaching_plan_handoff_contract.py
rtk git commit -m "refactor: make planning output global teaching plan"
```

---

## Task 4: Refactor Resource Context And Base Agent Handoffs

**Files:**
- Modify: `server/app/resource/agents/common.py`
- Modify: `server/app/resource/agents/content.py`
- Modify: `server/app/resource/agents/mindmap.py`
- Modify: `server/app/resource/agents/quiz.py`
- Modify: `server/app/resource/agents/code.py`
- Modify: `server/app/resource/agents/reading.py`
- Modify: `server/tests/resource/test_agent_integration.py`

- [ ] **Step 1: Add base-agent handoff test helpers**

Append to `server/tests/resource/test_agent_integration.py`:

```python
from app.resource.schemas import DownstreamContext, TeachingOutlineItem, TeachingPlan


def _sample_teaching_plan() -> TeachingPlan:
    return TeachingPlan(
        topic="TCP 三次握手",
        learning_goal="理解三次握手",
        outline=[
            TeachingOutlineItem(
                id="o1",
                title="为什么需要三次握手",
                goal="理解目的",
                key_points=["确认双方收发能力"],
                suggested_visuals=["时序图"],
            ),
            TeachingOutlineItem(
                id="o2",
                title="三次握手过程",
                goal="理解流程",
                key_points=["SYN", "SYN-ACK", "ACK"],
            ),
        ],
    )


def _assert_valid_handoff(ctx: DownstreamContext, source_agent: str):
    assert ctx.schema_version == "resource_handoff/v1"
    assert ctx.source_agent == source_agent
    assert ctx.title
    assert ctx.one_sentence_summary
    assert len(ctx.one_sentence_summary) <= 180
    assert len(ctx.materials) <= 8
    for material in ctx.materials:
        assert len(material.summary) <= 500
        assert len(material.evidence_excerpt) <= 180
```

- [ ] **Step 2: Add context builder test**

Append to `server/tests/resource/test_agent_integration.py`:

```python
def test_build_resource_context_uses_teaching_plan_and_handoffs_only():
    from app.resource.agents.common import build_resource_context
    from app.resource.schemas import ResourceInput

    plan = _sample_teaching_plan()
    handoff = DownstreamContext(
        source_agent="content",
        title="TCP 内容",
        one_sentence_summary="解释 TCP 三次握手。",
    )

    parts = build_resource_context(
        ResourceInput(
            learning_need="学习 TCP",
            agent_name="video",
            teaching_plan=plan,
            upstream_handoffs={"content": handoff},
        )
    )
    joined = "\n\n".join(parts)

    assert "## 教学计划" in joined
    assert "## 上游交接摘要" in joined
    assert "previous_results" not in joined
    assert "规划师指令" not in joined
```

- [ ] **Step 3: Modify `build_resource_context()`**

Replace standalone resource logic in `server/app/resource/agents/common.py`:

```python
def build_resource_context(input_data: ResourceInput) -> list[str]:
    """构建 standalone 多智能体资源生成上下文。"""
    parts = [f"## 学习需求\n{input_data.learning_need}"]
    parts.append(f"## 学习场景\n{input_data.learning_scenario}")

    profile_text = format_learner_profile_for_prompt(input_data.profile)
    if profile_text:
        parts.append(f"## 学习者画像摘要\n{profile_text}")

    if input_data.teaching_plan:
        parts.append(f"## 教学计划\n{input_data.teaching_plan.model_dump_json(indent=2)}")

    if input_data.upstream_handoffs:
        handoffs = {
            agent_id: handoff.model_dump(mode="json")
            for agent_id, handoff in input_data.upstream_handoffs.items()
        }
        parts.append("## 上游交接摘要\n" + json.dumps(handoffs, ensure_ascii=False, indent=2))

    return parts
```

- [ ] **Step 4: Add handoff builder helpers**

In `server/app/resource/agents/common.py`, add:

```python
from app.resource.schemas import DownstreamContext, DownstreamMaterial, ReusableAssets, TeachingPlan


def outline_ids_from_plan(plan: TeachingPlan | None) -> list[str]:
    if not plan:
        return []
    return [item.id for item in plan.outline]


def first_outline_id(plan: TeachingPlan | None) -> str:
    ids = outline_ids_from_plan(plan)
    return ids[0] if ids else ""


def clip_text(value: str, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def build_basic_handoff(
    *,
    source_agent: str,
    title: str,
    summary: str,
    teaching_plan: TeachingPlan | None,
    material_type: str,
    key_points: list[str] | None = None,
    evidence: str = "",
    examples: list[str] | None = None,
    visual_ideas: list[str] | None = None,
    practice_refs: list[str] | None = None,
    code_refs: list[str] | None = None,
    cautions: list[str] | None = None,
) -> DownstreamContext:
    outline_ids = outline_ids_from_plan(teaching_plan)
    material_outline_id = first_outline_id(teaching_plan)
    material = DownstreamMaterial(
        outline_id=material_outline_id,
        type=material_type,
        summary=clip_text(summary, 500),
        key_points=(key_points or [])[:8],
        evidence_excerpt=clip_text(evidence, 180),
        priority=1,
    )
    return DownstreamContext(
        source_agent=source_agent,
        title=clip_text(title, 120),
        one_sentence_summary=clip_text(summary, 180),
        covered_outline_ids=outline_ids,
        materials=[material] if material.summary else [],
        reusable_assets=ReusableAssets(
            examples=(examples or [])[:6],
            visual_ideas=(visual_ideas or [])[:6],
            practice_refs=(practice_refs or [])[:6],
            code_refs=(code_refs or [])[:6],
        ),
        cautions=(cautions or [])[:6],
    )
```

- [ ] **Step 5: Update each base agent to return `metrics` and `downstream_context`**

Use the following patterns.

For `server/app/resource/agents/content.py`, import `build_basic_handoff` and return:

```python
handoff = build_basic_handoff(
    source_agent="content",
    title=f"{title_prefix} - 课程内容",
    summary="生成专业课程讲解文档",
    teaching_plan=config.get("_teaching_plan"),
    material_type="explanation",
    key_points=[],
    evidence=content,
)
return AgentResult(
    success=True,
    content=content,
    file_type="markdown",
    title=f"{title_prefix} - 课程内容",
    summary="生成专业课程讲解文档",
    metrics={"char_count": len(content)},
    downstream_context=handoff,
    metadata={"agent_id": "content"},
)
```

Before calling `_generate_content()`, pass the teaching plan through config:

```python
agent_config = dict(input_data.agent_config)
agent_config["_teaching_plan"] = input_data.teaching_plan
```

Use the same config handoff pattern for `mindmap`, `quiz`, `code`, and `reading` with these `material_type` values:

```python
"mindmap" -> "structure"
"quiz" -> "practice"
"code" -> "code"
"reading" -> "reading"
```

For `quiz`, set `practice_refs` to question ids:

```python
practice_refs=[str(q.get("id")) for q in questions][:6]
```

For `code`, set `code_refs` to the generated language and case type:

```python
code_refs=[language, case_type]
```

For `mindmap`, set `visual_ideas` to branch names:

```python
visual_ideas=list(dict.fromkeys(branches))[:6]
```

- [ ] **Step 6: Rename `summary_data` references to `metrics` in base agent tests**

In `server/tests/resource/test_agent_integration.py`, replace assertions like:

```python
result.summary_data.get("branches")
```

with:

```python
result.metrics.get("branches")
```

Also add assertions after each successful base agent generation:

```python
assert result.downstream_context is not None
_assert_valid_handoff(result.downstream_context, "content")
```

Use the correct source agent string for each test.

- [ ] **Step 7: Run base agent tests**

From `server/`:

```bash
rtk uv run pytest tests/resource/test_agent_integration.py tests/resource/test_teaching_plan_handoff_contract.py -q
```

Expected after implementation: all selected tests pass.

- [ ] **Step 8: Commit**

```bash
rtk git add server/app/resource/agents/common.py server/app/resource/agents/content.py server/app/resource/agents/mindmap.py server/app/resource/agents/quiz.py server/app/resource/agents/code.py server/app/resource/agents/reading.py server/tests/resource/test_agent_integration.py server/tests/resource/test_teaching_plan_handoff_contract.py
rtk git commit -m "refactor: emit downstream handoffs from base agents"
```

---

## Task 5: Refactor ResourceService DAG And Persistence

**Files:**
- Modify: `server/app/resource/service.py`
- Modify: `server/app/resource/items.py`
- Modify: `server/tests/resource/test_video_service_orchestration.py`

- [ ] **Step 1: Add orchestration tests for plan and handoff flow**

Append to `server/tests/resource/test_video_service_orchestration.py`:

```python
def test_worker_input_contains_teaching_plan_not_instruction():
    from app.resource.service import _build_agent_resource_input
    from app.resource.schemas import ResourceGenerationRequest, ResourceInput, TeachingPlan

    request = ResourceGenerationRequest(learning_need="学习 TCP")
    plan = TeachingPlan(topic="TCP", learning_goal="理解 TCP", outline=[])

    resource_input = _build_agent_resource_input(
        request=request,
        resource_id=1,
        agent_id="content",
        teaching_plan=plan,
        profile={},
        upstream_handoffs={},
        agent_config_extra=None,
    )

    assert isinstance(resource_input, ResourceInput)
    assert resource_input.teaching_plan is plan
    assert resource_input.upstream_handoffs == {}
    assert not hasattr(resource_input, "instruction")
    assert not hasattr(resource_input, "previous_results")


def test_handoffs_are_collected_only_from_successful_base_results():
    from app.resource.schemas import AgentResult, DownstreamContext
    from app.resource.service import _collect_successful_handoffs

    content_handoff = DownstreamContext(source_agent="content", title="内容", one_sentence_summary="讲解")
    results = {
        "content": AgentResult(success=True, downstream_context=content_handoff),
        "quiz": AgentResult(success=True),
        "reading": AgentResult(success=False, downstream_context=DownstreamContext(source_agent="reading")),
        "ppt": AgentResult(success=True, downstream_context=DownstreamContext(source_agent="ppt")),
    }

    handoffs = _collect_successful_handoffs(results)

    assert set(handoffs.keys()) == {"content"}
    assert handoffs["content"].source_agent == "content"
```

- [ ] **Step 2: Update `_build_agent_resource_input()` signature**

In `server/app/resource/service.py`, replace the helper signature with:

```python
def _build_agent_resource_input(
    *,
    request: ResourceGenerationRequest,
    resource_id: int,
    agent_id: str,
    teaching_plan: TeachingPlan | None,
    profile: dict[str, Any],
    upstream_handoffs: dict[str, DownstreamContext],
    agent_config_extra: dict[str, Any] | None,
) -> ResourceInput:
```

Use this body:

```python
agent_config = request.agent_configs.get(agent_id, {})
if agent_config_extra:
    agent_config = {**agent_config, **agent_config_extra}
return ResourceInput(
    resource_id=resource_id,
    learning_need=request.learning_need,
    learning_scenario=request.learning_scenario,
    agent_name=agent_id,
    agent_config=agent_config,
    teaching_plan=teaching_plan,
    profile=profile,
    upstream_handoffs=upstream_handoffs,
)
```

Add imports:

```python
from app.resource.schemas import DownstreamContext, TeachingPlan
```

- [ ] **Step 3: Add handoff collector**

In `server/app/resource/service.py`, add near `_select_worker_agents()`:

```python
BASE_RESOURCE_AGENT_IDS = {"content", "mindmap", "quiz", "code", "reading"}


def _collect_successful_handoffs(results: dict[str, AgentResult]) -> dict[str, DownstreamContext]:
    handoffs: dict[str, DownstreamContext] = {}
    for agent_id, result in results.items():
        if agent_id not in BASE_RESOURCE_AGENT_IDS:
            continue
        if not result.success or result.downstream_context is None:
            continue
        handoffs[agent_id] = result.downstream_context
    return handoffs
```

- [ ] **Step 4: Update planning phase**

Replace `blueprint` and `instruction_map` extraction with:

```python
teaching_plan = None
if planning_result.success and planning_result.metadata:
    plan_data = planning_result.metadata.get("teaching_plan")
    if isinstance(plan_data, dict):
        teaching_plan = TeachingPlan.model_validate(plan_data)

if teaching_plan is None:
    logger.error("Planning 未返回 teaching_plan，终止生成: resource_id=%s run_id=%s", resource_id, run_id)
    await emitter.emit_done(success=False, message="规划阶段未返回教学计划")
    done_emitted = True
    success = False
    return
```

Remove `instruction_map` entirely.

- [ ] **Step 5: Update worker phase inputs**

In `run_one()`, pass:

```python
teaching_plan=teaching_plan,
upstream_handoffs={},
```

for base workers. Base workers must not receive other base worker outputs.

Replace `result.summary_data` with `result.metrics` in tracker metrics, logger, and artifact events.

- [ ] **Step 6: Update PPT/Video phase inputs**

After base workers finish:

```python
base_handoffs = _collect_successful_handoffs(base_results)
```

For PPT:

```python
await run_one(PPT_AGENT_ID, {
    "upstream_handoff_agent_ids": list(base_handoffs.keys()),
})
```

and ensure `_build_agent_resource_input()` receives:

```python
upstream_handoffs=base_handoffs,
```

For Video, use the same `base_handoffs`. Remove `previous_result_agent_ids`.

- [ ] **Step 7: Update `save_agent_result()` and item serialization**

In `server/app/resource/service.py`, when creating `GeneratedResourceItemModel`, add:

```python
metrics=result.metrics,
downstream_context=result.downstream_context.model_dump(mode="json") if result.downstream_context else None,
```

In `server/app/resource/items.py`, change `content_envelope()`:

```python
envelope = {
    "title": result.title,
    "summary": result.summary,
    "metadata": result.metadata,
    "format": result.file_type,
    "content": content,
}
```

In `db_item_to_resource_item()`, set:

```python
metrics=item.metrics or {},
downstream_context=(
    DownstreamContext.model_validate(item.downstream_context)
    if isinstance(item.downstream_context, dict)
    else None
),
```

In `db_item_to_agent_result()`, set:

```python
metrics=item.metrics or {},
downstream_context=(
    DownstreamContext.model_validate(item.downstream_context)
    if isinstance(item.downstream_context, dict)
    else None
),
```

Import `DownstreamContext` in `items.py`.

- [ ] **Step 8: Update final resource persistence**

Change `save_generation_results()` signature:

```python
async def save_generation_results(
    self,
    *,
    user_id: int,
    resource_id: int,
    request: ResourceGenerationRequest,
    results: dict[str, AgentResult],
    review_result: ReviewResult,
    teaching_plan: TeachingPlan,
) -> None:
```

Inside it, remove `personalization` writes and set:

```python
resource.teaching_plan = teaching_plan.model_dump(mode="json")
resource.review_result = review_result.model_dump(mode="json")
resource.failed_agents = failed_agents
resource.workflow_metadata = {
    "selected_agents": request.enabled_agent_ids(),
}
```

In `get_resource_bundle()`, replace personalization reads with:

```python
review_result = (
    ReviewResult.model_validate(resource.review_result)
    if isinstance(resource.review_result, dict)
    else None
)
metadata = {
    "source": "database",
    "failed_agents": resource.failed_agents or [],
    "teaching_plan": resource.teaching_plan or {},
}
```

- [ ] **Step 9: Run orchestration tests**

From `server/`:

```bash
rtk uv run pytest tests/resource/test_video_service_orchestration.py tests/resource/test_teaching_plan_handoff_contract.py tests/resource/test_resource_contract.py -q
```

Expected after implementation: all selected tests pass.

- [ ] **Step 10: Commit**

```bash
rtk git add server/app/resource/service.py server/app/resource/items.py server/tests/resource/test_video_service_orchestration.py
rtk git commit -m "refactor: route resource generation through teaching plan handoffs"
```

---

## Task 6: Refactor PPT And Video To Consume Handoffs Only

**Files:**
- Modify: `server/app/resource/agents/ppt.py`
- Modify: `server/app/resource/agents/video.py`
- Modify: `server/app/resource/prompts/ppt_material.md`
- Modify: `server/app/resource/prompts/video_material.md`
- Modify: `server/app/resource/prompts/video_outline.md`
- Modify: `server/tests/resource/test_ppt_internal_multi_agent.py`
- Modify: `server/tests/resource/test_video_agent.py`

- [ ] **Step 1: Add Video input filtering test**

Append to `server/tests/resource/test_video_agent.py`:

```python
def test_video_input_context_uses_upstream_handoffs_only():
    from app.resource.agents.video import _input_context
    from app.resource.schemas import DownstreamContext, ResourceInput, TeachingPlan

    plan = TeachingPlan(topic="TCP", learning_goal="理解 TCP", outline=[])
    handoff = DownstreamContext(
        source_agent="content",
        title="TCP 内容",
        one_sentence_summary="解释三次握手",
    )
    input_data = ResourceInput(
        resource_id=1,
        learning_need="学习 TCP",
        agent_name="video",
        teaching_plan=plan,
        upstream_handoffs={"content": handoff},
    )

    context = _input_context(input_data, {"duration_seconds": 180})

    assert context["teaching_plan"]["topic"] == "TCP"
    assert set(context["upstream_handoffs"].keys()) == {"content"}
    assert "previous_results" not in context
```

- [ ] **Step 2: Update VideoAgent context**

In `server/app/resource/agents/video.py`, replace `_input_context()` with:

```python
VIDEO_SOURCE_AGENT_IDS = {"content", "mindmap", "quiz", "code", "reading"}


def _input_context(input_data: ResourceInput, config: dict[str, Any]) -> dict[str, Any]:
    handoffs = {
        agent_id: handoff.model_dump(mode="json")
        for agent_id, handoff in input_data.upstream_handoffs.items()
        if agent_id in VIDEO_SOURCE_AGENT_IDS
    }
    return {
        "learning_need": input_data.learning_need,
        "learning_scenario": input_data.learning_scenario,
        "profile": input_data.profile,
        "teaching_plan": input_data.teaching_plan.model_dump(mode="json") if input_data.teaching_plan else {},
        "upstream_handoffs": handoffs,
        "config": config,
    }
```

Replace every `input_data.blueprint` usage with `input_data.teaching_plan`.

In fallback topic logic:

```python
fallback_topic = input_data.teaching_plan.topic if input_data.teaching_plan else input_data.learning_need
```

- [ ] **Step 3: Update VideoMaterialDigest source model**

Keep `VideoMaterialDigest.source_map`, but populate it from handoff agent IDs. `VideoMaterialAgent` prompt now receives `upstream_handoffs`.

Update `server/app/resource/prompts/video_material.md` input section:

```markdown
- `teaching_plan`：总体教学方向、大纲和边界
- `upstream_handoffs`：上游基础资源给下游的交接摘要，只包含 content、mindmap、quiz、code、reading 的短摘要、关键点和引用片段
```

Replace the first constraint with:

```markdown
1. 只使用 `teaching_plan` 与 `upstream_handoffs` 中出现的素材，不要求也不要引用上游完整正文。
```

- [ ] **Step 4: Update PPT material construction**

In `server/app/resource/agents/ppt.py`, replace any resource material extraction from `input_data.previous_results` with `input_data.upstream_handoffs`.

Use this material bundle shape:

```python
MaterialBundle(
    topic=input_data.teaching_plan.topic if input_data.teaching_plan else input_data.learning_need,
    learning_goal=input_data.teaching_plan.learning_goal if input_data.teaching_plan else input_data.learning_need,
    blueprint=input_data.teaching_plan.model_dump(mode="json") if input_data.teaching_plan else None,
    artifacts=[
        {
            "agent_id": agent_id,
            "title": handoff.title,
            "summary": handoff.one_sentence_summary,
            "covered_outline_ids": handoff.covered_outline_ids,
            "materials": [material.model_dump(mode="json") for material in handoff.materials],
            "reusable_assets": handoff.reusable_assets.model_dump(mode="json"),
            "cautions": handoff.cautions,
        }
        for agent_id, handoff in input_data.upstream_handoffs.items()
    ],
)
```

If current `MaterialBundle` fields differ, update that Pydantic model to this exact field set.

- [ ] **Step 5: Update PPT/Video output metadata**

PPT and Video results must include:

```python
metadata={
    "agent_id": "video",
    "schema_version": "video/v1",
    "source_handoff_agent_ids": sorted(input_data.upstream_handoffs.keys()),
    "teaching_plan_outline_ids": [
        item.id for item in input_data.teaching_plan.outline
    ] if input_data.teaching_plan else [],
    "missing_source_outline_ids": missing_source_outline_ids,
}
```

For PPT use `"agent_id": "ppt"` and the PPT schema version already present in code.

- [ ] **Step 6: Update tests from previous results to handoffs**

In `server/tests/resource/test_video_agent.py` and `server/tests/resource/test_ppt_internal_multi_agent.py`, replace `previous_results={...AgentResult...}` setup with:

```python
upstream_handoffs={
    "content": DownstreamContext(
        source_agent="content",
        title="TCP 内容",
        one_sentence_summary="解释三次握手",
        covered_outline_ids=["o1"],
        materials=[
            DownstreamMaterial(
                outline_id="o1",
                type="explanation",
                summary="三次握手确认双方收发能力。",
                evidence_excerpt="三次握手用于建立通信初始状态。",
                priority=1,
            )
        ],
    )
}
```

- [ ] **Step 7: Run PPT/Video tests**

From `server/`:

```bash
rtk uv run pytest tests/resource/test_video_agent.py tests/resource/test_ppt_internal_multi_agent.py -q
```

Expected after implementation: tests pass and no code path reads `previous_results`.

- [ ] **Step 8: Commit**

```bash
rtk git add server/app/resource/agents/ppt.py server/app/resource/agents/video.py server/app/resource/prompts/ppt_material.md server/app/resource/prompts/video_material.md server/app/resource/prompts/video_outline.md server/tests/resource/test_video_agent.py server/tests/resource/test_ppt_internal_multi_agent.py
rtk git commit -m "refactor: ground ppt and video in resource handoffs"
```

---

## Task 7: Refactor Review Inputs

**Files:**
- Modify: `server/app/resource/review.py`
- Modify: `server/app/resource/service.py`
- Modify: `server/tests/resource/test_video_service_orchestration.py`

- [ ] **Step 1: Add review envelope test**

Append to `server/tests/resource/test_video_service_orchestration.py`:

```python
def test_video_audit_envelope_uses_teaching_plan_and_handoffs():
    from app.resource.review import build_video_audit_envelope
    from app.resource.schemas import AgentResult, DownstreamContext, ResourceGenerationRequest, TeachingPlan

    request = ResourceGenerationRequest(learning_need="学习 TCP")
    plan = TeachingPlan(topic="TCP", learning_goal="理解 TCP", outline=[])
    handoff = DownstreamContext(source_agent="content", title="内容", one_sentence_summary="解释 TCP")
    results = {
        "content": AgentResult(success=True, downstream_context=handoff, metadata={"agent_id": "content"}),
        "video": AgentResult(
            success=True,
            content='{"schema_version":"video/v1","scenes":[]}',
            file_type="json",
            metadata={"agent_id": "video", "missing_source_outline_ids": []},
        ),
    }

    envelope, missing = build_video_audit_envelope(
        request=request,
        results=results,
        profile={},
        teaching_plan=plan,
    )

    assert missing == []
    assert envelope["teaching_plan"]["topic"] == "TCP"
    assert envelope["upstream_handoffs"]["content"]["source_agent"] == "content"
    assert "previous_results" not in envelope
```

- [ ] **Step 2: Update review builder signatures**

In `server/app/resource/review.py`, change:

```python
build_pre_audit_envelope(..., blueprint=...)
build_ppt_audit_envelope(..., blueprint=...)
build_video_audit_envelope(..., blueprint=...)
```

to:

```python
build_pre_audit_envelope(..., teaching_plan: TeachingPlan | None)
build_ppt_audit_envelope(..., teaching_plan: TeachingPlan | None)
build_video_audit_envelope(..., teaching_plan: TeachingPlan | None)
```

Each envelope must include:

```python
"teaching_plan": teaching_plan.model_dump(mode="json") if teaching_plan else {},
"upstream_handoffs": {
    agent_id: result.downstream_context.model_dump(mode="json")
    for agent_id, result in results.items()
    if result.success and result.downstream_context is not None
},
```

Do not include full `result.content` for base resources in pre-audit, PPT audit, or video audit.

- [ ] **Step 3: Update service calls**

In `server/app/resource/service.py`, replace `blueprint=blueprint` with:

```python
teaching_plan=teaching_plan
```

for all review envelope builders.

- [ ] **Step 4: Run review orchestration tests**

From `server/`:

```bash
rtk uv run pytest tests/resource/test_video_service_orchestration.py -q
```

Expected after implementation: tests pass.

- [ ] **Step 5: Commit**

```bash
rtk git add server/app/resource/review.py server/app/resource/service.py server/tests/resource/test_video_service_orchestration.py
rtk git commit -m "refactor: review teaching plan and handoff envelopes"
```

---

## Task 8: Update Frontend Resource Types

**Files:**
- Modify: `src/features/resource/model/resource.ts`
- Modify: `src/features/resource/views/ResourceGenerator.vue`
- Modify: `src/features/resource/views/ResourceResult.vue`
- Modify: `src/features/resource/components/VideoView.vue`

- [ ] **Step 1: Update TypeScript DTOs**

In `src/features/resource/model/resource.ts`, replace `summary_data` with `metrics` and add downstream context:

```ts
export interface DownstreamMaterial {
  outline_id: string
  type: 'explanation' | 'structure' | 'practice' | 'code' | 'reading' | 'example' | 'visual'
  summary: string
  key_points: string[]
  evidence_excerpt: string
  priority: number
}

export interface DownstreamContext {
  schema_version: 'resource_handoff/v1'
  source_agent: string
  title: string
  one_sentence_summary: string
  covered_outline_ids: string[]
  materials: DownstreamMaterial[]
  reusable_assets: {
    examples: string[]
    misconceptions: string[]
    visual_ideas: string[]
    practice_refs: string[]
    code_refs: string[]
  }
  cautions: string[]
}

export interface GeneratedResourceItem {
  id: string
  type: ResourceAgentId
  title: string
  format: string
  content: unknown
  summary: string
  metrics: Record<string, unknown>
  downstream_context?: DownstreamContext | null
  execution_report?: string | null
  metadata: Record<string, unknown>
  status: string
  error_message?: string | null
  created_at?: string | null
  updated_at?: string | null
}
```

- [ ] **Step 2: Replace frontend field reads**

Run from repo root:

```bash
rtk rg -n "summary_data|execution_plan" src/features/resource
```

For every `summary_data` read, replace with `metrics`.

For every `metadata.execution_plan` read, replace with:

```ts
metadata.teaching_plan
```

where `metadata` is the resource bundle metadata returned by backend.

- [ ] **Step 3: Ensure VideoView accepts new payload path**

In `src/features/resource/components/VideoView.vue`, do not read `downstream_context`. VideoView receives the final video `content` as before. It can show source info from:

```ts
const sourceAgentIds = computed(() => {
  const metadata = normalizedPayload.value?.metadata
  return Array.isArray(metadata?.source_handoff_agent_ids) ? metadata.source_handoff_agent_ids : []
})
```

- [ ] **Step 4: Run frontend build**

From repo root:

```bash
rtk npm run build
```

Expected after implementation: `vue-tsc` and Vite build complete successfully.

- [ ] **Step 5: Commit**

```bash
rtk git add src/features/resource/model/resource.ts src/features/resource/views/ResourceGenerator.vue src/features/resource/views/ResourceResult.vue src/features/resource/components/VideoView.vue
rtk git commit -m "refactor: update frontend resource handoff types"
```

---

## Task 9: Remove Old Contract References

**Files:**
- Modify every file returned by the searches in this task.

- [ ] **Step 1: Search for old standalone resource contract names**

From repo root:

```bash
rtk rg -n "LearningBlueprint|AgentInstruction|ExecutionPlan|summary_data|previous_results|blueprint|instruction_map|personalization\\.execution_plan|resource_guidance" server src
```

Expected after prior tasks: matches remain only in path-domain docs or tests that will be updated in this task.

- [ ] **Step 2: Replace backend old references**

Apply these replacements in backend resource files:

```text
summary_data -> metrics
blueprint -> teaching_plan
previous_results -> upstream_handoffs
ExecutionPlan -> TeachingPlan
```

Do not perform blind replacement in `server/app/path`; inspect each match. If path-domain code only uses `AgentResult.summary_data`, migrate it to `AgentResult.metrics`.

- [ ] **Step 3: Replace tests expecting old types**

In `server/tests/resource/test_resource_refactoring.py`, replace old contract tests with assertions for:

```python
from app.resource.schemas import DownstreamContext, ResourceInput, TeachingPlan


def test_teaching_plan_replaces_execution_plan():
    plan = TeachingPlan(topic="TCP", learning_goal="理解 TCP", outline=[])
    assert plan.topic == "TCP"
    assert not hasattr(plan, "agent_instructions")


def test_resource_input_replaces_worker_state():
    plan = TeachingPlan(topic="TCP", learning_goal="理解 TCP", outline=[])
    handoff = DownstreamContext(source_agent="content", title="内容", one_sentence_summary="讲解")
    state = ResourceInput(
        learning_need="学习 TCP",
        teaching_plan=plan,
        upstream_handoffs={"content": handoff},
    )
    assert state.teaching_plan is plan
    assert state.upstream_handoffs["content"].source_agent == "content"
```

- [ ] **Step 4: Run old-contract search again**

From repo root:

```bash
rtk rg -n "LearningBlueprint|AgentInstruction|ExecutionPlan|summary_data|previous_results|instruction_map|personalization\\.execution_plan|resource_guidance" server src
```

Expected after implementation: no matches in executable resource code. Mentions in migration comments or docs are acceptable only if they describe removed fields and are not read by code.

- [ ] **Step 5: Run focused backend tests**

From `server/`:

```bash
rtk uv run pytest tests/resource/test_teaching_plan_handoff_contract.py tests/resource/test_resource_contract.py tests/resource/test_agent_integration.py tests/resource/test_video_agent.py tests/resource/test_ppt_internal_multi_agent.py tests/resource/test_video_service_orchestration.py -q
```

Expected after implementation: all selected tests pass.

- [ ] **Step 6: Commit**

```bash
rtk git add server src
rtk git commit -m "refactor: remove old resource generation contracts"
```

---

## Task 10: Full Verification

**Files:**
- No code edits unless a verification command exposes a regression.

- [ ] **Step 1: Run resource backend regression suite**

From `server/`:

```bash
rtk uv run pytest tests/resource -q
```

Expected: resource tests pass.

- [ ] **Step 2: Run broader backend smoke suite**

From `server/`:

```bash
rtk uv run pytest tests/resource/test_resource_request_schema.py tests/resource/test_agent_dual_entry.py tests/resource/test_ppt_agent.py tests/resource/test_ppt_standalone.py tests/resource/test_resource_contract.py -q
```

Expected: selected tests pass.

- [ ] **Step 3: Run frontend build**

From repo root:

```bash
rtk npm run build
```

Expected: TypeScript and Vite build pass.

- [ ] **Step 4: Run final old-contract audit**

From repo root:

```bash
rtk rg -n "LearningBlueprint|AgentInstruction|ExecutionPlan|summary_data|previous_results|instruction_map|personalization\\.execution_plan|resource_guidance" server/app src/features/resource
```

Expected: no matches.

- [ ] **Step 5: Manual standalone resource smoke**

Start backend:

```bash
cd /Users/apple/Code/software/server
rtk uv run fastapi dev app/main.py --port 9999
```

Start frontend:

```bash
cd /Users/apple/Code/software
rtk npm run dev
```

Manual check:

```text
1. Generate a resource package with content, mindmap, quiz, ppt, video selected.
2. Confirm planning progress says it generated teaching direction and outline.
3. Confirm content/mindmap/quiz resources save normally.
4. Confirm saved base items have downstream_context in API response.
5. Confirm PPT and Video generate after base resources finish.
6. Confirm PPT/Video metadata includes source_handoff_agent_ids.
7. Confirm final resource bundle metadata includes teaching_plan.
8. Confirm no request or response payload contains summary_data or execution_plan.
```

- [ ] **Step 6: Commit verification fixes**

If verification required fixes:

```bash
rtk git add server src
rtk git commit -m "fix: complete teaching plan handoff verification"
```

If no fixes were needed, do not create an empty commit.

---

## Acceptance Criteria

- PlanningAgent 输出 `TeachingPlan`，只包含总体方向、概要、大纲和边界。
- PlanningAgent 不输出任何 per-agent instruction。
- `ResourceInput` 不包含 `blueprint`、`instruction`、`previous_results`。
- `AgentResult` 使用 `metrics`，不使用 `summary_data`。
- 基础 agent 输出完整资源时同步输出 `downstream_context`。
- `downstream_context` 使用 `resource_handoff/v1`，并受字符数和条目数限制。
- PPT/Video 只消费 `teaching_plan` 和 `upstream_handoffs`，不读取上游完整正文。
- PPT/Video metadata 记录 `source_handoff_agent_ids` 与 `missing_source_outline_ids`。
- Review envelope 包含 `teaching_plan` 和 `upstream_handoffs`，不包含基础资源全文。
- 数据库 `generated_resources` 使用 `teaching_plan/review_result/failed_agents/workflow_metadata`，不再使用 `personalization.execution_plan`。
- 数据库 `generated_resource_items` 使用 `metrics/downstream_context` 一等字段。
- `server/app/infra/models.py` 与 `server/init_schema.sql` 字段一致。
- 前端 DTO 和展示层不再读取 `summary_data` 或 `execution_plan`。
- 资源测试和前端 build 通过。

---

## Suggested Commit Order

1. `refactor: replace resource plan and handoff schemas`
2. `refactor: persist teaching plan and handoff contracts`
3. `refactor: make planning output global teaching plan`
4. `refactor: emit downstream handoffs from base agents`
5. `refactor: route resource generation through teaching plan handoffs`
6. `refactor: ground ppt and video in resource handoffs`
7. `refactor: review teaching plan and handoff envelopes`
8. `refactor: update frontend resource handoff types`
9. `refactor: remove old resource generation contracts`
10. `fix: complete teaching plan handoff verification`
