# Chat Agent Tool Status Event Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用自研 `ToolExcute` 统一发送工具生命周期事件，并让智能辅导前端在回答前显示一条简洁的实时工具状态。

**Architecture:** `ToolExcute` 仅暴露通用异步生命周期回调，不依赖 Chat。Chat 请求级工厂把工具名和安全参数转换为 `agent_status` SSE；前端消费该单一事件、覆盖当前提示，并在答案开始或流结束时清理。Path 不传回调，Resource 不改动。

**Tech Stack:** Python 3.13、FastAPI、Pydantic、LangChain `ChatOpenAI`（仅模型客户端）、Vue 3、TypeScript、SSE

---

### Task 1: ToolExcute 生命周期回调

**Files:**
- Modify: `server/app/infra/tool_excute.py`
- Modify: `server/app/infra/llm.py`

- [ ] **Step 1: 定义基础设施事件契约**

在 `tool_excute.py` 增加不依赖 Chat 的类型，并让构造函数接收可选回调：

```python
ToolRuntimeEvent = dict[str, Any]
ToolEventHandler = Callable[[ToolRuntimeEvent], Awaitable[None]]

def __init__(
    self,
    model: Any,
    tools: Sequence[Tool] | None = None,
    event_handler: ToolEventHandler | None = None,
) -> None:
    self.model = model
    self._event_handler = event_handler
    self._tools: dict[str, Tool] = {}
```

- [ ] **Step 2: 在唯一执行入口报告生命周期**

参数校验通过后发送 `running`；handler 正常返回后发送 `done`；handler 抛错时发送 `failed` 后原样抛出：

```python
validated_args = validated.model_dump()
await self._emit_event("running", name, validated_args)
try:
    result = await tool.handler(**validated_args)
except Exception:
    await self._emit_event("failed", name, validated_args)
    raise
await self._emit_event("done", name, validated_args)
return result
```

事件回调自身失败只写日志，不得阻断工具业务执行。

- [ ] **Step 3: 扩展 Llm 工厂但保留 ChatOpenAI 调用方式**

`create_tool_excute()` 增加 `event_handler` 参数并传给 `ToolExcute`；不得引入 `bind_tools()` 或 LangChain 工具类型：

```python
def create_tool_excute(
    self,
    tools: list[Tool] | None = None,
    event_handler: ToolEventHandler | None = None,
) -> ToolExcute:
    return ToolExcute(self.model, tools, event_handler=event_handler)
```

### Task 2: Chat 统一生成 agent_status

**Files:**
- Modify: `server/app/chat/events.py`
- Modify: `server/app/chat/tool_executor.py`
- Modify: `server/app/chat/tools/profile.py`
- Modify: `server/app/chat/tools/memory.py`
- Modify: `server/app/chat/tools/knowledge.py`
- Modify: `server/app/chat/agent/nodes.py`

- [ ] **Step 1: 用单一状态格式化器替换旧事件辅助函数**

删除 `emit_tool_start()`、`emit_tool_done()`。`events.py` 只负责将工具生命周期转换为安全 UI 文案：

```python
def build_agent_status_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    status = str(event.get("status") or "running")
    tool_name = str(event.get("tool_name") or "")
    arguments = event.get("arguments") if isinstance(event.get("arguments"), Mapping) else {}
    return {
        "stage": "tool_running",
        "status": status,
        "tool_name": tool_name,
        "message": _tool_status_message(tool_name, arguments, status),
    }
```

查询、URL、关键词预览最多 50 个字符；不得包含 `reason`、用户 ID、异常文本或工具结果。

- [ ] **Step 2: 在请求级工具工厂连接事件流**

`build_tutor_tool_excute()` 创建闭包，把 `ToolExcute` 回调转换为 `ChatStreamEvent(type="agent_status", ...)`：

```python
async def _emit_runtime_status(event: ToolRuntimeEvent) -> None:
    if emit_event is None:
        return
    await emit_event(
        ChatStreamEvent(
            type="agent_status",
            payload=build_agent_status_payload(event),
            sequence=seq_start,
        )
    )

return llm.create_tool_excute(tools, event_handler=_emit_runtime_status)
```

- [ ] **Step 3: 删除分散工具事件与兼容参数**

搜索和网页包装器只捕获业务异常并返回现有失败文本。画像、记忆、知识库工厂删除 `emit_event`、`seq_start` 参数及旧事件调用。更新所有调用点，不保留别名、转发参数或旧 `tool_start` / `tool_done` 发送路径。

- [ ] **Step 4: 清理节点注释**

更新 `_execute_single_tool()` 注释，明确工具状态由 `ToolExcute` 回调发出；Evidence、工具消息和 invocation 持久化流程保持不变。

### Task 3: 后端 SSE 公共契约

**Files:**
- Modify: `server/app/chat/schemas/agent.py`
- Modify: `server/app/chat/service.py`

- [ ] **Step 1: 替换事件类型**

从 `ChatStreamEventType` 删除 `tool_start`、`tool_done`，加入唯一类型 `agent_status`。

- [ ] **Step 2: 保持 SSE 事件名不变**

删除旧映射并增加：

```python
"agent_status": "agent_status",
```

未知内部事件仍按现有策略处理，本次不增加任何旧事件兼容分支。

### Task 4: 前端显示当前工具状态

**Files:**
- Modify: `src/features/chat/views/Tutor.vue`

- [ ] **Step 1: 提取状态设置与清理函数**

在脚本区增加局部函数，避免首次订阅与恢复订阅逻辑漂移：

```ts
type AgentStatusPayload = {
  stage?: string
  status?: 'running' | 'done' | 'failed'
  tool_name?: string
  message?: string
}

function applyAgentStatus(msg: ChatMsg | undefined, payload: AgentStatusPayload) {
  if (!msg) return
  msg.searchStage = payload.stage || 'tool_running'
  msg.searchMessage = payload.message || '正在调用工具...'
}

function clearAgentStatus(msg: ChatMsg | undefined) {
  if (!msg) return
  msg.searchStage = undefined
  msg.searchMessage = undefined
}
```

- [ ] **Step 2: 两条 SSE 订阅路径统一消费 agent_status**

在恢复订阅和新建流的 `onEvent` 中处理 `evt.event === 'agent_status'`，调用 `applyAgentStatus()`；删除旧 `tool_start`、`tool_done` 分支。每次事件直接覆盖上一条，不建立时间线或历史数组。

- [ ] **Step 3: 在回答开始与终态清理状态**

两个 `onChunk` 在入队前调用 `clearAgentStatus()`。两个 `onDone`、`onError`、`done` 事件和 diagram 接管展示时也调用同一清理函数，确保状态不会残留。

### Task 5: 源代码验证与 Claude Code 测试提示词

**Files:**
- No test files modified

- [ ] **Step 1: 扫描旧工具事件零残留**

Run:

```bash
rg -n "tool_start|tool_done|emit_tool_start|emit_tool_done" server/app src
```

Expected: 无生产代码匹配。

- [ ] **Step 2: 后端编译检查**

Run: `cd server && uv run python -m compileall -f app`

Expected: exit code 0。

- [ ] **Step 3: 运行现有 Chat 定向测试**

Run: `cd server && uv run pytest tests/chat/ -q --ignore=tests/chat/test_agent_single_module_refactor.py --ignore=tests/chat/test_onboarding_api.py --ignore=tests/chat/test_reasoning_agent.py`

Expected: 除仍引用已删除旧接口的历史测试外，其余通过；不为旧测试恢复兼容代码。

- [ ] **Step 4: 前端构建**

Run: `npm run build`

Expected: `vue-tsc` 与 Vite build 均成功。

- [ ] **Step 5: 交付 Claude Code 测试提示词**

最终回复附上提示词，要求 Claude Code 只新增测试，覆盖 `ToolExcute` 的 running/done/failed 回调、回调异常隔离、Chat `agent_status` SSE 映射、前端状态覆盖和首 token 清理；明确不得修改生产代码来迁就旧 `tool_start` / `tool_done` 契约。
