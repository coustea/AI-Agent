"""
内容 Agent — 生成专业课程讲解文档。

支持两阶段生成:
  1. outline_only=True: 仅生成大纲 (供下游 Agent 参考)
  2. outline_only=False: 生成完整内容 (大纲 + 详细展开)
"""

from __future__ import annotations

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import Agent
from app.resource.schemas import WorkerResult, WorkerState
from app.resource.utils import (
    build_content_summary_data_with_llm,
    learning_need_from_task,
)

logger = get_logger(__name__)


class ContentAgent(Agent):
    """内容生成 Agent。"""

    AGENT_NAME = "content"
    ROLE_NAME = "课程内容智能体"
    STEPS = ["分析输入", "融合画像与依赖", "生成内容", "整理输出"]

    def _default_template_values(self) -> dict[str, str]:
        return {
            "structure": "progressive",
            "depth_level": "standard",
            "focus_mode": "key_concepts",
            "include_examples_instruction": "包含示例说明",
            "include_mistakes_instruction": "包含常见误区",
        }

    def _resolve_template_variables(self, variables: set, state: WorkerState) -> dict[str, str]:
        """Content Agent 特殊变量解析。"""
        result = super()._resolve_template_variables(variables, state)
        config = state.agent_config or {}

        # 布尔值转中文指令
        if "include_examples_instruction" in variables:
            result["include_examples_instruction"] = "包含示例和代码说明" if config.get("include_examples", True) else "不包含示例"
        if "include_mistakes_instruction" in variables:
            result["include_mistakes_instruction"] = "包含常见误区和易错点" if config.get("include_common_mistakes", True) else "不包含常见误区"

        return result

    async def _generate(self, state: WorkerState, prompt: str, input_text: str) -> WorkerResult:
        outline_only = state.outline_only

        if outline_only:
            return await self._generate_outline(state, prompt, input_text)
        else:
            return await self._generate_full(state, prompt, input_text)

    async def _generate_outline(self, state: WorkerState, prompt: str, input_text: str) -> WorkerResult:
        """阶段一: 仅生成大纲。"""
        outline_prompt = f"{prompt}\n\n{input_text}\n\n请只生成内容大纲，不要展开详细讲解。大纲需要包含各分支主题和关键知识点，以便其他 Agent 参考使用。"

        llm = get_llm()
        response = await llm.ainvoke(outline_prompt, temperature=0.3)

        content = response.content if hasattr(response, "content") else str(response)
        markdown = self._extract_markdown(content)

        return WorkerResult(
            success=True,
            content=markdown,
            file_type="markdown",
            title=self._title(state, "内容大纲"),
            summary="生成内容大纲",
            summary_data={"outline_only": True, "char_count": len(markdown)},
            metadata={"phase": "outline", "agent_id": "content"},
        )

    async def _generate_full(self, state: WorkerState, prompt: str, input_text: str) -> WorkerResult:
        """阶段二: 生成完整内容。"""
        # 如果有上游大纲，注入到输入中
        outline = state.outline or ""
        if outline:
            input_text = f"{input_text}\n\n## 参考大纲\n{outline}\n\n请基于以上大纲，生成完整的专业课程讲解文档。"

        llm = get_llm()
        response = await llm.ainvoke(f"{prompt}\n\n{input_text}", temperature=0.3)

        content = response.content if hasattr(response, "content") else str(response)
        markdown = self._extract_markdown(content)
        markdown = self._clean_content(markdown)

        # 构建 summary_data
        summary_data = await build_content_summary_data_with_llm(markdown, llm)

        return WorkerResult(
            success=True,
            content=markdown,
            file_type="markdown",
            title=self._title(state, "课程内容"),
            summary="生成专业课程讲解文档",
            summary_data=summary_data,
            metadata={"phase": "full", "char_count": len(markdown), "agent_id": "content"},
        )

    def _clean_content(self, content: str) -> str:
        """清理内容中的常见问题。"""
        lines = content.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if stripped in ("```", "```markdown", "```text"):
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    def _input_suffix(self) -> str:
        return "请生成专业课程讲解文档，只输出 Markdown 内容。"