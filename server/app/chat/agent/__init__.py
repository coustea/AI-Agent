"""TutorAgent — LangGraph 驱动的辅导智能体编排器。

图结构（重构后）: START → preprocess → react_node → END

职责边界:
  - TutorAgent: 推理编排、流式输出、节点级持久化
  - ChatService: 会话/turn 生命周期、历史构建、最终消息持久化、SSE 转发

节点实现委托给 nodes.py，后台任务委托给 background.py。
"""

from __future__ import annotations

import asyncio
import time
from functools import partial
from typing import Any, AsyncIterator

from langgraph.graph import END, START, StateGraph

from app.chat.agent.nodes import (
    preprocess_node,
    react_node,
)
from app.chat.agent.state import TutorAgentState
from app.chat.memory.service import get_chat_memory_service
from app.chat.schemas import TutorRuntimeEvent, TutorAgentInput
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts

logger = get_logger(__name__)


# TutorAgent：基于 LangGraph 的辅导智能体，负责单条用户消息的推理编排与流式输出
class TutorAgent:
    """LangGraph 驱动的辅导智能体 — 处理一条用户消息。"""

    # 初始化 LLM、记忆服务并构建推理图
    def __init__(self, memory_service: Any | None = None) -> None:
        self.llm = get_llm()
        self.memory_service = memory_service or get_chat_memory_service()
        self._graph = self._build_graph()

    # 执行一次辅导对话，以异步迭代器形式流式返回运行时事件（供 ChatService 转发为 SSE）
    async def chat(self, input: TutorAgentInput) -> AsyncIterator[TutorRuntimeEvent]:
        """执行一次辅导对话，流式返回事件。

        ChatService 调用此方法，逐事件转发为 SSE。
        """
        event_queue: asyncio.Queue[TutorRuntimeEvent] = asyncio.Queue()
        initial_state: TutorAgentState = {
            "user_id": input.user_id,
            "username": input.username,
            "session_id": input.session_id,
            "user_message_id": input.user_message_id,
            "question": input.question,
            "attachments": input.attachments,
            "enable_web_search": input.enable_web_search,
            "need_teaching_diagram": input.need_teaching_diagram,
            "voice_mode": input.voice_mode,
            "history_messages": input.history_messages,
            "session_summary": input.session_summary,
            "attachment_context": "",
            "messages": [],
            "event_queue": event_queue,
            "stream_events": [],
            "tool_invocations": [],
            "sources": [],
            "errors": [],
            "final_answer": "",
            "diagram_result": None,
        }

        # 发送对话开始事件
        yield TutorRuntimeEvent(type="message_start", payload={}, sequence=0, timestamp=time.time())

        # 创建后台图任务与哨兵任务（图结束后向队列发送结束哨兵）
        graph_task: asyncio.Task[Any] | None = None
        sentinel_task: asyncio.Task[Any] | None = None
        try:
            graph_task = asyncio.create_task(self._graph.ainvoke(initial_state))

            async def _graph_with_sentinel() -> Any:
                try:
                    return await graph_task
                finally:
                    await event_queue.put(None)

            sentinel_task = asyncio.create_task(_graph_with_sentinel())

            # 从事件队列消费事件并逐个 yield 给调用方，遇到 None 哨兵则结束
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield event

            # 图执行完成，获取最终状态并发送 final 事件
            final_state = await sentinel_task

            yield TutorRuntimeEvent(
                type="final",
                payload={
                    "final_answer": final_state.get("final_answer", ""),
                    "diagram_result": final_state.get("diagram_result"),
                    "sources": final_state.get("sources", []),
                    "tool_invocations": final_state.get("tool_invocations", []),
                    "errors": final_state.get("errors", []),
                },
                sequence=9999,
                timestamp=time.time(),
            )
        # 捕获图执行异常，取消未完成任务并向调用方发送 error 事件
        except Exception as exc:
            logger.exception("[TutorAgent] graph 执行失败")
            if graph_task is not None and not graph_task.done():
                graph_task.cancel()
            if sentinel_task is not None and not sentinel_task.done():
                sentinel_task.cancel()
            yield TutorRuntimeEvent(
                type="error",
                payload={"error": str(exc)},
                sequence=9999,
                timestamp=time.time(),
            )

    # ------------------------------------------------------------------
    # 事件 / 持久化辅助方法
    # ------------------------------------------------------------------

    # 向 SSE 队列发送事件，可选将活动状态持久化到记忆服务
    async def _emit_event(
        self,
        state: TutorAgentState,
        event: TutorRuntimeEvent,
        *,
        persist: bool = True,
    ) -> list[TutorRuntimeEvent]:
        """向 SSE 队列发送流事件。

        返回包含该事件的单元素列表，供调用者以 ``{"stream_events": [event]}`` 形式返回——
        stream_events 上的 operator.add reducer 会自动将其追加到累积列表中。
        """
        if persist and event.type == "agent_status":
            try:
                await self.memory_service.upsert_activity(
                    user_id=state.get("user_id", 0),
                    session_id=state.get("session_id", ""),
                    user_message_id=state.get("user_message_id", 0),
                    payload=event.payload,
                )
            except Exception as exc:
                logger.warning("[TutorAgent] 持久化活动失败: %s", exc)
        queue = state.get("event_queue")
        if queue is not None:
            await queue.put(event)
        return [event]

    # ------------------------------------------------------------------
    # 图构建
    # ------------------------------------------------------------------

    # 构建 LangGraph 状态图：START → preprocess → react_node → END
    def _build_graph(self) -> Any:
        workflow = StateGraph(TutorAgentState)

        # 使用 partial 绑定节点函数的额外参数（agent 实例、llm、prompts、记忆服务）
        workflow.add_node("preprocess", partial(preprocess_node, self))
        workflow.add_node("react_node", partial(react_node, self, llm=self.llm, prompts=prompts, memory_service=self.memory_service))

        # 定义图的边：从开始依次经过预处理节点与 ReAct 节点，最终结束
        workflow.add_edge(START, "preprocess")
        workflow.add_edge("preprocess", "react_node")
        workflow.add_edge("react_node", END)

        # 编译状态图并返回可执行对象
        return workflow.compile()
