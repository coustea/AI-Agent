"""
思维导图生成 Agent。
Agent 只负责生成 Markdown 内容，渲染和保存由代码直接处理。
"""

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.utils import append_context, load_prompt
from app.resource.agents.mindmap.utils import (
    NEED_MAP,
    extract_markdown_content,
    check_markdown_quality,
    render_markmap_html,
    save_mindmap_html,
)

logger = get_logger(__name__)


class MindmapGenerator:
    def __init__(self) -> None:
        self.name = "MindmapAgent"
        self.agent_dir = Path(__file__).parent
        self.prompt_template = load_prompt(self.agent_dir)
        self.llm_manager = get_llm_manager()
        self.model_kwargs = {"temperature": 0.1}

    def _build_system_message(self, state: dict[str, Any]) -> str:
        need_key = state.get("need", "review")
        need_text = NEED_MAP.get(need_key, need_key)
        prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", "待定"),
            topic=state.get("topic", "未知知识点"),
            gap=state.get("gap", "无"),
            need=need_text,
            extra=state.get("extra", "无"),
        )
        prompt += (
            "\n\n【执行指南】\n"
            "1. 严格基于用户当前请求生成内容，先满足主题、薄弱点和额外要求。\n"
            "2. 只输出 Markdown 思维导图内容，不要解释过程，不要分步规划，不要先输出提纲。\n"
            "3. 一级分支必须顶格写成 `- 分支名称`，不要在一级分支前加空格。\n"
            "4. 只在有助于理解或应用时适当拓展，不要默认生成百科式大而全导图。"
        )
        return append_context(prompt, state=state)

    def _build_initial_human_message(self, state: dict[str, Any]) -> str:
        topic = state.get("topic")
        gap = state.get("gap")
        need = state.get("need", "review")
        extra = state.get("extra", "")
        msg = f"请为知识点 '{topic}' 生成思维导图。"
        if gap and gap != "无":
            msg += f" 特别注意学生在 '{gap}' 方面存在薄弱环节，请在图中重点体现。"
            msg += " 如果主题范围很大，请围绕这个薄弱点生成导图，主题只作为必要背景，不要展开无关章节。"
        if need:
            msg += f" 本次导图目标为：{need}。"
        if extra:
            msg += f" 额外要求：{extra}。"
        return msg + " 请只输出可直接渲染的 Markdown 思维导图内容。"

    async def _validate_and_render(
        self,
        agent_output: str,
        retry_count: int,
        user_id: int,
        resource_id: int,
    ) -> dict[str, Any]:
        """验证 Markdown 内容并直接渲染保存。"""
        markdown_content = extract_markdown_content(agent_output)
        quality_ok, quality_feedback, node_count = check_markdown_quality(markdown_content)

        if not quality_ok or not markdown_content:
            return {
                "file_path": None,
                "html_content": None,
                "agent_output": agent_output,
                "markdown_content": markdown_content,
                "node_count": node_count,
                "is_valid": False,
                "retry_count": retry_count + 1,
                "validation_feedback": quality_feedback or "未检测到有效的 Markdown 内容。",
            }

        # 直接渲染和保存，不通过工具调用
        try:
            html_content = render_markmap_html(markdown_content)
            title = markdown_content.split("\n")[0].lstrip("# ").strip() or "思维导图"
            file_path = save_mindmap_html(title, html_content, user_id, resource_id)
        except Exception as exc:
            logger.exception("[MindmapAgent] 渲染或保存失败")
            return {
                "file_path": None,
                "html_content": None,
                "agent_output": agent_output,
                "markdown_content": markdown_content,
                "node_count": node_count,
                "is_valid": False,
                "retry_count": retry_count + 1,
                "validation_feedback": f"渲染或保存失败：{exc}",
            }

        return {
            "file_path": file_path,
            "html_content": html_content,
            "agent_output": agent_output,
            "markdown_content": markdown_content,
            "node_count": node_count,
            "is_valid": True,
            "retry_count": retry_count + 1,
            "validation_feedback": "",
        }

    async def _generate_markdown(self, system_prompt: str, user_message: str) -> str:
        """调用模型生成 Markdown 思维导图内容。"""
        response = await self.llm_manager.ainvoke(
            "spark_x",
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ],
            model_kwargs=self.model_kwargs,
        )
        content = getattr(response, "content", response)
        return content if isinstance(content, str) else str(content)

    async def generate_mindmap(
        self,
        topic: str = "",
        gap: str = "",
        course: str = "",
        major: str = "通用",
        need: str = "review",
        extra: str = "",
        user_profile: dict | None = None,
        shared_memory: dict | None = None,
        user_id: int = 0,
        resource_id: int = 0,
    ) -> dict[str, Any]:
        logger.info("[MindmapAgent] 收到生成请求: topic=%s gap=%s user_id=%s resource_id=%s", topic, gap, user_id, resource_id)
        state = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "need": need,
            "extra": extra,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
        }
        try:
            system_prompt = self._build_system_message(state)
            feedback = ""
            result: dict[str, Any] = {}
            for attempt in range(3):
                user_message = self._build_initial_human_message(state)
                if feedback:
                    user_message += f"\n\n上一次生成未通过校验，原因：{feedback}\n请重新生成合格的 Markdown 思维导图。"
                agent_output = await self._generate_markdown(system_prompt, user_message)
                result = await self._validate_and_render(agent_output, attempt, user_id, resource_id)
                if result.get("is_valid"):
                    break
                feedback = result.get("validation_feedback", "")
        except Exception as exc:
            logger.error("[MindmapAgent] 工作流执行失败: %s", exc)
            return {
                "success": False,
                "file_path": None,
                "html_content": None,
                "agent_output": "",
                "error": str(exc),
            }

        return {
            "success": result.get("is_valid", False),
            "file_path": result.get("file_path"),
            "html_content": result.get("html_content"),
            "agent_output": result.get("agent_output", ""),
            "markdown_content": result.get("markdown_content", ""),
            "node_count": result.get("node_count", 0),
            "error": result.get("validation_feedback") if not result.get("is_valid") else None,
        }


if __name__ == '__main__':
    import asyncio
    agent = MindmapGenerator()
    result = asyncio.run(agent.generate_mindmap(
        topic="计算机操作系统",
        gap="进程之间的调度薄弱",
        course="操作系统",
    ))
    print(json.dumps(result, ensure_ascii=False, indent=2))
