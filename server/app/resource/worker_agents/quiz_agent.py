"""
Quiz Agent — 习题 Agent。

生成练习题、答案和解析（JSON 格式）。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.schemas import WorkerState, WorkerResult
from app.resource.utils import write_agent_artifact, get_workspace_dir, read_agent_report
from app.resource.worker_agents.reporter_agent import ReporterAgent
from app.shared.json_utils import parse_first_json_object

logger = get_logger(__name__)


class QuizAgent:
    """习题 Agent。"""

    def __init__(self, user_id: int, resource_id: int):
        self.user_id = user_id
        self.resource_id = resource_id
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "quiz.md"

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行习题生成。"""
        logger.info("[QuizAgent] 开始执行: topic=%s", state.task.get("course", ""))

        prompt = self._load_prompt()
        input_text = await self._build_input(state)

        try:
            response = await self.llm_manager.ainvoke(
                "spark_x",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={"temperature": 0.3},
            )

            content = response.content if hasattr(response, "content") else str(response)
            quiz_json = self._parse_quiz_json(content)

            if quiz_json is None:
                logger.warning("[QuizAgent] JSON 解析失败，返回原始内容")
                quiz_json = {"error": "解析失败", "raw_content": content}

            json_str = json.dumps(quiz_json, ensure_ascii=False, indent=2)
            artifact_path = await write_agent_artifact(
                self.user_id, self.resource_id, "quiz", json_str, file_type="json"
            )

            # 后台异步生成执行报告
            asyncio.create_task(
                self._generate_report_async(state.task, json_str)
            )

            return WorkerResult(
                success=True,
                content=json_str,
                artifact_path=artifact_path,
                artifact_dir=str(get_workspace_dir(self.user_id, self.resource_id)),
                file_type="json",
            )

        except Exception as exc:
            logger.exception("[QuizAgent] 执行失败")

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
                agent_type="quiz",
                task=task,
                content=content,
                error=error,
            )
            logger.info("[QuizAgent] 报告已生成: %s", report_path)
        except Exception as exc:
            logger.warning("[QuizAgent] 报告生成失败: %s", exc)

    def _load_prompt(self) -> str:
        if self.prompt_path.exists():
            return self.prompt_path.read_text(encoding="utf-8")
        return """你是一位教育测评专家。请根据给定的内容，生成练习题。

要求输出 JSON 格式：
```json
{
  "title": "习题标题",
  "questions": [
    {
      "id": 1,
      "type": "choice|fill|short",
      "difficulty": "basic|intermediate|advanced",
      "question": "题目内容",
      "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
      "answer": "正确答案",
      "analysis": "解析说明"
    }
  ]
}
```"""

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

        parts.append("\n请生成练习题（JSON 格式）。")
        return "\n".join(parts)

    def _parse_quiz_json(self, content: str) -> dict | None:
        """解析 LLM 返回的 JSON。"""
        return parse_first_json_object(content)