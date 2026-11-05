"""SkillLoader、load_skill 与 copy_skill_template 工具 — 基于 learn-claude-code s07_skill_loading。

每个本地 Skill (`server/skills/<name>/`) 包含：
- ``SKILL.md``: 核心规范与工作流说明
- ``references/``: 详细参考文档（如 ``format.md``, ``motion.md``, ``python_pptx_cookbook.md``）
- ``templates/``: 物理契约骨架文件（如 ``scene_skeleton.html``, ``slide_skeleton.py``, ``ppt_helpers.py``）
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import re
import shutil
from typing import Any

from pydantic import BaseModel, Field

from app.shared.tools.registry import Tool
from app.shared.tools.sandbox import resolve

DEFAULT_SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"


class SkillLoader:
    """扫描并管理 server/skills/ 目录下的技能说明、参考手册与物理模板骨架。"""

    def __init__(self, skills_dir: Path | None = None) -> None:
        self.skills_dir = (skills_dir or DEFAULT_SKILLS_DIR).resolve()
        self.skills: dict[str, dict[str, Any]] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not self.skills_dir.exists():
            return
        for skill_md in sorted(self.skills_dir.rglob("SKILL.md")):
            if skill_md.parent.parent != self.skills_dir:
                continue
            text = skill_md.read_text(encoding="utf-8")
            meta, body = self._parse_frontmatter(text)
            name = meta.get("name", skill_md.parent.name).strip()

            refs_dir = skill_md.parent / "references"
            references: list[str] = []
            if refs_dir.is_dir():
                for ref_path in sorted(refs_dir.rglob("*.md")):
                    references.append(ref_path.relative_to(refs_dir).as_posix())

            tpl_dir = skill_md.parent / "templates"
            templates: list[str] = []
            if tpl_dir.is_dir():
                for tpl_path in sorted(tpl_dir.rglob("*")):
                    if tpl_path.is_file() and not tpl_path.name.startswith("."):
                        templates.append(tpl_path.relative_to(tpl_dir).as_posix())

            self.skills[name] = {
                "meta": meta,
                "body": body,
                "dir": skill_md.parent,
                "path": skill_md,
                "references": references,
                "templates": templates,
            }

    @staticmethod
    def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text
        meta: dict[str, str] = {}
        for line in match.group(1).strip().splitlines():
            if ":" in line and not line.lstrip().startswith(("#", "-")):
                key, val = line.split(":", 1)
                cleaned = val.strip().strip("\"'")
                if cleaned:
                    meta[key.strip()] = cleaned
        return meta, match.group(2).strip()

    def get_descriptions(self, only: Sequence[str] | None = None) -> str:
        """Layer 1: 生成放入 system prompt 的简短技能目录（含可用 references 与 templates）。"""
        if not self.skills:
            return "(no skills available)"
        allowed = set(only) if only is not None else None
        lines: list[str] = []
        for name, skill in self.skills.items():
            if allowed is not None and name not in allowed:
                continue
            desc = skill["meta"].get("description", "No description")
            refs = skill.get("references") or []
            tpls = skill.get("templates") or []
            line = f"  - {name}: {desc}"
            if refs:
                line += f"\n    references: {', '.join(refs)}"
            if tpls:
                line += f"\n    templates: {', '.join(tpls)}"
            lines.append(line)
        return "\n".join(lines) if lines else "(no matching skills)"

    def get_content(self, name: str, reference: str = "") -> str:
        """Layer 2: 按需返回完整 SKILL.md 或指定 reference 文档内容。"""
        skill = self.skills.get(name)
        if not skill:
            available = ", ".join(sorted(self.skills.keys()))
            return f"Error: Unknown skill '{name}'. Available: {available}"

        ref_clean = (reference or "").strip().lstrip("/")
        if ref_clean.startswith("references/"):
            ref_clean = ref_clean.removeprefix("references/")

        if ref_clean:
            refs_dir: Path = skill["dir"] / "references"
            target = (refs_dir / ref_clean).resolve()
            if not target.is_relative_to(refs_dir.resolve()) or not target.is_file():
                avail_refs = ", ".join(skill.get("references") or []) or "none"
                return (
                    f"Error: Unknown reference '{reference}' for skill '{name}'. "
                    f"Available references: {avail_refs}"
                )
            body = target.read_text(encoding="utf-8")
            return f'<skill name="{name}" reference="{ref_clean}">\n{body}\n</skill>'

        refs = skill.get("references") or []
        tpls = skill.get("templates") or []
        footer_parts: list[str] = []
        if refs:
            footer_parts.append(
                f"Available reference files via `load_skill(name=\"{name}\", reference=\"...\")`: {', '.join(refs)}"
            )
        if tpls:
            footer_parts.append(
                f"Available template files via `copy_skill_template(skill=\"{name}\", template=\"...\", dest_path=\"...\")`: {', '.join(tpls)}"
            )
        footer = ("\n\n---\n" + "\n".join(footer_parts)) if footer_parts else ""
        return f'<skill name="{name}">\n{skill["body"]}{footer}\n</skill>'

    def resolve_template_path(self, skill_name: str, template_rel: str) -> Path:
        """定位技能包内 templates/<template_rel> 的真实物理路径。"""
        skill = self.skills.get(skill_name)
        if not skill:
            raise ValueError(f"Unknown skill '{skill_name}'")
        tpl_dir = (skill["dir"] / "templates").resolve()
        clean_rel = template_rel.strip().lstrip("/").removeprefix("templates/")
        target = (tpl_dir / clean_rel).resolve()
        if not target.is_relative_to(tpl_dir) or not target.is_file():
            avail = ", ".join(skill.get("templates") or []) or "none"
            raise ValueError(
                f"Template '{template_rel}' not found in skill '{skill_name}'. Available templates: {avail}"
            )
        return target

    def copy_template(
        self,
        skill_name: str,
        template_rel: str,
        dest: Path,
        replacements: Mapping[str, str] | None = None,
    ) -> Path:
        """将技能包中的物理模板文件复制到目标路径 dest，并执行可选占位符替换。"""
        src = self.resolve_template_path(skill_name, template_rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if replacements:
            content = src.read_text(encoding="utf-8")
            for k, v in replacements.items():
                content = content.replace(str(k), str(v))
            dest.write_text(content, encoding="utf-8")
        else:
            shutil.copy2(src, dest)
        return dest

    def copy_template_to(
        self,
        skill_name: str,
        template_rel: str,
        workdir: Path,
        dest_rel: str,
        replacements: Mapping[str, str] | None = None,
    ) -> Path:
        """将技能包中的物理模板文件复制到用户工作目录 dest_rel，并执行可选占位符替换。"""
        dest = resolve(workdir, dest_rel)
        return self.copy_template(
            skill_name,
            template_rel,
            dest,
            replacements=replacements,
        )


_GLOBAL_LOADER: SkillLoader | None = None


def get_skill_loader(*, refresh: bool = False) -> SkillLoader:
    """获取全局 SkillLoader 实例。"""
    global _GLOBAL_LOADER
    if _GLOBAL_LOADER is None or refresh:
        _GLOBAL_LOADER = SkillLoader()
    return _GLOBAL_LOADER


class LoadSkillArgs(BaseModel):
    """按需加载本地技能说明或参考手册。"""

    name: str = Field(min_length=1, description="技能名称，如 'hyperframes'、'pptx'")
    reference: str = Field(
        default="",
        description="可选：references/ 下的参考文档名，如 'format.md'、'motion.md'、'python_pptx_cookbook.md'",
    )


def build_load_skill_tool(
    loader: SkillLoader | None = None,
    *,
    only: Sequence[str] | None = None,
) -> Tool:
    """构造供 Agent 按需加载技能文档的 load_skill 工具。"""
    skill_loader = loader or get_skill_loader()
    allowed = set(only) if only is not None else None

    async def _load_skill(name: str, reference: str = "") -> dict[str, Any]:
        if allowed is not None and name not in allowed:
            return {
                "text": f"Error: Skill '{name}' is not enabled. Allowed: {', '.join(sorted(allowed))}",
                "status": "failed",
            }
        text = skill_loader.get_content(name, reference)
        status = "failed" if text.startswith("Error:") else "ok"
        return {"text": text, "status": status}

    return Tool(
        name="load_skill",
        description=(
            "按需加载指定技能的完整 SKILL.md 说明或 references/ 下的专项参考文档"
            "（如 motion.md、format.md、python_pptx_cookbook.md）。"
        ),
        args_model=LoadSkillArgs,
        handler=_load_skill,
    )


class CopySkillTemplateArgs(BaseModel):
    """从技能包复制物理骨架模板到当前工作目录。"""

    skill: str = Field(min_length=1, description="技能名称，如 'hyperframes' 或 'pptx'")
    template: str = Field(
        min_length=1,
        description="技能 templates/ 下的模板文件名，如 'scene_skeleton.html' 或 'slide_skeleton.py'",
    )
    dest_path: str = Field(
        min_length=1,
        description="复制到当前工作目录的相对路径，如 'compositions/s01.html' 或 'slides/s01.py'",
    )
    replacements: dict[str, str] = Field(
        default_factory=dict,
        description="可选：复制时顺带替换的占位符字典，如 {'__SCENE_ID__': 's01', '__DURATION__': '6.2'}",
    )


def build_copy_skill_template_tool(
    workdir: Path,
    loader: SkillLoader | None = None,
    *,
    only: Sequence[str] | None = None,
) -> Tool:
    """构造将技能包物理骨架文件复制到工作区的 copy_skill_template 工具。"""
    skill_loader = loader or get_skill_loader()
    allowed = set(only) if only is not None else None
    root = workdir.resolve()

    async def _copy_template(
        skill: str,
        template: str,
        dest_path: str,
        replacements: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if allowed is not None and skill not in allowed:
            return {
                "text": f"Error: Skill '{skill}' is not enabled. Allowed: {', '.join(sorted(allowed))}",
                "status": "failed",
            }
        try:
            dest = skill_loader.copy_template_to(
                skill,
                template,
                root,
                dest_path,
                replacements=replacements,
            )
            content = dest.read_text(encoding="utf-8", errors="replace")
            numbered = "\n".join(f"{i + 1:>4}\t{line}" for i, line in enumerate(content.splitlines()))
            return {
                "text": (
                    f"已将模板 `{skill}/templates/{template}` 复制到 `{dest_path}`。\n"
                    f"当前文件内容（可直接用 `edit` 或 `write` 自由定制图形与动画）：\n{numbered}"
                ),
                "status": "ok",
                "path": dest_path,
            }
        except Exception as exc:
            return {"text": f"复制模板失败: {exc}", "status": "failed"}

    return Tool(
        name="copy_skill_template",
        description=(
            "将技能包 `templates/` 下的物理最小契约骨架文件复制到当前工作目录，"
            "并返回带行号的文件内容，随后可用 `edit` 或 `write` 自由编写具体图形与动画代码。"
        ),
        args_model=CopySkillTemplateArgs,
        handler=_copy_template,
    )


__all__ = [
    "CopySkillTemplateArgs",
    "DEFAULT_SKILLS_DIR",
    "LoadSkillArgs",
    "SkillLoader",
    "build_copy_skill_template_tool",
    "build_load_skill_tool",
    "get_skill_loader",
]
