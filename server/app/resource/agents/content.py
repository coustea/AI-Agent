"""
内容智能体 — 生成专业课程讲解文档。
"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.prompts import registry
from app.resource.events import AgentEventEmitter
from app.resource.schemas import WorkerResult, WorkerState
from app.resource.utils import format_learner_profile_for_prompt

logger = get_logger(__name__)


class ContentAgent:
    """基于知识图谱生成课程讲解文档。"""

    def __init__(self, emitter: AgentEventEmitter):
        self.emitter = emitter
        self.llm = get_llm()

    async def run(self, state: WorkerState) -> WorkerResult:
        await self.emitter.emit_agent("content", status="running", message="正在生成课程内容")

        prompt = registry.get("resource/content")
        input_text = self._build_input(state)

        response = await self.llm.ainvoke(
            f"{prompt}\n\n{input_text}",
            temperature=0.3,
        )
        content = response.content if hasattr(response, "content") else str(response)
        content = self._clean_content(content)

        await self.emitter.emit_agent("content", status="success", message="课程内容生成完成")
        return WorkerResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{state.learning_need[:32]} - 课程内容",
            summary="生成专业课程讲解文档",
            summary_data={"char_count": len(content)},
            metadata={"agent_id": "content"},
        )

    def _build_input(self, state: WorkerState) -> str:
        parts = [f"## 学习需求\n{state.learning_need}"]

        # 学习者画像（首要依据）
        profile_text = format_learner_profile_for_prompt(state.profile)
        if profile_text:
            parts.append(f"## 学习者画像摘要\n{profile_text}")

        if state.knowledge_graph:
            parts.append(f"## 知识图谱\n{state.knowledge_graph.model_dump_json(indent=2)}")

        if state.instruction:
            lines = [f"## 规划师指令\n- 重点: {state.instruction.focus}"]
            if state.instruction.difficulty:
                lines.append(f"- 难度: {state.instruction.difficulty}")
            if state.instruction.personalization_notes:
                lines.append(f"- 个性化建议: {state.instruction.personalization_notes}")
            for c in state.instruction.constraints:
                lines.append(f"- 约束: {c}")
            parts.append("\n".join(lines))

        # Content-specific config
        config = state.agent_config
        if config:
            cfg_lines = ["## 内容配置"]
            cfg_lines.append(f"- 结构: {config.get('structure', 'progressive')}")
            cfg_lines.append(f"- 深度: {config.get('depth_level', 'standard')}")
            cfg_lines.append(f"- 关注模式: {config.get('focus_mode', 'key_concepts')}")
            cfg_lines.append(
                "- 包含示例和代码说明" if config.get("include_examples", True) else "- 不包含示例"
            )
            cfg_lines.append(
                "- 包含常见误区和易错点" if config.get("include_common_mistakes", True) else "- 不包含常见误区"
            )
            parts.append("\n".join(cfg_lines))

        parts.append("请生成专业课程讲解文档，只输出 Markdown 内容。")
        return "\n\n".join(parts)

    def _clean_content(self, content: str) -> str:
        """清理内容中的常见问题。"""
        lines = content.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if stripped in ("```", "```markdown", "```text"):
                continue
            cleaned.append(line)
        return "\n".join(cleaned)