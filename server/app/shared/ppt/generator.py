from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.shared.ppt.compiler import compile_ppt_plan
from app.shared.ppt.html import PPTHTMLPublisher, PPTHTMLRenderer
from app.shared.ppt.models import (
    PPTArtifact,
    PPTPlan,
    PathPPTRequest,
    ResourcePPTRequest,
)
from app.shared.ppt.templates import get_ppt_template_catalog


ProgressCallback = Callable[[str, int], Awaitable[None]]

DENSITY_MODES = {
    "concise": "speaker_led",
    "standard": "reading_first",
    "detailed": "reading_first",
}


class PPTGenerationError(RuntimeError):
    """PPT generation failure with the failed stage preserved."""

    def __init__(self, stage: str, message: str):
        self.stage = stage
        super().__init__(f"{stage}: {message}")


class PPTGenerator:
    """Generate and publish a complete HTML PPT behind one deep Interface."""

    def __init__(
        self,
        *,
        llm: Any | None = None,
    ):
        self._llm = llm or get_llm()
        self._templates = get_ppt_template_catalog()
        self._renderer = PPTHTMLRenderer()

    async def generate(
        self,
        request: ResourcePPTRequest | PathPPTRequest,
        *,
        output_dir: Path,
        progress: ProgressCallback | None = None,
    ) -> PPTArtifact:
        stage = "planning"
        try:
            await self._progress(progress, "正在规划教学叙事与逐页画面...", 25)
            plan = await self._plan(request)
            plan = plan.model_copy(
                update={"density": DENSITY_MODES[request.preferences.density]}
            )

            stage = "template"
            await self._progress(progress, "正在匹配模板并编排多样化教学布局...", 58)
            resolved = self._templates.resolve(
                plan,
                template_id=request.preferences.template,
            )

            stage = "render"
            await self._progress(progress, "正在渲染动画教学课件...", 82)
            html = self._renderer.render(resolved)

            stage = "publish"
            await self._progress(progress, "正在发布 HTML 教学课件...", 96)
            path = PPTHTMLPublisher(output_dir).publish("slides", html)
        except Exception as exc:
            if isinstance(exc, PPTGenerationError):
                raise
            raise PPTGenerationError(stage, str(exc)) from exc

        return PPTArtifact(
            path=path,
            plan=plan,
            template_id=resolved.template.manifest.id,
            template_name=resolved.template.manifest.name,
            slide_count=len(resolved.slides),
        )

    async def _plan(
        self,
        request: ResourcePPTRequest | PathPPTRequest,
    ) -> PPTPlan:
        prompt = prompts.get("ppt").render(
            "slide_outline",
            request=request.model_dump_json(indent=2),
        )
        response = await self._llm.ainvoke(prompt)
        markdown = response.content if hasattr(response, "content") else str(response)
        return compile_ppt_plan(
            markdown,
            title="",  # 由 Markdown 内 # 标题指定
            density=DENSITY_MODES[request.preferences.density],
            template_family=request.preferences.template
            if request.preferences.template != "auto"
            else "auto",
        )

    @classmethod
    def available_templates(cls) -> list[dict[str, object]]:
        return [
            {
                "id": template.manifest.id,
                "name": template.manifest.name,
                "description": template.manifest.description,
                "family": template.manifest.family,
                "scheme": template.manifest.scheme,
                "tags": template.manifest.tags,
            }
            for template in get_ppt_template_catalog().all()
        ]

    @staticmethod
    async def _progress(
        callback: ProgressCallback | None,
        message: str,
        percent: int,
    ) -> None:
        if callback is not None:
            await callback(message, percent)
