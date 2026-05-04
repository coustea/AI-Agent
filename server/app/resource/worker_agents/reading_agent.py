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
from app.resource.worker_agents.utils import (
    append_backend_context_for_prompt,
    extract_markdown_from_llm_output,
    learning_need_from_task,
    title_from_learning_need,
)
from app.shared.json_utils import parse_first_json_value

logger = get_logger(__name__)


class ReadingAgent:
    """拓展阅读 Agent。"""

    STEPS = ["筛选高价值延伸资料", "匹配学习需求", "生成精简阅读导引", "标注内容关联性"]

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "reading.md"

    async def _emit_action(
        self,
        action: str,
        detail: str = "",
        current_step: int = 0,
        total_steps: int = 0,
        step_label: str = "",
    ) -> None:
        """发送 Agent 动作事件。"""
        if self.emitter:
            await self.emitter.emit_agent_action(
                "reading",
                action,
                detail,
                current_step=current_step,
                total_steps=total_steps,
                step_label=step_label,
            )

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行拓展阅读生成。"""
        logger.info("[ReadingAgent] 开始执行: learning_need=%s", learning_need_from_task(state.task)[:80])
        total = len(self.STEPS)

        await self._emit_action(
            "loading_prompt",
            "加载拓展阅读推荐提示词...",
            current_step=1,
            total_steps=total,
            step_label=self.STEPS[0],
        )
        prompt = self._load_prompt()

        await self._emit_action(
            "building_input",
            "正在根据学习需求筛选高价值延伸资料...",
            current_step=2,
            total_steps=total,
            step_label=self.STEPS[1],
        )
        input_text = await self._build_input(state)

        try:
            await self._emit_action(
                "calling_llm",
                "正在为你生成精简阅读导引...",
                current_step=3,
                total_steps=total,
                step_label=self.STEPS[2],
            )

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

            await self._emit_action(
                "finalizing_result",
                "正在标注内容关联性并生成推荐列表...",
                current_step=4,
                total_steps=total,
                step_label=self.STEPS[3],
            )

            return WorkerResult.model_construct(
                success=True,
                content=content,
                file_type="json",
                title=title_from_learning_need(state.task, "拓展阅读"),
                summary="生成拓展阅读材料与阅读顺序",
                metadata={
                    "reading_depth": state.agent_config.get("reading_depth", "course_extended"),
                },
            )

        except Exception as exc:
            logger.exception("[ReadingAgent] 执行失败")
            return WorkerResult(success=False, error=str(exc))

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
        agent_config = state.agent_config

        parts = [
            "## 学习需求",
            learning_need_from_task(task),
            "",
            "## Agent 配置",
            f"- 阅读深度: {agent_config.get('reading_depth', 'course_extended')}",
            f"- 最大条目数: {agent_config.get('max_items', 5)}",
            f"- 资源时效偏好: {agent_config.get('resource_quality', 'balanced')}",
            f"- 包含实践资源: {agent_config.get('include_practice', False)}",
            f"- 语言偏好: {agent_config.get('language_preference', 'chinese')}",
        ]

        append_backend_context_for_prompt(parts, state)

        parts.append("")
        parts.append("请推荐拓展阅读材料。")
        return "\n".join(parts)

    def _clean_content(self, content: str) -> str:
        """清理内容。"""
        return content.strip()
