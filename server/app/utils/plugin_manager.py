"""
PluginManager: 统一的 Agent 工具插件管理器。

支持三类工具来源：

  1. 本地工具 — 通过 register(tool) 注册 @tool 函数 / BaseTool 实例
  2. MCP 服务 — 每个 agent 自带 mcp/settings.json，初始化时传入路径自动加载
  3. Skills   — 每个 agent 自带 skills/ 目录，初始化时传入路径自动加载

所有工具最终通过 get_tools() 返回 list[BaseTool]，可直接传给 LLM。

用法（Resource Agent，有 MCP + Skills）：
    from app.utils.plugin_manager import PluginManager

    pm = PluginManager(
        workspace=Path("workplace/mindmap"),
        mcp_settings_path=agent_dir / "mcp" / "settings.json",
        skills_path=agent_dir / "skills",
    )
    await pm.load_all()

用法（Chat Agent，仅本地工具）：
    pm = PluginManager(
        workspace=Path("workplace/chat"),
        tools=[my_tool1, my_tool2],
    )
    await pm.load_all()

    # 注册自定义工具
    from langchain.tools import tool

    @tool
    def my_tool(query: str) -> str:
        '''My custom tool.'''
        return "result"

    plugin_manager.register(my_tool)

用法（Agent 内获取工具）：
    tools = await pm.get_tools()  # → list[BaseTool]
"""

import asyncio
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Callable

import yaml
from langchain.tools import tool
from langchain_core.tools import BaseTool

from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field, field_validator

from app.core.logging import get_logger
from app.utils.paths import SERVER_DIR

logger = get_logger(__name__)


_VAR_RE = re.compile(r"\$\{([^}]+)\}")  # 匹配 ${VAR} 格式的变量占位符
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)  # 匹配 Markdown frontmatter（--- 包裹的 YAML 头部）

class _MCPServerConfig(BaseModel):
    """单个 MCP 服务的连接配置模型。"""
    description: str = ""   # MCP 描述
    command: str | None = None  # stdio 模式下要执行的可执行文件路径
    args: list[str] = Field(default_factory=list)  # 传给 command 的命令行参数
    transport: str = "stdio"  # 传输协议类型：stdio（本地进程）或 http（远程服务）
    env: dict[str, str] | None = None  # 传递给子进程的环境变量
    url: str | None = None  # http 模式下的远程服务地址
    cwd: str | None = None  # 子进程的工作目录
    headers: dict[str, Any] | None = None  # http 模式下的自定义请求头
    ensureDirs: list[str] = Field(default_factory=list)  # 启动前需确保存在的目录列表
    mergeOsEnviron: bool = False  # 是否将系统环境变量与 env 字段合并

    @field_validator("transport", mode="before")
    @classmethod
    def _norm(cls, v: str) -> str:
        """将 streamable_http 等别名统一归为 http。"""
        return "http" if v in ("streamable_http", "streamable-http") else v


class _MCPSettings(BaseModel):
    """整个 settings.json 的顶层模型，包含多个 MCP 服务配置。"""
    mcpServers: dict[str, _MCPServerConfig]


def _builtin_vars() -> dict[str, str]:
    """返回内置变量映射，用于替换配置文件中的 ${VAR} 占位符。"""
    return {
        "SERVER_DIR": str(SERVER_DIR),
        "MCP_DIR": str(SERVER_DIR / "mcp"),
        "WORKPLACE_DIR": str(SERVER_DIR / "workplace"),
    }


def _resolve(value: Any, ctx: dict[str, str]) -> Any:
    """递归替换 ${VAR} 变量。优先查内置变量 ctx，其次查系统环境变量，找不到则保留原样。"""
    if isinstance(value, str):
        return _VAR_RE.sub(
            lambda m: ctx.get(m.group(1), os.environ.get(m.group(1), m.group(0))),
            value,
        )
    if isinstance(value, list):
        return [_resolve(v, ctx) for v in value]  # 逐项递归处理列表元素
    if isinstance(value, dict):
        return {k: _resolve(v, ctx) for k, v in value.items()}  # 递归处理字典值
    return value  # 非容器类型（int/bool 等）原样返回


def _build_connection(name: str, cfg: _MCPServerConfig, ctx: dict) -> dict:
    """将 _MCPServerConfig 转换为 MultiServerMCPClient connection_config。"""
    cmd = _resolve(cfg.command, ctx)  # 解析 command 中的变量
    args = _resolve(cfg.args, ctx)  # 解析参数列表中的变量
    env = _resolve(cfg.env, ctx) if cfg.env else None  # 解析环境变量中的占位符
    cwd = _resolve(cfg.cwd, ctx)  # 解析工作目录中的变量
    url = _resolve(cfg.url, ctx)  # 解析远程 URL 中的变量

    # 确保配置中指定的目录在启动前就已创建
    for d in _resolve(cfg.ensureDirs, ctx):
        Path(d).mkdir(parents=True, exist_ok=True)

    conn: dict[str, Any] = {"transport": cfg.transport}

    if cfg.transport == "stdio":
        # stdio 模式：通过子进程与 MCP 服务通信
        if not cmd:
            raise ValueError(f"MCP '{name}': stdio 模式缺少 command")
        conn["command"] = shutil.which(cmd) or cmd  # 优先使用 which 查找可执行文件完整路径
        conn["args"] = args
        # 根据配置决定是否合并系统环境变量
        merged_env = (
            {**os.environ, **env} if env else dict(os.environ)
        ) if cfg.mergeOsEnviron else env
        if merged_env is not None:
            conn["env"] = merged_env
        if cwd:
            conn["cwd"] = cwd
    else:
        # http 模式：通过 HTTP/WebSocket 与远程 MCP 服务通信
        if url:
            conn["url"] = url
        if cfg.headers:
            conn["headers"] = cfg.headers

    return conn


# ──────────────────────────────────────────────────────────────
# PluginManager
# ──────────────────────────────────────────────────────────────

class PluginManager:
    """统一的 Agent 工具插件管理器。

    三类工具来源，最终全部变成 list[BaseTool]：

      local   — 暴露 register() 给外部动态注册本地工具
      mcp     — 通过私有方法基于传入路径自动加载
      skill   — 通过私有方法基于传入路径自动加载

    Agent 只需调用：
        tools = await plugin_manager.get_tools()
        llm_with_tools = llm.bind_tools(tools)
    """

    def __init__(
        self,
        workspace: Path,
        mcp_settings_path: Path | None = None,
        skills_path: Path | None = None,
        tools: list[BaseTool] | None = None,
    ) -> None:
        self._mcp_settings_path = mcp_settings_path  # MCP 配置文件路径（如 mcp/settings.json）
        self._skills_path: Path | None = skills_path  # Skills 目录路径（包含多个 SKILL.md）
        self._workspace: Path = workspace  # Agent 专属工作目录

        # 本地工具：name → BaseTool
        self._local_tools: dict[str, BaseTool] = {}

        # 如果初始化时传入了工具列表，立即注册
        if tools:
            self.register(*tools)

        # MCP 相关状态：配置、客户端实例、工具缓存、异步锁（防并发重复加载）
        self._mcp_configs: dict[str, dict] = {}
        self._mcp_clients: dict[str, MultiServerMCPClient] = {}
        self._mcp_cache: dict[str, list[BaseTool]] = {}
        self._mcp_locks: dict[str, asyncio.Lock] = {}
        self._mcp_health: dict[str, dict[str, Any]] = {}  # MCP 健康状态记录
        self._load_lock = asyncio.Lock()  # 全局加载锁，防止并发加载
        self._locks_lock = asyncio.Lock()  # 保护 _mcp_locks 的并发访问

        # Skills 相关状态：元数据（文件路径、描述等）和包装后的 BaseTool 实例
        self._skill_meta: dict[str, dict] = {}
        self._skill_tools: dict[str, BaseTool] = {}

    # ══════════════════════════════════════════════════════════
    # 属性
    # ══════════════════════════════════════════════════════════

    @property
    def workspace(self) -> Path:
        """Agent 专属工作目录，如 workplace/mindmap、workplace/code。"""
        return self._workspace

    # ══════════════════════════════════════════════════════════
    # 一键加载（App 启动/初始化调用一次）
    # ══════════════════════════════════════════════════════════

    async def load_all(self) -> None:
        """扫描并加载所有工具插件。

        1. 创建 Agent 工作目录
        2. 加载 MCP 配置（如指定）
        3. 扫描 skills_path 下的所有子目录（如指定）
        """
        async with self._load_lock:
            # 0. 确保 Agent 工作目录存在
            self._workspace.mkdir(parents=True, exist_ok=True)
            logger.info(f"[PluginManager] Agent 工作目录: {self._workspace}")

            # 1. 加载 MCP 配置
            if self._mcp_settings_path:
                self._load_mcp_settings(self._mcp_settings_path)

            # 2. 加载技能
            if self._skills_path:
                self._load_skills()

            logger.info(
                f"[PluginManager] 加载完成 — "
                f"本地工具: {len(self._local_tools)}, "
                f"MCP 服务: {len(self._mcp_configs)}, "
                f"Skills: {len(self._skill_meta)}"
            )

    # ══════════════════════════════════════════════════════════
    # register: 注册自定义工具（唯一暴露的公共注册 API）
    # ══════════════════════════════════════════════════════════

    def register(self, *tools: BaseTool | Callable | list[BaseTool | Callable]) -> None:
        """动态注册本地自定义工具。支持 BaseTool 实例、@tool 函数或其列表。"""
        # 如果只传了一个列表参数，直接解包使用
        if len(tools) == 1 and isinstance(tools[0], list):
            actual_tools = tools[0]
        else:
            actual_tools = list(tools)

        for t in actual_tools:
            converted = self._convert_to_base_tool(t)  # 统一转换为 BaseTool
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

    # ══════════════════════════════════════════════════════════
    # 私有 MCP 与 Skills 加载方法
    # ══════════════════════════════════════════════════════════

    def _load_mcp_settings(self, path: Path) -> None:
        """读取 settings.json，解析并存储 connection_config。"""
        if not path.exists():
            logger.warning(f"[PluginManager] MCP 配置文件不存在: {path}")
            return

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))  # 读取 JSON 文件
            settings = _MCPSettings.model_validate(raw)  # 用 Pydantic 模型校验结构
        except Exception as e:
            logger.error(f"[PluginManager] MCP 配置解析失败 ({path}): {e}")
            return

        # 构建变量替换上下文：内置变量 + 当前 MCP 目录
        ctx = _builtin_vars()
        ctx["CURRENT_MCP_DIR"] = str(path.parent.resolve())

        # 遍历每个 MCP 服务配置，构建连接并创建客户端
        for name, cfg in settings.mcpServers.items():
            if name in self._mcp_configs:
                logger.debug(f"[PluginManager] MCP '{name}' 已注册，跳过")
                continue
            try:
                conn = _build_connection(name, cfg, ctx)  # 解析变量并构建连接配置
                self._mcp_configs[name] = conn
                self._mcp_clients[name] = MultiServerMCPClient({name: conn})  # 为每个服务创建独立客户端
                logger.info(
                    f"[PluginManager] 加载 MCP 服务: {name} — {cfg.description}"
                )
            except Exception as e:
                logger.error(f"[PluginManager] MCP '{name}' 初始化连接失败: {e}")

    async def _get_mcp_tools(self, name: str) -> list[BaseTool]:
        """内部方法：懒加载单个 MCP 服务的工具列表（首次调用时才实际连接）。"""
        # 命中缓存则直接返回，避免重复连接
        if name in self._mcp_cache:
            return self._mcp_cache[name]

        # 每个 MCP 服务一把锁，防止并发时重复加载
        async with self._locks_lock:
            lock = self._mcp_locks.setdefault(name, asyncio.Lock())
        async with lock:
            # 双重检查：获取锁后再查一次缓存
            if name in self._mcp_cache:
                return self._mcp_cache[name]

            client = self._mcp_clients.get(name)
            if not client:
                return []
            try:
                start_time = time.time()
                tools = await client.get_tools(server_name=name)  # 从 MCP 服务拉取可用工具
                elapsed = time.time() - start_time
                self._mcp_cache[name] = tools  # 缓存结果，后续直接复用
                # 记录健康状态
                self._mcp_health[name] = {
                    "healthy": True,
                    "last_check": time.time(),
                    "response_time": elapsed,
                    "error": None,
                }
                logger.info(
                    f"[PluginManager] MCP '{name}' 加载工具: {[t.name for t in tools]} (耗时: {elapsed:.2f}s)"
                )
                return tools
            except Exception as e:
                # 记录不健康状态
                self._mcp_health[name] = {
                    "healthy": False,
                    "last_check": time.time(),
                    "response_time": None,
                    "error": str(e),
                }
                logger.error(f"[PluginManager] MCP '{name}' 获取工具失败: {e}")
                return []

    def _load_skills(self) -> list[BaseTool]:
        """内部方法：扫描 skills_path 下各子目录的 SKILL.md，转化为 BaseTool。"""
        if not self._skills_path.exists():
            logger.warning(f"[PluginManager] Skills 路径不存在: {self._skills_path}")
        else:
            # 递归查找所有 SKILL.md 文件并解析
            for skill_md in self._skills_path.rglob("SKILL.md"):
                self._parse_skill(skill_md)

        # 为每个已解析的 skill 创建对应的 LangChain 工具
        for name, meta in self._skill_meta.items():
            if name not in self._skill_tools:
                self._skill_tools[name] = self._make_skill_tool(name, meta)

        logger.info(
            f"[PluginManager] 挂载 Skills: {list(self._skill_meta.keys())}"
        )
        return list(self._skill_tools.values())

    def _parse_skill(self, filepath: Path) -> None:
        """读取 SKILL.md，提取 Frontmatter（YAML 元数据）并在 _skill_meta 注册。"""
        try:
            content = filepath.read_text(encoding="utf-8")
            m = FRONTMATTER_RE.match(content)  # 提取 --- 包裹的 frontmatter
            if not m:
                logger.warning(
                    f"[PluginManager] SKILL.md 缺少 Frontmatter: {filepath}"
                )
                return
            fm = yaml.safe_load(m.group(1))  # 解析 YAML 头部为字典
            if not isinstance(fm, dict):
                return
            # 优先用 frontmatter 中的 name 字段，否则用目录名
            name = str(fm.get("name", filepath.parent.name))

            if name in self._skill_meta:
                existing = self._skill_meta[name]["filepath"]
                logger.warning(
                    f"[PluginManager] Skill '{name}' 已注册 ({existing})，跳过: {filepath}"
                )
                return

            # 存入元数据：instructions 初始为 None，首次使用时懒加载
            self._skill_meta[name] = {
                "filepath": filepath,
                "description": str(fm.get("description", "No description")),
                "keywords": fm.get("keywords", []),
                "instructions": None,
            }
        except Exception as e:
            logger.error(f"[PluginManager] 解析 SKILL.md 失败 ({filepath}): {e}")

    def _read_skill_instructions(self, name: str) -> str:
        """懒加载：首次调用时读取 SKILL.md 正文（frontmatter 之后的内容），后续从缓存取。"""
        meta = self._skill_meta.get(name, {})
        if meta.get("instructions") is not None:
            return meta["instructions"]  # 已缓存，直接返回
        try:
            content = meta["filepath"].read_text(encoding="utf-8")
            m = FRONTMATTER_RE.match(content)
            # 取 frontmatter 结束位置之后的全部内容作为指令正文
            instructions = content[m.end():].strip() if m else content.strip()
            meta["instructions"] = instructions  # 缓存以便复用
            return instructions
        except Exception as e:
            logger.error(f"[PluginManager] 读取 skill '{name}' 指令失败: {e}")
            return f"# {name} 指令加载失败: {e}"

    def _make_skill_tool(self, name: str, meta: dict) -> BaseTool:
        """为 skill 包装一个单纯返回字符串的 LangChain Tool（不允许内部调用大模型）。"""
        desc = f"加载 {name} 技能的专家指令：{meta['description']}"

        @tool(description=desc)
        async def _load_skill() -> str:
            """返回对应技能的文本指令内容，供 Agent 在运行时读取。"""
            logger.info(f"[PluginManager] 工具调用 -> 加载技能指令: {name}")
            return self._read_skill_instructions(name)  # 懒加载并返回 SKILL.md 正文

        _load_skill.name = f"load_skill_{name}"  # 工具名以 load_skill_ 为前缀，便于识别
        return _load_skill

    # ══════════════════════════════════════════════════════════
    # 核心获取接口 (暴露给 Agent)
    # ══════════════════════════════════════════════════════════

    async def get_tools(
        self,
        include_local: bool = True,
        include_mcp: list[str] | None = None,  # None = 全部，[] = 不含
        include_skills: bool = True,
    ) -> list[BaseTool]:
        """获取所有已加载的工具（整合本地、MCP 和 Skills），返回给 LangChain。"""
        tools: list[BaseTool] = []

        # 1. 收集本地工具
        if include_local:
            tools.extend(self._local_tools.values())

        # 2. 收集 MCP 工具（None 表示全部加载，空列表表示跳过）
        mcp_names = (
            list(self._mcp_configs.keys()) if include_mcp is None else include_mcp
        )
        for name in mcp_names:
            if name not in self._mcp_configs:
                logger.warning(f"[PluginManager] 未找到 MCP 服务: {name}")
                continue
            mcp_tools = await self._get_mcp_tools(name)  # 懒加载：首次调用时才连接 MCP 服务
            tools.extend(mcp_tools)

        # 3. 收集 Skill 工具
        if include_skills:
            tools.extend(self._skill_tools.values())

        logger.info(
            f"[PluginManager] get_tools() 返回 {len(tools)} 个工具"
        )
        return tools

    # ══════════════════════════════════════════════════════════
    # 查询与助手接口
    # ══════════════════════════════════════════════════════════

    def list_local_tools(self) -> list[str]:
        """返回所有已注册的本地工具名称列表。"""
        return list(self._local_tools.keys())

    def list_mcp_services(self) -> list[str]:
        """返回所有已加载的 MCP 服务名称列表。"""
        return list(self._mcp_configs.keys())

    def list_skills(self) -> list[dict]:
        """返回所有已解析的 Skill 摘要信息（名称、描述、关键词、工具名）。"""
        return [
            {
                "name": n,
                "description": m["description"],
                "keywords": m["keywords"],
                "tool_name": f"load_skill_{n}",
            }
            for n, m in self._skill_meta.items()
        ]

    def summary(self) -> dict:
        """返回当前插件管理器的概览：本地工具、MCP 服务、Skills 的名称列表。"""
        return {
            "local_tools": list(self._local_tools.keys()),
            "mcp_services": list(self._mcp_configs.keys()),
            "skills": list(self._skill_meta.keys()),
        }

    # ══════════════════════════════════════════════════════════
    # MCP 健康检查方法
    # ══════════════════════════════════════════════════════════

    async def check_mcp_health(self, name: str, timeout: float = 5.0) -> dict[str, Any]:
        """检查单个 MCP 服务的健康状态。

        Args:
            name: MCP 服务名称
            timeout: 超时时间（秒）

        Returns:
            健康状态字典，包含 healthy, last_check, response_time, error 等字段
        """
        if name not in self._mcp_configs:
            return {
                "healthy": False,
                "last_check": time.time(),
                "response_time": None,
                "error": f"MCP 服务 '{name}' 未配置",
            }

        client = self._mcp_clients.get(name)
        if not client:
            return {
                "healthy": False,
                "last_check": time.time(),
                "response_time": None,
                "error": f"MCP 服务 '{name}' 客户端未初始化",
            }

        try:
            start_time = time.time()
            # 尝试获取工具列表作为健康检查
            await asyncio.wait_for(client.get_tools(server_name=name), timeout=timeout)
            elapsed = time.time() - start_time

            health_status = {
                "healthy": True,
                "last_check": time.time(),
                "response_time": elapsed,
                "error": None,
            }
            self._mcp_health[name] = health_status
            return health_status
        except asyncio.TimeoutError:
            health_status = {
                "healthy": False,
                "last_check": time.time(),
                "response_time": None,
                "error": f"健康检查超时（>{timeout}s）",
            }
            self._mcp_health[name] = health_status
            logger.warning(f"[PluginManager] MCP '{name}' 健康检查超时")
            return health_status
        except Exception as e:
            health_status = {
                "healthy": False,
                "last_check": time.time(),
                "response_time": None,
                "error": str(e),
            }
            self._mcp_health[name] = health_status
            logger.warning(f"[PluginManager] MCP '{name}' 健康检查失败: {e}")
            return health_status

    async def check_all_mcp_health(self, timeout: float = 5.0) -> dict[str, dict[str, Any]]:
        """检查所有已配置的 MCP 服务健康状态。

        Args:
            timeout: 每个服务的超时时间（秒）

        Returns:
            字典，键为 MCP 服务名，值为健康状态字典
        """
        results = {}
        for name in self._mcp_configs.keys():
            results[name] = await self.check_mcp_health(name, timeout=timeout)
        return results

    def is_mcp_healthy(self, name: str) -> bool:
        """快速检查 MCP 服务是否健康（基于缓存的健康状态）。

        Args:
            name: MCP 服务名称

        Returns:
            True 如果服务健康或未配置，False 如果服务不健康
        """
        if name not in self._mcp_health:
            # 未配置或未检查过，默认认为健康
            return True
        return self._mcp_health[name].get("healthy", True)

    def __repr__(self) -> str:
        """可读的字符串表示，显示各类工具的数量。"""
        return (
            f"PluginManager("
            f"local={len(self._local_tools)}, "
            f"mcp={len(self._mcp_configs)}, "
            f"skills={len(self._skill_meta)})"
        )


# ──────────────────────────────────────────────────────────────
# 全局单例 (已废弃)
# ──────────────────────────────────────────────────────────────
# plugin_manager = PluginManager() 
# 每个 Agent 现在应该自行实例化独立的 PluginManager。
