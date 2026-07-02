# Resource Agent 非空输出契约设计

## 背景

资源生成流程当前允许 Planning、Quiz、Reading 的结构化输出模型接收空集合：

- `TeachingPlan.agent_assignments`
- `QuizPayload.questions`
- `ReadingPayload.resources`

因此，大模型网关会把业务上无效的响应视为结构化输出成功。无效结果直到 Agent 内部或工作流验证阶段才暴露，并触发无反馈的重复调用或最终验证失败。

本次重构不增加重试、兜底数据或旧实现兼容分支。目标是重新划分数据所有权，使空集合无法进入成功结果。

## 约束

- 保持当前对外 JSON 结构不变。
- `resource` 与 `path` 继续共用 Agent 类，但不合并记录、详情页或持久化模型。
- 删除 Planning 和 Reading 当前针对空集合的重试流程。
- 不以提示词加强、结果修补或默认占位内容掩盖生成失败。
- 无法生成合法结果时，在 generation 阶段明确失败，不把无效对象传入工作流 validation。

## 方案

### Planning：代码拥有 Agent 指派

大模型只负责生成：

- 非空教学策略
- 3 至 8 个非空教学大纲项

`PlanningAgent` 根据请求中的 `enabled_agents` 和已生成大纲确定性构造 `agent_assignments`。每个启用 Agent 恰好生成一条指派，Agent ID 直接来自请求，不再由模型复述。

指派规则由 Agent 角色定义：

- 每个 Agent 覆盖所有 `must_not_miss` 大纲项。
- 若没有大纲项显式标为 `must_not_miss`，覆盖全部大纲项。
- `focus_instruction`、`style_constraint`、`boundary_notes`、`avoid_overlap_with` 来自资源 Agent 的集中式角色定义。
- `key_points_emphasis` 从所覆盖大纲项的关键知识点按顺序去重生成。

这样，Planning 的成功结果在构造上保证：

- 指派集合与 `enabled_agents` 完全一致。
- 不存在重复 Agent ID。
- 所有指派只引用真实大纲 ID。
- 核心大纲项必然被覆盖。

旧的空指派检测和第二次 LLM 调用全部删除。

### Quiz：运行时精确题数契约

Quiz 保留大模型创作题目的职责，但输出模型根据当前 `question_count` 动态创建：

- `questions.min_length == question_count`
- `questions.max_length == question_count`
- `question_count` 必须是正整数

题目模型同时负责验证：

- 题型属于支持集合。
- 选择题选项数量与标签合法且唯一。
- 单选答案属于选项标签。
- 多选答案至少两个且全部属于选项标签。
- 判断题答案为布尔值。
- 题目 ID 唯一。

Quiz 只执行一次严格结构化调用。空题集、少题、多题或答案不合法均不能成为 `QuizPayload`，因此不会产生 `success=True` 的空结果。

### Reading：搜索结果拥有资源记录

阅读资源的标题、URL 和摘要来自搜索工具，代码负责：

1. 解析统一搜索结果格式。
2. 只保留包含合法 HTTP/HTTPS URL 的记录。
3. 按规范化 URL 去重。
4. 截取 `max_items` 条，并确保数量达到 `min_items`。
5. 确定性转换为 `ReadingResource`。
6. 根据资源顺序构造由浅到深的 `learning_path`。

Reading 不再调用大模型重新生成或抄写搜索资源，也不再合并两轮 LLM 结果。搜索已有有效记录时，模型无法再把它们变成空列表。

若所有查询结束后仍不足 `min_items`，Agent 直接以明确的资源不足错误结束。该错误表示外部搜索确实没有满足请求，而不是生成结果被模型丢失。

## 数据流

### Planning

`ResourceInput` → 严格非空大纲生成 → 确定性 Agent 指派 → `TeachingPlan` → `AgentResult`

### Quiz

`ResourceInput` → 运行时精确题数 Schema → 单次严格结构化生成 → `QuizPayload` → `AgentResult`

### Reading

`ResourceInput` → 搜索查询 → URL 解析、规范化、去重 → `ReadingPayload` → `AgentResult`

## 错误处理

- Planning 大纲为空或结构无效：generation 失败。
- Quiz 严格结构化调用无法生成精确题数：generation 失败。
- Reading 有效搜索记录少于 `min_items`：generation 失败，错误包含期望数与实际数。
- 工作流 validation 保留为跨边界防线，但不再承担发现 Agent 自身空输出的首要职责。
- 不进行空结果重试，不产生占位题目、占位资源或虚构 URL。

## 测试策略

先添加失败回归测试并确认 RED：

1. Planning 在模型只返回大纲时，仍为所有启用 Agent 构造且仅构造一条合法指派，并且只调用模型一次。
2. Quiz 的运行时 Schema 拒绝空题集、少题和多题；接受精确题数。
3. Reading 将有效搜索结果直接转换成非空资源及学习路径，不调用大模型。
4. Reading 在有效 URL 数量不足时直接失败，不进行第二轮搜索或生成重试。

实现后运行：

- Resource 定向测试。
- Schema 验证测试。
- Backend 全量测试；仅忽略项目文档列出的既有失败。

## 非目标

- 不改变前端展示契约。
- 不修改资源记录或学习路径记录的持久化边界。
- 不为搜索服务增加新的供应商或缓存。
- 不调整 Content、Mindmap、Code、PPT、Video Agent 的生成逻辑。
