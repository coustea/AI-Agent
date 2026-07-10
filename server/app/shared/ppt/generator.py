from __future__ import annotations

import hashlib
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.shared.ppt.compiler import PPTCompileError, compile_ppt_plan
from app.shared.ppt.html import PPTHTMLPublisher, PPTHTMLRenderer
from app.shared.ppt.models import PPTArtifact, PPTPlan, PathPPT, ResourcePPT
from app.shared.ppt.templates import PPTTemplateCatalog, get_ppt_template_catalog


ProgressCallback = Callable[[str, int], Awaitable[None]]

DENSITY_MODES = {
    "concise": "speaker_led",
    "standard": "reading_first",
    "detailed": "reading_first",
}

_CODE_FENCE_RE = re.compile(
    r"^```(?:markdown|md)?\s*(?P<body>.*?)\s*```$",
    re.IGNORECASE | re.DOTALL,
)


class PPTGenerationError(RuntimeError):
    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        super().__init__(f"{stage}: {message}")


class PPTGenerator:
    """HTML 教学 PPT 生成器。"""

    def __init__(
        self,
        *,
        llm: Any | None = None,
        templates: PPTTemplateCatalog | None = None,
        renderer: PPTHTMLRenderer | None = None,
    ) -> None:
        self._llm = llm or get_llm()
        self._templates = templates or get_ppt_template_catalog()
        self._renderer = renderer or PPTHTMLRenderer()

    async def generate(
        self,
        request: ResourcePPT | PathPPT,
        *,
        output_dir: Path,
        progress: ProgressCallback | None = None,
    ) -> PPTArtifact:
        stage = "generation"

        try:
            await self._progress(progress, "正在规划教学叙事与页面结构…", 20)
            plan, markdown = await self._generate_plan(request)

            stage = "template"
            await self._progress(progress, "正在匹配课件模板…", 58)
            resolved = self._templates.resolve(
                plan,
                template_id=request.preferences.template,
            )

            stage = "render"
            await self._progress(progress, "正在渲染 HTML 教学课件…", 82)
            document = self._renderer.render(resolved)

            stage = "publish"
            await self._progress(progress, "正在发布课件…", 96)
            path = PPTHTMLPublisher(output_dir).publish(
                self._safe_file_id(plan.title, markdown),
                document,
            )

            await self._progress(progress, "课件生成完成", 100)

        except PPTGenerationError:
            raise
        except PPTCompileError as exc:
            raise PPTGenerationError("compile", str(exc)) from exc
        except KeyError as exc:
            raise PPTGenerationError("template", str(exc)) from exc
        except Exception as exc:
            raise PPTGenerationError(stage, str(exc)) from exc

        return PPTArtifact(
            path=path,
            plan=plan,
            plan_markdown=markdown,
            template_id=resolved.template.manifest.id,
            template_name=resolved.template.manifest.name,
            slide_count=len(resolved.slides),
        )

    async def _generate_plan(
        self,
        request: ResourcePPT | PathPPT,
    ) -> tuple[PPTPlan, str]:
        prompt = prompts.get("ppt").render(
            "slide_outline",
            request=request.model_dump_json(indent=2),
        )

        response = await self._llm.ainvoke(prompt)
        markdown = self._normalize_markdown(self._response_to_text(response))

        selected_template = request.preferences.template
        template_family = "auto"

        if selected_template != "auto":
            template_family = self._templates.get(selected_template).manifest.family

        density = DENSITY_MODES[request.preferences.density]

        plan = compile_ppt_plan(
            markdown,
            density=density,
            template_family=template_family,
        )

        return plan, markdown

    @classmethod
    def available_templates(cls) -> list[dict[str, object]]:
        catalog = get_ppt_template_catalog()

        return [
            {
                "id": template.manifest.id,
                "name": template.manifest.name,
                "description": template.manifest.description,
                "family": template.manifest.family,
                "scheme": template.manifest.scheme,
                "tags": template.manifest.tags,
            }
            for template in catalog.all()
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
    def _response_to_text(response: Any) -> str:
        content = response.content if hasattr(response, "content") else response

        if isinstance(content, list):
            return "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )

        return str(content)

    @staticmethod
    def _normalize_markdown(markdown: str) -> str:
        text = markdown.strip()
        fence_match = _CODE_FENCE_RE.match(text)

        if fence_match:
            text = fence_match.group("body").strip()

        first_title = re.search(r"^#\s+", text, re.MULTILINE)
        if first_title and first_title.start() > 0:
            text = text[first_title.start() :].strip()

        return text

    @staticmethod
    def _safe_file_id(title: str, markdown: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        digest = hashlib.sha1(f"{title}\n{markdown}".encode("utf-8")).hexdigest()[:10]

        if slug:
            return f"{slug[:42].strip('-')}-{digest}"

        return f"teaching-slides-{digest}"