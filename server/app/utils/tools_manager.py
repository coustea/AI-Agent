"""
ToolsManager：统一的 Agent 工具管理器。

负责统一组装 Agent 所需的各类工具（本地安全工具、MCP 工具等）。
各 Agent 应该在初始化时请求自身所需的最小权限工具集。

用法：
    from app.utils.tools_manager import tools_manager

    # 在 Agent 内部获取特定工具
    self.tools = await tools_manager.get_agent_tools(
        tool_names=["read_file_safe", "safe_shell"], 
        mcp_services=["markmap"]
    )
"""

from pathlib import Path
from typing import List, Optional

from langchain_core.tools import BaseTool

from app.core.logging import get_logger
from app.modules.resource.tools.read_file import read_file_safe
from app.modules.resource.tools.shell_excute import safe_shell
from app.utils.mcp_manager import mcp_manager

logger = get_logger(__name__)

class ToolsManager:
    """管理 Agent 可用的工具。"""

    def __init__(self) -> None:
        self._registered_tools: dict[str, BaseTool] = {
            "read_file_safe": read_file_safe,
            "safe_shell": safe_shell
        }
        
    def register_tool(self, name: str, tool: BaseTool) -> None:
        """动态注册一个额外的本地基础工具。"""
        self._registered_tools[name] = tool

    async def get_agent_tools(
        self, 
        tool_names: Optional[List[str]] = None, 
        mcp_services: Optional[List[str]] = None
    ) -> List[BaseTool]:
        """
        按需组装并返回供 LangChain Agent 调用的 Tools 列表。
        
        Args:
            tool_names: 需要加载的本地工具名称列表（如 ["read_file_safe", "safe_shell"]）
            mcp_services: 需要加载的 MCP 服务名称列表（如 ["markmap"]）
        """
        tools = []
        
        if tool_names:
            for name in tool_names:
                if name in self._registered_tools:
                    tools.append(self._registered_tools[name])
                else:
                    logger.warning(f"[ToolsManager] 请求的本地工具 '{name}' 未注册。")
            
        if mcp_services:
            for mcp_name in mcp_services:
                try:
                    if not mcp_manager.has(mcp_name):
                        mcp_manager.load_from_settings()
                    mcp_tools = await mcp_manager.get_tools(mcp_name)
                    tools.extend(mcp_tools)
                except Exception as e:
                    logger.error(f"[ToolsManager] 加载 MCP 服务 '{mcp_name}' 失败: {e}")

        return tools


# 全局单例
tools_manager = ToolsManager()
