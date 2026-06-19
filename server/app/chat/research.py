"""Bounded model/tool loop for autonomous, read-only web research."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.infra.prompts import prompts


@dataclass
class ResearchToolStep:
    tool_call_id: str
    tool_name: str
    payload: dict[str, Any]
    status: str
    result_text: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    events: list[Any] = field(default_factory=list)
    invocation: dict[str, Any] | None = None
    sources: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


ResearchExecutor = Callable[
    [str, dict[str, Any], str],
    Awaitable[ResearchToolStep],
]


class WebResearchRunner:
    """Let the model choose web tools until it has enough evidence or hits a budget."""

    def __init__(
        self,
        *,
        llm: Any,
        tools: Sequence[Any],
        max_iterations: int = 8,
        max_domains: int = 5,
        system_prompt: str | None = None,
    ) -> None:
        self.llm = llm
        self.tools = list(tools)
        self.max_iterations = max(1, int(max_iterations))
        self.max_domains = max(1, int(max_domains))
        self.system_prompt = system_prompt or prompts.get("chat").get("search_instruction")
        self._allowed_tools = {str(tool.name) for tool in self.tools}

    async def run(self, question: str, *, execute: ResearchExecutor) -> list[ResearchToolStep]:
        messages: list[Any] = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=str(question or "")),
        ]
        steps: list[ResearchToolStep] = []
        visited_domains: set[str] = set()

        for _iteration in range(self.max_iterations):
            response = await self.llm.ainvoke_tools(messages, self.tools, temperature=0.1)
            messages.append(response)
            tool_calls = list(getattr(response, "tool_calls", None) or [])
            if not tool_calls:
                break

            executed_valid_call = False
            for raw_call in tool_calls:
                call = raw_call if isinstance(raw_call, dict) else {}
                call_id = str(call.get("id") or f"call-{uuid4().hex}")
                tool_name = str(call.get("name") or "").strip()
                payload = call.get("args")

                if tool_name not in self._allowed_tools:
                    step = self._failed_step(
                        call_id,
                        tool_name,
                        {},
                        f"Tool {tool_name or '<missing>'} is not available for web research.",
                    )
                elif not isinstance(payload, dict):
                    step = self._failed_step(
                        call_id,
                        tool_name,
                        {},
                        "Tool arguments must be a JSON object.",
                    )
                else:
                    domain = self._requested_domain(tool_name, payload)
                    if domain and domain not in visited_domains and len(visited_domains) >= self.max_domains:
                        step = self._failed_step(
                            call_id,
                            tool_name,
                            dict(payload),
                            "Web research domain budget has been exhausted.",
                        )
                    else:
                        if domain:
                            visited_domains.add(domain)
                        executed_valid_call = True
                        try:
                            step = await execute(tool_name, dict(payload), call_id)
                        except Exception as exc:
                            step = self._failed_step(
                                call_id,
                                tool_name,
                                dict(payload),
                                f"{tool_name} failed: {exc}",
                            )

                steps.append(step)
                messages.append(
                    ToolMessage(
                        content=self._tool_message_content(step),
                        tool_call_id=call_id,
                    )
                )

            if not executed_valid_call:
                break

        return steps

    @staticmethod
    def _requested_domain(tool_name: str, payload: dict[str, Any]) -> str:
        if tool_name not in {"open_web_page", "read_web_pdf"}:
            return ""
        return str(urlsplit(str(payload.get("url") or "")).hostname or "").lower()

    @staticmethod
    def _failed_step(
        call_id: str,
        tool_name: str,
        payload: dict[str, Any],
        message: str,
    ) -> ResearchToolStep:
        return ResearchToolStep(
            tool_call_id=call_id,
            tool_name=tool_name,
            payload=payload,
            status="failed",
            result_text=message,
            errors=[message],
        )

    @staticmethod
    def _tool_message_content(step: ResearchToolStep) -> str:
        metadata = []
        for evidence in step.evidence:
            if not isinstance(evidence, dict):
                continue
            details = evidence.get("details")
            if isinstance(details, dict) and details:
                metadata.append(details)
        return json.dumps(
            {
                "status": step.status,
                "result": step.result_text,
                "sources": step.sources,
                "metadata": metadata,
            },
            ensure_ascii=False,
        )
