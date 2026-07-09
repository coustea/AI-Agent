from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.shared.ppt.compiler import compile_ppt_plan
from app.shared.ppt.html import PPTHTMLPublisher, PPTHTMLRenderer
from app.shared.ppt.models import PPTArtifact, PPTPlan, PathPPTRequest, ResourcePPTRequest
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
    """生成知识点讲解型 HTML PPT。"""

    def __init__(self, *, llm: Any | None = None):
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
            await self._progress(progress, "正在生成知识点讲解型课件结构...", 25)
            plan, plan_markdown = await self._generate_markdown(request)
            plan = plan.model_copy(
                update={"density": DENSITY_MODES[request.preferences.density]}
            )

            stage = "template"
            await self._progress(progress, "正在匹配精修课件模板...", 58)
            resolved = self._templates.resolve(
                plan,
                template_id=request.preferences.template,
            )

            stage = "render"
            await self._progress(progress, "正在渲染教学 PPT HTML...", 84)
            html = self._renderer.render(resolved)

            stage = "publish"
            await self._progress(progress, "正在发布 HTML 课件...", 96)
            file_id = self._safe_file_id(plan.title)
            path = PPTHTMLPublisher(output_dir).publish(file_id, html)

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
        prompt = prompts.get("ppt").render(
            "slide_outline",
            request=request.model_dump_json(indent=2),
        )
        response = await self._llm.ainvoke(prompt)
        markdown = response.content if hasattr(response, "content") else str(response)

        plan = compile_ppt_plan(
            markdown,
            title="",
            density=DENSITY_MODES[request.preferences.density],
            template_family=self._resolve_template_family(request.preferences.template),
        )
        return plan, markdown

    def _resolve_template_family(self, template_id: str) -> str:
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

    @staticmethod
    def _safe_file_id(title: str) -> str:
        text = title.strip().lower()
        text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
        text = text.strip("-")
        if not text:
            return "slides"

        # PPTHTMLPublisher 当前只允许 A-Z a-z 0-9 _ -
        # 中文会被过滤掉，因此这里再做一次 ASCII 兜底。
        ascii_text = re.sub(r"[^a-z0-9_-]+", "", text)
        return ascii_text[:48] or "slides"