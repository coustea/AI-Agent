"""
思维导图 Agent — 生成 Markdown 知识结构图，返回给前端渲染。
"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import Agent
from app.resource.schemas import WorkerResult, WorkerState
from app.resource.utils import learning_need_from_task

logger = get_logger(__name__)


class MindmapAgent(Agent):
    """思维导图 Agent。"""

    AGENT_NAME = "mindmap"
    ROLE_NAME = "知识结构图谱智能体"
    STEPS = ["分析输入", "融合画像与依赖", "生成内容", "整理输出"]

    def _default_template_values(self) -> dict[str, str]:
        return {
            "map_type": "knowledge_tree",
            "max_depth": "4",
            "highlight_weak_instruction": "高亮标注薄弱知识点",
            "expand_weak_instruction": "不展开薄弱点",
            "prerequisites_instruction": "不包含前置知识",
        }

    def _resolve_template_variables(self, variables: set, state: WorkerState) -> dict[str, str]:
        """Mindmap Agent 特殊变量解析。"""
        result = super()._resolve_template_variables(variables, state)
        config = state.agent_config or {}

        if "highlight_weak_instruction" in variables:
            result["highlight_weak_instruction"] = "用粗体高亮标注薄弱知识点" if config.get("highlight_weak", True) else "不高亮薄弱知识点"
        if "expand_weak_instruction" in variables:
            result["expand_weak_instruction"] = "展开薄弱点的详细内容" if config.get("expand_weak_points", False) else "不展开薄弱点"
        if "prerequisites_instruction" in variables:
            result["prerequisites_instruction"] = "包含前置知识节点" if config.get("include_prerequisites", False) else "不包含前置知识"

        return result

    async def _generate(self, state: WorkerState, prompt: str, input_text: str) -> WorkerResult:
        llm = get_llm()
        response = await llm.ainvoke(
            f"{prompt}\n\n{input_text}",
            temperature=0.3,
        )

        content = response.content if hasattr(response, "content") else str(response)
        markdown = self._extract_markdown(content)

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
            "central_topic": learning_need_from_task(state.task)[:50],
            "branches": list(dict.fromkeys(branches))[:8],
            "weak_points": list(dict.fromkeys(weak_points))[:8],
            "map_type": state.agent_config.get("map_type", "knowledge_tree"),
        }

        return WorkerResult(
            success=True,
            content=markdown,
            file_type="markdown",
            title=self._title(state, "思维导图"),
            summary="生成 Markmap 思维导图 Markdown",
            summary_data=summary_data,
            metadata={
                "engine": "markmap",
                "render_at": "frontend",
                "map_type": state.agent_config.get("map_type", "knowledge_tree"),
                "agent_id": "mindmap",
            },
        )

    def _input_suffix(self) -> str:
        return "请生成思维导图，只输出 Markdown 内容。"