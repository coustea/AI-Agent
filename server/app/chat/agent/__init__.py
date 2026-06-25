"""TutorAgent — LangGraph 驱动的辅导智能体编排器。

图结构: START → classify → [analysis_files] → [search_node] → answer_node → [diagram_node] → END

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
    build_evidence_context,
    classify_node,
    analysis_files_node,
    search_node,
    answer_node,
    diagram_node,
)
from app.chat.agent.state import TutorAgentState
from app.chat.memory.service import get_chat_memory_service
from app.chat.schemas import TutorRuntimeEvent, TutorAgentInput
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts

logger = get_logger(__name__)


# ── 图路由函数 ──


def route_after_classify(state: TutorAgentState) -> str:
    cls = state.get("classification")
    if cls is None:
        return "answer_node"
    if cls.needs_file_analysis and state.get("attachments"):
        return "analysis_files"
    if cls.needs_knowledge_search or cls.needs_web_search or cls.needs_profile or cls.needs_long_term_memory:
        return "search_node"
    return "answer_node"


def route_after_analysis(state: TutorAgentState) -> str:
    cls = state.get("classification")
    if cls and (
        cls.needs_knowledge_search
        or cls.needs_web_search
        or cls.needs_profile
        or cls.needs_long_term_memory
    ):
        return "search_node"
    return "answer_node"


def route_after_answer(state: TutorAgentState) -> str:
    cls = state.get("classification")

    if cls and cls.needs_diagram:
        return "diagram_node"

    if state.get("need_teaching_diagram") and state.get("final_answer"):
        return "diagram_node"

    return END


class TutorAgent:
    """LangGraph 驱动的辅导智能体 — 单次对话 turn 的运行时。"""

    def __init__(self, memory_service: Any | None = None) -> None:
        self.llm = get_llm()
        self.memory_service = memory_service or get_chat_memory_service()
        self._graph = self._build_graph()

    async def chat(self, input: TutorAgentInput) -> AsyncIterator[TutorRuntimeEvent]:
        """执行一次辅导对话，流式返回事件。

        ChatService 调用此方法，逐事件转发为 SSE。
        """
        event_queue: asyncio.Queue[TutorRuntimeEvent] = asyncio.Queue()
        initial_state: TutorAgentState = {
            "user_id": input.user_id,
            "session_id": input.session_id,
            "question": input.question,
            "attachments": input.attachments,
            "enable_web_search": input.enable_web_search,
            "need_teaching_diagram": input.need_teaching_diagram,
            "history_messages": input.history_messages,
            "session_summary": input.session_summary,
            "attachment_context": "",
            "attachment_analyses": [],
            "evidence": [],
            "sources": [],
            "tool_invocations": [],
            "stream_events": [],
            "event_queue": event_queue,
            "errors": [],
            "final_answer": "",
            "diagram_result": None,
            "_search_attempted": False,
        }

        yield TutorRuntimeEvent(type="message_start", payload={}, sequence=0, timestamp=time.time())

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

            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield event

            final_state = await sentinel_task

            yield TutorRuntimeEvent(
                type="final",
                payload={
                    "final_answer": final_state.get("final_answer", ""),
                    "diagram_result": final_state.get("diagram_result"),
                    "sources": final_state.get("sources", []),
                    "tool_invocations": final_state.get("tool_invocations", []),
                    "attachment_analyses": final_state.get("attachment_analyses", []),
                    "errors": final_state.get("errors", []),
                },
                sequence=9999,
                timestamp=time.time(),
            )
        except Exception as exc:
            logger.exception("[TutorAgent] graph execution failed")
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
    # Event / persistence helpers
    # ------------------------------------------------------------------

    async def _emit_event(
        self,
        state: TutorAgentState,
        event: TutorRuntimeEvent,
        *,
        turn_event_type: str | None = None,
        persist: bool = True,
    ) -> list[TutorRuntimeEvent]:
        """Emit a stream event to the SSE queue.

        Returns a single-element list containing the event, for the caller
        to return as ``{"stream_events": [event]}`` — the operator.add reducer
        on stream_events will automatically append it to the accumulated list.
        """
        queue = state.get("event_queue")
        if queue is not None:
            await queue.put(event)
        return [event]

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        workflow = StateGraph(TutorAgentState)

        # 使用 partial 绑定节点函数的额外参数，避免重复定义 lambda
        workflow.add_node("classify",       partial(classify_node,       self, llm=self.llm, prompts=prompts))
        workflow.add_node("analysis_files", partial(analysis_files_node, self))
        workflow.add_node("search_node",    partial(search_node,         self, llm=self.llm, prompts=prompts, memory_service=self.memory_service))
        workflow.add_node("answer_node",    partial(answer_node,         self, llm=self.llm, prompts=prompts))
        workflow.add_node("diagram_node",   partial(diagram_node,        self))

        workflow.add_edge(START, "classify")
        workflow.add_conditional_edges("classify",       route_after_classify)
        workflow.add_conditional_edges("analysis_files", route_after_analysis)
        workflow.add_edge("search_node", "answer_node")
        workflow.add_conditional_edges("answer_node",    route_after_answer)
        workflow.add_edge("diagram_node", END)

        return workflow.compile()
