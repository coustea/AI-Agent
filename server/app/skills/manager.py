"""
技能管理器（SkillManager）。

从 PluginManager 瘦身而来，只保留技能加载能力：
  - 扫描 SKILL.md 文件，解析 frontmatter
  - 为每个技能生成 load_skill_xxx 工具
  - 按 skill_names 过滤返回指定技能

工具注册功能已移至 app/tools/registry.py。
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

import yaml
from langchain.tools import tool
from langchain_core.tools import BaseTool

from app.infra.logging import get_logger

logger = get_logger(__name__)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# 全局默认技能目录
DEFAULT_SKILLS_DIR = Path(__file__).resolve().parent


class SkillManager:
    """技能加载与管理。

    扫描 skills_path 下的 SKILL.md 文件，解析 frontmatter 元数据，
    并为每个技能生成可供 LLM 调用的 load_skill_xxx 工具。
    """

    def __init__(
        self,
        skills_path: Path | list[Path] | tuple[Path, ...] | None = None,
        **_: Any,
    ) -> None:
        if skills_path is None:
            skills_path = DEFAULT_SKILLS_DIR
        self._skills_paths = self._normalize_skills_paths(skills_path)
        self._skill_meta: dict[str, dict[str, Any]] = {}
        self._skill_tools: dict[str, BaseTool] = {}
        self._load_lock = asyncio.Lock()

    @staticmethod
    def _normalize_skills_paths(
        skills_path: Path | list[Path] | tuple[Path, ...] | None,
    ) -> list[Path]:
        if skills_path is None:
            return []
        if isinstance(skills_path, Path):
            return [skills_path]
        return [p for p in skills_path if p is not None]

    async def load_all(self) -> None:
        """加载所有技能（线程安全）。"""
        async with self._load_lock:
            self._load_skills()

    def _load_skills(self) -> None:
        """扫描所有 skills_path 目录，解析 SKILL.md 文件。"""
        for skills_path in self._skills_paths:
            if not skills_path.exists():
                continue
            for skill_md in skills_path.rglob("SKILL.md"):
                self._parse_skill(skill_md)
        for name, meta in self._skill_meta.items():
            if name not in self._skill_tools:
                self._skill_tools[name] = self._make_skill_tool(name, meta)

    def _parse_skill(self, filepath: Path) -> None:
        try:
            content = filepath.read_text(encoding="utf-8")
            match = FRONTMATTER_RE.match(content)
            if not match:
                return
            frontmatter = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter, dict):
                return
            name = str(frontmatter.get("name", filepath.parent.name))
            if name in self._skill_meta:
                return
            self._skill_meta[name] = {
                "filepath": filepath,
                "description": str(frontmatter.get("description", "No description")),
                "keywords": frontmatter.get("keywords", []),
                "instructions": None,
            }
        except Exception as exc:
            logger.error("[SkillManager] parse failed %s: %s", filepath, exc)

    def read_skill_instructions(self, name: str) -> str | None:
        """读取技能正文（带缓存）。"""
        meta = self._skill_meta.get(name)
        if not meta:
            return None
        if meta.get("instructions") is not None:
            return meta["instructions"]
        content = meta["filepath"].read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(content)
        instructions = content[match.end():].strip() if match else content.strip()
        meta["instructions"] = instructions
        return instructions

    def _make_skill_tool(self, name: str, meta: dict[str, Any]) -> BaseTool:
        @tool(description=f"加载 {name} 技能的专家指令：{meta['description']}")
        async def _load_skill() -> str:
            instructions = self.read_skill_instructions(name)
            return instructions or ""

        _load_skill.name = f"load_skill_{name}"
        return _load_skill

    async def get_tools(self, skill_names: list[str] | None = None) -> list[BaseTool]:
        """获取技能工具列表。

        Args:
            skill_names: 如果提供，只返回指定名称的技能工具；否则返回全部。
        """
        if skill_names is None:
            return list(self._skill_tools.values())
        return [self._skill_tools[n] for n in skill_names if n in self._skill_tools]

    def list_skills(self) -> list[dict[str, Any]]:
        """返回所有已加载技能的元数据。"""
        return [
            {
                "name": name,
                "description": meta["description"],
                "keywords": meta["keywords"],
                "tool_name": f"load_skill_{name}",
            }
            for name, meta in self._skill_meta.items()
        ]

    async def aclose(self) -> None:
        self._skill_meta.clear()
        self._skill_tools.clear()