"""
Reading Agent — 拓展阅读 Agent。

生成延伸阅读材料和参考方向，输出 JSON 格式。
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.schemas import WorkerState, WorkerResult
from app.resource.worker_agents.utils import generate_execution_report
from app.shared.json_utils import parse_first_json_value

logger = get_logger(__name__)


class ReadingAgent:
    """拓展阅读 Agent。"""

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "reading.md"

    async def _emit_action(self, action: str, detail: str = "") -> None:
        """发送 Agent 动作事件。"""
        if self.emitter:
            await self.emitter.emit_agent_action("reading", action, detail)

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行拓展阅读生成。"""
        logger.info("[ReadingAgent] 开始执行: topic=%s", state.task.get("topic", ""))

        await self._emit_action("loading_prompt", "加载拓展阅读推荐提示词")
        prompt = self._load_prompt()

        await self._emit_action("building_input", "构建输入内容，整合任务信息和依赖报告")
        input_text = await self._build_input(state)

        try:
            await self._emit_action("calling_llm", "调用 spark_x 生成拓展阅读推荐")

            response = await self.llm_manager.ainvoke(
                "spark_x",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={"temperature": 0.3},
            )

            raw_content = response.content if hasattr(response, "content") else str(response)

            try:
                content = parse_first_json_value(raw_content)
            except (TypeError, ValueError):
                logger.warning("[ReadingAgent] JSON 解析失败，返回原始内容")
                content = {"error": "解析失败", "raw_content": self._clean_content(raw_content)}

            await self._emit_action("finalizing_result", "生成拓展阅读 JSON")

            execution_report = generate_execution_report(
                agent_type="reading",
                task=state.task,
                content=content,
                success=True,
            )

            return WorkerResult.model_construct(
                success=True,
                content=content,
                file_type="json",
                title=f"{state.task.get('topic', state.task.get('course', ''))} - 拓展阅读",
                summary="生成拓展阅读材料与阅读顺序",
                execution_report=execution_report,
                metadata={
                    "reading_depth": state.agent_config.get("reading_depth", "course_extended"),
                    "source_types": state.agent_config.get("source_types", ["textbook", "article", "documentation"]),
                },
            )

        except Exception as exc:
            logger.exception("[ReadingAgent] 执行失败")

            execution_report = generate_execution_report(
                agent_type="reading",
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
        return """你是一位教育资源推荐专家。请根据给定的主题，推荐拓展阅读材料。

要求：
1. 推荐相关书籍、论文、文章
2. 说明推荐理由
3. 提供学习路径建议
4. 使用 Markdown 格式"""

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
            f"- 学习目标: {task.get('learning_goal', '')}",
            "",
            "## 个性化配置",
            f"- 当前水平: {personalization.get('current_level', 'basic')}",
            f"- 目标水平: {personalization.get('target_level', 'understand')}",
            "",
            "## Agent 配置",
            f"- 阅读深度: {agent_config.get('reading_depth', 'course_extended')}",
            f"- 来源类型: {', '.join(agent_config.get('source_types', ['textbook', 'article', 'documentation']))}",
            f"- 最大条目数: {agent_config.get('max_items', 5)}",
            f"- 包含推荐理由: {agent_config.get('include_reason', True)}",
            f"- 包含阅读顺序: {agent_config.get('include_reading_order', True)}",
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
        parts.append("请推荐拓展阅读材料。")
        return "\n".join(parts)

    def _clean_content(self, content: str) -> str:
        """清理内容。"""
        return content.strip()
