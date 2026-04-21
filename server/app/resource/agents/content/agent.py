"""
内容创作 Agent。
轻量实现：直接生成 Markdown 大纲与正文，必要时调用 deepagents + skills。
"""

import asyncio
import json
import re
import shlex
import shutil
import time
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from app.config import CONTENT_AGENT_TIMEOUT_SECONDS
from app.infra.llm import get_deepseek_chat_llm
from app.infra.logging import get_logger
from app.resource.agent_support import append_context, load_prompt, load_registered_tools, save_to_workplace
from app.tools.registry import get as get_tool

logger = get_logger(__name__)

_SERVER_ROOT = Path(__file__).resolve().parents[4]
_SKILLS_ROOT = _SERVER_ROOT / "app" / "skills"
_GENERATED_SKILLS_ROOT = _SERVER_ROOT / ".deepagents" / "skills"


class ReviewResult(BaseModel):
    passed: bool = Field(description="是否通过审查")
    feedback: str = Field(default="", description="如果不通过，说明具体原因和改进建议")


_REVIEW_PROMPT = (
    "你是一位教学文档质量审查专家。请审查以下课程讲解文档的质量。\n\n"
    "## 审查标准\n"
    "1. 字数检查：文档正文应在 1500-3000 字之间\n"
    "2. 结构完整性：是否包含 概述、核心讲解、案例分析、常见误区、总结 等主要章节\n"
    "3. 内容针对性：是否围绕主题 {topic} 深入展开，而非泛泛而谈\n"
    "4. 个性化匹配：是否考虑了用户画像中描述的学习特点\n"
    "5. 案例质量：是否包含至少一个完整的实际案例\n\n"
    "## 待审查文档\n"
    "{content}\n\n"
    "## 大纲\n"
    "{outline}\n\n"
)


def _materialize_skill_bundle(skill_names: list[str], bundle_name: str) -> str:
    bundle_dir = _GENERATED_SKILLS_ROOT / bundle_name
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    for skill_name in skill_names:
        skill_dir = _SKILLS_ROOT / skill_name
        if not (skill_dir / "SKILL.md").exists():
            raise FileNotFoundError(f"Missing skill directory: {skill_name}")
        shutil.copytree(skill_dir, bundle_dir / skill_name, dirs_exist_ok=True)
    return bundle_dir.relative_to(_SERVER_ROOT).as_posix()


def _extract_agent_text(result: dict[str, Any]) -> str:
    messages = result.get("messages", [])
    for message in reversed(messages):
        content = getattr(message, "content", "")
        if isinstance(content, str) and content.strip():
            return content
    return ""


class ContentWriter:
    tool_names = [
        "save_to_workplace", "read_file_safe",
        "write_file", "edit_file", "append_file", "read_file_lines",
        "list_directory", "file_tree", "find_files", "get_file_info",
        "save_docx_file", "extract_pdf_text",
    ]
    skill_names = ["docx", "pdf"]
    _TEXT_ASSET_EXTS = {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".toml", ".ini", ".xml", ".html"}

    def __init__(self) -> None:
        self.name = "ContentAgent"
        self.agent_dir = Path(__file__).parent
        self.prompt_template = load_prompt(self.agent_dir)
        self.llm = get_deepseek_chat_llm(temperature=0.3)
        self._review_llm = self.llm.with_structured_output(ReviewResult)
        self._tools = load_registered_tools(self.tool_names)

    @staticmethod
    def _workflow_timeout_seconds() -> int:
        return CONTENT_AGENT_TIMEOUT_SECONDS

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        mm = ((shared_memory or {}).get("mindmap") or {}).get("agent_output", "")
        return f"【思维导图核心结构】\n{mm}\n" if mm else ""

    def _build_system_message(self, state: dict[str, Any]) -> str:
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            user_profile="",
        )
        return append_context(system_prompt, state=state, extract_memory=self._extract_memory)

    @staticmethod
    def _strip_markdown_fence(text: str) -> str:
        value = (text or "").strip()
        if value.startswith("```"):
            value = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", value)
            value = re.sub(r"\s*```$", "", value)
        return value.strip()

    @staticmethod
    def _build_content_request(outline: str) -> str:
        outline_text = outline.strip() or "请沿用你刚刚生成的大纲结构。"
        return (
            "请根据以下大纲撰写完整的专业讲解文档（1500-3000字），严格遵循大纲结构，每个章节都要有充实的内容。"
            "不要向用户追问补充信息，直接完成正文写作。\n\n"
            f"现有大纲：\n{outline_text}"
        )

    @staticmethod
    def _looks_like_refusal(content: str) -> bool:
        text = (content or "").strip()
        if not text:
            return True
        refusal_markers = ("无法按照要求完成", "无法完成", "请补充", "请您补充", "未提供具体的大纲", "未提供大纲", "请提供大纲", "需要更多信息")
        return any(marker in text for marker in refusal_markers)

    @classmethod
    def _needs_content_recovery(cls, content: str) -> bool:
        text = (content or "").strip()
        return cls._looks_like_refusal(text) or len(text) < 500

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

    async def _rewrite_markdown_file(
        self,
        *,
        topic: str,
        target_md_path: str,
        edit_instruction: str = "",
        output_md_path: str | None = None,
    ) -> dict[str, Any]:
        read_result = get_tool("read_file_safe").invoke({"file_path": target_md_path})
        current_markdown = read_result if isinstance(read_result, str) else str(read_result)
        if self._looks_like_tool_error(current_markdown):
            return {"success": False, "content": "", "outline": "", "file_path": None, "docx_path": None, "pdf_path": None, "error": f"读取 Markdown 失败: {current_markdown}"}

        effective_instruction = edit_instruction.strip() or "在不改变原主题的前提下优化结构、补充关键知识点和示例，并保持 Markdown 格式规范。"
        prompt = (
            "你是专业 Markdown 文档编辑器。请基于编辑要求改写文档，仅输出最终 Markdown 正文，不要解释，不要代码块围栏。\n\n"
            f"主题：{topic}\n编辑要求：{effective_instruction}\n\n原始 Markdown：\n{current_markdown}"
        )
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        rewritten = self._strip_markdown_fence(response.content if hasattr(response, "content") else str(response))
        if not rewritten:
            return {"success": False, "content": "", "outline": "", "file_path": None, "docx_path": None, "pdf_path": None, "error": "Markdown 改写失败：模型未返回有效内容"}

        write_path = output_md_path or target_md_path
        write_result = get_tool("write_file").invoke({"filepath": write_path, "content": rewritten, "create_dirs": True})
        write_text = write_result if isinstance(write_result, str) else str(write_result)
        if self._looks_like_tool_error(write_text):
            return {"success": False, "content": rewritten, "outline": "", "file_path": None, "docx_path": None, "pdf_path": None, "error": f"写入 Markdown 失败: {write_text}"}

        return {"success": True, "content": rewritten, "outline": "", "file_path": write_path, "docx_path": None, "pdf_path": None, "skill_usage_report": {}, "skill_postprocess": {}, "error": None}

    async def _run_deepagents_text(self, *, state: dict[str, Any], user_message: str, thread_id: str) -> str:
        agent = create_deep_agent(
            name="content-agent",
            model=self.llm,
            tools=[],
            system_prompt=self._build_system_message(state),
            backend=FilesystemBackend(root_dir=_SERVER_ROOT, virtual_mode=True),
            skills=[_materialize_skill_bundle(self.skill_names, "content-agent")],
            checkpointer=MemorySaver(),
        )
        result = await agent.ainvoke({"messages": [{"role": "user", "content": user_message}]}, config={"configurable": {"thread_id": thread_id}})
        return self._strip_markdown_fence(_extract_agent_text(result))

    async def _validate_content(self, *, topic: str, content: str, outline: str) -> tuple[bool, str]:
        if not content:
            return False, "未生成正文，请基于现有大纲直接补全完整讲解文档，不要追问用户。"
        word_count = len(content)
        if word_count < 800:
            return False, f"文档字数仅 {word_count} 字，远低于 1500 字的最低要求，请大幅扩展。"
        prompt = _REVIEW_PROMPT.format(topic=topic, content=content[:3000], outline=outline[:1000])
        try:
            review = await self._review_llm.ainvoke([HumanMessage(content=prompt)])
            if isinstance(review, ReviewResult):
                return review.passed, review.feedback
        except Exception:
            logger.exception("[ContentAgent] 审查失败")
        return True, ""

    async def _fallback_generate_content(self, state: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "你是一位高校课程讲解文档作者。请直接生成一份完整的 Markdown 课程讲解文档，不要追问用户，不要输出额外说明。\n\n"
            f"专业：{state.get('major', '通用')}\n课程：{state.get('course', '')}\n主题：{state.get('topic', '')}\n知识短板：{state.get('gap', '')}\n参考大纲：\n{state.get('outline', '') or '请按标准教学文档结构自行组织'}\n"
            "要求：\n1. 必须包含：概述、核心讲解、案例分析、常见误区、总结\n2. 字数尽量充实，至少 1200 字\n3. 面向初学者，讲解清晰具体\n4. 直接输出最终 Markdown 文档\n5. 严禁向用户索要补充信息，必须直接完成全文\n6. 控制在 1500-3000 字之间，不要过长\n"
        )
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip() if isinstance(response.content, str) else str(response.content)
        return {"content": content, "outline": "1. 概述\n2. 核心讲解\n3. 案例分析\n4. 常见误区\n5. 总结", "error": None}

    async def _run_skill_postprocess(self, docx_path: str | None, pdf_path: str | None) -> dict[str, str]:
        postprocess: dict[str, str] = {}
        tool_map = {tool.name: tool for tool in (self._tools or [])}
        if docx_path and "skill_run" in tool_map:
            try:
                output = await tool_map["skill_run"].ainvoke({"name": "docx", "script_path": "scripts/office/validate.py", "script_args": shlex.quote(docx_path), "timeout_sec": 90})
                if output:
                    postprocess["docx_validate"] = str(output)
            except Exception:
                logger.exception("[ContentAgent] DOCX 技能后处理失败")
        if pdf_path and "skill_run" in tool_map:
            try:
                output = await tool_map["skill_run"].ainvoke({"name": "pdf", "script_path": "scripts/check_fillable_fields.py", "script_args": shlex.quote(pdf_path), "timeout_sec": 60})
                if output:
                    postprocess["pdf_check_fillable_fields"] = str(output)
            except Exception:
                logger.exception("[ContentAgent] PDF 技能后处理失败")
        return postprocess

    async def generate_content(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict | None = None,
        shared_memory: dict | None = None,
        target_md_path: str | None = None,
        edit_instruction: str = "",
        output_md_path: str | None = None,
    ) -> dict[str, Any]:
        logger.info("[ContentAgent] 收到生成请求: topic=%s", topic)
        if target_md_path:
            return await self._rewrite_markdown_file(topic=topic or "Markdown 文档", target_md_path=target_md_path, edit_instruction=edit_instruction, output_md_path=output_md_path)

        start_time = time.perf_counter()
        timeout_seconds = self._workflow_timeout_seconds()
        state = {"major": major, "course": course, "topic": topic, "gap": gap, "user_profile": user_profile or {}, "shared_memory": shared_memory or {}, "outline": ""}
        skill_usage_report = {"mode": "deepagents", "skills": list(self.skill_names)}

        try:
            outline = await asyncio.wait_for(self._run_deepagents_text(state=state, user_message="请先为这份讲解文档生成一份详细的大纲（列出各章节标题及每节要点的简短描述）。", thread_id=f"content:outline:{topic or 'default'}"), timeout=timeout_seconds)
            state["outline"] = outline
            content = await asyncio.wait_for(self._run_deepagents_text(state=state, user_message=self._build_content_request(outline), thread_id=f"content:content:{topic or 'default'}:0"), timeout=timeout_seconds)
            passed, feedback = await self._validate_content(topic=topic, content=content, outline=outline)
            retry_count = 0
            while not passed and retry_count < 2:
                retry_count += 1
                content = await asyncio.wait_for(
                    self._run_deepagents_text(
                        state=state,
                        user_message=f"上一次正文未通过审查，原因：{feedback}\n请基于现有大纲重新撰写完整的专业讲解文档，不要向用户追问额外信息。\n\n现有大纲：\n{outline or '请沿用你刚刚生成的大纲结构。'}",
                        thread_id=f"content:content:{topic or 'default'}:{retry_count}",
                    ),
                    timeout=timeout_seconds,
                )
                passed, feedback = await self._validate_content(topic=topic, content=content, outline=outline)
            result = {"outline": outline, "content": content, "error": None if passed else feedback}
        except Exception:
            logger.exception("[ContentAgent] deepagents 工作流失败，尝试降级生成")
            result = await self._fallback_generate_content(state)

        content = result.get("content", "")
        outline = result.get("outline", "")
        if self._needs_content_recovery(content):
            try:
                state["outline"] = outline
                fallback = await self._fallback_generate_content(state)
                content = fallback.get("content", "")
                outline = fallback.get("outline", outline)
            except Exception:
                logger.exception("[ContentAgent] 降级生成失败")

        success = bool(content)
        file_path = None
        docx_path = None
        pdf_path = None
        skill_postprocess: dict[str, str] = {}
        if success:
            file_path = save_to_workplace("content", topic, content, "md")
            try:
                saved_content = Path(file_path).read_text(encoding="utf-8")
                if saved_content.strip():
                    content = saved_content
            except Exception:
                logger.exception("[ContentAgent] 文档已保存，但回读文件失败: %s", file_path)
            try:
                docx_result = json.loads(get_tool("save_docx_file").invoke({"title": topic, "content": content}))
                docx_path = docx_result.get("file_path")
            except Exception:
                logger.exception("[ContentAgent] DOCX 生成失败")
            try:
                pdf_result = json.loads(get_tool("save_pdf_file").invoke({"title": topic, "content": content}))
                pdf_path = pdf_result.get("file_path")
            except Exception:
                logger.exception("[ContentAgent] PDF 生成失败")
            try:
                skill_postprocess = await self._run_skill_postprocess(docx_path, pdf_path)
            except Exception:
                logger.exception("[ContentAgent] 技能后处理脚本执行失败")

        logger.info("[ContentAgent] 执行结束: success=%s elapsed=%.2fs", success, time.perf_counter() - start_time)
        return {
            "success": success,
            "content": content,
            "outline": outline,
            "file_path": file_path,
            "docx_path": docx_path,
            "pdf_path": pdf_path,
            "skill_usage_report": skill_usage_report,
            "skill_postprocess": skill_postprocess,
            "error": result.get("error") if not success else None,
        }
