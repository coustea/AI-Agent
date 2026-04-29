"""
Mindmap Agent — 思维导图 Agent。

生成 Markdown 知识结构图，并转换为 HTML 格式保存。
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.schemas import WorkerState, WorkerResult
from app.resource.utils import write_agent_artifact, get_workspace_dir, markdown_to_mindmap_html, read_agent_report
from app.resource.worker_agents.reporter_agent import ReporterAgent

logger = get_logger(__name__)


class MindmapAgent:
    """思维导图 Agent。"""

    def __init__(self, user_id: int, resource_id: int):
        self.user_id = user_id
        self.resource_id = resource_id
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "mindmap.md"

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行思维导图生成。"""
        logger.info("[MindmapAgent] 开始执行: topic=%s", state.task.get("course", ""))

        # 加载 prompt
        prompt = self._load_prompt()

        input_text = await self._build_input(state)

        try:
            response = await self.llm_manager.ainvoke(
                "spark_x",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={"temperature": 0.3},
            )

            content = response.content if hasattr(response, "content") else str(response)
            markdown_content = self._clean_content(content)

            # 转换 Markdown 为 HTML
            html_content = markdown_to_mindmap_html(markdown_content, title=state.task.get("course", "知识思维导图"))

            artifact_path = await write_agent_artifact(
                self.user_id, self.resource_id, "mindmap", html_content, file_type="html"
            )

            # 后台异步生成执行报告
            asyncio.create_task(
                self._generate_report_async(state.task, markdown_content)
            )

            return WorkerResult(
                success=True,
                content=html_content,
                artifact_path=artifact_path,
                artifact_dir=str(get_workspace_dir(self.user_id, self.resource_id)),
                file_type="html",
            )

        except Exception as exc:
            logger.exception("[MindmapAgent] 执行失败")

            # 后台异步生成失败报告
            asyncio.create_task(
                self._generate_report_async(state.task, "", error=str(exc))
            )

            return WorkerResult(success=False, error=str(exc))

    async def _generate_report_async(
        self,
        task: dict[str, Any],
        content: str,
        error: str | None = None,
    ) -> None:
        """后台异步生成执行报告。"""
        try:
            reporter = ReporterAgent()
            report_path, _ = await reporter.generate_report(
                user_id=self.user_id,
                resource_id=self.resource_id,
                agent_type="mindmap",
                task=task,
                content=content,
                error=error,
            )
            logger.info("[MindmapAgent] 报告已生成: %s", report_path)
        except Exception as exc:
            logger.warning("[MindmapAgent] 报告生成失败: %s", exc)

    def _load_prompt(self) -> str:
        if self.prompt_path.exists():
            return self.prompt_path.read_text(encoding="utf-8")
        return """你是一位知识结构专家。请根据给定的主题，生成一份思维导图。

要求：
1. 使用 Markdown 列表格式表示层级结构
2. 主题作为根节点，分支作为子节点
3. 每个分支包含关键概念和要点
4. 结构清晰，层次分明"""

    async def _build_input(self, state: WorkerState) -> str:
        task = state.task
        parts = [
            f"## 主题: {task.get('course', '')}",
            f"## 知识点: {task.get('gap', '')}",
        ]

        # 读取依赖 Agent 的报告
        if state.dependencies:
            parts.append(f"\n## 参考内容（来自前置 Agent 的执行报告）")
            for dep_name in state.dependencies:
                report = await read_agent_report(
                    self.user_id, self.resource_id, dep_name
                )
                if report:
                    parts.append(f"\n### {dep_name} 报告")
                    parts.append(report)

        parts.append("\n请生成思维导图。")
        return "\n".join(parts)

    def _clean_content(self, content: str) -> str:
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        return content.strip()