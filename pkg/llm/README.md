# pkg/llm

零第三方依赖的大模型调用库。统一走 OpenAI Chat Completions + SSE，预置常见厂商规格，同时支持传入任意自定义 `BaseURL`、`APIKey`、`Model` 直连兼容端点。

| Provider | 默认端点 | 默认模型 | 鉴权 |
|---|---|---|---|
| `openai` / `custom` | 自定义 BaseURL | 自定义 Model | `Authorization: Bearer` (本地服务免密) |
| `deepseek` | `https://api.deepseek.com` | `deepseek-flash` | `Authorization: Bearer` |
| `gemini` | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-2.5-flash` | `x-goog-api-key` |
| `spark` | `https://maas-api.cn-huabei-1.xf-yun.com/v2` | `spark-x2.5-4b` | `Authorization: Bearer` |
| `llamacpp` | `http://127.0.0.1:8080` | `local-model` | 可空 |

## 快速开始

### 1. 通用端点直连（自主输入三要素）

```go
client, err := llm.New(llm.Config{
    BaseURL: "https://api.openai.com/v1", // 或任何兼容代理/中转端点，自动智能规范化
    APIKey:  os.Getenv("OPENAI_API_KEY"),
    Model:   "gpt-4o",
})
if err != nil {
    return err
}

// 同步调用（直接拿完整结果，复用 Chunk 零多余类型）
resp, err := client.Chat(ctx, llm.Request{
    Messages: []llm.Message{{Role: llm.RoleUser, Content: "你好"}},
})
if err != nil {
    return err
}
fmt.Println(resp.Delta, resp.Usage.TotalTokens)
```

### 2. 流式调用

```go
stream, err := client.ChatStream(ctx, llm.Request{
    Model:    "gpt-4o-mini", // 可选：单次请求覆盖 Client 默认模型
    Messages: []llm.Message{{Role: llm.RoleUser, Content: "讲个故事"}},
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

## Config

| 字段 | 说明 |
|---|---|
| `Provider` | 可选；预设厂商之一，或留空/自定义（只要传入 `BaseURL` 即自动兼容） |
| `APIKey` | 远程端点必填；本地服务（127.0.0.1/localhost）可空 |
| `BaseURL` | 服务端点（智能兼容 `/v1`、`/chat/completions` 等后缀）；预设厂商可留空使用默认值 |
| `Model` | 客户端默认模型名（单次 `Request.Model` 可覆盖） |
| `HTTPClient` | 空 = 内置 Transport（系统代理、HTTP/2、阶段超时） |
| `Timeout` | 整次调用硬超时；空 = 10 分钟 |
| `Attempts` | 最大尝试次数（含首次）；0 = 3，1 = 不重试 |

## 流式契约

- 终块（`chunk.Terminal()`）恰好一次，且一定是通道最后一个元素。
- `chunk.Err != nil` 当且仅当异常终止（取消、超时、上游截断、协议/传输失败）。
- `chunk.Usage` 只在终块有效；上游未上报时为零值。
- `chunk.ToolCalls` 只在终块携带，已按 index 跨分片还原。
- 调用方必须读完通道，或在放弃时取消 `ctx`；库会关闭响应体并释放资源。

## 错误处理

非 2xx 响应与传输失败返回 `*llm.APIError`：

```go
var apiErr *llm.APIError
if errors.As(err, &apiErr) {
    switch {
    case apiErr.Status == 401 || apiErr.Status == 403:
        // 密钥无效
    case apiErr.Status == 429:
        // 限流
    }
}
```

`APIError.Retryable()` 决定是否值得重试；`RetryAfter` 来自上游 `Retry-After`。

## 设计边界

库只负责网络与协议。展示名、别名、推荐模型、环境变量策略、本地服务探测属于调用方应用层，
不应写进本包；这样整包复制到其他项目时不会带走产品信息。
