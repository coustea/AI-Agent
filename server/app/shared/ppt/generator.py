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
        stage = "generation"
        try:
            await self._progress(progress, "正在基于教学资源生成课件内容...", 25)
            plan, plan_markdown = await self._generate_markdown(request)
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
            plan_markdown=plan_markdown,
            template_id=resolved.template.manifest.id,
            template_name=resolved.template.manifest.name,
            slide_count=len(resolved.slides),
        )

    async def _generate_markdown(
        self,
        request: ResourcePPTRequest | PathPPTRequest,
    ) -> tuple[PPTPlan, str]:
        """基于上游资源和协同计划，让 LLM 直接生成 Markdown 课件。

        不做二次规划——协同计划已由 PlanningAgent 完成，
        此处只将已有素材组织为课件页面。
        """
        prompt = prompts.get("ppt").render(
            "slide_outline",
            request=request.model_dump_json(indent=2),
        )
        response = await self._llm.ainvoke(prompt)
        markdown = response.content if hasattr(response, "content") else str(response)
        plan = compile_ppt_plan(
            markdown,
            title="",  # 由 Markdown 内 # 标题指定
            density=DENSITY_MODES[request.preferences.density],
            template_family=self._resolve_template_family(
                request.preferences.template
            ),
        )
        return plan, markdown

    def _resolve_template_family(self, template_id: str) -> str:
        """从模板 ID 解析 family，用于 compile_ppt_plan。

        PPTPreferences.template 存的是用户选择的模板 ID（如
        "instructional-editorial"），而 compile_ppt_plan 需要的是
        TemplateFamily（"auto" / "editorial" / "technical"）。
        """
        if template_id == "auto":
            return "auto"
        try:
            template = self._templates.get(template_id)
        except KeyError:
            return "auto"
        return template.manifest.family

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
