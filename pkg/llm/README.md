# pkg/llm

零第三方依赖、面向标准 **OpenAI 兼容协议**（Chat Completions + SSE）的轻量级大模型通信库。

只需提供 `BaseURL`、`APIKey`、`Model` 三要素，即可直连任意兼容端点（包括 OpenAI、DeepSeek、Moonshot、通义千问、SiliconFlow、Ollama、vLLM、LocalAI、Gemini 等）。

## 快速开始

### 1. 基础调用（三要素直连）

```go
client, err := llm.New(llm.Config{
    BaseURL: "https://api.openai.com/v1", // 自动智能兼容纯域名、/v1 或 /chat/completions 后缀
    APIKey:  os.Getenv("OPENAI_API_KEY"),
    Model:   "gpt-4o",
})
if err != nil {
    return err
}

// 同步非流式调用（直接拿完整结果，复用 Chunk 零多余类型）
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
    Model:    "deepseek-reasoner", // 可选：单次请求覆盖 Client 默认模型
    Messages: []llm.Message{{Role: llm.RoleUser, Content: "讲个故事"}},
})
if err != nil {
    return err
}

for chunk := range stream {
    if chunk.Terminal() {
        return chunk.Err
    }
    // 思考模型支持增量输出 ReasoningContent
    if chunk.ReasoningContent != "" {
        fmt.Print(chunk.ReasoningContent)
    }
    fmt.Print(chunk.Delta)
}
```

### 3. 本地模型直连（Ollama / vLLM 免密）

```go
client, err := llm.New(llm.Config{
    BaseURL: "http://127.0.0.1:11434", // APIKey 留空即可免密访问本地服务
    Model:   "qwen2.5:7b",
})
```

## Config 配置项

| 字段 | 类型 | 说明 |
|---|---|---|
| `BaseURL` | string | **必填**。服务根地址（如 `https://api.openai.com/v1`、`http://localhost:11434`） |
| `APIKey` | string | 可选。远程端点填 Bearer Token；本地端点可留空 |
| `Model` | string | 可选。客户端默认模型名（单次 `Request.Model` 可覆盖） |
| `HTTPClient` | *http.Client | 可选。空则使用内置优化 Transport（系统代理、HTTP/2、阶段超时） |
| `Timeout` | time.Duration | 可选。整次调用硬超时；空 = 默认 10 分钟 |
| `Attempts` | int | 可选。最大尝试次数（含首次）；0 = 默认 3 次，1 = 不重试 |

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

`APIError.Retryable()` 自动识别可重试错误（5xx、429、超时、网络闪断，自动规避证书/DNS/取消等不可恢复错误）；`RetryAfter` 自动解析上游 `Retry-After` 头。
