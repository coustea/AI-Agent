"""PPT 智能体 — 生成演示文稿大纲和内容。"""

from __future__ import annotations

import json

from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import build_worker_base_context, salvage_json_from_llm
from app.resource.schemas import WorkerResult, WorkerState


@register_agent
class PptAgent(BaseResourceAgent):
    """基于教学蓝图生成 PPT 大纲和内容。"""

    agent_id = "ppt"
    agent_name = "PPT 生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, state: WorkerState) -> WorkerResult:
        from app.prompts import registry

        parts = build_worker_base_context(state)
        config = state.agent_config
        if config:
            cfg = ["## PPT 配置"]
            cfg.append(f"- 页数范围: {config.get('slide_count', '8-12')}")
            cfg.append(f"- 设计风格: {config.get('style', 'professional')}")
            cfg.append(f"- 主题色: {config.get('theme_color', 'blue')}")
            cfg.append("- 包含动画效果" if config.get("include_animation", False) else "- 不包含动画效果")
            parts.append("\n".join(cfg))
        parts.append("请生成 PPT 演示文稿内容，以 JSON 格式输出幻灯片列表。")

        prompt = registry.get("resource/ppt")
        full_input = f"{prompt}\n\n{'\n\n'.join(parts)}"

        try:
            from pydantic import BaseModel, Field

            class PptSlide(BaseModel):
                slide_number: int = Field(description="幻灯片序号")
                title: str = Field(description="幻灯片标题")
                content: str = Field(description="幻灯片内容（Markdown）")
                notes: str = Field(default="", description="演讲者备注")

            class PptPayload(BaseModel):
                title: str = Field(description="演示文稿标题")
                theme: str = Field(default="professional", description="设计主题")
                slides: list[PptSlide] = Field(default_factory=list, description="幻灯片列表")

            result = await self.llm.ainvoke_json(
                PptPayload,
                full_input,
                temperature=0.3,
                function_name="generate_ppt",
                function_description="生成PPT大纲",
            )
            ppt_data = result.model_dump(mode="json")
            content = json.dumps(ppt_data, ensure_ascii=False, indent=2)
        except Exception as exc:
            response = await self.llm.ainvoke(full_input, temperature=0.3)
            raw = response.content if hasattr(response, "content") else str(response)
            ppt_data = salvage_json_from_llm(raw, require_key="slides")
            if ppt_data is None:
                return WorkerResult(success=False, error=f"PPT JSON 解析失败: {exc}")
            content = json.dumps(ppt_data, ensure_ascii=False, indent=2)

        slides = ppt_data.get("slides", []) if isinstance(ppt_data, dict) else []

        return WorkerResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{state.learning_need[:32]} - PPT",
            summary=f"生成 {len(slides)} 页 PPT 大纲",
            summary_data={"slide_count": len(slides)},
            metadata={"engine": "ppt_json", "agent_id": "ppt"},
        )
