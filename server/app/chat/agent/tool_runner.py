"""TutorToolRunner — 工具调用执行器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from app.chat.agent.tools import (
    LONG_TERM_MEMORY_CATEGORY_ALIASES,
    TOOL_EVIDENCE_TYPES,
    WEB_RESEARCH_TOOL_NAMES,
)
from app.chat.schemas import Evidence, normalize_tool_result
from app.infra.logging import get_logger
from app.infra.tool_excute import ToolExcute

logger = get_logger(__name__)


@dataclass(slots=True)
class ToolExecutionContext:
    user_id: int
    session_id: str
    memory_service: Any | None = None


@dataclass(slots=True)
class ToolExecutionResult:
    invocation: dict[str, Any] | None = None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class TutorToolRunner:
    """辅导工具执行器。"""

    async def execute(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        tool_call_id: str | None = None,
        context: ToolExecutionContext | None = None,
        tool_excute: ToolExcute | None = None,
    ) -> ToolExecutionResult:
        normalized_payload = dict(arguments)
        if tool_name == "get_long_term_memory":
            category = str(normalized_payload.get("category") or "").strip()
            if category:
                normalized_payload["category"] = LONG_TERM_MEMORY_CATEGORY_ALIASES.get(category, category)

        tool_call_id = tool_call_id or f"call-{uuid4().hex}"
        result_text = ""
        node_evidence: list[dict[str, Any]] = []
        node_sources: list[dict[str, Any]] = []
        node_errors: list[str] = []
        assistant_message_id: int | None = None
        tool_message_id: int | None = None

        user_id = context.user_id if context else 0
        session_id = context.session_id if context else ""
        memory_service = context.memory_service if context else None
        tool_status = "success"

        if memory_service:
            try:
                assistant_message = await memory_service.save_message(
                    user_id=user_id,
                    session_id=session_id,
                    role="assistant",
                    content=[{"type": "text", "text": f"正在调用工具：{tool_name}"}],
                    tool_calls=[{"id": tool_call_id, "name": tool_name, "args": normalized_payload}],
                )
                assistant_message_id = getattr(assistant_message, "id", None)
            except Exception as exc:
                logger.warning("[TutorToolRunner] save tool request failed: %s", exc)

        try:
            raw_result = await tool_excute.execute(
                {"id": tool_call_id, "name": tool_name, "args": normalized_payload}
            )
            normalized = normalize_tool_result(raw_result)
            result_text = normalized.text
            tool_status = "success" if result_text else "ignored"

            evidence_type = TOOL_EVIDENCE_TYPES.get(tool_name)
            if evidence_type and result_text:
                evidence_details = {"tool_name": tool_name, "args": normalized_payload, **normalized.metadata}
                evidence_entry = Evidence(
                    evidence_type=evidence_type,
                    summary=result_text,
                    details=evidence_details,
                ).model_dump()
                node_evidence.append(evidence_entry)

            if evidence_type and result_text:
                if tool_name == "search_knowledge_base":
                    raw_sources = normalized.metadata.get("sources", [])
                    if isinstance(raw_sources, list):
                        node_sources.extend(s for s in raw_sources if isinstance(s, dict))
                elif tool_name in WEB_RESEARCH_TOOL_NAMES:
                    url = normalized.metadata.get("url")
                    if url:
                        node_sources.append({
                            "source": tool_name,
                            "url": str(url),
                            "title": str(normalized.metadata.get("title", url)),
                            "summary": result_text[:500],
                        })
                    elif tool_name in ("duckduckgo_search", "tavily_search", "spark_search"):
                        node_sources.append({
                            "source": tool_name,
                            "query": str(normalized.metadata.get("query", "")),
                            "summary": result_text[:500],
                        })

        except Exception as exc:
            logger.warning("[TutorToolRunner] tool %s failed: %s", tool_name, exc)
            tool_status = "failed"
            node_errors.append(f"{tool_name}: {exc}")
            result_text = f"调用失败: {exc}"

        if memory_service:
            try:
                tool_message = await memory_service.save_message(
                    user_id=user_id,
                    session_id=session_id,
                    role="tool",
                    content=[{"type": "text", "text": result_text}],
                    tool_call_id=tool_call_id,
                )
                tool_message_id = getattr(tool_message, "id", None)
            except Exception as exc:
                logger.warning("[TutorToolRunner] save tool result failed: %s", exc)

        invocation: dict[str, Any] | None = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "payload": normalized_payload,
            "result_text": result_text,
            "status": tool_status,
            "evidence": node_evidence,
            "assistant_message_id": assistant_message_id,
            "tool_message_id": tool_message_id,
        }

        return ToolExecutionResult(
            invocation=invocation,
            evidence=node_evidence,
            sources=node_sources,
            errors=node_errors,
        )
