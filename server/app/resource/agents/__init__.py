"""Path 模块调用简单文本型资源智能体的无状态桥接层 (app.resource.agents)。

Path 节点的 mindmap / code / reading 三类辅助资源只需要「给提示词 → 拿 Markdown」，
因此这里直接用同一个适配器承载，不同角色通过构造参数区分。
"""

from __future__ import annotations

from app.infra.llm import LLM
from app.resource.schemas import AgentResult


class PathAgentAdapter:
    """供 Path 学习路径模块调用的轻量无状态桥接对象。"""

    def __init__(self) -> None:
        """初始化适配器与推理 LLM 实例。"""
        self.llm = LLM(temperature=0.3)

    async def generate_for_path(self, request: object) -> AgentResult:
        """为学习路径节点生成针对性的辅助资源。"""
        tutorial = getattr(request, "tutorial", None)
        node_title = getattr(request, "node_title", "学习节点")
        context_text = getattr(tutorial, "content_markdown", "") if tutorial else ""
        prompt = (
            f"围绕节点【{node_title}】，基于以下教程内容生成高质量教学辅助内容：\n"
            f"{context_text[:1500]}"
        )
        response = await self.llm.text(prompt)
        return AgentResult(
            success=True,
            title=f"{node_title} 辅助材料",
            file_type="markdown",
            content=response,
            summary=f"成功为节点 {node_title} 生成辅助材料",
        )


# 三类文本型资源共用同一适配器，Path 模块按 key 取用
MindmapAgent = PathAgentAdapter
CodeAgent = PathAgentAdapter
ReadingAgent = PathAgentAdapter

AGENT_REGISTRY: dict[str, type[PathAgentAdapter]] = {
    "mindmap": MindmapAgent,
    "code": CodeAgent,
    "reading": ReadingAgent,
}

__all__ = [
    "AGENT_REGISTRY",
    "CodeAgent",
    "MindmapAgent",
    "PathAgentAdapter",
    "ReadingAgent",
]
