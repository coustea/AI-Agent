"""思维导图智能体 — 生成 Markdown 知识结构图，返回给前端 Markmap 渲染。"""

from __future__ import annotations

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import (
    build_node_context,
    build_resource_context,
)
from app.infra.prompts import prompts
from app.resource.schemas import AgentResult, NodeInput, ResourceInput

logger = get_logger(__name__)


@register_agent
class MindmapAgent(BaseResourceAgent):
    """基于教学蓝图生成 Markmap 思维导图（标准 Markdown 标题+列表格式）。"""

    agent_id = "mindmap"
    agent_name = "思维导图生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
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
        await self.emitter.send(self.agent_id, "completed" if result.success else "failed", result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), 100 if result.success else 0)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        result = await self._generate_mindmap(
            input_text="\n\n".join(build_node_context(input_data)),
            title_prefix=input_data.node_title,
            config=input_data.agent_config,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.emitter.send(self.agent_id, "completed" if result.success else "failed", result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), 100 if result.success else 0)
        return result

    async def _generate_mindmap(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
        """内部方法 — 调用 LLM 生成 Markmap 思维导图 Markdown。

        agent_config 已由 build_resource_context / build_node_context 统一注入，
        此处仅提取运行时需要的参数。
        """
        input_text += (
            "\n\n请务必使用 `#` 一级标题、`##` 二级标题和 `-` 列表符号来构建导图结构。\n"
            "【注意】绝对不要使用 Mermaid 语法！请只输出标准的 Markdown 标题 and 列表文本。"
        )

        # 执行搜索以丰富导图中的分支深度与细化概念
        await self.emitter.send(self.agent_id, "running", "正在搜索相关知识导图大纲...", 30)
        search_query = f"{title_prefix} 知识图谱 知识链路"
        search_text = await self.search(search_query)

        if "搜索失败" not in search_text and "未找到" not in search_text:
            input_text = f"## 搜索到的相关知识大纲参考\n{search_text}\n\n" + input_text

        await self.emitter.send(self.agent_id, "running", "正在构建知识导图提示词...", 45)
        prompt = prompts.get("resource").get("mindmap")
        await self.emitter.send(self.agent_id, "running", "正在生成知识图谱结构...", 60)
        response = await self.llm.ainvoke(f"{prompt}\n\n{input_text}", temperature=INFERENCE_TEMPERATURE)
        content = response.content if hasattr(response, "content") else str(response)

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
