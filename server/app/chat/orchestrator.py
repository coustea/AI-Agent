"""对话轮次编排器 — 确定性四阶段流水线 + 推理循环 + transcript 投影。

执行顺序（transcript-first 确定性编排）：
  1. attachment_analysis  — 附件分析（图片 OCR / 文档解析）
  2. search              — 知识库检索 + 联网搜索
  3. answer              — 推理循环（ReasoningAgent ↔ ToolExecutor，最多 N 轮）
  4. diagram             — 教学图解生成（可选）

推理循环 _reason_until_final：
  agent.reason() → ToolIntent → executor.execute() → 证据回填 → 再次推理
  agent.reason() → FinalAnswer → 退出循环

project_turn_run 将 TurnRunResult 投影为前端可消费的 transcript 消息列表。
"""

from __future__ import annotations

import json
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.chat.agent import ReasoningAgent
from app.chat.memory.service import get_chat_memory_service
from app.chat.schemas import ConstraintReport, Evidence, EvidenceSet, FinalAnswer, ToolIntent, TurnRequest
from app.chat.stages import AttachmentAnalyzer, SearchOrchestrator, TeachingDiagramGenerator, WebSearchTool
from app.chat.tutor_tools import TutorToolExecutor


# ── 工具执行记录 ────────────────────────────────────────────────


class ToolExecutionRecord(BaseModel):
    """单次工具调用的完整记录，用于持久化和 transcript 投影。"""
    tool_call_id: str = Field(default_factory=lambda: f"tool-{uuid4().hex}")
    tool_name: str
    invoked_by: Literal["orchestrator", "agent"]  # 区分编排层直接调用 vs agent 推理触发
    payload: dict[str, Any] = Field(default_factory=dict)
    raw_result: dict[str, Any] = Field(default_factory=dict)
    result_text: str = ""
    status: str = "success"
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class ToolExecutor:
    """工具执行器：根据 ToolIntent 分发到对应工具并收集 Evidence。

    支持三种工具：
      - learner_profile  → 查询学习者画像
      - long_term_memory → 查询长期记忆
      - web_search       → 联网搜索（tavily/duckduckgo/serp/spark 降级链）
    """

    def __init__(self) -> None:
        self.web_search = WebSearchTool()

    async def execute(self, intent: ToolIntent, request: Any) -> dict[str, Any]:
        if intent.tool_name == "learner_profile":
            dimension = str(intent.payload.get("dimension") or "").strip() or None
            markdown = await get_chat_memory_service().get_profile_markdown(request.user_id, dimension=dimension)
            return {
                "tool_name": intent.tool_name,
                "status": "success",
                "evidence": [
                    Evidence(
                        evidence_type="learner_profile",
                        summary=markdown,
                        details={"dimension": dimension},
                    ).model_dump()
                ],
            }
        if intent.tool_name == "long_term_memory":
            category = str(intent.payload.get("category") or "").strip() or None
            markdown = await get_chat_memory_service().get_memory_markdown(request.user_id, category=category)
            return {
                "tool_name": intent.tool_name,
                "status": "success",
                "result_text": markdown,
                "evidence": [
                    Evidence(
                        evidence_type="long_term_memory",
                        summary=markdown,
                        details={"category": category},
                    ).model_dump()
                ],
            }
        if intent.tool_name == "web_search":
            query = str(intent.payload.get("query") or request.message or "").strip()
            result_text, tool_name = await self.web_search.search(query)
            status = "success" if result_text else "ignored"
            return {
                "tool_name": intent.tool_name,
                "status": status,
                "result_text": result_text,
                "evidence": [
                    Evidence(
                        evidence_type="web_search",
                        summary=result_text,
                        details={"query": query, "tool_name": tool_name or "web_search"},
                    ).model_dump()
                ] if result_text else [],
            }
        return {
            "tool_name": intent.tool_name,
            "status": "ignored",
            "result_text": "",
            "evidence": [],
        }


# ── Transcript 投影 ─────────────────────────────────────────────


class TurnProjection(BaseModel):
    """将编排结果投影为前端可消费的格式：消息列表 + 工具调用记录 + 知识来源。"""
    transcript_messages: list[dict[str, Any]] = Field(default_factory=list)
    tool_invocations: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_sources: list[dict[str, Any]] = Field(default_factory=list)
    attachment_analyses: list[dict[str, Any]] = Field(default_factory=list)


def project_turn_run(result: Any) -> TurnProjection:
    """将 TurnRunResult 投影为前端 transcript 消息列表。

    每个工具调用生成两条消息：assistant_tool_request + tool_result，
    最后追加 assistant_answer 消息。同时收集知识库和搜索来源。
    """
    transcript_messages: list[dict[str, Any]] = []
    tool_invocations: list[dict[str, Any]] = []

    for record in list(getattr(result, "tool_records", []) or []):
        tool_call_id = str(getattr(record, "tool_call_id", "") or "")
        tool_name = str(getattr(record, "tool_name", "") or "")
        payload = getattr(record, "payload", {}) if isinstance(getattr(record, "payload", {}), dict) else {}
        result_text = str(getattr(record, "result_text", "") or _stringify_result(getattr(record, "raw_result", {}))).strip()
        # 工具请求消息（assistant 发起）
        transcript_messages.append(
            {
                "role": "assistant",
                "content": f"正在调用工具：{tool_name}",
                "tool_calls": [{"id": tool_call_id, "name": tool_name, "args": payload}],
                "message_kind": "assistant_tool_request",
            }
        )
        # 工具结果消息
        transcript_messages.append(
            {
                "role": "tool",
                "content": result_text,
                "tool_call_id": tool_call_id,
                "message_kind": "tool_result",
            }
        )
        tool_invocations.append(
            {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "arguments_json": payload,
                "result_text": result_text,
                "result_json": getattr(record, "raw_result", {}) if isinstance(getattr(record, "raw_result", {}), dict) else {},
                "status": str(getattr(record, "status", "success") or "success"),
            }
        )

    final_answer = str(getattr(result, "final_answer", "") or "").strip()
    if final_answer:
        transcript_messages.append(
            {
                "role": "assistant",
                "content": final_answer,
                "tool_calls": [],
                "message_kind": "assistant_answer",
            }
        )

    knowledge_sources = _collect_knowledge_sources(list(getattr(result, "evidence", []) or []))
    attachment_analyses = list(getattr(result, "attachment_analyses", []) or [])
    return TurnProjection(
        transcript_messages=transcript_messages,
        tool_invocations=tool_invocations,
        knowledge_sources=knowledge_sources,
        attachment_analyses=attachment_analyses,
    )


def _collect_knowledge_sources(evidence_items: list[Evidence]) -> list[dict[str, Any]]:
    """从证据列表中提取知识库和搜索来源，供前端展示引用信息。"""
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
            sources.append(
                {
                    "source": details.get("tool_name") or "web_search",
                    "query": details.get("query") or "",
                    "summary": item.summary,
                }
            )
    return sources


def _stringify_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False)
    return str(result)


# ── 编排主循环 ──────────────────────────────────────────────────


class TurnRunResult(BaseModel):
    """一轮对话的完整结果：最终回答 + 图解 + 证据 + 工具记录 + 约束报告。"""
    final_answer: str = ""
    teaching_diagram: dict[str, Any] | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    tool_records: list[ToolExecutionRecord] = Field(default_factory=list)
    constraint_report: ConstraintReport = Field(default_factory=ConstraintReport)
    attachment_analyses: list[dict[str, Any]] = Field(default_factory=list)
    route: str = "default"
    execution_mode: str = "default"


class TurnOrchestrator:
    """对话轮次编排器 — 确定性四阶段流水线。

    阶段顺序固定：attachments → search → answer → diagram
    每个阶段将证据回填到 evidence_set，供后续阶段使用。
    推理阶段内部有循环：agent ↔ tool_executor，直到产出 FinalAnswer 或达到步数上限。
    """

    def __init__(
        self,
        *,
        attachments: Any = None,
        search: Any = None,
        agent: Any = None,
        diagram: Any = None,
        tools: Any = None,
        max_reasoning_steps: int = 4,
    ) -> None:
        self.attachments = attachments or AttachmentAnalyzer()
        self.search = search or SearchOrchestrator()
        self.agent = agent or ReasoningAgent()
        self.diagram = diagram or TeachingDiagramGenerator()
        self.tools = tools
        self.max_reasoning_steps = max_reasoning_steps

    async def run(self, request: TurnRequest) -> TurnRunResult:
        """执行一轮对话的完整流水线。"""
        evidence_set = EvidenceSet()
        constraints = ConstraintReport()
        tool_records: list[ToolExecutionRecord] = []
        attachment_analyses: list[dict[str, Any]] = []
        route = "answer"
        execution_mode = "answer"

        # 阶段 1：附件分析（图片 OCR / 文档解析 → attachment evidence）
        if request.attachment_analysis_enabled and request.attachments and self.attachments is not None:
            route = "attachment_analysis"
            execution_mode = "attachment"
            attachment_output = await self.attachments.analyze(request)
            evidence_set.extend(self._coerce_evidence(getattr(attachment_output, "evidence", [])))
            attachment_analyses = list(getattr(attachment_output, "records", []) or [])

        # 阶段 2：搜索（知识库 + 联网 → knowledge_base / web_search evidence）
        if request.search_enabled and self.search is not None:
            route = "search" if route == "answer" else route
            execution_mode = "attachment_search" if request.attachment_analysis_enabled and request.attachments else "search"
            search_output = await self.search.search(request, evidence_set)
            evidence_set.extend(self._coerce_evidence(getattr(search_output, "evidence", [])))

        # 阶段 3：推理循环（agent ↔ tools → FinalAnswer）
        final_answer = await self._reason_until_final(request, evidence_set, constraints, tool_records)
        teaching_diagram: dict[str, Any] | None = None

        # 阶段 4：教学图解生成（仅当启用且有回答时）
        if request.diagram_enabled and self.diagram is not None and final_answer:
            teaching_diagram = await self.diagram.generate(request, final_answer, evidence_set)

        return TurnRunResult(
            final_answer=final_answer,
            teaching_diagram=teaching_diagram,
            evidence=evidence_set.items,
            tool_records=tool_records,
            constraint_report=constraints,
            attachment_analyses=attachment_analyses,
            route=route if route != "attachment_analysis" or not request.search_enabled else "attachment_analysis",
            execution_mode=execution_mode,
        )

    async def _reason_until_final(
        self,
        request: TurnRequest,
        evidence_set: EvidenceSet,
        constraints: ConstraintReport,
        tool_records: list[ToolExecutionRecord],
    ) -> str:
        """推理循环：agent.reason() → ToolIntent → execute → 证据回填 → 再推理。

        最多执行 max_reasoning_steps 轮，防止无限循环。
        超限后设置 constraints.max_steps_reached = True 并返回空字符串。
        """
        if self.agent is None:
            return ""

        tool_executor = self.tools or TutorToolExecutor(request=request)

        for _ in range(self.max_reasoning_steps):
            outcome = await self.agent.reason(request, evidence_set, constraints)
            normalized = self._normalize_outcome(outcome)
            if isinstance(normalized, FinalAnswer):
                return normalized.answer
            if isinstance(normalized, ToolIntent):
                constraints.executed_tools.append(normalized.tool_name)
                if tool_executor is None:
                    constraints.failed_tools.append(normalized.tool_name)
                    break
                # 执行工具并回填证据
                tool_result = await tool_executor.execute(normalized, request)
                status = str(tool_result.get("status") or "success") if isinstance(tool_result, dict) else "success"
                if status != "success":
                    constraints.failed_tools.append(normalized.tool_name)
                tool_records.append(
                    ToolExecutionRecord(
                        tool_name=str(tool_result.get("tool_name") or normalized.tool_name)
                        if isinstance(tool_result, dict)
                        else normalized.tool_name,
                        invoked_by="agent",
                        payload=normalized.payload,
                        raw_result=tool_result if isinstance(tool_result, dict) else {},
                        result_text=str((tool_result or {}).get("result_text") or "") if isinstance(tool_result, dict) else "",
                        status=status,
                        evidence=(tool_result or {}).get("evidence", []) if isinstance(tool_result, dict) else [],
                    )
                )
                evidence_set.extend(self._coerce_tool_evidence(tool_result))
                continue
            break

        constraints.max_steps_reached = True
        return ""

    def _normalize_outcome(self, outcome: Any) -> FinalAnswer | ToolIntent | None:
        """兼容 dict / 对象两种返回格式，统一转为 ToolIntent 或 FinalAnswer。"""
        if isinstance(outcome, FinalAnswer | ToolIntent):
            return outcome
        if isinstance(outcome, dict):
            if str(outcome.get("kind") or "") == "final_answer":
                return FinalAnswer(answer=str(outcome.get("answer") or ""))
            if str(outcome.get("tool_name") or "").strip():
                return ToolIntent(
                    tool_name=str(outcome.get("tool_name") or ""),
                    payload=outcome.get("payload") if isinstance(outcome.get("payload"), dict) else {},
                )
        return None

    def _coerce_evidence(self, items: Any) -> list[Evidence]:
        """将混合类型（Evidence 对象 / dict）统一转为 Evidence 列表。"""
        results: list[Evidence] = []
        for item in items or []:
            if isinstance(item, Evidence):
                results.append(item)
                continue
            if isinstance(item, dict):
                results.append(Evidence.model_validate(item))
        return results

    def _coerce_tool_evidence(self, tool_result: Any) -> list[Evidence]:
        """从工具执行结果中提取 evidence 列表。"""
        if not isinstance(tool_result, dict):
            return []
        evidence_items = tool_result.get("evidence")
        return self._coerce_evidence(evidence_items)
