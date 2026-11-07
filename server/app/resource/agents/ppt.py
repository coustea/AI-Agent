"""Resource-owned input mapping for the PPT harness."""
import json
from app.config import user_resource_ppt_dir
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import AgentResult, ResourceInput
from app.shared.ppt import PPTAgent as Generator, PPTBrief, PPTGenerationError, PPTPreferences

@register_agent
class PPTAgent(BaseResourceAgent):
    agent_id = "ppt"
    agent_name = "演示幻灯"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._generator = Generator()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        if input_data.teaching_plan is None:
            return AgentResult(success=False, title="PPT 生成失败", file_type="pptx",
                               error="缺少教学计划", metadata={"agent_id": "ppt"})
        brief = PPTBrief(
            title=input_data.learning_need,
            context=json.dumps({"plan": input_data.teaching_plan.model_dump(mode="json"),
                                "materials": {k: v.model_dump(mode="json") for k, v in input_data.upstream_handoffs.items()},
                                "profile": input_data.profile, "scenario": input_data.learning_scenario}, ensure_ascii=False),
            preferences=PPTPreferences.model_validate(input_data.agent_config),
        )
        async def progress(message: str, percent: int) -> None:
            await self.emitter.send(self.agent_id, "running", message, percent)
        try:
            artifact = await self.run_with_heartbeat(
                self._generator.generate(brief, user_resource_ppt_dir(input_data.username or "anonymous", str(input_data.resource_id or "default")), progress=progress),
                messages=["正在设计课件内容与版式", "正在生成并检查课件页面"], interval_seconds=15, progress=70,
            )
            return AgentResult(success=True, title=artifact.title, file_type="pptx",
                               summary=f"生成 {artifact.slide_count} 页教学课件", metrics={"slide_count": artifact.slide_count},
                               metadata=artifact.metadata())
        except PPTGenerationError as exc:
            return AgentResult(success=False, title="PPT 生成失败", file_type="pptx", error=str(exc),
                               metadata={"agent_id": "ppt", "generation_stage": exc.stage})
