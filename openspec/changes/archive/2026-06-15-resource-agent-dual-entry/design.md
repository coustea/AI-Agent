## Context

资源 Agent 系统当前使用单一的 `run(WorkerState) -> WorkerResult` 入口。多智能体资源生成和路径规划节点资源生成都通过这个入口，但输入语义完全不同：

- 多智能体场景：`WorkerState` 携带 `learning_need`、`blueprint`、`instruction`、`profile`
- 路径规划场景：PathService 把 `path.goal`、`node.title`、`tutorial.content_markdown[:1200]` 拼成字符串塞进 `learning_need`

这导致 Agent 无法区分两种场景，路径场景的结构化信息（知识点、薄弱点、教程全文、生成重点）全部丢失。

当前涉及的表：
- `generated_resources` + `generated_resource_items`：多智能体资源包
- `path_node_resources`：路径节点资源（缺少 summary/status/error_message/input_json）

## Goals / Non-Goals

**Goals:**
- 每个 Agent 提供两个对等入口：`generate_resource(ResourceInput)` 和 `generate_node(NodeInput)`
- 路径规划传入结构化节点上下文，不再拼字符串
- 路径节点资源类型限定为 content/mindmap/ppt/code
- 统一输出为 AgentResult，删除 WorkerState 和 WorkerResult
- PathNodeResource 补齐 generation 状态字段

**Non-Goals:**
- 不改变 PPT 内部流水线（MaterialAgent/OutlineAgent/SlideAgent/PayloadBuilder）
- 不合并 generated_resources 和 path_node_resources 两张表
- 不给路径场景加 reading 和 quiz 资源类型
- 不重构 ResourceService 的编排 DAG（planning → workers → review + PPT → bundle）
- 不改前端 Vue 组件的渲染逻辑（只改按钮来源和类型支持）

## Decisions

### D1: 两个输入类型互不继承

`ResourceInput` 和 `NodeInput` 是独立的两个 Pydantic model，不共享基类。

**理由**：两者的必填字段完全不同。ResourceInput 有 blueprint/instruction/previous_results，NodeInput 有 node_title/tutorial_markdown/knowledge_points。强行用继承会导致一方携带大量 None 字段。

**替代方案**：Union[ResourceInput, NodeInput] 单入口 — 拒绝，因为调用方需要知道传哪个，两个方法签名比 Union 分支更清晰。

### D2: 路径场景不传 existing_resources

NodeInput 不携带 `existing_resources`（之前的 `previous_results` 对应物）。

**理由**：用户明确表示路径规划每次调用 Agent 生成资源是独立的，不需要看到同节点其他已生成资源。

### D3: PlanningAgent 和 ReviewAgent 的 generate_node 返回 not-supported

```python
async def generate_node(self, input: NodeInput) -> AgentResult:
    return AgentResult(success=False, error="planning/review agent 不用于路径节点资源生成")
```

**理由**：路径规划不走多智能体 DAG，不需要 planning 和 review。

### D4: 删除 run_single_agent_generation()

**理由**：用户明确表示不要过度封装。单 Agent 场景直接调用 `agent.generate_resource()`，不需要 service 层的额外包装函数。

### D5: AgentResult 字段与 WorkerResult 对齐

字段完全一致，只是换名。这样 `items.py` 和 `review.py` 的字段访问不需要改。

### D6: PathNodeResource 补齐 4 个字段

- `summary: str | None` — 资源摘要
- `status: str` — 默认 "completed"，失败时为 "failed"
- `error_message: str | None` — 失败原因
- `input_json: dict[str, Any] | None` — 生成时的完整 NodeInput 快照

**理由**：与 GeneratedResourceItem 对齐状态追踪能力。input_json 用于调试和重放。

### D7: PPT 素材构建拆为两个函数

`build_resource_material(input: ResourceInput) -> MaterialBundle` 和 `build_node_material(input: NodeInput) -> MaterialBundle`。

MaterialBundle 增加 `source_type: Literal["resource", "node"]` 和 `node_context: NodeMaterialContext | None`。

**理由**：PPT 内部流水线需要知道素材来源以调整大纲策略。node_context 提供路径节点的教学上下文。

## Risks / Trade-offs

- **[breaking change]** 删除 WorkerState/WorkerResult 是全仓库 breaking change → 一次性完成所有替换，Task 13 用 grep 确保无残留
- **[数据库迁移]** PathNodeResource 加字段需要 ALTER TABLE → 新字段都有默认值，existing rows 不受影响，无需 data migration
- **[PPT 回归]** PptAgent 内部流水线最复杂，拆素材构建可能引入 bug → 保持内部流水线不变，只改入口和素材构建
- **[路径 quiz 分流]** 路径节点的 quiz 走独立的 NodeLearningAgent → 不影响，两个系统并行
