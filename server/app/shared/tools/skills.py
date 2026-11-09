"""技能加载器与 load_skill 工具 —— 基于 learn-claude-code s05 技能按需加载。"""

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
        """扫描技能目录，建立 技能名 -> frontmatter 描述 的索引。"""
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

    name: str = Field(min_length=1, description="技能名称")
    reference: str = Field(
        default="",
        description="相对于技能根目录的文件路径，例如 references/format.md",
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


__all__ = [
    "DEFAULT_SKILLS_DIR",
    "LoadSkillArgs",
    "SkillLoader",
    "build_load_skill_tool",
    "get_skill_loader",
]
