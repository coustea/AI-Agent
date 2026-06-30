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

from langchain_core.messages import HumanMessage, SystemMessage

from app.chat.agent.state import TutorAgentState
from app.chat.emitter import (
    build_agent_status_payload,
    build_attachment_status_payload,
    build_workflow_activity_payload,
)
from app.chat.agent.tool_runner import (
    ToolExecutionContext,
    TutorToolRunner,
)
from app.chat.schemas import (
    TutorRuntimeEvent,
    ClassificationResult,
    Evidence,
    EvidenceSet,
    TutorTurnContext,
)
from app.chat.schemas.diagram import TeachingDiagramGenerator
from app.chat.streaming import ResponseStreamer, SafetyBufferedResponseStreamer
from app.chat.agent.tools import (
    WEB_RESEARCH_TOOL_NAMES,
    build_tutor_tools,
)
from app.chat.utils import normalize_message_content
from app.chat.utils.files import analyze_documents
from app.chat.utils.vision import VisionService
from app.config import IMAGE_EXTENSIONS
from app.infra.logging import get_logger
from app.infra.tool_excute import ToolExcute, ToolRuntimeEvent

logger = get_logger(__name__)




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
    events: list[TutorRuntimeEvent] = []

    start_event = TutorRuntimeEvent(
        type="workflow_status",
        payload=build_workflow_activity_payload(
            stage="classifying",
            activity_id="workflow:current",
            title="正在判断回答方式",
            message="正在判断是否需要查资料或分析附件",
            summary="",
        ),
        sequence=len(state.get("stream_events", [])) + 1,
        timestamp=time.time(),
    )
    events.extend(await agent._emit_event(state, start_event, turn_event_type="classify.start"))

    prompt = (
        f"学生问题: {question}\n"
        f"附件数量: {len(attachments)}\n"
        f"会话摘要: {summary[:200] if summary else '无'}\n"
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

    # 确保用户显式请求图解时，needs_diagram 被正确设置
    if has_diagram and not classification.needs_diagram:
        classification = classification.model_copy(update={"needs_diagram": True})

    route_parts: list[str] = []
    if classification.needs_file_analysis:
        route_parts.append("附件分析")
    if classification.needs_knowledge_search:
        route_parts.append("课程知识库")
    if classification.needs_web_search:
        route_parts.append("联网检索")
    if classification.needs_diagram:
        route_parts.append("教学图解")
    route_summary = "、".join(route_parts) if route_parts else "直接回答"

    event = TutorRuntimeEvent(
        type="classify_done",
        payload={
            **classification.model_dump(),
            **build_workflow_activity_payload(
                stage="route_ready",
                activity_id="workflow:current",
                title="正在选择信息来源",
                message=f"回答方式：{route_summary}",
                summary=route_summary,
            ),
        },
        sequence=len(state.get("stream_events", [])) + len(events) + 1,
        timestamp=time.time(),
    )
    events.extend(await agent._emit_event(state, event, turn_event_type="classify.done"))

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

    image_urls, file_urls = [], []
    for url in attachments:
        ext = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""
        if ext in IMAGE_EXTENSIONS:
            image_urls.append(url)
        else:
            file_urls.append(url)

    events: list[TutorRuntimeEvent] = []
    activity_groups = (("image", image_urls), ("document", file_urls))
    for index, (analysis_type, urls) in enumerate(activity_groups):
        if not urls:
            continue
        event = TutorRuntimeEvent(
            type="attachment_status",
            payload=build_attachment_status_payload(
                activity_id=f"attachment-{analysis_type}-{index}",
                status="running",
                file_names=[url.split("/")[-1] for url in urls],
                analysis_type=analysis_type,
            ),
            sequence=len(state.get("stream_events", [])) + 1 + index,
            timestamp=time.time(),
        )
        events.extend(await agent._emit_event(state, event, turn_event_type="file.analysis.start"))

    parts: list[str] = []
    analysis_errors: dict[str, str] = {}

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
            analysis_errors["image"] = str(exc)

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
            analysis_errors["document"] = str(exc)

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

    # 为每个附件分析创建 Evidence，供回答节点和图解生成器使用
    attachment_evidence: list[dict[str, Any]] = []
    for analysis in attachment_analyses:
        analysis_type = analysis.get("analysis_type", "image")
        summary_text = analysis.get("summary_text", "")
        file_urls = []
        file_names = []
        if analysis_type == "image":
            structured = analysis.get("structured_json", {}) if isinstance(analysis.get("structured_json"), dict) else {}
            file_urls = image_urls if analysis_type == "image" else file_urls
            file_names = [url.split("/")[-1] for url in file_urls]
        if summary_text:
            attachment_evidence.append(
                Evidence(
                    evidence_type="attachment",
                    summary=summary_text[:3000],
                    details={
                        "analysis_type": analysis_type,
                        "file_urls": image_urls if analysis_type == "image" else file_urls,
                        "file_names": [url.split("/")[-1] for url in (image_urls if analysis_type == "image" else file_urls)],
                    },
                ).model_dump()
            )

    done_events: list[TutorRuntimeEvent] = []
    analyses_by_type = {
        str(item.get("analysis_type") or "document"): item
        for item in attachment_analyses
    }
    for index, (analysis_type, urls) in enumerate(activity_groups):
        if not urls:
            continue
        analysis = analyses_by_type.get(analysis_type, {})
        status = "done" if analysis else "failed"
        event = TutorRuntimeEvent(
            type="attachment_status",
            payload=build_attachment_status_payload(
                activity_id=f"attachment-{analysis_type}-{index}",
                status=status,
                file_names=[str(url).split("/")[-1] for url in urls],
                analysis_type=analysis_type,
                summary=str(analysis.get("summary_text") or ""),
                error=analysis_errors.get(analysis_type, "未提取到可用内容") if status == "failed" else "",
            ),
            sequence=len(state.get("stream_events", [])) + len(events) + 1 + index,
            timestamp=time.time(),
        )
        done_events.extend(await agent._emit_event(state, event, turn_event_type="file.analysis.done"))

    return {
        "attachment_context": attachment_context,
        "attachment_analyses": attachment_analyses,
        "evidence": attachment_evidence,
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
    from app.chat.tools.web_research import ResearchToolStep, WebResearchRunner

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

    # 创建事件收集列表和 emit_event 回调
    node_events: list[TutorRuntimeEvent] = []
    base_seq = len(state.get("stream_events", [])) + 1

    async def emit_event_callback(event: TutorRuntimeEvent) -> None:
        """事件发送回调：收集工具发送的事件并发送给前端。"""
        node_events.append(event)
        # 同时通过 agent._emit_event 发送（用于 SSE 和持久化）
        await agent._emit_event(state, event)

    event_sequence = base_seq

    async def emit_tool_status(event: ToolRuntimeEvent) -> None:
        nonlocal event_sequence
        event_sequence += 1
        await emit_event_callback(
            TutorRuntimeEvent(
                type="agent_status",
                payload=build_agent_status_payload(event),
                sequence=event_sequence,
            )
        )

    tool_excute = ToolExcute(
        llm.model,
        build_tutor_tools(turn_context),
        event_handler=emit_tool_status,
    )

    tools_to_call: list[str] = []
    needs_web_research = bool(enable_web_search or (cls and cls.needs_web_search))

    if cls:
        if cls.needs_profile:
            tools_to_call.append("get_learner_profile")
        if cls.needs_long_term_memory:
            tools_to_call.append("get_long_term_memory")
        if cls.needs_knowledge_search:
            tools_to_call.append("search_knowledge_base")

    if not tools_to_call and not needs_web_research:
        return {
            "evidence": [],
            "tool_invocations": [],
            "stream_events": [],
            "sources": [],
            "errors": [],
            "_search_attempted": True,
        }

    node_evidence: list[dict[str, Any]] = []
    node_sources: list[dict[str, Any]] = []
    node_tool_invocations: list[dict[str, Any]] = []
    node_errors: list[str] = []

    plan_parts = []
    if tools_to_call:
        plan_parts.append("学习记录")
    if needs_web_research:
        plan_parts.append("网页资料")
    if plan_parts:
        plan_event = TutorRuntimeEvent(
            type="workflow_status",
            payload=build_workflow_activity_payload(
                stage="collecting_context",
                activity_id="workflow:current",
                title="正在查找相关信息",
                message=f"正在读取{'和'.join(plan_parts)}",
                summary="、".join(plan_parts),
            ),
            sequence=base_seq,
            timestamp=time.time(),
        )
        await emit_event_callback(plan_event)

    def collect_result(result: Any) -> None:
        if isinstance(result, Exception):
            node_errors.append(f"parallel_tool_call: {result}")
            return
        events, invocation, evidence, sources, errors = result
        # 事件已通过 emit_event_callback 收集，这里不需要再添加
        if invocation:
            node_tool_invocations.append(invocation)
        node_evidence.extend(evidence)
        node_sources.extend(sources)
        node_errors.extend(errors)

    if tools_to_call:
        coros = [
            _execute_single_tool(
                agent, state, tool_excute, name,
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
        web_tool_excute = tool_excute.subset(WEB_RESEARCH_TOOL_NAMES)
        research_prompt = prompts.get("chat").render(
            "search_instruction",
            attachment_context_section=(
                f"\n附件预分析：\n{state.get('attachment_context', '')}"
                if state.get("attachment_context")
                else ""
            ),
        )
        runner = WebResearchRunner(
            tool_excute=web_tool_excute,
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
                agent, state, tool_excute, tool_name, payload, next_seq,
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
    from app.chat.streaming import safety_filter

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

    node_events: list[TutorRuntimeEvent] = []
    full_answer = ""
    raw_answer = ""
    seq = len(state.get("stream_events", [])) + 1
    stream_started = False

    compose_event = TutorRuntimeEvent(
        type="workflow_status",
        payload=build_workflow_activity_payload(
            stage="composing_answer",
            activity_id="workflow:current",
            title="正在组织回答",
            message="正在把上下文整理成回答",
            summary="",
        ),
        sequence=seq,
        timestamp=time.time(),
    )
    node_events.extend(await agent._emit_event(state, compose_event, turn_event_type="answer.compose"))
    seq += 1

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
                stream_started = True
                full_answer += token
                event = TutorRuntimeEvent(
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
            stream_started = True
            full_answer += token
            event = TutorRuntimeEvent(
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
            fallback_answer = normalize_message_content(getattr(response, "content", ""))
            if fallback_answer:
                safety_result = await safety_filter.check(fallback_answer)
                fallback_answer = safety_result.sanitized_text
            if stream_started and fallback_answer:
                # 流式已输出部分内容，发送 content_replace 让前端替换
                replace_event = TutorRuntimeEvent(
                    type="content_replace",
                    payload={"content": fallback_answer},
                    sequence=seq,
                    timestamp=time.time(),
                )
                node_events.extend(await agent._emit_event(state, replace_event))
                seq += 1
            full_answer = fallback_answer
        except Exception as fallback_exc:
            logger.exception("[answer_node] fallback also failed")
            return {
                "final_answer": "",
                "stream_events": node_events,
                "errors": [f"answer_node: {exc}"]
            }

    answer_done_event = TutorRuntimeEvent(
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

    node_events: list[TutorRuntimeEvent] = []
    diagram_result: dict[str, Any] | None = None

    start_event = TutorRuntimeEvent(
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
        done_event = TutorRuntimeEvent(
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

    done_event = TutorRuntimeEvent(
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
    tool_excute: ToolExcute,
    tool_name: str,
    payload: dict[str, Any],
    seq: int,
    tool_call_id: str | None = None,
    memory_service: Any | None = None,
) -> tuple[list[TutorRuntimeEvent], dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """执行单个工具调用并返回结果（委托给 TutorToolRunner）。

    注意：ToolExcute 已通过请求级回调发送 agent_status 事件。

    Returns:
        (events, invocation_entry, evidence, sources, errors)
    """
    user_id = state.get("user_id", 0)
    session_id = state.get("session_id", "")

    runner = TutorToolRunner()
    context = ToolExecutionContext(
        user_id=user_id,
        session_id=session_id,
        memory_service=memory_service,
    )

    result = await runner.execute(
        tool_name=tool_name,
        arguments=payload,
        tool_call_id=tool_call_id,
        context=context,
        tool_excute=tool_excute,
    )

    return [], result.invocation, result.evidence, result.sources, result.errors
