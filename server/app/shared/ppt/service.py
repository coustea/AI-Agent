"""PPT 生成服务 — 只负责结合请求、返回生成结果。

generate: 接收已构建好的 Request，调用 Generator，返回 Artifact。
generate_for_path: 接收 PathResourceRequest，返回 AgentResult（路径规划专用）。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from pathlib import Path

from app.config import path_node_ppt_url, user_path_node_ppt_dir
from app.infra.logging import get_logger
from app.shared.ppt.generator import PPTGenerator, ProgressCallback
from app.shared.ppt.models import PPTArtifact, PathPPT, ResourcePPT, PPTPreferences

if TYPE_CHECKING:
    from app.path.schemas import PathResourceRequest
    from app.resource.schemas import AgentResult

logger = get_logger(__name__)


def _extract_core_content(markdown: str) -> str:
    """从教程 markdown 中提取核心知识点讲解部分。

    教程结构：
    - 元数据标题块（标题、摘要、知识点、类型）
    - 1. 概述 / 学习目标
    - 2. 前置知识（可选）
    - 3. 核心知识点讲解  ← 提取这部分
    - 4. 实战示例（可选）
    - 5. 总结回顾

    Returns:
        核心知识点讲解部分的 markdown 内容
    """
    lines = markdown.split("\n")
    core_start = -1
    core_end = len(lines)

    # 查找"核心知识点讲解"或"## 3."开头的部分
    for i, line in enumerate(lines):
        if re.match(r"^##\s*(?:3\.|核心知识点)", line):
            core_start = i
            break

    if core_start == -1:
        # 没找到，返回空
        return ""

    # 查找下一节（4. 实战示例 或 5. 总结回顾）
    for i in range(core_start + 1, len(lines)):
        if re.match(r"^##\s*(?:4\.|5\.|实战示例|总结回顾)", lines[i]):
            core_end = i
            break

    return "\n".join(lines[core_start:core_end]).strip()


class PPTService:
    """PPT 生成服务。

    职责：
    - 接收已构建好的 ResourcePPTRequest / PathPPTRequest
    - 调用 PPTGenerator 生成 HTML 课件并返回 PPTArtifact

    不负责：
    - 数据转换（DownstreamContext/AgentResult → PPTSource）
    - 路径计算和 URL 构建（由 resource/path 模块负责）
    - SSE 事件、数据库持久化、超时控制、LangGraph 编排
    """

    def __init__(self, *, generator: PPTGenerator | None = None) -> None:
        self._generator = generator or PPTGenerator()

    async def generate(
        self,
        request: ResourcePPT | PathPPT,
        output_dir: Path,
        *,
        progress: ProgressCallback | None = None,
    ) -> PPTArtifact:
        """生成 PPT。

        Args:
            request: 已构建好的 PPT 请求（ResourcePPTRequest 或 PathPPTRequest）。
            output_dir: 输出目录（由调用方计算）。
            progress: 可选进度回调。

        Returns:
            PPTArtifact: 生成结果，不含 html_url（由调用方填充）。
        """
        return await self._generator.generate(
            request, output_dir=output_dir, progress=progress,
        )

    async def generate_for_path(
        self,
        request: "PathResourceRequest",
    ) -> "AgentResult":
        """路径规划专用接口 — 接收 PathResourceRequest，返回 AgentResult。

        Args:
            request: 路径规划统一请求参数

        Returns:
            AgentResult: 统一输出结果
        """
        from app.resource.schemas import AgentResult
        from app.shared.ppt import PPTGenerationError

        tutorial = request.tutorial
        if tutorial is None:
            return AgentResult(
                success=False,
                title="PPT 生成失败",
                file_type="html",
                error="缺少教程内容",
            )

        # 构建 PathPPT 请求
        ppt_request = PathPPT(
            username=request.username,
            profile=request.profile,
            preferences=PPTPreferences(),
            path_title=request.path_title,
            path_goal=request.path_goal,
            node_title=request.node_title,
            node_key=request.node_key,
            difficulty=request.difficulty,
            knowledge_points=list(tutorial.knowledge_points or []),
            weak_knowledge_points=list(tutorial.weak_knowledge_points or []),
            tutorial_title=tutorial.title,
            tutorial_summary=tutorial.summary or "",
            tutorial_knowledge_points=list(tutorial.knowledge_points or []),
            tutorial_core_content=_extract_core_content(tutorial.content_markdown),
        )

        # 计算输出路径
        output_dir = user_path_node_ppt_dir(request.username, str(request.path_id), str(request.node_id))

        try:
            artifact = await self.generate(ppt_request, output_dir)
        except PPTGenerationError as exc:
            logger.exception("PPT 生成失败")
            return AgentResult(
                success=False,
                title="PPT 生成失败",
                file_type="html",
                error=str(exc),
                metadata={"generation_stage": exc.stage},
            )

        # 填充 html_url
        artifact.html_url = path_node_ppt_url(request.username, str(request.path_id), str(request.node_id))

        return AgentResult(
            success=True,
            title=f"{artifact.title} - 教学课件",
            file_type="html",
            content="",
            summary=f"生成 {artifact.slide_count} 页 HTML 教学课件",
            metrics={"slide_count": artifact.slide_count},
            metadata={
                "html_file_path": str(artifact.path),
                "html_url": artifact.html_url,
                "slide_count": artifact.slide_count,
                "style_name": artifact.template_name,
                "template_id": artifact.template_id,
                "file_size": artifact.path.stat().st_size,
            },
        )
