# Eino 源码深度教程

以 `github.com/cloudwego/eino v0.9.23` **源码为唯一依据**的 Go LLM 应用开发教程。

## 为什么以源码为准

官网文档在这个版本上已有明显滞后。举例（详见[第一章附录 D](ch01.md#附录-d-与旧版-api-的差异清单)）：

| 项 | 官网 | v0.9.23 源码 |
|---|---|---|
| `model.Options` 字段 | 列 6 个 | 实际 **11 个** |
| `Message` 字段 | 漏 `ToolName` / `ReasoningContent` | 实际 **12 个** |
| `schema.NewParamsOneOfByOpenAPIV3` | 文档提到 | **不存在** |
| `AgentMiddleware` | 仍在教 | 源码标 **Deprecated** |
| `TypedModelContext.Tools` | 仍在用 | 源码标 **Deprecated** |

源码注释里的 `Deprecated:` / `NOT RECOMMENDED:` / `Recommended use cases` 是最权威的 API 说明。

## 章节

| 章节 | 内容 | 篇幅 |
|---|---|---|
| [第一章：Message、ChatModel 与 Agent 运行时](ch01.md) | Message / ChatModel / ChatModelAgent / Runner / AgentEvent | 7250+ 行 |
| [第二章：Tool](ch02.md) | 工具接口、ToolsNode、自定义工具、传给 Agent | 670 行 |

## 第一章结构

| 部分 | 主题 |
|---|---|
| 阅读约定 | 源码定位、泛型 sealed union、两条消息路径 |
| 第 1 章 | Message：12 字段、`ConcatMessages` 拼接机制、多模态三代演进、`AgenticMessage` 对比、`StreamReader` 消费协议 |
| 第 2 章 | ChatModel：三层接口、`Options` 11 字段、`Option` 双通道、`ToolChoice`、`Generate` vs `Stream` |
| 第 3 章 | ChatModelAgent：13 字段、ReAct 图拓扑、迭代上限、`defaultGenModelInput` 的缓存陷阱、九个中间件钩子 |
| 第 4 章 | Runner：五项职责、`CheckPointStore`、`Resume` 两种恢复、取消三种粒度、`TurnLoop` |
| 第 5 章 | AgentEvent：六字段变体、`AsyncIterator` 无界缓冲、`Action` 五类信号、事件序列、SSE 翻译 |
| 第 6 章 | 完整可运行示例：纯 ChatModel → 加 Tool → 生产骨架 |
| 第 7 章 | 60 条陷阱清单 + 诊断流程 |
| 附录 A | 源码索引（按文件分组的 `文件:行号`） |
| 附录 B | 类型速查 |
| 附录 C | `AgenticMessage` 20 种 `ContentBlockType` |
| 附录 D | 与旧版 API 的差异清单 |

## 源码定位

所有引用格式为 `包内相对路径:行号`，拼上前缀即可定位：

```bash
echo "$(go env GOMODCACHE)/github.com/cloudwego/eino@v0.9.23"
```

例如 `adk/react.go:345` → `$(go env GOMODCACHE)/github.com/cloudwego/eino@v0.9.23/adk/react.go` 第 345 行。

## 代码验证

- 文中所有 ```` ```go ```` 完整程序（`package main`）均在本机 `go build` 通过；
- 三个不依赖真实 API 的示例已实际运行，输出与文中一致；
- 依赖真实模型的示例（第 6 章）只做编译验证。

复现验证：

```bash
go get github.com/cloudwego/eino@v0.9.23
go get github.com/cloudwego/eino-ext/components/model/openai@v0.1.13
```

## 依赖版本

```
github.com/cloudwego/eino v0.9.23
github.com/cloudwego/eino-ext/components/model/openai v0.1.13
```

## 阅读建议

**按顺序读**。第一章的 1.5 节（`ConcatMessages`）和 3.6 节（`defaultGenModelInput`）是理解后续所有内容的基础——前者解释流式拼接，后者解释 prompt 缓存。

**遇到问题时直接查第 7 章**。60 条陷阱按「现象 → 根因 → 解法」组织，每条都带源码行号。

**不要跳过附录 A**。它是全文的源码索引，比通读源码快得多。
