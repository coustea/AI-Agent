"""Cartoon 视频生成工具层 (app.shared.cartoon.tool) —— 基于无状态流与通用 subagent 工具。

包含：
1. 外部工具：供 chat、resource、path 等模块统一调用的 ``generate_teaching_video`` (``build_cartoon_subagent_tool``)
2. 导演主智能体工具集 (``build_cartoon_planner_tools``)：
   - ``init_storyboard_and_tts``：写入 ``STORYBOARD.json``、合成 TTS 配音并复制 ``compositions/sXX.html`` 骨架（无内存 state 闭包）
   - ``subagent``：复用 ``app.shared.tools.build_subagent_tool`` 派生无状态子智能体并发编写 ``compositions/sXX.html``
   - ``check_and_render_video``：执行 HyperFrames 契约校验、渲染 ``video.mp4`` 并落盘 ``audit.json``
3. 单场景确定性校验工具：``verify_scene(scene_id)``
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Coroutine
from uuid import uuid4

from pydantic import BaseModel, Field

from app.config import static_url, user_resource_cartoon_dir
from app.shared.cartoon.renderer import CartoonMedia, QualityGateError
from app.shared.cartoon.schemas import (
    CartoonBrief,
    CartoonGenerationConfig,
    SceneStoryboardSpec,
    VideoDesignPlan,
)
from app.shared.cartoon.tts import synthesize_plan_narration
from app.shared.cartoon.validator import validate_scene_composition_html
from app.shared.cartoon.workspace import copy_scene_skeleton, render_root_index_html
from app.shared.tools import (
    SkillLoader,
    Tool,
    build_copy_skill_template_tool,
    build_load_skill_tool,
    build_subagent_tool,
    get_skill_loader,
)

ProgressCallback = Callable[[str, int], Coroutine[Any, Any, None]]


# ── 工具参数模型 (Pydantic Schema) ──────────────────────────────────────────


class GenerateVideoToolArgs(BaseModel):
    """生成 HyperFrames 动画讲解视频的外部工具参数。"""

    topic: str = Field(min_length=2, description="视频讲解主题")
    learning_goal: str = Field(min_length=2, description="本视频要讲透的核心问题或目标")
    source_materials: list[str] = Field(
        default_factory=list,
        description="可选：上游教程摘要或核心知识点素材",
    )
    voice: str = Field(
        default="teacher",
        description="配音音色：teacher (女声讲师) | coach (男声教练)",
    )


class InitHyperframesPlanArgs(BaseModel):
    """初始化分镜蓝图、TTS 配音与脚手架的参数。"""

    title: str = Field(description="教学视频总标题")
    theme: str = Field(
        default="dark_tech",
        description="视觉风格主题：dark_tech | editorial_light | emerald_studio",
    )
    scenes: list[SceneStoryboardSpec] = Field(
        description="3 到 5 个按序排列的场景规格清单，每个场景必须指定 id, visual_style, title, narration, visual_cards",
    )


class CheckAndRenderVideoArgs(BaseModel):
    """验证子场景、渲染 video.mp4 并运行 ffprobe 音视频流校验。"""


class VerifySceneArgs(BaseModel):
    """验证单个 compositions/sXX.html 的参数。"""

    scene_id: str = Field(description="要验证的场景 ID，例如 's01'")


# ── 工具工厂函数（无状态流）───────────────────────────────────────────────


def build_verify_scene_tool(output_dir: Path) -> Tool:
    """构造无状态单场景契约校验工具 verify_scene(scene_id)。"""

    async def _handler(scene_id: str) -> str:
        clean_id = scene_id.strip().removesuffix(".html").removeprefix("compositions/")
        _, msg = validate_scene_composition_html(output_dir, clean_id)
        return msg

    return Tool(
        name="verify_scene",
        description="Validate compositions/<scene_id>.html against the HyperFrames sub-composition contract (<template>, data-composition-id, .clip, window.__timelines).",
        args_model=VerifySceneArgs,
        handler=_handler,
    )


def build_cartoon_planner_tools(
    output_dir: Path,
    *,
    skill_loader: SkillLoader | None = None,
    brief: CartoonBrief,
    media: CartoonMedia,
    progress: ProgressCallback | None = None,
) -> list[Tool]:
    """构造供 HyperFrames 教学视频导演主智能体调用的无状态工具集（直接通过 output_dir 文件系统流转）。"""
    loader = skill_loader or get_skill_loader()
    format_ref = loader.get_content("hyperframes", "format.md")

    scene_subagent_system_prompt = (
        "你是负责为单个 HyperFrames 动画场景创作定制视觉与镜头动效的无状态子智能体 (SceneSubagent)。\n"
        "工作区 `compositions/sXX.html` 中已准备好契约骨架。请用 `read` 查看当前骨架，"
        "再用 `edit` 或 `write` 将画布升级为贴合该场景教学主题的专属视觉舞台：\n"
        "- `architecture_flow`：绘制带 SVG 箭头/路径动画的多阶段架构拓扑图，配合镜头平移聚焦。\n"
        "- `code_walkthrough`：构建左侧深色代码/公式推演终端 + 右侧分步状态高亮卡片。\n"
        "- `comparison_split`：构建双栏对比矩阵或动态指标条。\n"
        "- `concept_hero` / `summary_recap`：构建中心视觉锚点 + 关键推论卡片与镜头缓慢推进动效。\n\n"
        "必须严格遵守 HyperFrames 子场景硬性契约：\n"
        "1. 整个文件必须包裹在 `<template>...</template>` 内。\n"
        '2. 根元素必须是 `<div id="root" data-composition-id="sXX" data-start="0" data-duration="..." data-width="1920" data-height="1080">`。\n'
        '3. 动效脚本必须使用 `const tl = gsap.timeline({ paused: true });` 并注册 `window.__timelines["sXX"] = tl;`，一律使用 `gsap.fromTo()`，严禁 `gsap.from()` 和 `tl.play()`。\n'
        "4. 编写完成后必须调用 `verify_scene(scene_id=...)` 验证返回 PASS。\n\n"
        f"{format_ref[:4500]}"
    )

    verify_scene_tool = build_verify_scene_tool(output_dir)
    copy_tpl_tool = build_copy_skill_template_tool(output_dir, loader, only=["hyperframes"])

    async def _init_storyboard_and_tts(
        title: str,
        scenes: list[dict[str, Any]],
        theme: str = "dark_tech",
    ) -> str:
        try:
            theme_val = theme if theme in {"dark_tech", "editorial_light", "emerald_studio"} else "dark_tech"
            raw_plan = VideoDesignPlan.model_validate(
                {
                    "title": title or brief.learning_need[:48],
                    "theme": theme_val,
                    "scenes": scenes,
                }
            )
        except Exception as exc:
            return f"Error validating VideoDesignPlan: {exc}"

        if progress:
            await progress(f"正在为 {len(raw_plan.scenes)} 个场景合成 TTS 配音并测定精确时长...", 30)

        timed_plan, cues = await synthesize_plan_narration(
            raw_plan,
            output_dir,
            voice=brief.configuration.voice,
            pace=brief.configuration.pace,
        )

        plan_json = json.dumps(timed_plan.model_dump(mode="json"), ensure_ascii=False, indent=2)
        (output_dir / "lesson.json").write_text(plan_json, encoding="utf-8")
        (output_dir / "STORYBOARD.json").write_text(plan_json, encoding="utf-8")

        root_html = render_root_index_html(timed_plan, cues)
        (output_dir / "index.html").write_text(root_html, encoding="utf-8")

        total = len(timed_plan.scenes)
        for idx, sc in enumerate(timed_plan.scenes, start=1):
            copy_scene_skeleton(
                output_dir,
                sc,
                scene_index=idx,
                total_scenes=total,
            )

        if progress:
            await progress(f"完成 {total} 个场景骨架与 TTS 合成，准备派生无状态子智能体...", 50)
        scene_summaries = [
            f"- {sc.id} ({sc.visual_style}, {sc.duration_sec:.2f}s): {sc.title} | cards={sc.visual_cards}"
            for sc in timed_plan.scenes
        ]
        return (
            f"Synthesized TTS and copied HyperFrames skeletons for {total} scenes "
            f"(total duration: {timed_plan.total_duration_sec:.2f}s):\n"
            + "\n".join(scene_summaries)
            + "\nNext step: call `subagent` with a list of prompts (one per scene) to customize "
            "`compositions/s01.html` .. `compositions/sNN.html` in parallel, then call `check_and_render_video`."
        )

    async def _check_and_render_video(**_kwargs: Any) -> str:
        storyboard_file = output_dir / "STORYBOARD.json"
        if not storyboard_file.is_file():
            return "Error: Call `init_storyboard_and_tts` first."

        plan = VideoDesignPlan.model_validate_json(storyboard_file.read_text(encoding="utf-8"))
        if progress:
            await progress("正在运行 HyperFrames CLI 渲染 1080p MP4 并执行 ffprobe 校验...", 85)
        try:
            report = await media.check(output_dir)
            video_path = await media.render(output_dir, "video.mp4")
            probe = await media.probe(
                video_path,
                expected_duration_ms=plan.total_duration_ms,
            )
            audit_payload = {
                "ok": True,
                "report": report.model_dump(mode="json"),
                "probe": probe.model_dump(mode="json"),
            }
            (output_dir / "audit.json").write_text(
                json.dumps(audit_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return json.dumps(audit_payload, ensure_ascii=False, indent=2)
        except QualityGateError as exc:
            return "HyperFrames Quality Gate Failed:\n- " + "\n- ".join(exc.problems)
        except Exception as exc:
            return f"HyperFrames Render/Probe Error: {type(exc).__name__}: {exc}"

    return [
        build_load_skill_tool(loader, only=["hyperframes", "hyperframes-cli"]),
        Tool(
            name="init_storyboard_and_tts",
            description=(
                "Initialize the 3-5 scene storyboard, synthesize TTS voiceovers for each scene, "
                "measure exact audio durations, write captions.vtt, and copy root_index.html and scene_skeleton.html from skills/hyperframes/templates/."
            ),
            args_model=InitHyperframesPlanArgs,
            handler=_init_storyboard_and_tts,
        ),
        build_subagent_tool(
            output_dir,
            system_prompt=scene_subagent_system_prompt,
            extra_tools=[copy_tpl_tool, verify_scene_tool],
            description=(
                "Spawn stateless SceneSubagents in parallel (pass `prompts=[...]`, one prompt per scene or a single prompt to fix one scene) "
                "to customize `compositions/sXX.html` and verify each with `verify_scene`."
            ),
        ),
        Tool(
            name="check_and_render_video",
            description="Validate all HyperFrames compositions, render video.mp4, and verify streams with ffprobe.",
            args_model=CheckAndRenderVideoArgs,
            handler=_check_and_render_video,
        ),
        verify_scene_tool,
    ]


# ── 外部集成工具（供 chat / resource / path 统一挂载）────────────────────


def build_cartoon_subagent_tool(
    *,
    username: str = "anonymous",
    resource_id: str | None = None,
    session_id: str | None = None,
    output_dir: Path | None = None,
    pipeline: Any = None,
) -> Tool:
    """构造供 chat、resource 等父智能体统一调用的 generate_teaching_video 工具。"""

    async def _run(
        topic: str,
        learning_goal: str,
        source_materials: list[str] | None = None,
        voice: str = "teacher",
    ) -> dict[str, Any]:
        if pipeline is not None:
            cartoon_agent = pipeline
        else:
            from app.shared.cartoon.agent import CartoonAgent
            cartoon_agent = CartoonAgent()

        res_key = resource_id or (f"chat_{session_id}" if session_id else uuid4().hex[:12])
        target_dir = output_dir or user_resource_cartoon_dir(username, res_key)
        voice_val = "coach" if voice == "coach" else "teacher"
        brief = CartoonBrief(
            learning_need=f"{topic}：{learning_goal}",
            instruction_context={"topic": topic, "learning_goal": learning_goal},
            source_materials=list(source_materials or [learning_goal])[:8],
            configuration=CartoonGenerationConfig(voice=voice_val),  # type: ignore[arg-type]
        )
        artifact = await cartoon_agent.generate(brief, target_dir)
        return {
            "status": "ok",
            "title": artifact.title,
            "scene_count": artifact.scene_count,
            "duration_seconds": round(artifact.duration_ms / 1000.0, 2),
            "video_url": static_url(artifact.video_path),
            "preview_url": static_url(artifact.html_path),
            "captions_url": static_url(artifact.caption_path),
        }

    return Tool(
        name="generate_teaching_video",
        description=(
            "Invoke the specialized CartoonAgent (Plan-and-Execute + HyperFrames + TTS) "
            "to generate a 1920x1080 narrated MP4 teaching video with synchronized captions."
        ),
        args_model=GenerateVideoToolArgs,
        handler=_run,
    )


__all__ = [
    "CheckAndRenderVideoArgs",
    "GenerateVideoToolArgs",
    "InitHyperframesPlanArgs",
    "ProgressCallback",
    "VerifySceneArgs",
    "build_cartoon_planner_tools",
    "build_cartoon_subagent_tool",
    "build_verify_scene_tool",
]
