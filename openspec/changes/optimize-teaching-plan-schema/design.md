## Context

当前 `TeachingPlan` 是 `app/resource/schemas/plan.py` 中定义的 Pydantic 模型，由 `PlanningAgent` 输出，被 5 个基础 Agent（content, mindmap, quiz, code, reading）和 2 个聚合 Agent（ppt, video）消费。

架构核心问题：
- `TeachingPlan` 的 `audience`、`difficulty`、`boundaries` 字段在所有 Agent 中从未被用于任何逻辑判断或差异化生成
- Planning 输出是"广播式"——全部 Agent 拿全量 TeachingPlan JSON，自行判断覆盖范围
- `outline_ids_from_plan()` 返回全量 ID 列表，5 个 Agent 声称覆盖相同的 outline IDs，没有区分
- `CodeAgent` 用 `select_outline_ids_by_keywords()` 做关键字模糊匹配选 outline_id，脆弱且不稳定
- `must_not_miss` 布尔字段存在于 `TeachingOutlineItem` 但从未被任何消费逻辑检查

## Goals / Non-Goals

**Goals:**
- 精简 TeachingPlan，删除未被消费的字段（`audience`, `difficulty`, `boundaries`）
- 新增 `AgentAssignment` 模型，让 Planning 为每个 Agent 生成精确指派
- Worker Agent 从全量消费改为只消费自己的 assignment 切片
- `must_not_miss` 升级为一等消费点——未覆盖时发出警告
- Optimization of Planning prompt for agent-aware assignment generation

**Non-Goals:**
- 不改变 LangGraph 的拓扑结构（Planning → Workers → Merge → Aggregation → Save 顺序不变）
- 不改变 SSE 事件系统的架构（只新增 `coverage_gap_warning` 事件类型）
- 不改 PPT/Video Agent 的内部实现逻辑（只改变输入方式）
- 不改数据库 schema（`generated_resources.teaching_plan` 存 JSON，新字段自然兼容）
- 不改 NodeInput 路径域的入口（path_helpers.py 只调 `generate_node()`，不受影响）

## Decisions

### Decision 1: 删除 `audience`, `difficulty`, `boundaries` — 而非保留为可选

**选择**: 直接删除，不保留为 `Optional` 字段。

**理由**: 这三个字段在所有 5+2 Agent 的代码中没有任何消费点。保留为 `Optional` 会给 LLM 额外的输出来增加幻觉风险，且 Planning prompt 需要引导 LLM 生成更精准的 per-agent 指令来替代。`boundaries` 的功能由 `AgentAssignment.boundary_notes` 精准替代——每个 Agent 收到自己的边界提醒，而不是一个全局的模糊边界。

**替代方案**: 保留为 `Optional` + 注释"未消费"→ 放弃，因为这会让 LLM 仍然试图填充这些字段，浪费输出 token 且不增加约束力。

### Decision 2: `AgentAssignment` 作为 `TeachingPlan` 的子字段而非独立模型

**选择**: `agent_assignments: list[AgentAssignment]` 作为 `TeachingPlan` 的字段。

**理由**: Assignment 依赖 outline ID，必须与大纲绑定。如果独立存储，需要额外的映射逻辑。放在 `TeachingPlan` 内让 Planning 一次输出，Worker 一次解析。

**替代方案**: Assignment 作为 `ParentState` 独立字段 → 放弃，因为 Assignment 的 outline_ids 引用 TeachingPlan.outline，分开会增加数据一致性风险。

### Decision 3: Worker 消费方式——切片注入而非全量注入

**选择**: 新增 `build_agent_assignment_context()` 函数，每个 Worker Agent 只注入自己的 `AgentAssignment` + 对应的 `outline` 切片。

**理由**:
- 减少 prompt token（全量 TeachingPlan ~2000 字符 vs 切片 ~500 字符）
- 聚焦 Agent 不被无关大纲项干扰
- 降低越界风险

**替代方案**: 继续全量注入但增加约束 prompt → 放弃，LLM 对长上下文中的约束指令遵从率不稳定。

### Decision 4: 覆盖度检查放在 `merge_workers_node` 而非新增 node

**选择**: 在现有 `merge_workers_node` 中增加覆盖度计算和事件发射。

**理由**: 不改变图拓扑。merge_workers 已经是汇聚点，覆盖度检查只有所有 Worker 完成后才能做。

**替代方案**: 新增 `coverage_check_node` 在 merge_workers 后面 → 放弃，增加不必要的拓扑复杂度且需要修改 `route_after_merge`。

### Decision 5: `summary` 保留但降权——只用于前端和 PPT 参考

**选择**: 保留 `TeachingPlan.summary` 字段（前端展示需要），但 Worker Agent prompt 不再注入 summary 作为核心上下文。

**理由**: 前端状态页已展示 summary。PPT/Video 聚合 Agent 可从 `AgentAssignment.summary_for_aggregation` 获取更精准的摘要。移除会让前端丢失展示内容。

## Risks / Trade-offs

- **[Breaking change]** `TeachingPlan` 的 `audience`, `difficulty`, `boundaries` 字段删除后，数据库中已存储的旧 `teaching_plan` JSON 在读取时会被 Pydantic 忽略。需将 `model_config` 从 `extra="forbid"` 改为 `extra="ignore"` 以兼容旧数据。→ **缓解**: Pydantic V2 的 `extra="ignore"` 可安全忽略未知字段。

- **[Planning Agent 输出复杂度增加]** Agent 需要生成 `agent_assignments`，输出 token 增加约 30-50%。→ **缓解**: `agent_assignments` 字段结构明确、格式固定（每 Agent 约 5 行 JSON），比起之前模糊的"全局教学策略"文本，LLM 生成结构化指派的准确率更高。

- **[Prompt engineering 风险]** Planning prompt 从"不分配任务"改为"生成指派合约"，LLM 需要理解每个 Agent 的定位。→ **缓解**: prompt 中明确列出每个 Agent 的职责和生成目标，减少歧义。

- **[Code Agent 的 outline_id 选择逻辑变简单]** 之前用 `select_outline_ids_by_keywords()` 关键字匹配，改为 Planning 直接指定 `assigned_outline_ids`。→ **正面影响**: 消除关键字匹配的不稳定性。