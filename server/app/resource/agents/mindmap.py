"""思维导图智能体 — 生成 Markdown 知识结构图，返回给前端 Markmap 渲染。"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import WorkerResult, WorkerState


@register_agent
class MindmapAgent(BaseResourceAgent):
    """基于教学蓝图生成 Markmap 思维导图。"""

    agent_id = "mindmap"
    agent_name = "思维导图生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        from app.prompts import registry

        config = state.agent_config
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

        prompt = registry.get("resource/mindmap")
        response = await self.llm.ainvoke(f"{prompt}\n\n{input_text}", temperature=0.3)
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

        return WorkerResult(
            success=True,
            content=content,
            file_type="markdown",
            title=f"{state.learning_need[:32]} - 思维导图",
            summary="生成 Markmap 思维导图 Markdown",
            summary_data={
                "central_topic": state.learning_need[:50],
                "branches": list(dict.fromkeys(branches))[:8],
                "weak_points": list(dict.fromkeys(weak_points))[:8],
            },
            metadata={"engine": "markmap", "render_at": "frontend", "agent_id": "mindmap"},
        )


def _clean_markdown(content: str) -> str:
    lines = content.split("\n")
    return "\n".join(
        line for line in lines
        if line.strip() not in ("```", "```markdown", "```text", "```mermaid")
        and not line.strip().startswith("```mermaid")
    )
