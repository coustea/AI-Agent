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
    append_backend_context_for_prompt,
    extract_markdown_from_llm_output,
    learning_need_from_task,
    title_from_learning_need,
)

logger = get_logger(__name__)


class MindmapAgent:
    """思维导图 Agent。"""

    STEPS = ["分析输入", "融合画像与依赖", "生成内容", "整理输出"]
    ROLE_NAME = "知识结构图谱智能体"

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "mindmap.md"

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
        """执行思维导图生成。"""
        logger.info("[MindmapAgent] 开始执行: learning_need=%s", learning_need_from_task(state.task)[:80])
        total = 5

        await self._emit_action(
            state,
            "analyze_input",
            "知识结构图谱智能体正在分析学习需求",
            current_step=2,
            total_steps=total,
            step_label=self.STEPS[0],
            current_action="分析知识结构需求",
            output_preview="正在识别核心概念、层级关系和知识组织目标",
        )
        prompt = self._load_prompt()

        await self._emit_action(
            state,
            "merge_profile_dependencies",
            "知识结构图谱智能体正在融合画像和依赖信息",
            current_step=3,
            total_steps=total,
            step_label=self.STEPS[1],
            current_action="融合画像与依赖",
            output_preview="正在结合学习短板、前置知识和规划参数梳理导图范围",
        )
        input_text = await self._build_input(state)

        try:
            await self._emit_action(
                state,
                "generate_content",
                "知识结构图谱智能体正在生成思维导图",
                current_step=4,
                total_steps=total,
                step_label=self.STEPS[2],
                current_action="生成多级思维导图",
                output_preview="正在构建主题节点、一级分支和关键概念层级",
            )

            response = await self.llm_manager.ainvoke(
                "spark_x",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={"temperature": 0.3},
            )

            content = response.content if hasattr(response, "content") else str(response)
            markdown_content = extract_markdown_from_llm_output(content)

            await self._emit_action(
                state,
                "finalize_output",
                f"知识结构图谱智能体正在整理输出 ({len(markdown_content)} 字符)",
                current_step=5,
                total_steps=total,
                step_label=self.STEPS[3],
                current_action="整理导图结构",
                output_preview=markdown_content[:240],
            )

            return WorkerResult(
                success=True,
                content=markdown_content,
                file_type="markdown",
                title=title_from_learning_need(state.task, "思维导图"),
                summary="生成 Markmap 思维导图 Markdown",
                metadata={
                    "engine": "markmap",
                    "render_at": "frontend",
                    "map_type": state.agent_config.get("map_type", "knowledge_tree"),
                },
            )

        except Exception as exc:
            logger.exception("[MindmapAgent] 执行失败")
            return WorkerResult(success=False, error=str(exc))

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
        agent_config = state.agent_config

        parts = [
            "## 学习需求",
            learning_need_from_task(task),
            "",
            "## 学习场景",
            f"- 场景类型: {state.learning_scenario}",
            "",
            "## Agent 配置",
            f"- 导图类型: {agent_config.get('map_type', 'knowledge_tree')}",
            f"- 最大深度: {agent_config.get('max_depth', 4)}",
            f"- 高亮短板: {agent_config.get('highlight_weak', True)}",
            f"- 展开薄弱点: {agent_config.get('expand_weak_points', False)}",
            f"- 包含前置知识: {agent_config.get('include_prerequisites', False)}",
        ]

        append_backend_context_for_prompt(parts, state)

        parts.append("")
        parts.append("请生成思维导图，只输出 Markdown 内容。")
        return "\n".join(parts)
