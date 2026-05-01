"""
Content Agent — 内容讲解 Agent。

生成基础知识讲解 Markdown。
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


class ContentAgent:
    """内容讲解 Agent。"""

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "content.md"

    async def _emit_action(self, action: str, detail: str = "") -> None:
        """发送 Agent 动作事件。"""
        if self.emitter:
            await self.emitter.emit_agent_action("content", action, detail)

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行内容生成。"""
        logger.info("[ContentAgent] 开始执行: topic=%s", state.task.get("topic", ""))

        await self._emit_action("loading_prompt", "加载内容生成提示词")
        prompt = self._load_prompt()

        await self._emit_action("building_input", "构建输入内容，整合任务信息和依赖报告")
        input_text = await self._build_input(state)

        try:
            await self._emit_action("calling_llm", "调用 spark_x 生成讲解内容")

            response = await self.llm_manager.ainvoke(
                "spark_x",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={"temperature": 0.3},
            )

            content = response.content if hasattr(response, "content") else str(response)
            content = self._clean_content(content)

            await self._emit_action("finalizing_result", f"生成讲解文档 ({len(content)} 字符)")

            execution_report = generate_execution_report(
                agent_type="content",
                task=state.task,
                content=content,
                success=True,
            )

            return WorkerResult(
                success=True,
                content=content,
                file_type="markdown",
                title=f"{state.task.get('topic', state.task.get('course', ''))} - 内容讲解",
                summary="生成课程讲解文档",
                execution_report=execution_report,
                metadata={"engine": "markdown", "render_at": "frontend"},
            )

        except Exception as exc:
            logger.exception("[ContentAgent] 执行失败")

            execution_report = generate_execution_report(
                agent_type="content",
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
        return """你是一位专业的教育内容创作者。请根据给定的主题和知识点，生成一份清晰、专业的讲解文档。

要求：
1. 内容结构清晰，使用 Markdown 格式
2. 包含概念解释、示例、注意事项
3. 字数控制在 1500-3000 字
4. 使用中文撰写"""

    async def _build_input(self, state: WorkerState) -> str:
        """构建输入文本。

        使用新的 WorkerState 字段：
        - task: 任务信息
        - personalization: 个性化配置
        - agent_config: Agent 专属配置
        - learner_profile: 学习者画像
        - upstream_results: 上游结果
        - dependencies: 依赖的 Agent
        """
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
            f"- 额外要求: {task.get('extra_requirement', '')}",
            "",
            "## 个性化配置",
            f"- 当前水平: {personalization.get('current_level', 'basic')}",
            f"- 目标水平: {personalization.get('target_level', 'understand')}",
            f"- 讲解风格: {personalization.get('explanation_style', 'easy')}",
            f"- 内容深度: {personalization.get('content_depth', 'standard')}",
            f"- 示例偏好: {personalization.get('example_preference', 'visual')}",
            f"- 输出语言: {personalization.get('output_language', 'zh')}",
            "",
            "## Agent 配置",
            f"- 结构类型: {agent_config.get('structure', 'progressive')}",
            f"- 包含总结: {agent_config.get('include_summary', True)}",
            f"- 包含要点: {agent_config.get('include_key_points', True)}",
            f"- 包含常见错误: {agent_config.get('include_common_mistakes', True)}",
            f"- 包含记忆技巧: {agent_config.get('include_memory_tips', True)}",
            f"- 包含示例: {agent_config.get('include_examples', True)}",
        ]

        if profile:
            parts.append("")
            parts.append("## 学习者画像")
            profile_markdown = profile.get("profile_markdown", "")
            if profile_markdown:
                parts.append(profile_markdown)
            else:
                parts.append(f"- 专业: {profile.get('major', '未知')}")
                parts.append(f"- 年级: {profile.get('grade', '未知')}")
                parts.append(f"- 学校: {profile.get('school', '未知')}")

        # 上游结果摘要
        if state.upstream_results:
            parts.append("")
            parts.append("## 上游结果摘要")
            for agent_id, result in state.upstream_results.items():
                content_preview = str(result.get("content", ""))[:300]
                parts.append(f"- {agent_id}: {content_preview}...")

        parts.append("")
        parts.append("请生成讲解文档。")
        return "\n".join(parts)

    def _clean_content(self, content: str) -> str:
        """清理内容。"""
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        return content.strip()
