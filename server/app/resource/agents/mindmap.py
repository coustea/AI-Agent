"""思维导图智能体 — 生成 Markdown 知识结构图，返回给前端 Markmap 渲染。"""

from __future__ import annotations

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.infra.prompts import prompts
from app.resource.schemas import WorkerResult, WorkerState

logger = get_logger(__name__)


@register_agent
class MindmapAgent(BaseResourceAgent):
    """基于教学蓝图生成 Markmap 思维导图（标准 Markdown 标题+列表格式）。"""

    agent_id = "mindmap"
    agent_name = "思维导图生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        """核心生成逻辑：拼接导图配置 → LLM 生成 → 解析分支和薄弱点。"""
        config = state.agent_config
        # 拼接思维导图配置（类型、深度、高亮模式）
        if config:
            cfg = ["## 思维导图配置"]
            cfg.append(f"- 导图类型: {config.get('map_type', 'knowledge_tree')}")
            cfg.append(f"- 最大深度: {config.get('max_depth', 4)}")
            cfg.append("- 用粗体高亮标注薄弱知识点" if config.get("highlight_weak", True) else "- 不高亮薄弱知识点")
            input_text += f"\n\n{chr(10).join(cfg)}"
        # 明确要求使用标准 Markdown 格式，禁止 Mermaid 语法
        input_text += (
            "\n\n请务必使用 `#` 一级标题、`##` 二级标题和 `-` 列表符号来构建导图结构。\n"
            "【注意】绝对不要使用 Mermaid 语法！请只输出标准的 Markdown 标题和列表文本。"
        )

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="running",
                message="正在构建知识导图提示词",
                progress=25,
            )

        logger.info("Agent[mindmap] 步骤: 调用 LLM 生成知识导图, input_len=%d", len(input_text))
        prompt = prompts.get("resource").get("mindmap")
        response = await self.llm.ainvoke(f"{prompt}\n\n{input_text}", temperature=INFERENCE_TEMPERATURE)

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="running",
                message="导图已生成，正在解析分支结构",
                progress=85,
            )

        content = response.content if hasattr(response, "content") else str(response)
        # 清理 LLM 输出中多余的 fence 标记
        content = _clean_markdown(content)

        # 解析导图分支和薄弱知识点
        branches: list[str] = []
        weak_points: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            # 二级标题作为分支节点
            if stripped.startswith("## "):
                branches.append(stripped.lstrip("#").strip())
            # 列表项中包含易错/薄弱标记的作为薄弱点
            elif stripped.startswith("- "):
                item = stripped[2:].strip()
                if any(token in item for token in ("易错", "误区", "难点", "薄弱")):
                    weak_points.append(item)

        logger.info("Agent[mindmap] 步骤: 导图解析完成, output_len=%d branches=%d weak=%d", len(content), len(branches), len(weak_points))

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
    """清理 LLM 输出中的 markdown fence 和 mermaid 标记。"""
    lines = content.split("\n")
    return "\n".join(
        line for line in lines
        if line.strip() not in ("```", "```markdown", "```text", "```mermaid")
        and not line.strip().startswith("```mermaid")
    )
