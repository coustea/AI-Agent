from .shell_execute import shell_exec
from .web_fetch import web_fetch
from .file_write import file_append
from .file_read import file_read
from .file_list import file_list
from .data_analyzer import data_analyze
from .web_search import web_search



AGENT_TOOLS = [shell_exec, web_fetch, file_append, file_read, file_list, data_analyze, web_search]

__all__ = ["AGENT_TOOLS"]
