from .shell_execute import shell_exec
from .web_fetch import web_fetch
from .file_write import file_append



AGENT_TOOLS = [shell_exec, web_fetch, file_append]

__all__ = ["AGENT_TOOLS"]
