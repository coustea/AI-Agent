from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from app.infra.llm import _is_infra_error, get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.shared.ppt.html import PPTHTMLPublisher, PPTHTMLRenderer
from app.shared.ppt.models import PPTArtifact, PPTPlan, PPTPreferences, PathPPT, ResourcePPT
from app.shared.ppt.templates import PPTTemplateCatalog, get_ppt_template_catalog


ProgressCallback = Callable[[str, int], Awaitable[None]]
logger = get_logger(__name__)

_PLAN_ATTEMPTS = 3
_PLAN_MAX_TOKENS = 4_200
_PLAN_RETRY_DELAYS_SECONDS = (1.0, 3.0)


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
            document = self._renderer.render(resolved)

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
                if attempt >= _PLAN_ATTEMPTS:
                    if self._can_use_fallback_plan(exc):
                        logger.warning(
                            "PPT plan LLM unavailable after %d attempts; "
                            "using fallback teaching deck: error=%s",
                            attempt,
                            exc,
                        )
                        plan = self._fallback_plan(request)
                        return plan, plan.model_dump_json(indent=2)
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
    def _can_use_fallback_plan(exc: Exception) -> bool:
        if not _is_infra_error(exc):
            return False

        text = f"{type(exc).__name__}: {exc}".lower()
        permanent_markers = (
            "authentication",
            "permission",
            "permissiondenied",
            "invalid api key",
            "notfound",
            "not found",
            "401",
            "403",
        )
        return not any(marker in text for marker in permanent_markers)

    @staticmethod
    def _fallback_plan(request: ResourcePPT | PathPPT) -> PPTPlan:
        title = PPTGenerator._fallback_title(request)
        context = PPTGenerator._fallback_context(request)
        keywords = PPTGenerator._fallback_keywords(request, title)

        return PPTPlan.model_validate(
            {
                "title": title,
                "subtitle": "网络连接暂时不可用，已生成保底教学课件",
                "purpose": "在大纲模型暂时不可用时，保留可讲授、可打开的基础课件。",
                "audience": "计算机课程学习者。",
                "narrative": (
                    "先给出学习路径和目标，再用定义、边界、机制、对比、误区和知识地图"
                    "搭建最小可讲授结构。"
                ),
                "density": "speaker_led",
                "language": "zh-CN",
                "template_preference": {
                    "family": "teaching",
                    "scheme": "light",
                    "keywords": keywords[:6],
                },
                "slides": [
                    {
                        "type": "cover",
                        "title": title,
                        "subtitle": "网络连接暂时不可用，已生成保底教学课件",
                        "statement": PPTGenerator._clip(context, 180),
                        "cover_meta": {
                            "organization": "高校计算机课程",
                            "keywords": keywords[:6],
                        },
                    },
                    {
                        "type": "agenda",
                        "title": "学习路径",
                        "statement": "先建立概念，再理解机制，最后形成判断方法。",
                        "steps": [
                            {
                                "key": "01",
                                "title": "概念定位",
                                "detail": "明确本主题讨论的对象、作用和学习边界。",
                            },
                            {
                                "key": "02",
                                "title": "机制过程",
                                "detail": "按状态变化、数据流或控制流梳理运行过程。",
                            },
                            {
                                "key": "03",
                                "title": "辨析应用",
                                "detail": "通过对比和误区把知识转成可复述的判断规则。",
                            },
                        ],
                    },
                    {
                        "type": "learning_goals",
                        "title": "学习目标",
                        "statement": "完成学习后，应能说清概念、画出关系并解释关键过程。",
                        "points": [
                            {
                                "label": "说清对象",
                                "detail": f"用自己的话解释“{title}”解决什么问题。",
                            },
                            {
                                "label": "建立结构",
                                "detail": "把相关概念放入层次、状态或流程关系中理解。",
                            },
                            {
                                "label": "判断条件",
                                "detail": "识别概念成立的前提、限制和常见混淆点。",
                            },
                        ],
                    },
                    {
                        "type": "hook_question",
                        "title": "开篇问题",
                        "question": f"如果要向同学讲清“{title}”，第一步应该先解释什么？",
                        "points": [
                            {
                                "label": "先定对象",
                                "detail": "确认讨论的是数据、程序、系统行为还是抽象模型。",
                            },
                            {
                                "label": "再找变化",
                                "detail": "观察它在输入、执行、存储或通信过程中如何变化。",
                            },
                            {
                                "label": "最后归纳",
                                "detail": "把变化背后的规则总结成可迁移的方法。",
                            },
                        ],
                    },
                    {
                        "type": "definition",
                        "title": "核心定义",
                        "statement": PPTGenerator._clip(context, 180),
                        "points": [
                            {
                                "label": "对象",
                                "detail": "定义首先说明被研究的核心对象是什么。",
                            },
                            {
                                "label": "职责",
                                "detail": "说明它在计算机系统或算法过程中的作用。",
                            },
                            {
                                "label": "边界",
                                "detail": "说明它不等同于哪些相近概念。",
                            },
                        ],
                    },
                    {
                        "type": "concept_boundary",
                        "title": "概念边界",
                        "statement": "学习计算机课程时，边界比记忆术语更重要。",
                        "points": [
                            {
                                "label": "不要只背名称",
                                "detail": "同一个术语在不同章节里可能强调不同层面。",
                            },
                            {
                                "label": "关注输入输出",
                                "detail": "看清它接收什么、改变什么、交给谁继续处理。",
                            },
                            {
                                "label": "关注限制条件",
                                "detail": "很多结论只在特定前提下成立。",
                            },
                        ],
                    },
                    {
                        "type": "mechanism_overview",
                        "title": "机制总览",
                        "statement": "把机制拆成连续步骤，能避免课件只停留在概念解释。",
                        "steps": [
                            {
                                "key": "01",
                                "title": "输入进入",
                                "detail": "先明确系统、算法或结构接收到的初始信息。",
                            },
                            {
                                "key": "02",
                                "title": "状态改变",
                                "detail": "观察关键对象在规则约束下如何发生变化。",
                            },
                            {
                                "key": "03",
                                "title": "结果输出",
                                "detail": "说明变化结束后产生的结果、影响或下一步动作。",
                            },
                        ],
                    },
                    {
                        "type": "knowledge_explain",
                        "title": "理解线索一",
                        "statement": "优先寻找“为什么需要它”，再学习“它是什么”。",
                        "points": [
                            {
                                "label": "问题来源",
                                "detail": "每个概念都对应一个需要被解决的计算问题。",
                            },
                            {
                                "label": "设计取舍",
                                "detail": "机制设计通常是在效率、空间、可靠性之间权衡。",
                            },
                            {
                                "label": "适用范围",
                                "detail": "理解适用条件比记住结论更稳定。",
                            },
                        ],
                    },
                    {
                        "type": "knowledge_explain",
                        "title": "理解线索二",
                        "statement": "把静态定义转成动态过程，是计算机课程讲解的关键。",
                        "points": [
                            {
                                "label": "画状态",
                                "detail": "用状态节点表示对象可能处于的不同阶段。",
                            },
                            {
                                "label": "画迁移",
                                "detail": "用箭头表示触发条件和变化方向。",
                            },
                            {
                                "label": "讲原因",
                                "detail": "每一次变化都要说明由什么规则触发。",
                            },
                        ],
                    },
                    {
                        "type": "comparison",
                        "title": "对比辨析",
                        "statement": "用对比表可以快速暴露相近概念的本质差异。",
                        "table": {
                            "headers": ["维度", "容易混淆的理解", "更准确的理解"],
                            "rows": [
                                ["记忆方式", "背术语定义", "理解对象、条件和过程"],
                                ["学习重点", "只看结论", "追踪状态变化与因果链"],
                                ["应用方式", "套固定题型", "先判断前提再选择方法"],
                            ],
                        },
                    },
                    {
                        "type": "misconception",
                        "title": "常见误区",
                        "statement": "保底课件只提供基础框架，后续仍应补充课程细节。",
                        "misconceptions": [
                            {
                                "myth": "能说出定义就算理解",
                                "reason": "定义不能替代过程、条件和例外情况。",
                                "truth": "真正理解要能解释它如何工作。",
                            },
                            {
                                "myth": "所有章节都能用同一种图表示",
                                "reason": "数据结构、操作系统、网络等课程关注对象不同。",
                                "truth": "应按主题选择状态图、流程图、结构图或对比图。",
                            },
                        ],
                    },
                    {
                        "type": "knowledge_map",
                        "title": "知识地图",
                        "statement": title,
                        "branches": [
                            {"label": "概念", "keywords": ["对象", "职责", "边界"]},
                            {"label": "过程", "keywords": ["输入", "状态", "输出"]},
                            {"label": "判断", "keywords": ["条件", "限制", "误区"]},
                        ],
                    },
                    {
                        "type": "closing",
                        "title": "总结",
                        "statement": "先保住可讲授结构，再在网络恢复后生成更精细的大纲。",
                        "takeaway": "网络连接暂时不可用时，本课件可作为基础讲授版本继续使用。",
                    },
                ],
            }
        )

    @staticmethod
    def _fallback_title(request: ResourcePPT | PathPPT) -> str:
        if isinstance(request, ResourcePPT):
            return PPTGenerator._clip(request.learning_need, 64) or "计算机课程讲解"

        return (
            PPTGenerator._clip(request.node_title, 64)
            or PPTGenerator._clip(request.tutorial_title, 64)
            or "计算机课程讲解"
        )

    @staticmethod
    def _fallback_context(request: ResourcePPT | PathPPT) -> str:
        parts: list[str] = []
        if isinstance(request, ResourcePPT):
            parts.extend(
                [
                    request.teaching_plan or "",
                    *(source.summary for source in request.artifacts),
                    *(material for source in request.artifacts for material in source.materials),
                ]
            )
        else:
            parts.extend(
                [
                    request.path_goal,
                    request.tutorial_summary,
                    request.tutorial_core_content,
                    *request.knowledge_points,
                    *request.tutorial_knowledge_points,
                ]
            )

        text = " ".join(part.strip() for part in parts if part and part.strip())
        return PPTGenerator._clip(text, 180) or "围绕核心概念、机制过程和应用边界展开讲解。"

    @staticmethod
    def _fallback_keywords(
        request: ResourcePPT | PathPPT,
        title: str,
    ) -> list[str]:
        candidates: list[str] = []
        if isinstance(request, ResourcePPT):
            candidates.extend(source.title for source in request.artifacts)
            candidates.extend(
                material for source in request.artifacts for material in source.materials
            )
        else:
            candidates.extend(request.knowledge_points)
            candidates.extend(request.tutorial_knowledge_points)

        words = [title, *candidates]
        result: list[str] = []
        for word in words:
            clipped = PPTGenerator._clip(word, 18)
            if clipped and clipped not in result:
                result.append(clipped)
            if len(result) >= 6:
                break

        return result or ["计算机课程"]

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
