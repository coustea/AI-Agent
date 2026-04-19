# Agent 计划模式优化设计（严格模式，零 Replan）

- 日期: 2026-04-19
- 目标模块: `server/app/chat/agent.py`
- 设计目标优先级: 回答质量 > 稳定性 > 速度
- 核心约束: 永不进入 `replan`

## 1. 背景与问题

当前 Planner 虽已支持结构化输出，但计划与执行契约仍有两个核心风险：

1. 计划可执行性依赖执行期补救，容易出现“先执行再发现不可执行”。
2. 失败恢复路径会放大等待时间与不确定性。

## 2. 目标与非目标

### 2.1 目标

1. Planner 明确感知可用工具与技能，只生成可执行步骤。
2. 执行前引入编译阶段，拒绝不可执行计划。
3. 严格模式下执行器不做猜测性修复。
4. 全流程零 `replan`，失败直接收口。

### 2.2 非目标

1. 不改造 direct/vision 主路径行为。
2. 不引入复杂多代理协同规划。
3. 不在失败后进行二次规划循环。

## 3. 方案对比与决策

### 方案 A（采用）：契约编译器优先 + Fail-Fast 收口

- Planner 基于能力白名单生成计划。
- 新增 `compile_plan` 将计划编译为可执行计划。
- 编译失败或执行失败都直接 `final_summarize`，不触发重规划。
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
         -> final_summarize -> END
         -> end -> END
```

说明：

1. `planner` 只负责生成“候选计划”。
2. `compile_plan` 负责强校验和编译，失败不允许进入执行。
3. `execute_step` 内部完成流程决策（`next_step | final_summarize | end`）。
4. 不存在 `replan` 节点与分支。

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

## 7. 严格执行策略（零 Replan）

1. 仅执行 `compiled_plan`。
2. 执行器不自动猜测修复参数。
3. 工具运行时错误（timeout/exception）直接标记失败并进入 `final_summarize`。
4. `execute_step` 直接输出下一跳决策（`next_step | final_summarize | end`）。
5. 失败上下文（错误码、失败步骤、已完成摘要）用于最终总结，不回流到 planner。

## 8. 零 Replan 硬约束

1. 图结构中不注册 `replan` 节点。
2. `guard_route` / 决策枚举中不允许出现 `replan`。
3. 一旦 `compile_ok=false`，直接 `final_summarize`。
4. 一旦 `step_success=false`，直接 `final_summarize`。
5. 增加启动期自检：若配置或状态出现 `replan` 路由值，视为配置错误并降级到 `final_summarize`。

## 9. 状态字段调整

在 `TutorState` 中新增：

1. `compiled_plan: list[PlanStep]`
2. `compile_ok: bool`
3. `compile_errors: list[dict]`
4. `last_compile_error_code: str`

保留：

1. `plan`
2. `step_results`
3. `last_failure_reason`

移除：

1. `replan_count`
2. 与重规划相关的任何计数或签名字段

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
3. 决策枚举中不包含 `replan`。

### 11.2 集成测试

1. 文档问答正常链路。
2. 编译失败 -> `final_summarize` 收口链路。
3. 工具运行失败 -> `final_summarize` 收口链路。
4. 成功计划多步执行链路（`next_step` 循环到结束）。

### 11.3 验收指标

1. 白名单范围内 `compile pass rate >= 95%`。
2. 失败可解释性 `100%`（有错误码和失败节点）。
3. `replan invocations = 0`。
4. 任意失败都在单轮内收口，不出现循环等待。

## 12. 风险与缓解

1. 风险：零 replan 会降低坏计划的恢复机会。
- 缓解：提高 planner 输入约束质量（能力白名单、必填参数、模板兜底）并强化编译器提示。

2. 风险：失败直接收口可能影响一次性成功率。
- 缓解：在最终总结中输出明确失败边界与可执行下一步建议，便于用户快速重试。

3. 风险：错误码粒度不足影响可观测性。
- 缓解：先最小集上线，再按日志扩展。

## 13. 实施顺序（建议）

1. 定义 `available_capabilities` 数据结构并注入 planner。
2. 实现 `compile_plan` 节点与错误码。
3. 切换 execute 使用 `compiled_plan`，并内聚决策为 `next_step | final_summarize | end`。
4. 删除 `replan` 相关节点、路由与状态字段。
5. 增加测试与指标埋点。

