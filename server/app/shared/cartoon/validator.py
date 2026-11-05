"""HyperFrames 子场景 HTML 静态契约校验器。

严格遵循 ``server/skills/hyperframes/references/format.md`` 官方契约：
1. 每个子场景 ``compositions/sXX.html`` 必须以 ``<template>...</template>`` 包裹全部 ``<style>``、``#root[data-composition-id="sXX"]`` 与 ``<script>``。
2. 宿主 ``id``、子场景 ``data-composition-id`` 与 ``window.__timelines["sXX"]`` 三者完全一致。
3. 动画一律使用 ``gsap.fromTo()`` 且时间轴 ``gsap.timeline({ paused: true })``，严禁 ``gsap.from()`` 与 ``tl.play()``。
"""

from __future__ import annotations

from pathlib import Path
import re


def validate_scene_composition_html(output_dir: Path, scene_id: str) -> tuple[bool, str]:
    """根据 HyperFrames 官方 format.md 规则校验单个子场景 compositions/sXX.html。"""
    comp_file = output_dir / "compositions" / f"{scene_id}.html"
    if not comp_file.is_file():
        return False, f"File not found: compositions/{scene_id}.html"

    raw = comp_file.read_text(encoding="utf-8", errors="replace").strip()
    problems: list[str] = []

    if not raw.startswith("<template>") or not raw.endswith("</template>"):
        problems.append(
            "Sub-composition MUST wrap all <style>, <div id='root'>, and <script> inside <template>...</template>."
        )
    if f'data-composition-id="{scene_id}"' not in raw and f"data-composition-id='{scene_id}'" not in raw:
        problems.append(
            f'Root element inside compositions/{scene_id}.html must have data-composition-id="{scene_id}".'
        )
    if f'__timelines["{scene_id}"]' not in raw and f"__timelines['{scene_id}']" not in raw:
        problems.append(
            f'Script must register window.__timelines["{scene_id}"] = tl; matching "{scene_id}".'
        )
    if "paused: true" not in raw and "paused:true" not in raw:
        problems.append("GSAP timeline must be created with gsap.timeline({ paused: true }).")
    if re.search(r"\btl\.play\s*\(", raw):
        problems.append("Never call tl.play() inside a HyperFrames composition.")
    if re.search(r"\bgsap\.from\s*\(", raw):
        problems.append("Use gsap.fromTo() instead of gsap.from() for deterministic frame seeking.")
    if 'class="clip' not in raw and "class='clip" not in raw:
        problems.append("Sub-composition must contain at least one element with class='clip' and data-start/data-duration.")

    if problems:
        return False, f"HyperFrames Contract Errors in compositions/{scene_id}.html:\n- " + "\n- ".join(problems)
    return True, f"PASS: compositions/{scene_id}.html satisfies all HyperFrames sub-composition rules."


__all__ = ["validate_scene_composition_html"]
