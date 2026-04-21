"""
拓展阅读推荐 Agent。
轻量实现：直接生成结构化推荐列表，并支持 Markdown 文件追加阅读章节。
"""

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.infra.llm import get_deepseek_chat_llm
from app.infra.logging import get_logger
from app.resource.agent_support import append_context, format_profile_fields, load_prompt, save_to_workplace

logger = get_logger(__name__)


class ReadingItem(BaseModel):
    title: str
    author_or_source: str
    abstract: str
    relevance: str
    type: str


class ReadingOutput(BaseModel):
    recommendations: list[ReadingItem]


class ReadingAgent:
    def __init__(self) -> None:
        self.name = "ReadingAgent"
        self.agent_dir = Path(__file__).parent
        self.prompt_template = load_prompt(self.agent_dir)
        self.llm = get_deepseek_chat_llm(temperature=0.3)

    @staticmethod
    def _extract_memory(shared_memory: dict[str, Any]) -> str:
        outline = ((shared_memory or {}).get("content") or {}).get("outline", "")
        return f"【内容大纲】\n{outline}\n" if outline else ""

    @staticmethod
    def _format_user_profile(profile: dict[str, Any]) -> str:
        return format_profile_fields(
            profile,
            [
                ("interest_preference", "兴趣偏好"),
                ("cognitive_style", "认知风格"),
            ],
        )

    def _build_system_message(self, state: dict[str, Any]) -> str:
        user_profile = state.get("user_profile", {})
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            interest_preference=user_profile.get("interest_preference", ""),
            cognitive_style=user_profile.get("cognitive_style", ""),
        )
        return append_context(
            system_prompt,
            state=state,
            format_user_profile=self._format_user_profile,
            extract_memory=self._extract_memory,
        )

    @staticmethod
    def _looks_like_tool_error(text: str) -> bool:
        value = (text or "").strip()
        if not value:
            return True
        if value.startswith("\u2713"):
            return False
        if value.startswith("\u274c"):
            return True
        return value.startswith(("ERROR", "Error", "Traceback", "Exception"))

    @staticmethod
    def _render_reading_section(items: list[dict[str, Any]]) -> str:
        lines: list[str] = ["## Suggested Reading", ""]
        for idx, item in enumerate(items, start=1):
            lines.extend(
                [
                    f"### {idx}. {item.get('title', 'Untitled Resource')}",
                    f"- Source: {item.get('author_or_source', 'Unknown')}",
                    f"- Type: {item.get('type', 'Unknown')}",
                    f"- Relevance: {item.get('relevance', 'Not specified')}",
                    f"- Abstract: {item.get('abstract', '').strip()}",
                    "",
                ]
            )
        return "\n".join(lines).strip()

    async def _generate_recommendations(self, state: dict[str, Any]) -> ReadingOutput:
        prompt = self._build_system_message(state)
        human = f"请为主题 '{state.get('topic')}' 生成推荐阅读清单。"
        structured_llm = self.llm.with_structured_output(ReadingOutput)
        return ReadingOutput.model_validate(await structured_llm.ainvoke([HumanMessage(content=prompt), HumanMessage(content=human)]))

    async def _operate_markdown_file(
        self,
        *,
        topic: str,
        target_md_path: str,
        edit_instruction: str = "",
        output_md_path: str | None = None,
    ) -> dict[str, Any]:
        from app.tools.registry import get as get_tool

        read_result = get_tool("read_file_safe").invoke({"file_path": target_md_path})
        markdown_text = read_result if isinstance(read_result, str) else str(read_result)
        if self._looks_like_tool_error(markdown_text):
            return {
                "success": False,
                "recommendations": [],
                "file_path": None,
                "raw_json": "",
                "error": f"Failed to read Markdown: {markdown_text}",
            }

        effective_instruction = edit_instruction.strip() or "Add high-quality reading recommendations grounded in the current document."
        prompt = (
            "You are a reading recommendation assistant. Generate structured recommendations from the Markdown document.\n"
            f"Topic: {topic}\n"
            f"Instruction: {effective_instruction}\n"
            "Recommendations must be document-grounded, not generic.\n\n"
            "Markdown content:\n"
            f"{markdown_text}"
        )
        structured_llm = self.llm.with_structured_output(ReadingOutput)
        validated = ReadingOutput.model_validate(await structured_llm.ainvoke([HumanMessage(content=prompt)]))
        items = [item.model_dump() for item in validated.recommendations]
        if len(items) < 3:
            return {
                "success": False,
                "recommendations": [],
                "file_path": None,
                "raw_json": "",
                "error": f"Insufficient recommendations ({len(items)}). Need at least 3.",
            }

        section = self._render_reading_section(items)
        separator = "\n\n" if markdown_text.strip() else ""
        merged_markdown = f"{markdown_text.rstrip()}{separator}{section}\n"
        write_path = output_md_path or target_md_path
        write_result = get_tool("write_file").invoke({"filepath": write_path, "content": merged_markdown, "create_dirs": True})
        write_text = write_result if isinstance(write_result, str) else str(write_result)
        if self._looks_like_tool_error(write_text):
            return {
                "success": False,
                "recommendations": items,
                "file_path": None,
                "raw_json": json.dumps({"recommendations": items}, ensure_ascii=False),
                "error": f"Failed to write Markdown: {write_text}",
            }

        return {
            "success": True,
            "recommendations": items,
            "file_path": write_path,
            "raw_json": json.dumps({"recommendations": items}, ensure_ascii=False),
            "content": merged_markdown,
            "error": None,
        }

    async def generate_reading(
        self,
        topic: str,
        course: str = "",
        major: str = "general",
        gap: str = "",
        user_profile: dict | None = None,
        shared_memory: dict | None = None,
        target_md_path: str | None = None,
        edit_instruction: str = "",
        output_md_path: str | None = None,
    ) -> dict[str, Any]:
        logger.info("[ReadingAgent] Request received: topic=%s", topic)
        if target_md_path:
            return await self._operate_markdown_file(
                topic=topic or "Markdown Document",
                target_md_path=target_md_path,
                edit_instruction=edit_instruction,
                output_md_path=output_md_path,
            )

        state = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
        }
        try:
            output = await self._generate_recommendations(state)
        except Exception as exc:
            logger.error("[ReadingAgent] Workflow execution failed: %s", exc)
            return {"success": False, "recommendations": [], "raw_json": "", "error": str(exc)}

        parsed = [item.model_dump() for item in output.recommendations]
        raw_json = json.dumps({"recommendations": parsed}, ensure_ascii=False)
        file_path = save_to_workplace("reading", topic, json.dumps(parsed, ensure_ascii=False, indent=2), "json")
        return {
            "success": bool(parsed),
            "recommendations": parsed,
            "file_path": file_path,
            "raw_json": raw_json,
            "error": None if parsed else "empty recommendations",
        }
