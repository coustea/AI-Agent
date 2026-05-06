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
from app.resource.worker_agents.utils import (
    append_backend_context_for_prompt,
    extract_markdown_from_llm_output,
    learning_need_from_task,
    title_from_learning_need,
)

logger = get_logger(__name__)


class CodeAgent:
    """代码示例 Agent。"""

    STEPS = ["分析输入", "融合画像与依赖", "生成内容", "整理输出"]
    ROLE_NAME = "实战代码沙箱智能体"

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "code.md"

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
                layer_name="实践拓展层",
                agent_role=self.ROLE_NAME,
                resource_type=state.agent_name,
            )

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行代码生成。"""
        logger.info("[CodeAgent] 开始执行: learning_need=%s", learning_need_from_task(state.task)[:80])
        total = 5

        await self._emit_action(
            state,
            "analyze_input",
            "实战代码沙箱智能体正在分析实践任务",
            current_step=2,
            total_steps=total,
            step_label=self.STEPS[0],
            current_action="分析代码实践需求",
            output_preview="正在识别编程语言、案例目标、难度和关键知识点",
        )
        prompt = self._load_prompt()

        await self._emit_action(
            state,
            "merge_profile_dependencies",
            "实战代码沙箱智能体正在读取上游讲解重点",
            current_step=3,
            total_steps=total,
            step_label=self.STEPS[1],
            current_action="融合画像与依赖",
            output_preview="正在结合 ContentAgent 输出、学习画像和代码配置构建提示词",
        )
        input_text = await self._build_input(state)

        try:
            await self._emit_action(
                state,
                "generate_content",
                "实战代码沙箱智能体正在生成代码案例",
                current_step=4,
                total_steps=total,
                step_label=self.STEPS[2],
                current_action="生成代码与讲解",
                output_preview="正在编写可运行代码、关键注释、运行步骤和练习任务",
            )

            response = await self.llm_manager.ainvoke(
                "spark_x",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={"temperature": 0.3},
            )

            content = response.content if hasattr(response, "content") else str(response)
            content = self._clean_content(content)
            language = state.agent_config.get("programming_language", "python")
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

            await self._emit_action(
                state,
                "finalize_output",
                f"实战代码沙箱智能体正在整理输出 ({len(content)} 字符)",
                current_step=5,
                total_steps=total,
                step_label=self.STEPS[3],
                current_action="整理代码资源",
                output_preview=content[:240],
            )

            return WorkerResult.model_construct(
                success=True,
                content=code_data,
                file_type="json",
                title=title_from_learning_need(state.task, "代码实操案例"),
                summary="生成代码实操案例",
                metadata={"language": language},
            )

        except Exception as exc:
            logger.exception("[CodeAgent] 执行失败")
            return WorkerResult(success=False, error=str(exc))

    def _load_prompt(self) -> str:
        """加载提示词。"""
        if self.prompt_path.exists():
            return self.prompt_path.read_text(encoding="utf-8")
        prompt = """你是一位编程教育专家。请根据给定的主题，生成代码示例。
                
                要求：
                1. 代码可运行，有详细注释
                2. 包含讲解说明
                3. 使用 Markdown 代码块格式
                4. 适合学习者理解
                """
        return prompt

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
            f"- 编程语言: {agent_config.get('programming_language', 'python')}",
            f"- 案例类型: {agent_config.get('case_type', 'basic_demo')}",
            f"- 注释详细程度: {agent_config.get('comment_level', 'standard')}",
            f"- 包含测试用例: {agent_config.get('include_test', False)}",
            f"- 代码难度: {agent_config.get('difficulty', 'beginner')}",
        ]

        append_backend_context_for_prompt(parts, state)

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
