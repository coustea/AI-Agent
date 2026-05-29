"""
PPT 智能体 — 生成幻灯片内容 JSON 供前端渲染。
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.prompts import registry
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import build_worker_base_context
from app.resource.events import AgentEventEmitter
from app.resource.schemas import WorkerResult, WorkerState

logger = get_logger(__name__)


class SlideContent(BaseModel):
    heading: str = Field(description="幻灯片标题")
    bullets: list[str] = Field(default_factory=list, description="要点列表")
    notes: str = Field(default="", description="演讲者备注")


class PptPayload(BaseModel):
    title: str = Field(description="PPT 标题")
    theme: str = Field(default="education", description="主题风格")
    slides: list[SlideContent] = Field(default_factory=list, description="幻灯片列表")


@register_agent
class PptAgent(BaseResourceAgent):
    """基于教学蓝图生成 PPT 幻灯片内容。"""

    agent_id = "ppt"
    agent_name = "PPT生成"

    def __init__(self, emitter: AgentEventEmitter | None = None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        await self.emitter.emit_agent("ppt", status="running", message="正在准备PPT", progress=0)
        await self.emitter.emit_agent_action(
            "ppt", "outline", detail="正在规划幻灯片大纲",
            current_step=1, total_steps=4, step_label="规划大纲", progress=10,
        )

        prompt = registry.get("resource/ppt")
        full_prompt = f"{prompt}\n\n{input_text}\n\n请生成 PPT 内容，以 JSON 格式输出。"

        await self.emitter.emit_agent_action(
            "ppt", "generate", detail="正在生成幻灯片内容",
            current_step=2, total_steps=4, step_label="生成内容", progress=35,
        )

        try:
            result = await self.llm.ainvoke_json(
                PptPayload,
                full_prompt,
                temperature=0.3,
                function_name="generate_ppt",
                function_description="生成 PPT 幻灯片内容",
            )
            ppt_data = result.model_dump(mode="json")
            content = json.dumps(ppt_data, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("[PptAgent] 结构化输出失败，尝试 JSON 文本解析: %s", exc)

            await self.emitter.emit_agent_action(
                "ppt", "fallback", detail="正在重新整理PPT格式",
                current_step=3, total_steps=4, step_label="格式整理", progress=55,
            )

            response = await self.llm.ainvoke(full_prompt, temperature=0.3)
            raw = response.content if hasattr(response, "content") else str(response)
            ppt_data = self._salvage_ppt_payload(raw)
            if ppt_data is None:
                return WorkerResult(success=False, error=f"PPT JSON 解析失败: {exc}")
            content = json.dumps(ppt_data, ensure_ascii=False, indent=2)

        slide_count = len(ppt_data.get("slides", []))

        await self.emitter.emit_agent_action(
            "ppt", "done", detail=f"已生成 {slide_count} 页幻灯片",
            current_step=4, total_steps=4, step_label="生成完成", progress=100,
        )
        await self.emitter.emit_agent("ppt", status="success", message=f"已生成 {slide_count} 页幻灯片", progress=100)
        return WorkerResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{state.learning_need[:32]} - PPT",
            summary=f"生成 {slide_count} 页幻灯片",
            summary_data={"slide_count": slide_count},
            metadata={
                "engine": "ppt_json",
                "slide_count": slide_count,
                "agent_id": "ppt",
            },
        )

    def _build_input_override(self, state: WorkerState) -> str:
        parts = build_worker_base_context(state)
        config = state.agent_config
        if config:
            cfg_lines = ["## PPT配置"]
            cfg_lines.append(f"- 幻灯片数量: {config.get('slide_count', 10)}")
            cfg_lines.append(f"- 风格: {config.get('style', 'teaching')}")
            cfg_lines.append(f"- 主题: {config.get('theme', 'education')}")
            parts.append("\n".join(cfg_lines))
        parts.append("请生成 PPT 幻灯片内容。")
        return "\n\n".join(parts)

    async def run(self, state: WorkerState) -> WorkerResult:
        input_text = self._build_input_override(state)
        return await self._execute(input_text, state)

    def _salvage_ppt_payload(self, raw: str) -> dict | None:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "slides" in data:
                return data
        except json.JSONDecodeError:
            pass

        pattern = r"```(?:json)?\s*\n(.*?)```"
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict) and "slides" in data:
                    return data
            except json.JSONDecodeError:
                pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start:end + 1])
                if isinstance(data, dict) and "slides" in data:
                    return data
            except json.JSONDecodeError:
                pass

        return None