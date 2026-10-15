# coustea 架构重设计与分步实施计划（v0.4：统一 OpenAI 协议）

> 日期：2026-10-15｜状态：设计草案 + 已开始阶段 1 实施。本版体现最新要求：**全部模型统一走 OpenAI Chat Completions 协议**；先实现 ReAct 循环与工具调用，完成后再重新设计并实现记忆，最后接入 TUI。本地单用户运行，不设计并发请求协调。

## 1. 统一协议决策（本版核心变化）

原方案为 Gemini 保留独立官方 SDK 适配。经核实，Google 官方提供 OpenAI 兼容端点 `https://generativelanguage.googleapis.com/v1beta/openai/`（Azure API Management 官方文档亦引用该 base URL 作为 Gemini 的 OpenAI 兼容入口），因此**可以全部统一**。本版据此调整：

- **单一适配器**：只保留一个 OpenAI Chat Completions 兼容适配器 `internal/gateway/openai.go`。Gemini、DeepSeek 及后续任何厂商都只是「baseURL + apiKey + model」的不同配置实例。
- **删除** `internal/gateway/gemini.go`、`internal/gateway/deepseek.go` 两个厂商专属实现，并移除 `google.golang.org/genai` 直接依赖（`go mod tidy` 后确认是否仍被间接引用）。
- **配置模型**：`config.Config` 的 provider 解析为统一的端点信息。Gemini 默认 baseURL 为 `https://generativelanguage.googleapis.com/v1beta/openai`，DeepSeek 为 `https://api.deepseek.com`（其 `/chat/completions` 即 OpenAI 兼容路径）。保留 `provider` 字段以便 TUI 展示与默认模型选择，但不再决定协议实现。

**已知权衡（如实记录）**：Gemini 的 OpenAI 兼容层属于官方 beta，功能覆盖不等于原生 `generateContent`。若后续需要 Gemini 原生专有能力（如 thought signature、grounding、多模态高级特性），需另开设计评审决定是否增加原生适配器——本阶段不预先实现。

## 2. 已确认的设计约束

- **实施先后**：① ReAct 循环 + 工具调用；② 完成后再重新设计并实现会话记忆；③ 最后接入 TUI 工具状态与审批交互。阶段 1 完成即报告并暂停。
- **不兼容旧实现**：删除 `Runtime`、`Plugin`、`ChatPlugin`、`SimpleAgent`、`PluginRegistry` 及相关测试，不留别名或包装层。
- **单用户无并发请求**：不实现轮次锁、请求队列或 generation 竞争；仅保留流式 channel/context 的异步协作。
- **记忆延期**：阶段 1 每次 `StreamRun` 使用只存活于本次运行的临时消息序列；这不是会话记忆。跨轮历史、窗口裁剪、摘要全部延后。
- **危险工具**：阶段 1 只用无副作用工具（测试用 fake 工具），不接入真实 shell/文件写入。

## 3. 阶段 1 实施范围（进行中）

| 切片 | 内容 |
| --- | --- |
| 1A | 新建 `internal/gateway/gateway.go`：Role/Message/ToolDefinition/ToolCall/ToolResult/Usage/ChatRequest/ChatResponse/StreamChunk/Gateway/GatewayMiddleware，并明确工具调用必须是**已完整聚合、参数为合法 JSON** 的调用。 |
| 1B | 新建 `internal/gateway/openai.go` 单一适配器：请求 DTO 独立于内部结构；SSE 按 choice 与 tool_calls index 聚合参数碎片；缺少 `[DONE]` 视为流失败；支持流式文本与工具调用。 |
| 1C | 新建 `internal/tool`：Tool 接口、Registry、Executor、Middleware 洋葱链。 |
| 1D | 重写 `internal/agent`：`Agent` + `NewAgent(gw, opts...)` + `StreamRun` + `Reset` + 事件；Functional Options 装配 SystemPrompt/Memory/Tools/ToolMiddlewares/GatewayMiddlewares/MaxSteps；实现多步 ReAct 循环与错误自愈观察结果。 |
| 1E | 新建 `internal/memory`：`Memory` 接口 + 阶段 1 的空实现（不保留跨轮历史），供后续阶段替换。 |
| 1F | 接线：更新 `internal/config`、`internal/gateway/factory.go`、`internal/tui/*`、`main.go`、`cmd/coustea/main.go` 及全部测试，移除旧类型引用。 |

**阶段 1 验收**：OpenAI 兼容适配器的本地 mock 验证文本与工具消息 wire format、SSE 参数分片聚合、截断流失败；ReAct 单元测试验证工具调用闭环、错误自愈、未知工具、MaxSteps、context 取消；`go test ./...`、`go build ./...`、`make build` 通过。不引入 `-race` 并发目标。

## 4. 阶段 2（待阶段 1 完成后重新设计）

基于阶段 1 的实际消息结构、事件与工具历史，重新通读全仓并单独提交记忆设计文档（轮次边界、原子写入、失败回滚、工具调用与结果配对、窗口裁剪、`/clear`、模型切换时历史合法性），经审核后再实现。首期只做会话内记忆。

## 5. 阶段 3（待阶段 2 完成后设计）

TUI 工具状态卡片与交互审批：事件驱动、不阻塞 Bubble Tea 事件循环，审批绑定运行代次与 call ID，过期/取消决定一律拒绝。

## 6. 后续

阶段 1–3 完成后再次全仓评审，再决定日志审计、权限策略、超时中间件、真实文件/命令工具、Token 预算与长期持久化。每类新能力都先设计、后实施。
