# 自研 ToolExcute 工具调用设计

## 目标

优先重构 Chat 模块的工具调用，保留 LangChain `ChatOpenAI` 作为模型客户端，但彻底移除项目对 LangChain 工具体系的依赖，包括 `@tool`、`StructuredTool`、`bind_tools()`、`Llm.ainvoke_tools()` 与工具对象的 `.ainvoke()`。

本次重构不提供兼容层或双轨入口。Chat 迁移完成后，同一轮继续迁移 Path 的模型工具调用并删除旧接口。Resource 只有在存在真实模型工具调用时才接入，不为了接口统一增加空注册或代理代码。Resource 与 Path 继续保持各自的业务流程、记录、详情页和持久化模型。

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
- `invoke(messages, **model_kwargs)`：调用 `ChatOpenAI.ainvoke()`，通过原生 `tools` 参数发送工具描述，返回模型消息和规范化工具调用列表。
- `execute(tool_call)`：查找工具、解析参数、执行 Pydantic 校验并调用 handler。
- `execute_all(tool_calls)`：并发执行一批工具调用，并保留与输入一致的结果顺序。

`invoke()` 不调用 `bind_tools()`。工具描述以原生 OpenAI-compatible JSON 通过 `ChatOpenAI.ainvoke(messages, tools=...)` 传入。返回值使用二元组 `(response, tool_calls)`，保留原始模型消息供 Chat 和 Path 继续构造工具结果上下文，同时避免再增加结果包装类。

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

删除旧 `ainvoke_tools()`。任何调用者不得通过 `bind_tools()` 或旧入口请求工具调用，也不保留转发、弃用提示或别名。

## Path 迁移

Path 现有搜索工具改为普通异步 callable，并使用 `Tool` 描述参数。工作流通过 `ToolExcute.invoke()` 获取模型消息与工具调用，再通过 `ToolExcute.execute()` 执行。Path 自己继续负责搜索结果整理、规划状态和持久化，不复用 Chat 的 Evidence 或调用记录。

迁移完成后，全仓库生产代码和测试中都不得再出现 `bind_tools()`、`StructuredTool`、`@tool` 或 `ainvoke_tools()`。

## Resource 边界

Resource 当前以 LangGraph 节点直接调度 agent，没有模型选择工具的调用链，因此本次不增加 `ToolExcute` 依赖。若检查发现真实的模型工具调用，则只迁移该调用点；不得合并 Resource 与 Path 的记录、详情页或持久化模型。

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
9. Path 搜索循环使用 `ToolExcute`，结果与规划状态契约保持不变。
10. 全仓库静态扫描确认旧工具接口零残留。

验证命令以 Chat 定向测试为主，并避开项目文档中注明的既有失败测试；最后运行后端相关测试集合。

## 完成标准

1. Chat 与 Path 的模型工具调用全部经过 `ToolExcute`。
2. `ChatOpenAI` 仍是模型客户端，普通生成和结构化输出接口不受影响。
3. 全仓库不存在 LangChain 工具注册、绑定或执行代码。
4. 不存在旧工具接口兼容层。
5. Chat、Path、Resource 的业务数据与持久化边界保持独立。
