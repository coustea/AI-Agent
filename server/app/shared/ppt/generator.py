from __future__ import annotations

import asyncio
from datetime import datetime
import hashlib
import json
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.infra.llm import _is_infra_error, get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.shared.ppt.html import PPTHTMLPublisher, PPTHTMLRenderer, PPTPublication
from app.shared.ppt.models import PPTArtifact, PPTPlan, PPTPreferences, PathPPT, ResourcePPT
from app.shared.ppt.templates import PPTTemplateCatalog, get_ppt_template_catalog


ProgressCallback = Callable[[str, int], Awaitable[None]]
logger = get_logger(__name__)

_PLAN_ATTEMPTS = 3
_PLAN_MAX_TOKENS = 4_200
_PLAN_RETRY_DELAYS_SECONDS = (1.0, 3.0)
_PRESENTATION_TIMEZONE = ZoneInfo("Asia/Shanghai")


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
        self._llm = llm or get_llm("ppt")
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
            plan, plan_json = await self._generate_plan(request)

            stage = "template"
            await self._progress(progress, "正在匹配课件模板…", 58)
            resolved = self._templates.resolve(plan)

            stage = "render"
            await self._progress(progress, "正在渲染 HTML 教学课件…", 82)
            publication = PPTPublication(
                generated_at=datetime.now(_PRESENTATION_TIMEZONE)
            )
            document = self._renderer.render(resolved, publication)

            stage = "publish"
            await self._progress(progress, "正在发布课件…", 96)
            path = PPTHTMLPublisher(output_dir).publish(
                self._safe_file_id(plan.title, plan_json),
                document,
            )

            await self._progress(progress, "课件生成完成", 100)

        except PPTGenerationError:
            raise
        except KeyError as exc:
            raise PPTGenerationError("template", str(exc)) from exc
        except Exception as exc:
            raise PPTGenerationError(stage, str(exc)) from exc

        return PPTArtifact(
            path=path,
            plan=plan,
            plan_json=plan_json,
            generated_at=publication.generated_at,
            template_id=resolved.template.manifest.id,
            template_name=resolved.template.manifest.name,
            slide_count=len(resolved.slides),
        )

    async def _generate_plan(
        self,
        request: ResourcePPT | PathPPT,
    ) -> tuple[PPTPlan, str]:
        prompt = prompts.get("ppt").render(
            "slide_plan",
            request=json.dumps(
                self._prompt_payload(request),
                ensure_ascii=False,
                indent=2,
            ),
            ppt_preferences=self._render_preferences(request.preferences),
        )
        for attempt in range(1, _PLAN_ATTEMPTS + 1):
            try:
                plan = await self._llm.ainvoke_json(
                    PPTPlan,
                    prompt,
                    temperature=0.15,
                    max_tokens=_PLAN_MAX_TOKENS,
                )
                return plan, plan.model_dump_json(indent=2)
            except Exception as exc:
                if _is_infra_error(exc):
                    raise

                if attempt >= _PLAN_ATTEMPTS:
                    raise
                logger.warning(
                    "PPT plan attempt failed; retrying dedicated generation channel: "
                    "attempt=%d/%d error=%s",
                    attempt,
                    _PLAN_ATTEMPTS,
                    exc,
                )
                await asyncio.sleep(_PLAN_RETRY_DELAYS_SECONDS[attempt - 1])

        raise RuntimeError("PPT plan generation exhausted without a result")

    @staticmethod
    def _prompt_payload(request: ResourcePPT | PathPPT) -> dict[str, Any]:
        """Create the small, content-only input accepted by the outline model."""
        if isinstance(request, ResourcePPT):
            return {
                "learning_need": PPTGenerator._clip(request.learning_need, 800),
                "learning_scenario": PPTGenerator._clip(request.learning_scenario, 80),
                "profile": PPTGenerator._profile_text(request.profile),
                "teaching_plan": PPTGenerator._clip(request.teaching_plan or "", 6_000),
                "artifacts": [
                    {
                        "agent_id": PPTGenerator._clip(source.agent_id, 32),
                        "title": PPTGenerator._clip(source.title, 120),
                        "summary": PPTGenerator._clip(source.summary, 320),
                        "materials": [
                            PPTGenerator._clip(material, 360)
                            for material in source.materials[:4]
                        ],
                    }
                    for source in request.artifacts[:6]
                ],
            }

        return {
            "path_title": PPTGenerator._clip(request.path_title, 120),
            "path_goal": PPTGenerator._clip(request.path_goal, 600),
            "node_title": PPTGenerator._clip(request.node_title, 120),
            "difficulty": PPTGenerator._clip(request.difficulty, 40),
            "profile": PPTGenerator._profile_text(request.profile),
            "knowledge_points": [PPTGenerator._clip(item, 100) for item in request.knowledge_points[:12]],
            "weak_knowledge_points": [PPTGenerator._clip(item, 100) for item in request.weak_knowledge_points[:8]],
            "tutorial_title": PPTGenerator._clip(request.tutorial_title, 120),
            "tutorial_summary": PPTGenerator._clip(request.tutorial_summary, 800),
            "tutorial_knowledge_points": [
                PPTGenerator._clip(item, 100) for item in request.tutorial_knowledge_points[:12]
            ],
            "tutorial_core_content": PPTGenerator._clip(request.tutorial_core_content, 7_000),
        }

    @staticmethod
    def _profile_text(profile: dict[str, Any] | str) -> str:
        text = profile if isinstance(profile, str) else json.dumps(profile, ensure_ascii=False)
        return PPTGenerator._clip(text, 1_600)

    @staticmethod
    def _clip(value: str, limit: int) -> str:
        return " ".join(value.split())[:limit]

    @staticmethod
    def _render_preferences(preferences: PPTPreferences) -> str:
        template_map = {
            "auto": "根据学习需求自行选择内容组织取向，不输出任何视觉模板名称。",
            "teaching": "内容取向偏课堂讲授，强化概念递进、定义边界和教师口头讲解。",
            "technical": "内容取向偏技术解析，强化机制、数据流、约束条件和系统关系。",
            "case_study": "内容取向偏案例拆解，围绕真实情境说明问题、条件、过程和取舍。",
            "exam_review": "内容取向偏复习巩固，突出考点辨析、易错点和可复述的知识结构。",
        }
        narrative_map = {
            "concept": "从概念建立开始，先定义对象和边界，再解释机制与应用。",
            "case_driven": "从具体案例或工程场景切入，再抽象出概念、机制和判断方法。",
            "problem_led": "从一个核心问题或认知冲突出发，逐步推导出所需知识结构。",
            "review": "以复习巩固为主线，先唤起已有知识，再补齐薄弱点和误区。",
        }
        density_map = {
            "concise": "页面正文保持精炼，每页优先 3～4 个要点，把补充解释放入讲稿。",
            "standard": "页面正文保持标准教学密度，每页 4～5 个要点，讲稿补充关键承接。",
            "detailed": "页面正文覆盖更多条件、限制和推理细节，每页可使用 5～6 个要点，但不得堆砌。",
        }
        emphasis_map = {
            "core_concepts": "核心概念：优先讲清定义、对象、成立条件、体系位置。",
            "cases": "案例应用：优先补充真实场景、输入条件、判断过程和适用边界。",
            "pitfalls": "易错误区：优先指出常见误解、错误原因和正确判断方法。",
            "derivation": "推导过程：优先展示因果链、状态变化、机制步骤和结论来源。",
        }
        emphasis_text = "\n".join(
            f"- {emphasis_map[value]}" for value in preferences.emphasis
        )

        return "\n".join(
            [
                f"- 内容取向 template={preferences.template}: {template_map[preferences.template]}",
                f"- 叙事方式 narrative_style={preferences.narrative_style}: {narrative_map[preferences.narrative_style]}",
                f"- 内容密度 density={preferences.density}: {density_map[preferences.density]}",
                "- 教学重点 emphasis:",
                emphasis_text,
            ]
        )

    @staticmethod
    async def _progress(
        callback: ProgressCallback | None,
        message: str,
        percent: int,
    ) -> None:
        if callback is not None:
            await callback(message, percent)

    @staticmethod
    def _safe_file_id(title: str, plan_json: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        digest = hashlib.sha1(f"{title}\n{plan_json}".encode("utf-8")).hexdigest()[:10]

        if slug:
            return f"{slug[:42].strip('-')}-{digest}"

        return f"teaching-slides-{digest}"
