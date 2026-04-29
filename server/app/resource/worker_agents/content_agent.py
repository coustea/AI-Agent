"""
Content Agent — 内容讲解 Agent。

生成基础知识讲解 Markdown。
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
from app.resource.utils import write_agent_artifact, get_workspace_dir, read_agent_report
from app.resource.worker_agents.reporter_agent import ReporterAgent

logger = get_logger(__name__)


class ContentAgent:
    """内容讲解 Agent。"""

    def __init__(self, user_id: int, resource_id: int):
        self.user_id = user_id
        self.resource_id = resource_id
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "content.md"

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行内容生成。"""
        logger.info("[ContentAgent] 开始执行: topic=%s", state.task.get("course", ""))

        # 读取提示词
        prompt = self._load_prompt()

        # 构建输入（包含依赖报告）
        input_text = await self._build_input(state)

        # 调用 LLM
        try:
            response = await self.llm_manager.ainvoke(
                "spark_x",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={"temperature": 0.3},
            )

            content = response.content if hasattr(response, "content") else str(response)
            content = self._clean_content(content)

            # 写入产物
            artifact_path = await write_agent_artifact(
                self.user_id, self.resource_id, "content", content, file_type="md"
            )

            # 构建产物目录路径
            artifact_dir = str(get_workspace_dir(self.user_id, self.resource_id))

            # 后台异步生成执行报告
            asyncio.create_task(
                self._generate_report_async(state.task, content)
            )

            return WorkerResult(
                success=True,
                content=content,
                artifact_path=artifact_path,
                artifact_dir=artifact_dir,
                file_type="md",
            )

        except Exception as exc:
            logger.exception("[ContentAgent] 执行失败")

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
                agent_type="content",
                task=task,
                content=content,
                error=error,
            )
            logger.info("[ContentAgent] 报告已生成: %s", report_path)
        except Exception as exc:
            logger.warning("[ContentAgent] 报告生成失败: %s", exc)

    def _load_prompt(self) -> str:
        """加载提示词。"""
        if self.prompt_path.exists():
            return self.prompt_path.read_text(encoding="utf-8")
        return """你是一位专业的教育内容创作者。请根据给定的主题和知识点，生成一份清晰、专业的讲解文档。

要求：
1. 内容结构清晰，使用 Markdown 格式
2. 包含概念解释、示例、注意事项
3. 字数控制在 1500-3000 字
4. 使用中文撰写"""

    async def _build_input(self, state: WorkerState) -> str:
        """构建输入文本。"""
        task = state.task
        profile = state.profile

        parts = [
            f"## 课程信息",
            f"- 主题: {task.get('course', '')}",
            f"- 知识点: {task.get('gap', '')}",
            f"- 需求类型: {task.get('need', 'review')}",
        ]

        if profile:
            parts.append(f"\n## 学习者画像")
            parts.append(profile.get("profile_markdown", "暂无"))

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

        parts.append(f"\n请生成讲解文档。")
        return "\n".join(parts)

    def _clean_content(self, content: str) -> str:
        """清理内容。"""
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        return content.strip()