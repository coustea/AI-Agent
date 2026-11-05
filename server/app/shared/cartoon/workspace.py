"""HyperFrames 视频工作区初始化与物理技能模板复制器（零内嵌 HTML/CSS 字符串）。

所有 HTML/CSS/JS 骨架均存放在物理技能目录 ``server/skills/hyperframes/templates/`` 下：
- ``root_index.html``: 根组合骨架 (``#root[data-composition-id="main"]``)
- ``scene_skeleton.html``: 子组合契约骨架 (``<template>...</template>`` + ``#__SCENE_ID__-camera`` 镜头容器)
"""

from __future__ import annotations

import html
from pathlib import Path

from app.shared.cartoon.schemas import (
    CaptionCue,
    SceneStoryboardSpec,
    VideoDesignPlan,
)
from app.shared.tools.skills import get_skill_loader


def _split_card_text(raw: str, idx: int) -> tuple[str, str]:
    text = str(raw).strip()
    for sep in ("：", ":", " — ", " - "):
        if sep in text:
            head, tail = text.split(sep, 1)
            if 1 <= len(head.strip()) <= 28 and tail.strip():
                return head.strip(), tail.strip()
    return f"关键节点 {idx:02d}", text


def _build_scene_replacements(
    scene: SceneStoryboardSpec,
    *,
    scene_index: int = 1,
    total_scenes: int = 4,
) -> dict[str, str]:
    """生成用于填充 scene_skeleton.html 占位符的字典。"""
    dur = max(3.0, scene.duration_sec)
    cards = [_split_card_text(c, i + 1) for i, c in enumerate(scene.visual_cards or ["核心概念：深入拆解机制本质"])]
    while len(cards) < 2:
        cards.append(("关键推论", scene.title))

    takeaway = scene.takeaway or scene.subtitle or scene.title
    hold_end = max(1.0, dur - 0.6)
    exit_start = max(1.5, dur - 0.45)

    return {
        "__SCENE_ID__": html.escape(scene.id),
        "__DURATION__": f"{dur:.3f}",
        "__HOLD_END__": f"{hold_end:.2f}",
        "__EXIT_START__": f"{exit_start:.2f}",
        "__SCENE_BADGE__": html.escape(scene.badge),
        "__SCENE_INDEX__": f"{scene_index:02d}",
        "__TOTAL_SCENES__": f"{total_scenes:02d}",
        "__SCENE_TITLE__": html.escape(scene.title),
        "__SCENE_SUBTITLE__": html.escape(scene.subtitle or scene.narration[:64]),
        "__CARD_1_TITLE__": html.escape(cards[0][0]),
        "__CARD_1_BODY__": html.escape(cards[0][1]),
        "__CARD_2_TITLE__": html.escape(cards[1][0]),
        "__CARD_2_BODY__": html.escape(cards[1][1]),
        "__SCENE_TAKEAWAY__": html.escape(takeaway),
    }


def render_root_index_html(plan: VideoDesignPlan, cues: list[CaptionCue]) -> str:
    """从 skills/hyperframes/templates/root_index.html 读取物理模板并注入挂载块。"""
    loader = get_skill_loader()
    skill = loader.skills.get("hyperframes")
    if not skill:
        raise RuntimeError("Skill 'hyperframes' not found in skills directory")

    template_path: Path = skill["dir"] / "templates" / "root_index.html"
    raw_template = template_path.read_text(encoding="utf-8")

    total_dur = max(1.0, plan.total_duration_sec)
    scene_mounts: list[str] = []
    audio_clips: list[str] = []

    for sc in plan.scenes:
        sid = html.escape(sc.id)
        scene_mounts.append(
            f'    <div id="{sid}" data-composition-id="{sid}" '
            f'data-composition-src="compositions/{sid}.html" '
            f'data-start="{sc.start_sec:.3f}" data-duration="{sc.duration_sec:.3f}" '
            f'data-track-index="1" data-width="1920" data-height="1080"></div>'
        )
        if sc.audio_src:
            audio_clips.append(
                f'    <audio id="vo-{sid}" class="clip" src="{html.escape(sc.audio_src)}" '
                f'data-start="{sc.start_sec:.3f}" data-duration="{sc.duration_sec:.3f}" '
                f'data-track-index="0" data-volume="1"></audio>'
            )

    caption_divs: list[str] = []
    for idx, cue in enumerate(cues):
        c_start = cue.start_ms / 1000.0
        c_dur = max(0.25, (cue.end_ms - cue.start_ms) / 1000.0)
        caption_divs.append(
            f'    <div id="cap-{idx}" class="clip hf-caption-pill" '
            f'data-start="{c_start:.3f}" data-duration="{c_dur:.3f}" data-track-index="2">'
            f"{html.escape(cue.text)}</div>"
        )

    replacements = {
        "__TITLE__": html.escape(plan.title),
        "__TOTAL_DURATION__": f"{total_dur:.3f}",
        "<!-- SCENE_MOUNTS -->": "\n".join(scene_mounts),
        "<!-- AUDIO_CLIPS -->": "\n".join(audio_clips),
        "<!-- CAPTION_CLIPS -->": "\n".join(caption_divs),
    }

    content = raw_template
    for key, val in replacements.items():
        content = content.replace(key, val)
    return content


def render_scene_subcomposition_html(
    scene: SceneStoryboardSpec,
    *,
    theme: str = "dark_tech",
    scene_index: int = 1,
    total_scenes: int = 4,
) -> str:
    """从 skills/hyperframes/templates/scene_skeleton.html 读取物理骨架并替换占位符。"""
    _ = theme
    loader = get_skill_loader()
    skill = loader.skills.get("hyperframes")
    if not skill:
        raise RuntimeError("Skill 'hyperframes' not found in skills directory")

    template_path: Path = skill["dir"] / "templates" / "scene_skeleton.html"
    content = template_path.read_text(encoding="utf-8")
    for key, val in _build_scene_replacements(
        scene,
        scene_index=scene_index,
        total_scenes=total_scenes,
    ).items():
        content = content.replace(key, val)
    return content


def copy_scene_skeleton(
    output_dir: Path,
    scene: SceneStoryboardSpec,
    *,
    scene_index: int = 1,
    total_scenes: int = 4,
) -> Path:
    """将渲染后的 scene_skeleton.html 写入 compositions/sXX.html。"""
    dest = output_dir / "compositions" / f"{scene.id}.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        render_scene_subcomposition_html(
            scene,
            scene_index=scene_index,
            total_scenes=total_scenes,
        ),
        encoding="utf-8",
    )
    return dest


__all__ = [
    "copy_scene_skeleton",
    "render_root_index_html",
    "render_scene_subcomposition_html",
]
