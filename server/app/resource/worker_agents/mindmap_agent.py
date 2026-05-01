"""
思维导图 Agent — 思维导图生成 Agent。

生成 Markdown 知识结构图，返回给前端渲染。
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.schemas import WorkerState, WorkerResult
from app.resource.worker_agents.utils import (
    extract_markdown_from_llm_output,
    generate_execution_report,
)

logger = get_logger(__name__)


class MindmapAgent:
    """思维导图 Agent。"""

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "mindmap.md"

    async def _emit_action(self, action: str, detail: str = "") -> None:
        """发送 Agent 动作事件。"""
        if self.emitter:
            await self.emitter.emit_agent_action("mindmap", action, detail)

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行思维导图生成。"""
        logger.info("[MindmapAgent] 开始执行: topic=%s", state.task.get("topic", ""))

        await self._emit_action("loading_prompt", "加载思维导图生成提示词")
        prompt = self._load_prompt()

        await self._emit_action("building_input", "构建输入内容")
        input_text = await self._build_input(state)

        try:
            await self._emit_action("calling_llm", "调用 spark_x 生成思维导图结构")

            response = await self.llm_manager.ainvoke(
                "spark_x",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={"temperature": 0.3},
            )

            content = response.content if hasattr(response, "content") else str(response)
            markdown_content = extract_markdown_from_llm_output(content)

            await self._emit_action("finalizing_result", f"生成思维导图 Markdown ({len(markdown_content)} 字符)")

            execution_report = generate_execution_report(
                agent_type="mindmap",
                task=state.task,
                content=markdown_content,
                success=True,
            )

            return WorkerResult(
                success=True,
                content=markdown_content,
                file_type="markdown",
                title=f"{state.task.get('topic', state.task.get('course', ''))} - 思维导图",
                summary="生成 Markmap 思维导图 Markdown",
                execution_report=execution_report,
                metadata={
                    "engine": "markmap",
                    "render_at": "frontend",
                    "map_type": state.agent_config.get("map_type", "knowledge_tree"),
                },
            )

        except Exception as exc:
            logger.exception("[MindmapAgent] 执行失败")

            execution_report = generate_execution_report(
                agent_type="mindmap",
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
        return """你是一位知识结构专家。请根据给定的主题，生成一份思维导图。

要求：
1. 使用 Markdown 格式，以一级标题作为根节点，列表表示层级结构
2. 主题作为根节点，分支作为子节点
3. 每个分支包含关键概念和要点
4. 结构清晰，层次分明
5. 一级分支必须顶格写成 `- 分支名称`，不要在一级分支前加空格
6. 只输出 Markdown 内容，不要包含代码块标记"""

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
            f"- 讲解风格: {personalization.get('explanation_style', 'easy')}",
            f"- 示例偏好: {personalization.get('example_preference', 'visual')}",
            "",
            "## Agent 配置",
            f"- 导图类型: {agent_config.get('map_type', 'knowledge_tree')}",
            f"- 最大深度: {agent_config.get('max_depth', 4)}",
            f"- 聚焦短板: {agent_config.get('focus_on_weak_points', True)}",
            f"- 包含考点: {agent_config.get('include_exam_points', True)}",
            f"- 包含常见错误: {agent_config.get('include_common_mistakes', True)}",
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
        parts.append("请生成思维导图，只输出 Markdown 内容。")
        return "\n".join(parts)
