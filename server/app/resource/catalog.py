"""资源 Agent 的唯一静态目录：执行策略与前端展示共用同一份定义。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AgentKind = Literal["base", "aggregation"]


@dataclass(frozen=True, slots=True)
class ResourceAgentDescriptor:
    agent_id: str
    name: str
    icon: str
    description: str
    kind: AgentKind
    content_format: str
    timeout_seconds: float
    start_message: str


RESOURCE_AGENTS: tuple[ResourceAgentDescriptor, ...] = (
    ResourceAgentDescriptor("content", "课程内容", "Document", "专业课程讲解文档", "base", "markdown", 600, "开始生成课程讲解资源..."),
    ResourceAgentDescriptor("mindmap", "思维导图", "Mindmap", "知识结构思维导图", "base", "markdown", 600, "开始生成知识结构导图..."),
    ResourceAgentDescriptor("quiz", "练习题", "Quiz", "练习习题", "base", "json", 600, "开始生成随堂练习题..."),
    ResourceAgentDescriptor("code", "代码示例", "Code", "代码实操案例", "base", "markdown", 600, "开始生成代码实操案例..."),
    ResourceAgentDescriptor("reading", "拓展阅读", "Reading", "拓展阅读推荐", "base", "json", 600, "开始生成拓展阅读资源..."),
    ResourceAgentDescriptor("ppt", "PPT文稿", "DataBoard", "PPT文稿生成", "aggregation", "pptx", 1800, "开始生成教学课件..."),
    ResourceAgentDescriptor("cartoon", "动画讲解", "FilmStrip", "知识点动画、配音与字幕同步的 MP4 教学视频", "aggregation", "mp4", 1800, "开始生成动画讲解视频..."),
)

AGENT_BY_ID = {agent.agent_id: agent for agent in RESOURCE_AGENTS}
AGENT_DEFAULT_ORDER = tuple(agent.agent_id for agent in RESOURCE_AGENTS)
AGENT_DEFAULT_ENABLED = AGENT_DEFAULT_ORDER
BASE_RESOURCE_AGENT_IDS = frozenset(agent.agent_id for agent in RESOURCE_AGENTS if agent.kind == "base")
AGGREGATION_AGENT_IDS = tuple(agent.agent_id for agent in RESOURCE_AGENTS if agent.kind == "aggregation")
AGENT_CONTENT_FORMAT = {agent.agent_id: agent.content_format for agent in RESOURCE_AGENTS}

