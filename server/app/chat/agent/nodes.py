"""TutorAgent 节点实现 — LangGraph 图的各个处理节点。

节点列表（重构后）：
  - preprocess_node: 附件预处理（确定性步骤）
  - react_node: ReAct Agent 循环（自主决策工具调用和回答）
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.chat.agent.state import TutorAgentState
from app.chat.emitter import (
    build_agent_status_payload,
    build_attachment_status_payload,
    build_research_status_payload,
    build_workflow_activity_payload,
)
from app.chat.agent.tool_runner import ToolExecutionContext, TutorToolRunner
from app.chat.schemas import TutorRequestContext, TutorRuntimeEvent
from app.chat.streaming import ResponseStreamer
from app.chat.agent.tools import build_tutor_tools
from app.chat.utils import normalize_message_content
from app.chat.utils.files import analyze_documents
from app.chat.utils.vision import VisionService
from app.config import IMAGE_EXTENSIONS
from app.infra.logging import get_logger
from app.infra.tool_excute import ToolExcute, ToolRuntimeEvent

logger = get_logger(__name__)


def _current_date_text() -> str:
    return datetime.now().date().isoformat()


_ANSWER_BLOCK_RE = re.compile(
    r"^\s*(?P<reasoning>.*?)\s*"
    r"<answer>\s*(?P<answer>.*?)\s*</answer>\s*$",
    re.DOTALL | re.IGNORECASE,
)


def _normalize_reasoning_summary(text: str) -> str:
    summary = re.sub(r"</?[^>]+>", " ", text)
    summary = re.sub(r"\*\*([^*]+)\*\*", r"\1", summary)
    summary = re.sub(r"\*([^*]+)\*", r"\1", summary)
    return re.sub(r"\s+", " ", summary).strip()[:200]


def split_reasoning_and_answer(text: str) -> tuple[str, str]:
    """拆分可公开的进度摘要与严格包裹的正式回答。"""
    match = _ANSWER_BLOCK_RE.match(text)
    if match:
        return (
            _normalize_reasoning_summary(match.group("reasoning")),
            match.group("answer").strip(),
        )

    # 出现半截 answer 标签时，整段内容都不可信，不能进入思考卡片或正式回答。
    if re.search(r"</?answer\b", text, re.IGNORECASE):
        return "", ""

    return _normalize_reasoning_summary(text), ""


def _thinking_summary(reasoning: str, iteration: int, decision_text: str = "") -> str:
    return (
        reasoning
        or _normalize_reasoning_summary(decision_text)
        or f"第 {iteration} 次推理：分析问题 → 规划回答策略"
    )


# -----------------------------------------------------------------------
# 节点 1: preprocess_node（附件预处理）
# -----------------------------------------------------------------------


async def preprocess_node(
    agent: Any,
    state: TutorAgentState,
) -> dict:
    """预处理节点：分析附件（图片 OCR、文档解析），填充 attachment_context。

    这是确定性步骤，无条件执行。无附件时返回空结果。
    """
    attachments = state.get("attachments", [])
    user_id = state.get("user_id", 0)
    username = state.get("username", "")
    session_id = state.get("session_id", "")
    user_message_id = state.get("user_message_id", 0)

    if not attachments:
        return {"attachment_context": ""}

    image_urls, file_urls = [], []
    for url in attachments:
        ext = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""
        if ext in IMAGE_EXTENSIONS:
            image_urls.append(url)
        else:
            file_urls.append(url)

    events: list[TutorRuntimeEvent] = []
    analysis_records: dict[str, Any] = {}
    activity_groups = (("image", image_urls), ("document", file_urls))
    for index, (analysis_type, urls) in enumerate(activity_groups):
        if not urls:
            continue
        analysis_records[analysis_type] = await agent.memory_service.create_attachment_analysis(
            user_id=user_id,
            session_id=session_id,
            user_message_id=user_message_id,
            analysis_type=analysis_type,
        )
        event = TutorRuntimeEvent(
            type="agent_status",
            payload=build_attachment_status_payload(
                activity_id=f"attachment-{analysis_type}-{index}",
                status="running",
                file_names=[url.split("/")[-1] for url in urls],
                analysis_type=analysis_type,
            ),
            sequence=len(state.get("stream_events", [])) + 1 + index,
            timestamp=time.time(),
        )
        events.extend(await agent._emit_event(state, event))

    analysis_results: dict[str, str] = {}
    analysis_errors: dict[str, str] = {}

    if image_urls:
        try:
            vision_result = await VisionService().analyze_images(
                image_urls[:5],
                "请详细分析这些图片中的文字、题目、图表和关键信息，并用中文总结。",
            )
            analysis_text = str(vision_result.get("analysis_text") or "").strip()
            if analysis_text:
                analysis_results["image"] = analysis_text
                await agent.memory_service.finish_attachment_analysis(
                    analysis_id=str(analysis_records["image"].id),
                    content=analysis_text,
                )
            else:
                analysis_errors["image"] = "未提取到可用内容"
        except Exception as exc:
            logger.warning("[preprocess_node] image analysis failed: %s", exc)
            analysis_errors["image"] = str(exc)
        if "image" in analysis_errors:
            await agent.memory_service.finish_attachment_analysis(
                analysis_id=str(analysis_records["image"].id),
                content="",
                error_message=analysis_errors["image"],
            )

    if file_urls:
        try:
            analysis = await analyze_documents(
                current_username=username,
                file_urls=file_urls[:5],
                question="请分析这些文档",
            )
            summary = str(analysis.get("analysis_text") or "").strip()
            if summary:
                analysis_results["document"] = summary
                await agent.memory_service.finish_attachment_analysis(
                    analysis_id=str(analysis_records["document"].id),
                    content=summary,
                )
            else:
                analysis_errors["document"] = "未提取到可用内容"
        except Exception as exc:
            logger.warning("[preprocess_node] document analysis failed: %s", exc)
            analysis_errors["document"] = str(exc)
        if "document" in analysis_errors:
            await agent.memory_service.finish_attachment_analysis(
                analysis_id=str(analysis_records["document"].id),
                content="",
                error_message=analysis_errors["document"],
            )

    attachment_context = "\n".join(
        f"[{'图片' if analysis_type == 'image' else '文档'}] {content}"
        for analysis_type, content in analysis_results.items()
    )

    done_events: list[TutorRuntimeEvent] = []
    for index, (analysis_type, urls) in enumerate(activity_groups):
        if not urls:
            continue
        status = "done" if analysis_results.get(analysis_type) else "failed"
        event = TutorRuntimeEvent(
            type="agent_status",
            payload=build_attachment_status_payload(
                activity_id=f"attachment-{analysis_type}-{index}",
                status=status,
                file_names=[str(url).split("/")[-1] for url in urls],
                analysis_type=analysis_type,
                summary=analysis_results.get(analysis_type, "") if status == "done" else "",
                error=analysis_errors.get(analysis_type, "未提取到可用内容") if status == "failed" else "",
            ),
            sequence=len(state.get("stream_events", [])) + len(events) + 1 + index,
            timestamp=time.time(),
        )
        done_events.extend(await agent._emit_event(state, event))

    return {
        "attachment_context": attachment_context,
        "stream_events": events + done_events,
    }


# -----------------------------------------------------------------------
# 节点 2: react_node（ReAct Agent 循环）
# -----------------------------------------------------------------------


async def react_node(
    agent: Any,
    state: TutorAgentState,
    llm: Any,
    prompts: Any,
    memory_service: Any,
) -> dict:
    """ReAct 节点：LLM 自主决策工具调用，流式输出回答。

    流程：
    1. 构建工具集（per-request binding）
    2. 构建 system prompt（统一 tutor_agent.md）
    3. ReAct loop: LLM → tool_call → tool_result → LLM → ... → 最终回答
    4. 流式输出 answer_token（进入 SafetyBuffer）
    """
    question = state.get("question", "")
    history = state.get("history_messages", [])
    session_summary = state.get("session_summary", "")
    attachment_context = state.get("attachment_context", "")
    attachments = state.get("attachments", [])
    user_id = state.get("user_id", 0)
    session_id = state.get("session_id", "")
    user_message_id = state.get("user_message_id", 0)
    enable_web_search = state.get("enable_web_search", False)
    need_teaching_diagram = state.get("need_teaching_diagram", False)

    node_events: list[TutorRuntimeEvent] = []
    node_tool_invocations: list[dict[str, Any]] = []
    node_sources: list[dict[str, Any]] = []
    node_errors: list[str] = []
    full_answer = ""
    base_seq = len(state.get("stream_events", [])) + 1

    async def emit_research_status(event: Any) -> None:
        nonlocal base_seq
        base_seq += 1
        emitted = await agent._emit_event(
            state,
            TutorRuntimeEvent(
                type="agent_status",
                payload=build_research_status_payload(event),
                sequence=base_seq,
                timestamp=time.time(),
            ),
        )
        node_events.extend(emitted)

    # ── 1. 构建工具集 ──
    request_context = TutorRequestContext(
        user_id=user_id,
        username=state.get("username", ""),
        session_id=session_id,
        user_input=question,
        attachments=attachments,
        enable_web_search=enable_web_search,
        need_teaching_diagram=need_teaching_diagram,
    )
    tools = build_tutor_tools(
        request_context,
        research_event_handler=emit_research_status,
    )

    # ── 2. 构建 system prompt ──
    system_prompt = prompts.get("chat").render(
        "tutor_agent",
        session_summary_context=session_summary,
        file_context=f"附件 {len(attachments)} 个" if attachments else "本轮没有上传附件。",
        attachment_analysis_context=attachment_context or "本轮没有可用的附件预分析内容。",
        current_date=_current_date_text(),
    )

    # ── 3. 初始化消息和事件收集 ──
    human_content = question
    if attachment_context:
        human_content = f"{question}\n\n[附件分析结果]\n{attachment_context}"

    messages: list[AnyMessage] = [SystemMessage(content=system_prompt), *history, HumanMessage(content=human_content)]

    # ── 4. ReAct 循环 ──
    max_iterations = 8
    iteration = 0

    # 创建 ToolExcute 用于工具调用
    async def emit_tool_status(event: ToolRuntimeEvent) -> None:
        nonlocal base_seq
        base_seq += 1
        emitted = await agent._emit_event(
            state,
            TutorRuntimeEvent(
                type="agent_status",
                payload=build_agent_status_payload(event),
                sequence=base_seq,
                timestamp=time.time(),
            ),
        )
        node_events.extend(emitted)

    tool_excute = ToolExcute(tools=tools, event_handler=emit_tool_status)
    tool_model = (
        llm.model.bind_tools(tool_excute.get_tools_description())
        if tools
        else llm.model
    )
    format_repair_used = False

    while iteration < max_iterations:
        iteration += 1

        # ── 4.1 发送"正在思考"状态 ──
        thinking_event = TutorRuntimeEvent(
            type="agent_status",
            payload=build_workflow_activity_payload(
                stage="thinking",
                activity_id=f"thinking-iteration-{iteration}",
                title="分析思考过程",
                message=f"第 {iteration} 次推理：正在分析问题并规划回答策略...",
                status="running",
            ),
            sequence=base_seq + iteration * 10 - 1,
            timestamp=time.time(),
        )
        await agent._emit_event(state, thinking_event)

        # ── 4.2 流式调用 LLM（支持工具调用）──
        try:
            # 先收集完整一轮。只有流结束后才能可靠判断该轮是工具决策还是最终回答，
            # 因此不能在这里提前把文本作为 answer_token 发给前端。
            answer_text = ""
            seq = base_seq + iteration * 10
            accumulated_response = None  # 用于累积工具调用

            async for chunk in llm.astream(
                messages,
                model=tool_model,
            ):
                # 累积响应（用于最终获取完整的 tool_calls）
                accumulated_response = chunk if accumulated_response is None else accumulated_response + chunk

                # 文本可能是思考摘要、工具决策说明或最终回答，暂不对外发送。
                token = normalize_message_content(getattr(chunk, "content", ""))
                if token:
                    answer_text += token

                # 处理工具调用 chunks（流式累积）
                # tool_call_chunks 在流式过程中逐步到达
                tool_call_chunks = getattr(chunk, "tool_call_chunks", None)
                if tool_call_chunks:
                    # 工具调用正在生成，可以在这里发送状态
                    # 但完整的工具调用信息需要在流式结束后从 accumulated_response 获取
                    pass

            # ── 4.3 从累积的响应中获取完整的 tool_calls ──
            tool_calls = getattr(accumulated_response, "tool_calls", None) if accumulated_response else None
            reasoning_summary, answer_body = split_reasoning_and_answer(answer_text)

            has_final_answer = bool(answer_body)
            needs_format_repair = not tool_calls and not has_final_answer

            # 每轮 thinking 都必须收口；工具轮使用其决策文本作为降级摘要。
            thinking_done_event = TutorRuntimeEvent(
                type="agent_status",
                payload=build_workflow_activity_payload(
                    stage="thinking",
                    activity_id=f"thinking-iteration-{iteration}",
                    title="思考完成",
                    message=(
                        f"第 {iteration} 次推理完成，准备调用工具"
                        if tool_calls
                        else "回答边界校验未通过，正在重新整理"
                        if needs_format_repair
                        else f"第 {iteration} 次推理完成，开始生成回答"
                    ),
                    summary=_thinking_summary(
                        reasoning_summary,
                        iteration,
                        answer_text if tool_calls else "",
                    ),
                    status="failed" if needs_format_repair and format_repair_used else "done",
                ),
                sequence=base_seq + iteration * 10,
                timestamp=time.time(),
            )
            await agent._emit_event(state, thinking_done_event)

            if not tool_calls:
                if needs_format_repair:
                    if format_repair_used:
                        error_message = "模型未按 <answer>...</answer> 协议返回正式回答"
                        node_errors.append(error_message)
                        await agent._emit_event(
                            state,
                            TutorRuntimeEvent(
                                type="error",
                                payload={"error": error_message},
                                sequence=seq,
                                timestamp=time.time(),
                            ),
                        )
                        break

                    format_repair_used = True
                    if accumulated_response is not None:
                        messages.append(accumulated_response)
                    messages.append(HumanMessage(content=(
                        "[FORMAT REPAIR]\n"
                        "上一条响应缺少完整的最终回答边界。不要调用工具，不要重复内部推理。"
                        "请仅输出一条简短、可公开的进度摘要，随后把面向学生的完整回答严格放入 "
                        "<answer>...</answer> 中。"
                    )))
                    continue

                # 无工具调用 → 这是最终回答。思考 activity 完成后才发送纯正文。
                streamer = ResponseStreamer()
                async for chunk_event in streamer.stream_answer(answer_body, skip_blank=False):
                    chunk_token = chunk_event.get("data", "")
                    if chunk_token:
                        full_answer += chunk_token
                        event = TutorRuntimeEvent(
                            type="answer_token",
                            payload={"token": chunk_token},
                            sequence=seq,
                            timestamp=time.time(),
                        )
                        await agent._emit_event(state, event, persist=False)
                        seq += 1

                # 回答完成事件
                answer_done_event = TutorRuntimeEvent(
                    type="answer_done",
                    payload={"answer_length": len(full_answer)},
                    sequence=seq,
                    timestamp=time.time(),
                )
                await agent._emit_event(state, answer_done_event)

                break  # 跳出循环

            # ── 4.4 有 tool_calls → 执行工具 ──
            messages.append(accumulated_response)  # 添加完整的 AIMessage（含 tool_calls）

        except Exception as exc:
            logger.exception("[react_node] LLM streaming failed")
            return {
                "final_answer": "",
                "stream_events": node_events,
                "errors": [f"LLM streaming failed: {exc}"],
            }

        for tool_call in tool_calls:
            tool_call_id = str(tool_call.get("id", ""))
            tool_name = str(tool_call.get("name", ""))
            tool_args = tool_call.get("args", {}) if isinstance(tool_call.get("args"), dict) else {}

            # 执行工具
            runner = TutorToolRunner()
            context = ToolExecutionContext(
                user_id=user_id,
                session_id=session_id,
                user_message_id=user_message_id,
                memory_service=memory_service,
            )

            try:
                result = await runner.execute(
                    tool_name=tool_name,
                    arguments=tool_args,
                    tool_call_id=tool_call_id,
                    context=context,
                    tool_excute=tool_excute,
                )

                # 收集结果
                if result.invocation:
                    node_tool_invocations.append(result.invocation)
                node_sources.extend(result.sources)
                node_errors.extend(result.errors)

                # 添加 ToolMessage
                tool_result_text = str((result.invocation or {}).get("result_text", "") or "")
                messages.append(ToolMessage(content=tool_result_text, tool_call_id=tool_call_id))

            except Exception as exc:
                logger.warning("[react_node] tool %s failed: %s", tool_name, exc)
                node_errors.append(f"{tool_name}: {exc}")
                messages.append(ToolMessage(content=f"工具调用失败: {exc}", tool_call_id=tool_call_id))

    # ── 5. 返回 state 更新 ──
    return {
        "final_answer": full_answer,
        "messages": messages,
        "stream_events": node_events,
        "tool_invocations": node_tool_invocations,
        "sources": node_sources,
        "errors": node_errors,
    }
