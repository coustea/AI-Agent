# -*- coding: utf-8 -*-
"""资源审查器。

审查已生成资源的完整性和质量。
"""

from __future__ import annotations

from typing import Any

from app.infra.logging import get_logger
from app.resource.schemas import (
    GeneratedResourceItem,
    ResourceGenerationRequest,
    ReviewIssue,
    ReviewResult,
)

logger = get_logger(__name__)


class Reviewer:
    """资源审查器：审查资源完整性，不生成资源正文。"""

    def review(
        self,
        *,
        request: ResourceGenerationRequest,
        resources: list[GeneratedResourceItem],
        failed_agents: list[str],
        skipped_agents: list[str] | None = None,
        errors: list[str],
    ) -> ReviewResult:
        """审查已生成资源，并区分失败与跳过 Agent。"""
        skipped_agents = skipped_agents or []
        _, missing_issues = self._check_resources(
            resources=resources,
            selected=request.enabled_agent_ids(),
            failed=failed_agents,
            skipped=skipped_agents,
        )

        issues: list[ReviewIssue] = []
        suggestions: list[str] = []

        for message in missing_issues:
            level = "error" if "失败" in message else "warning"
            issues.append(ReviewIssue(
                level=level,
                message=message,
                suggestion="可重新生成对应资源",
            ))

        for error in errors:
            issues.append(ReviewIssue(
                level="error",
                message=str(error),
                suggestion="检查对应 Agent 日志后重试",
            ))

        if skipped_agents:
            suggestions.append("部分 Agent 因依赖未满足被跳过，可先修复上游资源后重试。")
        if failed_agents:
            suggestions.append("部分 Agent 生成失败，已保留成功生成的资源。")

        score = 100
        score -= min(len(failed_agents) * 20, 60)
        score -= min(len(skipped_agents) * 10, 30)
        score -= min(len(errors) * 10, 30)
        score = max(0, score)

        return ReviewResult(
            passed=bool(resources),
            score=score,
            issues=issues,
            suggestions=suggestions,
            failed_agents=failed_agents,
            skipped_agents=skipped_agents,
        )

    def _check_resources(
        self,
        resources: list[GeneratedResourceItem],
        selected: list[str],
        failed: list[str],
        skipped: list[str],
    ) -> tuple[bool, list[str]]:
        """检查每个 Agent 是否有生成内容。返回 (passed, issues)。"""
        issues: list[str] = []

        if not resources:
            return False, ["没有生成任何资源"]

        # 检查每个启用的 Agent 是否有产出
        resource_map = {res.type.value: res for res in resources}
        for agent_id in selected:
            if agent_id in failed:
                issues.append(f"{agent_id} 生成失败")
            elif agent_id in skipped:
                issues.append(f"{agent_id} 被跳过")
            elif agent_id not in resource_map:
                issues.append(f"{agent_id} 未产出结果")

        return len(resources) > 0, issues