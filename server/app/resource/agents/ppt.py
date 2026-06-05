"""PPT 智能体 — 生成演示文稿大纲和内容。"""

from __future__ import annotations

import json

from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import WorkerResult, WorkerState


@register_agent
class PptAgent(BaseResourceAgent):
    """基于教学蓝图生成 PPT 大纲和内容。"""

    agent_id = "ppt"
    agent_name = "PPT 生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        from app.prompts import registry

        config = state.agent_config
        if config:
            cfg = ["## PPT 配置"]
            cfg.append(f"- 页数范围: {config.get('slide_count', '8-12')}")
            cfg.append(f"- 设计风格: {config.get('style', 'professional')}")
            cfg.append(f"- 主题色: {config.get('theme_color', 'blue')}")
            cfg.append("- 包含动画效果" if config.get("include_animation", False) else "- 不包含动画效果")
            input_text += f"\n\n{chr(10).join(cfg)}"
        input_text += "\n\n请生成 PPT 演示文稿内容，以 JSON 格式输出幻灯片列表。"

        prompt = registry.get("resource/ppt")
        full_input = f"{prompt}\n\n{input_text}"

        from pydantic import BaseModel as _Base, Field as _Field

        class PptSlide(_Base):
            slide_number: int = _Field(description="幻灯片序号")
            title: str = _Field(description="幻灯片标题")
            content: str = _Field(description="幻灯片内容（Markdown）")
            notes: str = _Field(default="", description="演讲者备注")

        class PptPayload(_Base):
            title: str = _Field(description="演示文稿标题")
            theme: str = _Field(default="professional", description="设计主题")
            slides: list[PptSlide] = _Field(default_factory=list, description="幻灯片列表")

        result = await self.llm.ainvoke_json(
            PptPayload,
            full_input,
            temperature=0.3,
            function_name="generate_ppt",
            function_description="生成PPT结构",
        )
        ppt_data = result.model_dump(mode="json")
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