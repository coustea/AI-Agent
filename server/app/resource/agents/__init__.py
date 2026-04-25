"""Resource agent package.

显式导出所有活跃的 Agent 实例，便于：
- IDE 自动补全和类型检查
- 明确模块边界
- 统一导入入口
"""

from app.resource.agents.content import content_writer
from app.resource.agents.mindmap import mindmap_generator
from app.resource.agents.quiz import quiz_agent
from app.resource.agents.reading import reading_agent
from app.resource.agents.code import code_agent
from app.resource.agents.ppt import ppt_agent

__all__ = [
    "content_writer",
    "mindmap_generator",
    "quiz_agent",
    "reading_agent",
    "code_agent",
    "ppt_agent",
]
