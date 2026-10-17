# 网关去重与领域类型分层重构方案

> 状态：✅ 已实施（S1–S5 全部完成，`go build` / `go vet` / `go test` / `gofmt` 全绿）
> 日期：2026-10-17
> 关联文档：`HARNESS_ARCHITECTURE.md`（总架构）、`PURE_CONTRACT_DECOUPLING_PLAN.md`（protocol 纯数据契约）、`HOOKS_INTEGRATION.md`（Pre/PostToolUse 钩子）
> 触发来源：全量代码审查，识别出分层倒挂、provider 复制粘贴、死代码、别名映射重复四类问题。

## 0. 一句话

把寄生在 `gateway` 包里的**领域类型**下沉到独立的 `internal/model` 包（修复 memory/tool/permission 反向依赖 gateway 的倒挂），并把四个 LLM provider 的**复制粘贴实现**收敛为一个共享 `compatClient`，同时删除生产零使用的非流式 `Chat` 死代码、收敛散落五处的 provider 别名映射。

---

## 1. 现状核验（2026-10-17，当前工作树）

基线：`go version go1.26.2`；`go build ./...`、`go vet ./...`、`go test ./...` 全绿。

| 模块 | 状态 | 关键事实 | 测试证据 |
|---|---|---|---|
| gateway | ✅ 可用 | 统一 `Gateway` 接口 + `Router` 路由 + OpenAI wire（`wire.go`）；四个 provider 走同一套 SSE 解析 | `gateway_test.go`、`spark_test.go` |
| agent | ✅ 可用 | ReAct 循环、流式聚合、工具执行、错误即观察、maxSteps 护栏、异步权限审批 | `agent_test.go` 13 例 |
| tool | ✅ 可用 | `Tool` 接口 + `Registry` 管线 + Pre/Post 钩子 + 5 内置工具 | `tool_test.go` + `builtin_test.go` |
| memory | ✅ 可用 | 滑动窗口（40）+ 轮次原子性 + 长期记忆落盘 | `memory_test.go`、`storage_test.go` |
| permission | ✅ 可用 | 三闸门（硬拒/危险命令与越界规则/交互审批 + 会话信任） | `permission_test.go` |

**审查发现（本设计要解决的痛点）：**

1. **分层倒挂**：`internal/gateway` 是传输层，却定义了一堆核心领域类型 `Message / Role / ToolCall / ToolResult / ToolDefinition / Usage`（`gateway.go:14-93`）。`memory`（`memory.go:6`）、`tool`（`tool.go:9`）、`permission`（`permission.go:13`）、`agent` 全都 `import "my-agent/internal/gateway"` **只为拿这些类型**。记忆模块依赖网关是方向性错误。
2. **provider 复制粘贴**：`deepseek.go` / `gemini.go` / `spark.go` / `llamacpp.go` 四份几乎完全相同的 `constructor / endpoint / Chat / ChatStream / TotalUsage`（如 `deepseek.go:60-131` vs `gemini.go:59-130`）。真实差异仅三处：错误前缀、鉴权头、默认 URL/模型。
3. **死代码**：生产链路 agent 只调 `ChatStream`（`agent.go:458`）；`Chat` / `ChatResponse` / `parseResponse` / `wireResp`（`gateway.go:98`、`wire.go:59-70`、`wire.go:201-230`）仅在测试中调用。
4. **别名映射重复**：`switch strings.ToLower(string(p))` + 别名（`llama`/`ds`/`google`/`maas`/`xfyun`）散落五处——`config.go:98`（normalizeProviderKey）、`config.go:360-405`（DefaultModel/BaseURL/RecommendedModels）、`config.go:408-437`（DisplayName/Description）、`config.go:440-454`（InferProviderFromModel）、`router.go:153-167`（initProviderGateway）。
5. **环境变量回填重复**：`config.go:158-190`（DefaultConfig）与 `config.go:249-291`（LoadConfig）两处几乎相同的 `DEEPSEEK_API_KEY / GEMINI_API_KEY / GOOGLE_API_KEY / SPARK_API_KEY / MAAS_API_KEY` 读取。
6. **命名与细节**：`Config.ProviderConfig(p)` 方法与 `ProviderConfig` 类型同名（`config.go:115` vs `config.go:46`）；`agent.go` 内注释编号出现两个「3.」；`Registry.Execute` 返回 `(ToolResult, error)` 但错误已编码进 `ToolResult.IsError`；`readSSE` 既 `return Usage` 又把它塞进 `Done` chunk（`wire.go:239` + `wire.go:333`）。

---

## 2. 设计原则（对齐本仓约定）

1. **零兼容包袱**：抽 `model` 包时直接改 import 路径，不留 `type Message = model.Message` 之类的别名 shim；一次改成唯一正确实现。
2. **依赖单向向下**：`agent → {gateway, tool, memory, permission, model, protocol}`；`gateway → {model, config}`；`memory/tool/permission → model`；`protocol` 保持零依赖。
3. **传输与领域分离**：`gateway` 只负责「领域类型 ↔ OpenAI wire」的转换与 HTTP/SSE 传输；领域类型本身不放在 gateway。
4. **元数据表单一来源**：provider 的 id / 别名 / 默认 URL / 模型 / 展示名 / 描述 / 是否本地，收敛为一张注册表；构造器映射作为 gateway 内一张小 map。
5. **消费者优先**：只删生产零使用的死代码（非流式 `Chat`）；不为「可能用到」保留。

---

## 3. 目标架构

```
internal/
  model/        ← 新增：Message / Role / ToolCall / ToolResult / ToolDefinition / Usage
  protocol/     ← 不变：Event 等纯数据契约（零依赖，继续独立）
  gateway/      ← 只做传输：Gateway 接口 + compatClient + Router + wire + 构造器表
  agent/        ← 只做编排：ReAct 循环 + 钩子桥（依赖 model/gateway/protocol）
  tool/         ← 工具注册表 + 内置工具（依赖 model）
  memory/       ← 滑动窗口 + 长期记忆（依赖 model）
  permission/   ← 三道闸门（依赖 model）
  config/       ← 配置 + provider 元数据注册表（依赖 protocol）
```

依赖矩阵（`→` 表示 import）：

```
agent   → gateway, tool, memory, permission, model, config, protocol
gateway → model, config
tool    → model
memory  → model
permission → model
config  → protocol
protocol → （无）
```

> 决策说明：`protocol.Usage` 与 `model.Usage` **保持两份**。`protocol` 是面向前端的零依赖序列化契约（AGENTS.md 明确要求），`model` 是内部领域类型。`agent.TotalUsage` 的 `model.Usage → protocol.Usage` 转换保留，属契约边界而非重复。

---

## 4. 分阶段实施

### S1：抽取 `internal/model` 包（分层修复，行为等价重构）

**改动**：新建 `internal/model/model.go`，从 `internal/gateway/gateway.go` 平移：

- `Role` + `RoleSystem/RoleUser/RoleAssistant/RoleTool`
- `Message`、`ToolCall`、`ToolResult`、`ToolDefinition`
- `Usage` + `Add`

随后全局替换 import 与类型引用：

| 包 | 变更 |
|---|---|
| gateway | `import model`；`ChatRequest.Messages/Tools`、`StreamChunk.ToolCalls/Usage`、`ChatResponse` 引用 `model.*`；wire.go 的 `toWireMessages` 入参改为 `[]model.Message` |
| agent | `gateway.Message/Role/ToolCall` → `model.*` |
| tool | `gateway.ToolCall/ToolResult/ToolDefinition` → `model.*` |
| memory | `gateway.Message/Role` → `model.*` |
| permission | `gateway.ToolCall` → `model.*` |
| builtin | 无（不依赖 gateway） |

**验收**：`go build ./...`、`go test ./...` 全绿；`grep -R '"my-agent/internal/gateway"' internal/memory internal/tool internal/permission` 仅剩 `internal/permission` 无 gateway 引用（若后续 permission 无 gateway 依赖则应为零命中）。

### S2：抽 `compatClient` 去重四个 provider

**改动**：新建 `internal/gateway/compat.go`：

```go
type compatClient struct {
    name       string            // 错误前缀
    baseURL    string
    apiKey     string
    model      string
    httpClient *http.Client
    auth       func(*http.Request) // 鉴权头差异
    mu         sync.RWMutex
    totalUsage model.Usage
}
func (c *compatClient) ChatStream(ctx, req) (<-chan StreamChunk, error)
func (c *compatClient) TotalUsage() model.Usage
```

四个 provider 退化为内嵌 `*compatClient` 的薄壳，各自构造器只填 `name / auth / 默认值`：

```go
type DeepSeek struct{ *compatClient }
func NewDeepSeek(baseURL, apiKey, model string, client *http.Client) (*DeepSeek, error) {
    c, err := newCompat("deepseek", baseURL, apiKey, model, config.DeepSeekBaseURL, config.DefaultDeepSeekModel, client, func(r *http.Request){ r.Header.Set("Authorization", "Bearer "+apiKey) })
    ...
    return &DeepSeek{c}, nil
}
```

`Gemini` 的 `auth` 额外 `Set("x-goog-api-key", ...)`；`LlamaCpp` 的 apiKey 允许为空（`newCompat` 需加 `allowEmptyKey` 或分设构造路径）。

**验收**：`go build ./...`、`go test ./...` 全绿；四文件总行数从 ~540 降至 ~120；`Chat`/`ChatStream`/`TotalUsage` 在四个 provider 文件中不再出现重复定义。

### S3：删除非流式 `Chat` 死代码

**改动**（依赖 S2，同批文件）：
- `Gateway` 接口删 `Chat`，仅保留 `ChatStream` + `TotalUsage`。
- 删 `ChatResponse`（`gateway.go:78-83`）、`parseResponse`（`wire.go:201-230`）、`wireResp`（`wire.go:59-70`）。
- 删 `Router.Chat`；测试 `gateway_test.go` / `spark_test.go` 中调用 `.Chat` 的用例改为驱动 `ChatStream` 收集 `Done` 块断言。
- 测试 mock 中无用的 `Chat` 实现同步删减。

**验收**：`grep -rn "\.Chat("` 仅命中 `ChatStream`；`go test ./...` 全绿；`wire.go` 瘦身约 1/3。

### S4：provider 元数据注册表（单一来源）

**改动**：
- `config` 包内建一张注册表（结构体切片 + map 索引）：每项含 `ID / Aliases / DefaultBaseURL / DefaultModel / RecommendedModels / DisplayName / Description / IsLocal`。
- 改写 `config.go` 的 `normalizeProviderKey / DefaultModel / DefaultBaseURL / RecommendedModels / ProviderDisplayName / ProviderDescription / IsLocalProvider / InferProviderFromModel` 全部查表。
- `gateway/router.go` 的 `initProviderGateway` 保留为一个**构造器映射**（`id → func(...) (Gateway, error)`），但 provider 的 id 归一化调用 `config` 的注册表，不再各自写 `case "gemini","google"`。

**验收**：新增/修改厂商只需改注册表一项 + 构造器 map 一项；`go test ./...` 全绿；`config.go` 中 `switch strings.ToLower(string(p))` 数量从 5 处降为 0 处。

### S5：清理与命名（低风险）

- 抽取 `config.applyEnvFallbacks(cfg)`，`DefaultConfig` 与 `LoadConfig` 共用，删除重复的环境变量读取块。
- `Config.ProviderConfig(p)` 方法改名 `ProviderFor(p)`（避免与 `ProviderConfig` 类型混淆）。
- `agent.go` 抽出 `step()` 私有方法承载循环体，`StreamRun` 只保留装配与生命周期；修正重复注释编号。
- `Registry.Execute` 返回值收敛为 `(model.ToolResult)`，错误经 `IsError` 传递（连带更新 `tool_test.go` 与 agent 调用点）。
- `readSSE` 二选一：保留 `Done` chunk 携带 `Usage`，删除函数返回值路径。

**验收**：`go build ./...`、`go vet ./...`、`go test ./...` 全绿；`gofmt -l .` 空输出。

---

## 5. 验证

每阶段结束统一执行：

```
go build ./...
go vet ./...
go test ./...          # 或单包：go test ./internal/gateway -run TestXxx
gofmt -l .
```

提交按仓库约定 `主题：描述` 一条一改，S1–S5 各自独立提交。

---

## 6. 本批明确不做

- 不把 `protocol.Usage` 合并进 `model.Usage`（保留 protocol 零依赖）。
- 不改 ReAct 循环的语义（工具串行执行、maxSteps 熔断语义、流异常回滚行为）。
- 不动 TUI 层。
- 不新增 provider，仅在注册表就绪后验证「加厂商只改一处」的形态。

---

## 7. 实施记录（2026-10-17）

### S1 领域类型下沉

- 新增 `internal/model/model.go`（61 行）：`Role / Message / ToolCall / ToolResult / ToolDefinition / Usage`。
- `gateway` 改为 import `model`，wire 层只做 `model ↔ wire` 转换。
- `memory / tool / permission` 不再 import `gateway`（已验证零命中）。
- 行为等价，全量测试通过。

### S2 provider 去重

- 新增 `internal/gateway/compat.go`（118 行）：`compatClient` + `compatOptions`，承载 `ChatStream / TotalUsage` 与构造归一化。
- 四个 provider 退化为薄壳：`deepseek.go 30 / gemini.go 31 / spark.go 30 / llamacpp.go 61` 行（原合计约 545 行）。
- `LlamaCpp.CheckHealth` 保留为厂商特有方法。

### S3 删除非流式死代码

- 删除 `Gateway.Chat`、`ChatResponse`、`parseResponse`、`wireResp`、`Router.Chat`。
- 原非流式测试（llama 文本/工具调用/工具结果、gemini、router 路由、spark 文本/错误）全部改写为 `ChatStream` + `collectStream` 断言，覆盖不降。

### S4 provider 元数据注册表

- `config` 新增 `providerMeta` + `providerRegistry`（单一来源），全部别名/默认值/展示信息查表。
- `normalizeProviderKey`、7 个 `switch strings.ToLower` 全部移除。
- `gateway/router.go` 改为 `providerConstructors` 映射 + `config.ProviderID` 归一化。

### S5 清理

- 新增 `applyEnvFallbacks` + `envFallbacks` + `firstEnv`，消除 `DefaultConfig` / `LoadConfig` 的重复环境变量读取。
- `Config.ProviderConfig` 方法改名 `ProviderFor`（消除与类型同名）。
- `agent.go` 抽出 `runStep`，`StreamRun` 只保留装配、并发锁与循环生命周期；修正重复注释编号。
- `Registry.Execute` 收敛为只返回 `model.ToolResult`，错误统一由 `IsError` 表达。

### 偏差说明（readSSE）

原计划 S5 第 5 项「readSSE 二选一」经实施评估后**保留双通道**：`readSSE` 的返回值为 provider 侧的 `TotalUsage` 累积服务，`Done` chunk 的 `Usage` 为 agent 侧单轮用量服务，两者消费者不同。删除任一都将导致 `Gateway.TotalUsage` 或 `EventDone.Usage` 失效，属功能回退而非清理，故不做删减。
