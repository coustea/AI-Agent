"""审核智能体 — 审核各 Agent 生成内容的质量。"""

from __future__ import annotations

import json

from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import WorkerResult, WorkerState


@register_agent
class ReviewAgent(BaseResourceAgent):
    """审核各 Agent 生成内容的质量和一致性。"""

    agent_id = "review"
    agent_name = "审核"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, state: WorkerState) -> WorkerResult:
        from app.prompts import registry

        prompt = registry.get("resource/review")
        input_text = self._build_review_input(state)
        response = await self.llm.ainvoke(
            f"{prompt}\n\n{input_text}",
            temperature=0.2,
        )
        content = response.content if hasattr(response, "content") else str(response)

        passed = "通过" in content or "PASS" in content.upper()
        issues = self._extract_issues(content)

        return WorkerResult(
            success=True,
            content=content,
            file_type="markdown",
            title="资源质量审核报告",
            summary="审核通过" if passed else f"审核发现 {len(issues)} 个问题",
            metadata={
                "agent_id": "review",
                "passed": passed,
                "issues": issues,
            },
        )

    def _build_review_input(self, state: WorkerState) -> str:
        parts = ["## 待审核内容"]
        if hasattr(state, "worker_results") and state.worker_results:
            for agent_id, result in state.worker_results.items():
                if result.success:
                    preview = result.content[:500] if result.content else ""
                    parts.append(f"### {agent_id}\n{preview}...")
        return "\n\n".join(parts)

    @staticmethod
    def _extract_issues(content: str) -> list[str]:
        issues = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith(("- [ ]", "* [ ]")) or (stripped and stripped[0].isdigit() and "." in stripped[:4]):
                issues.append(stripped.lstrip("-*0123456789. ").strip())
        return issues
