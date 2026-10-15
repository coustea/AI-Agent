# coustea Harness 架构设计

> 日期：2026-10-15｜状态：**设计草案，待用户审核**。审核通过前不修改任何业务代码。
> 参考实现：`/Users/apple/Code/Python/learn-claude-code`（重点 s01、s03、s04、s15）。
> 关联文档：`OPTIMIZATION_PLAN.md`（P1–P5 问题清单）、`P2_BASH_HARDENING.md`（P2 权限接缝，已实施）。

---

## 0. 本文档要回答的问题

用户提出：**「整个系统我想学习 learn-claude-code 采用 Harness 来设计 Agent。」**

因此本文档不是"再加一个功能"，而是**一次结构性重定向**：把 coustea 从「一个内部塞满机制的 Agent」重构为「一个循环 + 一圈可插拔接缝的 Harness」。

本文档只做设计与影响面分析，**不改任何业务代码**。等审核通过后按阶段实施，每阶段验收后暂停。

---

## 1. 参考实现：learn-claude-code 的 Harness 是什么

### 1.1 核心命题

来自 `README-zh.md`：

```
Harness = Tools + Knowledge + Observation + Action Interfaces + Permissions

    Tools:        文件读写、Shell、网络、数据库、浏览器
    Knowledge:    产品文档、领域资料、API 规范、风格指南
    Observation:  git diff、错误日志、浏览器状态、传感器数据
    Action:       CLI 命令、API 调用、UI 交互
    Permissions:  沙箱隔离、审批流程、信任边界
```

三句原文，直接决定本设计的取舍：

1. **「Agency 来自模型训练，不是来自外部代码的编排。」**
2. **「模型是驾驶者，harness 是载具。本仓库教你造载具。」**
3. **「它没有试图成为 agent 本身。它没有强加僵化的工作流。它给模型提供了工具、知识、上下文管理和权限边界 —— 然后让开了。」**

推论：**代码里不该出现"替模型做决策"的逻辑**。编排越少越好，接缝越多越好。

### 1.2 结构实证（s15 `agent_loop`，`code.py:3137-3259`）

```text
用户输入 / cron / 后台通知 / 团队事件        ← 多个事件源喂同一个循环
  → UserPromptSubmit hooks
  → prepare_context(messages)               ← 上下文管线：预算→裁剪→微压缩→摘要
  → update_context() + assemble_system_prompt(context)   ← 每轮重算系统提示词
  → assemble_tool_pool()                    ← 每轮重算工具池（内置 + MCP）
  → call_llm(...)  [with_retry 包装]         ← 429/529 退避、max_tokens 升级
  → 响应里有 tool_use 吗？
      否 → Stop hooks → 结束本轮
      是 → PreToolUse hooks（权限在此）
          → handler 分发
          → PostToolUse hooks
          → tool_result 追加回 messages
          → 下一轮
```

三个必须记住的事实：

- **循环的终止条件只有一个**：响应里没有 `tool_use`。**不是步数计数**（`docs/zh/s01`：「一个退出条件控制整个流程」）。
- **钩子注册表是全局的**：`HOOKS = {"UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"}` + `register_hook` / `trigger_hooks`（`code.py:1777-1790`）。
- **每轮重算三样东西**：系统提示词、工具池、上下文。

### 1.3 判定一条机制是否"挂上去"的唯一判据

> **新增一个机制时，是否需要修改循环本体？**
> 需要 → 机制被**嵌进**去了。不需要 → 机制是**挂上去**的。

这条判据贯穿本文档。

### 1.4 机制的三种挂载形态

通读 s15 后可归纳出，参考实现里所有机制都以下面三种形态之一存在，**没有第四种**：

| 形态 | 语义 | 参考实现中的例子 |
|---|---|---|
| **钩子 Hook** | 在固定点上拦截或观察，返回非空即短路 | `permission_hook`、`log_hook`、`large_output_hook`、`user_prompt_hook`、`stop_hook` |
| **装饰器 Decorator** | 包裹一个接口，增强其行为，调用方无感 | `with_retry(...)` 包住 `client.messages.create` |
| **贡献者/阶段 Contributor·Stage** | 为某个组装过程提供一段内容，或做一次变换 | `assemble_system_prompt` 的 7 个 section、`prepare_context` 的 4 段管线 |

**这是本设计最重要的抽象。** coustea 的每一个机制都必须能被归入这三类之一，且**只能通过注册接口挂载**。

---

## 2. 现状盘点：coustea 离 Harness 有多远

### 2.1 逐机制对照

| 机制 | learn-claude-code (s15) | coustea 现状 | 差距 |
|---|---|---|---|
| **循环** | 一个循环，`tool_use` 驱动终止 | `agent.CoreAgent.StreamRun` 一个循环，但终止由 `maxSteps=10` 计数主导（`agent.go:291,403`） | 循环是**封闭**的：组装→调用→执行全序列硬编码在循环体内 |
| **扩展点** | 4 个钩子事件 | 仅 1 个：`tool.PreToolUse`（P2 引入），且只覆盖工具执行 | 缺**轮次级**接缝 |
| **系统提示词** | 每轮 `assemble_system_prompt(context)`，7 段 + skills + memory + MCP + 时间 | P1 后每**用户轮次** `composeSystemPrompt(persona, workDir)`，两段硬拼（`agent.go:53-59`） | 是"两段拼接"，不是"贡献者链"；且**没有当前时间** |
| **工具池** | 每轮 `assemble_tool_pool()`（内置 + MCP，动态） | `Registry` 一次性注册，`Definitions()` 返回快照（`tool.go:67`） | 静态，无外部来源接缝 |
| **上下文** | 4 段管线：`tool_result_budget → snip_compact → micro_compact → compact_history` | `SlidingWindowMemory.BuildContext` 单段滑动窗口 + 轮次原子性（`sliding_window.go:53`） | 缺预算、缺压缩、缺摘要；大工具输出会直接吃掉窗口 |
| **错误恢复** | `with_retry`：429 退避、529 退避+fallback、`max_tokens` 升级、prompt-too-long → reactive compact | **无**。流一报错直接 `EventError` 退出整轮（`agent.go:350-353`） | 缺 |
| **事件源** | 用户输入 / cron / 后台通知 / 团队事件 | 只有用户输入（`StreamRun(ctx, prompt)`） | 缺（未来） |
| **权限** | `PreToolUse` 钩子 | **P2 已做到 ✓**（`tool/hook.go` + `tool/permission/`） | **已对齐** |
| **子 agent** | `task` 一次性 subagent（独立 messages，只回摘要） | 无 | 缺（未来） |
| **知识/技能** | `load_skill(name)` 按需加载，目录进 prompt | 无（长期记忆是唯一的知识通道） | 缺（未来） |

### 2.2 结论

P2 已经把**权限**这一个机制从循环里挪到了流水线上，方向是对的。但**其余所有机制仍然嵌在 `CoreAgent` 内部**：

- 系统提示词怎么拼 → 写死在 `composeSystemPrompt`；
- 上下文怎么裁 → 写死在 `SlidingWindowMemory.BuildContext`；
- 循环怎么停 → 写死在 `maxSteps` 计数；
- 工具池从哪来 → 写死在 `Registry` 的构造期注册。

所以准确的判断是：**coustea 现在是一个"循环里塞满机制的 Agent"，还不是"一个循环 + 一圈可插拔机制的 Harness"。** 本次设计要解决的正是这件事。

### 2.3 顺带暴露的两个建模问题

1. **`memory.Memory` 把两件事混在一起了。**
   `Append/History/Clear` 是**会话转录**，`BuildContext(ctx, systemPrompt)` 是**提示词组装 + 裁剪**。
   参考实现里这两件事是分开的：`messages` 只是一个列表，`.memory/MEMORY.md` 才是记忆。
   本仓把 system prompt 塞进记忆接口，导致记忆层反向依赖了提示词概念。

2. **`agent.go:375-399` 的工具执行内联在循环里**。
   P2 把权限挂到 `Registry.Execute` 上是对的，但循环仍然要自己处理 `execErr` 兜底、自己 append `RoleTool`。这属于"循环知道太多"。

---

## 3. 目标架构

### 3.1 一句话

把 `CoreAgent` 从「拥有并编排一切的状态机」重构为 **`Harness`**：一个只负责「驱动唯一循环 + 在固定点按序调用接缝」的载具。**所有机制都变成接缝的实现**，在装配期挂上去。

### 3.2 分层与接缝位置

```text
┌─────────────────────────────────────────────────────────────────────┐
│ cmd/coustea  装配根：读配置 → 建 gateway → 建 harness → 挂机制 → TUI  │
└─────────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────────┐
│ internal/tui   Bubble Tea 前端（只依赖窄接口 Bridge）                  │
└─────────────────────────────────────────────────────────────────────┘
                                 │  Bridge: StreamRun / Reset / SetGateway
┌─────────────────────────────────────────────────────────────────────┐
│ internal/harness  ★载具★                                             │
│                                                                     │
│   唯一循环 runTurn()  ——  终止条件：模型不再返回 tool_use              │
│                                                                     │
│     ① 轮次钩子      UserPromptSubmit ────────────────────► 接缝 A     │
│     ② 上下文管线    Stage 链（预算/裁剪/压缩/摘要）──────► 接缝 E     │
│     ③ 提示词组装    Contributor 链（身份/工作区/工具/记忆）► 接缝 C     │
│     ④ 工具池组装    ToolPool.Definitions() ──────────────► 接缝 D     │
│     ⑤ 模型调用      gateway.Gateway（可被装饰）──────────► 接缝 F     │
│     ⑥ 工具执行      ToolPool.Execute()（内含钩子）────────► 接缝 B     │
│     ⑦ 轮次收尾      Stop ────────────────────────────────► 接缝 A'    │
└─────────────────────────────────────────────────────────────────────┘
        │                        │                          │
        ▼                        ▼                          ▼
   gateway（协议/厂商）   tool.Registry（工具+执行钩子）   memory（长期记忆）
```

**关键性质**：循环体只做「按序调用接缝 + 转发事件」。它不认识权限、不认识压缩、不认识恢复、不认识 MCP。**加任何机制都不需要碰它。**

### 3.3 唯一循环（Go 伪代码）

```go
func (h *Harness) runTurn(ctx context.Context, prompt string, out chan<- Event) {
    // ── 接缝 A：轮次开始 ──
    h.turnHooks.TriggerUserPromptSubmit(ctx, prompt)

    h.session.Append(gateway.Message{Role: gateway.RoleUser, Content: prompt})

    for step := 0; ; step++ {
        if step >= h.maxSteps {                       // 安全护栏，非主终止条件
            emit(out, Event{Type: EventError, Err: ErrMaxSteps, Done: true})
            return
        }

        msgs := h.pipeline.Build(ctx, h.session.Snapshot())  // ── 接缝 E ──
        sys := h.prompt.Build(ctx, h.state())                // ── 接缝 C ──
        defs := h.pool.Definitions(ctx)                      // ── 接缝 D ──

        resp, err := h.callModel(ctx, msgs, sys, defs, out)  // ── 接缝 F ──
        if err != nil {
            emit(out, Event{Type: EventError, Err: err, Done: true})
            return
        }

        h.session.Append(assistantMessage(resp))

        // ── 主终止条件：模型不再调用工具 ──
        if len(resp.ToolCalls) == 0 {
            h.turnHooks.TriggerStop(ctx, h.session.Snapshot())  // ── 接缝 A' ──
            emit(out, Event{Type: EventDone, Usage: &resp.Usage, Done: true})
            return
        }

        for _, tc := range resp.ToolCalls {
            emit(out, Event{Type: EventToolCallStart, ToolCall: &tc})
            res := h.pool.Execute(ctx, tc)          // ── 接缝 B：内含 Pre/Post 钩子 ──
            emit(out, Event{Type: EventToolCallResult, ToolResult: &res})
            h.session.Append(toolMessage(res))
        }
    }
}
```

与 `agent.go:291-401` 的差异，逐条：

| 项 | 现状 | 目标 |
|---|---|---|
| 终止 | `maxSteps` 计数耗尽 → 报错 | 无 tool_use → 正常结束；`maxSteps` 降级为护栏 |
| 系统提示词 | 轮次开始时算一次，两段硬拼 | **每 step** 由 Contributor 链产出（等价性见 §5.1） |
| 上下文 | `memory.BuildContext(ctx, sysPrompt)` | `pipeline.Build(ctx, snapshot)`，system 由循环单独传给 gateway |
| 工具池 | `a.tools.Definitions()` 直接调 | `h.pool.Definitions(ctx)`，pool 是接口 |
| 模型调用 | 直接 `gw.ChatStream`，错误即失败 | `h.callModel`，gateway 可被恢复装饰器包裹 |
| 工具错误兜底 | 循环里 6 行 `if execErr != nil && ...` | 由 `pool.Execute` 保证 `ToolResult.Content` 非空，循环只转发 |

### 3.4 包结构（提议）

```text
internal/
  harness/                ★ 载具（原 internal/agent 重构而来）
    harness.go            Harness 类型、Option、NewHarness（装配）
    loop.go               runTurn：唯一循环
    event.go              Event / EventType（原 agent.AgentEvent）
    session.go            Session：会话转录（Append / Snapshot / Clear）
    prompt.go             Contributor 链 + Build()
    context.go            Stage 链 + Build()
    hook.go               UserPromptSubmit / Stop 注册表
  tool/                   工具层
    tool.go               Tool 接口 + Registry（+ ToolPool 接口在 harness 侧定义）
    hook.go               PreToolUse / PostToolUse
    validator.go
    builtin/              bash / read_file / write_file / edit_file / glob
    permission/           权限策略（PreToolUse 的一个实现，P2 已交付）
  gateway/                协议与厂商（+ 未来 recovery 装饰器）
  memory/                 长期记忆（Bundle / LoadBundle / InitTemplates / 目录）
  config/
  tui/
```

三处**结构性删除**（按项目约定不留兼容层）：

- `internal/agent` 包整体消失，内容迁入 `internal/harness`。**代码库里不再有名为 "agent" 的包** —— 因为按参考实现的立场，我们造的是载具，不是 agent。
- `memory.Memory` 接口与 `SlidingWindowMemory` 消失：转录归 `harness.Session`，裁剪归 `harness.Pipeline` 的第一段。
- `memory` 包瘦身为纯长期记忆（文件读取与播种）。

---

## 4. 接缝设计（逐个）

### 接缝 A：轮次钩子（UserPromptSubmit / Stop）

```go
type UserPromptSubmit func(ctx context.Context, prompt string) error
type Stop             func(ctx context.Context, messages []gateway.Message) error
```

**当前消费者**：无。**建议：本阶段不建。**

理由：项目约定明确反对留死代码（P2 阶段已因此否决 `PostToolUse`）。这个接缝的真实消费者要等到「cron 注入 / 后台通知 / 记忆抽取」出现。**先记录在案，等机制出现时再建**——这正是"机制挂上去"的含义：接缝与消费者同时诞生。

### 接缝 B：工具执行钩子（PreToolUse / PostToolUse）

`PreToolUse` 已存在（P2，`tool/hook.go` + `tool.Registry.Execute`），**保持不动**。

`PostToolUse` 目前无消费者。但**在 H2 阶段会出现真实消费者**：大工具输出落盘（见接缝 E 的 `toolResultBudget`）。届时再加：

```go
type PostToolUse func(ctx context.Context, call gateway.ToolCall, res gateway.ToolResult) error
```

**建议：本阶段不建，H2 与消费者一起建。**

### 接缝 C：系统提示词贡献者链 ★本阶段核心

现状（`agent.go:53-59`）：两段硬拼。

```go
func composeSystemPrompt(persona, workDir string) string {
    memoryBlock := memory.LoadBundle(workDir).FormatForPrompt()
    if memoryBlock == "" { return persona }
    return persona + "\n\n" + memoryBlock
}
```

目标：

```go
// Contributor 产出一段系统提示词内容；返回空串表示不贡献。
type Contributor func(ctx context.Context, s *State) string

type PromptBuilder struct{ contributors []Contributor }

func (b *PromptBuilder) Use(c Contributor) { ... }

func (b *PromptBuilder) Build(ctx context.Context, s *State) string {
    var sections []string
    for _, c := range b.contributors {
        if sec := strings.TrimSpace(c(ctx, s)); sec != "" {
            sections = append(sections, sec)
        }
    }
    return strings.Join(sections, "\n\n")
}
```

内置贡献者（对应现状）：

| 贡献者 | 产出 | 对应现状 |
|---|---|---|
| `identityContributor` | 身份 + 准则 | `defaultPersona` 前半 |
| `workspaceContributor` | `Working Directory: ...` | `defaultPersona` 中段 |
| `toolsContributor` | 可用工具清单 | **新增**（现状靠准则里手写工具名，会与注册表脱节） |
| `timeContributor` | `Current time: ...` | **新增**（s15 有；现状模型不知道今天几号，日程/相对时间类任务是硬伤） |
| `memoryContributor` | `memory.LoadBundle(workDir).FormatForPrompt()` | `composeSystemPrompt` 第二段 |

装配期（`NewHarness`）：

```go
h.prompt.Use(identityContributor(persona))
h.prompt.Use(workspaceContributor(workDir))
h.prompt.Use(toolsContributor(h.pool))
h.prompt.Use(timeContributor(clock))
h.prompt.Use(memoryContributor(workDir))
```

**收益**：未来 skills、MCP 状态、队友列表各自加一个 `Use(...)` 即可，`composeSystemPrompt` 不用改，循环更不用改。

**顺带修正 P1 的一个遗留**：`WithSystemPrompt` 现在覆盖 persona 但记忆仍追加。改成 Contributor 链后语义更干净——自定义 persona 就是替换 `identityContributor`，其余贡献者照旧。

### 接缝 D：工具池组装（ToolPool）

现状：`agent` 直接持有 `*tool.Registry` 并调 `Definitions()`。

目标：`harness` 侧定义**消费方接口**（Go 惯用的依赖倒置）：

```go
// ToolPool 是 harness 对"工具来源"的最小要求。
// *tool.Registry 天然满足；未来 MCP / 技能池可用聚合器实现。
type ToolPool interface {
    Definitions(ctx context.Context) []gateway.ToolDefinition
    Execute(ctx context.Context, call gateway.ToolCall) (gateway.ToolResult, error)
}
```

**关键**：`*tool.Registry` 已经满足这个接口，**无需改动任何现有代码**。改变的只是 harness 依赖的是接口而不是具体类型——这样 MCP 接入时是「换一个 pool 实现」，不是「改 harness」。

**建议：本阶段建。成本约等于零，且是 MCP/技能的必经之路。**

### 接缝 E：上下文管线（Stage 链）★本阶段核心

现状（`sliding_window.go:53-103`）：单段滑动窗口（`maxMessages=40`）+ 轮次原子性回溯。

目标：`Stage` 链，逐段变换消息序列。

```go
type Stage func(ctx context.Context, msgs []gateway.Message) []gateway.Message

type Pipeline struct{ stages []Stage }

func (p *Pipeline) Use(s Stage) { ... }

func (p *Pipeline) Build(ctx context.Context, msgs []gateway.Message) []gateway.Message {
    for _, s := range p.stages { msgs = s(ctx, msgs) }
    return msgs
}
```

对照 s15 的 `prepare_context`，四个阶段：

| 阶段 | 作用 | 本仓对应 |
|---|---|---|
| `turnAtomicWindow` | 消息数超限时裁剪，保证 `User→Assistant(ToolCalls)→Tool` 同生共死 | **现有逻辑原样迁移**（`sliding_window.go` 的回溯段） |
| `toolResultBudget` | 单条工具结果超阈值 → 落盘 + 只留预览与路径 | **新增**。现状一次 `read_file` 大输出即可吃掉整个窗口 |
| `microCompact` | 超 token 预算时，把较早的工具结果替换为"已归档，路径=…"的恢复指针，最近 K 条保持完整 | **新增** |
| `summarize` | 仍超限时，调模型把中段历史摘要化，保留首尾 | **新增**，需要 `gateway.Gateway` 注入 |

**必须保持的不变量**：轮次原子性（Turn Atomicity）在**每一段之后**都成立。这是本仓的既有资产（P1 时确认过：孤立 `RoleTool` 会让 OpenAI 兼容端点返回 400），管线化后必须用测试锁住。

**建议：H1 只做"把滑动窗口重构为 Stage 链的第一段"（行为等价）；H2 再加后三段。**

### 接缝 F：模型调用恢复（Decorator）

现状：`gw.ChatStream` 一旦返回错误 chunk，整轮失败。

目标：**装饰器**，而不是循环里的一段 `if`：

```go
// gateway 侧（或 harness/gateway 之间的 recovery 包）
type recoveryGateway struct {
    inner gateway.Gateway
    policy RetryPolicy
}

func (g *recoveryGateway) ChatStream(ctx context.Context, req *gateway.ChatRequest) (<-chan gateway.StreamChunk, error) {
    // 429 / 5xx → 指数退避重试
    // prompt too long → 触发 pipeline 的 summarize 段后重试
    // 流中途中断 → 仅在"尚未产出任何内容"时重试，否则保持流式回滚原则
}
```

装配期：

```go
gw = recovery.Wrap(gw, recovery.DefaultPolicy())   // 机制挂上去，循环不知道
h := harness.New(gw, ...)
```

**前置条件**：`gateway` 需要能区分错误种类。当前错误全是 `fmt.Errorf` 字符串，无法可靠分类。**需要先给 gateway 增加一个轻量的错误类型**（携带 HTTP 状态码 / 可重试标记）。

**建议：H3。** 涉及 gateway 改动，独立验收。

---

## 5. 关键设计决策

### 5.1 系统提示词：每 step 还是每 turn？

s15 是**每 step**（`call_llm` 内部调 `assemble_system_prompt`）。P1 拍板的是**每用户轮次**（选项 a），理由是"本轮内工具写入的记忆在下一轮生效"。

两者不冲突：**把"记忆贡献者的读取时机"与"提示词组装时机"解耦即可。**

- 组装：每 step（Harness 的语义要求，且成本只是一次字符串拼接）。
- 记忆读取：**每轮次缓存一次**（保持 P1 的行为契约：本轮写入的记忆下一轮可见，而不是本 step 可见）。

实现：`State` 在轮次开始时冻结一份 `memorySnapshot`，`memoryContributor` 读它。这样既是"每 step 组装"，又**不破坏 P1 已验收的行为**。

> **需你确认**：是否接受"每 step 组装、但记忆快照每轮次冻结"？若你希望本轮工具写入的记忆**当轮即生效**，把快照改为每 step 重读即可（代价：每 step 一次磁盘 IO）。

### 5.2 终止条件：`tool_use` 驱动 + 安全护栏

现状：`maxSteps=10`，耗尽即 `ErrMaxSteps`。真实后果是复杂任务（多轮读改文件）会**中途硬失败**。

目标：主终止条件是"模型不再调用工具"；`maxSteps` 保留为护栏，默认值上调（建议 **50**）。

> **需你确认**：护栏默认值取多少？（10 / 30 / 50 / 无上限）

### 5.3 会话与长期记忆的职责切分

| 概念 | 归属 | 内容 |
|---|---|---|
| **会话转录 Session** | `harness.Session` | 本次进程的消息列表（Append / Snapshot / Clear） |
| **上下文管线 Pipeline** | `harness.Pipeline` | 从转录到请求消息序列的变换（裁剪/压缩/摘要） |
| **系统提示词 PromptBuilder** | `harness.PromptBuilder` | Contributor 链 |
| **长期记忆 Long-term memory** | `memory` 包 | `~/.coustea/memory` 与 `<workdir>/.coustea/memory` 的 Markdown 文件 |

现状把前两项塞进 `memory.Memory` 接口，导致记忆层反向依赖 `systemPrompt` 概念。切分后 `memory` 包只做文件，职责单一。

### 5.4 钩子的类型化（Go vs Python）

s15 用 `trigger_hooks(event, *args)` 一个函数吃所有事件——因为 Python 是动态类型。**Go 不应照抄**：`*args` 会退化成 `...any`，丢失全部类型安全。

本设计采用**每事件一个具名函数类型**（`PreToolUse`、`PostToolUse`、`UserPromptSubmit`、`Stop`），注册表就是几个切片 + 几个 `Use*` 方法。语义与参考实现等价，但编译期可查。

### 5.5 并发与锁

沿用既定偏好：**本地单用户，不为并发请求设计协调**。

保留 `running` 单轮互斥（防止 TUI 重复触发），去掉不必要的细粒度锁。钩子/贡献者/阶段在装配期注册、运行期只读，无需加锁。

### 5.6 明确不引入的东西

- **不做**多事件源（cron / 后台 / 团队）——H5+，等真实需求。
- **不做**子 agent（`task` 工具）——H5+。
- **不做**skills / MCP——H5+。
- **不做**worktree / 任务图 / 团队——不属于本仓定位（通用个人助手，非编码 agent 团队）。
- **不做**为旧 API 保留别名或兼容层——按既定约定，直接删。

---

## 6. 分阶段实施

每阶段**独立验收**（`gofmt` / `go build` / `go vet` / `go test ./... -count=1` / `make build` 全绿），**验收后暂停**等你确认。

### H1：骨架（纯结构，行为等价）

1. `internal/agent` → `internal/harness`；`CoreAgent` → `Harness`；`AgentEvent` → `Event`。
2. 拆 `Session`（转录）与 `Pipeline`（上下文）；`memory.Memory` 接口删除；`SlidingWindowMemory` 的裁剪逻辑迁为 `Pipeline` 第一段 `turnAtomicWindow`。
3. 引入 `PromptBuilder` + Contributor 链，内置身份/工作区/工具/时间/记忆五个贡献者。
4. 引入 `ToolPool` 接口；`harness` 依赖接口而非 `*tool.Registry`。
5. 循环改为 `tool_use` 驱动终止，`maxSteps` 降为护栏。
6. `tui.Bridge`（原 `AgentBridge`）指向 `*harness.Harness`。

**验收标准**：全部现有测试通过（含 P1 的记忆刷新测试、P2 的权限端到端测试），无新增行为。

### H2：上下文管线后三段

`toolResultBudget`（大输出落盘 + 预览）→ `microCompact`（恢复指针）→ `summarize`（模型摘要）。
同时引入 `PostToolUse` 钩子作为大输出告警的挂载点。

**验收标准**：构造超长工具输出与超长历史，断言管线把请求压回预算内、且**每一段之后轮次原子性都成立**。

### H3：恢复装饰器

给 `gateway` 增加可分类错误（HTTP 状态码 / 可重试标记），新增 `recovery.Wrap` 装饰器（429/5xx 退避、prompt-too-long → 触发摘要段后重试）。

**验收标准**：mock 网关返回 429/超长错误，断言重试与降级路径；断言"已产出内容后的流中断仍走回滚，不重复输出"。

### H4（可选）：轮次钩子

`UserPromptSubmit` / `Stop` 注册表 + 真实消费者（轮次统计、审计日志）。**仅在消费者出现时做。**

### H5+（未来）：skills / MCP / 子 agent / 多事件源

每一项都是"给已有接缝加一个实现"，**不碰循环**。这正是本次重构要买到的东西。

---

## 7. 风险与取舍

| 风险 | 说明 | 缓解 |
|---|---|---|
| **重构面大** | H1 触及 `agent`/`memory`/`tui` 三个包 | H1 严格限定为"结构等价"改造，用现有测试当回归网；不夹带任何行为变更 |
| **`maxSteps` 放开后失控** | 模型可能陷入工具循环 | 保留护栏（默认 50）+ P2 的 persona 约束句（"勿重试被拒命令"）；后续可加"同一命令重复 N 次即停" |
| **每 step 组装提示词的磁盘 IO** | `memoryContributor` 每 step 读盘 | 按 §5.1 每轮次冻结快照，实际每轮只读一次 |
| **轮次原子性在管线化后被破坏** | 孤立 `RoleTool` 会导致 400 | 管线每段后都做原子性断言，测试锁住 |
| **重命名带来的 git 噪音** | `agent`→`harness` 全仓改名 | 单独立一个提交，便于 review 与回退 |
| **`timeContributor` 破坏提示词缓存** | 每 step 时间戳变化，可能影响服务端 prompt cache | 时间精确到分钟；或放在提示词末尾（已如此设计） |

**不做的事的取舍**：本阶段**不建** `UserPromptSubmit`/`Stop`/`PostToolUse` 三个接缝，因为当前无消费者。代价是未来引入 cron/后台时需再补——但换来的是零死代码，符合既定约定。

---

## 8. 需要你拍板的问题

1. **包名**：是否接受 `internal/agent` → `internal/harness`（代码库中不再有 "agent" 包）？还是保留 `agent` 包名、只把内部结构 Harness 化？
2. **终止条件**：`maxSteps` 护栏默认值取多少（建议 50）？
3. **提示词组装时机**：接受 §5.1 的"每 step 组装 + 记忆快照每轮次冻结"吗？还是本轮工具写入的记忆当轮即生效？
4. **接缝 A/B 的建与不建**：是否同意"无消费者的接缝一律不建"（即本阶段不建 `UserPromptSubmit` / `Stop` / `PostToolUse`）？
5. **实施范围**：本次是否只做 **H1**？还是 H1+H2 一起？
6. **`memory.Memory` 接口删除**：接受吗？（`Append/History/Clear` 迁 `Session`，`BuildContext` 拆成 `Pipeline` + `PromptBuilder`）

你确认后我再动代码。**在收到你的明确答复前，我不会修改任何业务代码。**
