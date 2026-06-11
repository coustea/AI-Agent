"""推理 Agent — 决定「需要调工具还是直接回答」+ 构建推理 prompt。

调用链路：TurnOrchestrator → ReasoningAgent.reason() → LangChain tool call 或 LLM 回答

决策流程：
  1. 构建 reasoning prompt 并绑定可用工具
  2. 若模型选择工具 → 返回 ToolIntent，由 orchestrator 执行后再次进入推理循环
  3. 若模型未选择工具 → 返回 FinalAnswer

Prompt 构建三要素：
  - 会话摘要上下文（压缩后的历史）
  - 学习评估摘要（测验分数、薄弱点）
  - 附件分析上下文 + 已收集证据
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.chat.schemas import ConstraintReport, EvidenceSet, FinalAnswer, ToolIntent, TurnRequest
from app.chat.runtime import _classify_attachments, history_to_langchain_messages
from app.chat.memory.service import get_chat_memory_service
from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.chat.utils import normalize_message_content


# ── Prompt 构建 ──────────────────────────────────────────────────


def build_file_context(attachments: list[str]) -> str:
    """将附件列表转为简短描述文本，嵌入系统 prompt 告知模型当前附件情况。"""
    if not attachments:
        return "本轮没有上传附件。"
    image_urls, file_urls = _classify_attachments(attachments)
    parts: list[str] = []
    if image_urls:
        parts.append(f"图片附件 {len(image_urls)} 个")
    if file_urls:
        parts.append(f"文档附件 {len(file_urls)} 个")
    return "，".join(parts) if parts else "本轮没有上传附件。"


async def build_tutor_system_prompt(
    *,
    user_id: int,
    session_id: str,
    attachments: list[str],
    attachment_context: str,
) -> str:
    """组装辅导老师系统 prompt，注入三路上下文：会话摘要、评估记录、附件分析。"""
    # 压缩后的历史摘要，提供跨轮次对话连贯性
    session_summary_context = await get_chat_memory_service().get_session_summary_context(
        user_id=user_id,
        session_id=session_id,
    )
    evaluation_summary_context = "如需近期测验、薄弱点或学习计划依据，请调用 get_recent_evaluation 工具。"

    return prompts.get("chat").render(
        "tutor_system",
        session_summary_context=session_summary_context,
        file_context=build_file_context(attachments),
        attachment_analysis_context=attachment_context or "本轮没有可用的附件预分析内容。",
        evaluation_summary_context=evaluation_summary_context,
    )


async def build_reasoning_messages(
    *,
    request: TurnRequest,
    evidence_set: EvidenceSet,
    constraint_report: ConstraintReport,
) -> list[Any]:
    """构建 LLM 推理用的完整消息列表：系统 prompt + 历史消息 + 当前问题（含证据）。"""
    # 从 evidence_set 中提取附件分析结果作为上下文
    attachment_context = "\n".join(
        item.summary for item in evidence_set.items if item.evidence_type == "attachment"
    ).strip()
    system_prompt = await build_tutor_system_prompt(
        user_id=request.user_id,
        session_id=request.session_id,
        attachments=request.attachments,
        attachment_context=attachment_context,
    )
    # 构建人类消息：问题 + 已有证据摘要 + 本轮工具执行情况
    evidence_text = "\n".join(f"- {item.summary}" for item in evidence_set.for_answer()) or "无"
    executed_tools = ", ".join(constraint_report.executed_tools) if constraint_report.executed_tools else "无"
    # 截取最近 N 条历史避免 token 溢出
    history_messages = history_to_langchain_messages(request.history[-request.history_limit:]) if request.history else []
    question_prompt = HumanMessage(
        content=(
            "你是一个智能辅导老师。请先判断是否需要调用工具，再回答学生。\n"
            "工具使用原则：\n"
            "- 涉及学生目标、背景、偏好时，调用 get_learner_profile。\n"
            "- 涉及之前、上次、长期偏好或稳定薄弱点时，调用 get_long_term_memory。\n"
            "- 涉及课程知识、定义、教材内容时，调用 search_knowledge_base。\n"
            "- 涉及最新、今天、目前、刚刚发生的信息时，调用 web_search。\n"
            "- 涉及薄弱点补救、学习计划、练习建议时，调用 get_recent_evaluation。\n"
            "- 涉及上传的图片或文档细节时，调用 analyze_attachment。\n"
            "如果已有证据足够，就直接回答。证据不足时说明缺口，不要编造。\n\n"
            f"学生当前问题：{request.message}\n"
            f"已知证据：\n{evidence_text}\n\n"
            f"本轮已执行工具：{executed_tools}"
        )
    )
    return [SystemMessage(content=system_prompt), *history_messages, question_prompt]


# ── 推理 Agent ──────────────────────────────────────────────────


class ReasoningAgent:
    """LangChain tool-calling tutor agent.

    The orchestrator still owns actual tool execution. This agent only lets the model
    choose a typed tool and converts that tool call into the existing ToolIntent contract.
    """

    def __init__(self, llm: Any | None = None, tools: list[Any] | None = None) -> None:
        self.llm = llm or get_llm()
        self.tools = list(tools or [])

    async def reason(
        self,
        request: TurnRequest,
        evidence_set: EvidenceSet,
        constraints: ConstraintReport,
        tools: list[Any] | None = None,
    ) -> ToolIntent | FinalAnswer:
        messages = await build_reasoning_messages(
            request=request,
            evidence_set=evidence_set,
            constraint_report=constraints,
        )
        available_tools = list(self.tools if tools is None else tools)
        model = self.llm.model.bind_tools(available_tools) if available_tools else None
        response = await self.llm.ainvoke(messages, model=model, temperature=0.25)
        tool_call = self._first_new_tool_call(response, constraints)
        if tool_call is not None:
            return ToolIntent(
                tool_name=str(tool_call.get("name") or ""),
                payload=self._tool_payload(tool_call),
            )
        answer = normalize_message_content(getattr(response, "content", ""))
        tool_calls = getattr(response, "tool_calls", None)
        if isinstance(tool_calls, list) and tool_calls and not answer:
            response = await self.llm.ainvoke(messages, model=None, temperature=0.25)
            answer = normalize_message_content(getattr(response, "content", ""))
        return FinalAnswer(answer=answer)

    def _first_new_tool_call(self, response: Any, constraints: ConstraintReport) -> dict[str, Any] | None:
        tool_calls = getattr(response, "tool_calls", None)
        if not isinstance(tool_calls, list):
            return None
        executed = set(constraints.executed_tools)
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            name = str(tool_call.get("name") or "").strip()
            if name and name not in executed:
                return tool_call
            if name:
                constraints.skipped_tools.append(name)
        return None

    def _tool_payload(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        args = tool_call.get("args")
        if isinstance(args, dict):
            return args
        if isinstance(args, str):
            try:
                parsed = json.loads(args)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}
