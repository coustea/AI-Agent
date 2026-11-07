"""Learning-path-owned adapter for the PPT harness."""
from app.config import user_path_node_ppt_dir
from app.path.schemas import PathResourceRequest
from app.resource.schemas import AgentResult
from app.shared.ppt import PPTAgent, PPTBrief, PPTGenerationError

class PathPPTAdapter:
    async def generate(self, request: PathResourceRequest) -> AgentResult:
        tutorial = request.tutorial
        if tutorial is None or not tutorial.content_markdown.strip():
            return AgentResult(success=False, title="PPT 生成失败", file_type="pptx", error="缺少教程正文")
        brief = PPTBrief(title=request.node_title, context=f"路径：{request.path_title}\n目标：{request.path_goal}\n难度：{request.difficulty}\n薄弱点：{tutorial.weak_knowledge_points}\n{tutorial.content_markdown}")
        try:
            artifact = await PPTAgent().generate(brief, user_path_node_ppt_dir(request.username, str(request.path_id), str(request.node_id)))
            return AgentResult(success=True, title=artifact.title, file_type="pptx",
                               summary=f"生成 {artifact.slide_count} 页教学课件", metrics={"slide_count": artifact.slide_count},
                               metadata=artifact.metadata())
        except PPTGenerationError as exc:
            return AgentResult(success=False, title="PPT 生成失败", file_type="pptx", error=str(exc),
                               metadata={"agent_id": "ppt", "generation_stage": exc.stage})
