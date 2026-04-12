"""
PluginManager: 统一的 Agent 工具插件管理器。

支持两类工具来源：

  1. 本地工具 — 通过 register(tool) 注册 @tool 函数 / BaseTool 实例
  2. Skills   — 每个 agent 自带 skills/ 目录，初始化时自动加载

所有工具最终通过 get_tools() 返回 list[BaseTool]，可直接传给 LLM。
"""

import asyncio
import re
from pathlib import Path
from typing import Any, Callable

import yaml
from langchain.tools import tool
from langchain_core.tools import BaseTool

from app.core.logging import get_logger

logger = get_logger(__name__)


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class PluginManager:
    """统一的 Agent 工具插件管理器。

    两类工具来源，最终全部变成 list[BaseTool]：

      local   — 暴露 register() 给外部动态注册本地工具
      skill   — 通过私有方法基于传入路径自动加载

    Agent 只需调用：
        tools = await plugin_manager.get_tools()
        llm_with_tools = llm.bind_tools(tools)
    """

    def __init__(
        self,
        workspace: Path,
        skills_path: Path | None = None,
        tools: list[BaseTool] | None = None,
        **_: Any,
    ) -> None:
        self._skills_path: Path | None = skills_path
        self._workspace: Path = workspace

        self._local_tools: dict[str, BaseTool] = {}
        self._skill_meta: dict[str, dict[str, Any]] = {}
        self._skill_tools: dict[str, BaseTool] = {}

        self._load_lock = asyncio.Lock()

        if tools:
            self.register(*tools)

    @property
    def workspace(self) -> Path:
        """Agent 专属工作目录。"""
        return self._workspace

    async def load_all(self) -> None:
        """扫描并加载所有插件工具。"""
        async with self._load_lock:
            self._workspace.mkdir(parents=True, exist_ok=True)
            logger.info(f"[PluginManager] Agent 工作目录: {self._workspace}")

            if self._skills_path:
                self._load_skills()

            logger.info(
                f"[PluginManager] 加载完成 — "
                f"本地工具: {len(self._local_tools)}, "
                f"Skills: {len(self._skill_meta)}"
            )

    def register(self, *tools: BaseTool | Callable | list[BaseTool | Callable]) -> None:
        """动态注册本地自定义工具。支持 BaseTool 实例、@tool 函数或其列表。"""
        if len(tools) == 1 and isinstance(tools[0], list):
            actual_tools = tools[0]
        else:
            actual_tools = list(tools)

        for t in actual_tools:
            converted = self._convert_to_base_tool(t)
            self._local_tools[converted.name] = converted
            logger.debug(f"[PluginManager] 注册本地工具: {converted.name}")

    def unregister(self, name: str) -> bool:
        """移除已注册的本地工具。"""
        if name in self._local_tools:
            del self._local_tools[name]
            logger.debug(f"[PluginManager] 移除本地工具: {name}")
            return True
        return False

    @staticmethod
    def _convert_to_base_tool(t: BaseTool | Callable) -> BaseTool:
        """将输入统一转为 BaseTool。"""
        if isinstance(t, BaseTool):
            return t
        if callable(t):
            return tool(t)
        raise TypeError(
            f"register() 只接受 BaseTool 实例或可调用对象，收到: {type(t)}"
        )

    def _load_skills(self) -> list[BaseTool]:
        """扫描 skills_path 下各子目录的 SKILL.md，转化为 BaseTool。"""
        if not self._skills_path or not self._skills_path.exists():
            logger.warning(f"[PluginManager] Skills 路径不存在: {self._skills_path}")
            return list(self._skill_tools.values())

        for skill_md in self._skills_path.rglob("SKILL.md"):
            self._parse_skill(skill_md)

        for name, meta in self._skill_meta.items():
            if name not in self._skill_tools:
                self._skill_tools[name] = self._make_skill_tool(name, meta)

        logger.info(f"[PluginManager] 挂载 Skills: {list(self._skill_meta.keys())}")
        return list(self._skill_tools.values())

    def _parse_skill(self, filepath: Path) -> None:
        """读取 SKILL.md，提取 Frontmatter 并在 _skill_meta 注册。"""
        try:
            content = filepath.read_text(encoding="utf-8")
            match = FRONTMATTER_RE.match(content)
            if not match:
                logger.warning(f"[PluginManager] SKILL.md 缺少 Frontmatter: {filepath}")
                return

            frontmatter = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter, dict):
                return

            name = str(frontmatter.get("name", filepath.parent.name))
            if name in self._skill_meta:
                existing = self._skill_meta[name]["filepath"]
                logger.warning(
                    f"[PluginManager] Skill '{name}' 已注册 ({existing})，跳过: {filepath}"
                )
                return

            self._skill_meta[name] = {
                "filepath": filepath,
                "description": str(frontmatter.get("description", "No description")),
                "keywords": frontmatter.get("keywords", []),
                "instructions": None,
            }
        except Exception as exc:
            logger.error(f"[PluginManager] 解析 SKILL.md 失败 ({filepath}): {exc}")

    def _read_skill_instructions(self, name: str) -> str:
        """懒加载技能正文内容。"""
        meta = self._skill_meta.get(name, {})
        if meta.get("instructions") is not None:
            return meta["instructions"]

        try:
            content = meta["filepath"].read_text(encoding="utf-8")
            match = FRONTMATTER_RE.match(content)
            instructions = content[match.end():].strip() if match else content.strip()
            meta["instructions"] = instructions
            return instructions
        except Exception as exc:
            logger.error(f"[PluginManager] 读取 skill '{name}' 指令失败: {exc}")
            return f"# {name} 指令加载失败: {exc}"

    def _make_skill_tool(self, name: str, meta: dict[str, Any]) -> BaseTool:
        """为 skill 包装一个返回字符串的 LangChain Tool。"""
        desc = f"加载 {name} 技能的专家指令：{meta['description']}"

        @tool(description=desc)
        async def _load_skill() -> str:
            logger.info(f"[PluginManager] 工具调用 -> 加载技能指令: {name}")
            return self._read_skill_instructions(name)

        _load_skill.name = f"load_skill_{name}"
        return _load_skill

    async def get_tools(
        self,
        include_local: bool = True,
        include_skills: bool = True,
    ) -> list[BaseTool]:
        """获取所有已加载的工具。"""
        tools: list[BaseTool] = []

        if include_local:
            tools.extend(self._local_tools.values())

        if include_skills:
            tools.extend(self._skill_tools.values())

        logger.info(f"[PluginManager] get_tools() 返回 {len(tools)} 个工具")
        return tools

    def list_local_tools(self) -> list[str]:
        """返回所有已注册的本地工具名称列表。"""
        return list(self._local_tools.keys())

    def list_skills(self) -> list[dict[str, Any]]:
        """返回所有已解析的 Skill 摘要信息。"""
        return [
            {
                "name": name,
                "description": meta["description"],
                "keywords": meta["keywords"],
                "tool_name": f"load_skill_{name}",
            }
            for name, meta in self._skill_meta.items()
        ]

    def summary(self) -> dict[str, list[str]]:
        """返回当前插件管理器的概览。"""
        return {
            "local_tools": list(self._local_tools.keys()),
            "skills": list(self._skill_meta.keys()),
        }

    async def aclose(self) -> None:
        """清理缓存与注册状态。"""
        self._skill_meta.clear()
        self._skill_tools.clear()
        self._local_tools.clear()
        logger.info("[PluginManager] 资源清理完成")

    def __repr__(self) -> str:
        return (
            f"PluginManager("
            f"local={len(self._local_tools)}, "
            f"skills={len(self._skill_meta)})"
        )
