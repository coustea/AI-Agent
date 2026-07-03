"""资源生成智能体 — 通过 @register_agent 装饰器自动注册。

每个 agent 实现 BaseResourceAgent 的 generate_resource 和 generate_node 方法，
通过全局 AGENT_REGISTRY 字典按 agent_id 查找调用。
"""

# 基类、注册表和注册装饰器
from app.resource.agents.base import AGENT_REGISTRY, BaseResourceAgent, register_agent

# 导入所有 agent 以触发 @register_agent 注册 — 模块加载时自动调用装饰器

# 规划 Agent：分析学习需求，生成全局教学大纲
from app.resource.agents.planning import PlanningAgent

# 内容 Agent：生成专业课程讲解文档
from app.resource.agents.content import ContentAgent

# 习题 Agent：生成选择题/判断题等结构化习题
from app.resource.agents.quiz import QuizAgent

# 思维导图 Agent：生成 Markmap 格式知识结构图
from app.resource.agents.mindmap import MindmapAgent

# 代码 Agent：生成教学示例代码
from app.resource.agents.code import CodeAgent

# 阅读 Agent：生成拓展阅读材料（含真实 URL）
from app.resource.agents.reading import ReadingAgent

# 课件 Agent：生成教学 PPT
from app.resource.agents.ppt import PPTAgent

# 视频 Agent：生成最终 MP4 讲解视频
from app.resource.agents.video import VideoAgent

# 动画讲解 Agent：使用 HyperFrames 生成带配音与字幕的 MP4
from app.resource.agents.cartoon import CartoonAgent

# 模块公开导出列表
__all__ = [
    # 全局 agent 注册表字典
    "AGENT_REGISTRY",
    # Agent 基类，所有具体 Agent 继承此类
    "BaseResourceAgent",
    # 注册装饰器，将 Agent 类加入 AGENT_REGISTRY
    "register_agent",
    # 规划 Agent
    "PlanningAgent",
    # 内容 Agent
    "ContentAgent",
    # 习题 Agent
    "QuizAgent",
    # 思维导图 Agent
    "MindmapAgent",
    # 代码 Agent
    "CodeAgent",
    # 阅读 Agent
    "ReadingAgent",
    # 课件 Agent
    "PPTAgent",
    # 视频 Agent
    "VideoAgent",
    # 动画讲解 Agent
    "CartoonAgent",
]
