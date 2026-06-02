"""
审核智能体 — 校验各 Worker Agent 的生成结果，输出评审意见和修改建议。
"""

from __future__ import annotations

import json
import re
import time

from app.infra.llm import get_llm
from app.infra.logging import get_module_logger
from app.prompts import registry
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.events import AgentEventEmitter
from app.resource.schemas import WorkerResult, WorkerState

logger = get_module_logger("resource", sub="review")


@register_agent
class ReviewAgent(BaseResourceAgent):
    """审核生成内容的事实性、安全性和防幻觉风险。"""

    agent_id = "review"
    agent_name = "审核"

    def __init__(self, emitter: AgentEventEmitter | None = None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        start = time.perf_counter()
        logger.info("Agent[review] 启动: learning_need=%s", state.learning_need[:50])

        review_envelope = state.agent_config.get("review_envelope", {})
        review_mode = review_envelope.get("mode", "") if isinstance(review_envelope, dict) else ""
        progress_agent_id = state.agent_config.get("progress_agent_id") or self._progress_agent_id(review_mode)

        await self.emitter.emit_agent(progress_agent_id, status="running", message="正在审核生成结果", progress=0)
        await self.emitter.emit_agent_action(
            progress_agent_id, "inspect", detail="正在检查内容质量",
            current_step=1, total_steps=3, step_label="检查质量", progress=20,
        )

        prompt = registry.get("resource/review")

        await self.emitter.emit_agent_action(
            progress_agent_id, "evaluate", detail="正在评估与大纲一致性",
            current_step=2, total_steps=3, step_label="评估一致性", progress=60,
        )

        response = await self.llm.ainvoke(
            f"{prompt}\n\n{input_text}",
            temperature=0.2,
        )

        elapsed = time.perf_counter() - start
        logger.debug("Agent[review] LLM 调用完成: %.2fs", elapsed)

        content = response.content if hasattr(response, "content") else str(response)
        parsed_review, parse_error = self._parse_review_response(content)
        review_status = parsed_review.get("status") if parsed_review else "blocked"
        success = review_status == "pass"

        await self.emitter.emit_agent_action(
            progress_agent_id, "done", detail="审核完成",
            current_step=3, total_steps=3, step_label="审核完成", progress=100,
        )
        await self.emitter.emit_agent(
            progress_agent_id,
            status="success" if success else "failed",
            message="审核通过" if success else "审核未通过",
            progress=100,
        )

        elapsed = time.perf_counter() - start
        logger.info("Agent[review] 完成: %.2fs", elapsed)

        return WorkerResult(
            success=success,
            content=content,
            file_type="json",
            title="审核意见",
            summary="审核生成内容的事实性、安全性和防幻觉风险",
            metadata={
                "agent_id": "review",
                "review_status": review_status,
                "review_mode": review_mode,
                "progress_agent_id": progress_agent_id,
                "parsed_review": parsed_review,
                "parse_error": parse_error,
            },
            error=parse_error or ("" if success else f"review status: {review_status}"),
        )

    def agent_input_parts(self, state: WorkerState) -> list[str]:
        review_envelope = state.agent_config.get("review_envelope")
        if isinstance(review_envelope, dict):
            mode = review_envelope.get("mode", "")
            return [
                f"## 审核模式\n{mode}",
                "## 审核输入 JSON",
                json.dumps(review_envelope, ensure_ascii=False, indent=2),
                "请仅根据审核模式输出 JSON，不要输出 Markdown 或解释性文字。",
            ]

        worker_results = state.agent_config.get("worker_results", [])
        if worker_results:
            parts = ["## 待审核内容"]
            for wr in worker_results:
                agent_name = wr.get("agent_name", wr.get("agent_id", "unknown"))
                parts.append(f"### {agent_name}")
                parts.append(wr.get("content", "")[:2000])
                parts.append("")
            parts.append("请审核以上内容，仅输出结构化 JSON。")
            return parts
        return []

    @staticmethod
    def _progress_agent_id(review_mode: str) -> str:
        if review_mode == "pre_audit":
            return "pre_review"
        if review_mode == "ppt_audit":
            return "ppt_review"
        return "review"

    def _parse_review_response(self, content: str) -> tuple[dict, str]:
        raw = content.strip()
        if not raw:
            return {
                "status": "blocked",
                "checks": {},
                "violations": ["empty_review_response"],
                "revision_targets": ["review"],
            }, "empty review response"

        match = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        if match:
            raw = match.group(1).strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            return {
                "status": "blocked",
                "checks": {},
                "violations": [{"type": "invalid_review_json", "message": str(exc)}],
                "revision_targets": ["review"],
            }, f"invalid review JSON: {exc}"

        if not isinstance(parsed, dict):
            return {
                "status": "blocked",
                "checks": {},
                "violations": [{"type": "invalid_review_payload"}],
                "revision_targets": ["review"],
            }, "review JSON must be an object"

        status = parsed.get("status")
        if status not in {"pass", "needs_revision", "blocked"}:
            parsed["status"] = "blocked"
            parsed.setdefault("violations", []).append(
                {"type": "invalid_review_status", "value": status}
            )
            parsed.setdefault("revision_targets", ["review"])
            return parsed, "review status must be pass, needs_revision, or blocked"

        parsed.setdefault("checks", {})
        parsed.setdefault("violations", [])
        parsed.setdefault("revision_targets", [])
        return parsed, ""

    