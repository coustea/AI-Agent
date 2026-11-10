"""学习路径文本型辅助资源生成适配器 (app.path.text_resource)。

为学习路径节点生成针对性的 mindmap / code / reading 等辅助教学正文。
"""

from __future__ import annotations

from typing import Any

from app.infra.llm import LLM
from app.resource.schemas import AgentResult


class PathTextResourceAdapter:
    """学习路径节点轻量文本辅助资源（思维导图、代码实操、拓展阅读）生成适配器。"""

    def __init__(self, resource_type: str = "mindmap") -> None:
        """初始化文本资源适配器与推理 LLM 实例。"""
        self.resource_type = resource_type
        self.llm = LLM(temperature=0.3)

    async def generate_for_path(self, request: object) -> AgentResult:
        """为学习路径节点生成针对性的辅助资源 Markdown 正文。"""
        tutorial = getattr(request, "tutorial", None)
        node_title = getattr(request, "node_title", "学习节点")
        context_text = getattr(tutorial, "content_markdown", "") if tutorial else ""
        prompt = (
            f"围绕节点【{node_title}】（类型：{self.resource_type}），基于以下教程内容生成高质量教学辅助内容：\n"
            f"{context_text[:1500]}"
        )
        response = await self.llm.text(prompt)
        return AgentResult(
            success=True,
            title=f"{node_title} 辅助材料",
            file_type="markdown",
            content=response,
            summary=f"成功为节点 {node_title} 生成 {self.resource_type} 辅助材料",
        )


__all__ = ["PathTextResourceAdapter"]
