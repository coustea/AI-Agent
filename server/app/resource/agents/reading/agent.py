"""
拓展阅读推荐 Agent。
轻量实现：直接生成结构化推荐列表，并支持 Markdown 文件追加阅读章节。
"""

import json
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.utils import append_context, format_profile_fields, load_prompt, save_resource_file

logger = get_logger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


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
        self.llm_manager = get_llm_manager()
        self.model_kwargs = {"temperature": 0.3}

    @staticmethod
    def _extract_memory(shared_memory: dict[str, Any]) -> str:
        outline = ((shared_memory or {}).get("content") or {}).get("outline", "")
        return f"【内容大纲】\n{outline}\n" if outline else ""

    @staticmethod
    def _format_user_profile(profile: dict[str, Any]) -> str:
        """格式化用户画像，从 profile_markdown 中提取兴趣和认知风格信息。"""
        profile_markdown = profile.get("profile_markdown", "")
        if not profile_markdown:
            return ""

        # 解析 Markdown 提取相关字段
        sections: dict[str, str] = {}
        current_section: str | None = None
        current_content: list[str] = []

        for line in profile_markdown.split("\n"):
            if line.startswith("## "):
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line[3:].strip()
                current_content = []
            else:
                if current_section:
                    current_content.append(line)
        if current_section and current_content:
            sections[current_section] = "\n".join(current_content).strip()

        parts: list[str] = []
        if "兴趣方向" in sections:
            parts.append(f"- 兴趣偏好：{sections['兴趣方向']}")
        if "认知风格" in sections:
            parts.append(f"- 认知风格：{sections['认知风格']}")
        return "\n".join(parts)

    def _build_system_message(self, state: dict[str, Any]) -> str:
        user_profile = state.get("user_profile", {})
        profile_markdown = user_profile.get("profile_markdown", "")

        # 解析 Markdown 提取兴趣和认知风格
        interest_preference = ""
        cognitive_style = ""
        sections: dict[str, str] = {}
        current_section: str | None = None
        current_content: list[str] = []

        for line in profile_markdown.split("\n"):
            if line.startswith("## "):
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line[3:].strip()
                current_content = []
            else:
                if current_section:
                    current_content.append(line)
        if current_section and current_content:
            sections[current_section] = "\n".join(current_content).strip()

        if "兴趣方向" in sections:
            interest_preference = sections["兴趣方向"]
        if "认知风格" in sections:
            cognitive_style = sections["认知风格"]

        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            interest_preference=interest_preference,
            cognitive_style=cognitive_style,
        )
        return append_context(
            system_prompt,
            state=state,
            format_user_profile=self._format_user_profile,
            extract_memory=self._extract_memory,
        )

    @staticmethod
    def _render_reading_section(items: list[dict[str, Any]]) -> str:
        lines: list[str] = ["# 拓展阅读", ""]
        for idx, item in enumerate(items, start=1):
            lines.extend(
                [
                    f"### {idx}. {item.get('title', 'Untitled Resource')}",
                    f"- 来源：{item.get('author_or_source', 'Unknown')}",
                    f"- 类型：{item.get('type', 'Unknown')}",
                    f"- 推荐理由：{item.get('relevance', 'Not specified')}",
                    f"- 摘要：{item.get('abstract', '').strip()}",
                    "",
                ]
            )
        return "\n".join(lines).strip()

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, Any]:
        raw = str(text or "").strip()
        if not raw:
            raise ValueError("模型返回为空，无法提取阅读推荐 JSON")

        match = _JSON_FENCE_RE.search(raw)
        if match:
            raw = match.group(1).strip()

        if not raw.startswith("{"):
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                raw = raw[start:end + 1]

        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("阅读推荐 JSON 顶层必须是对象")
        return parsed

    async def _generate_recommendations(self, state: dict[str, Any]) -> ReadingOutput:
        prompt = self._build_system_message(state)
        human = (
            f"请为主题 '{state.get('topic')}' 生成推荐阅读清单。"
            "只输出合法 JSON 对象，不要 Markdown 代码块和解释文字。"
            "JSON 格式："
            '{"recommendations":[{"title":"资源标题","author_or_source":"作者或来源",'
            '"abstract":"摘要","relevance":"与主题的关联","type":"book|paper|article|course|docs"}]}'
            "至少返回 3 条推荐。"
        )
        response = await self.llm_manager.ainvoke(
            "deepseek",
            [
                SystemMessage(content=prompt),
                HumanMessage(content=human),
            ],
            model_kwargs=self.model_kwargs,
        )
        raw_content = getattr(response, "content", response)
        return ReadingOutput.model_validate(self._extract_json_object(str(raw_content)))

    async def _operate_markdown_file(
        self,
        *,
        topic: str,
        target_md_path: str,
        edit_instruction: str = "",
        output_md_path: str | None = None,
    ) -> dict[str, Any]:
        try:
            markdown_text = Path(target_md_path).read_text(encoding="utf-8")
        except Exception as exc:
            return {
                "success": False,
                "recommendations": [],
                "file_path": None,
                "raw_json": "",
                "error": f"Failed to read Markdown: {exc}",
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
        response = await self.llm_manager.ainvoke(
            "deepseek",
            [
                HumanMessage(
                    content=(
                        f"{prompt}\n\n"
                        "只输出合法 JSON 对象，不要 Markdown 代码块和解释文字。"
                        'JSON 顶层格式为 {"recommendations":[...]}，至少 3 条。'
                    )
                )
            ],
            model_kwargs=self.model_kwargs,
        )
        raw_content = getattr(response, "content", response)
        validated = ReadingOutput.model_validate(self._extract_json_object(str(raw_content)))
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
        try:
            path = Path(write_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(merged_markdown, encoding="utf-8")
        except Exception as exc:
            return {
                "success": False,
                "recommendations": items,
                "file_path": None,
                "raw_json": json.dumps({"recommendations": items}, ensure_ascii=False),
                "error": f"Failed to write Markdown: {exc}",
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
        user_id: int = 0,
        resource_id: int = 0,
    ) -> dict[str, Any]:
        logger.info("[ReadingAgent] Request received: topic=%s user_id=%s resource_id=%s", topic, user_id, resource_id)
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
        markdown_content = self._render_reading_section(parsed) if parsed else ""
        file_path = None
        if parsed and user_id and resource_id:
            file_path = save_resource_file(topic, markdown_content, user_id, resource_id, "md", prefix="reading")
            logger.info("[ReadingAgent] 文件已保存: %s", file_path)
        return {
            "success": bool(parsed),
            "recommendations": parsed,
            "content": markdown_content,
            "markdown_content": markdown_content,
            "file_path": file_path,
            "raw_json": raw_json,
            "error": None if parsed else "empty recommendations",
        }
