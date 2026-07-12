"""HTML PPT agent — 多智能体资源生成。

职责：
- 数据转换（upstream_handoffs → PPTSource）
- 构建 ResourcePPT 请求
- 路径计算和 URL 构建
- 调用 PPTService 生成
- 转换 PPTArtifact 为 AgentResult

注意：路径规划模块的 PPT 生成由 path/service.py 直接调用 PPTService。
"""

from __future__ import annotations

from typing import Any

from app.config import resource_ppt_url, user_resource_ppt_dir
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import AgentResult, DownstreamContext, ResourceInput
from app.shared.ppt import (
    PPTGenerationError,
    PPTPreferences,
    PPTService,
    PPTSource,
    ResourcePPT,
)

logger = get_logger(__name__)


# ── 数据转换函数 ──────────────────────────────────────────────────────


def _source_artifacts(
    handoffs: dict[str, DownstreamContext],
) -> list[PPTSource]:
    """将上游交接内容转换为 PPT 素材。"""
    artifacts: list[PPTSource] = []
    for agent_id, handoff in handoffs.items():
        materials = list(
            dict.fromkeys(
                str(item).strip()
                for item in handoff.materials
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
    """从 agent_config 中提取 PPTPreferences（去掉 agent_id 字段）。"""
    return PPTPreferences.model_validate(
        {k: v for k, v in agent_config.items() if k != "agent_id"}
    )


# ── PPTAgent ────────────────────────────────────────────────────────────


@register_agent
class PPTAgent(BaseResourceAgent):
    """PPT Agent — 多智能体资源生成专用。

    只负责 generate_resource，路径规划模块的 PPT 生成由 PathService 直接调用 PPTService。

    调用链：
    1. 数据转换：upstream_handoffs → artifacts (PPTSource)
    2. 构建 ResourcePPT + output_dir
    3. 调用 PPTService.generate() → PPTArtifact
    4. 填充 html_url，转换为 AgentResult
    """

    agent_id = "ppt"
    agent_name = "演示幻灯"
    research_enabled = False

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._ppt_service = PPTService()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """多智能体资源生成入口。

        调用链：
        1. 数据转换：upstream_handoffs → artifacts (PPTSource)
        2. 构建 ResourcePPT 请求
        3. 计算输出路径
        4. 调用 PPTService.generate() → PPTArtifact
        5. 填充 html_url，转换为 AgentResult
        """
        username = input_data.username
        resource_key = (
            str(input_data.resource_id)
            if input_data.resource_id is not None
            else ""
        )

        # 1. 数据转换：upstream_handoffs → artifacts
        artifacts = _source_artifacts(input_data.upstream_handoffs)

        # 2. 构建 ResourcePPT 请求
        request = ResourcePPT(
            username=username,
            learning_need=input_data.learning_need,
            learning_scenario=input_data.learning_scenario,
            profile=input_data.profile or {},
            teaching_plan=input_data.teaching_plan,
            artifacts=artifacts,
            preferences=_parse_preferences(input_data.agent_config),
        )

        # 3. 计算输出路径
        output_dir = user_resource_ppt_dir(username, resource_key)

        # 4. 调用 PPTService.generate()
        async def progress(message: str, percent: int) -> None:
            await self.emitter.send(self.agent_id, "running", message, percent)

        try:
            artifact = await self.run_with_heartbeat(
                self._ppt_service.generate(request, output_dir, progress=progress),
                messages=[
                    "正在规划课件大纲与版式...",
                    "正在生成教学课件页面...",
                    "正在渲染 HTML 课件，请稍候...",
                ],
                interval_seconds=15.0,
                progress=70,
            )
        except PPTGenerationError as exc:
            logger.exception("PPT 生成失败")
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

        # 5. 填充 html_url，转换为 AgentResult
        artifact.html_url = resource_ppt_url(username, resource_key)
        return self._artifact_to_result(artifact)

    def _artifact_to_result(self, artifact: object) -> AgentResult:
        """将 PPTArtifact 转换为 AgentResult。"""
        from app.shared.ppt.models import PPTArtifact

        if not isinstance(artifact, PPTArtifact):
            return AgentResult(
                success=False,
                title="PPT 生成失败",
                file_type="html",
                error=f"unexpected result type: {type(artifact)}",
                metadata={"agent_id": self.agent_id},
            )

        title = artifact.plan.title
        path = artifact.path
        logger.info(
            "Agent[%s] 生成完成: slides=%d style=%s size_bytes=%d",
            self.agent_id, artifact.slide_count, artifact.template_name,
            path.stat().st_size,
        )
        return AgentResult(
            success=True,
            title=f"{title} - 教学课件",
            file_type="html",
            content="",
            summary=f"生成 {artifact.slide_count} 页 HTML 教学课件",
            metrics={"slide_count": artifact.slide_count},
            metadata={
                "agent_id": self.agent_id,
                "html_file_path": str(path),
                "html_url": artifact.html_url,
                "slide_count": artifact.slide_count,
                "style_name": artifact.template_name,
                "template_id": artifact.template_id,
                "density": artifact.plan.density,
                "file_size": path.stat().st_size,
            },
        )
