"""SkillLoader、load_skill 与 copy_skill_template 工具。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.shared.tools.registry import Tool

DEFAULT_SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"


def _read_description(path: Path) -> str:
    """只读取 SKILL.md 头部 frontmatter 的 description，不加载技能正文。"""
    try:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return ""
        parts = text.split("---", 2)
        if len(parts) < 3:
            return ""
        meta = yaml.safe_load(parts[1]) or {}
        if isinstance(meta, dict):
            desc = meta.get("description", "")
            if isinstance(desc, str):
                return " ".join(desc.split()).strip()
    except Exception:
        pass
    return ""


def _strip_frontmatter(text: str) -> str:
    """剥离 SKILL.md 顶部的 YAML frontmatter，返回正文。"""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text.strip()


class SkillLoader:
    """技能目录索引：扫描时只记描述，正文在 load_skill 时按需读取。"""

    def __init__(self, skills_dir: Path | None = None) -> None:
        """扫描技能目录，建立 技能名 → frontmatter 描述 的索引。"""
        self.skills_dir = (skills_dir or DEFAULT_SKILLS_DIR).resolve()
        self.skills: dict[str, str] = {
            path.parent.name: _read_description(path)
            for path in sorted(self.skills_dir.glob("*/SKILL.md"))
        }

    def get_descriptions(self, only: Sequence[str] | None = None) -> str:
        """生成供 System Prompt 使用的已启用技能目录描述。"""
        return "\n".join(
            f"  - {name}: {description}"
            for name, description in self.skills.items()
            if only is None or name in only
        )

    def get_content(self, name: str, reference: str = "") -> str:
        """读取指定技能的说明正文，或该技能目录内的参考文档。"""
        if name not in self.skills:
            return f"Error: Unknown skill '{name}'"
        root = (self.skills_dir / name).resolve()
        ref_clean = (reference or "").strip().lstrip("/")
        if ref_clean:
            path = (root / ref_clean).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                return f"Error: Unknown skill file '{reference}'"
            return path.read_text(encoding="utf-8")
        skill_file = root / "SKILL.md"
        if not skill_file.is_file():
            return f"Error: Missing SKILL.md for '{name}'"
        body = _strip_frontmatter(skill_file.read_text(encoding="utf-8"))
        return (
            f'<skill name="{name}">\n'
            f"Skill root: {root}\n"
            'Paths are relative to this root. Read files with load_skill(reference="relative/path"); '
            "execute scripts via bash using their absolute paths.\n"
            f"{body}\n</skill>"
        )


_LOADER: SkillLoader | None = None


def get_skill_loader(*, refresh: bool = False) -> SkillLoader:
    """获取全局单例技能加载器。"""
    global _LOADER
    if _LOADER is None or refresh:
        _LOADER = SkillLoader()
    return _LOADER


class LoadSkillArgs(BaseModel):
    """读取技能说明或技能目录内的参考文件。"""

    name: str = Field(min_length=1)
    reference: str = Field(
        default="",
        description="Optional file path relative to the skill root, e.g. references/format.md",
    )


def build_load_skill_tool(loader: SkillLoader | None = None, *, only: Sequence[str] | None = None) -> Tool:
    """构造按需读取技能说明的 load_skill 工具；``only`` 限定该 Agent 可用的技能。"""
    skill_loader = loader or get_skill_loader()

    async def load(name: str, reference: str = "") -> dict[str, Any]:
        """按需读取技能完整说明或该技能目录内的专项参考文档。"""
        if only is not None and name not in only:
            return {"status": "failed", "text": f"Skill not enabled: {name}"}
        text = skill_loader.get_content(name, reference)
        return {"status": "failed" if text.startswith("Error:") else "ok", "text": text}

    return Tool(
        name="load_skill",
        description="读取技能说明或技能目录内的参考文件。",
        args_model=LoadSkillArgs,
        handler=load,
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
        description="可选：复制时顺带替换的占位符字典",
    )


def build_copy_skill_template_tool(
    workdir: Path,
    loader: SkillLoader | None = None,
    *,
    only: Sequence[str] | None = None,
) -> Tool:
    """构造将技能包物理骨架文件复制到工作区的 copy_skill_template 工具。"""
    skill_loader = loader or get_skill_loader()

    async def _copy_template(
        skill: str,
        template: str,
        dest_path: str,
        replacements: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """将技能模板安全复制到工作区并替换占位符。"""
        root = skill_loader.skills_dir / skill
        src = (root / "templates" / template).resolve()
        if not src.is_file():
            return {"status": "failed", "error": f"Template not found: {template}"}
        dest = (workdir / dest_path).resolve()
        if not dest.is_relative_to(workdir.resolve()):
            raise PermissionError(f"目标路径越界: {dest_path}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = src.read_text(encoding="utf-8")
        for k, v in (replacements or {}).items():
            content = content.replace(k, str(v))
        dest.write_text(content, encoding="utf-8")
        return {"status": "ok", "path": str(dest)}

    return Tool(
        name="copy_skill_template",
        description="从技能包复制物理骨架模板到当前工作目录。",
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
