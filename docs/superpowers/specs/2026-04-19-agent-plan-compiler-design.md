# Agent 计划模式优化设计（严格模式）

- 日期: 2026-04-19
- 目标模块: `server/app/chat/agent.py`
- 设计目标优先级: 回答质量 > 稳定性 > 速度

## 1. 背景与问题

当前 Planner 虽已支持结构化输出，但在计划与执行契约上仍存在风险：

1. 计划可执行性依赖执行期补救，容易出现“先执行再发现不可执行”。
2. 失败恢复主要依赖 `replan`，缺少对“重复无效重规划”的显式熔断机制。
3. 前端体验上需要避免长时间等待和循环重试，但不能牺牲质量与稳定性。

## 2. 目标与非目标

### 2.1 目标

1. Planner 明确感知可用工具与技能，只生成可执行步骤。
2. 执行前引入编译阶段，拒绝不可执行计划。
3. 严格模式下执行器不做猜测性修复，失败即重规划。
4. 保证不会出现无限 `replan`。

### 2.2 非目标

1. 不改造 direct/vision 主路径行为。
2. 不引入复杂多代理协同规划。
3. 不追求“零 replan”，而是追求“有界、可解释、可收敛”。

## 3. 方案对比与决策

### 方案 A（采用）：契约编译器优先 + 模板兜底

- Planner 基于能力白名单生成计划。
- 新增 `compile_plan` 将计划编译为可执行计划。
- 编译失败直接 `replan`，执行失败也直接 `replan`。
- 常见任务可用轻量模板缩短首轮规划时间。

### 方案 B：纯 Prompt 约束

- 仅强化提示词和 schema。
- 缺点是稳定性仍依赖模型波动，不适合严格模式。

### 方案 C：全模板化

- 稳定但灵活性差，难覆盖复杂长尾请求。

**决策**：采用方案 A。

## 4. 目标架构

```
START
  -> classify
    -> direct_answer -> END
    -> vision_answer -> END
    -> planner -> compile_plan -> execute_step
         -> execute_step (next_step)
         -> replan -> planner
         -> final_summarize -> END
         -> end -> END
```

说明：

1. `planner` 只负责生成“候选计划”。
2. `compile_plan` 负责强校验和编译，失败不允许进入执行。
3. `execute_step` 内部完成流程决策（next/replan/final），不再单独设置 `step_guard`。
4. `replan` 仅负责重规划触发和预算控制。

## 5. Planner-Executor 契约

### 5.1 输入契约（给 Planner）

`available_capabilities` 必须包含：

1. `name`: 工具/技能名。
2. `kind`: `tool` 或 `skill`。
3. `required_args`: 必填参数名列表。
4. `arg_schema`: 参数类型定义（最小集即可）。
5. `description`: 能力说明（精简）。

Planner 约束：

1. 只能使用白名单能力。
2. `final_answer` 必须且只能在末尾。
3. 禁止无意义重复步骤。

### 5.2 输出契约（Planner 产物）

每步固定结构：

1. `kind`: `tool | skill | llm | final_answer`
2. `name`
3. `goal`
4. `args_hint`（字典）

## 6. 编译阶段（新增）

新增节点：`compile_plan`。

输入：`plan`（Planner 输出）。
输出：

1. `compiled_plan`: 可执行计划（标准化后的步骤）。
2. `compile_ok`: 布尔值。
3. `compile_errors`: 结构化错误列表。
4. `last_compile_error_code`: 主要错误码。

校验规则：

1. `kind` 合法。
2. `tool/skill` 的 `name` 在白名单中。
3. 必填参数齐全且类型匹配。
4. `final_answer` 唯一且位于末尾。
5. 禁止连续重复且参数相同的低价值步骤（如重复搜索）。

## 7. 严格执行策略

1. 仅执行 `compiled_plan`。
2. 执行器不自动猜测修复参数。
3. 工具运行时错误（timeout/exception）直接标记失败并进入 `replan`。
4. `execute_step` 直接输出下一跳决策（`next_step | replan | final_summarize | end`）。
5. 失败上下文（错误码、失败步骤、已完成摘要）回传下一轮 planner。

## 8. 防无限 Replan 机制（硬约束）

必须同时启用以下三层保护：

### 8.1 预算上限（Hard Cap）

- `MAX_REPLAN_ATTEMPTS` 设为固定上限（建议 3）。
- 达上限后强制进入 `final_summarize`，禁止再次重规划。

### 8.2 重复错误熔断（Repeat Breaker）

- 若连续两轮（或可配 N 轮）`last_compile_error_code` 相同且失败步骤语义相同，判定为“无前进”。
- 直接熔断到 `final_summarize`，并输出明确边界与下一步建议。

### 8.3 前向进展检测（Progress Guard）

- 以“新增成功步骤数、关键信息覆盖度、计划差异度”判断是否有实质进展。
- 连续无进展时提前终止重规划，避免用户等待。

## 9. 状态字段调整

在 `TutorState` 中新增：

1. `compiled_plan: list[PlanStep]`
2. `compile_ok: bool`
3. `compile_errors: list[dict]`
4. `last_compile_error_code: str`
5. `replan_streak_signature: str`（用于重复失败检测）
6. `no_progress_replan_count: int`

保留：

1. `plan`
2. `replan_count`
3. `step_results`
4. `last_failure_reason`

## 10. 错误码体系（最小集）

1. `UNKNOWN_CAPABILITY`
2. `INVALID_STEP_KIND`
3. `MISSING_REQUIRED_ARG`
4. `ARG_TYPE_MISMATCH`
5. `PLAN_TERMINATION_INVALID`
6. `DUPLICATE_LOW_VALUE_STEP`
7. `TOOL_RUNTIME_ERROR`
8. `TOOL_TIMEOUT`
9. `REPLAN_STAGNATION`
10. `REPLAN_BUDGET_EXHAUSTED`

## 11. 测试与验收

### 11.1 单元测试

1. 编译器每条规则至少一条正反用例。
2. 错误码映射正确。
3. 重复失败熔断与预算上限生效。

### 11.2 集成测试

1. 文档问答正常链路。
2. 编译失败 -> replan -> 成功链路。
3. 工具运行失败 -> replan -> 成功链路。
4. 连续 replan 无进展 -> 熔断收口链路。

### 11.3 验收指标

1. 白名单范围内 `compile pass rate >= 95%`。
2. 失败可解释性 `100%`（有错误码和失败节点）。
3. `infinite replan incidents = 0`。
4. 达上限后必收口，且输出可执行下一步建议。

## 12. 风险与缓解

1. 风险：约束过严导致首轮通过率下降。
- 缓解：补充高频模板和参数默认策略（在 planner 阶段，不在 execute 阶段猜）。

2. 风险：熔断过早影响成功率。
- 缓解：将“重复错误轮数”和“无进展阈值”参数化，灰度调优。

3. 风险：错误码粒度不足影响可观测性。
- 缓解：先最小集上线，再按日志扩展。

## 13. 实施顺序（建议）

1. 定义 `available_capabilities` 数据结构并注入 planner。
2. 实现 `compile_plan` 节点与错误码。
3. 切换 execute 使用 `compiled_plan`，并将原 guard 决策内聚到 execute 节点。
4. 接入三层防无限重规划机制。
5. 增加测试与指标埋点。
