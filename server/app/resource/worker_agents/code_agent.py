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
    AgentContextBuilder,
    append_backend_context_for_prompt,
    learning_need_from_task,
    title_from_learning_need,
)
from app.utils.json import parse_first_json_object

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
            )

            response = await self.llm_manager.ainvoke(
                "spark_x",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                },
            )

            raw_content = response.content if hasattr(response, "content") else str(response)
            language = state.agent_config.get("programming_language", "python")

            try:
                parsed = parse_first_json_object(raw_content)
                code_data = {
                    "language": parsed.get("language", language),
                    "code": parsed.get("code", ""),
                    "explanation": parsed.get("explanation", "代码实操案例"),
                    "input_example": parsed.get("input_example", ""),
                    "output_example": parsed.get("output_example", ""),
                    "complexity": parsed.get("complexity", {"time": "", "space": ""}),
                    "run_steps": parsed.get("run_steps", [])[:5],
                    "debug_tips": parsed.get("debug_tips", []),
                    "exercises": parsed.get("exercises", [])[:3],
                }
            except Exception:
                # Fallback: 原始内容作为 code
                code_data = {
                    "language": language,
                    "code": self._clean_content(raw_content),
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
                f"实战代码沙箱智能体正在整理输出 ({len(code_data.get('code', ''))} 字符)",
                current_step=5,
                total_steps=total,
                step_label=self.STEPS[3],
                current_action="整理代码资源",
            )

            explanation = code_data.get("explanation")
            if isinstance(explanation, list):
                practice_points = [str(item) for item in explanation if item]
            elif explanation:
                practice_points = [str(explanation)]
            else:
                practice_points = []
            practice_points.extend(str(item) for item in code_data.get("run_steps", []) if item)
            main_functions = re.findall(r"\bdef\s+([A-Za-z_]\w*)\s*\(", str(code_data.get("code") or ""))
            summary_data = {
                "language": str(code_data.get("language") or language),
                "case_type": state.agent_config.get("case_type", "basic_demo"),
                "practice_points": list(dict.fromkeys(practice_points))[:8],
                "main_functions": list(dict.fromkeys(main_functions))[:8],
                "has_exercises": bool(code_data.get("exercises")),
            }

            return WorkerResult.model_construct(
                success=True,
                content=code_data,
                file_type="json",
                title=title_from_learning_need(state.task, "代码实操案例"),
                summary="生成代码实操案例",
                metadata={"language": language},
                summary_data=summary_data,
            )

        except Exception as exc:
            logger.exception("[CodeAgent] 执行失败")
            return WorkerResult(success=False, error=str(exc))

    def _load_prompt(self) -> str:
        """加载提示词。"""
        if self.prompt_path.exists():
            return self.prompt_path.read_text(encoding="utf-8")
        return """你是一位编程教育专家。请根据给定的主题，生成代码示例。

输出必须是 JSON 格式：
{
  "language": "python",
  "code": "完整可运行代码",
  "explanation": ["说明1", "说明2"],
  "run_steps": ["步骤1", "步骤2"],
  "exercises": ["练习1", "练习2"]
}

要求：
1. 代码可运行，有详细注释
2. 适合学习者理解
3. 不要输出 Markdown 代码块，直接输出 JSON"""

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

        # Use AgentContextBuilder for context-aware prompt building
        builder = AgentContextBuilder()
        context_text = builder.build_for_agent("code", state)
        if context_text:
            parts.append("")
            parts.append(context_text)
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
