"""全系统统一工具层 (app.shared.tools) —— 基于 learn-claude-code s02_tool_use、s04_subagent & s05_skill_loading。

职责划分：
- ``registry.py``: ``Tool`` 定义与 ``ToolRegistry`` 注册及执行分派器
- ``sandbox.py``: 工作区路径越界防护与工具输出截断
- ``skills.py``: ``SkillLoader``、``load_skill`` 与 ``copy_skill_template``
- ``subagent.py``: ``run_subagent`` 与 ``build_subagent_tool`` 通用无状态子智能体工具
- ``builtin/``: 沙箱工作目录工具集（``bash``, ``read``, ``write``, ``edit``, ``glob``, ``grep``, ``view_image``）
"""

from app.shared.tools.builtin import build_builtin_tools
from app.shared.tools.registry import (
    Tool,
    ToolEventHandler,
    ToolHandler,
    ToolRegistry,
    ToolRuntimeEvent,
    format_tool_output,
    tool,
)
from app.shared.tools.sandbox import (
    BASH_TIMEOUT_S,
    MAX_GLOB_RESULTS,
    MAX_GREP_RESULTS,
    MAX_OUTPUT_CHARS,
    MAX_READ_LINES,
    resolve,
    resolve_sandbox_path,
    safe_path,
    truncate,
    truncate_output,
)
from app.shared.tools.skills import (
    CopySkillTemplateArgs,
    DEFAULT_SKILLS_DIR,
    LoadSkillArgs,
    SkillLoader,
    build_copy_skill_template_tool,
    build_load_skill_tool,
    get_skill_loader,
)
from app.shared.tools.subagent import (
    DEFAULT_SUBAGENT_SYSTEM_PROMPT,
    SubagentArgs,
    build_subagent_tool,
    run_subagent,
)

__all__ = [
    "BASH_TIMEOUT_S",
    "CopySkillTemplateArgs",
    "DEFAULT_SKILLS_DIR",
    "DEFAULT_SUBAGENT_SYSTEM_PROMPT",
    "LoadSkillArgs",
    "MAX_GLOB_RESULTS",
    "MAX_GREP_RESULTS",
    "MAX_OUTPUT_CHARS",
    "MAX_READ_LINES",
    "SkillLoader",
    "SubagentArgs",
    "Tool",
    "ToolEventHandler",
    "ToolHandler",
    "ToolRegistry",
    "ToolRuntimeEvent",
    "build_builtin_tools",
    "build_copy_skill_template_tool",
    "build_load_skill_tool",
    "build_subagent_tool",
    "format_tool_output",
    "get_skill_loader",
    "resolve",
    "resolve_sandbox_path",
    "run_subagent",
    "safe_path",
    "tool",
    "truncate",
    "truncate_output",
]
