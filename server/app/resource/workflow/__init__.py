"""资源域 LangGraph 工作流 — 全局编排图和状态定义。"""

# 仅对外暴露全局编排图构建函数
from app.resource.workflow.graph import build_parent_graph

__all__ = ["build_parent_graph"]
