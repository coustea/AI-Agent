"""思维导图智能体 — 生成 Markdown 知识结构图，返回给前端 Markmap 渲染。"""

from __future__ import annotations

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import (
    build_basic_handoff,
    build_node_context,
    build_resource_context,
    assigned_outline_ids,
)
from app.infra.prompts import prompts
from app.resource.schemas import AgentResult, NodeInput, ResourceInput

logger = get_logger(__name__)


@register_agent
class MindmapAgent(BaseResourceAgent):
    """基于教学蓝图生成 Markmap 思维导图（标准 Markdown 标题+列表格式）。"""

    agent_id = "mindmap"
    agent_name = "思维导图生成"

    def __init__(self, events=None, emitter=None):
        super().__init__(events=events, emitter=emitter)
        self.llm = get_llm()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        config = {
            **input_data.agent_config,
            "_teaching_plan": input_data.teaching_plan,
        }
        result = await self._generate_mindmap(
            input_text="\n\n".join(build_resource_context(input_data)),
            title_prefix=input_data.learning_need[:32],
            config=config,
        )
        branches = result.metrics.get("branches", [])
        outline_ids = assigned_outline_ids(input_data.teaching_plan, "mindmap")
        handoff = build_basic_handoff(
            source_agent="mindmap",
            title=result.title,
            summary=result.summary,
            teaching_plan=input_data.teaching_plan,
            covered_outline_ids=outline_ids,
            visual_ideas=branches,
        )
        result.downstream_context = handoff
        await self.events.send_agent_status(self.agent_id, status="completed" if result.success else "failed", message=result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), progress=100 if result.success else 0)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        result = await self._generate_mindmap(
            input_text="\n\n".join(build_node_context(input_data)),
            title_prefix=input_data.node_title,
            config=input_data.agent_config,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.events.send_agent_status(self.agent_id, status="completed" if result.success else "failed", message=result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), progress=100 if result.success else 0)
        return result

    async def _generate_mindmap(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
        """内部方法 — 调用 LLM 生成 Markmap 思维导图 Markdown。"""
        if config:
            cfg = ["## 思维导图配置"]
            cfg.append(f"- 导图类型: {config.get('map_type', 'knowledge_tree')}")
            cfg.append(f"- 最大深度: {config.get('max_depth', 4)}")
            cfg.append("- 用粗体高亮标注薄弱知识点" if config.get("highlight_weak", True) else "- 不高亮薄弱知识点")
            input_text += f"\n\n{chr(10).join(cfg)}"
        input_text += (
            "\n\n请务必使用 `#` 一级标题、`##` 二级标题和 `-` 列表符号来构建导图结构。\n"
            "【注意】绝对不要使用 Mermaid 语法！请只输出标准的 Markdown 标题和列表文本。"
        )

        await self.events.send_agent_step(self.agent_id, phase="start", message="正在构建知识导图提示词", progress=25)
        prompt = prompts.get("resource").get("mindmap")
        response = await self.llm.ainvoke(f"{prompt}\n\n{input_text}", temperature=INFERENCE_TEMPERATURE)
        content = response.content if hasattr(response, "content") else str(response)
        content = _clean_markdown(content)

        branches: list[str] = []
        weak_points: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                branches.append(stripped.lstrip("#").strip())
            elif stripped.startswith("- "):
                item = stripped[2:].strip()
                if any(token in item for token in ("易错", "误区", "难点", "薄弱")):
                    weak_points.append(item)

        return AgentResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{title_prefix} - 思维导图",
            summary="生成 Markmap 思维导图 Markdown",
            metrics={
                "central_topic": title_prefix[:50],
                "branches": list(dict.fromkeys(branches))[:8],
                "weak_points": list(dict.fromkeys(weak_points))[:8],
            },
            metadata={"engine": "markmap", "render_at": "frontend", "agent_id": "mindmap"},
        )


def _clean_markdown(content: str) -> str:
    """清理 LLM 输出中的 markdown fence 和 mermaid 标记。"""
    lines = content.split("\n")
    return "\n".join(
        line for line in lines
        if line.strip() not in ("```", "```markdown", "```text", "```mermaid")
        and not line.strip().startswith("```mermaid")
    )
