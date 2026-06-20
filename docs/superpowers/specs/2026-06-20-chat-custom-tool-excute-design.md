# Chat 自研工具调用设计

## 目标

优先重构 Chat 模块的工具调用，保留 LangChain `ChatOpenAI` 作为模型客户端，但彻底移除 Chat 对 LangChain 工具体系的依赖，包括 `@tool`、`StructuredTool`、`bind_tools()` 与工具对象的 `.ainvoke()`。

本阶段不修改 Path 和 Resource。它们将在 Chat 验证稳定后复用相同的 `Tool` / `ToolExcute` 基础接口，但继续保持各自的业务流程、记录和持久化模型。

## 文件结构

只新增一个基础设施文件：

```text
server/app/infra/tool_excute.py
├── Tool
└── ToolExcute
```

现有业务工具仍保留在 `server/app/chat/tools/`，不会把搜索、画像、记忆、知识库或网页读取实现搬入基础设施层。

## Tool

`Tool` 是单个工具的定义对象，包含：

- `name`：发给模型并用于注册表查找的稳定名称。
- `description`：模型选择工具时使用的用途说明。
- `args_model`：Pydantic 参数模型，用于生成 JSON Schema 和执行前校验。
- `handler`：普通异步 Python callable，执行真实业务逻辑。

`Tool` 不继承 LangChain 类型，也不使用装饰器。无参数工具仍应提供一个明确的空 Pydantic 模型，保证 schema 与校验行为一致。

## ToolExcute

`ToolExcute` 在一个类内完成工具注册、模型调用和工具执行，避免拆出多层抽象。它持有一个 `ChatOpenAI` 模型实例和一个按名称索引的 `Tool` 注册表。

公开能力如下：

- `register(tool)`：注册一个工具；重复名称直接报错，防止静默覆盖。
- `register_many(tools)`：批量注册。
- `get_tool(name)`：获取已注册工具；未知名称给出明确错误。
- `get_tools_description()`：返回 OpenAI-compatible `tools` JSON Schema。
- `invoke(messages, **model_kwargs)`：调用 `ChatOpenAI.ainvoke()`，通过原生 `tools` 参数发送工具描述，自行规范化并返回工具调用列表。
- `execute(tool_call)`：查找工具、解析参数、执行 Pydantic 校验并调用 handler。
- `execute_all(tool_calls)`：并发执行一批工具调用，并保留与输入一致的结果顺序。

`invoke()` 不调用 `bind_tools()`。工具描述以原生 OpenAI-compatible JSON 通过 `ChatOpenAI.ainvoke(messages, tools=...)` 传入。

## 模型响应兼容

`ToolExcute` 统一将模型响应规范化为项目内部字典：

```python
{
    "id": "call_xxx",
    "name": "duckduckgo_search",
    "args": {"query": "..."},
}
```

解析需要覆盖：

- 标准 OpenAI `tool_calls` 数组。
- Spark 返回单个 `tool_calls` 字典。
- `arguments` 为 JSON 字符串、字典或空值。
- 缺少调用 ID 时生成稳定格式的本地 ID。
- JSON 无法解析、工具名为空或参数不是对象时返回明确错误，不执行 handler。

解析逻辑不依赖 LangChain 的 `StructuredTool` 或工具调用解析器。允许从 `ChatOpenAI` 返回消息的原始附加字段读取响应；若不同 provider 已将其规范化到消息的 `tool_calls` 字段，也转换为同一内部格式。

## Chat 迁移

### 工具注册

删除 `TutorToolRegistry` 对 `StructuredTool.from_function()` 的使用。Chat 在每个辅导轮次创建请求级 `ToolExcute`，并注册：

- `get_learner_profile`
- `get_long_term_memory`
- `search_knowledge_base`
- `duckduckgo_search`
- `duckduckgo_instant_answer`
- `tavily_search`
- `spark_search`
- `open_web_page`
- `find_in_web_page`
- `extract_web_links`
- `read_web_pdf`

请求级创建是必要的，因为画像、记忆、网页研究 session 和事件回调都绑定到当前轮次，不能放入全局单例。

### 工具实现

Chat 工具改为普通异步函数：

- 删除 `@tool`。
- 不再调用工具对象 `.ainvoke(payload)`。
- 包装器直接调用底层 handler，并继续发送现有 `tool_start` / `tool_done` 事件。

### 研究循环

`WebResearchRunner` 继续负责 Chat 专属策略：最大迭代数、域名预算、证据整理与 ToolMessage 上下文。模型工具选择改由 `ToolExcute.invoke()` 完成，真实执行改由 `ToolExcute.execute()` 完成。

事件、Evidence、source 整理和 `ChatToolInvocation` 落库保持现有语义，不迁入通用类。

## llm.py 集成

`Llm` 保留普通生成、流式输出、结构化 JSON 和视觉接口。它新增一个轻量创建入口，根据当前文本模型返回请求级 `ToolExcute`。

旧 `ainvoke_tools()` 和 `ChatModel` 内仅为 LangChain 工具解析服务的兼容代码，在 Chat 完成迁移且无其他调用者依赖后删除。由于 Path 仍在使用旧工具链，本阶段允许旧入口暂时保留，但 Chat 不再引用它；删除工作放入 Path 迁移阶段。

## 错误处理

- 重复注册：立即抛出配置错误。
- 未知工具：产生失败结果，不执行任何 handler。
- 参数 JSON 错误：产生失败结果并保留原始调用 ID。
- Pydantic 校验错误：产生失败结果，错误信息可记录但不把敏感上下文暴露给前端。
- handler 异常：由 Chat 现有执行层转换为失败事件和失败 invocation。
- 单个并发工具失败：不取消同批其他工具。

## 测试

采用 TDD，先补失败测试，再修改生产代码。覆盖：

1. `Tool` 生成正确的 OpenAI function schema。
2. `ToolExcute` 注册、重复名称拒绝和工具描述获取。
3. 标准、Spark 单字典、缺失 ID、字符串/字典 arguments 的解析。
4. Pydantic 校验后调用正确 handler。
5. 未知工具、非法 JSON、handler 异常。
6. Chat 请求级工具注册不再产生 LangChain `StructuredTool`。
7. WebResearchRunner 能完成多轮“模型选择 → 工具执行 → 结果回传”。
8. Chat 工具调用事件、Evidence 和持久化契约保持不变。

验证命令以 Chat 定向测试为主，并避开项目文档中注明的既有失败测试；最后运行后端相关测试集合。

## 后续阶段

Chat 稳定后：

1. Path 将搜索工具迁移到 `ToolExcute`，删除其 `bind_tools()` 和工具 `.ainvoke()`。
2. Resource 根据明确的业务调用场景注册自己的工具，不与 Path 合并记录、详情页或持久化模型。
3. 全仓库无调用者后，从 `llm.py` 删除旧 `ainvoke_tools()` 及不再需要的 LangChain 工具兼容代码，并清理相关依赖引用。
