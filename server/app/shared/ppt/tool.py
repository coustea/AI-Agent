"""PPT 工具层 (app.shared.ppt.tool) —— 基于无状态流与通用 subagent 工具。

包含：
1. 外部工具：供 chat、resource、path 等模块统一调用的 ``generate_ppt_deck`` (``build_ppt_subagent_tool``)
2. 架构师工具集 (``build_ppt_planner_tools``)：
   - ``init_deck_plan``：写入 ``DESIGN_PLAN.json`` 与幻灯片骨架（无内存 state 闭包）
   - ``subagent``：复用 ``app.shared.tools.build_subagent_tool`` 派生无状态子智能体并发编写 ``slides/sXX.py``
   - ``build_and_audit_deck``：编译 ``deck.pptx``、执行 OOXML 审计并落盘 ``AUDIT_REPORT.json``
3. 单页确定性校验工具：``test_slide(slide_id)``
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Callable, Coroutine
from uuid import uuid4

from pydantic import BaseModel, Field
from pptx import Presentation
from pptx.util import Inches

from app.config import resource_ppt_url, static_url, user_resource_ppt_dir
from app.shared.ppt.renderer import (
    build_thumbnail_grid,
    publish_viewer_html,
    render_pptx_thumbnails,
)
from app.shared.ppt.schemas import (
    DeckDesignPlan,
    PPTPreferences,
    PPTSource,
    ResourcePPT,
    SlideSpec,
)
from app.shared.ppt.validator import audit_pptx, audit_single_slide
from app.shared.ppt.workspace import copy_slide_skeleton, write_workspace_scaffold
from app.shared.tools import (
    SkillLoader,
    Tool,
    build_builtin_tools,
    build_copy_skill_template_tool,
    build_load_skill_tool,
    build_subagent_tool,
    get_skill_loader,
)

ProgressCallback = Callable[[str, int], Coroutine[Any, Any, None]]


# ── 工具参数模型 (Pydantic Schema) ──────────────────────────────────────────


class GeneratePPTToolArgs(BaseModel):
    """生成 PPTX 教学课件的外部工具参数。"""

    topic: str = Field(min_length=2, description="课件主题名称")
    learning_goal: str = Field(min_length=2, description="本课件的核心教学目标")
    source_points: list[str] = Field(
        default_factory=list,
        description="可选：上游提炼的核心知识点或教程摘要列表",
    )
    narrative_style: str = Field(
        default="concept",
        description="叙事风格：concept | case_driven | problem_led | review",
    )


class InitDeckPlanArgs(BaseModel):
    """初始化 DESIGN_PLAN.json 与所有幻灯片骨架的参数。"""

    title: str = Field(description="演示文稿主标题")
    subtitle: str = Field(default="", description="副标题或引导问题")
    palette_name: str = Field(
        default="ocean_editorial",
        description="配色预设：ocean_editorial | emerald_academy | warm_terracotta",
    )
    slides: list[SlideSpec] = Field(
        description="6 到 10 页结构化幻灯片规划清单，每页必须指定 id, layout, title, core_claim, key_points",
    )


class BuildAndAuditDeckArgs(BaseModel):
    """编译 deck.pptx 并运行 OOXML 几何与排版审计。"""


class TestSlideArgs(BaseModel):
    """验证单个 slides/sXX.py 的参数。"""

    slide_id: str = Field(description="要验证的幻灯片 ID，例如 's01'")


# ── 编译与确定性审计底层函数 ────────────────────────────────────────────────


def _test_single_slide_script(output_dir: Path, slide_id: str) -> tuple[bool, str]:
    """独立测试单个 slides/sXX.py 是否可被 python-pptx 成功执行且通过 OOXML 确定性几何审计。"""
    clean_id = slide_id.strip().removesuffix(".py").removeprefix("slides/")
    slide_py = output_dir / f"slides/{clean_id}.py"
    if not slide_py.is_file():
        return False, f"File not found: slides/{clean_id}.py"

    if str(output_dir) not in sys.path:
        sys.path.insert(0, str(output_dir))

    try:
        theme_file = output_dir / "theme_tokens.py"
        theme_ns: dict[str, Any] = {}
        if theme_file.is_file():
            exec(theme_file.read_text(encoding="utf-8"), theme_ns)
        theme = theme_ns.get("THEME") or {}

        spec = importlib.util.spec_from_file_location(f"test_{clean_id}", slide_py)
        if spec is None or spec.loader is None:
            return False, f"Cannot load module spec for slides/{clean_id}.py"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "build_slide"):
            return False, f"slides/{clean_id}.py must define def build_slide(prs, theme):"

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        module.build_slide(prs, theme)

        if len(prs.slides) != 1:
            return False, f"build_slide must add exactly 1 slide (added {len(prs.slides)})"

        idx_num = int(clean_id.lstrip("s") or "1")
        errors = audit_single_slide(prs.slides[0], idx_num)
        if errors:
            return False, "OOXML Single-Slide Geometry Audit Failed:\n- " + "\n- ".join(errors)
        return True, f"PASS: slides/{clean_id}.py executed cleanly and passed OOXML geometry audit."
    except Exception as exc:
        return False, f"Runtime error in slides/{clean_id}.py: {type(exc).__name__}: {exc}"


def _compile_and_audit_workspace(output_dir: Path, title: str | None = None) -> tuple[bool, dict[str, Any]]:
    """执行 build_deck.py，运行 OOXML 审计，渲染缩略图网格，发布 slides.html 并落盘 AUDIT_REPORT.json。"""
    if str(output_dir) not in sys.path:
        sys.path.insert(0, str(output_dir))

    build_py = output_dir / "build_deck.py"
    if not build_py.is_file():
        return False, {"error": "build_deck.py not found. Call init_deck_plan first."}

    plan_path = output_dir / "DESIGN_PLAN.json"
    expected_count: int | None = None
    deck_title = title or "教学演示课件"
    if plan_path.is_file():
        try:
            plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
            expected_count = len(plan_data.get("slides") or [])
            deck_title = str(plan_data.get("title") or deck_title)
        except Exception:
            expected_count = None

    try:
        spec = importlib.util.spec_from_file_location("ppt_build_deck", build_py)
        if spec is None or spec.loader is None:
            return False, {"error": "Cannot load build_deck.py"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        pptx_path: Path = mod.compile_deck("deck.pptx")
    except Exception as exc:
        return False, {"error": f"Failed to compile deck.pptx: {type(exc).__name__}: {exc}"}

    audit_report = audit_pptx(pptx_path, expected_slides=expected_count)
    slide_pngs = render_pptx_thumbnails(pptx_path, output_dir)
    grid_path = build_thumbnail_grid(slide_pngs, output_dir / "thumbnails" / "grid.png")
    html_path = publish_viewer_html(pptx_path, slide_pngs, output_dir, title=deck_title)

    audit_report["pptx_path"] = str(pptx_path)
    audit_report["html_path"] = str(html_path)
    audit_report["grid_path"] = str(grid_path.relative_to(output_dir))
    (output_dir / "AUDIT_REPORT.json").write_text(
        json.dumps(audit_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return bool(audit_report.get("passed")), audit_report


# ── 工具工厂函数（无状态流）───────────────────────────────────────────────


def build_test_slide_tool(output_dir: Path) -> Tool:
    """构造无状态单页校验工具 test_slide(slide_id)。"""

    async def _handler(slide_id: str) -> str:
        _, detail = _test_single_slide_script(output_dir, slide_id)
        return detail

    return Tool(
        name="test_slide",
        description="Execute slides/<slide_id>.py on a test Presentation and run the deterministic OOXML single-slide geometry checker.",
        args_model=TestSlideArgs,
        handler=_handler,
    )


def build_ppt_planner_tools(
    output_dir: Path,
    *,
    skill_loader: SkillLoader | None = None,
    topic: str = "",
    progress: ProgressCallback | None = None,
) -> list[Tool]:
    """构造供 PPT 架构师主智能体调用的无状态工具集（直接通过 output_dir 文件系统流转）。"""
    loader = skill_loader or get_skill_loader()
    cookbook_text = loader.get_content("pptx", "python_pptx_cookbook.md")

    slide_subagent_system_prompt = (
        "你是负责编写单页 PowerPoint 代码的无状态子智能体 (SlideSubagent)。\n"
        "工作区 `slides/sXX.py` 中已准备好契约骨架。请用 `read` 查看当前骨架，"
        "然后用 `edit` 或 `write` 将 `# BESPOKE_SLIDE_BODY` 替换为符合该页教学主题与版式方向的专属 `python-pptx` 代码：\n"
        "- `hero_cover`：深色背景 `apply_slide_background(slide, theme['bg_dark'])`，搭配大标题与 3 张顶部色条亮点卡片或指标卡。\n"
        "- `process_flow`：绘制 3 个阶段的递进卡片并在卡片间隙调用 `add_arrow_right`。\n"
        "- `comparison_matrix`：绘制左右双栏对比卡片。\n"
        "- `bento_quad`：绘制 2x2 四宫格 Bento 矩阵卡片。\n"
        "- `code_or_formula_spotlight`：左侧调用 `add_code_panel` 绘制深色代码/公式面板，右侧堆叠解析卡片。\n"
        "- `summary_takeaways`：深色背景 `theme['bg_dark']` 与横向复盘要点卡。\n\n"
        '严禁破坏 `def build_slide(prs, theme: dict) -> None:` 签名，所有元素必须保持在 13.333"x7.500" 安全边距内且互不重叠。\n'
        "编写完成后必须调用 `test_slide(slide_id=...)` 验证返回 PASS。\n\n"
        f"{cookbook_text}"
    )

    test_slide_tool = build_test_slide_tool(output_dir)
    copy_tpl_tool = build_copy_skill_template_tool(output_dir, loader, only=["pptx"])

    async def _init_deck_plan(
        title: str,
        slides: list[Any],
        subtitle: str = "",
        palette_name: str = "ocean_editorial",
    ) -> str:
        try:
            plan = DeckDesignPlan.model_validate(
                {
                    "title": title,
                    "subtitle": subtitle,
                    "palette_name": palette_name,
                    "slides": slides,
                }
            )
        except Exception as exc:
            return f"Error validating DeckDesignPlan: {exc}"

        write_workspace_scaffold(output_dir, plan)
        total = len(plan.slides)
        for idx, s_spec in enumerate(plan.slides, start=1):
            copy_slide_skeleton(output_dir, s_spec, idx, total)

        if progress:
            await progress(f"已完成 {total} 页幻灯片蓝图设计，准备并行生成定制代码...", 35)
        slide_summaries = [
            f"- {s.id} ({s.layout}): {s.title} | key_points={s.key_points}"
            for s in plan.slides
        ]
        return (
            f"Initialized DESIGN_PLAN.json and copied PPTX skeletons for {total} slides:\n"
            + "\n".join(slide_summaries)
            + "\nNext step: call `subagent` with a list of prompts (one per slide) to customize `slides/s01.py` .. "
            f"`slides/s{total:02d}.py` in parallel, then call `build_and_audit_deck`."
        )

    async def _build_and_audit_deck(**_kwargs: Any) -> str:
        if progress:
            await progress("正在编译 deck.pptx 并运行 OOXML 几何与视觉审计...", 80)
        _, report = _compile_and_audit_workspace(output_dir, title=topic or None)
        return json.dumps(report, ensure_ascii=False, indent=2)

    return [
        build_load_skill_tool(loader, only=["pptx"]),
        Tool(
            name="init_deck_plan",
            description=(
                "Initialize DESIGN_PLAN.json, theme_tokens.py, and copy ppt_helpers.py, build_deck.py, and slide_skeleton.py from skills/pptx/templates/. "
                "Ensure 6-10 slides: s01 (hero_cover), s02 (roadmap_grid), content slides with varied layouts, and sNN (summary_takeaways)."
            ),
            args_model=InitDeckPlanArgs,
            handler=_init_deck_plan,
        ),
        build_subagent_tool(
            output_dir,
            system_prompt=slide_subagent_system_prompt,
            extra_tools=[copy_tpl_tool, test_slide_tool],
            description=(
                "Spawn stateless SlideSubagents in parallel (pass `prompts=[...]`, one prompt per slide or a single prompt to fix one slide) "
                "to author bespoke `slides/sXX.py` scripts and verify each with `test_slide`."
            ),
        ),
        Tool(
            name="build_and_audit_deck",
            description="Compile deck.pptx, run the deterministic OOXML geometry audit, render thumbnails/grid.png, and publish slides.html.",
            args_model=BuildAndAuditDeckArgs,
            handler=_build_and_audit_deck,
        ),
        test_slide_tool,
        *build_builtin_tools(output_dir, include_bash=False, include_view_image=True, include_glob_grep=False),
    ]


# ── 外部集成工具（供 chat / resource / path 统一挂载）────────────────────


def build_ppt_subagent_tool(
    *,
    username: str = "anonymous",
    resource_id: str | None = None,
    session_id: str | None = None,
    output_dir: Path | None = None,
    service: Any = None,
) -> Tool:
    """构造供 chat、resource 等父智能体统一调用的 generate_ppt_deck 工具。"""

    async def _run(
        topic: str,
        learning_goal: str,
        source_points: list[str] | None = None,
        narrative_style: str = "concept",
    ) -> dict[str, Any]:
        if service is not None:
            ppt_service = service
        else:
            from app.shared.ppt.agent import PPTService
            ppt_service = PPTService()

        res_key = resource_id or (f"chat_{session_id}" if session_id else uuid4().hex[:12])
        target_dir = output_dir or user_resource_ppt_dir(username, res_key)
        style_val = narrative_style if narrative_style in {"concept", "case_driven", "problem_led", "review"} else "concept"
        req = ResourcePPT(
            username=username,
            learning_need=f"{topic}：{learning_goal}",
            resource_plan={"topic": topic, "learner_goal": learning_goal},
            artifacts=[
                PPTSource(
                    agent_id="upstream",
                    title=topic,
                    summary=learning_goal,
                    materials=list(source_points or [learning_goal])[:12],
                )
            ],
            preferences=PPTPreferences(narrative_style=style_val),  # type: ignore[arg-type]
        )
        artifact = await ppt_service.generate(req, target_dir)
        artifact.html_url = resource_ppt_url(username, res_key) if output_dir is None else static_url(artifact.path)
        if artifact.pptx_path and artifact.pptx_path.is_file():
            artifact.pptx_url = static_url(artifact.pptx_path)
        return {
            "status": "ok",
            "title": artifact.title,
            "slide_count": artifact.slide_count,
            "html_url": artifact.html_url,
            "pptx_url": artifact.pptx_url,
            "pptx_path": str(artifact.pptx_path or ""),
        }

    return Tool(
        name="generate_ppt_deck",
        description=(
            "Invoke the specialized PPTAgent (Plan-and-Execute + python-pptx) to generate "
            "a 16:9 PowerPoint (.pptx) presentation and interactive HTML slide viewer."
        ),
        args_model=GeneratePPTToolArgs,
        handler=_run,
    )


__all__ = [
    "BuildAndAuditDeckArgs",
    "GeneratePPTToolArgs",
    "InitDeckPlanArgs",
    "ProgressCallback",
    "TestSlideArgs",
    "_compile_and_audit_workspace",
    "_test_single_slide_script",
    "build_ppt_planner_tools",
    "build_ppt_subagent_tool",
    "build_test_slide_tool",
]
