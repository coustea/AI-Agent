"""Tool-plugin adapter."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any, Callable

import yaml
from langchain.tools import tool
from langchain_core.tools import BaseTool

from app.infra.logging import get_logger

logger = get_logger(__name__)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class PluginManager:
    def __init__(
        self,
        workspace: Path,
        skills_path: Path | list[Path] | tuple[Path, ...] | None = None,
        tools: list[BaseTool] | None = None,
        **_: Any,
    ) -> None:
        self._skills_paths = self._normalize_skills_paths(skills_path)
        self._workspace = workspace
        self._local_tools: dict[str, BaseTool] = {}
        self._skill_meta: dict[str, dict[str, Any]] = {}
        self._skill_tools: dict[str, BaseTool] = {}
        self._load_lock = asyncio.Lock()
        if tools:
            self.register(*tools)

    @property
    def workspace(self) -> Path:
        return self._workspace

    async def load_all(self) -> None:
        async with self._load_lock:
            self._workspace.mkdir(parents=True, exist_ok=True)
            if self._skills_paths:
                self._load_skills()

    @staticmethod
    def _normalize_skills_paths(
        skills_path: Path | list[Path] | tuple[Path, ...] | None,
    ) -> list[Path]:
        if skills_path is None:
            return []
        if isinstance(skills_path, Path):
            return [skills_path]
        return [p for p in skills_path if p is not None]

    def register(self, *tools: BaseTool | Callable | list[BaseTool | Callable]) -> None:
        actual_tools = list(tools[0]) if len(tools) == 1 and isinstance(tools[0], list) else list(tools)
        for item in actual_tools:
            converted = self._convert_to_base_tool(item)
            self._local_tools[converted.name] = converted

    def unregister(self, name: str) -> bool:
        if name in self._local_tools:
            del self._local_tools[name]
            return True
        return False

    @staticmethod
    def _convert_to_base_tool(item: BaseTool | Callable) -> BaseTool:
        if isinstance(item, BaseTool):
            return item
        if callable(item):
            return tool(item)
        raise TypeError(f"unsupported tool type: {type(item)}")

    def _load_skills(self) -> None:
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
            logger.error("[PluginManager] parse failed %s: %s", filepath, exc)

    def _read_skill_instructions(self, name: str) -> str:
        meta = self._skill_meta.get(name, {})
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
            return self._read_skill_instructions(name)

        _load_skill.name = f"load_skill_{name}"
        return _load_skill

    async def get_tools(self, include_local: bool = True, include_skills: bool = True) -> list[BaseTool]:
        tools: list[BaseTool] = []
        if include_local:
            tools.extend(self._local_tools.values())
        if include_skills:
            tools.extend(self._skill_tools.values())
        return tools

    def list_skills(self) -> list[dict[str, Any]]:
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
        self._local_tools.clear()
