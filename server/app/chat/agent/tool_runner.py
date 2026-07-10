"""TutorToolRunner — 工具调用执行器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from app.chat.agent.tools import TOOL_EVIDENCE_TYPES
from app.chat.tools.user_context import LONG_TERM_MEMORY_CATEGORY_ALIASES
from app.chat.schemas import Evidence, normalize_tool_result
from app.infra.logging import get_logger
from app.infra.tool_excute import ToolExcute

logger = get_logger(__name__)


# 单次工具执行的上下文信息（用户/会话/消息标识及记忆服务）
@dataclass(slots=True)
class ToolExecutionContext:
    user_id: int
    session_id: str
    user_message_id: int
    memory_service: Any | None = None


# 单次工具执行的结果（调用记录、证据、来源、错误）
@dataclass(slots=True)
class ToolExecutionResult:
    invocation: dict[str, Any] | None = None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# 辅导工具执行器：负责真正调用工具、持久化消息、构造证据与来源
class TutorToolRunner:
    """辅导工具执行器。"""

    # 执行单个工具调用，归一化结果并收集调用记录/证据/来源/错误
    async def execute(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        tool_call_id: str | None = None,
        context: ToolExecutionContext | None = None,
        tool_excute: ToolExcute | None = None,
    ) -> ToolExecutionResult:
        # 复制入参并归一化：长期记忆工具需将类别名映射为规范分类
        normalized_payload = dict(arguments)
        if tool_name == "get_long_term_memory":
            category = str(normalized_payload.get("category") or "").strip()
            if category:
                normalized_payload["category"] = LONG_TERM_MEMORY_CATEGORY_ALIASES.get(category, category)

        # 无 tool_call_id 时生成唯一标识
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
        raw_result: Any = None

        # 执行前先持久化 assistant 的工具调用占位消息
        if memory_service:
            try:
                assistant_message = await memory_service.save_message(
                    user_id=user_id,
                    session_id=session_id,
                    user_message_id=context.user_message_id,
                    role="assistant",
                    content=[],
                    tool_calls=[{"id": tool_call_id, "name": tool_name, "args": normalized_payload}],
                )
                assistant_message_id = getattr(assistant_message, "id", None)
            except Exception as exc:
                logger.warning("[TutorToolRunner] 保存工具请求失败: %s", exc)

        # 真正执行工具并获取原始结果
        try:
            raw_result = await tool_excute.execute(
                {"id": tool_call_id, "name": tool_name, "args": normalized_payload}
            )
            # 归一化工具结果文本，并根据 RAG 状态字段判定工具状态
            normalized = normalize_tool_result(raw_result)
            result_text = normalized.text
            # RAG 工具返回 status 字段：ok/empty/unavailable
            tool_status_value = normalized.metadata.get("status")
            if tool_status_value == "empty":
                tool_status = "ignored"
            elif tool_status_value == "unavailable":
                tool_status = "failed"
            else:
                tool_status = "success" if result_text else "ignored"

            # 仅在有效结果下构建证据条目
            evidence_type = TOOL_EVIDENCE_TYPES.get(tool_name)
            # empty 和 unavailable 不建立 Evidence 和收集 sources
            if evidence_type and result_text and tool_status_value != "empty" and tool_status_value != "unavailable":
                evidence_details = {"tool_name": tool_name, "args": normalized_payload, **normalized.metadata}
                evidence_entry = Evidence(
                    evidence_type=evidence_type,
                    summary=result_text,
                    details=evidence_details,
                ).model_dump()
                node_evidence.append(evidence_entry)

            # 收集结果的引用来源
            if evidence_type and result_text and tool_status_value != "empty" and tool_status_value != "unavailable":
                node_sources.extend(source.model_dump() for source in normalized.sources)

        # 工具执行异常则标记失败并记录错误信息
        except Exception as exc:
            logger.warning("[TutorToolRunner] 工具 %s 失败: %s", tool_name, exc)
            tool_status = "failed"
            node_errors.append(f"{tool_name}: {exc}")
            result_text = f"调用失败: {exc}"

        # 持久化 tool 角色的结果消息
        if memory_service:
            try:
                tool_message = await memory_service.save_message(
                    user_id=user_id,
                    session_id=session_id,
                    user_message_id=context.user_message_id,
                    role="tool",
                    content=[{"type": "text", "text": result_text}],
                    tool_call_id=tool_call_id,
                )
                tool_message_id = getattr(tool_message, "id", None)
            except Exception as exc:
                logger.warning("[TutorToolRunner] 保存工具结果失败: %s", exc)

        # 组装工具调用记录
        invocation: dict[str, Any] | None = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "payload": normalized_payload,
            "result_payload": raw_result,
            "result_text": result_text,
            "status": tool_status,
            "evidence": node_evidence,
            "assistant_message_id": assistant_message_id,
            "tool_message_id": tool_message_id,
        }

        # 返回执行结果（调用记录/证据/来源/错误）
        return ToolExecutionResult(
            invocation=invocation,
            evidence=node_evidence,
            sources=node_sources,
            errors=node_errors,
        )
