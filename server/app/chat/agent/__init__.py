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
from typing import Any, AsyncIterator

from langgraph.graph import END, START, StateGraph

from app.chat.agent.background import run_background_memory_jobs
from app.chat.agent.nodes import (
    classify_node,
    analysis_files_node,
    search_node,
    answer_node,
    diagram_node,
    build_evidence_context,
)
from app.chat.agent.routing import (
    route_after_classify,
    route_after_analysis,
    route_after_search,
    route_after_answer,
)
from app.chat.agent.state import TutorAgentState
from app.chat.memory.service import get_chat_memory_service
from app.chat.schemas import TutorRuntimeEvent, TutorAgentInput
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts

logger = get_logger(__name__)


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
            "turn_id": input.turn_id,
            "user_message_id": input.user_message_id,
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
        try:
            graph_task = asyncio.create_task(self._graph.ainvoke(initial_state))

            while True:
                if graph_task.done() and event_queue.empty():
                    break
                get_event_task = asyncio.create_task(event_queue.get())
                done, pending = await asyncio.wait(
                    {graph_task, get_event_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if get_event_task in done:
                    yield get_event_task.result()
                else:
                    get_event_task.cancel()
                    await asyncio.gather(get_event_task, return_exceptions=True)
                for task in pending:
                    if task is not graph_task:
                        task.cancel()

            final_state = await graph_task

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
        """Emit a stream event to the SSE queue and optionally persist it.

        Returns a single-element list containing the event, for the caller
        to return as ``{"stream_events": [event]}`` — the operator.add reducer
        on stream_events will automatically append it to the accumulated list.
        """
        queue = state.get("event_queue")
        if queue is not None:
            await queue.put(event)

        if persist:
            await self._persist_turn_event(
                state,
                turn_event_type or self._default_turn_event_type(event.type),
                event.payload,
            )
        return [event]

    @staticmethod
    def _default_turn_event_type(event_type: str) -> str:
        return event_type.replace("_", ".")

    async def _persist_turn_event(
        self,
        state: TutorAgentState,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        turn_id = state.get("turn_id")
        if not turn_id:
            return
        try:
            await self.memory_service.append_turn_event(
                user_id=state.get("user_id", 0),
                session_id=state.get("session_id", ""),
                turn_id=turn_id,
                event_type=event_type,
                payload=payload or {},
            )
        except Exception as exc:
            logger.warning("[TutorAgent] persist turn event failed: %s", exc)

    async def run_background_memory_jobs(
        self,
        *,
        user_id: int,
        session_id: str,
        turn_id: int,
        user_message: str,
        assistant_reply: str,
        turn_index: int = 0,
    ) -> None:
        """后台记忆管线 — 委托给 background.py。"""
        await run_background_memory_jobs(
            self.memory_service,
            user_id=user_id,
            session_id=session_id,
            turn_id=turn_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
            turn_index=turn_index,
        )

    async def run_post_turn_jobs(self, **kwargs) -> None:
        """Compatibility wrapper — delegates to run_background_memory_jobs."""
        await self.run_background_memory_jobs(**kwargs)

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        workflow = StateGraph(TutorAgentState)

        # 添加节点 — 委托给 nodes.py 中的实现
        workflow.add_node("classify", self._classify_node_wrapper)
        workflow.add_node("analysis_files", self._analysis_files_node_wrapper)
        workflow.add_node("search_node", self._search_node_wrapper)
        workflow.add_node("answer_node", self._answer_node_wrapper)
        workflow.add_node("diagram_node", self._diagram_node_wrapper)

        workflow.add_edge(START, "classify")
        workflow.add_conditional_edges("classify", self._route_after_classify)
        workflow.add_conditional_edges("analysis_files", self._route_after_analysis)
        workflow.add_conditional_edges("search_node", self._route_after_search)
        workflow.add_conditional_edges("answer_node", self._route_after_answer)
        workflow.add_edge("diagram_node", END)

        return workflow.compile()

    # ------------------------------------------------------------------
    # Node wrappers — 委托给 nodes.py
    # ------------------------------------------------------------------

    async def _classify_node_wrapper(self, state: TutorAgentState) -> dict:
        return await classify_node(self, state, self.llm, prompts)

    async def _analysis_files_node_wrapper(self, state: TutorAgentState) -> dict:
        return await analysis_files_node(self, state)

    async def _search_node_wrapper(self, state: TutorAgentState) -> dict:
        return await search_node(self, state, self.llm, prompts, self.memory_service)

    async def _answer_node_wrapper(self, state: TutorAgentState) -> dict:
        return await answer_node(self, state, self.llm, prompts)

    async def _diagram_node_wrapper(self, state: TutorAgentState) -> dict:
        return await diagram_node(self, state)

    # ------------------------------------------------------------------
    # Routing functions — 委托给 routing.py
    # ------------------------------------------------------------------

    @staticmethod
    def _route_after_classify(state: TutorAgentState) -> str:
        return route_after_classify(state)

    @staticmethod
    def _route_after_analysis(state: TutorAgentState) -> str:
        return route_after_analysis(state)

    @staticmethod
    def _route_after_search(state: TutorAgentState) -> str:
        return route_after_search(state)

    @staticmethod
    def _route_after_answer(state: TutorAgentState) -> str:
        return route_after_answer(state)
