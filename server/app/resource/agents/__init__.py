"""Resource 模块智能体对外导出与 Path 模块轻量桥接定义 (app.resource.agents)。"""

from __future__ import annotations

from typing import Any
from app.infra.llm import LLM


class PathAgentAdapter:
    """供 Path 学习路径模块调用的轻量无状态桥接对象。"""

    def __init__(self, role: str = "学科专家") -> None:
        """初始化适配器与推理 LLM 实例及课件生成器。"""
        self.role = role
        self.llm = LLM(temperature=0.3)
        from app.shared.ppt.agent import PPTAgent as _SharedPPTAgent

        self._generator: Any = _SharedPPTAgent()

    async def generate_for_path(self, request: Any) -> Any:
        """为学习路径节点生成针对性的辅助资源。"""
        tutorial = getattr(request, "tutorial", None)
        node_title = getattr(request, "node_title", "学习节点")
        context_text = getattr(tutorial, "content_markdown", "") if tutorial else ""
        prompt = f"围绕节点【{node_title}】，基于以下教程内容生成高质量教学辅助内容：\n{context_text[:1500]}"
        response = await self.llm.text(prompt)
        from app.resource.schemas import AgentResult

        return AgentResult(
            success=True,
            title=f"{node_title} 辅助材料",
            file_type="markdown",
            content=response,
            summary=f"成功为节点 {node_title} 生成辅助材料",
        )

    async def generate_resource(self, input: Any, **kwargs: Any) -> Any:
        """资源生成兼容入口。"""
        from app.resource.schemas import AgentResult

        if hasattr(input, "learning_need") or hasattr(input, "teaching_plan"):
            from uuid import uuid4
            from app.config import user_resource_ppt_dir
            from app.shared.ppt.schemas import PPTBrief, PPTGenerationError

            target_dir = user_resource_ppt_dir(getattr(input, "username", "alice"), uuid4().hex)
            brief = PPTBrief(
                title=getattr(input, "learning_need", "教学课件"),
                context=getattr(input, "learning_need", ""),
            )
            try:
                artifact = await self._generator.generate(brief, target_dir)
                return AgentResult(
                    success=True,
                    title=artifact.title,
                    file_type="pptx",
                    content="",
                    summary=f"成功生成课件 {artifact.title}",
                    metadata=artifact.metadata(),
                )
            except PPTGenerationError as exc:
                return AgentResult(
                    success=False,
                    title="课件制作失败",
                    file_type="pptx",
                    error=str(exc),
                    metadata={"generation_stage": getattr(exc, "stage", "failed")},
                )
        return await self.generate_for_path(input)


def _create_agent_factory(role: str) -> Any:
    """创建工厂函数以支持无参数实例化。"""
    return lambda *args, **kwargs: PathAgentAdapter(role=role)


ContentAgent = _create_agent_factory("资深课程讲师")
MindmapAgent = _create_agent_factory("知识体系架构师")
QuizAgent = _create_agent_factory("教学测评出题专家")
CodeAgent = _create_agent_factory("资深软件研发专家")
ReadingAgent = _create_agent_factory("学科文献策展人")
PptAgent = _create_agent_factory("课件制作专家")
PPTAgent = PptAgent
CartoonAgent = _create_agent_factory("动画讲解专家")
PlanningAgent = _create_agent_factory("课程规划主专家")
PlanAgent = PlanningAgent

AGENT_REGISTRY: dict[str, Any] = {
    "planning": PlanningAgent,
    "planner": PlanAgent,
    "content": ContentAgent,
    "mindmap": MindmapAgent,
    "quiz": QuizAgent,
    "code": CodeAgent,
    "reading": ReadingAgent,
    "ppt": PptAgent,
    "cartoon": CartoonAgent,
}

__all__ = [
    "AGENT_REGISTRY",
    "ContentAgent",
    "MindmapAgent",
    "QuizAgent",
    "CodeAgent",
    "ReadingAgent",
    "PptAgent",
    "PPTAgent",
    "CartoonAgent",
    "PlanningAgent",
    "PlanAgent",
]
