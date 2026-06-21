# 全局 Agent Run 事件设计

## 目标

为智能辅导、资源生成和路径规划提供同一套后端主动消息协议。三个模块共享事件数据类型、发布器、事件总线、SSE 编码和订阅入口；业务记录、详情页面与持久化模型继续相互独立，尤其不得合并 `resource` 与 `path` 数据。

不兼容现有三套事件协议。迁移完成后直接删除旧事件类型、旧 EventBus、旧 SSE 拼装及前端旧解析逻辑。

## 运行模型

每次异步 Agent 执行对应一个全局唯一的 `run_id`。chat、resource、path 的启动接口负责创建运行并返回 `run_id` 与原有业务 ID。前端只通过以下接口订阅该次运行：

```http
GET /api/v1/ai/agent-runs/{run_id}/events
```

统一接口根据运行记录校验当前用户是否为运行所有者，不再由订阅接口理解各模块业务表。运行记录只保存路由和鉴权所需元数据，不替代任何模块的业务记录。

## 统一事件类型

```python
class AgentEvent(BaseModel):
    event_id: str
    run_id: str
    sequence: int
    module: Literal["chat", "resource", "path"]
    business_id: str
    type: Literal[
        "run.started",
        "agent.status",
        "tool.status",
        "artifact.ready",
        "content.delta",
        "run.completed",
        "run.failed",
        "heartbeat",
    ]
    status: Literal["pending", "running", "completed", "failed", "skipped"]
    activity_id: str | None = None
    agent_id: str | None = None
    title: str = ""
    summary: str = ""
    progress: int | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    elapsed_ms: int | None = None
    timestamp: float
```

`sequence` 在单次运行中严格递增，用于前端排序、去重和断线恢复。`detail` 只承载经过清洗、可向用户展示的数据，禁止包含密钥、内部提示词或无限长度的工具原始输出。

## 全局基础设施

新增 `server/app/infra/agent_events.py`，全局只维护以下职责：

- `AgentEvent`：唯一事件 Schema。
- `AgentRun`：运行元数据，包含 `run_id`、用户、模块、业务 ID、状态和序列号。
- `AgentEventBus`：按 `run_id` 发布和订阅，管理有界队列、心跳与连接清理。
- `AgentEventEmitter`：提供 `started`、`running`、`completed`、`failed`、`content_delta`、`artifact_ready` 和 `done` 方法。
- `encode_sse_event`：唯一 SSE 序列化入口。

事件发送属于观测路径。普通状态事件发送失败只记录日志，不应中断 Agent；最终完成或失败状态必须同步更新运行状态，确保前端重连后可得到终态。

## 数据流

1. 模块启动接口创建业务记录和 `AgentRun`，返回 `run_id`。
2. 前端连接统一事件接口。
3. Agent 通过请求级或任务级 `AgentEventEmitter` 发布事件。
4. EventBus 将事件广播给该 `run_id` 的订阅者。
5. 智能辅导回答 token 也使用 `content.delta`，不再保留第二条 chat 流。
6. Agent 结束时发送 `run.completed` 或 `run.failed`，SSE 发送终态后关闭。

为解决“任务先运行、前端后订阅”的竞态，EventBus 为每个活跃运行保留有界事件缓冲和最新快照。订阅时先按 `sequence` 回放缓冲，再接收实时事件。进程重启后的恢复以持久化运行终态及各模块现有业务数据为准，不新增统一业务历史表。

## 模块接入

### 智能辅导

- 工具执行、附件分析、准备状态和回答 token 全部发往统一 emitter。
- 保留 AIMessage、UserMessage、ToolMessage、工具调用记录和附件分析记录，统一事件不能替代模型上下文。
- 历史页面仍从 chat 持久化记录恢复活动卡。

### 资源生成

- DAG Agent 状态映射为 `agent.status`。
- 生成产物使用 `artifact.ready`。
- 删除 `ResourceEventBus`、`AgentEvent` 和资源 API 中的 SSE 拼装。
- 资源记录、生成详情页和资源持久化保持独立。

### 路径规划

- 规划阶段映射为 `agent.status`，规划完成使用 `run.completed`。
- 删除 `PathEvent`、`PathEventBus` 和路径 API 中的 SSE 拼装。
- 路径记录、节点详情页和路径持久化保持独立。

## 前端

新增共享事件模型及 `subscribeAgentRun(runId)`，三个模块不得自行声明另一套 SSE 类型或创建另一套解析器。

- chat 消费 `tool.status`、附件 `agent.status` 和 `content.delta`。
- resource 消费 DAG `agent.status` 与 `artifact.ready`。
- path 消费规划 `agent.status`。
- 三者共同处理运行开始、终态、失败、心跳、排序和去重。

模块展示组件可以不同；统一的是数据协议和连接管理，而不是强制三种业务使用同一个界面。

## 错误与安全

- 运行不存在或不属于当前用户时返回统一 404，避免泄露运行 ID。
- 一个用户只能订阅自己的运行。
- 慢消费者使用有界队列；超限时保留最新状态并记录告警。
- Agent 异常必须产生 `run.failed`，其 `summary` 是可展示信息，内部堆栈只写后端日志。
- `run.completed` 和 `run.failed` 是互斥终态，终态后拒绝业务事件。

## 验证标准

- 三个模块均只依赖 `app.infra.agent_events`。
- 后端只存在一个 EventBus、一个事件 Schema、一个 SSE 编码函数和一个订阅路由。
- 前端只存在一个事件数据类型和一个订阅客户端。
- chat token、工具状态、resource Agent 状态及 path 规划状态均通过同一 `run_id` 连接到达。
- `resource` 与 `path` 的记录、详情页和持久化模型没有合并。
- 旧事件名称、旧 EventBus 和旧模块订阅接口均被删除。
