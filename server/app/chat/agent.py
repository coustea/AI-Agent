"""TutorAgent — LangGraph 驱动的辅导智能体。

图结构: START → classify → [analysis_files] → [search_node] → answer_node → [diagram_node] → END

每个节点产生 ChatStreamEvent，通过 chat() 方法以 AsyncIterator 形式返回给 ChatService。
ChatService 负责将内部事件转换为 SSE 格式推送给前端。

职责边界:
  - TutorAgent: 推理编排、工具调用、流式输出、节点级持久化
  - ChatService: 会话/turn 生命周期、历史构建、最终消息持久化、SSE 转发
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, AsyncIterator, TypedDict
from uuid import uuid4

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.chat.memory.service import get_chat_memory_service
from app.chat.schemas import (
    ChatStreamEvent,
    ClassificationResult,
    Evidence,
    EvidenceSet,
    TutorToolCall,
    TutorTurnContext,
    TutorAgentInput,
)
from app.chat.stages import TeachingDiagramGenerator
from app.chat.streaming import ResponseStreamer, SafetyBufferedResponseStreamer
from app.chat.tool_execute import TutorToolExecutor, TutorToolRegistry
from app.chat.utils import normalize_message_content
from app.chat.utils.files import analyze_documents
from app.chat.utils.vision import VisionService
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.profile.service import get_profile_service

logger = get_logger(__name__)

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _current_date_text() -> str:
    return datetime.now().date().isoformat()


# ===================================================================
# Graph State
# ===================================================================


class TutorAgentState(TypedDict, total=False):
    """LangGraph 图状态 — 各节点通过返回 dict 更新部分字段。"""

    # 请求
    user_id: int
    session_id: str
    turn_id: int
    user_message_id: int | None
    question: str
    attachments: list[str]
    enable_web_search: bool
    need_teaching_diagram: bool

    # 上下文
    history_messages: list[AnyMessage]
    session_summary: str

    # 分类
    classification: ClassificationResult

    # 附件
    attachment_context: str
    attachment_analyses: list[dict[str, Any]]

    # 证据
    evidence: list[dict[str, Any]]
    sources: list[dict[str, Any]]

    # 运行时
    tool_invocations: list[dict[str, Any]]
    stream_events: list[ChatStreamEvent]
    event_queue: asyncio.Queue
    errors: list[str]

    # 输出
    final_answer: str
    diagram_result: dict[str, Any] | None


# ===================================================================
# TutorAgent
# ===================================================================


class TutorAgent:
    """LangGraph 驱动的辅导智能体 — 单次对话 turn 的运行时。"""

    def __init__(self, memory_service: Any | None = None) -> None:
        self.llm = get_llm()
        self.memory_service = memory_service or get_chat_memory_service()
        self._graph = self._build_graph()

    async def chat(self, input: TutorAgentInput) -> AsyncIterator[ChatStreamEvent]:
        """执行一次辅导对话，流式返回事件。

        ChatService 调用此方法，逐事件转发为 SSE。
        """
        event_queue: asyncio.Queue[ChatStreamEvent] = asyncio.Queue()
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
        }

        yield ChatStreamEvent(type="message_start", payload={}, sequence=0, timestamp=time.time())

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

            yield ChatStreamEvent(
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
            yield ChatStreamEvent(
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
        event: ChatStreamEvent,
        events: list[ChatStreamEvent] | None = None,
        *,
        turn_event_type: str | None = None,
        persist: bool = True,
    ) -> list[ChatStreamEvent]:
        updated = list(events if events is not None else state.get("stream_events", []))
        updated.append(event)

        queue = state.get("event_queue")
        if queue is not None:
            await queue.put(event)

        if persist:
            await self._persist_turn_event(
                state,
                turn_event_type or self._default_turn_event_type(event.type),
                event.payload,
            )
        return updated

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

    async def run_post_turn_jobs(
        self,
        *,
        user_id: int,
        session_id: str,
        turn_id: int,
        user_message: str,
        assistant_reply: str,
        turn_index: int = 0,
    ) -> None:
        """在最终回答落盘后调度会话压缩、长期记忆和画像更新。

        默认每轮最多运行一个重 LLM 任务：压缩 > 长期记忆 > 画像。
        """
        state: TutorAgentState = {
            "user_id": user_id,
            "session_id": session_id,
            "turn_id": turn_id,
            "event_queue": asyncio.Queue(),
        }
        await self._persist_turn_event(
            state,
            "memory.update.start",
            {"stage": "post_turn", "turn_index": turn_index},
        )

        job = "none"
        status = "skipped"
        payload: dict[str, Any] = {}
        try:
            counters = await self.memory_service.update_post_turn_counters(
                user_id=user_id,
                session_id=session_id,
                turn_id=turn_id,
                user_message=user_message,
                assistant_reply=assistant_reply,
            )
            payload["counters"] = counters

            summary_block = await self.memory_service.compress_session(
                user_id=user_id,
                session_id=session_id,
            )
            if summary_block is not None:
                job = "compression"
                status = "completed"
                payload["summary_block_id"] = getattr(summary_block, "id", None)
            else:
                should_ltm, ltm_schedule = await self.memory_service.should_update_long_term_memory(
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_message,
                    assistant_reply=assistant_reply,
                )
                payload["ltm_schedule"] = ltm_schedule
                if should_ltm:
                    job = "long_term_memory"
                    ltm_result = await self.memory_service.update_long_term_memory(
                        user_id=user_id,
                        session_id=session_id,
                        user_message=user_message,
                        assistant_reply=assistant_reply,
                        signal_detected=bool(ltm_schedule.get("signal_detected")),
                    )
                    status = "completed" if ltm_result.get("updated") else "analyzed" if ltm_result.get("analyzed") else "skipped"
                    payload["ltm_result"] = ltm_result
                else:
                    import re
                    profile_service = get_profile_service()

                    turn_text = f"{user_message}\n{assistant_reply}"

                    global_patterns = [
                        r"(喜欢|习惯|偏好|擅长|感兴趣|反感|讨厌|更愿意|认知|风格|学习方式)",
                        r"(节奏|速度|时间|每天|太快|太慢|稍微|快一点|慢一点|进度|频繁)",
                        r"(实践|动手|写代码|做题|编程|实验|实战|练习|编码|Debug)",
                    ]
                    course_patterns = [
                        r"(这门课|操作系统|数据库|计网|网络|计组|算法|数据结构|高数|线代)",
                        r"(进程|线程|锁|事务|索引|内存|虚拟内存|调度|TCP|IP|握手|矩阵|导数|概念)",
                        r"(薄弱|搞错|出错|卡住|记不住|混淆|搞不清|老是错|不会做|不懂|理解不了)",
                        r"(基础|掌握|熟悉|了解|懂了|不明白|难度|简单|困难|稍微深点)",
                    ]

                    should_update_global = any(re.search(p, turn_text) for p in global_patterns)
                    should_update_course = any(re.search(p, turn_text) for p in course_patterns)
                    logger.info("[TutorAgent] 画像更新检查: should_update_global=%s should_update_course=%s",
                                 should_update_global, should_update_course)

                    global_updated = False
                    course_updated = False

                    if should_update_global:
                        res_global = await profile_service.update_global_from_tutoring(
                            user_id=user_id,
                            session_id=session_id,
                        )
                        global_updated = res_global.get("profile_updated", False)
                        logger.info("[TutorAgent] 全局画像更新完成: global_updated=%s", global_updated)

                    if should_update_course:
                        global_profile = await profile_service.get_or_create_global_profile(user_id=user_id)
                        profile_json = global_profile.profile_json or {}
                        active_courses = profile_json.get("base_info", {}).get("courses", [])
                        course_name = ""
                        if active_courses and isinstance(active_courses, list):
                            first_course = active_courses[0]
                            if isinstance(first_course, dict):
                                course_name = first_course.get("course", "")
                            elif isinstance(first_course, str):
                                course_name = first_course

                        if course_name:
                            res_course = await profile_service.update_course_from_tutoring(
                                user_id=user_id,
                                session_id=session_id,
                                course_name=course_name,
                            )
                            course_updated = res_course.get("profile_updated", False)
                            logger.info("[TutorAgent] 课程画像更新完成: course_name=%s course_updated=%s",
                                         course_name, course_updated)
                            
                    job = "learner_profile"
                    status = "completed" if (global_updated or course_updated) else "skipped"
                    payload["profile_updated"] = global_updated or course_updated
                    payload["global_updated"] = global_updated
                    payload["course_updated"] = course_updated

            await self._persist_turn_event(
                state,
                "memory.update.done",
                {"job": job, "status": status, **payload},
            )
        except Exception as exc:
            logger.error("[TutorAgent] post-turn jobs failed: %s", exc)
            await self._persist_turn_event(
                state,
                "memory.update.done",
                {"job": job, "status": "error", "error": str(exc), **payload},
            )

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        workflow = StateGraph(TutorAgentState)

        workflow.add_node("classify", self._classify_node)
        workflow.add_node("analysis_files", self._analysis_files_node)
        workflow.add_node("search_node", self._search_node)
        workflow.add_node("answer_node", self._answer_node)
        workflow.add_node("diagram_node", self._diagram_node)

        workflow.add_edge(START, "classify")
        workflow.add_conditional_edges("classify", self._route_after_classify)
        workflow.add_conditional_edges("analysis_files", self._route_after_analysis)
        workflow.add_conditional_edges("search_node", self._route_after_search)
        workflow.add_conditional_edges("answer_node", self._route_after_answer)
        workflow.add_edge("diagram_node", END)

        return workflow.compile()

    # ------------------------------------------------------------------
    # Routing functions
    # ------------------------------------------------------------------

    @staticmethod
    def _route_after_classify(state: TutorAgentState) -> str:
        cls = state.get("classification")
        if cls is None:
            return "answer_node"
        if cls.needs_file_analysis and state.get("attachments"):
            return "analysis_files"
        if cls.needs_knowledge_search or cls.needs_web_search or cls.needs_profile or cls.needs_long_term_memory or cls.needs_recent_evaluation:
            return "search_node"
        return "answer_node"

    @staticmethod
    def _route_after_analysis(state: TutorAgentState) -> str:
        cls = state.get("classification")
        if cls and (cls.needs_knowledge_search or cls.needs_web_search or cls.needs_profile or cls.needs_long_term_memory or cls.needs_recent_evaluation):
            return "search_node"
        return "answer_node"

    @staticmethod
    def _route_after_search(state: TutorAgentState) -> str:
        return "answer_node"

    @staticmethod
    def _route_after_answer(state: TutorAgentState) -> str:
        cls = state.get("classification")
        if cls and cls.needs_diagram:
            return "diagram_node"
        if state.get("need_teaching_diagram") and state.get("final_answer"):
            return "diagram_node"
        return END

    # ------------------------------------------------------------------
    # Node: classify
    # ------------------------------------------------------------------

    async def _classify_node(self, state: TutorAgentState) -> dict:
        question = state.get("question", "")
        attachments = state.get("attachments", [])
        summary = state.get("session_summary", "")

        has_attachments = bool(attachments)
        has_web_search = state.get("enable_web_search", False)
        has_diagram = state.get("need_teaching_diagram", False)

        prompt = (
            f"学生问题: {question}\n"
            f"附件数量: {len(attachments)}\n"
            f"会话摘要: {summary[:500] if summary else '无'}\n"
            f"当前日期: {_current_date_text()}\n"
            f"用户请求联网搜索: {has_web_search}\n"
            f"用户请求教学图解: {has_diagram}\n\n"
            "请先判断该问题是否能仅凭稳定的通用知识可靠回答。"
            "如果问题依赖最新、实时、未来、官方发布、具体试题、具体来源、具体数据，"
            "或者你不能确信答案在当前日期仍然准确，应将 needs_web_search 设为 true。"
        )

        try:
            classify_system_prompt = prompts.get("chat").get("classify_system") or "你是辅导分类器。"
            classification = await self.llm.ainvoke_json(
                ClassificationResult,
                [
                    SystemMessage(content=classify_system_prompt),
                    HumanMessage(content=prompt),
                ],
                temperature=0.1,
            )
        except Exception as exc:
            logger.warning("[TutorAgent] classify LLM failed, using defaults: %s", exc)
            classification = ClassificationResult(
                needs_file_analysis=has_attachments,
                needs_knowledge_search=False,
                needs_web_search=has_web_search,
                needs_diagram=has_diagram,
            )

        if has_web_search and not classification.needs_web_search:
            classification = classification.model_copy(update={"needs_web_search": True})

        event = ChatStreamEvent(
            type="classify_done",
            payload=classification.model_dump(),
            sequence=1,
            timestamp=time.time(),
        )
        events = await self._emit_event(state, event, turn_event_type="classify.done")

        return {
            "classification": classification,
            "stream_events": events,
        }

    # ------------------------------------------------------------------
    # Node: analysis_files
    # ------------------------------------------------------------------

    async def _analysis_files_node(self, state: TutorAgentState) -> dict:
        attachments = state.get("attachments", [])
        user_id = state.get("user_id", 0)
        session_id = state.get("session_id", "")

        start_event = ChatStreamEvent(type="file_analysis_start", payload={"count": len(attachments)}, sequence=2, timestamp=time.time())
        events = await self._emit_event(state, start_event, turn_event_type="file.analysis.start")

        image_urls, file_urls = [], []
        for url in attachments:
            ext = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""
            if ext in IMAGE_EXTENSIONS:
                image_urls.append(url)
            else:
                file_urls.append(url)

        parts: list[str] = []

        if image_urls:
            try:
                vision_result = await VisionService().analyze_images(
                    image_urls[:5],
                    "请详细分析这些图片中的文字、题目、图表和关键信息，并用中文总结。",
                )
                analysis_text = str(vision_result.get("analysis_text") or "").strip()
                if analysis_text:
                    parts.append(f"[图片] {analysis_text}")
            except Exception as exc:
                logger.warning("[TutorAgent] image analysis failed: %s", exc)

        if file_urls:
            try:
                analysis = await analyze_documents(
                    current_user_id=user_id,
                    file_urls=file_urls[:5],
                    question="请分析这些文档",
                )
                summary = str(analysis.get("analysis_text") or "").strip()
                if summary:
                    parts.append(f"[文档] {summary}")
            except Exception as exc:
                logger.warning("[TutorAgent] document analysis failed: %s", exc)

        attachment_context = "\n".join(parts)
        attachment_analyses: list[dict[str, Any]] = []
        if image_urls and any(part.startswith("[图片]") for part in parts):
            image_summary = "\n".join(part.removeprefix("[图片] ").strip() for part in parts if part.startswith("[图片]"))
            attachment_analyses.append({
                "file_url": image_urls[0],
                "file_name": image_urls[0].split("/")[-1],
                "analysis_type": "image",
                "summary_text": image_summary,
                "structured_json": {"file_urls": image_urls},
            })
        if file_urls and any(part.startswith("[文档]") for part in parts):
            document_summary = "\n".join(part.removeprefix("[文档] ").strip() for part in parts if part.startswith("[文档]"))
            attachment_analyses.append({
                "file_url": file_urls[0],
                "file_name": file_urls[0].split("/")[-1],
                "analysis_type": "document",
                "summary_text": document_summary,
                "structured_json": {"file_urls": file_urls},
            })

        done_event = ChatStreamEvent(
            type="file_analysis_done",
            payload={"context_length": len(attachment_context)},
            sequence=3,
            timestamp=time.time(),
        )
        events = await self._emit_event(state, done_event, events, turn_event_type="file.analysis.done")

        return {
            "attachment_context": attachment_context,
            "attachment_analyses": attachment_analyses,
            "stream_events": events,
        }

    # ------------------------------------------------------------------
    # Node: search_node
    # ------------------------------------------------------------------

    async def _search_node(self, state: TutorAgentState) -> dict:
        cls = state.get("classification")
        question = state.get("question", "")
        user_id = state.get("user_id", 0)
        session_id = state.get("session_id", "")
        attachments = state.get("attachments", [])
        enable_web_search = state.get("enable_web_search", False)
        need_diagram = state.get("need_teaching_diagram", False)

        turn_context = TutorTurnContext(
            user_id=user_id,
            session_id=session_id,
            user_input=question,
            attachments=attachments,
            enable_web_search=enable_web_search,
            need_teaching_diagram=need_diagram,
        )

        registry = TutorToolRegistry(request=turn_context)
        executor = TutorToolExecutor(request=turn_context, registry=registry)

        evidence_list: list[dict[str, Any]] = list(state.get("evidence", []))
        tool_invocations: list[dict[str, Any]] = list(state.get("tool_invocations", []))
        events = list(state.get("stream_events", []))
        sources: list[dict[str, Any]] = list(state.get("sources", []))
        errors: list[str] = list(state.get("errors", []))

        # Decide which tools to call based on classification
        tools_to_call: list[str] = []
        if cls:
            if cls.needs_profile:
                tools_to_call.append("get_learner_profile")
            if cls.needs_long_term_memory:
                tools_to_call.append("get_long_term_memory")
            if cls.needs_knowledge_search:
                tools_to_call.append("search_knowledge_base")
            if cls.needs_web_search or enable_web_search:
                tools_to_call.append("web_search")
            if cls.needs_recent_evaluation:
                tools_to_call.append("get_recent_evaluation")

        if not tools_to_call and enable_web_search:
            tools_to_call.append("web_search")

        seq = len(events) + 1
        for tool_name in tools_to_call:
            start_event = ChatStreamEvent(type="tool_start", payload={"tool_name": tool_name}, sequence=seq, timestamp=time.time())
            events = await self._emit_event(state, start_event, events, turn_event_type="tool.start")
            seq += 1

            intent = TutorToolCall(tool_name=tool_name, payload={"query": question, "reason": "classify routed"})
            tool_status = "success"
            tool_call_id = f"call-{uuid4().hex}"
            result_text = ""
            result_evidence: list[dict[str, Any]] = []
            assistant_message_id: int | None = None
            tool_message_id: int | None = None

            try:
                assistant_message = await self.memory_service.save_message(
                    user_id=user_id,
                    session_id=session_id,
                    role="assistant",
                    content=f"正在调用工具：{tool_name}",
                    tool_calls=[{"id": tool_call_id, "name": tool_name, "args": intent.payload}],
                    turn_id=state.get("turn_id"),
                    message_kind="assistant_tool_request",
                )
                assistant_message_id = getattr(assistant_message, "id", None)
            except Exception as exc:
                logger.warning("[TutorAgent] save tool request message failed: %s", exc)

            try:
                result = await executor.execute(intent)
                tool_status = str(result.get("status", "success")) if isinstance(result, dict) else "success"
                result_text = str((result or {}).get("result_text", "")) if isinstance(result, dict) else ""
                result_evidence = (result or {}).get("evidence", []) if isinstance(result, dict) else []

                tool_invocations.append({
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "payload": intent.payload,
                    "result_text": result_text,
                    "status": tool_status,
                    "evidence": result_evidence,
                    "assistant_message_id": assistant_message_id,
                })

                if isinstance(result, dict):
                    if result_evidence:
                        evidence_list.extend(result_evidence)

                    if tool_name == "search_knowledge_base":
                        for e in result_evidence:
                            if isinstance(e, dict):
                                raw_sources = (e.get("details") or {}).get("sources", [])
                                if isinstance(raw_sources, list):
                                    sources.extend(s for s in raw_sources if isinstance(s, dict))
                    elif tool_name == "web_search":
                        for e in result_evidence:
                            if isinstance(e, dict):
                                details = e.get("details") or {}
                                sources.append({
                                    "source": details.get("tool_name") or "web_search",
                                    "query": details.get("query") or "",
                                    "summary": e.get("summary", ""),
                                })

            except Exception as exc:
                logger.warning("[TutorAgent] tool %s failed: %s", tool_name, exc)
                tool_status = "error"
                errors.append(f"{tool_name}: {exc}")
                result_text = f"调用失败: {exc}"
                tool_invocations.append({
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "payload": intent.payload,
                    "result_text": result_text,
                    "status": "error",
                    "evidence": [],
                    "assistant_message_id": assistant_message_id,
                })

            try:
                tool_message = await self.memory_service.save_message(
                    user_id=user_id,
                    session_id=session_id,
                    role="tool",
                    content=result_text,
                    tool_call_id=tool_call_id,
                    turn_id=state.get("turn_id"),
                    message_kind="tool_result",
                )
                tool_message_id = getattr(tool_message, "id", None)
            except Exception as exc:
                logger.warning("[TutorAgent] save tool result message failed: %s", exc)

            if tool_invocations:
                tool_invocations[-1]["tool_message_id"] = tool_message_id

            try:
                await self.memory_service.save_tool_invocations(
                    user_id=user_id,
                    session_id=session_id,
                    turn_id=state.get("turn_id"),
                    invocations=[
                        {
                            "tool_call_id": tool_call_id,
                            "tool_name": tool_name,
                            "arguments_json": intent.payload,
                            "result_text": result_text,
                            "result_json": {"evidence": result_evidence},
                            "status": tool_status,
                            "assistant_message_id": assistant_message_id,
                            "tool_message_id": tool_message_id,
                        }
                    ],
                )
            except Exception as exc:
                logger.warning("[TutorAgent] save tool invocation failed: %s", exc)

            done_event = ChatStreamEvent(
                type="tool_done",
                payload={"tool_name": tool_name, "status": tool_status},
                sequence=seq,
                timestamp=time.time(),
            )
            events = await self._emit_event(state, done_event, events, turn_event_type="tool.done")
            seq += 1

        return {
            "evidence": evidence_list,
            "tool_invocations": tool_invocations,
            "stream_events": events,
            "sources": sources,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Node: answer_node
    # ------------------------------------------------------------------

    async def _answer_node(self, state: TutorAgentState) -> dict:
        question = state.get("question", "")
        history = state.get("history_messages", [])
        session_summary = state.get("session_summary", "")
        attachment_context = state.get("attachment_context", "")
        evidence_list = state.get("evidence", [])
        attachments = state.get("attachments", [])

        # Build evidence context
        evidence_parts: list[str] = []
        for e in evidence_list:
            if isinstance(e, dict) and e.get("summary"):
                evidence_parts.append(f"[{e.get('evidence_type', 'unknown')}] {e['summary']}")
        evidence_context = "\n".join(evidence_parts) if evidence_parts else "无额外证据。"

        # Build system prompt
        system_prompt = prompts.get("chat").render(
            "tutor_system",
            session_summary_context=session_summary,
            file_context=f"附件 {len(attachments)} 个" if attachments else "本轮没有上传附件。",
            attachment_analysis_context=attachment_context or "本轮没有可用的附件预分析内容。",
            evaluation_summary_context="如需近期测验、薄弱点或学习计划依据，请调用 get_recent_evaluation 工具。",
        )
        system_prompt += (
            f"\n\n# 当前日期\n{_current_date_text()}\n"
            "涉及年份、最新、考试真题、政策、版本或其他时效信息时，必须以本轮工具证据为准；"
            "如果没有可用证据，不要编造当前时间、发布时间、真题内容或来源。"
        )

        # Inject extra context
        extra_parts: list[str] = []
        if evidence_context and evidence_context != "无额外证据。":
            extra_parts.append(f"[检索证据]\n{evidence_context}")
        if extra_parts:
            system_prompt += "\n\n" + "\n\n".join(extra_parts)

        # Build messages
        human_content = question
        if attachment_context:
            human_content = f"{question}\n\n[附件分析结果]\n{attachment_context}"

        # Spark-compatible chat completions reject multiple system messages.
        history_without_system = [msg for msg in history if not isinstance(msg, SystemMessage)]
        messages = [SystemMessage(content=system_prompt), *history_without_system, HumanMessage(content=human_content)]

        events = list(state.get("stream_events", []))
        full_answer = ""
        raw_answer = ""
        seq = len(events) + 1

        try:
            from app.chat.service import safety_filter

            stream_buffer = SafetyBufferedResponseStreamer(
                response_streamer=ResponseStreamer(),
                safety_check=safety_filter.check,
                guard_chars=safety_filter.stream_guard_chars,
            )

            stream = self.llm.astream(messages, temperature=0.25)
            async for chunk in stream:
                content = getattr(chunk, "content", "")
                if isinstance(content, list) and content:
                    content = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
                chunk_str = normalize_message_content(content)
                if not chunk_str:
                    continue
                raw_answer += chunk_str
                async for safe_event in stream_buffer.push(chunk_str):
                    token = safe_event.get("data", "")
                    if not token:
                        continue
                    full_answer += token
                    event = ChatStreamEvent(type="answer_token", payload={"token": token}, sequence=seq, timestamp=time.time())
                    events = await self._emit_event(state, event, events, persist=False)
                    seq += 1

            async for safe_event in stream_buffer.flush():
                token = safe_event.get("data", "")
                if not token:
                    continue
                full_answer += token
                event = ChatStreamEvent(type="answer_token", payload={"token": token}, sequence=seq, timestamp=time.time())
                events = await self._emit_event(state, event, events, persist=False)
                seq += 1

            if not full_answer:
                full_answer = raw_answer

        except Exception as exc:
            logger.exception("[TutorAgent] answer streaming failed")
            try:
                response = await self.llm.ainvoke(messages, temperature=0.25)
                full_answer = normalize_message_content(getattr(response, "content", ""))
            except Exception as fallback_exc:
                logger.exception("[TutorAgent] answer fallback also failed")
                errors = list(state.get("errors", []))
                errors.append(f"answer_node: {exc}")
                return {"final_answer": "", "stream_events": events, "errors": errors}

        answer_done_event = ChatStreamEvent(
            type="answer_done",
            payload={"answer_length": len(full_answer)},
            sequence=seq,
            timestamp=time.time(),
        )
        events = await self._emit_event(state, answer_done_event, events, turn_event_type="answer.done")

        return {"final_answer": full_answer, "stream_events": events}

    # ------------------------------------------------------------------
    # Node: diagram_node
    # ------------------------------------------------------------------

    async def _diagram_node(self, state: TutorAgentState) -> dict:
        question = state.get("question", "")
        final_answer = state.get("final_answer", "")
        user_id = state.get("user_id", 0)
        session_id = state.get("session_id", "")
        attachments = state.get("attachments", [])
        enable_web_search = state.get("enable_web_search", False)
        need_diagram = state.get("need_teaching_diagram", False)

        events = list(state.get("stream_events", []))
        diagram_result: dict[str, Any] | None = None

        start_event = ChatStreamEvent(type="diagram_start", payload={}, sequence=len(events) + 1, timestamp=time.time())
        events = await self._emit_event(state, start_event, events, turn_event_type="diagram.start")

        try:
            evidence_set = EvidenceSet(items=[Evidence.model_validate(e) for e in state.get("evidence", []) if isinstance(e, dict)])
            diagram_result = await TeachingDiagramGenerator().generate(
                TutorTurnContext(
                    user_id=user_id,
                    session_id=session_id,
                    user_input=question,
                    attachments=attachments,
                    enable_web_search=enable_web_search,
                    need_teaching_diagram=need_diagram,
                ),
                final_answer,
                evidence_set,
            )
        except Exception as exc:
            logger.warning("[TutorAgent] diagram generation failed: %s", exc)
            errors = list(state.get("errors", []))
            errors.append(f"diagram_node: {exc}")
            done_event = ChatStreamEvent(type="diagram_done", payload={"has_diagram": False}, sequence=len(events) + 1, timestamp=time.time())
            events = await self._emit_event(state, done_event, events, turn_event_type="diagram.done")
            return {"diagram_result": None, "stream_events": events, "errors": errors}

        done_event = ChatStreamEvent(
            type="diagram_done",
            payload={"has_diagram": diagram_result is not None},
            sequence=len(events) + 1,
            timestamp=time.time(),
        )
        events = await self._emit_event(state, done_event, events, turn_event_type="diagram.done")

        return {"diagram_result": diagram_result, "stream_events": events}
