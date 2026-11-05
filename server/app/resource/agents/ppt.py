"""PPTAgent — 基于 Plan-and-Execute + python-pptx + 本地 Skill 的多智能体课件生成。"""

from __future__ import annotations

import time as _time
from typing import Any

from app.config import resource_ppt_url, static_url, user_resource_ppt_dir
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import AgentResult, DownstreamContext, ResourceInput
from app.shared.ppt import (
    PPTArtifact,
    PPTGenerationError,
    PPTPreferences,
    PPTService,
    PPTSource,
    ResourcePPT,
    ppt_pipeline_metadata,
)

logger = get_logger(__name__)


def _source_artifacts(handoffs: dict[str, DownstreamContext]) -> list[PPTSource]:
    """将上游交接内容转换为 PPT 素材。"""
    artifacts: list[PPTSource] = []
    for agent_id, handoff in (handoffs or {}).items():
        materials = list(
            dict.fromkeys(
                str(item).strip()
                for item in (handoff.materials or [])
                if str(item).strip()
            )
        )
        artifacts.append(
            PPTSource(
                agent_id=agent_id,
                title=handoff.title or agent_id,
                summary=handoff.one_sentence_summary or handoff.title or agent_id,
                materials=materials[:12],
            )
        )
    return artifacts


def _parse_preferences(agent_config: dict[str, Any]) -> PPTPreferences:
    """从 agent_config 提取 PPTPreferences。"""
    clean = {
        k: v
        for k, v in (agent_config or {}).items()
        if k in PPTPreferences.model_fields
    }
    return PPTPreferences.model_validate(clean)


@register_agent
class PPTAgent(BaseResourceAgent):
    """PPTAgent — 采用 Plan-and-Execute + python-pptx 生成 .pptx 与交互式预览课件。"""

    agent_id = "ppt"
    agent_name = "演示幻灯"

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._ppt_service = PPTService()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        started = _time.perf_counter()
        username = input_data.username or "anonymous"
        resource_key = (
            str(input_data.resource_id)
            if input_data.resource_id is not None
            else "default"
        )

        if input_data.teaching_plan is None:
            return AgentResult(
                success=False,
                title="PPT 生成失败",
                file_type="html",
                error="PPT 聚合生成缺少结构化教学计划",
                metadata={"agent_id": self.agent_id, "generation_stage": "assembling_context"},
            )

        artifacts = _source_artifacts(input_data.upstream_handoffs)
        logger.info(
            "Agent[%s] 开始 python-pptx 生成: learning_need=%s artifacts=%d",
            self.agent_id,
            input_data.learning_need[:40],
            len(artifacts),
        )

        request = ResourcePPT(
            username=username,
            learning_need=input_data.learning_need,
            learning_scenario=input_data.learning_scenario,
            profile=input_data.profile or {},
            resource_plan=input_data.teaching_plan.model_dump(mode="json"),
            artifacts=artifacts,
            preferences=_parse_preferences(input_data.agent_config),
        )

        output_dir = user_resource_ppt_dir(username, resource_key)

        async def progress(message: str, percent: int) -> None:
            await self.emitter.send(self.agent_id, "running", message, percent)

        try:
            artifact = await self.run_with_heartbeat(
                self._ppt_service.generate(request, output_dir, progress=progress),
                messages=[
                    "正在加载 pptx 技能并规划 60-30-10 课件蓝图...",
                    "正在并行调度 SlideSubagent 编写 python-pptx 幻灯片代码...",
                    "正在执行 OOXML 几何防重叠审计与缩略图渲染...",
                ],
                interval_seconds=15.0,
                progress=70,
            )
        except PPTGenerationError as exc:
            elapsed_ms = int((_time.perf_counter() - started) * 1000)
            logger.exception(
                "Agent[%s] PPT生成失败: stage=%s elapsed_ms=%d",
                self.agent_id,
                exc.stage,
                elapsed_ms,
            )
            return AgentResult(
                success=False,
                title="PPT 生成失败",
                file_type="html",
                error=str(exc),
                metadata={
                    "agent_id": self.agent_id,
                    "generation_stage": exc.stage,
                },
            )

        artifact.html_url = resource_ppt_url(username, resource_key)
        if artifact.pptx_path and artifact.pptx_path.is_file():
            artifact.pptx_url = static_url(artifact.pptx_path)

        return self._artifact_to_result(artifact)

    def _artifact_to_result(self, artifact: object) -> AgentResult:
        if not isinstance(artifact, PPTArtifact):
            return AgentResult(
                success=False,
                title="PPT 生成失败",
                file_type="html",
                error=f"unexpected result type: {type(artifact)}",
                metadata={"agent_id": self.agent_id},
            )

        title = artifact.title
        path = artifact.path
        pptx_size = (
            artifact.pptx_path.stat().st_size
            if artifact.pptx_path and artifact.pptx_path.is_file()
            else path.stat().st_size
        )
        return AgentResult(
            success=True,
            title=f"{title} - 教学课件",
            file_type="html",
            content="",
            summary=f"生成 {artifact.slide_count} 页 PPTX 教学课件",
            metrics={"slide_count": artifact.slide_count},
            metadata={
                "agent_id": self.agent_id,
                "html_file_path": str(path),
                "html_url": artifact.html_url,
                "pptx_file_path": str(artifact.pptx_path or ""),
                "pptx_url": artifact.pptx_url,
                "slide_count": artifact.slide_count,
                "file_size": pptx_size,
                "ppt_pipeline": ppt_pipeline_metadata(),
            },
        )
