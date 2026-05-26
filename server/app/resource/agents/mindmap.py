"""
思维导图智能体 — 生成 Markdown 知识结构图，返回给前端 Markmap 渲染。
"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.prompts import registry
from app.resource.events import AgentEventEmitter
from app.resource.schemas import WorkerResult, WorkerState
from app.resource.utils import format_learner_profile_for_prompt

logger = get_logger(__name__)


class MindmapAgent:
    """基于教学蓝图生成 Markmap 思维导图。"""

    def __init__(self, emitter: AgentEventEmitter):
        self.emitter = emitter
        self.llm = get_llm()

    async def run(self, state: WorkerState) -> WorkerResult:
        await self.emitter.emit_agent("mindmap", status="running", message="正在准备思维导图", progress=0)
        await self.emitter.emit_agent_action(
            "mindmap", "extract", detail="正在提取知识要点",
            current_step=1, total_steps=3, step_label="提取要点", progress=15,
        )

        prompt = registry.get("resource/mindmap")
        input_text = self._build_input(state)

        await self.emitter.emit_agent_action(
            "mindmap", "generate", detail="正在构建思维导图结构",
            current_step=2, total_steps=3, step_label="构建结构", progress=45,
        )

        response = await self.llm.ainvoke(
            f"{prompt}\n\n{input_text}",
            temperature=0.3,
        )
        content = response.content if hasattr(response, "content") else str(response)
        markdown = self._clean_markdown(content)

        # 提取分支和薄弱点
        branches: list[str] = []
        weak_points: list[str] = []
        for line in markdown.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                branches.append(stripped.lstrip("#").strip())
            elif stripped.startswith("- "):
                item = stripped[2:].strip()
                if any(token in item for token in ("易错", "误区", "难点", "薄弱")):
                    weak_points.append(item)

        summary_data = {
            "central_topic": state.learning_need[:50],
            "branches": list(dict.fromkeys(branches))[:8],
            "weak_points": list(dict.fromkeys(weak_points))[:8],
            "map_type": state.agent_config.get("map_type", "knowledge_tree"),
        }

        await self.emitter.emit_agent_action(
            "mindmap", "done", detail="思维导图生成完成",
            current_step=3, total_steps=3, step_label="生成完成", progress=100,
        )
        await self.emitter.emit_agent("mindmap", status="success", message="思维导图生成完成", progress=100)
        return WorkerResult(
            success=True,
            content=markdown,
            file_type="markdown",
            title=f"{state.learning_need[:32]} - 思维导图",
            summary="生成 Markmap 思维导图 Markdown",
            summary_data=summary_data,
            metadata={
                "engine": "markmap",
                "render_at": "frontend",
                "map_type": state.agent_config.get("map_type", "knowledge_tree"),
                "agent_id": "mindmap",
            },
        )

    def _build_input(self, state: WorkerState) -> str:
        parts = [f"## 学习需求\n{state.learning_need}"]

        # 学习者画像（首要依据）
        profile_text = format_learner_profile_for_prompt(state.profile)
        if profile_text:
            parts.append(f"## 学习者画像摘要\n{profile_text}")

        if state.blueprint:
            parts.append(f"## 教学蓝图\n{state.blueprint.model_dump_json(indent=2)}")

        if state.instruction:
            lines = [f"## 规划师指令\n- 重点: {state.instruction.focus}"]
            for c in state.instruction.constraints:
                lines.append(f"- 约束: {c}")
            parts.append("\n".join(lines))

        # Mindmap-specific config
        config = state.agent_config
        if config:
            cfg_lines = ["## 思维导图配置"]
            cfg_lines.append(f"- 导图类型: {config.get('map_type', 'knowledge_tree')}")
            cfg_lines.append(f"- 最大深度: {config.get('max_depth', 4)}")
            cfg_lines.append(
                "- 用粗体高亮标注薄弱知识点" if config.get("highlight_weak", True) else "- 不高亮薄弱知识点"
            )
            cfg_lines.append(
                "- 展开薄弱点的详细内容" if config.get("expand_weak_points", False) else "- 不展开薄弱点"
            )
            cfg_lines.append(
                "- 包含前置知识节点" if config.get("include_prerequisites", False) else "- 不包含前置知识"
            )
            parts.append("\n".join(cfg_lines))

        parts.append("请生成思维导图，只输出 Markdown 内容。")
        return "\n\n".join(parts)

    def _clean_markdown(self, content: str) -> str:
        """清理 Markdown 外壳。"""
        lines = content.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if stripped in ("```", "```markdown", "```text"):
                continue
            cleaned.append(line)
        return "\n".join(cleaned)