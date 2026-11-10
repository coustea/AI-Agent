"""全系统统一工具层 (app.shared.tools) —— 基于 learn-claude-code s02_tool_use 与 s05_skill_loading。

职责划分：
- ``registry.py``: ``Tool`` 定义与 ``ToolRegistry`` 注册及执行分派器
- ``sandbox.py``: 工作区路径越界防护与工具输出截断
- ``skills.py``: ``SkillLoader`` 与 ``load_skill`` 技能按需加载
- ``builtin/``: 沙箱工作目录工具集（``bash``, ``read``, ``write``, ``edit``, ``glob``, ``grep``, ``view_image``）
"""

from app.shared.tools.builtin import build_builtin_tools
from app.shared.tools.registry import (
    Tool,
    ToolHandler,
    ToolRegistry,
    format_tool_output,
    summarize_tool_args,
    summarize_tool_result,
    tool,
)
from app.shared.tools.sandbox import (
    BASH_TIMEOUT_S,
    MAX_GLOB_RESULTS,
    MAX_GREP_RESULTS,
    MAX_OUTPUT_CHARS,
    MAX_READ_LINES,
    resolve_sandbox_path,
    truncate_output,
)
from app.shared.tools.skills import (
    DEFAULT_SKILLS_DIR,
    LoadSkillArgs,
    SkillLoader,
    build_load_skill_tool,
    get_skill_loader,
)

__all__ = [
    "BASH_TIMEOUT_S",
    "DEFAULT_SKILLS_DIR",
    "LoadSkillArgs",
    "MAX_GLOB_RESULTS",
    "MAX_GREP_RESULTS",
    "MAX_OUTPUT_CHARS",
    "MAX_READ_LINES",
    "SkillLoader",
    "Tool",
    "ToolHandler",
    "ToolRegistry",
    "build_builtin_tools",
    "build_load_skill_tool",
    "format_tool_output",
    "get_skill_loader",
    "resolve_sandbox_path",
    "summarize_tool_args",
    "summarize_tool_result",
    "tool",
    "truncate_output",
]
