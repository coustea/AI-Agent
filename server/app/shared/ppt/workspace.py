"""PPT 工作区初始化与物理技能模板复制器（零内嵌 Python/HTML 字符串）。

所有 Python 与 HTML 脚手架均存放在物理技能目录 ``server/skills/pptx/templates/`` 下：
- ``ppt_helpers.py``: 原子级 ``python-pptx`` 造型与排版原语库
- ``build_deck.py``: ``slides/s01.py .. slides/sNN.py`` 组装编译器
- ``slide_skeleton.py``: 单页 ``build_slide(prs, theme)`` 最小契约骨架
- ``viewer.html``: 交互式幻灯片预览器与 ``.pptx`` 下载页
"""

from __future__ import annotations

import json
from pathlib import Path

from app.shared.ppt.schemas import DeckDesignPlan, SlideSpec
from app.shared.tools.skills import get_skill_loader


def _escape_py_str(value: str) -> str:
    """安全转义用于替换 slide_skeleton.py 占位符的单行字符串。"""
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )


def _build_slide_replacements(spec: SlideSpec, index: int, total: int) -> dict[str, str]:
    """构造用于替换 slide_skeleton.py 占位符的键值字典。"""
    takeaway_text = spec.takeaway or spec.core_claim
    notes_text = spec.speaker_notes or f"{spec.title}：{spec.core_claim}"
    claim_body = "；".join(spec.key_points[:3]) if spec.key_points else spec.core_claim
    return {
        "__SLIDE_BADGE__": _escape_py_str(spec.chapter_badge),
        "__SLIDE_TITLE__": _escape_py_str(spec.title),
        "__SLIDE_SUBTITLE__": _escape_py_str(spec.subtitle or spec.core_claim),
        "__SLIDE_CLAIM__": _escape_py_str(claim_body),
        "__SLIDE_TAKEAWAY__": _escape_py_str(takeaway_text),
        "__SLIDE_NOTES__": _escape_py_str(notes_text),
        "__SLIDE_INDEX__": str(int(index)),
        "__TOTAL_SLIDES__": str(int(total)),
    }


def write_workspace_scaffold(output_dir: Path, plan: DeckDesignPlan) -> None:
    """在 output_dir 下写入 DESIGN_PLAN.json、theme_tokens.py，并复制 ppt_helpers.py 与 build_deck.py。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "slides").mkdir(parents=True, exist_ok=True)

    (output_dir / "DESIGN_PLAN.json").write_text(
        json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    theme_dict = plan.theme.model_dump(mode="json")
    (output_dir / "theme_tokens.py").write_text(
        f"# Auto-generated 60-30-10 Theme Tokens\nTHEME = {json.dumps(theme_dict, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )

    loader = get_skill_loader()
    loader.copy_template("pptx", "ppt_helpers.py", output_dir / "ppt_helpers.py")
    loader.copy_template("pptx", "build_deck.py", output_dir / "build_deck.py")


def generate_slide_python_code(spec: SlideSpec, index: int, total: int) -> str:
    """从 skills/pptx/templates/slide_skeleton.py 读取物理模板并替换占位符。"""
    loader = get_skill_loader()
    skill = loader.skills.get("pptx")
    if not skill:
        raise RuntimeError("Skill 'pptx' not found in skills directory")

    template_path: Path = skill["dir"] / "templates" / "slide_skeleton.py"
    content = template_path.read_text(encoding="utf-8")
    for key, val in _build_slide_replacements(spec, index, total).items():
        content = content.replace(key, val)
    return content


def copy_slide_skeleton(
    output_dir: Path,
    spec: SlideSpec,
    index: int,
    total: int,
) -> Path:
    """将渲染后的 slide_skeleton.py 写入 slides/sXX.py。"""
    dest = output_dir / "slides" / f"{spec.id}.py"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(generate_slide_python_code(spec, index, total), encoding="utf-8")
    return dest


__all__ = [
    "copy_slide_skeleton",
    "generate_slide_python_code",
    "write_workspace_scaffold",
]
