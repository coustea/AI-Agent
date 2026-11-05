"""思维导图智能体 — 生成 Markdown 知识结构图，返回给前端 Markmap 渲染。"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from app.infra.llm import LLM
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import build_path_context, build_resource_context
from app.infra.prompts import prompts
from app.resource.schemas import AgentResult, ResourceInput

if TYPE_CHECKING:
    from app.path.schemas import PathResourceRequest

logger = get_logger(__name__)


@register_agent
class MindmapAgent(BaseResourceAgent):
    """基于教学蓝图生成 Markmap 思维导图（标准 Markdown 标题+列表格式）。"""

    agent_id = "mindmap"
    agent_name = "思维导图"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = LLM(temperature=0.7)

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        return await self._generate_mindmap(
            input_text="\n\n".join(build_resource_context(input_data)),
            title_prefix=input_data.learning_need[:32],
            config=input_data.agent_config,
        )

    async def generate_for_path(self, request: "PathResourceRequest") -> AgentResult:
        """路径规划统一接口 — 接收 PathResourceRequest，返回 AgentResult。"""
        if request.tutorial is None:
            return AgentResult(
                success=False,
                title="思维导图生成失败",
                file_type="markdown",
                error="缺少教程内容",
            )
        result = await self._generate_mindmap(
            input_text="\n\n".join(build_path_context(request)),
            title_prefix=request.node_title,
            config={},
        )
        result.metadata["node_id"] = request.node_id
        return result

    async def _generate_mindmap(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
        """内部方法 — 调用 LLM 生成 Markmap 思维导图 Markdown。"""
        logger.info("Agent[%s] 开始生成: learning_need=%s", self.agent_id, title_prefix)
        started = time.perf_counter()

        input_text += (
            "\n\n请务必使用 `#` 一级标题、`##` 二级标题和 `-` 列表符号来构建导图结构。\n"
            "【注意】绝对不要使用 Mermaid 语法！请只输出标准的 Markdown 标题 and 列表文本。"
        )

        await self.emitter.send(self.agent_id, "running", "正在构建知识导图提示词...", 45)
        prompt = prompts.get("resource").get("mindmap")
        await self.emitter.send(self.agent_id, "running", "正在生成知识图谱结构...", 60)
        full_prompt = f"{prompt}\n\n{input_text}"
        logger.info("Agent[%s] LLM 调用: input_len=%d", self.agent_id, len(full_prompt))
        llm_started = time.perf_counter()
        content = await self.run_with_heartbeat(
            self.llm.text(full_prompt),
            messages=[
                "正在生成知识导图主体结构...",
                "正在补充知识层级与分支关系...",
            ],
            interval_seconds=12.0,
            progress=70,
        )
        llm_elapsed = int((time.perf_counter() - llm_started) * 1000)
        logger.info(
            "Agent[%s] LLM 完成: output_len=%d elapsed_ms=%d",
            self.agent_id, len(content), llm_elapsed,
        )

        branches: list[str] = []
        weak_points: list[str] = []
        # 解析导图中的二级分支与薄弱点关键词
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                branches.append(stripped.lstrip("#").strip())
            elif stripped.startswith("- "):
                item = stripped[2:].strip()
                # 命中易错/难点等标记则归入薄弱点
                if any(token in item for token in ("易错", "误区", "难点", "薄弱")):
                    weak_points.append(item)

        total_elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Agent[%s] 生成完成: branches=%d weak_points=%d elapsed_ms=%d → %s",
            self.agent_id, len(branches), len(weak_points), total_elapsed,
            content[:200].replace("\n", " "),
        )
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
