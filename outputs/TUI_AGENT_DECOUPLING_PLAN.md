# TUI 与 Agent 解耦设计方案（v2 · 单用户本地版 · 评审稿）

> 状态：**待审核**（审核通过前不新增代码修改）。
> 基线：`git HEAD f524f1f` + 工作区未提交重构（该重构单独成一笔提交，见 Q5；本方案在其之上继续）。
> 本文替代 v1 方案（v1 按"多前端/跨进程/需并发隔离"设计，已被本次约束推翻）。

---

## 0. 约束与重写说明

已确认的系统约束：

1. **单用户本地运行**：同一时刻只有一个人、一个对话、一个前端进程。
2. **前端形态**：TUI（现状）→ 可能追加无头 CLI、桌面端；且均为 **Go 同进程内**接入（同仓 cmd / Wails / Fyne），**不存在跨进程前端需求**。
3. **无需考虑并发**：不做多会话、多窗口、请求排队。

据此推翻 v1 的三项设计，并说明理由：

| v1 设计 | v2 改判 | 理由 |
|---|---|---|
| 独立 `internal/protocol` 包 + JSON 序列化约束 | **不做**，契约留在 `agent` 包 | 同进程 Go 前端直接共享类型；序列化边界是跨进程需求的产物，本系统没有 |
| `RequestID` + pending map + 响应路由 | **不做**，单槽应答 `RespondPermission(d)` | 单用户 + 单次运行 + 工具串行 ⇒ 同一时刻至多 1 个待审批（论证见 3.3） |
| 架构测试包 + headless CLI 强制验收 | **降级**：一行 grep 即验收；CLI 列为可选步骤 | 不为"防未来"付长期维护成本 |

但以下两项**仍然要做**（它们与并发无关，是"页面与内核耦合"本身）：

1. **事件与审批纯数据化**：闭包 `Respond func(...)` 和 `Err error` 使事件无法被内核之外的任何前端复用，也难测试（证据见 1.2-① ②）。
2. **配置/生命周期职责上收内核**：TUI 目前自己读写配置文件、自行构造/热切换模型，这是最重的耦合（证据见 1.2-④）。

---

## 1. 现状取证（工作区基线）

### 1.1 已完成项（工作区未提交，`go build ./...` 与 `go test ./...` 全绿）

| 项 | 证据 |
|---|---|
| `internal/tui/bridge.go` 已删除 | `git status`：`D internal/tui/bridge.go` |
| 根目录冗余 `main.go` 已删除 | `git status`：`D main.go` |
| 已建立前端契约接口 `agent.Agent` | internal/agent/agent.go:117-127 |
| 单一装配点：仅 cmd 入口组装 | cmd/coustea/main.go:15-26 |
| TUI 已剔除 gateway/memory/permission 直接依赖 | internal/tui/chat.go:3-13（仅剩 agent） |
| 记忆统计已走内核方法而非读文件 | internal/tui/chat.go:197-202（`m.agent.MemoryCount()`） |

方向正确，但只完成了一半：接口偏胖且泄漏实现类型、权限仍是闭包、配置域仍在页面。

### 1.2 残留耦合清单（本方案要解决的）

**① 权限审批是进程内闭包（最硬的耦合点）**

- 内核把"回调函数"塞进事件：`PermissionPrompt{Respond func(permission.Decision)}`（internal/agent/agent.go:97-101）。
- 为临时获得该回调，`StreamRun` 内部**运行期动态换入/换出 approver**（agent.go:505-539，`SetApprover` → `Evaluate` → `SetApprover(nil)`），共享可变状态、无法脱离单进程使用。
- TUI 直接持有闭包并调用：字段 `pendingPrompt *agent.PermissionPrompt`（internal/tui/app.go:73）、`m.pendingPrompt.Respond(...)` 四键分支（internal/tui/chat.go:39-83）。

**② 事件携带 `error` 对象与 `Done` 标志（语义混用）**

- `AgentEvent.Err error` / `AgentEvent.Done bool`（agent.go:112-113）；错误与完成事件在 6 处手工构造（agent.go:414、427、437、475、489-493、586-590）。
- TUI 对 `error` 直接 `%v` 展示（app.go:270-281）；通道关闭时前端**伪造** `AgentEvent{Done: true}`（app.go:34-47）。

**③ 契约接口偏胖且泄漏实现类型**

`agent.Agent`（agent.go:117-127）12 个方法中包含：

- `SetGateway(gw gateway.Gateway)`、`TotalUsage() gateway.Usage`、`History() []gateway.Message` → 暴露 gateway 概念；
- `SwitchModel(cfg *config.Config) error` → 暴露 config 概念且要求前端会构造配置；
- `History/SystemPrompt/WorkDir/TotalUsage` 前端实际未用（TUI 只用 StreamRun/Reset/SwitchModel/MemoryCount，见 app.go:86、chat.go:117、152、200、model.go:133）。

**④ 前端仍拥有配置域（最重的耦合）**

- TUI 直接 `import config`（internal/tui/app.go:9、internal/tui/model.go:7）。
- `Model` 持有 `cfgPath` + `config.Config` 字段（app.go:54-55），`NewModel` 自己 `LoadConfig` 并判定"是否可用"（app.go:91-92、146-164）。
- 向导直接落盘并驱动热切换：`config.SaveConfig(m.cfgPath, &m.config)` + `m.agent.SwitchModel(&m.config)`（model.go:127-134），且**忽略切换错误**。
- 平台知识与文案硬编码在视图层：choices 列表（app.go:125-130）、平台描述与默认端点/模型拼接（model.go:174-189、204-213、226-230）。

**⑤ 未配置态靠 `nil` agent 分支**

- 入口可能注入 nil（main.go:15-23），TUI 到处判空：发送路径（chat.go:149-175）、`/clear`（chat.go:116-118）、头部统计（chat.go:199-201）。

**⑥ 测试耦合（可接受，仅列基线）**

tui_test.go 仍 `import config/gateway/permission` 构造真实 CoreAgent（tui_test.go:10-13），并通过 `m.cfgPath = test_config.json` 打补丁（tui_test.go:28-29），断言文件落盘（tui_test.go:100-106）。

### 1.3 解耦判据（验收标准引用的定义）

判定"页面与 agent 解耦完成"不看 import 了哪个包（同进程二进制里依赖本来就都在），而看：

1. **职责**：前端不读写配置文件、不构造 gateway/agent、不读记忆文件、不碰权限规则；
2. **交互面**：前端与内核之间只有 `Agent` 接口（6 方法）+ `AgentEvent` 事件流（纯数据）；
3. **可替换性**：换一个同进程前端（CLI/桌面）接入时，内核零改动；
4. **反过来说**：内核不知道前端是谁（不 import 任何 UI 库）。

---

## 2. 目标架构

```
 cmd/coustea (TUI 二进制)    (未来) cmd/coustea-cli    (未来) desktop (Wails/Fyne 同进程)
         │                          │                        │
         ▼                          ▼                        ▼
  ┌─────────────────┐    仅依赖 Agent 接口 + AgentEvent
  │  internal/tui   │◄──────────────  （6 方法 + 一条事件流）
  └─────────────────┘
         │
         ▼  只 import：agent + bubbletea 系 UI 库
  ┌───────────────────────────────────────────────────────────────┐
  │ internal/agent —— 前端契约 + 唯一装配者 + 配置/热切换 + 记忆统计 │
  │  内部实现，前端不可见：                                        │
  │   ├── internal/gateway（4 适配器 + 前缀路由）                  │
  │   ├── internal/tool(+builtin)（注册表 + 内置工具）             │
  │   ├── internal/permission（三道闸门）                          │
  │   ├── internal/memory（滑动窗口 + 长效记忆）                   │
  │   └── internal/config（数据与持久化，0600）                    │
  └───────────────────────────────────────────────────────────────┘
```

依赖规则（可 grep 验收）：

1. `internal/tui` 不得 import `config/gateway/memory/permission/tool`——只允许 `agent`。
2. `internal/agent` 不得 import bubbletea/lipgloss/glamour（现状已满足，保持）。
3. 前端不出现任何文件 IO（配置读写、记忆读取）。

---

## 3. 契约设计（internal/agent）

### 3.1 `Agent` 接口：12 → 6 方法

```go
// Agent 前端契约：TUI、CLI、桌面端（同进程）统一通过它驱动内核。
type Agent interface {
	StreamRun(ctx context.Context, prompt string) (<-chan AgentEvent, error)
	RespondPermission(d Decision) error
	Configure(provider, apiKey, model string) error // id 为字符串，不泄漏 config.Provider
	Providers() []ProviderInfo                       // 向导数据源
	Status() Status                                  // 就绪/模型/工作区/记忆数
	Reset()
}
```

| 删除自接口 | 去向 |
|---|---|
| `SetGateway(gateway.Gateway)` | 内核内部方法（Configure 内部使用），不再对前端暴露 |
| `SwitchModel(*config.Config)` | 由 `Configure(provider, apiKey, model)` 取代 |
| `MemoryCount()` | 并入 `Status()` |
| `TotalUsage()/History()/SystemPrompt()/WorkDir()` | 前端未使用，移出契约（实现类上按测试需要保留，不再是契约面） |

### 3.2 `AgentEvent`：闭包与 error → 纯数据

```go
// PermissionRequest 待审批请求（纯数据，替代原闭包类型 PermissionPrompt）
type PermissionRequest struct {
	ToolCallID string
	ToolName   string
	Arguments  json.RawMessage
	WorkDir    string
	Reason     string
}

type AgentEvent struct {
	Type       EventType            // 类型枚举不变：text_delta/…/tool_permission_request/done/error
	Delta      string
	Reasoning  string
	ToolCall   *gateway.ToolCall
	Permission *PermissionRequest   // ← 替换 PermissionPrompt（无函数）
	ToolResult *gateway.ToolResult
	Usage      *gateway.Usage
	Message    string               // ← 替换 Err error：仅 EventError 携带的人类可读文案
}
```

- 删除 `Done bool`、`Err error`（agent.go:112-113）；重复的 6 处事件构造收敛为一个 `finish(outCh, err)` 辅助。
- **终态语义**：`EventDone`（携带 Usage）或 `EventError`（携带 Message）为终态，随后通道关闭；通道关闭 ≡ Done（TUI 保留"关闭即结束"处理，删除伪造事件逻辑）。
- 附带收益：`AgentEvent` 字段全部是带 json tag 的纯数据（gateway.go:25-60），将来若真出现跨进程桌面端（Electron），补一层 JSON 编解码即可，零重构。

### 3.3 权限应答：单槽、无 RequestID

**单槽成立的论证**（这就是"不考虑并发"的落点）：
内核本就强制单次运行（`running` 标志，agent.go:380-386）；ReAct 循环内工具串行执行（agent.go:498 的 for 循环）；单用户单前端 ⇒ 同一时刻至多 1 个待审批请求。故不需要 ID/映射/路由。

```go
// CoreAgent 内部
runCh   chan<- AgentEvent // 当前运行的事件通道（StreamRun 设置、结束时清理）
pending chan Decision      // 容量 1 的单槽应答通道

// 构建时一次性安装（删除 agent.go:505-539 的换入换出 hack）：
permMgr.SetApprover(permission.ApproverFunc(func(ctx context.Context, req permission.Request) (Decision, error) {
	// 快照 runCh；发射 EventToolPermissionRequest（携带纯数据 PermissionRequest）
	// select { <-pending | <-ctx.Done()(拒绝) | 通道失效(拒绝) }
}))

func (a *CoreAgent) RespondPermission(d Decision) error {
	if a.pending == nil { return ErrNoPendingPermission } // 迟到/重复应答
	a.pending <- d                                        // 容量 1，不会阻塞
	return nil
}
```

- 中断语义不变：`ctx.Done()` → `DecisionDeny`。
- `WithApprover`（自定义审批器）与 `WithAutoApprove`（测试/无人值守）选项保持不变；无人审批场景走 Gate 3 默认拒绝（permission.go:242-245），行为不变。

### 3.4 生命周期与配置域上收

```go
// Open 容错初始化：配置缺失/不完整时仍返回可用实例（Ready=false），
// StreamRun 此时返回 ErrNotConfigured；Configure 成功后即可对话。
func Open(opts ...Option) (*CoreAgent, error)

// Configure 选中平台 → 载入该平台已存配置 → 覆盖非空输入 →
// 先构建 gateway（失败则返回错误、不落盘不切换）→ SaveConfig(0600) → 热切换
func (a *CoreAgent) Configure(provider, apiKey, model string) error

type ProviderInfo struct {
	ID           string // llamacpp/deepseek/gemini/spark
	Description  string // 向导文案（含默认端点/模型），从 model.go:174-189 迁入
	IsLocal      bool   // 无需 Key
	DefaultModel string
	APIKey       string // 已保存 Key（本机单用户，直接回填密码框）
	ModelName    string // 已保存模型
	Configured   bool
	Active       bool
}

type Status struct {
	Ready       bool
	Provider    string
	Model       string
	WorkDir     string
	ConfigPath  string // 原 TUI cfgPath，仅用于展示"已保存至 [路径]"
	MemoryCount int
}
```

配套调整：

- `NewAgent` 放宽对 nil gateway 的限制（未配置态合法）；`ErrNilGateway` 删除（不保留兼容），新增 `ErrNotConfigured`、`ErrNoPendingPermission`。
- 新增 `WithConfigPath(path)` 选项：测试与嵌入场景指定配置文件（替代 tui_test.go:28-29 的字段打补丁）。
- 平台别名（llama/ds/google/maas…）与默认值逻辑全部留在 config/gateway 内部（config.go:94-109、355-385），前端只认 `ProviderInfo.ID`。

### 3.5 显式不做（与 v1 对比）

- 不做：RequestID/pending map/多会话隔离/序列化边界/JSON-RPC/stdio 传输层/架构测试包。
- 仅保留两处必要的同步原语：`running` 互斥（已有）与 `pending` 单槽（跨 goroutine 交接：事件泵一轮在独立 goroutine，TUI 在自身事件循环应答）。

---

## 4. TUI 改造清单

**删除**：

| 删除项 | 位置 |
|---|---|
| `import config`（全部） | app.go:9、model.go:7 |
| `cfgPath`、`config.Config` 字段 | app.go:54-55 |
| `NewModel` 中的 LoadConfig/可用性判定 | app.go:91-92、146-164 |
| 硬编码 choices 与平台文案 switch | app.go:125-130、model.go:174-189、204-213、226-230 |
| `m.agent == nil` 全部分支 | chat.go:116-118、149-175、199-201 |
| 通道关闭伪造 Done 事件 | app.go:34-47（改为"关闭=终态"） |
| `pendingPrompt` 闭包调用 | app.go:73、chat.go:39-83 |

**改造**：

- 向导：`Providers()` 渲染列表（已配置标记、描述文案）→ Key 输入（回填 `ProviderInfo.APIKey`；`IsLocal` 直接 Enter）→ 模型输入（默认 `ModelName`/`DefaultModel`）→ `agent.Configure(id, key, model)`；**失败展示错误并留在向导页**（修复现状静默失败，model.go:133）。
- 权限卡片：`*agent.PermissionRequest` 字段渲染不变；y/a/n/Esc → `m.agent.RespondPermission(...)`。
- 头部/初始消息：模型信息、工作目录、记忆数、配置路径全部改读 `Status()`（chat.go:185-212 的 `m.config` 引用删除）。
- 事件处理：`EventError` 用 `Message`（app.go:270-281）；`EventDone` 处理和现在一致。

**入口**（cmd/coustea/main.go 15-26 简化为）：

```go
ag, _ := agent.Open() // 永不返回 nil（容错），未配置也可用
m := tui.NewModel(ag)
```

---

## 5. 影响面与行为变化

| 文件 | 改动 |
|---|---|
| internal/agent/agent.go（603 行） | 事件结构、审批桥、Open/Configure/Providers/Status、接口裁剪、错误收敛（核心文件） |
| internal/tui/{app,chat,model}.go | 按第 4 节删改，净减代码 |
| cmd/coustea/main.go | 简化为两行装配 |
| internal/tui/tui_test.go（612 行） | 测试改用 `agent.Open(agent.WithConfigPath(...))`，断言 Configure 落盘；事件用例改纯数据构造 |
| internal/agent/agent_test.go | 小幅适配（SetGateway/History/SystemPrompt 等实现方法保留） |
| outputs/、README.md、AGENTS.md | 文档同步（结构表述、文档表加本文件；随实施步骤 3） |

**行为变化（需确认，见 Q4）**：
1. 向导保存改为"先构建后落盘"：无效平台配置不再静默落盘（原 model.go:129-134 先写文件、忽略切换错误）。
2. 冲突场景提示更明确：未配置态任意提问 → 明确提示"未配置可用模型"，与现文案一致但来自 `ErrNotConfigured`。
3. 无其他 UI 变化（视觉、键位、审批三键语义全部不变）。

---

## 6. 实施步骤（每步可编译、可测试、可提交）

| 步骤 | 内容 | 建议提交（中文风格） | 验证 |
|---|---|---|---|
| 0 | 将工作区现有未提交重构落账（bridge/根 main 已删、接口已建、测试全绿） | `架构重构：删除桥接层与冗余入口，建立Agent前端契约接口` | `go build ./... && go test ./...` |
| 1 | 事件纯数据化 + 权限应答方法化：删 `PermissionPrompt`/`Done`/`Err`，加 `PermissionRequest`/`Message`/`RespondPermission`/单槽/常驻 approver；TUI 与测试同步适配 | `架构解耦：事件协议去闭包化与权限审批应答方法化` | 同上 + TUI 审批手工冒烟 |
| 2 | 生命周期与配置上收：`Open/Configure/Providers/Status/WithConfigPath`、入口简化、TUI 向导与判空改造、接口裁剪至 6 方法 | `架构解耦：配置职责上收内核并将前端契约瘦身为六方法` | 同上 + 未配置全流程冒烟 |
| 3（可选） | `cmd/coustea-cli` 无头前端（stdin 一轮问答，审批事件一律回 `DecisionDeny` 并打印），验证"换前端零内核改动"；文档同步 | `架构解耦：新增无头CLI前端验证内核可复用性` | CLI 跑通普通问答 + 高危命令被拒 |

---

## 7. 验收标准

1. **依赖**：`rg "my-agent/internal/(config|gateway|memory|permission|tool)" internal/tui --glob '!*_test.go'` 零命中（当前剩 config 两处）。
2. **职责**：`internal/tui` 无任何 `os.ReadFile/os.WriteFile/config.Save/Load` 调用。
3. **契约面**：TUI 对内核的调用仅为 `Agent` 接口 6 方法 + `AgentEvent` 字段访问。
4. **行为无回归**（手工冒烟）：流式输出、工具卡片、`y/a/n/Esc` 审批、`Ctrl+C/Esc` 中断、`/model` 向导、`/clear`、Markdown 渲染。
5. **未配置全流程**：新机器启动（无配置/无环境变量）→ 提问得到明确未配置提示 → `/model` 三步向导完成 → 立即可对话，无需重启。
6. **切换平台复用**：`/model` 切回已配置过的平台，自动回填已存 Key 与模型名（保持现状体验，model.go:50-56 行为）。
7. `go build ./...`、`go test ./...` 全绿；步骤 3 时 CLI 与 TUI 共用同一 `agent.Open()` 装配，无内核改动。

---

## 8. 待裁决问题

| # | 问题 | 推荐 |
|---|---|---|
| Q1 | 契约收敛在 `agent` 包（不新增包）是否可接受？若将来跨进程桌面端（Electron/Tauri）出现，再基于纯数据事件拆 `protocol` 包 | 接受，零新包零维护 |
| Q2 | `RespondPermission` 不带 RequestID（单槽，单用户串行论证见 3.3） | 接受 |
| Q3 | 向导平台文案（平台描述/默认模型端点）从 TUI 迁入内核 `Providers()` | 接受，视图只做样式 |
| Q4 | 两处行为变化：Configure 失败不落盘；`Open()` 容错（放宽 `ErrNilGateway`） | 接受，均为改进 |
| Q5 | 工作区未提交重构先落账（步骤 0），再叠加步骤 1-3 | 接受 |
| Q6 | 步骤 3（无头 CLI）是否纳入本次范围 | 推荐纳入（20-30 行，是"可替换前端"的唯一硬验收） |
