# TutorAgent 图解说明后端能力设计

## 背景

TutorAgent 当前主工作流是：

```text
START -> classify
  ├─ direct_answer -> END
  └─ attachment_answer -> END
```

本次改造在智能辅导文字回答完成后，可选生成一份结构化知识图解数据 `diagram`。图解不是图片生成模型生成的图片，而是 DeepSeek 输出、受 Pydantic 约束的结构化 JSON，前端后续根据 `diagram.type` 渲染对应图解组件。

## 目标

- 普通回答和附件回答都可以生成图解。
- 图解生成是回答后的可选资源节点，不参与主回答路由。
- 图解失败不能影响主回答。
- 前端只上传 `need_diagram: true | false`。
- `need_diagram=true` 时后端尽量生成图解，并由后端自动选择图解类型。
- `need_diagram=false` 时后端跳过图解生成。
- 最终通过 SSE `done.data.resources.diagram` 返回图解 JSON 或 `null`。

## 非目标

- 不生成图片文件。
- 不接入图片生成模型。
- 不让前端第一版指定 `diagram_type`。
- 不修改 deepagent 核心回答逻辑。
- 不把图解作为新的 `classify` 主路由。
- 不在第一版实现 JSON prompt + Pydantic 校验兜底；第一版优先使用 LangChain `with_structured_output`。

## 工作流设计

改造后的 LangGraph 工作流：

```text
START -> classify
  ├─ direct_answer -> diagram_generate -> END
  └─ attachment_answer -> diagram_generate -> END
```

`classify` 的条件路由保持现状，只决定走纯文本回答还是附件回答。`direct_answer` 和 `attachment_answer` 仍然只负责生成最终文字回答。`diagram_generate` 只读取已完成的最终回答和上下文，作为回答后的可选资源生成节点运行。

`GRAPH_NODE_NAMES` 增加 `diagram_generate`，`ANSWER_NODE_NAMES` 保持 `{"direct_answer", "attachment_answer"}`。这样 SSE 的正文 token 仍只在回答节点结束时发送，不会把图解生成过程混入正文流。

## 请求与状态

请求链路增加 `need_diagram`：

- `MentorChatRequest.need_diagram: Optional[bool] = None`
- `/chat/stream` Form 参数 `need_diagram: bool = Form(default=False)`
- `ChatUseCases.stream_chat_events(...)`
- `ChatUseCases.stream_chat(...)`
- `TutorAgent.chat_stream(...)`
- `prepare_tutor_turn(...)`
- `initial_state["need_diagram"]`

虽然内部状态类型保留 `Optional[bool]` 以兼容未来自动判断，但第一版前端只传 `true/false`，接口默认值为 `False`。因此不传时默认不生成图解，避免额外模型调用。

`TutorState` 增加：

```python
need_diagram: Optional[bool]
diagram: Optional[dict[str, Any]]
diagram_error: Optional[str]
```

含义：

- `need_diagram=True`：前端要求尽量生成图解。
- `need_diagram=False`：前端关闭图解生成。
- `need_diagram=None`：保留给未来自动判断。
- `diagram`：最终结构化图解 JSON。
- `diagram_error`：调试用错误信息，不返回给普通用户。

## 图解 Schema

新增 `server/app/chat/diagram_schemas.py`，只负责结构定义和校验。

公共约束：

- 使用 Pydantic v2。
- 所有模型使用 `ConfigDict(extra="forbid")`。
- `type` 使用 `Literal` 限制。
- `title` 最大 20 字。
- `summary` 最大 50 字。
- `label` 最大 16 字。
- `description` 最大 40 字。
- 使用 `model_validator` 校验边、消息、状态转换引用的节点 id 是否存在。
- `sequence` 和 `state` 的 `from/to` 使用 alias，Python 内部字段使用 `from_actor/to_actor`、`from_state/to_state`。
- `HierarchyNode` 是递归类型，定义后调用 `HierarchyNode.model_rebuild()`。
- 导出 `DIAGRAM_MODEL_MAP`。

核心类型：

- `BaseDiagramModel`
- `DiagramNode`
- `DiagramEdge`
- `HierarchyNode`
- `HierarchySpec`
- `FlowStep`
- `FlowEdge`
- `FlowSpec`
- `CompareItem`
- `CompareSpec`
- `RelationSpec`
- `SequenceActor`
- `SequenceMessage`
- `SequenceSpec`
- `StateTransition`
- `StateSpec`
- `HierarchyDiagram`
- `FlowDiagram`
- `CompareDiagram`
- `RelationDiagram`
- `SequenceDiagram`
- `StateDiagram`
- `EnabledDiagram`
- `DiagramDecision`
- `DIAGRAM_MODEL_MAP`

支持的图解类型：

- `hierarchy`：知识点组成、分类、结构拆解。
- `flow`：步骤、过程、运行机制。
- `compare`：区别、优缺点、易混概念。
- `relation`：依赖、因果、模块关系。
- `sequence`：客户端/服务器、前后端、协议交互。
- `state`：状态机、生命周期、算法过程。

`EnabledDiagram` 使用 `Annotated + Union + Field(discriminator="type")`，但实际结构化输出不直接对 `EnabledDiagram` 调用。第一步先用 `DiagramDecision` 决策类型，第二步根据 `DIAGRAM_MODEL_MAP` 选择具体 Diagram 模型生成。

## 图解 LLM 与 Prompt

`TutorAgent.__init__` 新增图解专用 LLM：

```python
self.diagram_llm = get_deepseek_chat_llm(
    temperature=0.1,
    streaming=False,
    max_tokens=1600,
)
```

图解生成固定使用 DeepSeek，且不开 streaming。

新增两个系统 Prompt：

- `DIAGRAM_DECISION_SYSTEM_PROMPT`：判断是否生成图解、选择最合适的 6 类图解结构。
- `DIAGRAM_GENERATION_SYSTEM_PROMPT`：根据学生问题、最终回答和上下文生成前端可渲染的结构化图解对象。

在 `need_diagram=True` 的第一版行为中，决策器仍然负责选择 `diagram_type`，但应尽量返回 `need_diagram=True`。如果模型判断完全不适合图解，可以返回不生成。

## Agent 方法设计

新增 `_decide_diagram(...)`：

- 读取 `state.get("need_diagram")`。
- `False` 时直接返回 `DiagramDecision(need_diagram=False, diagram_type=None, reason="用户未开启图解生成")`。
- 使用 `self.diagram_llm.with_structured_output(DiagramDecision)`。
- 输入包含用户问题、最终回答、用户是否主动要求图解。
- 如果返回的 `diagram_type` 不在 `DIAGRAM_MODEL_MAP`，降级为不生成。
- 捕获异常并 `logger.warning`，返回不生成。

新增 `_generate_diagram_by_type(...)`：

- 通过 `DIAGRAM_MODEL_MAP` 获取具体 Pydantic Diagram 类。
- 从 state 读取 `profile_context`、`fact_context`、`recent_chat_context`、`attachment_analysis_context`。
- 使用 `self.diagram_llm.with_structured_output(model_cls)`。
- 不直接对 `EnabledDiagram` 这个 Union 做结构化输出。
- 调用后再次执行 `model_cls.model_validate(diagram)`。
- 返回 `diagram.model_dump(by_alias=True)`。
- 捕获异常并 `logger.warning`，返回 `None`。

新增 `_diagram_generate_node(...)`：

- 从 `state["messages"]` 用 `extract_question` 提取问题。
- 从 state 中按优先级读取最终回答：`final_answer`、`answer_text`、`answer`、`response`。
- 缺少问题或回答时写入 `diagram=None` 和 `diagram_error`，直接返回。
- 调用 `_decide_diagram`。
- 不需要图解时写入 `diagram=None`。
- 需要图解时调用 `_generate_diagram_by_type` 并写入 `state["diagram"]`。
- 整个节点用 `try/except` 包裹，异常只影响图解，不影响主回答。

回答节点当前返回 `answer_text`，因此 `_diagram_generate_node` 会优先读取 `answer_text` 作为最终回答。`_run_answer_model` 不需要改变 deepagent 回答逻辑。

## SSE 响应设计

正文 token 流保持现状。最后 `done` 事件新增 `resources.diagram`：

```json
{
  "session_id": "session-id",
  "resource_mode": "none",
  "resource": null,
  "resources": {
    "diagram": null,
    "video": null
  }
}
```

有图解时：

```json
{
  "resources": {
    "diagram": {
      "type": "sequence",
      "title": "TCP三次握手",
      "summary": "说明客户端和服务器建立连接的交互过程",
      "spec": {
        "actors": [],
        "messages": []
      }
    },
    "video": null
  }
}
```

不返回 `diagram_error` 给普通用户。若后续需要 debug 返回，必须受项目 debug 配置控制。

## 前端契约

本次设计只要求后端接口支持前端上传 `need_diagram`，不要求实现前端渲染组件。

`src/api/ai.ts` 的 `StreamChatParams` 增加：

```ts
need_diagram?: boolean
```

`streamChat` 将该值放入 `FormData`。`src/views/Tutor.vue` 后续可在现有开关逻辑中传入 `need_diagram`，并从 `done` 事件读取 `resources.diagram`。

## 错误处理

- 图解决策失败：记录 warning，返回不生成图解。
- 图解生成失败：记录 warning，`diagram=None`。
- Schema 校验失败：视为图解生成失败，`diagram=None`。
- `diagram_generate` 节点异常：写入 `diagram_error`，不影响 answer 保存和 `done` 事件。
- 主回答失败仍按现有错误流程处理。

## 测试计划

Schema 测试：

- `flow` / `relation` 边引用不存在时报错。
- `sequence` 消息引用不存在的 actor 时报错。
- `state` 转换引用不存在的状态时报错。
- `sequence` / `state` 支持输入输出 JSON 字段名 `"from"` / `"to"`。
- `extra="forbid"` 生效。
- title、summary、label、description 长度限制生效。

Agent 单元测试：

- `need_diagram=False` 不调用结构化生成，返回 `diagram=None`。
- `need_diagram=True` 且决策为 `sequence` 时，按 `SequenceDiagram` 生成并写入 state。
- 生成异常时不抛出，写入 `diagram=None` 和 `diagram_error`。
- 决策返回未知类型时降级为 `diagram=None`。

SSE 测试：

- 原有最终答案仍通过 `token` 事件发送。
- `done.data.resources.diagram` 在无图解时为 `null`。
- 有图解时 `done.data.resources.diagram.type` 可为 `sequence` / `compare` 等合法类型。

手动测试样例：

1. 输入“TCP 三次握手是什么？请配图解释”，`need_diagram=true`，期望 `diagram.type = "sequence"`。
2. 输入“进程和线程有什么区别？”，`need_diagram=true`，期望 `diagram.type = "compare"`。
3. 输入“Redis 是什么？”，`need_diagram=false`，期望 `diagram = null` 且回答正常。

## 风险与后续

`with_structured_output` 是否可用取决于当前 DeepSeek LangChain 封装能力。如果当前模型封装不支持结构化输出，第一版会暴露在测试或运行时日志中；后续需要切换到 JSON Prompt + Pydantic 校验兜底。本次设计先不实现兜底，以保持主路径符合结构化输出要求。

图解会增加一次或两次非流式模型调用。由于第一版默认 `need_diagram=false`，只有前端明确开启时才产生额外延迟和成本。
