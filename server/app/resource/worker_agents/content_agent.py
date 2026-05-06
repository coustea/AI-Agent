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
from app.resource.worker_agents.utils import (
    append_backend_context_for_prompt,
    extract_markdown_from_llm_output,
    learning_need_from_task,
    title_from_learning_need,
)

logger = get_logger(__name__)


class ContentAgent:
    """内容讲解 Agent。"""

    STEPS = ["分析输入", "融合画像与依赖", "生成内容", "整理输出"]
    ROLE_NAME = "课程讲解智能体"

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "content.md"

    async def _emit_action(
        self,
        state: WorkerState,
        action: str,
        detail: str = "",
        current_step: int = 0,
        total_steps: int = 0,
        step_label: str = "",
        current_action: str = "",
        output_preview: str = "",
    ) -> None:
        """发送 Agent 动作事件。"""
        if self.emitter:
            await self.emitter.emit_agent_action(
                state.agent_name,
                action,
                detail,
                current_step=current_step,
                total_steps=total_steps,
                step_label=step_label,
                current_action=current_action,
                output_preview=output_preview,
                layer=state.layer_index,
                layer_name="认知建构层",
                agent_role=self.ROLE_NAME,
                resource_type=state.agent_name,
            )

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行内容生成。"""
        logger.info("[ContentAgent] 开始执行: learning_need=%s", learning_need_from_task(state.task)[:80])
        total = 5

        await self._emit_action(
            state,
            "analyze_input",
            "课程讲解智能体正在分析学习需求",
            current_step=2,
            total_steps=total,
            step_label=self.STEPS[0],
            current_action="分析学习需求",
            output_preview="正在识别课程主题、知识短板和资源目标",
        )
        prompt = self._load_prompt()

        await self._emit_action(
            state,
            "merge_profile_dependencies",
            "课程讲解智能体正在融合学习画像和上游信息",
            current_step=3,
            total_steps=total,
            step_label=self.STEPS[1],
            current_action="融合画像与依赖",
            output_preview="正在读取个性化约束、学习偏好和 MasterAgent 输入参数",
        )
        input_text = await self._build_input(state)

        try:
            await self._emit_action(
                state,
                "generate_content",
                "课程讲解智能体正在生成讲解内容",
                current_step=4,
                total_steps=total,
                step_label=self.STEPS[2],
                current_action="生成课程讲解",
                output_preview="正在组织概念解释、示例、易错点和复习重点",
            )

            response = await self.llm_manager.ainvoke(
                "spark_x",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={"temperature": 0.3},
            )

            content = response.content if hasattr(response, "content") else str(response)
            content = self._clean_content(content)

            await self._emit_action(
                state,
                "finalize_output",
                f"课程讲解智能体正在整理输出 (约 {len(content)} 字符)",
                current_step=5,
                total_steps=total,
                step_label=self.STEPS[3],
                current_action="整理讲解文档",
                output_preview=content[:240],
            )

            return WorkerResult(
                success=True,
                content=content,
                file_type="markdown",
                title=title_from_learning_need(state.task, "内容讲解"),
                summary="生成课程讲解文档",
                metadata={"engine": "markdown", "render_at": "frontend"},
            )

        except Exception as exc:
            logger.exception("[ContentAgent] 执行失败")
            return WorkerResult(success=False, error=str(exc))

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
        agent_config = state.agent_config

        parts = [
            "## 学习需求",
            learning_need_from_task(task),
            "",
            "## 学习场景",
            f"- 场景类型: {state.learning_scenario}",
            "",
            "## Agent 配置",
            f"- 结构类型: {agent_config.get('structure', 'progressive')}",
            f"- 包含常见错误: {agent_config.get('include_common_mistakes', True)}",
            f"- 包含示例: {agent_config.get('include_examples', True)}",
            f"- 聚焦模式: {agent_config.get('focus_mode', 'full_coverage')}",
            f"- 深度级别: {agent_config.get('depth_level', 'standard')}",
        ]

        append_backend_context_for_prompt(parts, state)

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
