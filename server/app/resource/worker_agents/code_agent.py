"""
Code Agent — 代码示例 Agent。

生成可运行代码、注释和讲解。
"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.messages import HumanMessage

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.schemas import WorkerState, WorkerResult
from app.resource.worker_agents.utils import generate_execution_report

logger = get_logger(__name__)


class CodeAgent:
    """代码示例 Agent。"""

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "code.md"

    async def _emit_action(self, action: str, detail: str = "") -> None:
        """发送 Agent 动作事件。"""
        if self.emitter:
            await self.emitter.emit_agent_action("code", action, detail)

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行代码生成。"""
        logger.info("[CodeAgent] 开始执行: topic=%s", state.task.get("topic", ""))

        await self._emit_action("loading_prompt", "加载代码示例生成提示词")
        prompt = self._load_prompt()

        await self._emit_action("building_input", "构建输入内容，整合任务信息和依赖报告")
        input_text = await self._build_input(state)

        try:
            await self._emit_action("calling_llm", "调用 spark_x 生成代码示例")

            response = await self.llm_manager.ainvoke(
                "spark_x",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={"temperature": 0.3},
            )

            content = response.content if hasattr(response, "content") else str(response)
            content = self._clean_content(content)
            language = state.agent_config.get("programming_language", "cpp")
            code_data = {
                "language": language,
                "code": content,
                "explanation": "代码实操案例",
                "input_example": "",
                "output_example": "",
                "complexity": {"time": "", "space": ""},
                "run_steps": [],
                "debug_tips": [],
                "exercises": [],
            }

            await self._emit_action("finalizing_result", f"生成代码示例 ({len(content)} 字符)")

            execution_report = generate_execution_report(
                agent_type="code",
                task=state.task,
                content=code_data,
                success=True,
            )

            return WorkerResult.model_construct(
                success=True,
                content=code_data,
                file_type="json",
                title=f"{state.task.get('topic', state.task.get('course', ''))} - 代码实操案例",
                summary="生成代码实操案例",
                execution_report=execution_report,
                metadata={"language": language},
            )

        except Exception as exc:
            logger.exception("[CodeAgent] 执行失败")

            execution_report = generate_execution_report(
                agent_type="code",
                task=state.task,
                content=None,
                success=False,
                error=str(exc),
            )

            return WorkerResult(success=False, error=str(exc), execution_report=execution_report)

    def _load_prompt(self) -> str:
        """加载提示词。"""
        if self.prompt_path.exists():
            return self.prompt_path.read_text(encoding="utf-8")
        return """你是一位编程教育专家。请根据给定的主题，生成代码示例。

要求：
1. 代码可运行，有详细注释
2. 包含讲解说明
3. 使用 Markdown 代码块格式
4. 适合学习者理解"""

    async def _build_input(self, state: WorkerState) -> str:
        """构建输入内容。"""
        task = state.task
        personalization = state.personalization
        agent_config = state.agent_config
        profile = state.learner_profile

        parts = [
            "## 课程信息",
            f"- 课程: {task.get('course', '')}",
            f"- 章节: {task.get('chapter', '')}",
            f"- 学习主题: {task.get('topic', task.get('course', ''))}",
            f"- 知识短板: {', '.join(task.get('weak_points', []))}",
            f"- 学习目标: {task.get('learning_goal', '')}",
            "",
            "## 个性化配置",
            f"- 当前水平: {personalization.get('current_level', 'basic')}",
            f"- 目标水平: {personalization.get('target_level', 'understand')}",
            f"- 示例偏好: {personalization.get('example_preference', 'visual')}",
            "",
            "## Agent 配置",
            f"- 编程语言: {agent_config.get('programming_language', 'cpp')}",
            f"- 案例类型: {agent_config.get('case_type', 'basic_demo')}",
            f"- 包含注释: {agent_config.get('include_comments', True)}",
            f"- 包含输入输出示例: {agent_config.get('include_input_output', True)}",
            f"- 包含复杂度分析: {agent_config.get('include_complexity', True)}",
            f"- 包含调试技巧: {agent_config.get('include_debug_tips', True)}",
            f"- 包含练习题: {agent_config.get('include_exercises', True)}",
        ]

        if profile:
            parts.append("")
            parts.append("## 学习者画像")
            profile_markdown = profile.get("profile_markdown", "")
            if profile_markdown:
                parts.append(profile_markdown)

        if state.upstream_results:
            parts.append("")
            parts.append("## 上游结果摘要")
            for agent_id, result in state.upstream_results.items():
                content_preview = str(result.get("content", ""))[:300]
                parts.append(f"- {agent_id}: {content_preview}...")

        parts.append("")
        parts.append("请生成代码示例。")
        return "\n".join(parts)

    def _clean_content(self, content: str) -> str:
        """清理内容。"""
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        return content.strip()
