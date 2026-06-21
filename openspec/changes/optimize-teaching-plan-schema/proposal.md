## Why

当前 `TeachingPlan` 输出的字段存在两类问题：(1) 部分字段（`audience`, `difficulty`, `boundaries`）从未被下游 Agent 实际消费或约束生成行为，只是作为 prompt 中的"噪音"文本注入；(2) Planning 的输出是"广播式"的——所有 Agent 拿到同一份全量 TeachingPlan，自己判断该覆盖哪些大纲点，导致覆盖重叠、大纲点遗漏、风格不一致。需要精简冗余字段，并增加 Agent 级别的指派合约，让 Plan 真正发挥"约束不偏离"的作用。

## What Changes

- **删除 TeachingPlan 中未被消费的字段**：移除 `audience`、`difficulty`——5 个基础 Agent 和聚合 Agent 均未依据这两个字段做任何差异化处理；`boundaries` 退化为纯文本提示，对 LLM 约束力极弱，改由 `agent_assignments[].boundary_notes` 替代（更精准）
- **将 `TeachingOutlineItem.must_not_miss` 升级为一等消费点**：在 `merge_workers_node` 中引入覆盖度检查，`must_not_miss` 大纲点未被覆盖时发出 SSE 警告事件，影响最终 `status` 判定（`partial_completed` vs `completed`）
- **新增 `AgentAssignment` 模型**：Planning 为每个选中的 Agent 生成精确指派——`assigned_outline_ids`、`focus_instruction`、`style_constraint`、`boundary_notes`、`key_points_emphasis`、`avoid_overlap_with`
- **Worker Agent 从全量消费改为切片消费**：`build_resource_context()` 和各 Agent 只注入自己的 `AgentAssignment` + 对应大纲切片，不再注入整个 TeachingPlan
- **优化 Planning Prompt**：从"你不负责分配具体任务"反转为"你需要为每个选中的 Agent 生成精确指派合约"
- **`TeachingPlan.summary` 保留但降权**：不再作为 Agent prompt 的核心上下文注入，仅用于前端展示和 PPT 聚合参考

**BREAKING**: `TeachingPlan` schema 变更影响 `PlanningAgent` 输出、所有基础 Agent 的 `generate_resource()` 方法、`DownstreamContext` 构建逻辑、`merge_workers_node` 流程。

## Capabilities

### New Capabilities
- `agent-assignment`: Planning 为每个选中 Agent 生成的精确指派合约，包含覆盖大纲点、聚焦指令、风格约束、边界提醒和重叠回避规则
- `coverage-check`: Worker 合并后的覆盖度检查机制——检测大纲点遗漏、核心大纲未被覆盖时发出警告事件

### Modified Capabilities
- `resource-service-orchestration`: TeachingPlan schema 变更导致 workflow nodes 和 Agent 消费方式改变，`build_resource_context` 从全量注入改为切片注入

## Impact

- **Schema 变更**: `app/resource/schemas/plan.py` — `TeachingPlan` 移除 `audience`, `difficulty`, `boundaries`，新增 `agent_assignments`
- **Planning Agent**: `app/resource/agents/planning.py` 和 `prompts/planning.md` — 从"纯大纲"模式改为"大纲 + 指派合约"模式
- **所有基础 Agent**: `content.py`, `mindmap.py`, `quiz.py`, `code.py`, `reading.py` — `generate_resource()` 改为接收自己的 `AgentAssignment` 切片
- **公共模块**: `agents/common.py` — `build_resource_context()` 和 `build_basic_handoff()` 增加按 Agent assignment 切片逻辑
- **Workflow**: `workflow/nodes.py` — `merge_workers_node` 增加覆盖度检查，`planning_node` 解析 `agent_assignments` 注入 state
- **Workflow State**: `workflow/state.py` — `ParentState` 可能需要新增字段传递 assignment 映射
- **聚合 Agent**: `ppt.py`, `video.py` — 消费 `agent_assignments` 中与自身相关的部分
- **前端**: SSE 事件增加 `coverage_gap_warning` 类型，资源详情页可展示覆盖热力图（可选）