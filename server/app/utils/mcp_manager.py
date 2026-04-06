"""
MCPManager: MCP 服务管理器。

统一管理所有 MCP 服务的注册、调用和生命周期。
支持从 mcp/settings.json 自动加载配置。

用法：
    from app.utils.mcp_manager import mcp_manager

    # 自动从 settings.json 加载所有服务
    mcp_manager.load_from_settings()

    # 手动注册 MCP 服务
    mcp_manager.register("markmap", {
        "command": "node",
        "args": ["/path/to/index.js"],
        "transport": "stdio",
    })

    # 调用工具
    result = await mcp_manager.call_tool("markmap", "markdown_to_mindmap", markdown="# Hello")

    # 获取 LangChain tools（可直接传给 Agent）
    tools = await mcp_manager.get_tools("markmap")
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Literal

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field, field_validator

from app.core.logging import get_logger

logger = get_logger(__name__)

# ==========================================
# 常量
# ==========================================

# ${VAR} 变量匹配正则
_VAR_RE = re.compile(r"\$\{([^}]+)\}")

# server/ 目录（本文件位于 app/utils/mcp_manager.py）
SERVER_DIR = Path(__file__).resolve().parents[2]

# settings.json 默认路径
DEFAULT_SETTINGS_PATH = SERVER_DIR / "mcp" / "settings.json"


# ==========================================
# Pydantic 模型
# ==========================================


class MCPServerConfig(BaseModel):
    """单个 MCP 服务的配置。"""

    description: str = ""
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    transport: Literal["stdio", "sse", "http", "websocket"] = "stdio"
    env: dict[str, str] | None = None
    url: str | None = None
    cwd: str | None = None
    headers: dict[str, Any] | None = None
    ensureDirs: list[str] = Field(default_factory=list)
    mergeOsEnviron: bool = False

    @field_validator("transport", mode="before")
    @classmethod
    def normalize_transport(cls, v: str) -> str:
        if v in ("streamable_http", "streamable-http"):
            return "http"
        return v


class MCPSettings(BaseModel):
    """settings.json 顶层结构。"""

    mcpServers: dict[str, MCPServerConfig]


# ==========================================
# 变量替换
# ==========================================


def _build_builtin_vars() -> dict[str, str]:
    """构建内置变量映射。"""
    return {
        "SERVER_DIR": str(SERVER_DIR),
        "MCP_DIR": str(SERVER_DIR / "mcp"),
        "WORKPLACE_DIR": str(SERVER_DIR / "workplace"),
    }


def _resolve_variables(value: Any, context: dict[str, str]) -> Any:
    """递归替换字符串中的 ${VAR} 变量。

    内置变量优先，其次从 os.environ 查找，未找到则保留原样。
    """
    if isinstance(value, str):
        return _VAR_RE.sub(
            lambda m: context.get(
                m.group(1), os.environ.get(m.group(1), m.group(0))
            ),
            value,
        )
    if isinstance(value, list):
        return [_resolve_variables(item, context) for item in value]
    if isinstance(value, dict):
        return {k: _resolve_variables(v, context) for k, v in value.items()}
    return value


def _prepare_server_config(
    name: str,
    config: MCPServerConfig,
    builtin_vars: dict[str, str],
) -> tuple[dict, str]:
    """将 Pydantic 配置转换为 MultiServerMCPClient 所需的 connection_config。

    Returns:
        (connection_config, description)
    """
    resolved_command = _resolve_variables(config.command, builtin_vars)
    resolved_args = _resolve_variables(config.args, builtin_vars)
    resolved_env = (
        _resolve_variables(config.env, builtin_vars) if config.env else None
    )
    resolved_cwd = _resolve_variables(config.cwd, builtin_vars)
    resolved_url = _resolve_variables(config.url, builtin_vars)
    resolved_ensure_dirs = _resolve_variables(config.ensureDirs, builtin_vars)

    # 创建目录
    for dir_path in resolved_ensure_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    # 构建 connection_config
    connection_config: dict[str, Any] = {"transport": config.transport}

    if config.transport == "stdio":
        if not resolved_command:
            raise ValueError(
                f"MCP 服务 '{name}' 使用 stdio 传输，但缺少 command 字段"
            )
        # 尝试解析 command 为绝对路径（解析不到则保留原值，运行时由子进程 PATH 解析）
        resolved_abs = shutil.which(resolved_command)
        if resolved_abs:
            resolved_command = resolved_abs
        connection_config["command"] = resolved_command
        connection_config["args"] = resolved_args
        if resolved_env is not None:
            if config.mergeOsEnviron:
                connection_config["env"] = {**os.environ, **resolved_env}
            else:
                connection_config["env"] = resolved_env
        elif config.mergeOsEnviron:
            connection_config["env"] = dict(os.environ)
        if resolved_cwd:
            connection_config["cwd"] = resolved_cwd
    else:
        if resolved_url:
            connection_config["url"] = resolved_url
        if config.headers:
            connection_config["headers"] = config.headers

    return connection_config, config.description


# ==========================================
# MCPManager 类
# ==========================================


class MCPManager:
    """MCP 服务管理器。

    统一管理所有 MCP 服务的注册、调用和生命周期。
    Agent 通过此类与 MCP 服务交互。
    """

    def __init__(self):
        self._services: dict[str, dict] = {}
        self._clients: dict[str, MultiServerMCPClient] = {}
        self._descriptions: dict[str, str] = {}

    # ==========================================
    # 配置加载
    # ==========================================

    def load_from_settings(self, settings_path: Path | None = None) -> None:
        """从 mcp/settings.json 加载并注册所有 MCP 服务。

        单个服务注册失败不影响其余服务。

        Args:
            settings_path: 配置文件路径，默认 server/mcp/settings.json
        """
        path = settings_path or DEFAULT_SETTINGS_PATH

        if not path.exists():
            logger.warning(f"[MCPManager] 配置文件不存在: {path}")
            return

        logger.info(f"[MCPManager] 正在加载配置: {path}")

        # 读取并解析 JSON
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"[MCPManager] JSON 解析失败 ({path}): {e}")
            return

        # Pydantic 校验
        try:
            settings = MCPSettings.model_validate(raw)
        except Exception as e:
            logger.error(f"[MCPManager] 配置校验失败 ({path}): {e}")
            return

        # 注册每个服务
        builtin_vars = _build_builtin_vars()
        for name, config in settings.mcpServers.items():
            try:
                connection_config, description = _prepare_server_config(
                    name, config, builtin_vars
                )
                self.register(
                    name=name,
                    connection_config=connection_config,
                    description=description,
                )
            except (ValueError, KeyError) as e:
                logger.error(f"[MCPManager] 注册服务 '{name}' 失败: {e}")
            except Exception as e:
                logger.error(f"[MCPManager] 注册服务 '{name}' 时发生意外错误: {e}")

        logger.info(
            f"[MCPManager] 已注册 {len(self.list_services())} 个 MCP 服务: "
            f"{self.list_services()}"
        )

    # ==========================================
    # 注册 / 删除
    # ==========================================

    def register(
        self,
        name: str,
        connection_config: dict,
        description: str = "",
    ) -> None:
        """注册一个 MCP 服务。

        Args:
            name: 服务唯一名称，如 "markmap"
            connection_config: MultiServerMCPClient 连接配置
            description: 服务描述

        Raises:
            ValueError: 服务名已存在
        """
        if name in self._services:
            raise ValueError(f"MCP 服务 '{name}' 已注册，不可重复注册")

        self._services[name] = connection_config
        self._descriptions[name] = description
        self._clients[name] = MultiServerMCPClient({name: connection_config})
        logger.info(f"[MCPManager] 已注册服务: {name} — {description}")

    def unregister(self, name: str) -> None:
        """删除已注册的 MCP 服务。

        Args:
            name: 服务名称

        Raises:
            KeyError: 服务不存在
        """
        if name not in self._services:
            raise KeyError(f"MCP 服务 '{name}' 不存在，无法删除")

        del self._services[name]
        del self._clients[name]
        del self._descriptions[name]
        logger.info(f"[MCPManager] 已删除服务: {name}")

    # ==========================================
    # 调用工具
    # ==========================================

    async def call_tool(
        self, service_name: str, tool_name: str, **kwargs
    ) -> Any:
        """调用指定 MCP 服务的工具。

        每次调用会建立一个新的 MCP session，调用完毕自动关闭。
        """
        client = self._get_client(service_name)
        logger.info(
            f"[MCPManager] 调用 {service_name}.{tool_name}，参数: {kwargs}"
        )
        async with client.session(service_name) as session:
            result = await session.call_tool(tool_name, arguments=kwargs)
            logger.info(f"[MCPManager] {service_name}.{tool_name} 调用完成")
            return result

    async def call_tool_json(
        self, service_name: str, tool_name: str, **kwargs
    ) -> dict:
        """调用工具并将结果解析为 dict。"""
        result = await self.call_tool(service_name, tool_name, **kwargs)
        result_text = result.content[0].text if result.content else "{}"
        return json.loads(result_text)

    # ==========================================
    # 获取 LangChain Tools
    # ==========================================

    async def get_tools(self, service_name: str) -> list[BaseTool]:
        """获取指定服务暴露的 LangChain Tools。"""
        client = self._get_client(service_name)
        return await client.get_tools(server_name=service_name)

    async def get_all_tools(
        self, service_names: list[str] | None = None
    ) -> list[BaseTool]:
        """获取多个服务的 LangChain Tools。"""
        names = service_names or list(self._services.keys())
        all_tools: list[BaseTool] = []
        for name in names:
            tools = await self.get_tools(name)
            all_tools.extend(tools)
        return all_tools

    # ==========================================
    # 查询
    # ==========================================

    def has(self, name: str) -> bool:
        """检查服务是否已注册。"""
        return name in self._services

    def list_services(self) -> list[str]:
        """列出所有已注册的服务名。"""
        return list(self._services.keys())

    def get_service_info(self, name: str) -> dict:
        """获取指定服务的信息。"""
        if name not in self._services:
            raise KeyError(f"MCP 服务 '{name}' 不存在")
        return {
            "name": name,
            "description": self._descriptions[name],
            "config": self._services[name],
        }

    def list_services_detail(self) -> list[dict]:
        """列出所有服务的详细信息。"""
        return [
            {"name": n, "description": self._descriptions[n]}
            for n in self._services
        ]

    # ==========================================
    # 内部方法
    # ==========================================

    def _get_client(self, service_name: str) -> MultiServerMCPClient:
        """获取已注册服务的 client，不存在则抛异常。"""
        if service_name not in self._clients:
            available = self.list_services()
            raise KeyError(
                f"MCP 服务 '{service_name}' 未注册。已注册: {available}"
            )
        return self._clients[service_name]

    def __repr__(self) -> str:
        return f"MCPManager(services={self.list_services()})"


# ==========================================
# 全局单例
# ==========================================
mcp_manager = MCPManager()
