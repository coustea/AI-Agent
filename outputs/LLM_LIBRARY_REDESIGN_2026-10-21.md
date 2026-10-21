# pkg/llm 库化重构设计

> 状态：**已批准（2026-10-21）**。本文档取代 `LLM_MULTIPROVIDER_DESIGN_2026-10-20.md` 中的对外 API 部分；
> 旧文档的缺陷分析（P0/P1）仍然有效，本次保留其流终止不变量与错误模型。
> 变更级别：**T3**（删除公共 API、跨包依赖调整、结构性重构）。
> 硬约束：不保留任何旧接口、Option、别名或兼容层。

---

## 0. 结论

`pkg/llm` 从"围绕 tide 应用的多厂商网关"收敛为**可整包复制的纯调用库**：

- 调用方只需提供 `Provider + APIKey + BaseURL + Model`，通过 `ChatStream` 拿到流式结果。
- 库内只保留网络事实：厂商默认端点、chat 路径、默认模型、鉴权方式、是否本地。
- 产品层信息（展示名、描述、别名、推荐模型、环境变量策略、本地服务探测、模型名推断）全部迁回 `internal/config`。
- 仅支持 `deepseek`、`gemini`、`spark`、`llamacpp` 四家。
- 零第三方依赖，公共 API 只保留一个构造函数、一个调用方法和少量领域类型。

---

## 1. 边界

**做什么**

- OpenAI Chat Completions 协议 + SSE 流式。
- Function Calling、`reasoning_content`、`usage` 统计。
- 有界自动重试（可关闭）、流式硬超时、结构化 `*APIError`。

**不做什么**

- 不做展示名、别名、推荐模型、环境变量、UI 探测。
- 不做非流式 `Chat()`、多模态、自定义网关、Anthropic 原生协议。
- 不做请求级 `Model` 覆盖：模型只在 `Config` 绑定一次。
- 不保留 `Option` 函数、厂商别名解析、模型常量等旧符号。

---

## 2. 对外 API

```go
package llm

type Provider string

const (
    ProviderDeepSeek Provider = "deepseek"
    ProviderGemini   Provider = "gemini"
    ProviderSpark    Provider = "spark"
    ProviderLlamaCpp Provider = "llamacpp"
)

// Config 是创建 Client 的全部输入；零值字段由厂商默认值补齐。
type Config struct {
    Provider   Provider
    APIKey     string
    BaseURL    string        // 根地址，不含 /chat/completions
    Model      string        // 空 = 厂商默认模型
    HTTPClient *http.Client  // 空 = 内置客户端
    Timeout    time.Duration // 空 = 10 分钟（整次流式调用硬超时）
    Attempts   int           // 0 = 默认 3 次；1 = 不重试
}

func New(cfg Config) (*Client, error)

func (c *Client) Provider() Provider
func (c *Client) BaseURL() string
func (c *Client) Model() string
func (c *Client) ChatStream(ctx context.Context, req Request) (<-chan Chunk, error)

// 厂商默认值查询，供上层复用。
func Lookup(p Provider) (Spec, bool)
func Specs() []Spec
```

使用示例：

```go
client, err := llm.New(llm.Config{
    Provider: llm.ProviderDeepSeek,
    APIKey:   os.Getenv("DEEPSEEK_API_KEY"),
    Model:    "deepseek-chat",
})
if err != nil {
    return err
}

stream, err := client.ChatStream(ctx, llm.Request{
    Messages: []llm.Message{{Role: llm.RoleUser, Content: "你好"}},
})
if err != nil {
    return err
}
for chunk := range stream {
    if chunk.Terminal() {
        return chunk.Err
    }
    fmt.Print(chunk.Delta)
}
```

**校验规则**

| 条件 | 行为 |
|---|---|
| `Provider` 为空或未知 | `ErrUnknownProvider`（无别名解析） |
| 远程厂商 `APIKey` 为空 | `ErrNoAPIKey` |
| `BaseURL` 为空 | 用 `Spec.BaseURL`；非空则去掉尾部 `/` |
| `Model` 为空 | 用 `Spec.DefaultModel` |
| `Timeout <= 0` | 10 分钟 |
| `Attempts <= 0` | 3 次；`1` 表示不重试 |
| `HTTPClient == nil` | 内置 Transport（系统代理、HTTP/2、阶段超时） |

`Request` 不含 `Model` 字段；换模型就新建 Client（Client 无状态，成本极低）。

---

## 3. 内部结构

单包七文件，按变更轴切分：

| 文件 | 职责 | 预算 |
|---|---|---|
| `llm.go` | `Config`、`Client`、`New`、`ChatStream`、包注释 | ~150 |
| `types.go` | `Role` / `Message` / `ToolDefinition` / `ToolCall` / `ToolResult` / `Request` / `Chunk` / `StopReason` / `Usage` | ~110 |
| `provider.go` | `Provider` 常量、`AuthKind`、`Spec`、`Lookup` / `Specs` / `endpoint` / `authorize` | ~110 |
| `protocol.go` | OpenAI wire 结构、请求编码、SSE data 解码（纯函数） | ~250 |
| `stream.go` | `pump` / `readSSE` / 工具调用分片归并、终块不变量 | ~200 |
| `transport.go` | HTTP 客户端、请求发送、有界重试与退避 | ~150 |
| `errors.go` | sentinel + `*APIError` + `Retryable()` | ~90 |

依赖方向单向：`llm.go → stream.go → protocol.go → types.go`，`transport.go → provider.go`，`errors.go` 被各层引用。
`protocol.go` 不认识 `http`，`stream.go` 不认识 `json`，`transport.go` 不认识 SSE。

不采用子包：四个厂商的叶子包没有分层收益，只会增加导入路径与复制成本。

---

## 4. 厂商事实表

```go
type AuthKind uint8

const (
    AuthBearer AuthKind = iota // Authorization: Bearer <key>
    AuthGoogleKey              // x-goog-api-key: <key>
)

type Spec struct {
    ID           Provider
    BaseURL      string
    ChatPath     string
    DefaultModel string
    Auth         AuthKind
    Local        bool
}
```

| Provider | BaseURL | ChatPath | 默认模型 | Auth | Local |
|---|---|---|---|---|---|
| `deepseek` | `https://api.deepseek.com` | `/v1/chat/completions` | `deepseek-flash` | Bearer | 否 |
| `gemini` | `https://generativelanguage.googleapis.com/v1beta/openai` | `/chat/completions` | `gemini-2.5-flash` | GoogleKey | 否 |
| `spark` | `https://maas-api.cn-huabei-1.xf-yun.com/v2` | `/chat/completions` | `spark-x2.5-4b` | Bearer | 否 |
| `llamacpp` | `http://127.0.0.1:8080` | `/v1/chat/completions` | `local-model` | Bearer | 是 |

库内不再包含 `Aliases`、`DisplayName`、`Description`、`RecommendedModels`、`ModelPrefixes`、`ModelSubstrings`、`ProbePath` 与模型常量。

---

## 5. 流与错误语义

四条不变量保持不变：

1. 终块（`Finish != ""`）恰好一次，且是通道最后一个元素。
2. `Err != nil` 当且仅当 `Finish ∈ {canceled, timeout, truncated, failed}`。
3. `Usage` 为值类型；上游未上报时为零值。
4. 工具调用只在终块携带，已按 index 跨分片还原；通道关闭前响应体必关闭、Context 必释放。

`StopReason`：`end` / `tool_calls` / `length` / `content_filter` / `canceled` / `truncated` / `failed`。
`length` 与 `content_filter` 仍算正常完成。

错误模型保留 `*APIError`（`Status` / `Body` / `RetryAfter` / `Retryable()`）：

- 重试：`408`、`409`、`429`、`5xx`、临时传输错误。
- 不重试：`400/401/403/404`、证书错误、DNS NXDOMAIN、取消、超时。
- 退避：`300ms × 2^(n-1)`，上限 8s，±20% 抖动；`Retry-After` 优先并夹到 30s。

---

## 6. 调用方迁移

| 位置 | 改动 |
|---|---|
| `internal/config/provider_meta.go`（新增） | 展示名、描述、别名、推荐模型、模型前缀推断、环境变量键、Spark 模型名纠错、`ParseProvider`、`ProbeLocal` |
| `internal/config/config.go` | 删除展示层元数据函数与 `providerEnvKeys`，改为消费 `providerMetas`；`ProviderSpec` 合并 `llm.Spec` 与本地元数据 |
| `internal/agent/config.go` | `llm.ParseProvider` → `config.ParseProvider`；`llm.New(llm.Config{...})` |
| `internal/agent/loop.go` | `ChatStream(ctx, &llm.Request{...})` → `ChatStream(ctx, llm.Request{...})` |
| `internal/protocol/protocol.go` | `LLM` 接口改为值传递 `llm.Request` |
| `internal/tui/config_wizard.go` | `llm.Probe(ctx, "")` → `config.ProbeLocal(ctx, "")`；`"llamacpp"` → `string(llm.ProviderLlamaCpp)` |
| 测试 | mock 去掉 `*llm.Request`；构造改用 `llm.Config`；模型常量改为 config 层常量或默认值查询 |

`internal/config` 预计 +140 行；`internal/agent` / `internal/tui` 为机械替换。

---

## 7. 删除清单

| 位置 | 删除项 |
|---|---|
| `pkg/llm` | 6 个 `Option` 函数、`ParseProvider`、`ProviderIDs`、`Probe`、`Spec` 的展示字段、模型常量、`Request.Model`、`AuthNone`、历史厂商常量 |
| `internal/config` | `llm.ParseProvider` / `llm.ProviderIDs` / `llm.Probe` / `llm.Model*` 依赖 |
| 测试 | 别名/探测用例迁至 `internal/config`；`llm_test.go` 全部改用 `Config` |

不保留任何 `Deprecated` 注释或转发函数。

---

## 8. 测试与验收

| 测试文件 | 覆盖 |
|---|---|
| `pkg/llm/llm_test.go` | `New` 默认值/校验、Config 覆盖、ChatStream 端到端 |
| `pkg/llm/provider_test.go` | 四个 Spec、端点拼接、鉴权头、Local、无别名 |
| `pkg/llm/protocol_test.go` | 请求编码（模型来自 Client、reasoning 不外传、工具调用、include_usage）、SSE 解码 |
| `pkg/llm/stream_test.go` | 终块唯一性、截断、取消、末行无换行、工具分片归并、usage |
| `pkg/llm/transport_test.go` | 500 重试、401 不重试、Retry-After、错误体上限、代理/HTTP2、证书错误不重试 |
| `internal/config/provider_meta_test.go` | 别名、展示顺序、模型推断、Spark 纠错、ProbeLocal |
| `internal/agent/integration_test.go` | 配置 → 真实 SSE 假网关 → Agent → 事件流 |

验收：

- `make verify` 全绿（gofmt + vet + `go test -race` + build）。
- `pkg/llm` 覆盖率 ≥ 80%。
- 生产代码行数目标 ≤ 1050 行（重构前 1254 行）。

---

## 9. 风险

1. 元数据搬家不是重复维护：网络事实只在 `llm.Spec` 一份，`internal/config` 只补充展示层字段。
2. `deepseek-flash` 仍是默认模型（未验证官方有效性），本次不改，避免破坏当前可用配置。
3. `BaseURL` 语义为根地址，不接受完整 `/chat/completions`。
4. 破坏性变更仅影响本仓库，已确认无外部 Go 模块依赖。

---

## 10. 实施结果（2026-10-21）

- `pkg/llm` 生产代码 **1117 行**（重构前 1254 行），七文件；公共 API 收敛为 `Config` + `New` + `ChatStream` + 四个 `Provider` 常量 + 领域类型/错误。
- `pkg/llm` 测试覆盖率 **85.0%**。
- `make verify` 全绿：gofmt、`go vet`、`go test -race -count=1 ./...`、build 均通过。
- 已删除：6 个 `Option`、`ParseProvider`（库内）、`ProviderIDs`、`Probe`、`Spec` 展示字段、模型常量、`Request.Model`。
- 已迁移：展示名/别名/推荐模型/模型推断/环境变量/Spark 纠错/本地探测 → `internal/config/provider_meta.go`；调用方改用 `config.ParseProvider`、`config.ProbeLocal`、`llm.New(llm.Config{...})`。
- 新增 `pkg/llm/README.md`，记录库的对外契约与使用方式。
- 本次未使用内置密钥发起真实厂商线上调用；`internal/agent/integration_test.go` 通过真实 HTTP/SSE 假网关覆盖完整链路。
