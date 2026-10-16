# 钩子系统引入设计与实施计划

> 状态：待评审（评审通过后按 S1 → S2 两阶段实施，各自独立验收）
> 日期：2026-10-16
> 前置核验：agent_loop / tool_use / permission 三模块均已完成且有测试锁定（见 §1）
> 关联文档：`HARNESS_ARCHITECTURE.md`（总架构与 H1–H5 阶段）、`P2_BASH_HARDENING.md`（PreToolUse 接缝来源）

## 0. 一句话

把「权限」这一步从循环体内联迁移为**装配期挂载的 PreToolUse 钩子**（修复接缝漂移），并引入 **PostToolUse 钩子**及其第一个真实消费者（大工具输出落盘 + 预览），让 coustea 从「循环里塞机制」迈出「机制挂上去」的第一步。

---

## 1. 现状核验（2026-10-16，当前工作树）

| 模块 | 状态 | 关键事实 | 测试证据 |
|---|---|---|---|
| agent_loop | ✅ 已实现 | StreamRun 单飞互斥、流式聚合（正文/思维链/工具调用/用量）、工具执行、错误即观察、maxSteps 护栏（默认 10）、RespondPermission 异步审批 | `TestCoreAgent_ReAct_ToolExecution`、`_ErrorAsObservation`、`_MaxStepsExceeded`、`_PermissionPipeline_InteractiveApproval` 等 13 例 |
| tool_use | ✅ 已实现 | Tool 接口 + Registry 管线（查找→前钩子→参数校验→执行）、PreToolUse 接缝（顺序 + 短路）、5 个内置工具 + SafePath 沙箱 | `TestRegistry_*` 6 例 + builtin 6 例 |
| permission | ✅ 已实现 | 三闸门（硬拒表 / 危险命令与越界路径规则 / 交互审批 + 会话信任）、autoApprove | `TestPermission_*` 6 例 |

`go build ./...`、`go vet ./...` 通过；上述包 `go test -count=1` 全绿。

**核验发现（本设计要解决的痛点）：**

1. **接缝漂移**：P2 与总架构文档声称「权限已挂到 PreToolUse 流水线」，但代码实际把权限裁决**内联在循环**中（`agent.go` 工具执行段约 60 行：临时换装 approver、Evaluate、组装拒绝结果）；`UsePreToolUse` 在生产代码中**零调用**（仅测试使用）。即：接缝早已建好，但没有任何机制真正「挂上去」。（旧文档写作 `internal/tool/permission`，实际为 `internal/permission`；本设计保持现路径。）
2. **PostToolUse 缺失**：工具级只有前置接缝；大输出（`read_file` 无输出上限、`bash` 上限 50k 字符）会原样灌进记忆与请求，单条即可逼近小模型的整个上下文。
3. **轮次级接缝缺失（有意）**：UserPromptSubmit / Stop 尚无真实消费者，按仓库「消费者优先」约定暂不实现（见 §6）。

**已知相邻项（本批明确不动）**：maxSteps 耗尽语义（现为 EventError）、系统提示词无当前时间、gateway 错误不可分类（H3 前置）。

> 核验环境备注：工作树含未提交的「模型看板/向导」WIP（config/agent/protocol/tui 六文件），与三模块无关；其 TUI 测试暂红（测试尚未跟上新向导流程），本批零触碰 TUI。

---

## 2. 设计原则（对齐参考实现与本仓约定）

1. **类型化事件**：每个钩子事件一个具名函数类型 + 一个注册表（切片 + `Use*` 方法），不做 `...any` 通用分发——Go 编译期可查，不照抄 Python 的动态分发。
2. **装配期挂载、运行期只读**：钩子链在 `NewAgent` 选项应用完毕后一次性挂载；运行期快照后锁外调用（沿用 P2 约定）。
3. **消费者优先**：接缝与消费者同时诞生，不为「可能用到」而预建（P2 曾据此否决 PostToolUse；本批它有了真实消费者才引入）。
4. **循环不知道机制**：判据——新增一个机制是否需要改循环本体？需要即「嵌进去」，不需要即「挂上去」。本批结束后，循环内不再出现 permission/权限字样。

---

## 3. 事件模型总览

| 事件 | 层级 | 语义 | 本批 | 消费者 |
|---|---|---|---|---|
| `PreToolUse` | 工具级 | 执行前拦截；返回 error 即短路，错误文案作为观察结果回灌 | **S1 落地**（修为挂载） | 三闸门权限 |
| `PostToolUse` | 工具级 | 执行后观察 + 改写结果（不阻断） | **S2 落地** | 大输出落盘预览 |
| `UserPromptSubmit` | 轮次级 | 轮次开始时拦截/注入 | 设计预留，不落地 | 待出现（时间注入、记忆抽取等） |
| `Stop` | 轮次级 | 自然收敛时否决退出（goal 判停） | 设计预留，不落地 | 待出现（goal、轮次审计等） |

---

## 4. S1：权限挂载修复（行为等价重构）

### 4.1 目标形态

```go
// NewAgent 装配顺序（改动后）：
a := &CoreAgent{ /* 字段初始化（不再在字面量里建 permission） */ }
a.permission = permission.NewManager(wd, permission.WithApprover(permission.ApproverFunc(a.bridgeApproval)))
for _, opt := range opts { opt(a) }
// 选项全部应用后，在最终对象上挂载内置横切机制：
a.tools.UsePreToolUse(a.permissionHook)    // S1
a.tools.UsePostToolUse(a.largeResultHook)  // S2
```

要点：

- **钩子是装配产物**：选项可能替换 registry（`WithTools`）、权限管理器（`WithPermission`）、工作目录（`WithWorkDir`），因此挂载必须发生在选项之后、最终对象上。
- `WithWorkDir` 不再重建 Manager：给 `permission.Manager` 增加 `SetWorkDir(dir)` **原地更新**工作目录。顺带修复两个既有小问题——重建会丢失 `autoApprove`、会话信任表与自定义硬拒表（当前 `WithAutoApprove(...) + WithWorkDir(...)` 的组合会把自动放行配置丢掉）。
- `WithPermission` 换成自定义 Manager 时不再自动装配审批桥（保留「无 approver 则高危拒绝」的现状语义）；需要交互审批的自定义管理器由调用方自行注入（与现状一致）。

### 4.2 事件接收器（ctx sink）——钩子如何向 TUI 发审批请求

现状：审批桥是循环临时构造的闭包，因为它需要本轮事件通道 `outCh`。钩子只有 `(ctx, call)`，因此把事件通道用 ctx 携带：

```go
// internal/agent/hook.go（新文件）
type eventSinkKey struct{}

// withEventSink 在轮次运行期 Context 上装载本轮事件接收器（供流水线钩子回传事件）。
func withEventSink(ctx context.Context, ch chan<- protocol.Event) context.Context

func eventSinkFrom(ctx context.Context) (chan<- protocol.Event, bool)
```

- 循环启动时 `ctx = withEventSink(ctx, outCh)`（单飞约束下每轮唯一通道，无并发歧义）。
- 语义与现状一致：找不到通道 → 拒绝（等效于现状「无 approver 时拒绝」）；`sendEvent` 失败（ctx 取消）→ 拒绝并回传 ctx 错误。

### 4.3 审批桥（原内联闭包整体迁移）

```go
func (a *CoreAgent) bridgeApproval(ctx context.Context, req permission.Request) (permission.Decision, error)
```

流程原样保留：生成 RequestID（`perm_N` 原子序号）→ 注册 `pendingPerms` → 发出 `EventPermissionReq` → 等待 `RespondPermission` 决策 → 映射为 permission.Decision（allow_once / allow_session / 其余拒绝）；`allow_session` 的会话信任仍由 Evaluate 记录。`RespondPermission` 与 TUI 端**零改动**。

### 4.4 前置钩子（裁决 → error 短路）

```go
func (a *CoreAgent) permissionHook(ctx context.Context, call gateway.ToolCall) error {
    allowed, reason, err := a.permission.Evaluate(ctx, call)
    if err != nil { return fmt.Errorf("permission evaluation error: %w", err) }
    if !allowed { return errors.New(reason) }
    return nil
}
```

Registry 在钩子返回 error 时构造 `ToolResult{Content: err.Error(), IsError: true}` 并透传——拒绝文案与现状逐字一致（现有测试断言 Gate1 文案原样到达、且不得被通用错误覆盖）。

### 4.5 循环瘦身

删除循环内权限分支与临时 approver 换装（约 60 行），工具执行段收敛为：

```go
res, execErr := tools.Execute(ctx, tc)   // 权限/落盘等策略已在钩子链中
if execErr != nil && strings.TrimSpace(res.Content) == "" { /* 空内容兜底 */ }
// 发 EventToolCallResult → 入史
```

### 4.6 语义等价对照（验收基线）

| 场景 | 现状 | 改后 | 结论 |
|---|---|---|---|
| Gate1 硬拒 | 拒绝文案作为 IsError 观察结果 | 同左（经钩子 error → Registry 构造） | 逐字一致 |
| Gate2/3 允许审批 | 发 EventPermissionReq，等待决策；取消/超时处理同现状 | 同左（桥从 ctx 取通道） | 事件顺序一致 |
| Gate3 用户拒绝 | `permission denied by user: ...` | 同左 | 逐字一致 |
| 无交互通道 | `no approver configured` 拒绝 | 拒绝，文案 `no interactive approval channel`（更明确） | 等价 |
| autoApprove / 自定义 approver | 生效 | 生效（autoApprove 跳过 Gate3；`WithApprover` 覆盖桥） | 一致 |

### 4.7 测试计划（S1）

- **重写** `TestCoreAgent_PermissionHook_Mounted`：直接 `ag.tools.Execute(...)`（不经循环）驱动一次 Gate1 拒绝，断言 IsError + 文案——这才真正锁住「钩子已挂载」；另保留一条端到端拒绝链路断言。
- **新增** `TestCoreAgent_PermissionBridge_NoSink_Denies`：无事件通道的 ctx 直调 Execute，风险命令被拒且文案明确。
- **新增** `TestPermission_SetWorkDir_PreservesState`：工作目录切换后越界判定按新目录生效，且会话信任 / 自动放行保留。
- **回归**：`TestCoreAgent_PermissionPipeline_InteractiveApproval`（审批全流程）与全部 Gate 测试**不改一字**通过。

---

## 5. S2：PostToolUse 与大输出落盘

### 5.1 类型与语义

```go
// PostToolUse 是工具执行后的观察/改写钩子（对应参考实现的 PostToolUse）：
// 执行已经发生，因此钩子不能「阻断」，也没有 error 返回——它只观察并按需改写结果。
// 典型用途：大结果落盘预览、审计、结果规范化。
type PostToolUse func(ctx context.Context, call gateway.ToolCall, result *gateway.ToolResult)
```

触发边界：

- **触发**：工具**实际执行后**——成功或失败（执行错误的输出同样可能巨大）；
- **不触发**：未找到工具、前置钩子短路、参数校验失败（根因：没有发生执行）。
- 多个后置钩子按挂载顺序执行；快照后锁外调用（沿用 P2 约定）。

### 5.2 Registry.Execute 管线更新

查找 → 前置钩子 → 参数校验 → 执行 → **后置钩子** → 返回。

### 5.3 第一个消费者：大输出落盘 + 预览

```go
const (
    toolResultBudgetRunes  = 8000 // 单条工具结果落盘阈值（字符）
    toolResultPreviewRunes = 2000 // 落盘后保留的预览字符数
)

func (a *CoreAgent) largeResultHook(ctx context.Context, call gateway.ToolCall, res *gateway.ToolResult)
```

行为：

1. `res.Content` 字符数 ≤ 阈值 → 原样返回；
2. 超过 → 全量写入 `<workDir>/.coustea/tool-results/<callID>.txt`（文件名净化；冲突追加序号；文件权限 0600，目录沿用 0755 约定）；
3. 写入成功 → `res.Content = 预览(前 2000 字符) + 标记`，标记含总量与相对路径，例如：
   `... [output truncated: 25134 characters total; full content saved to .coustea/tool-results/call_1.txt — use read_file to view]`
4. 写入失败 → **降级为原文不动**（宁可占上下文，不丢输出）。

为什么选这个消费者：

- 直面真问题：`read_file` 无输出上限、`bash` 上限 50k 字符，单条大输出即可逼近小模型整个上下文；
- 与总架构文档 H2 的 `toolResultBudget` 目标一致——本批**前移**该能力到 PostToolUse（写时一次落盘）；H2 剩余的三段（turnAtomicWindow 之后 microCompact / summarize / 归档）不受影响；
- 预览 + 路径对模型是可恢复信息（read_file 可回读），对 TUI 用户可见且不丢事实。

### 5.4 测试计划（S2）

- `internal/tool/tool_test.go`：后置钩子改写结果可见于返回值；执行错误路径触发；前置拒绝 / 校验失败 / 未找到不触发；多钩子顺序；无钩子回归。
- `internal/agent/agent_test.go`：`TestCoreAgent_LargeToolResult_Persisted`——大输出经一轮 StreamRun 后：工具结果事件与记忆中的该条消息为「预览 + 标记」，磁盘文件为全量；小输出不受影响。

---

## 6. 轮次级接缝（设计预留，本批不落地）

```go
// 类型草案（与 §2 类型化约定一致）：
type UserPromptSubmit func(ctx context.Context, prompt string) error          // 非 nil 即拦截（文案回给用户）
type Stop             func(ctx context.Context, messages []gateway.Message) error // 非 nil 即否决退出（文案回灌继续）
```

- 挂载位置：agent 级注册表（未来 harness 重构后随迁），与工具级 Registry 分离。
- 落地条件（任一真实消费者出现）：时间注入 / 记忆抽取 / goal 判停 / 轮次审计。
- 与 `HARNESS_ARCHITECTURE.md` H4 的约定一致：**仅在消费者出现时做**。

---

## 7. 影响面与实施

**改动文件**

| 文件 | 改动 |
|---|---|
| `internal/tool/hook.go` | 新增 PostToolUse 类型 |
| `internal/tool/tool.go` | Registry 增加 postHooks + UsePostToolUse；Execute 尾部接入 |
| `internal/tool/tool_test.go` | 新增后置钩子用例组 |
| `internal/agent/hook.go` | **新增**：ctx sink + bridgeApproval + permissionHook + largeResultHook |
| `internal/agent/agent.go` | NewAgent 装配调整；循环删除权限分支；WithWorkDir 改用 SetWorkDir |
| `internal/agent/agent_test.go` | 重写挂载测试 + 新增桥 / 落盘用例 |
| `internal/permission/permission.go` | 新增 SetWorkDir（原地更新，保留全部内部状态） |
| `internal/permission/permission_test.go` | 新增 SetWorkDir 用例 |

**提交节奏**（沿用仓库约定：一个提交一个主题，中文主题）

1. `权限优化：权限裁决从循环内联迁移为装配期挂载的 PreToolUse 钩子`（S1）
2. `钩子扩展：引入 PostToolUse 后置钩子与大工具输出落盘预览`（S2）

**验收标准**

- `gofmt -l`（改动文件）无输出；`go build ./...`、`go vet ./...` 通过；
- `go test ./internal/agent ./internal/tool/... ./internal/permission ./internal/memory ./internal/config ./internal/gateway -count=1` 全绿；
- 现有权限测试（Gate1 文案穿透 / 交互审批全流程）**不改断言**通过；
- 代码审查项：循环内不再引用 permission 与审批桥。
- 备注：TUI 包测试以其在途 WIP 收尾后为准（本批零触碰 `internal/tui`）。

---

## 8. 待确认决策点

> 沿用 P2 文档惯例：未回复则一律采用推荐项。

| # | 决策 | 推荐项 |
|---|---|---|
| D1 | 大输出阈值 / 预览长度 | 8000 / 2000 字符（rune），常量集中定义、便于调参 |
| D2 | 落盘位置与文件权限 | `<workDir>/.coustea/tool-results/`，文件 0600（已被 `.gitignore` 的 `.coustea/` 覆盖） |
| D3 | 轮次级接缝 | 本批仅设计预留，不落地（等真实消费者） |
| D4 | 实施时机 | TUI WIP 提交后开始（本批与 WIP 文件无交集，风险低；避免同窗口并行编辑） |
