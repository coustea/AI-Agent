"""聊天服务层 — 对话流编排、记忆管理、附件分析、文件上传。

核心函数：
  build_messages()  — 从数据库构建 LangChain 消息列表（含工具调用链）
  analysis_files()  — 调用大模型分析附件（先星火降级 GLM）
  chat()            — 总编排：build_messages → analysis_files → agent 推理循环 → 流式响应

ChatUseCases 保留会话管理、文件上传等辅助功能，对话核心逻辑由以上三个函数驱动。
"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, NamedTuple
from uuid import uuid4

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.chat.memory.service import get_chat_memory_service as _get_chat_memory_service
from app.chat.agent import ReasoningAgent
from app.chat.streaming import ResponseStreamer, SafetyBufferedResponseStreamer
from app.chat.schemas import (
    ConstraintReport, Evidence, EvidenceSet, FinalAnswer, FinalAnswerStream,
    ToolIntent, TurnRequest, UploadResponse,
)
from app.chat.stages import TeachingDiagramGenerator
from app.chat.tool_execute import TutorToolExecutor
from app.chat.utils import normalize_message_content
from app.chat.utils.vision import VisionService
from app.chat.utils.files import analyze_documents
from app.config import CHAT_DIR, MAX_UPLOAD_FILES_PER_REQUEST
from app.infra.database import session_scope
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatToolInvocation
from app.infra.prompts import prompts
from app.profile.service import get_profile_service

logger = get_logger(__name__)


# -----------------------------------------------------------------------
# 核心函数：build_messages / analysis_files / chat
# -----------------------------------------------------------------------

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
HISTORY_LIMIT = 20  # 从数据库读取的最近消息条数


def _normalize_tool_calls(tool_calls: list[dict] | None) -> list[dict]:
    """标准化工具调用格式，确保字段存在且类型正确。"""
    normalized: list[dict] = []
    for tc in tool_calls or []:
        if not isinstance(tc, dict):
            continue
        normalized.append({
            "id": str(tc.get("id", "")),
            "name": str(tc.get("name", "")),
            "args": tc.get("args", {}) if isinstance(tc.get("args", {}), dict) else {},
            "type": "tool_call",
        })
    return normalized


# ── 工具执行记录 ────────────────────────────────────────────────


class ToolExecutionRecord(BaseModel):
    """单次工具调用的完整记录 — 用于持久化和 transcript 投影。"""
    tool_call_id: str = Field(default_factory=lambda: f"tool-{uuid4().hex}")
    tool_name: str
    invoked_by: str = "agent"
    payload: dict[str, Any] = Field(default_factory=dict)
    raw_result: dict[str, Any] = Field(default_factory=dict)
    result_text: str = ""
    status: str = "success"
    evidence: list[dict[str, Any]] = Field(default_factory=list)


# ── Transcript 投影 ─────────────────────────────────────────────


def project_turn_run(
    final_answer: str,
    tool_records: list[ToolExecutionRecord],
    evidence: list[Evidence],
    attachment_analyses: list[dict[str, Any]],
) -> dict[str, Any]:
    """将推理结果投影为前端可消费的格式 — 消息列表 + 工具调用记录 + 知识来源。"""
    transcript_messages: list[dict[str, Any]] = []
    tool_invocations: list[dict[str, Any]] = []

    for record in tool_records:
        tool_call_id = record.tool_call_id
        tool_name = record.tool_name
        payload = record.payload
        result_text = record.result_text or _stringify_result(record.raw_result)

        transcript_messages.append({
            "role": "assistant",
            "content": f"正在调用工具：{tool_name}",
            "tool_calls": [{"id": tool_call_id, "name": tool_name, "args": payload}],
            "message_kind": "assistant_tool_request",
        })
        transcript_messages.append({
            "role": "tool",
            "content": result_text,
            "tool_call_id": tool_call_id,
            "message_kind": "tool_result",
        })
        tool_invocations.append({
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "arguments_json": payload,
            "result_text": result_text,
            "result_json": record.raw_result,
            "status": record.status,
        })

    if final_answer:
        transcript_messages.append({
            "role": "assistant",
            "content": final_answer,
            "tool_calls": [],
            "message_kind": "assistant_answer",
        })

    knowledge_sources = _collect_knowledge_sources(evidence)

    return {
        "transcript_messages": transcript_messages,
        "tool_invocations": tool_invocations,
        "knowledge_sources": knowledge_sources,
        "attachment_analyses": attachment_analyses,
    }


def _collect_knowledge_sources(evidence_items: list[Evidence]) -> list[dict[str, Any]]:
    """从证据列表中提取知识库和搜索来源。"""
    sources: list[dict[str, Any]] = []
    for item in evidence_items:
        if item.evidence_type == "knowledge_base":
            raw_sources = item.details.get("sources") if isinstance(item.details, dict) else []
            if isinstance(raw_sources, list):
                for source in raw_sources:
                    if isinstance(source, dict):
                        sources.append(source)
        elif item.evidence_type == "web_search":
            details = item.details if isinstance(item.details, dict) else {}
            sources.append({
                "source": details.get("tool_name") or "web_search",
                "query": details.get("query") or "",
                "summary": item.summary,
            })
    return sources


def _stringify_result(result: Any) -> str:
    """将工具返回结果统一转为字符串。"""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False)
    return str(result)


async def build_messages(user_id: int, session_id: str) -> list[AnyMessage]:
    """从数据库构建 LangChain 消息列表。

    流程：
    1. 查询 ChatMessage（按时间升序，最近 HISTORY_LIMIT 条）
    2. 查询 ChatToolInvocation（关联到这些消息的工具调用）
    3. 将消息转为 LangChain 类型：HumanMessage / AIMessage(tool_calls) / ToolMessage(tool_call_id)
    4. 在列表头部注入 SystemMessage（含会话压缩摘要）
    """
    svc = _get_chat_memory_service()

    # 查询历史消息
    raw_messages = await svc.list_messages(user_id=user_id, session_id=session_id, limit=HISTORY_LIMIT)

    # 查询工具调用记录，按 tool_call_id 建索引
    tool_invocations = await svc.list_tool_invocations(user_id=user_id, session_id=session_id, limit=50)
    invocations_by_id: dict[str, Any] = {}
    for inv in tool_invocations:
        tc_id = getattr(inv, "tool_call_id", None)
        if tc_id:
            invocations_by_id[tc_id] = inv

    # 转换为 LangChain 消息
    messages: list[AnyMessage] = []
    for msg in raw_messages:
        role = getattr(msg, "role", "")
        content = (getattr(msg, "content", "") or "").strip()
        tool_calls = getattr(msg, "tool_calls", None)
        tool_call_id = getattr(msg, "tool_call_id", None)

        if role == "user" and content:
            messages.append(HumanMessage(content=content))
        elif role in {"assistant", "ai"} and (content or tool_calls):
            # 如果有 tool_calls，构建 AIMessage(tool_calls=[...])
            normalized_tc = _normalize_tool_calls(tool_calls)
            if normalized_tc:
                messages.append(AIMessage(content=content, tool_calls=normalized_tc))
            elif content:
                messages.append(AIMessage(content=content))
        elif role == "system" and content:
            messages.append(SystemMessage(content=content))
        elif role == "tool" and tool_call_id:
            # ToolMessage 必须关联 tool_call_id
            tc_id_str = str(tool_call_id)
            messages.append(ToolMessage(content=content or "", tool_call_id=tc_id_str))

    # 注入会话压缩摘要到 SystemMessage
    summary_context = await svc.get_session_summary_context(user_id=user_id, session_id=session_id)
    system_content = f"以下是之前对话的压缩摘要，供你了解上下文：\n{summary_context}"

    return [SystemMessage(content=system_content), *messages]


async def analysis_files(attachments: list[str], user_id: int, session_id: str) -> str:
    """分析附件，返回分析结果文本。

    图片先走星火 OCR，降级 GLM-4V；文档走文本解析 + LLM 摘要。
    返回拼接后的分析上下文文本，供注入 LLM prompt。
    """
    if not attachments:
        return ""

    image_urls, file_urls = [], []
    for url in attachments:
        ext = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""
        if ext in IMAGE_EXTENSIONS:
            image_urls.append(url)
        else:
            file_urls.append(url)

    parts: list[str] = []

    # 图片分析：VisionService（先星火降级 GLM）
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
            logger.warning("[analysis_files] 图片分析失败: %s", exc)

    # 文档分析：提取文本 + LLM 摘要
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
            logger.warning("[analysis_files] 文档分析失败: %s", exc)

    return "\n".join(parts)


MAX_REASONING_STEPS = 4  # 推理循环最大步数


async def chat(
    *,
    user_id: int,
    session_id: str,
    user_input: str,
    attachments: list[str] | None = None,
    enable_web_search: bool = False,
    need_teaching_diagram: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """总编排函数：build_messages → analysis_files → agent 推理循环 → 流式响应。

    流程：
    1. 从数据库构建历史消息（build_messages）
    2. 如有附件，先分析附件（analysis_files），结果注入上下文
    3. 构建完整消息列表 [SystemMessage, ...历史, HumanMessage(当前问题+附件分析)]
    4. 推理循环：agent.reason() → ToolIntent → execute → 证据回填 → 再推理
    5. 流式输出 SSE 事件
    6. 后置教学图解生成
    7. 持久化结果，后台触发记忆管线和画像更新
    """
    uc = get_chat_usecases()
    effective_session = session_id or uc.default_session_id(user_id)
    merged_attachments = list(dict.fromkeys(attachments or []))
    current_message = (user_input or "").strip()

    if not current_message:
        yield {"event": "error", "data": "请输入您的问题。"}
        yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
        return

    logger.info(
        "[chat] 开始对话: user_id=%s session_id=%s msg_len=%d attachments=%d",
        user_id, effective_session, len(current_message), len(merged_attachments),
    )

    yield {
        "event": "status",
        "data": {
            "stage": "preparing_context",
            "message": "正在分析附件并准备本轮对话..." if merged_attachments else "正在准备本轮对话...",
        },
    }

    # ── 1. 创建 turn 记录 + 持久化用户消息 ──
    svc = uc._memory_service
    turn_id: int | None = None

    user_content = current_message
    if merged_attachments:
        image_urls, file_urls = [], []
        for url in merged_attachments:
            ext = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""
            if ext in IMAGE_EXTENSIONS:
                image_urls.append(url)
            else:
                file_urls.append(url)
        if image_urls:
            user_content += f" [Attached Images: {', '.join(image_urls)}]"
        if file_urls:
            user_content += f" [Attached Files: {', '.join(file_urls)}]"

    turn_row = await svc.create_turn(
        user_id=user_id, session_id=effective_session,
        route="default", execution_mode="default",
        has_attachments=bool(merged_attachments),
        used_web_search=enable_web_search,
        used_teaching_diagram=need_teaching_diagram,
        status="running",
    )
    turn_id = turn_row.id

    await svc.append_turn_event(
        user_id=user_id, session_id=effective_session, turn_id=turn_id,
        event_type="turn.started", payload={"status": "running"},
    )

    user_attachment_records = [
        {"url": url, "type": "image" if url.rsplit(".", 1)[-1].lower().split("?")[0] in IMAGE_EXTENSIONS else "document", "name": url.split("/")[-1]}
        for url in merged_attachments
    ] if merged_attachments else None

    await uc.save_message(
        user_id=user_id, session_id=effective_session,
        role="user", content=user_content,
        attachments=user_attachment_records,
        turn_id=turn_id, message_kind="user_input",
    )

    await svc.append_turn_event(
        user_id=user_id, session_id=effective_session, turn_id=turn_id,
        event_type="user.message", payload={"content": user_content},
    )

    # 首条消息时自动生成会话标题
    if await uc.count_messages(user_id, effective_session) <= 1:
        uc._spawn_background(
            svc.generate_session_title(user_id=user_id, session_id=effective_session, first_message=current_message),
            label="generate_title",
        )

    # ── 2. 分析附件 + 构建消息列表 ──
    attachment_context = ""
    if merged_attachments:
        yield {"event": "status", "data": {"stage": "attachment_analysis", "message": "正在分析附件内容..."}}
        attachment_context = await analysis_files(merged_attachments, user_id, effective_session)

    # 构建历史消息（含会话压缩摘要）
    history_messages = await build_messages(user_id, effective_session)

    # 构建当前问题的 HumanMessage，附加附件分析上下文
    human_content = current_message
    if attachment_context:
        human_content = f"{current_message}\n\n[附件分析结果]\n{attachment_context}"

    # 获取会话压缩摘要用于系统 prompt
    session_summary = await svc.get_session_summary_context(user_id=user_id, session_id=effective_session)
    system_prompt = prompts.get("chat").render(
        "tutor_system",
        session_summary_context=session_summary,
        file_context=f"附件 {len(merged_attachments)} 个" if merged_attachments else "本轮没有上传附件。",
        attachment_analysis_context=attachment_context or "本轮没有可用的附件预分析内容。",
        evaluation_summary_context="如需近期测验、薄弱点或学习计划依据，请调用 get_recent_evaluation 工具。",
    )

    messages = [SystemMessage(content=system_prompt), *history_messages, HumanMessage(content=human_content)]

    # ── 3. 推理循环 ──
    yield {"event": "status", "data": {"stage": "answer", "message": "正在组织回答..."}}

    agent = ReasoningAgent()
    constraints = ConstraintReport()
    evidence_set = EvidenceSet()
    tool_records: list[ToolExecutionRecord] = []
    tool_executor = TutorToolExecutor(request=TurnRequest(
        user_id=user_id, session_id=effective_session, user_input=current_message,
        attachments=merged_attachments, enable_web_search=enable_web_search,
        need_teaching_diagram=need_teaching_diagram,
    ))

    # 获取可用工具 schema
    tool_schema_provider = getattr(tool_executor, "tools", None)
    available_tools = tool_schema_provider() if callable(tool_schema_provider) else None

    full_answer = ""
    attachment_analyses: list[dict[str, Any]] = []

    try:
        stream_buffer = SafetyBufferedResponseStreamer(
            response_streamer=uc._response_streamer,
            safety_check=safety_filter.check,
            guard_chars=safety_filter.stream_guard_chars,
        )

        for _ in range(MAX_REASONING_STEPS):
            # 调用 agent 推理
            outcome = await agent.reason(messages, constraints, tools=available_tools)

            if isinstance(outcome, FinalAnswerStream):
                # 流式文本生成
                async for chunk in outcome.stream:
                    full_answer += chunk
                    async for event in stream_buffer.push(chunk):
                        yield event
                break

            if isinstance(outcome, FinalAnswer):
                full_answer = outcome.answer
                if full_answer:
                    async for event in stream_buffer.push(full_answer):
                        yield event
                break

            if isinstance(outcome, ToolIntent):
                # 执行工具
                constraints.executed_tools.append(outcome.tool_name)
                tool_result = await tool_executor.execute(outcome)
                status = str(tool_result.get("status") or "success") if isinstance(tool_result, dict) else "success"
                if status != "success":
                    constraints.failed_tools.append(outcome.tool_name)

                tool_records.append(ToolExecutionRecord(
                    tool_name=str(tool_result.get("tool_name") or outcome.tool_name) if isinstance(tool_result, dict) else outcome.tool_name,
                    invoked_by="agent",
                    payload=outcome.payload,
                    raw_result=tool_result if isinstance(tool_result, dict) else {},
                    result_text=str((tool_result or {}).get("result_text") or "") if isinstance(tool_result, dict) else "",
                    status=status,
                    evidence=(tool_result or {}).get("evidence", []) if isinstance(tool_result, dict) else [],
                ))

                # 证据回填
                evidence_items = (tool_result or {}).get("evidence") if isinstance(tool_result, dict) else None
                if evidence_items:
                    evidence_set.extend([Evidence.model_validate(e) if isinstance(e, dict) else e for e in evidence_items])

                # 将工具结果追加到消息列表，供下一轮推理使用
                tool_call_id = f"call-{len(tool_records)}"
                messages.append(AIMessage(
                    content="",
                    tool_calls=[{"id": tool_call_id, "name": outcome.tool_name, "args": outcome.payload, "type": "tool_call"}],
                ))
                result_text = str((tool_result or {}).get("result_text") or "") if isinstance(tool_result, dict) else ""
                messages.append(ToolMessage(content=result_text, tool_call_id=tool_call_id))

                continue

            break
        else:
            constraints.max_steps_reached = True

        async for event in stream_buffer.flush():
            yield event

    except Exception as exc:
        logger.exception("[chat] 推理执行失败")
        if turn_id is not None:
            await svc.append_turn_event(
                user_id=user_id, session_id=effective_session, turn_id=turn_id,
                event_type="turn.failed", payload={"error": str(exc)},
            )
            await svc.update_turn(
                user_id=user_id, session_id=effective_session, turn_id=turn_id,
                status="failed", route="default", execution_mode="default",
                used_web_search=enable_web_search, used_teaching_diagram=need_teaching_diagram,
                error_message=str(exc),
            )
        yield {"event": "error", "data": f"服务器出错: {exc}"}
        yield {"event": "done", "data": {"session_id": effective_session, "error": True}}
        return

    # ── 4. 后置教学图解 ──
    teaching_diagram: dict[str, Any] | None = None
    if need_teaching_diagram and full_answer:
        try:
            teaching_diagram = await TeachingDiagramGenerator().generate(
                TurnRequest(
                    user_id=user_id, session_id=effective_session, user_input=current_message,
                    attachments=merged_attachments, enable_web_search=enable_web_search,
                    need_teaching_diagram=need_teaching_diagram,
                ),
                full_answer, evidence_set,
            )
        except Exception as exc:
            logger.warning("[chat] 图解生成失败: %s", exc)

    # ── 5. 后处理：安全过滤、持久化 ──
    if full_answer:
        safety_result = await safety_filter.check(full_answer)
        if safety_result.has_violation:
            full_answer = safety_result.sanitized_text
            yield {"event": "status", "data": {"stage": "safety_filter", "message": "内容触发安全策略，已进行部分过滤"}}

    if teaching_diagram is not None:
        yield {"event": "diagram", "data": teaching_diagram}

    projection = project_turn_run(full_answer, tool_records, evidence_set.items, attachment_analyses)
    tool_calls = [
        {"id": item["tool_call_id"], "name": item["tool_name"], "args": item.get("arguments_json") or {}}
        for item in projection["tool_invocations"]
    ]
    knowledge_sources = list(projection["knowledge_sources"])

    # ── 持久化助手回复和工具调用 ──
    if turn_id is not None:
        yield {"event": "status", "data": {"stage": "persisting_turn", "message": "正在保存本轮学习记录..."}}

        transcript_messages = list(projection["transcript_messages"])
        assistant_messages = [item for item in transcript_messages if str(item.get("role") or "") == "assistant"]
        if assistant_messages:
            for index, am in enumerate(assistant_messages):
                content = str(am.get("content") or "")
                if index == len(assistant_messages) - 1 and full_answer:
                    content = full_answer
                await uc.save_message(
                    user_id=user_id, session_id=effective_session,
                    role="assistant", content=content,
                    tool_calls=am.get("tool_calls") if isinstance(am.get("tool_calls"), list) else None,
                    knowledge_sources=knowledge_sources if index == len(assistant_messages) - 1 else None,
                    teaching_diagram=teaching_diagram if index == len(assistant_messages) - 1 else None,
                    attachment_analyses=attachment_analyses if index == len(assistant_messages) - 1 else None,
                    turn_id=turn_id,
                    message_kind=str(am.get("message_kind") or "assistant_answer"),
                )
        else:
            await uc.save_message(
                user_id=user_id, session_id=effective_session,
                role="assistant", content=full_answer,
                tool_calls=tool_calls, knowledge_sources=knowledge_sources,
                teaching_diagram=teaching_diagram, attachment_analyses=attachment_analyses,
                turn_id=turn_id, message_kind="assistant_answer",
            )

        for tm in transcript_messages:
            if str(tm.get("role") or "") != "tool":
                continue
            await uc.save_message(
                user_id=user_id, session_id=effective_session,
                role="tool", content=str(tm.get("content") or ""),
                tool_call_id=str(tm.get("tool_call_id") or ""),
                turn_id=turn_id, message_kind="tool_result",
            )

        await svc.save_tool_invocations(
            user_id=user_id, session_id=effective_session,
            turn_id=turn_id, invocations=projection["tool_invocations"],
        )

        await svc.append_turn_event(
            user_id=user_id, session_id=effective_session, turn_id=turn_id,
            event_type="answer.completed", payload={"answer": full_answer},
        )
        await svc.finalize_turn_transcript(
            user_id=user_id, session_id=effective_session, turn_id=turn_id,
            status="completed", final_answer=full_answer,
            constraint_report=constraints.model_dump(),
        )
        await svc.update_turn(
            user_id=user_id, session_id=effective_session, turn_id=turn_id,
            status="completed", route="answer", execution_mode="answer",
            used_web_search=enable_web_search, used_teaching_diagram=need_teaching_diagram,
            error_message=None,
        )

    # ── 后台任务：记忆管线和画像更新 ──
    if full_answer:
        uc._spawn_background(
            svc.after_turn(
                user_id=user_id, session_id=effective_session,
                user_message=current_message, assistant_reply=full_answer,
            ),
            label="memory_pipeline",
        )
        uc._spawn_background(
            uc._update_learner_profile(user_id=user_id, session_id=effective_session),
            label="profile_update",
        )

    yield {
        "event": "done",
        "data": {
            "session_id": effective_session,
            "full_response": full_answer,
            "knowledge_sources": knowledge_sources,
            "teaching_diagram": teaching_diagram,
            "tool_calls": tool_calls,
            "attachment_analyses": attachment_analyses,
        },
    }


# -----------------------------------------------------------------------
# 内容安全过滤（原 utils/safety.py 内联）
# -----------------------------------------------------------------------

class SafetyResult(NamedTuple):
    """安全检查结果：是否触发违规 + 脱敏后的文本。"""
    has_violation: bool
    sanitized_text: str

class ContentSafetyFilter:
    """基于正则的敏感词过滤器。

    工作原理：
    1. 预编译正则匹配所有敏感词（色情/赌博/毒品/暴力）
    2. check() 方法对文本执行全文扫描，命中则替换为 ***
    3. stream_guard_chars 用于流式场景：需要缓存最后 N 个字符，
       防止敏感词被流式切分导致漏检（例如 "色"+"情" 分两次推送）

    注意：这是一个轻量级防护，复杂的语义级安全判断应由上游 LLM 完成。
    """

    def __init__(self):
        # 敏感词列表 — 可扩展
        self.sensitive_terms = ("色情", "赌博", "毒品", "暴力")
        # 预编译正则：将所有敏感词用 | 连接，一次扫描全部命中
        self.sensitive_patterns = [
            re.compile("|".join(re.escape(term) for term in self.sensitive_terms), re.IGNORECASE)
        ]
        # 流式缓冲的守卫字符数：最长敏感词长度 - 1，确保流式切分不会漏检
        self.stream_guard_chars = max(1, max(len(term) for term in self.sensitive_terms) - 1)

    async def check(self, text: str) -> SafetyResult:
        """对文本执行敏感词检查并脱敏。

        返回 SafetyResult：has_violation 表示是否触发，sanitized_text 是脱敏后文本。
        空文本直接返回无违规，避免无谓的正则扫描。
        """
        if not text:
            return SafetyResult(has_violation=False, sanitized_text=text)
        sanitized = text
        has_violation = False
        for pattern in self.sensitive_patterns:
            if pattern.search(sanitized):
                has_violation = True
                # 将所有匹配的敏感词替换为 ***
                sanitized = pattern.sub("***", sanitized)
        return SafetyResult(has_violation=has_violation, sanitized_text=sanitized)

# 全局单例过滤器，所有 ChatUseCases 实例共享同一份正则编译结果
safety_filter = ContentSafetyFilter()


# -----------------------------------------------------------------------
# 本地文件存储（原 utils/storage.py 内联）
# -----------------------------------------------------------------------

class LocalFileStore:
    """用户上传文件的本地存储。

    目录结构: {CHAT_DIR}/{user_id}/{session_id}/{filename}
    每个用户每个会话独立一个文件夹，避免文件名冲突。
    支持的文件类型分为图片（≤5MB）和文档（≤10MB）两类。
    """

    def __init__(self) -> None:
        self.upload_dir = CHAT_DIR  # 上传文件根目录，来自 config.yaml
        # 允许的图片扩展名（小写，带点号）
        self.allowed_image_ext = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        # 允许的文档扩展名
        self.allowed_doc_ext = {".pdf", ".docx", ".txt", ".md", ".log", ".xlsx", ".xls", ".csv", ".tsv"}
        # 图片大小上限 5MB
        self.max_image_size = 5 * 1024 * 1024
        # 文档大小上限 10MB
        self.max_doc_size = 10 * 1024 * 1024

    def list_files(self, *, user_id: int, session_id: str) -> list[Path]:
        """列出指定会话目录下的所有上传文件。"""
        # 路径: {CHAT_DIR}/{user_id}/{session_id}/
        session_dir = self.upload_dir / str(user_id) / session_id
        if not session_dir.exists():
            return []
        # 只返回文件，忽略子目录
        return [path for path in session_dir.iterdir() if path.is_file()]

    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        user_id: int,
        session_id: str,
    ) -> dict:
        """保存用户上传的文件到磁盘。

        流程：
        1. 根据扩展名判断文件类型（图片/文档）和大小上限
        2. 校验文件大小，超限抛出 ValueError
        3. 创建会话目录（不存在则递归创建）
        4. 对文件名做安全清洗，防止路径穿越
        5. 写入磁盘并返回 UploadResponse 元数据
        """
        suffix = Path(filename).suffix.lower()
        # 根据扩展名确定文件类型和大小上限
        if suffix in self.allowed_image_ext:
            file_type = "image"
            max_size = self.max_image_size
        elif suffix in self.allowed_doc_ext:
            file_type = "document"
            max_size = self.max_doc_size
        else:
            raise ValueError(f"不支持的文件类型: {suffix}")

        # 文件大小校验
        if len(content) > max_size:
            raise ValueError(f"文件大小超过限制（{max_size // (1024 * 1024)}MB）")

        # 创建用户-会话目录: {CHAT_DIR}/{user_id}/{session_id}/
        session_dir = self.upload_dir / str(user_id) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # 文件名安全清洗：去除非法字符，过长则截断
        safe_name = self._safe_filename(filename)
        if not safe_name:
            # 文件名清洗后为空，用时间戳兜底
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = f"{timestamp}{suffix}"

        # 写入磁盘
        file_path = session_dir / safe_name
        file_path.write_bytes(content)

        # 返回文件元数据，供前端和附件分析器使用
        return UploadResponse(
            url=f"/api/v1/ai/chat/uploads/{user_id}/{session_id}/{safe_name}",
            file_type=file_type,
            original_name=filename,
            size_bytes=len(content),
            storage_key=f"{user_id}/{session_id}/{safe_name}",
            mime_type=_guess_mime_type(suffix),
            extension=suffix,
        ).model_dump()

    def _safe_filename(self, filename: str) -> str:
        """清洗文件名：移除危险字符，限制长度。

        移除 \ / * ? : " < > | 等文件系统特殊字符，
        文件名超过 100 字符时截断（保留扩展名），防止路径过长。
        """
        safe = re.sub(r'[\\/*?:"<>|]', "", filename).strip()
        if len(safe) > 100:
            name, ext = Path(safe).stem, Path(safe).suffix
            safe = f"{name[:100 - len(ext)]}{ext}"
        return safe

    def resolve_user_file(
        self,
        *,
        current_user_id: int,
        owner_id: int,
        session_id: str,
        filename: str,
    ) -> Path:
        """安全地解析用户文件路径，防止路径穿越攻击。

        多层防护：
        1. 权限校验：只能访问自己的文件
        2. 禁止 .. 目录遍历
        3. 只允许特定子目录（diagrams）
        4. 解析后检查路径是否仍在 session_dir 内
        """
        if owner_id != current_user_id:
            raise PermissionError("无权访问该文件")

        filename_path = Path(filename)
        # 禁止 .. 目录遍历
        if ".." in filename_path.parts:
            raise ValueError("非法文件名")

        # 子目录白名单检查：只允许 diagrams 子目录
        if filename_path.parent != Path("."):
            parent_name = filename_path.parent.name
            if parent_name not in {"diagrams"}:
                raise ValueError("非法子目录")
            if filename_path.name != filename_path.parts[-1]:
                raise ValueError("非法文件名")
            else:
                # 文件名必须与原始输入完全一致
                if filename_path.name != filename:
                    raise ValueError("非法文件名")

        # 解析真实路径，确保没有逃逸出 session_dir
        session_dir = (self.upload_dir / str(owner_id) / session_id).resolve()
        file_path = (session_dir / filename).resolve()
        if not str(file_path).startswith(str(session_dir)):
            raise ValueError("非法文件路径")
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("文件不存在")
        return file_path


def _guess_mime_type(suffix: str) -> str:
    """根据文件扩展名推断 MIME 类型，未知类型返回 octet-stream。"""
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".log": "text/plain",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".csv": "text/csv",
        ".tsv": "text/tab-separated-values",
    }
    return mapping.get(suffix, "application/octet-stream")



class ChatMessageItem:
    """对话消息数据模型，用于历史记录查询和前端渲染。

    字段说明：
    - id: 消息数据库主键
    - role: user / assistant / tool
    - content: 消息正文
    - attachments: 附件列表（图片/文件）
    - tool_calls: 工具调用记录（搜索、图解等）
    - tool_call_id: 关联的工具调用 ID（tool 角色消息使用）
    - knowledge_sources: 知识来源（搜索结果引用）
    - attachment_analyses: 附件分析结果（图片描述/文档摘要）
    - teaching_diagram: 教学图解数据
    - turn_id: 所属 turn 的 ID
    - message_kind: 消息分类（user_input / assistant_answer / tool_result 等）
    - created_at: 创建时间
    """

    def __init__(
        self,
        *,
        id: int,
        role: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        knowledge_sources: list[dict[str, Any]] | None = None,
        attachment_analyses: list[dict[str, Any]] | None = None,
        teaching_diagram: dict[str, Any] | None = None,
        turn_id: int | None = None,
        message_kind: str | None = None,
        created_at: Any = None,
    ) -> None:
        self.id = id
        self.role = role
        self.content = content
        self.attachments = attachments
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
        self.knowledge_sources = knowledge_sources
        self.attachment_analyses = attachment_analyses
        self.teaching_diagram = teaching_diagram
        self.turn_id = turn_id
        self.message_kind = message_kind
        self.created_at = created_at

    def model_dump(self) -> dict[str, Any]:
        """序列化为字典，用于 JSON API 响应。

        只包含有值的字段，避免返回大量 null。
        附件会递归调用自身的 model_dump()。
        """
        data: dict[str, Any] = {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
        }
        if self.attachments:
            data["attachments"] = self.attachments
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.knowledge_sources:
            data["knowledge_sources"] = self.knowledge_sources
        if self.attachment_analyses:
            data["attachment_analyses"] = self.attachment_analyses
        if self.teaching_diagram:
            data["teaching_diagram"] = self.teaching_diagram
        if self.turn_id is not None:
            data["turn_id"] = self.turn_id
        if self.message_kind:
            data["message_kind"] = self.message_kind
        return data


class ChatUseCases:
    """聊天服务核心类 — 编排完整的对话生命周期。

    职责：
    1. 请求解析和会话管理（创建/归档/查询）
    2. 附件上传、存储和分析
    3. 流式对话（SSE 事件流）
    4. 安全过滤（敏感词检测）
    5. 消息持久化（消息、工具调用、turn 事件）
    6. 后台任务（记忆管线、画像更新）

    通过 get_chat_usecases() 获取单例，避免重复初始化。
    """

    def __init__(self) -> None:
        # 记忆服务：管理会话、消息、turn 事件的持久化
        self._memory_service = get_chat_memory_service()
        # 本地文件存储：用户上传文件的磁盘读写
        self.file_store: LocalFileStore = LocalFileStore()
        # 后台任务集合：防止未等待的协程被 GC 回收
        self._background_tasks: set[asyncio.Task] = set()
        # 已上传文件的 URL→数据库 ID 映射
        self._uploaded_file_ids_by_url: dict[str, int] = {}
        # 响应流生成器：将 LLM 输出转为 SSE 事件
        self._response_streamer = ResponseStreamer()

    def default_session_id(self, user_id: int) -> str:
        """生成默认会话 ID — 格式: user-{user_id}-default-mentor。"""
        return f"user-{user_id}-default-mentor"

    async def list_sessions(self, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        """列出用户的最近 N 个会话，按更新时间倒序。"""
        sessions = await self._memory_service.list_sessions(user_id=user_id, limit=limit)
        return [{"id": item.id, "title": item.title, "updated_at": item.updated_at} for item in sessions]

    async def create_session(self, user_id: int, title: str = "新对话") -> dict[str, Any]:
        """创建新会话，默认标题为"新对话"，后续由后台任务自动生成标题。"""
        session = await self._memory_service.create_session(user_id=user_id, title=title)
        return {"id": session.id, "title": session.title}

    async def archive_session(self, user_id: int, session_id: str) -> bool:
        """归档会话（软删除），不物理删除消息数据。"""
        return await self._memory_service.archive_session(user_id=user_id, session_id=session_id)

    async def update_session_title(self, user_id: int, session_id: str, title: str) -> bool:
        """更新会话标题。"""
        return await self._memory_service.update_session_title(user_id=user_id, session_id=session_id, title=title)

    async def get_history(
        self,
        *,
        user_id: int,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[ChatMessageItem]:
        """获取会话历史消息，组装为 ChatMessageItem 列表。

        流程：
        1. 若未指定 session_id，自动取用户最近的会话
        2. 查询消息列表和附件分析结果
        3. 按 message_id 分组附件分析
        4. 查询附件绑定关系（新旧两种存储格式兼容）
        5. 组装 ChatMessageItem 返回
        """
        if not session_id:
            sessions = await self._memory_service.list_sessions(user_id=user_id, limit=1)
            if not sessions:
                return []
            session_id = sessions[0].id

        # 查询原始消息列表
        raw_messages = await self._memory_service.list_messages(user_id=user_id, session_id=session_id, limit=limit)
        # 查询附件分析结果（图片描述/文档摘要）
        attachment_analyses = await self._memory_service.list_attachment_analyses(
            user_id=user_id,
            session_id=session_id,
            limit=max(limit, 20),
        )
        # 按 message_id 分组附件分析结果，供后续组装使用
        analyses_by_message_id: dict[int, list[dict[str, Any]]] = {}
        for analysis in attachment_analyses:
            message_id = getattr(analysis, "message_id", None)
            if not message_id:
                continue
            analyses_by_message_id.setdefault(message_id, []).append(
                {
                    "id": getattr(analysis, "id", None),
                    "file_id": getattr(analysis, "file_id", None),
                    "file_name": getattr(analysis, "file_name", None),
                    "file_url": getattr(analysis, "file_url", None),
                    "analysis_type": getattr(analysis, "analysis_type", ""),
                    "summary_text": getattr(analysis, "summary_text", ""),
                    "structured_json": getattr(analysis, "structured_json", None),
                }
            )
        # 查询附件绑定关系：新版本用 message_attachments 表，旧版本用 message.attachments 字段
        attachment_records_by_message_id = await self._memory_service.list_message_attachments(
            user_id=user_id,
            session_id=session_id,
            message_ids=[item.id for item in raw_messages if getattr(item, "id", None) is not None],
        )
        # 组装 ChatMessageItem 列表
        result: list[ChatMessageItem] = []
        for message in raw_messages:
            parsed_attachments = None
            # 优先使用新版本的附件绑定关系
            bound_attachments = attachment_records_by_message_id.get(message.id, []) if isinstance(attachment_records_by_message_id, dict) else []
            if bound_attachments:
                parsed_attachments = [
                    {"url": item.get("url", ""), "type": item.get("type", ""), "name": item.get("name", "")}
                    for item in bound_attachments
                ]
            elif message.attachments:
                # 兼容旧版本：附件信息直接存储在 message.attachments 字段（JSON 字符串或列表）
                try:
                    raw = message.attachments if isinstance(message.attachments, list) else json.loads(message.attachments)
                    parsed_attachments = [
                        {"url": item.get("url", ""), "type": item.get("type", ""), "name": item.get("name", "")}
                        for item in raw
                    ]
                except Exception:
                    parsed_attachments = None
            # 组装 ChatMessageItem
            result.append(
                ChatMessageItem(
                    id=message.id,
                    role=message.role,
                    content=message.content,
                    attachments=parsed_attachments,
                    tool_calls=message.tool_calls if isinstance(message.tool_calls, list) else None,
                    tool_call_id=getattr(message, "tool_call_id", None),
                    knowledge_sources=message.knowledge_sources if isinstance(message.knowledge_sources, list) else None,
                    attachment_analyses=analyses_by_message_id.get(message.id, []),  # 关联的附件分析结果
                    teaching_diagram=message.teaching_diagram if isinstance(message.teaching_diagram, dict) else None,
                    turn_id=getattr(message, "turn_id", None),
                    message_kind=getattr(message, "message_kind", None),
                    created_at=message.created_at,
                )
            )
        return result

    async def save_message(
        self,
        *,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        knowledge_sources: list[dict[str, Any]] | None = None,
        attachment_analyses: list[dict[str, Any]] | None = None,
        teaching_diagram: dict[str, Any] | None = None,
        usage_metadata: dict[str, Any] | None = None,
        turn_id: int | None = None,
        message_kind: str | None = None,
    ) -> None:
        """保存单条消息到数据库。

        由 chat() 在流式结束后调用，持久化用户消息和助手回复。
        turn_id 将消息关联到具体的对话轮次，便于后续记忆管线处理。
        """
        await self._memory_service.save_message(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            attachments=attachments,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            knowledge_sources=knowledge_sources,
            attachment_analyses=attachment_analyses,
            teaching_diagram=teaching_diagram,
            usage_metadata=usage_metadata,
            turn_id=turn_id,
            message_kind=message_kind,
        )

    async def count_messages(self, user_id: int, session_id: str) -> int:
        """统计会话中的消息总数。"""
        return await self._memory_service.count_messages(user_id=user_id, session_id=session_id)

    async def clear_history(self, user_id: int, session_id: str) -> int:
        """清空会话历史：删除短期消息并重置计数器。

        返回删除的消息数量。注意：只删除短期消息，长期记忆保留。
        """
        deleted_count = await self._memory_service.delete_short_term_messages(user_id=user_id, session_id=session_id)
        await self._memory_service.reset_session_counters(user_id=user_id, session_id=session_id)
        return deleted_count

    async def save_upload(
        self,
        *,
        filename: str,
        content: bytes,
        user_id: int,
        session_id: str,
    ) -> dict[str, Any]:
        """保存用户上传的文件：磁盘存储 + 数据库记录。

        流程：
        1. 校验文件名非空
        2. 检查单次上传文件数是否超限
        3. 调用 LocalFileStore 写入磁盘
        4. 在数据库中保存文件记录
        5. 维护 URL→数据库 ID 映射，供附件分析器引用
        """
        if not filename:
            raise ValueError("文件名不能为空")
        # 检查文件数上限
        existing = self.file_store.list_files(user_id=user_id, session_id=session_id)
        if len(existing) >= MAX_UPLOAD_FILES_PER_REQUEST:
            raise ValueError(f"单次上传最多 {MAX_UPLOAD_FILES_PER_REQUEST} 个文件")
        # 写入磁盘
        payload = await self.file_store.save_upload(
            filename=filename,
            content=content,
            user_id=user_id,
            session_id=session_id,
        )
        # 保存文件记录到数据库，返回带 ID 的记录
        file_record = await self._memory_service.save_uploaded_file(user_id=user_id, session_id=session_id, payload=payload)
        # 维护 URL→文件 ID 映射，附件分析器需要用这个 ID 引用文件
        self._uploaded_file_ids_by_url[str(payload.get("url") or "")] = file_record.id
        return payload

    def resolve_uploaded_file(
        self,
        *,
        current_user_id: int,
        owner_id: int,
        session_id: str,
        filename: str,
    ) -> Path:
        """解析上传文件路径，带权限校验。

        只有文件所有者才能访问，防止越权读取。
        实际路径解析委托给 LocalFileStore.resolve_user_file。
        """
        if current_user_id != owner_id:
            raise PermissionError("无权访问此文件")
        return self.file_store.resolve_user_file(
            current_user_id=current_user_id,
            owner_id=owner_id,
            session_id=session_id,
            filename=filename,
        )

    async def _update_learner_profile(self, *, user_id: int, session_id: str) -> None:
        """根据对话内容更新学习者画像（后台执行）。"""
        await get_profile_service().maybe_update_from_tutoring_turn(user_id=user_id, session_id=session_id)

    def _spawn_background(self, coro, *, label: str = "") -> None:
        """安全地启动后台协程任务。

        关键设计：
        1. 任务加入 _background_tasks 集合，防止被 GC 回收
        2. 完成回调自动从集合移除，避免内存泄漏
        3. 异常被 catch 并记录日志，不会影响主流程
        4. 若当前不在事件循环中（极端情况），记录警告而非崩溃
        """
        async def _run() -> None:
            try:
                await coro
            except Exception as exc:
                logger.error("[ChatUseCases] 后台任务失败 label=%s err=%s", label, exc)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            # 确保任务被引用，不会被垃圾回收
            task = asyncio.ensure_future(_run())
            self._background_tasks.add(task)
            # 完成后自动从集合移除
            task.add_done_callback(self._background_tasks.discard)
        else:
            logger.warning("[ChatUseCases] 无法在非事件循环中启动后台任务 label=%s", label)


# ── 单例管理 ──
# 两个独立单例：主对话和数字人对话，避免共享状态（如 _uploaded_file_ids_by_url）
_chat_usecases: ChatUseCases | None = None
_avatar_chat_usecases: ChatUseCases | None = None


def get_chat_usecases() -> ChatUseCases:
    """获取主对话的 ChatUseCases 单例。

    懒加载模式：首次调用时创建实例，后续复用。
    """
    global _chat_usecases
    if _chat_usecases is None:
        _chat_usecases = ChatUseCases()
    return _chat_usecases


def get_chat_memory_service():
    """获取记忆服务实例，委托给 memory 模块的工厂函数。"""
    return _get_chat_memory_service()


def get_avatar_chat_usecases() -> ChatUseCases:
    """获取数字人对话的 ChatUseCases 单例。

    与主对话单例独立，避免上传文件映射等状态互相干扰。
    """
    global _avatar_chat_usecases
    if _avatar_chat_usecases is None:
        _avatar_chat_usecases = ChatUseCases()
    return _avatar_chat_usecases
