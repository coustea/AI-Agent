# Agent 计划模式优化设计（严格模式，低 Replan）

- 日期: 2026-04-19
- 目标模块: `server/app/chat/agent.py`
- 设计目标优先级: 回答质量 > 稳定性 > 速度
- 核心约束: 默认不触发 `replan`，仅在执行失败时允许一次兜底重规划

## 1. 背景与问题

当前 Planner 虽已支持结构化输出，但计划与执行契约仍有两个核心风险：

1. 计划可执行性依赖执行期补救，容易出现“先执行再发现不可执行”。
2. 失败恢复路径若无约束，容易放大等待时间与不确定性。

## 2. 目标与非目标

### 2.1 目标

1. Planner 明确感知可用工具与技能，只生成可执行步骤。
2. 执行前引入编译阶段，拒绝不可执行计划。
3. 严格模式下执行器不做猜测性修复。
4. `replan` 只作为执行失败的一次性兜底，不进入循环。

### 2.2 非目标

1. 不改造 direct/vision 主路径行为。
2. 不引入复杂多代理协同规划。
3. 不允许多轮重规划循环。

## 3. 方案对比与决策

### 方案 A（采用）：契约编译器优先 + 单次 Replan 兜底

- Planner 基于能力白名单生成计划。
- 新增 `compile_plan` 将计划编译为可执行计划。
- 编译失败直接收口；执行失败允许一次 `replan`。
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
         -> replan_once -> planner
         -> final_summarize -> END
         -> end -> END
```

说明：

1. `planner` 只负责生成“候选计划”。
2. `compile_plan` 负责强校验和编译，失败不进入执行。
3. `execute_step` 内部完成流程决策（`next_step | replan_once | final_summarize | end`）。
4. `replan_once` 仅可触发一次，用于执行失败兜底。

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

## 7. 严格执行策略（低 Replan）

1. 仅执行 `compiled_plan`。
2. 执行器不自动猜测修复参数。
3. `compile_ok=false` 时直接进入 `final_summarize`。
4. 工具运行时错误（timeout/exception）触发 `replan_once`（若尚未使用）。
5. `replan_once` 后再次失败，直接 `final_summarize`。
6. 失败上下文（错误码、失败步骤、已完成摘要）回传下一轮 planner（仅一次）。

## 8. 防循环 Replan 硬约束

1. 状态中增加 `replan_used: bool`，默认 `false`。
2. 仅当 `replan_used=false` 且失败类型为 `EXECUTION_FAILED` 时允许 `replan_once`。
3. 触发一次后立刻置 `replan_used=true`，后续任何失败都禁止 replan。
4. 启动期自检：若路由决策出现 `replan` 且 `replan_used=true`，强制改写为 `final_summarize`。
5. 监控指标要求 `replan_count_per_request <= 1`。

## 9. 状态字段调整

在 `TutorState` 中新增：

1. `compiled_plan: list[PlanStep]`
2. `compile_ok: bool`
3. `compile_errors: list[dict]`
4. `last_compile_error_code: str`
5. `replan_used: bool`

保留：

1. `plan`
2. `step_results`
3. `last_failure_reason`

移除：

1. `replan_count`
2. 多轮重规划相关计数与签名字段

## 10. 错误码体系（最小集）

1. `UNKNOWN_CAPABILITY`
2. `INVALID_STEP_KIND`
3. `MISSING_REQUIRED_ARG`
4. `ARG_TYPE_MISMATCH`
5. `PLAN_TERMINATION_INVALID`
6. `DUPLICATE_LOW_VALUE_STEP`
7. `TOOL_RUNTIME_ERROR`
8. `TOOL_TIMEOUT`
9. `COMPILE_FAILED`
10. `EXECUTION_FAILED`

## 11. 测试与验收

### 11.1 单元测试

1. 编译器每条规则至少一条正反用例。
2. 错误码映射正确。
3. `replan_used` 闸门逻辑正确（仅允许一次）。

### 11.2 集成测试

1. 文档问答正常链路。
2. 编译失败 -> `final_summarize` 收口链路。
3. 执行失败 -> `replan_once` -> 成功链路。
4. 执行失败 -> `replan_once` -> 再失败 -> `final_summarize` 收口链路。

### 11.3 验收指标

1. 白名单范围内 `compile pass rate >= 95%`。
2. 失败可解释性 `100%`（有错误码和失败节点）。
3. `replan_count_per_request <= 1`。
4. `replan_invocation_rate` 持续下降并维持低位。

## 12. 风险与缓解

1. 风险：编译失败直接收口可能降低一次性成功率。
- 缓解：提高 planner 输入约束质量（能力白名单、必填参数、模板兜底）并强化编译器提示。

2. 风险：单次 replan 仍增加等待时间。
- 缓解：仅对执行失败开放，且仅一次；并在 prompt 中优先“一步到位计划”。

3. 风险：错误码粒度不足影响可观测性。
- 缓解：先最小集上线，再按日志扩展。

## 13. 实施顺序（建议）

1. 定义 `available_capabilities` 数据结构并注入 planner。
2. 实现 `compile_plan` 节点与错误码。
3. 切换 execute 使用 `compiled_plan`，并内聚决策为 `next_step | replan_once | final_summarize | end`。
4. 增加 `replan_used` 闸门并删除多轮重规划相关字段。
5. 增加测试与指标埋点。

