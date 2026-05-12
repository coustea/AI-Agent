# -*- coding: utf-8 -*-
"""资源包组装器。

组装最终的 ResourceBundle 输出。
"""

from __future__ import annotations

from typing import Any

from app.infra.logging import get_logger
from app.resource.schemas import (
    GeneratedResourceItem,
    ResourceBundle,
    ResourceGenerationRequest,
    ReviewResult,
)
from app.resource.assembler.reviewer import Reviewer
from app.resource.assembler.study_path_builder import StudyPathBuilder

logger = get_logger(__name__)


class BundleAssembler:
    """资源包组装器：组装最终 ResourceBundle，不负责首次发送单个资源。"""

    def __init__(self) -> None:
        self.reviewer = Reviewer()
        self.path_builder = StudyPathBuilder()

    def assemble(
        self,
        *,
        task_id: str,
        resource_id: str,
        request: ResourceGenerationRequest,
        resources: list[GeneratedResourceItem],
        review_result: ReviewResult,
        failed_agents: list[str],
        skipped_agents: list[str] | None = None,
        profile: dict[str, Any] | None = None,
        timing: dict[str, Any] | None = None,
    ) -> ResourceBundle:
        """根据审查结果组装最终资源包。"""
        skipped_agents = skipped_agents or []
        title = request.output_options.final_bundle_title or "个性化学习资源包"
        study_path = (
            self.path_builder.build(resources, profile=profile, request=request)
            if request.output_options.include_study_path
            else []
        )

        if not resources:
            status = "failed"
        elif failed_agents:
            status = "partial_completed"
        elif review_result.issues:
            status = "completed_with_warnings"
        else:
            status = "completed"

        metadata: dict[str, Any] = {
            "agent_count": len(resources),
            "failed_agents": failed_agents,
            "skipped_agents": skipped_agents,
        }
        if timing:
            metadata["timing"] = timing

        return ResourceBundle(
            id=str(resource_id),
            task_id=task_id,
            title=title,
            learning_need=request.learning_need,
            selected_agents=[
                selection for selection in request.selected_agents
                if selection.enabled
            ],
            resources=resources,
            study_path=study_path,
            review_result=review_result,
            status=status,
            metadata=metadata,
        )

    def build_bundle(
        self,
        *,
        task_id: str,
        resource_id: int,
        request: ResourceGenerationRequest,
        resources: list[GeneratedResourceItem],
        failed: list[str],
        skipped: list[str],
        errors: list[str] | None = None,
        review_result: ReviewResult | None = None,
        profile: dict[str, Any] | None = None,
        timing: dict[str, Any] | None = None,
    ) -> ResourceBundle:
        """组装资源包（便捷方法，自动执行审查）。"""
        errors = errors or []
        review_result = review_result or self.reviewer.review(
            request=request,
            resources=resources,
            failed_agents=failed,
            skipped_agents=skipped,
            errors=errors,
        )
        return self.assemble(
            task_id=task_id,
            resource_id=str(resource_id),
            request=request,
            resources=resources,
            review_result=review_result,
            failed_agents=failed,
            skipped_agents=skipped,
            profile=profile,
            timing=timing,
        )
