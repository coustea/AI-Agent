"""TutorAgent 节点实现 — LangGraph 图的各个处理节点。

节点列表：
  - classify_node: 意图分类
  - analysis_files_node: 附件分析（图片OCR、文档解析）
  - search_node: 工具调用和联网搜索
  - answer_node: 流式回答生成
  - diagram_node: 教学图解生成
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage

from app.chat.agent.state import TutorAgentState
from app.chat.schemas import (
    ChatStreamEvent,
    ClassificationResult,
    Evidence,
    EvidenceSet,
    TutorToolCall,
    TutorTurnContext,
)
from app.chat.diagram import TeachingDiagramGenerator
from app.chat.streaming import ResponseStreamer, SafetyBufferedResponseStreamer
from app.chat.tool_executor import TutorToolExecutor, TutorToolRegistry
from app.chat.utils import normalize_message_content
from app.chat.utils.files import analyze_documents
from app.chat.utils.vision import VisionService
from app.config import IMAGE_EXTENSIONS
from app.infra.logging import get_logger

logger = get_logger(__name__)

WEB_RESEARCH_TOOL_NAMES = (
    "web_search",
    "open_web_page",
    "find_in_web_page",
    "extract_web_links",
    "read_web_pdf",
)


def _current_date_text() -> str:
    return datetime.now().date().isoformat()


def build_evidence_context(evidence_list: list[dict[str, Any]]) -> str:
    """Format answer-usable evidence, preserving precise web source identity."""
    parts: list[str] = []
    seen_urls: set[str] = set()
    source_number = 0
    for evidence in evidence_list:
        if not isinstance(evidence, dict) or evidence.get("usable_for_answer", True) is False:
            continue
        summary = str(evidence.get("summary") or "").strip()
        if not summary:
            continue
        evidence_type = str(evidence.get("evidence_type") or "unknown")
        details = evidence.get("details") if isinstance(evidence.get("details"), dict) else {}
        url = str(details.get("url") or "").strip()
        if evidence_type == "web_search" and url:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            source_number += 1
            title = str(details.get("title") or url).strip()
            parts.append(
                f"[来源 {source_number}] {title}\n"
                f"URL: {url}\n"
                f"摘录: {summary[:3000]}"
            )
        else:
            parts.append(f"[{evidence_type}] {summary[:3000]}")
    return "\n\n".join(parts) if parts else "无额外证据。"


async def classify_node(
    agent: Any,
    state: TutorAgentState,
    llm: Any,
    prompts: Any,
) -> dict:
    """分类节点：判断需要哪些工具和后续流程。"""
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
        classification = await llm.ainvoke_json(
            ClassificationResult,
            [
                SystemMessage(content=classify_system_prompt),
                HumanMessage(content=prompt),
            ],
            temperature=0.1,
        )
    except Exception as exc:
        logger.warning("[classify_node] LLM failed, using defaults: %s", exc)
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
    events = await agent._emit_event(state, event, turn_event_type="classify.done")

    return {
        "classification": classification,
        "stream_events": events,
    }


async def analysis_files_node(
    agent: Any,
    state: TutorAgentState,
) -> dict:
    """附件分析节点：图片OCR和文档解析。"""
    attachments = state.get("attachments", [])
    user_id = state.get("user_id", 0)
    session_id = state.get("session_id", "")

    start_event = ChatStreamEvent(
        type="file_analysis_start",
        payload={"count": len(attachments)},
        sequence=2,
        timestamp=time.time()
    )
    events = await agent._emit_event(state, start_event, turn_event_type="file.analysis.start")

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
            logger.warning("[analysis_files_node] image analysis failed: %s", exc)

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
            logger.warning("[analysis_files_node] document analysis failed: %s", exc)

    attachment_context = "\n".join(parts)
    attachment_analyses: list[dict[str, Any]] = []

    if image_urls and any(part.startswith("[图片]") for part in parts):
        image_summary = "\n".join(
            part.removeprefix("[图片] ").strip()
            for part in parts if part.startswith("[图片]")
        )
        attachment_analyses.append({
            "file_url": image_urls[0],
            "file_name": image_urls[0].split("/")[-1],
            "analysis_type": "image",
            "summary_text": image_summary,
            "structured_json": {"file_urls": image_urls},
        })

    if file_urls and any(part.startswith("[文档]") for part in parts):
        document_summary = "\n".join(
            part.removeprefix("[文档] ").strip()
            for part in parts if part.startswith("[文档]")
        )
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
    done_events = await agent._emit_event(state, done_event, turn_event_type="file.analysis.done")

    return {
        "attachment_context": attachment_context,
        "attachment_analyses": attachment_analyses,
        "stream_events": events + done_events,
    }


async def search_node(
    agent: Any,
    state: TutorAgentState,
    llm: Any,
    prompts: Any,
    memory_service: Any,
) -> dict:
    """搜索节点：工具调用和联网搜索。"""
    from app.chat.research import ResearchToolStep, WebResearchRunner

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

    tools_to_call: list[str] = []
    needs_web_research = bool(enable_web_search or (cls and cls.needs_web_search))

    if cls:
        if cls.needs_profile:
            tools_to_call.append("get_learner_profile")
        if cls.needs_long_term_memory:
            tools_to_call.append("get_long_term_memory")
        if cls.needs_knowledge_search:
            tools_to_call.append("search_knowledge_base")
        if cls.needs_recent_evaluation:
            tools_to_call.append("get_recent_evaluation")

    if not tools_to_call and not needs_web_research:
        return {
            "evidence": [],
            "tool_invocations": [],
            "stream_events": [],
            "sources": [],
            "errors": [],
            "_search_attempted": True,
        }

    node_events: list[ChatStreamEvent] = []
    node_evidence: list[dict[str, Any]] = []
    node_sources: list[dict[str, Any]] = []
    node_tool_invocations: list[dict[str, Any]] = []
    node_errors: list[str] = []

    def collect_result(result: Any) -> None:
        if isinstance(result, Exception):
            node_errors.append(f"parallel_tool_call: {result}")
            return
        events, invocation, evidence, sources, errors = result
        node_events.extend(events)
        if invocation:
            node_tool_invocations.append(invocation)
        node_evidence.extend(evidence)
        node_sources.extend(sources)
        node_errors.extend(errors)

    base_seq = len(state.get("stream_events", [])) + 1

    if tools_to_call:
        coros = [
            _execute_single_tool(
                agent, state, executor, name,
                {"query": question, "reason": "classify routed"},
                base_seq + i * 2,
                memory_service=memory_service,
            )
            for i, name in enumerate(tools_to_call)
        ]
        results = await asyncio.gather(*coros, return_exceptions=True)
        for result in results:
            collect_result(result)

    if needs_web_research:
        web_tools = [registry.by_name(name) for name in WEB_RESEARCH_TOOL_NAMES]
        research_prompt = prompts.get("chat").render(
            "search_instruction",
            attachment_context_section=(
                f"\n附件预分析：\n{state.get('attachment_context', '')}"
                if state.get("attachment_context")
                else ""
            ),
        )
        runner = WebResearchRunner(
            llm=llm,
            tools=web_tools,
            system_prompt=research_prompt,
        )
        next_seq = base_seq + len(tools_to_call) * 2

        async def execute_research_tool(
            tool_name: str,
            payload: dict[str, Any],
            call_id: str,
        ) -> ResearchToolStep:
            nonlocal next_seq
            result = await _execute_single_tool(
                agent, state, executor, tool_name, payload, next_seq,
                tool_call_id=call_id, memory_service=memory_service
            )
            next_seq += 2
            events, invocation, evidence, sources, errors = result
            return ResearchToolStep(
                tool_call_id=call_id,
                tool_name=tool_name,
                payload=payload,
                status=str((invocation or {}).get("status") or "failed"),
                result_text=str((invocation or {}).get("result_text") or ""),
                evidence=evidence,
                events=events,
                invocation=invocation,
                sources=sources,
                errors=errors,
            )

        research_steps = await runner.run(question, execute=execute_research_tool)
        for step in research_steps:
            if step.invocation is None:
                node_errors.extend(step.errors)
                continue
            collect_result((step.events, step.invocation, step.evidence, step.sources, step.errors))

    return {
        "evidence": node_evidence,
        "tool_invocations": node_tool_invocations,
        "stream_events": node_events,
        "sources": node_sources,
        "errors": node_errors,
        "_search_attempted": True,
    }


async def answer_node(
    agent: Any,
    state: TutorAgentState,
    llm: Any,
    prompts: Any,
) -> dict:
    """回答节点：流式生成回答。"""
    from app.chat.safety import safety_filter

    question = state.get("question", "")
    history = state.get("history_messages", [])
    session_summary = state.get("session_summary", "")
    attachment_context = state.get("attachment_context", "")
    evidence_list = state.get("evidence", [])
    attachments = state.get("attachments", [])

    evidence_context = build_evidence_context(evidence_list)

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

    extra_parts: list[str] = []
    if evidence_context and evidence_context != "无额外证据。":
        extra_parts.append(f"[检索证据]\n{evidence_context}")
        extra_parts.append(
            "引用外部事实时使用对应来源 URL；不要引用未出现在证据中的网页。"
            "如果证据不足或互相冲突，请明确说明不确定性。"
        )
    if extra_parts:
        system_prompt += "\n\n" + "\n\n".join(extra_parts)

    human_content = question
    if attachment_context:
        human_content = f"{question}\n\n[附件分析结果]\n{attachment_context}"

    history_without_system = [msg for msg in history if not isinstance(msg, SystemMessage)]
    messages = [SystemMessage(content=system_prompt), *history_without_system, HumanMessage(content=human_content)]

    node_events: list[ChatStreamEvent] = []
    full_answer = ""
    raw_answer = ""
    seq = len(state.get("stream_events", [])) + 1

    try:
        stream_buffer = SafetyBufferedResponseStreamer(
            response_streamer=ResponseStreamer(),
            safety_check=safety_filter.check,
            guard_chars=safety_filter.stream_guard_chars,
        )

        stream = llm.astream(messages, temperature=0.25)
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
                event = ChatStreamEvent(
                    type="answer_token",
                    payload={"token": token},
                    sequence=seq,
                    timestamp=time.time()
                )
                node_events.extend(await agent._emit_event(state, event, persist=False))
                seq += 1

        async for safe_event in stream_buffer.flush():
            token = safe_event.get("data", "")
            if not token:
                continue
            full_answer += token
            event = ChatStreamEvent(
                type="answer_token",
                payload={"token": token},
                sequence=seq,
                timestamp=time.time()
            )
            node_events.extend(await agent._emit_event(state, event, persist=False))
            seq += 1

        if not full_answer:
            full_answer = raw_answer

    except Exception as exc:
        logger.exception("[answer_node] streaming failed")
        try:
            response = await llm.ainvoke(messages, temperature=0.25)
            full_answer = normalize_message_content(getattr(response, "content", ""))
        except Exception as fallback_exc:
            logger.exception("[answer_node] fallback also failed")
            return {
                "final_answer": "",
                "stream_events": node_events,
                "errors": [f"answer_node: {exc}"]
            }

    answer_done_event = ChatStreamEvent(
        type="answer_done",
        payload={"answer_length": len(full_answer)},
        sequence=seq,
        timestamp=time.time(),
    )
    node_events.extend(await agent._emit_event(state, answer_done_event, turn_event_type="answer.done"))

    return {"final_answer": full_answer, "stream_events": node_events}


async def diagram_node(
    agent: Any,
    state: TutorAgentState,
) -> dict:
    """图解节点：生成教学图解。"""
    question = state.get("question", "")
    final_answer = state.get("final_answer", "")
    user_id = state.get("user_id", 0)
    session_id = state.get("session_id", "")
    attachments = state.get("attachments", [])
    enable_web_search = state.get("enable_web_search", False)
    need_diagram = state.get("need_teaching_diagram", False)

    node_events: list[ChatStreamEvent] = []
    diagram_result: dict[str, Any] | None = None

    start_event = ChatStreamEvent(
        type="diagram_start",
        payload={},
        sequence=len(state.get("stream_events", [])) + 1,
        timestamp=time.time()
    )
    node_events.extend(await agent._emit_event(state, start_event, turn_event_type="diagram.start"))

    try:
        evidence_set = EvidenceSet(
            items=[Evidence.model_validate(e) for e in state.get("evidence", []) if isinstance(e, dict)]
        )
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
        logger.warning("[diagram_node] generation failed: %s", exc)
        done_event = ChatStreamEvent(
            type="diagram_done",
            payload={"has_diagram": False},
            sequence=len(state.get("stream_events", [])) + len(node_events) + 1,
            timestamp=time.time()
        )
        node_events.extend(await agent._emit_event(state, done_event, turn_event_type="diagram.done"))
        return {
            "diagram_result": None,
            "stream_events": node_events,
            "errors": [f"diagram_node: {exc}"]
        }

    done_event = ChatStreamEvent(
        type="diagram_done",
        payload={"has_diagram": diagram_result is not None},
        sequence=len(state.get("stream_events", [])) + len(node_events) + 1,
        timestamp=time.time(),
    )
    node_events.extend(await agent._emit_event(state, done_event, turn_event_type="diagram.done"))

    return {"diagram_result": diagram_result, "stream_events": node_events}


# -----------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------


async def _execute_single_tool(
    agent: Any,
    state: TutorAgentState,
    executor: TutorToolExecutor,
    tool_name: str,
    payload: dict[str, Any],
    seq: int,
    tool_call_id: str | None = None,
    memory_service: Any | None = None,
) -> tuple[list[ChatStreamEvent], dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """执行单个工具调用并返回结果。

    Returns:
        (events, invocation_entry, evidence, sources, errors)
    """
    node_events: list[ChatStreamEvent] = []
    node_evidence: list[dict[str, Any]] = []
    node_sources: list[dict[str, Any]] = []
    node_errors: list[str] = []
    user_id = state.get("user_id", 0)
    session_id = state.get("session_id", "")

    start_event = ChatStreamEvent(
        type="tool_start",
        payload={"tool_name": tool_name},
        sequence=seq,
        timestamp=time.time()
    )
    node_events.extend(await agent._emit_event(state, start_event, turn_event_type="tool.start"))

    intent = TutorToolCall(tool_name=tool_name, payload=payload)
    tool_status = "success"
    tool_call_id = tool_call_id or f"call-{uuid4().hex}"
    result_text = ""
    result_evidence: list[dict[str, Any]] = []
    assistant_message_id: int | None = None
    tool_message_id: int | None = None
    invocation_entry: dict[str, Any] | None = None

    # 保存工具请求消息
    if memory_service:
        try:
            assistant_message = await memory_service.save_message(
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
            logger.warning("[_execute_single_tool] save tool request message failed: %s", exc)

    # 执行工具
    try:
        result = await executor.execute(intent)
        tool_status = str(result.get("status", "success")) if isinstance(result, dict) else "success"
        result_text = str((result or {}).get("result_text", "")) if isinstance(result, dict) else ""
        result_evidence = (result or {}).get("evidence", []) if isinstance(result, dict) else []

        invocation_entry = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "payload": intent.payload,
            "result_text": result_text,
            "status": tool_status,
            "evidence": result_evidence,
            "assistant_message_id": assistant_message_id,
        }

        if isinstance(result, dict):
            if result_evidence:
                node_evidence.extend(result_evidence)

            if tool_name == "search_knowledge_base":
                for e in result_evidence:
                    if isinstance(e, dict):
                        raw_sources = (e.get("details") or {}).get("sources", [])
                        if isinstance(raw_sources, list):
                            node_sources.extend(s for s in raw_sources if isinstance(s, dict))
            elif tool_name in WEB_RESEARCH_TOOL_NAMES:
                for e in result_evidence:
                    if isinstance(e, dict):
                        details = e.get("details") or {}
                        if details.get("url"):
                            node_sources.append({
                                "source": details.get("tool_name") or tool_name,
                                "url": details.get("url"),
                                "title": details.get("title") or details.get("url"),
                                "summary": e.get("summary", ""),
                            })
                        elif tool_name == "web_search":
                            args = details.get("args") if isinstance(details.get("args"), dict) else {}
                            node_sources.append({
                                "source": details.get("tool_name") or "web_search",
                                "query": details.get("query") or args.get("query") or "",
                                "summary": e.get("summary", ""),
                            })

    except Exception as exc:
        logger.warning("[_execute_single_tool] tool %s failed: %s", tool_name, exc)
        tool_status = "error"
        node_errors.append(f"{tool_name}: {exc}")
        result_text = f"调用失败: {exc}"
        invocation_entry = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "payload": intent.payload,
            "result_text": result_text,
            "status": "error",
            "evidence": [],
            "assistant_message_id": assistant_message_id,
        }

    # 保存工具结果消息
    if memory_service:
        try:
            tool_message = await memory_service.save_message(
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
            logger.warning("[_execute_single_tool] save tool result message failed: %s", exc)

    if invocation_entry:
        invocation_entry["tool_message_id"] = tool_message_id

    # 持久化工具调用记录
    if memory_service:
        try:
            await memory_service.save_tool_invocations(
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
            logger.warning("[_execute_single_tool] save tool invocation failed: %s", exc)

    done_event = ChatStreamEvent(
        type="tool_done",
        payload={"tool_name": tool_name, "status": tool_status},
        sequence=seq + 1,
        timestamp=time.time(),
    )
    node_events.extend(await agent._emit_event(state, done_event, turn_event_type="tool.done"))

    return node_events, invocation_entry, node_evidence, node_sources, node_errors
