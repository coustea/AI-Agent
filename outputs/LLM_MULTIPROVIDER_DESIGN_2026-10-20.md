# pkg/llm 重构设计：OpenAI 协议多厂商调用层

> **已被 `LLM_LIBRARY_REDESIGN_2026-10-21.md` 取代（对外 API 与库边界部分）。**
> 本文档的缺陷分析（P0/P1）、流终止不变量与错误模型仍然有效，保留作历史记录。

> 状态：**待审核**。本文档只描述设计，未改动任何代码（工作区已回退至 `235f0c8`）。
> 适用范围：`pkg/llm` 全量重写 + `internal/protocol`、`internal/agent`、`internal/config`、`internal/tui` 的适配点。
> 硬约束：**不保留任何旧接口、别名、兼容层**。旧符号直接删除，调用方一次性改到位。

---

## 0. 结论

`pkg/llm` 当前 5 个文件、904 行，真正的问题不是文件大小，而是**四类互不相关的职责被平铺在同一个命名空间里**：

| 职责 | 当前所在位置 |
|---|---|
| 传输策略（重试、退避、超时、HTTP 客户端） | `client.go` + `openai.go:311-330` |
| 协议编解码（OpenAI wire 结构、SSE 解析） | `openai.go` |
| 厂商元数据（别名、端点、默认模型、鉴权） | `providers.go`，且与 `internal/config` 的 `providerRegistry` **完全重复** |
| 会话状态（累计用量） | `client.go:46-48`，与 agent 的 `totalTurnUsage` 重复记账 |

最致命的是：**流的三条异常终止路径（取消、超时、上游断连）全部被伪装成"正常完成"**，上层 `loop.go` 拿到的是 `finished=true`，于是半截回答被写进记忆、TUI 显示完成。这不是风格问题，是会静默污染上下文的数据正确性缺陷。

本次重构做四件事：

1. **把"流如何终止"变成显式类型**（`StopReason` + 终块不变量），消灭 4 个 P0 缺陷。
2. **厂商差异变成一张数据表**（`Spec`），删除 `ResolveChatURL` 的字符串后缀猜测，删除 `internal/config` 的第二份元数据。
3. **`Client` 无状态化**，`protocol.LLM` 收缩为单方法，用量记账只保留 agent 一处。
4. **错误变成结构化类型**（`*APIError`），上层可按状态码分流，重试策略由错误自身决定。

---

## 1. 边界与目标

**做什么**

- 支持且仅支持 4 个厂商：`deepseek`、`spark`（讯飞星辰 MaaS）、`gemini`（OpenAI 兼容端点）、`llamacpp`（本地）。
- 统一走 OpenAI Chat Completions 协议 + SSE 流式。
- 支持 Function Calling、`reasoning_content` 深度思考链、`usage` 统计。

**不做什么（明确排除）**

- 不做自建/自定义网关（删除 `ProviderCustom`）、不做 OpenAI 官方（删除 `ProviderOpenAI`）。
- 不做 Anthropic/Gemini 原生协议适配。
- 不做请求级 `Model` 覆盖（模型只在 Client 上绑定一处）。
- 不做非流式 `Chat()` 便捷方法（当前全仓唯一调用点是它自己的测试，属死代码）。
- 不做多模态、不做 `tools` 之外的参数透传。

**配置兼容性**：`config.json` 字段名（`provider` / `base_url` / `model_name` / `api_key` / `providers`）**保持不变**，无需迁移。

---

## 2. 现状缺陷清单

### P0：会把失败伪装成成功

**P0-1 取消/超时被当成正常完成**

`openai.go:302-309` 的 `sendChunk` 在 `ctx.Done()` 时返回 `false`，`readSSE` 拿到 `false` 就 `return turnUsage`——**不发终块**。`client.go:175-186` 的 goroutine 随后 `close(out)`。`loop.go:183` 的 `for chunk := range stream` 只是正常结束，`chunk.Err` 始终为 nil，于是：

```
executeStep → 无 err → 把 replyBuilder（半截文本）Append 进 memory → 无 toolCalls → finished=true → EventDone
```

**用户 Ctrl+C 或撞上 10 分钟 `streamHardLimit` 后，界面显示"完成"，残缺的 assistant 消息永久留在会话上下文里。**

**P0-2 上游断连被当成正常完成**

`openai.go:202-209`：`if err == io.EOF { break }`，直接落到 `openai.go:292-296` 发送 `Done: true` + `Usage: &turnUsage`。服务端中途断连时既没有 `[DONE]` 也没有 `finish_reason`，代码无法区分"正常收尾"与"半路夭折"，一律按成功处理，Usage 还可能记 0。

**P0-3 非 200 响应体无上限读入内存**

`client.go:243`：`io.ReadAll(resp.Body)`。错误网关返回一个几 MB 的 HTML 错误页时，全量进内存。

**P0-4 自建 Transport 静默丢弃代理与 HTTP/2**

`client.go:23-31` 只设了 `DialContext` / `TLSHandshakeTimeout` / `ResponseHeaderTimeout`：

- `Proxy` 未设置 → 完全不读 `HTTPS_PROXY`/`HTTP_PROXY`。国内访问 Gemini 必失败，而报错是"连接超时"，排查方向完全错。
- `DialContext` 非 nil 且 `ForceAttemptHTTP2` 为 false → `net/http` 的 HTTP/2 自动升级被跳过（`Transport.onceSetNextProtoDefaults` 的判定条件），全部降级 HTTP/1.1。

### P1：结构性缺陷

**P1-1 累计用量双口径**

`Client` 持 `mu sync.RWMutex` + `totalUsage`（`client.go:46-48`），与注释「并发安全、不可变配置」自相矛盾；同时 `loop.go:73` 的 `totalTurnUsage` 又在独立累计。两套数字永远可能不一致，且 `protocol.LLM` 因此被迫要求 `TotalUsage()`，所有 mock 都得实现一个无人读取的方法。

**P1-2 端点路径靠字符串后缀猜**

`openai.go:134-143` `ResolveChatURL`：以 `/openai`、`/v1`、`/v2` 结尾就拼 `/chat/completions`，否则拼 `/v1/chat/completions`。当前 4 个默认值恰好都能猜对，但 `https://gw.example.com/openai/v1` 这类地址会被拼成 `/v1/chat/completions` 而丢掉前缀。这是"猜"而不是"声明"。

**P1-3 空配置静默变成本地厂商**

`providers.go:57-62`：`NormalizeProvider("")` → `llamacpp`。配置缺失/损坏时用户不会收到任何提示，只会在对话时报"连接 127.0.0.1:8080 失败"。

**P1-4 `ProviderCustom` 的错误提示指向错误原因**

`providers.go:78-80` 的 `DefaultBaseURL` 兜底返回 `127.0.0.1:8080`，而 `IsLocalProvider(custom)==false`，于是 `New` 报 `ErrEmptyAPIKey`。用户想接自建网关，收到的却是"API Key 不能为空"。

**P1-5 `ProbeLocalService` 会拼出 `/v1/v1/models`**

`providers.go:140`：无条件 `clean + "/v1/models"`。baseURL 已是 `.../v1` 时路径重复。且用 `http.DefaultClient`（无超时）、`ctx == nil` 时偷偷自建 2s 超时（调用方无法感知）。

**P1-6 错误无法被上层识别**

`client.go:245`：`fmt.Errorf("%s: stream status %d: %s", ...)`。上层要区分 401（密钥无效）/429（限流）/400（请求非法）只能做字符串匹配。`builder.go:164` 是全仓唯一一处结构化判断（`errors.Is(err, llm.ErrEmptyAPIKey)`），因为只有它是 sentinel。

**P1-7 重试策略过宽**

`openai.go:311-316`：除取消/超时外**一切**网络错误都可重试——包括 TLS 证书校验失败、DNS NXDOMAIN、协议错误，这些重试 100 次也不会成功，只是把错误延迟 3 次。同时不读 `Retry-After`，退避无上限、无 jitter。`maxRetries` 命名与语义不符（`client.go:198-201` 实际当 maxAttempts 用，`WithMaxRetries(3)` 等于 3 次尝试、2 次重试）。

**P1-8 解码失败被静默吞掉**

`openai.go:225-227`：`json.Unmarshal` 失败就 `continue`。厂商返回 `{"error":{...}}` 或网关返回半截 HTML 时，数据被逐行丢弃，最后因 P0-2 被当作成功。

**P1-9 末行无换行符时丢数据**

`openai.go:202`：`ReadString('\n')` 在读到末尾但无换行符时同时返回数据和 `io.EOF`，代码直接 `break`，该行内容被丢弃。

**P1-10 元数据两处维护**

`internal/config/config.go:36-95` 的 `providerRegistry` 与 `pkg/llm/providers.go` 各自维护别名（`llama`/`local`、`ds`、`google`、`maas`/`xfyun`）、默认端点、默认模型。改一处忘另一处就是线上不一致。

**P1-11 `Message.ToolResult` 是可空嵌套指针**

`types.go:43`：`ToolResult *ToolResult` 只在 `Role == tool` 时合法，但类型系统不阻止 `Role: user` + `ToolResult` 非空，也不阻止 `Role: tool` + `ToolResult: nil`。wire 编码时还要再展平一次（`openai.go:94-99`）。

---

## 3. 架构设计

### 3.1 文件划分与命名

单包 `pkg/llm`，不引入子包（叶子包无分层必要，子包只增加 import 噪音）。

划分原则：**按"变更轴"切文件，不按"行数"切**。一个文件对应一种"什么情况下才会改它"。同一变更轴上的代码放一起，跨变更轴的代码即使都在讲"chat"也要分开。

| 文件 | 内容 | 预算 | 变更轴（何时改它） |
|---|---|---|---|
| `types.go` | `Role` / `Message` / `ToolCall` / `ToolDefinition` / `ToolResult` / `Request` / `Chunk` / `Result` / `StopReason` / `Usage` | ~110 | 领域模型变化：加字段、加终止原因 |
| `provider.go` | `Provider` 常量、`AuthKind`、`Spec` 表、`Lookup`/`ParseProvider`/`InferProvider`、`Endpoint`、`Probe` | ~160 | 加厂商、改端点/默认模型/别名 |
| `protocol.go` | wire 结构体、`encodeRequest`、`decodeChunk`（**纯函数，无 ctx、无 channel**） | ~190 | OpenAI 协议字段变化 |
| `stream.go` | `pump` / `readSSE` / `streamState` / `result`（**有 ctx 与 goroutine，承载 4 条不变量**） | ~200 | 流生命周期与终止判定变化 |
| `transport.go` | `newHTTPClient` / `newRequest` / `authorize` / `do` / `backoff` / `wrapFailure` | ~190 | 超时、重试、代理、鉴权注入变化 |
| `errors.go` | sentinel + `*APIError` + `Retryable()` | ~90 | 错误分类变化 |
| `llm.go` | `Client`、`Option` 族、`New`、`ChatStream`（入口，与包同名） | ~200 | 对外装配与 API 变化 |

单文件上限约 200 行（最大 220）。合计约 1140 行，比现在的 904 行多约 25%——增量全部来自新增的 `Result`/`StopReason`/`*APIError`/`Probe`，不是重复代码。

依赖方向（单向，无环）：

```
llm.go ──→ transport.go ──→ provider.go
   │             │                │
   ├──→ protocol.go               │
   ├──→ stream.go ─┘               │
   └──→ errors.go ←────────────────┘
types.go 被所有文件引用，自身零依赖（仅 encoding/json）
```

关键约束：**`protocol.go` 不认识 `http`，`stream.go` 不认识 `json`，`transport.go` 不认识 SSE**。当前 `openai.go` 里 `readSSE`（协议）与 `sleepBackoff`（传输）同居一文件、互不调用，就是这个约束被破坏的结果。

#### 3.1.1 命名规范（三条）

1. **单数、描述内容，不描述作者**：`providers.go` → `provider.go`；`openai.go`（谁定义的协议）→ `protocol.go`（里面装的是什么）。
2. **入口文件与包同名**：包 `llm` → `llm.go`，替代 `client.go`。对齐 `context.go` / `errors.go` / `http.go` 的惯例，读者找"这个包对外给什么"时第一眼就看它。`options.go` 一并并入（`Option` 只服务于 `New`，改一个选项不该跨文件）。
3. **测试文件跟随被测文件**：`llm_test.go` / `provider_test.go` / `stream_test.go`，不搞一个 357 行的 `client_test.go` 大杂烩。

#### 3.1.2 为什么 chat 与 stream 不合并进 `llm.go`

"types / llm / provider 三分"在 types 和 provider 上是对的（已采纳），但把 chat 与 stream 实现全塞进 `llm.go` 会重演当前 `openai.go` 的问题：

- **体量失衡**：`ChatStream` 入口（~40 行）+ wire 编码（~120 行）+ SSE 解析（~150 行）+ 重试退避（~60 行）+ 选项（~50 行）≈ 420 行，占全包 40%。届时 `llm.go` 就是今天的 `openai.go` 换个名字。
- **纯函数与并发代码混装**：`protocol.go` 是纯函数（字节 → 结构，可穷举单测，无副作用）；`stream.go` 持有 goroutine、ctx、channel 生命周期。两者的正确性论证方式完全不同，混在一处会让不变量审查变难。
- **不变量必须同文件**：4 条终止不变量横跨 `readSSE`（只报事实）与 `pump`（发终块）两个函数，必须能一眼核对，所以 `stream.go` 独立成文件，而不是 `llm.go` 里的一节。

若你更看重文件数量而非职责边界，可退到 3 文件版本（`types.go` + `provider.go` + `llm.go` 约 700 行），但我不推荐：那正是本次要修的病。

#### 3.1.3 `protocol.go` 到底在做什么（它不是类型转换）

先明确它**不做**什么：它不做 `Message` ↔ `wireMsg` 的机械搬运。如果真只是字段对字段，那就该把 `json` tag 直接打在领域类型上，这层代码一行都不需要写。

它存在的理由是：**领域语义与线上报文语义不是一一对应的**，中间有 4 类只有这一层能表达的规则。全部取自现有代码：

**① 三态与方向不对称（编码）** — `toWireMessages`（`openai.go:79-119`）

- `Content *string` 而非 `string`。`null` / `""` / 字段缺省在 OpenAI 协议里是三个不同的意思：assistant 消息带 `tool_calls` 且无文本时必须发 `null`，发 `""` 部分厂商直接 400；`tool` 消息的空结果必须是 `""` 而非 `null`。第 86 行那个 `if` 就是这个判定的全部内容。
- `reasoning_content` **只进不出**（第 91-92 行注释）：入站要提取给上层展示与存储，出站必须彻底剥离，否则多数厂商报 400。这是一条单向约束，只能落在编码函数里。
- `tool` 消息要摊平：领域侧是 `Message.ToolResult{ToolCallID, Name, Content}` 的嵌套结构，报文侧是 `content` + `tool_call_id` + `name` 三个平级字段。

**② 分片重组（解码）** — `readSSE` 里的 `tcMap` / `tcBuilder`（`openai.go:189-193, 253-290`）

OpenAI 流式 `tool_calls` 是**按 `index` 分片**的：同一个函数的 `name` 和 `arguments` 会被切成多段、跨多个 chunk 陆续到达。必须先累积、再按 index 排序输出，才能还原成一个完整的 `ToolCall`。`json.Unmarshal` 一行解决不了这件事——这是协议规定的传输语义。

**③ 一个结构体两个方向** — `wireToolCall.Index *int`

请求方向必须省略（客户端给 index 属于非法字段），响应方向必须解析。用指针区分"值为 0"与"没给这个字段"。

**④ 信封与空壳识别**

`wireChunk.Choices` 可能是空数组（纯 usage chunk）；`FinishReason *string` 要区分"没给"（流还没结束）与 `"stop"`（正常结束）。当前 `openai.go:225` 的 `json.Unmarshal` 失败直接 `continue`，导致厂商的 `{"error":{...}}` 信封被静默吞掉——这类判定的归属地也是这里。

**可测性**：纯函数意味着可以拿真实抓包报文做表驱动测试，不需要 `httptest.Server`、不需要 goroutine、不需要 sleep。现在要测一行 JSON 解析，得先把整个 HTTP 服务搭起来。

**变更轴**：`types.go` 被 `agent` / `memory` / `tui` 直接读，改它意味着"领域模型变了"；`protocol.go` 只有本包 3 个文件引用，改它意味着"厂商报文格式变了"。合并后，一次厂商字段适配会让所有读 `types.go` 的人先看一遍 `json` tag。

**如果一定要少一个文件**：可以并进 `types.go`（约 300 行），但不要并进 `llm.go`——后者会让"协议解析"和"goroutine 生命周期"重新同居，等于本次要修的病没修。

### 3.2 领域类型（`types.go`）

```go
type Role string

const (
	RoleSystem    Role = "system"
	RoleUser      Role = "user"
	RoleAssistant Role = "assistant"
	RoleTool      Role = "tool"
)

// Request 是一次调用的完整输入。按值传递：不可变，调用方无需判空。
type Request struct {
	Messages    []Message
	Tools       []ToolDefinition
	Temperature *float32
	MaxTokens   *int
}

// Chunk 是流上的一个元素。两类元素互斥：
//   - 增量块：Final == nil，携带 Text / Reasoning
//   - 终块：  Final != nil，且必为最后一个元素，Text/Reasoning 恒为空
type Chunk struct {
	Text      string
	Reasoning string
	Final     *Result
}

// Result 汇总一次流的最终结局。
// 不变量：Err != nil  ⟺  Stop ∉ {StopEnd, StopToolCalls}
type Result struct {
	Stop      StopReason
	Usage     Usage       // 恒有效（未收到 usage 时为零值）
	ToolCalls []ToolCall  // 仅在终块出现，按 index 升序
	Err       error
}

type StopReason string

const (
	StopEnd       StopReason = "end"        // 正常收尾：收到 [DONE] 或 finish_reason 非空
	StopToolCalls StopReason = "tool_calls" // 模型请求工具（finish_reason == "tool_calls"）
	StopLength    StopReason = "length"     // 输出触达 max_tokens，回答不完整
	StopCanceled  StopReason = "canceled"   // 调用方取消
	StopTimeout   StopReason = "timeout"    // 超过流式硬超时
	StopTruncated StopReason = "truncated"  // 上游无 [DONE] / finish_reason 即断连
	StopFailed    StopReason = "failed"     // HTTP 错误、解码失败、读错误
)
```

`StopLength` 归入"异常"（`Err != nil`），因为触达 `max_tokens` 意味着回答被硬切断：整段文本写进记忆会污染后续上下文，且工具调用参数很可能是残缺 JSON。上层应把它当作失败上报，而不是静默接受半截答案。

### 3.3 流终止不变量（`stream.go`）

这是本次重构的核心，四条不变量：

| # | 不变量 | 保证方式 |
|---|---|---|
| I1 | 终块**恰好一次**，且是通道最后一个元素 | 只有 `pump` 里的一个 `defer`/末尾调用能发终块 |
| I2 | `Result.Err != nil` ⟺ `Stop ∉ {end, tool_calls}` | `streamState.result(err)` 是唯一构造 `Result` 的地方 |
| I3 | `Usage` 恒非 nil（零值表示上游未上报） | `Result.Usage` 是值类型，不存在 nil |
| I4 | 通道关闭前 Body 必关、Context 必释放 | `pump` 的三个 `defer` 顺序固定 |

职责切分——`readSSE` **只报告事实，不决定结局**：

```go
// streamState 累积一轮流中需要跨 chunk 聚合的事实。
type streamState struct {
	usage   Usage
	tools   map[int]*toolBuilder
	sawDone bool
	finish  string
}

// readSSE 只做两件事：把增量推给 out、把事实记进 st。
// 返回非 nil error 当且仅当流异常终止（读错误 / 解码错误 / 无收尾标记的 EOF / ctx 结束）。
func readSSE(ctx context.Context, body io.Reader, out chan<- Chunk, st *streamState) error

// result 是 Result 的唯一构造点，把"事实 + 终止原因"映射为 StopReason。
func (st *streamState) result(err error) *Result
```

`pump` 是唯一的收敛点：

```go
func (c *Client) pump(ctx context.Context, cancel context.CancelFunc, body io.ReadCloser) <-chan Chunk {
	out := make(chan Chunk, 32)
	go func() {
		defer close(out)      // 最后执行
		defer cancel()
		defer body.Close()
		st := &streamState{tools: make(map[int]*toolBuilder)}
		err := readSSE(ctx, body, out, st)
		deliver(ctx, out, Chunk{Final: st.result(err)})
	}()
	return out
}
```

`readSSE` 的终止判定表：

| 情况 | 返回 | `st.result` 映射 |
|---|---|---|
| 收到 `data: [DONE]` | nil | `sawDone` → `StopEnd`（若 `finish=="tool_calls"` 则 `StopToolCalls`） |
| 收到 `finish_reason: "length"` | nil | `StopLength` + `ErrLength` |
| 收到 `finish_reason: "tool_calls"` | nil | `StopToolCalls` |
| EOF 且 `!sawDone && finish == ""` | `ErrStreamTruncated` | `StopTruncated` |
| `ctx.Err() == DeadlineExceeded` | `ctx.Err()` | `StopTimeout` |
| `ctx.Err() == Canceled` | `ctx.Err()` | `StopCanceled` |
| 其他读错误 / JSON 解码失败 / `{"error":...}` 信封 | 包装后的 error | `StopFailed`（或 `*APIError`） |

三个实现细节：

1. **末行无换行符**：`ReadString('\n')` 返回 `(data, io.EOF)` 时，**先处理 data，再判 EOF**，修掉 P1-9。
2. **解码失败不再 `continue`**：单行 JSON 解析失败即 `StopFailed`，错误信息里带上该行前 200 字节。SSE 注释行（`:` 开头）与空行在此之前已被过滤，不会误伤。厂商的 `{"error":{...}}` 信封解析为 `*APIError`。
3. **终块投递**：`deliver` 用 `select { case out <- chunk: case <-ctx.Done(): case <-time.After(terminalGrace): }`。正常路径（消费者还在读）立即投递；消费者已放弃且 ctx 已结束时直接丢弃——此时无人读取，不变量对观察者无意义，但 goroutine 不会泄漏。**契约**：消费者必须读完通道，或在放弃时取消 ctx（agent 的 ctx 就是轮次 ctx，天然满足）。

### 3.4 厂商规格表（`provider.go`）

厂商差异全部收敛为一张表，**端点路径显式声明**，`ResolveChatURL` 删除：

```go
type Provider string

const (
	ProviderDeepSeek Provider = "deepseek"
	ProviderSpark    Provider = "spark"
	ProviderGemini   Provider = "gemini"
	ProviderLlamaCpp Provider = "llamacpp"
)

type AuthKind int

const (
	AuthBearer AuthKind = iota // Authorization: Bearer <key>
	AuthGoogle                 // x-goog-api-key: <key>
	AuthNone                   // 本地服务，不注入
)

type Spec struct {
	ID          Provider
	Aliases     []string          // 用户输入别名
	DisplayName string
	Description string
	BaseURL     string            // 根地址（不含 chat 路径）
	ChatPath    string            // 相对根地址的 chat completions 路径
	ProbePath   string            // 健康探测路径（空表示不支持探测）
	Models      []string          // 推荐模型，[0] 为默认
	ModelAliases map[string]string // 模型名笔误修正
	Local       bool              // 无需 API Key
	Auth        AuthKind
	EnvKeys     []string          // 环境变量密钥来源，按优先级
	ModelPrefixes []string        // 模型名 → 厂商反推
}
```

规格表（**取值与当前代码完全一致，行为不变**）：

| ID | BaseURL | ChatPath | 默认模型 | Auth | Local | 别名 |
|---|---|---|---|---|---|---|
| `deepseek` | `https://api.deepseek.com` | `/v1/chat/completions` | `deepseek-flash` ⚠ | Bearer | 否 | `ds` |
| `gemini` | `https://generativelanguage.googleapis.com/v1beta/openai` | `/chat/completions` | `gemini-2.5-flash` | Google | 否 | `google` |
| `spark` | `https://maas-api.cn-huabei-1.xf-yun.com/v2` | `/chat/completions` | `spark-x2.5-4b` | Bearer | 否 | `maas`、`xfyun` |
| `llamacpp` | `http://127.0.0.1:8080` | `/v1/chat/completions` | `local-model` | None | 是 | `llama`、`local` |

⚠ 见第 8 节待确认项 1。

对外 API：

```go
func Specs() []Spec                          // 按展示顺序，供 config/TUI 遍历
func Lookup(p Provider) (Spec, bool)         // 精确 ID 查询
func ParseProvider(s string) (Provider, bool) // 含别名、大小写、空白归一
func InferProvider(model string) (Provider, bool)

// endpoint 拼接：唯一的 URL 生成逻辑，无后缀猜测。
func (s Spec) Endpoint(baseURL string) string {
	base := strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if base == "" {
		base = s.BaseURL
	}
	return base + s.ChatPath
}
```

**行为变化**：`New("")` 与 `New("custom")` 一律返回 `ErrUnknownProvider`，不再静默回落 llamacpp（修 P1-3/P1-4）。默认厂商的选择权完全交给 `internal/config`（它已有明确逻辑），`pkg/llm` 不做任何猜测。

**不做 per-vendor 工厂函数**：`provider.go` 是"厂商差异的数据表 + 解析"，不是"每个厂商一个构造函数"。以下写法明确排除：

```go
// ❌ 4 个厂商 = 4 个几乎相同的函数，新增厂商要改 5 处（4 个函数 + 1 张表）
func NewDeepSeek(key string) (*Client, error)
func NewGemini(key string) (*Client, error)
func NewSpark(key string) (*Client, error)
func NewLlamaCpp() (*Client, error)

// ✅ 一张表 + 一个入口，新增厂商只改表里一行
func New(p Provider, opts ...Option) (*Client, error)
```

厂商之间真正不同的只有 6 个字段（BaseURL / ChatPath / 默认模型 / Auth / Local / ProbePath），已经全部进 `Spec`。任何"为某厂商写专用逻辑"的冲动，都应该先检查是不是 `Spec` 少了一个字段。

**用户覆盖 BaseURL 的语义**：`WithBaseURL` 只接受**根地址**（不含 `/chat/completions`），文档写明。若用户填了完整端点，会拼成 `.../chat/completions/chat/completions` 并在 404 时给出清晰错误（`APIError` 带 URL）。这是刻意放弃的灵活性——没有自定义网关需求，就不该为它保留猜测逻辑。

### 3.5 错误模型（`errors.go`）

```go
var (
	ErrNoAPIKey       = errors.New("llm: api key required")
	ErrEmptyMessages  = errors.New("llm: messages cannot be empty")
	ErrUnknownProvider = errors.New("llm: unknown provider")
	ErrStreamTruncated = errors.New("llm: stream ended without completion marker")
	ErrLength          = errors.New("llm: output truncated by max_tokens")
)

// APIError 覆盖两类失败：非 2xx 响应、流内错误信封。
type APIError struct {
	Provider   Provider
	Status     int           // 0 表示无 HTTP 状态（传输层失败）
	Message    string        // 响应体摘要，截断至 2KB
	RetryAfter time.Duration // 解析自 Retry-After，0 表示未提供
	Err        error         // 底层错误，供 errors.Is/As 穿透
}

func (e *APIError) Error() string
func (e *APIError) Unwrap() error
func (e *APIError) Retryable() bool // 408/409/429/5xx 或临时传输错误
```

重试决策从"错误长什么样"改为"错误自己说能不能重试"：

```go
func (c *Client) do(ctx context.Context, payload []byte) (*http.Response, error) {
	for attempt := 1; ; attempt++ {
		resp, err := c.http.Do(req)
		if err == nil && resp.StatusCode == http.StatusOK {
			return resp, nil
		}
		apiErr := wrapFailure(c.spec.ID, resp, err) // 统一构造 *APIError
		if attempt >= c.attempts || !apiErr.Retryable() {
			return nil, apiErr
		}
		if err := sleep(ctx, backoff(attempt, apiErr.RetryAfter)); err != nil {
			return nil, err
		}
	}
}
```

`Retryable()` 规则：`Status ∈ {408, 409, 429} ∪ [500,600)` 可重试；`401/403/400/404` 不可重试；`Status == 0`（传输层）时仅当底层错误是 `net.Error` 的超时/临时错误或 `io.ErrUnexpectedEOF` 才可重试，**证书校验失败、DNS NXDOMAIN 不再重试**（修 P1-7）。

退避：`base 300ms × 2^(n-1)`，上限 8s，±20% jitter；`RetryAfter > 0` 时以它为准（再夹到 30s 上限）。默认 `attempts = 3`（字段名改对，不再叫 maxRetries）。

上层收益（`internal/tui` / `internal/agent`）：

```go
var apiErr *llm.APIError
if errors.As(err, &apiErr) {
	switch {
	case apiErr.Status == 401 || apiErr.Status == 403: // 密钥无效
	case apiErr.Status == 429:                          // 限流，提示稍后重试
	case apiErr.Status >= 500:                          // 服务端故障
	}
}
```

### 3.6 传输层（`transport.go`）

```go
func newHTTPClient() *http.Client {
	return &http.Client{Transport: &http.Transport{
		Proxy:                 http.ProxyFromEnvironment, // 修 P0-4
		ForceAttemptHTTP2:     true,                      // 修 P0-4
		DialContext:           (&net.Dialer{Timeout: 10 * time.Second, KeepAlive: 30 * time.Second}).DialContext,
		MaxIdleConns:          100,
		MaxIdleConnsPerHost:   10,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		ResponseHeaderTimeout: 120 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
	}}
}
```

错误响应体读取加硬上限（修 P0-3）：

```go
const maxErrorBody = 8 << 10
body, _ := io.ReadAll(io.LimitReader(resp.Body, maxErrorBody))
```

鉴权注入按 `Spec.Auth` 分派，key 为空时 `AuthNone` 与"远程厂商"的区分由 `New` 提前校验，不再在钩子里判空：

| Auth | 注入头 |
|---|---|
| `AuthBearer` | `Authorization: Bearer <key>` |
| `AuthGoogle` | `x-goog-api-key: <key>`（见待确认项 3） |
| `AuthNone` | 无 |

### 3.7 状态归属与入口（`llm.go`）

`Client` 去掉 `mu` / `totalUsage` / `TotalUsage()`，彻底无状态：

```go
type Client struct {
	spec     Spec
	baseURL  string
	apiKey   string
	model    string
	http     *http.Client
	attempts int
	timeout  time.Duration
}

func New(p Provider, opts ...Option) (*Client, error)
func (c *Client) Provider() Provider
func (c *Client) BaseURL() string
func (c *Client) Model() string
func (c *Client) ChatStream(ctx context.Context, req Request) (<-chan Chunk, error)
```

`llm.go` 里的 `ChatStream` 只做四步：校验 messages 非空 → `context.WithTimeout(ctx, c.timeout)` → `encodeRequest` + `do` → `pump`。约 40 行。选项（原 `options.go`）一并放在本文件，紧邻 `New`：

| Option | 用途 |
|---|---|
| `WithBaseURL(string)` | 覆盖根地址 |
| `WithAPIKey(string)` | 凭据 |
| `WithModel(string)` | 模型名 |
| `WithHTTPClient(*http.Client)` | 测试注入 / 链路追踪 |
| `WithAttempts(int)` | 最大尝试次数（替代 `WithMaxRetries`） |
| `WithStreamTimeout(time.Duration)` | 流式硬超时 |

（`WithHeader`、`WithAuthHook` 全仓零调用，删除。）

---

## 4. 调用方改造

### 4.1 `internal/protocol/protocol.go`

```go
// 之前：两个方法，mock 被迫实现无人调用的 TotalUsage
type LLM interface {
	ChatStream(ctx context.Context, req *llm.ChatRequest) (<-chan llm.ChatResponse, error)
	TotalUsage() llm.Usage
}

// 之后：单方法，Request 按值传递
type LLM interface {
	ChatStream(ctx context.Context, req llm.Request) (<-chan llm.Chunk, error)
}
```

`protocol.Event` / `ProviderInfo` / trace DTO 结构不变，仅 `llm.ChatRequest`→`llm.Request`、`llm.ChatResponse`→`llm.Chunk` 的类型名替换。

### 4.2 `internal/agent/loop.go`（`executeStep`，第 167-231 行）

改动的核心是把"通道关闭 = 成功"改为"读终块判定结局"：

```go
stream, err := llmClient.ChatStream(ctx, llm.Request{Messages: reqMsgs, Tools: toolDefs})
if err != nil { /* 原样保留：dispatch trace + return err */ }

var res *llm.Result
for chunk := range stream {
	if chunk.Final != nil {
		res = chunk.Final
		continue
	}
	if chunk.Reasoning != "" { /* 累计 + 发 EventReasoningDelta */ }
	if chunk.Text != ""      { /* 累计 + 发 EventDelta */ }
}

// 终块不变量被破坏（理论上不可达，防御性兜底）
if res == nil {
	res = &llm.Result{Stop: llm.StopFailed, Err: errNoTerminalChunk}
}
if res.Err != nil {
	a.dispatchLLMResponse(ctx, &protocol.LLMResponseTrace{Step: step, Duration: time.Since(stepStart), Error: res.Err})
	return stepUsage, false, res.Err   // 半截 assistant 消息不入记忆
}

stepUsage.Add(res.Usage)
toolCalls = res.ToolCalls
```

要点：

- **异常路径不再写入记忆**。`res.Err != nil` 直接 return，`replyBuilder` 里的半截文本丢弃（与现有"流式异常回滚"注释的意图一致，只是现在才真正生效）。
- **工具调用只在终块取**，增量块不再承载 `ToolCalls`，循环里少一个分支。
- `StopLength` 走 `res.Err != nil` 分支，用户看到"输出被 max_tokens 截断"而不是收到半截答案。
- `loop.go:210` 的 `chunk.Done && chunk.Usage != nil` 判断消失。

### 4.3 `internal/agent/config.go` / `builder.go`

- `builder.go:164`：`llm.ErrEmptyAPIKey` → `llm.ErrNoAPIKey`。
- `config.go:17-23`：`llm.New(...)` 调用形态不变（Option 名字相同），仅 `NormalizeModelName` 的来源改到 `llm.Spec.ModelAliases`。
- `config.go:61`：`llm.DefaultModel(newProvider)` → `spec.Models[0]`（经 `llm.Lookup`）。

### 4.4 `internal/config/config.go`

删除 `providerMeta`（第 36-47 行）、`providerRegistry`（第 50-95 行）、`lookupProvider`、`metaOrDefault`、`canonicalProvider`，改为消费 `llm.Specs()`：

| 现有函数 | 改造后 |
|---|---|
| `ProviderIDs()` | `for _, s := range llm.Specs() { ids = append(ids, string(s.ID)) }` |
| `ProviderAliases(p)` | `spec.Aliases` |
| `ProviderDisplayName(p)` | `spec.DisplayName` |
| `ProviderDescription(p)` | `spec.Description` |
| `RecommendedModels(p)` | `spec.Models` |
| `InferProviderFromModel(m)` | `llm.InferProvider(m)` |
| `NormalizeModelName(p, m)` | `spec.ModelAliases[strings.ToLower(m)]`，未命中则 `strings.TrimSpace(m)`，空则 `spec.Models[0]` |
| `envFallbacks` 表 | `spec.EnvKeys`（`DefaultSparkAPIKey` 内置兜底仍留在 config，属产品策略） |
| `SwitchProvider` / `ToView` | 用 `llm.Lookup` 取默认值 |

`config.go` 从 536 行降到约 400 行，且**厂商信息只剩一份**（修 P1-10）。模型常量（`SparkX25Model`、`DeepSeekProModel` 等）迁入 `Spec.Models`，`internal/config` 不再导出。

### 4.5 `internal/tui/config_wizard.go`

```go
// 之前：无参探测、内部偷建 ctx、http.DefaultClient、可能拼出 /v1/v1/models
if err := llm.ProbeLocalService(ctx, ""); err != nil { ... }

// 之后：显式厂商 + 显式 ctx，走 Spec.ProbePath，复用带超时的 Transport
if err := llm.Probe(ctx, llm.ProviderLlamaCpp, ""); err != nil { ... }
```

`appendLocalProviderNotice` 的 `"llamacpp"` 字面量改为 `string(llm.ProviderLlamaCpp)`。

---

## 5. 删除清单（不留兼容层）

| 文件 | 删除项 |
|---|---|
| `pkg/llm/openai.go` | 整个文件（内容拆入 `protocol.go` / `stream.go` / `transport.go` / `provider.go`） |
| `pkg/llm/providers.go` | 整个文件（内容重建为 `provider.go`） |
| `pkg/llm/client.go` + `options.go` | 整个文件（内容合并为 `llm.go`） |
| `pkg/llm` | `ProviderOpenAI`、`ProviderCustom`、`ResolveChatURL`、`BuildRequestPayload`、`IsLocalProvider`、`DefaultBaseURL`、`DefaultModel`、`NormalizeProvider`、`ProbeLocalService`、`Client.TotalUsage`、`Client.Chat`、`ChatRequest`、`ChatResponse`、`ErrEmptyAPIKey`、`WithHeader`、`WithAuthHook`、`WithMaxRetries` |
| `internal/config` | `providerMeta`、`providerRegistry`、`lookupProvider`、`metaOrDefault`、`canonicalProvider`、`DeepSeekProModel`/`DeepSeekReasonerModel`/`GeminiProModel`/`SparkX25Model`/`SparkX254BModel` |
| `internal/protocol` | `LLM.TotalUsage` |
| 测试 | `pkg/llm/client_test.go` 删除，按第 6 节拆为 5 个测试文件；`internal/agent/agent_test.go`、`internal/tui/tui_test.go` 中的 mock 去掉 `TotalUsage`、`Done: true` 改终块 |

---

## 6. 测试计划

测试文件跟随被测文件拆分，不搞单一大文件：

| 测试文件 | 覆盖内容 |
|---|---|
| `llm_test.go` | `New` 校验、`ChatStream` 端到端（httptest 假服务）、Option 生效 |
| `stream_test.go` | I1–I4 四条不变量、全部终止路径（第 1–11 条） |
| `transport_test.go` | 重试/退避/`Retry-After`/`Retryable`/错误体上限/Transport 字段（第 12–17 条） |
| `protocol_test.go` | 请求编码与 SSE 解码的纯函数断言（第 18–21 条） |
| `provider_test.go` | `Spec` 表、`Endpoint`、`ParseProvider`、`Probe`（第 22–24 条） |

按不变量组织，而不是按函数组织：

**I1/I2 终块语义**

1. 正常流 → 终块 `StopEnd`、`Err == nil`、文本完整、`Usage` 正确。
2. `[DONE]` 前上游断连 → `StopTruncated`、`ErrStreamTruncated`（**关键回归**：修复前这里是 `StopEnd`）。
3. `ctx` 取消 → `StopCanceled`、`errors.Is(err, context.Canceled)`，且**绝无** `StopEnd`。
4. 硬超时 → `StopTimeout`。
5. `finish_reason: "length"` → `StopLength`、`ErrLength`。
6. `data: {` 半截 JSON → `StopFailed`，错误信息含该行片段。
7. `data: {"error":{"message":"quota"}}` → `*APIError`，`Status` 从信封推断或为 0。
8. 末行无换行符的 `[DONE]` → 仍判定 `StopEnd`（修 P1-9）。
9. 消费者中途放弃 + 取消 ctx → goroutine 不泄漏（`goleak` 或超时断言）。

**I3/I4 资源与用量**

10. 通道关闭后 `Body` 已关闭（用自定义 `ReadCloser` 打点）。
11. 未上报 usage → `Result.Usage` 为零值且不 panic。

**传输层**

12. 500 重试至成功，`attempts` 计数正确；`WithAttempts(3)` = 3 次尝试。
13. 401 → 不重试，`APIError.Status == 401`。
14. 429 + `Retry-After: 1` → 退避时长 ≥ 1s（注入可替换的 sleep 或断言 `RetryAfter` 解析）。
15. 证书错误 / DNS 错误 → 不重试（构造 `x509.UnknownAuthorityError` 断言 `Retryable()==false`）。
16. `newHTTPClient()` 的 `Proxy != nil`、`ForceAttemptHTTP2 == true`（修 P0-4 的回归防线）。
17. 错误响应体 > 8KB → 只读 8KB（`Message` 长度有上限）。

**协议**

18. `reasoning_content` 不出现在请求体。
19. assistant + tool_calls、role=tool 的展平格式正确。
20. `stream_options.include_usage` 存在。
21. tool_calls 按 index 跨 chunk 拼接、顺序稳定。

**厂商**

22. 4 个 Spec 的 `Endpoint()` 拼接结果逐一断言（`/v1/chat/completions`、`/chat/completions`、`/chat/completions`、`/v1/chat/completions`）。
23. `ParseProvider` 别名（`ds`/`google`/`maas`/`llama`）、空串 → `ErrUnknownProvider`。
24. `Probe` 在 baseURL 为 `.../v1` 时不重复拼路径。

---

## 7. 实施阶段

| 阶段 | 范围 | 验收 |
|---|---|---|
| **P1** | `pkg/llm` 7 文件重写 + `internal/protocol` + `internal/agent/{loop,config,builder}` + `agent_test` mock + 5 个新测试文件 | `go build ./... && go vet ./... && go test ./...` 全绿；`pkg/llm` 覆盖率 ≥ 80% |
| **P2** | `internal/config` 元数据合并（删 registry）+ `internal/tui/config_wizard.go` 探测接口 + `tui_test` 适配 | 同上；`internal/config` 无厂商字面量残留 |
| **P3（可选）** | `Message.ToolResult` 嵌套指针扁平化为 `ToolCallID/Name/Content` | 影响 `internal/memory`、`internal/tool`、`internal/tui`、`loop.go` 共约 9 处构造点 |

P1 是必须一次做完的原子改动：接口整体更名，无法拆成更小的可编译单元。P2 可在 P1 绿后独立提交。P3 与本次缺陷修复无关，属可读性优化，可单独排期或不做。

---

## 8. 待确认

1. **`deepseek-flash` 是有效模型名吗？** 当前 `providers.go:29` 的默认值是 `deepseek-flash`，而 DeepSeek 官方模型名是 `deepseek-chat` / `deepseek-reasoner`。若 `deepseek-flash` 无效，DeepSeek 首次调用就会 400。我倾向保留现值不动（避免我改坏当前可用配置），但需要你确认。
2. **Spark 的 chat 路径确认为 `/v2/chat/completions`？** 即 baseURL `https://maas-api.cn-huabei-1.xf-yun.com/v2` + `ChatPath /chat/completions`。当前 `ResolveChatURL` 恰好推出这个结果，我按它固化到表里。
3. **Gemini 鉴权只发 `x-goog-api-key`，还是保持双写？** 官方 OpenAI 兼容端点只要求 `x-goog-api-key`，当前 `providers.go:113-117` 同时发 `Authorization: Bearer`。我倾向只发 `x-goog-api-key`（更贴近官方文档），但这会改动现有 `client_test.go:203-208`（重写后迁至 `llm_test.go`）的断言。
4. **`StopLength` 视为失败是否接受？** 即触达 `max_tokens` 时上报错误、不把半截回答写入记忆。另一种选择是当作正常完成（当前行为）。
5. **`Chat()` 非流式方法与 `WithHeader` / `WithAuthHook` 确认删除？** 三者当前全仓零业务调用，按"不保留兼容层"原则应删；若你计划后续接自定义网关，`WithHeader` 可以留。

确认以上 5 点后，我按 P1 → P2 顺序开工，每个阶段完成即停下等你验收。

---

## 9. 实施结果（2026-10-20 已落地）

P1 + P2 一次完成，工作区已可编译、`make verify` 全绿。

### 9.1 文件与行数（生产代码 1254 行）

| 文件 | 行数 | 内容 |
|---|---|---|
| `errors.go` | 100 | 6 个 sentinel + `*APIError`（Status/Body/RetryAfter/`Retryable()`） |
| `types.go` | 111 | 领域类型 + `StopReason` + `Chunk.Terminal()` |
| `llm.go` | 148 | `Client`（无状态）+ 6 个 `Option` + `New` + `ChatStream` |
| `transport.go` | 159 | `newHTTPClient`（Proxy/HTTP2 显式声明）+ 重试 + `backoffDelay` + `parseRetryAfter` |
| `stream.go` | 210 | `pump` / `readSSE` / `toolCallAccumulator` / 终块投递 |
| `provider.go` | 219 | 4 个 `Spec` + `ParseProvider` + `Endpoint` + `Authorize` + `Probe` |
| `protocol.go` | 307 | 请求/响应两套 wire 结构 + `encodeRequest` + `decodeData` |

`protocol.go` 超出 200 行预算，原因是 wire 结构体本身占 120 行（两套方向各一套），逻辑部分仍约 190 行。

### 9.2 与原方案的 3 处偏离

1. **`StopLength` / `StopContentFilter` 归入 Clean，不产生 `Err`。** 原文档 §3.3 把 `StopLength` 视为失败。实现时改判：`finish_reason: "length"` 是正常 API 结果，半截内容仍是有效内容，判失败会让用户丢掉本可见的回复。"传输是否可信"只由 `canceled` / `truncated` / `failed` 表达，语义更收敛。
2. **请求与响应各用一套 wire 结构体。** 原文档设想用一个结构体双向复用、靠 `Index *int` 区分"0 与未给"。实现改为 `reqMessage`/`reqToolCall` 与 `wireChunk`/`wireToolCall` 分离，彻底消除方向歧义（`Index` 在响应侧直接是 `int`）。
3. **`Probe` 在拼接前剥离尾部 `/v1`。** 原文档只要求"不拼出 `/v1/v1/models`"，实现用 `TrimSuffix(base, "/v1")` 一次性解决。

### 9.3 关键实现细节（与不变量对应）

- `readSSE` 先消费本行再判断读取错误 —— 修掉"末行无换行符时 `[DONE]` 被 `io.EOF` 吞掉"。
- `deliverTerminal` 不监听 `ctx`，只用 200ms 宽限期 —— 保证取消场景下终块仍能投递，否则 `Canceled` 无法与"正常完成"区分。
- `pump` 的 `defer` 顺序固定为 `close(out)` → `cancel()` → `Body.Close()`。
- `ChatStream` 只做：校验 → 编码 → `do`（含重试）→ `pump`，约 25 行。
- `Client` 无状态：删 `totalUsage` + `RWMutex`，`protocol.LLM` 收缩为单方法，用量只由 `agent/loop.go` 记录一处。
- `attempt()` 中取消/超时直接上抛 `ctx.Err()`，保证 `errors.Is(err, context.Canceled)` 可判定。

### 9.4 调用方改动

| 文件 | 改动 |
|---|---|
| `internal/protocol/protocol.go` | `LLM` 接口收为单方法，类型改为 `llm.Request` / `llm.Chunk` |
| `internal/agent/loop.go` | 循环只累积增量，收尾以终块为准；缺终块 → `ErrStreamIncomplete`；用量取自 `terminal.Usage` |
| `internal/agent/config.go` | 厂商经 `llm.ParseProvider` 校验（未知即报错）；默认模型/本地判定改读 `config.ProviderSpec` |
| `internal/agent/builder.go` | `ErrEmptyAPIKey` → `ErrNoAPIKey` |
| `internal/config/config.go` | 删 `providerMeta`/`providerRegistry`/`lookupProvider`/`metaOrDefault`/`canonicalProvider` 与 5 个模型常量；元数据全部消费 `llm.Specs()`；`envFallbacks` 由 Spec + 环境变量表派生 |
| `internal/tui/config_wizard.go` | `ProbeLocalService` → `Probe` |

### 9.5 验证

- `make verify`：gofmt + `go vet` + `go test -race ./...` + build 全通过。
- 新增 4 个测试文件按不变量组织：`llm_test.go`（构造/鉴权/重试/限长）、`stream_test.go`（终块唯一性、截断、取消、分片归并、末行无换行）、`protocol_test.go`（content 三态、reasoning 不外传、finish 语义、错误信封）、`provider_test.go`（别名、端点、鉴权头、探测）。
- 新增 `internal/agent/integration_test.go`：config → 真实 HTTP/SSE 假网关 → Agent → 事件流，覆盖"正常轮次"与"截断必须报错且不发 EventDone"。
- 用本机真实配置（spark / `spark-x2.5` / `https://maas-api.cn-huabei-1.xf-yun.com/v2`）发起一次线上流式调用：正常返回文本、`finish=end`、usage 正确解析，确认端点拼接与真实厂商兼容。

### 9.6 未处理（保持现状）

- `deepseek-flash` 仍为 DeepSeek 默认模型（未验证官方有效性），保留现值以免改坏当前可用配置。
- `Message.ToolResult` 嵌套指针未扁平化（原 P3，与本次缺陷无关）。

