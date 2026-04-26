"""
内容创作 Agent。
简化实现：大模型仅输出 Markdown 文本，Python 代码处理保存逻辑。
"""

import asyncio
import re
import shutil
import time
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.config import CONTENT_AGENT_TIMEOUT_SECONDS
from app.infra.llm import get_spark_x_llm
from app.infra.logging import get_logger
from app.resource.utils import append_context, load_prompt

logger = get_logger(__name__)

_SERVER_ROOT = Path(__file__).resolve().parents[4]
_SKILLS_ROOT = _SERVER_ROOT / "app" / "skills"
_GENERATED_SKILLS_ROOT = _SERVER_ROOT / ".deepagents" / "skills"

# 文本长度阈值：超过此值则保存到文件
MAX_INLINE_CONTENT_LENGTH = 8000


def _save_content_to_file(sub_dir: str, topic: str, content: str) -> str:
    """保存内容到 workplace 目录，返回文件路径。"""
    from app.tools.registry import get as get_tool
    return get_tool("save_to_workplace").invoke(
        {"sub_dir": sub_dir, "topic": topic, "content": content, "ext": "md"}
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
    """内容创作 Agent：生成 Markdown 课程讲解文档。"""

    skill_names = ["docx", "pdf"]

    def __init__(self) -> None:
        self.name = "ContentAgent"
        self.agent_dir = Path(__file__).parent
        self.prompt_template = load_prompt(self.agent_dir)
        self.llm = get_spark_x_llm(temperature=0.3)

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
    def _looks_like_refusal(content: str) -> bool:
        text = (content or "").strip()
        if not text:
            return True
        refusal_markers = (
            "无法按照要求完成", "无法完成", "请补充", "请您补充",
            "未提供具体的大纲", "未提供大纲", "请提供大纲", "需要更多信息",
        )
        return any(marker in text for marker in refusal_markers)

    async def _run_deepagents_text(
        self, *, state: dict[str, Any], user_message: str, thread_id: str
    ) -> str:
        agent = create_deep_agent(
            name="content-agent",
            model=self.llm,
            tools=[],
            system_prompt=self._build_system_message(state),
            backend=FilesystemBackend(root_dir=_SERVER_ROOT, virtual_mode=True),
            skills=[_materialize_skill_bundle(self.skill_names, "content-agent")],
            checkpointer=MemorySaver(),
        )
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config={"configurable": {"thread_id": thread_id}},
        )
        return self._strip_markdown_fence(_extract_agent_text(result))

    async def _fallback_generate_content(self, state: dict[str, Any]) -> str:
        """降级生成：直接调用 LLM 生成 Markdown。"""
        prompt = (
            "你是一位高校课程讲解文档作者。请直接生成一份完整的 Markdown 课程讲解文档，"
            "不要追问用户，不要输出额外说明。\n\n"
            f"专业：{state.get('major', '通用')}\n"
            f"课程：{state.get('course', '')}\n"
            f"主题：{state.get('topic', '')}\n"
            f"知识短板：{state.get('gap', '')}\n\n"
            "要求：\n"
            "1. 必须包含：概述、核心讲解、案例分析、常见误区、总结\n"
            "2. 字数 1500-3000 字\n"
            "3. 面向初学者，讲解清晰具体\n"
            "4. 直接输出 Markdown 文档\n"
        )
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return self._strip_markdown_fence(
            response.content if hasattr(response, "content") else str(response)
        )

    async def generate_content(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict | None = None,
        shared_memory: dict | None = None,
    ) -> dict[str, Any]:
        """生成 Markdown 内容。

        Returns:
            - content: Markdown 正文（始终返回）
            - file_path: 文件路径（仅当内容超过阈值时）
            - error: 错误信息（如果失败）
        """
        logger.info("[ContentAgent] 收到生成请求: topic=%s", topic)
        start_time = time.perf_counter()
        timeout_seconds = self._workflow_timeout_seconds()

        state = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
        }

        content = ""
        try:
            # 生成大纲
            outline = await asyncio.wait_for(
                self._run_deepagents_text(
                    state=state,
                    user_message="请先为这份讲解文档生成一份详细的大纲（列出各章节标题及每节要点的简短描述）。",
                    thread_id=f"content:outline:{topic or 'default'}",
                ),
                timeout=timeout_seconds,
            )
            state["outline"] = outline

            # 生成正文
            outline_text = outline.strip() or "请按标准教学文档结构自行组织。"
            content_request = (
                "请根据以下大纲撰写完整的专业讲解文档（1500-3000字），"
                "严格遵循大纲结构，每个章节都要有充实的内容。"
                "不要向用户追问补充信息，直接完成正文写作。\n\n"
                f"现有大纲：\n{outline_text}"
            )
            content = await asyncio.wait_for(
                self._run_deepagents_text(
                    state=state,
                    user_message=content_request,
                    thread_id=f"content:content:{topic or 'default'}",
                ),
                timeout=timeout_seconds,
            )
        except Exception:
            logger.exception("[ContentAgent] deepagents 工作流失败，尝试降级生成")
            try:
                content = await self._fallback_generate_content(state)
            except Exception:
                logger.exception("[ContentAgent] 降级生成失败")

        # 检查生成结果
        if not content or self._looks_like_refusal(content):
            logger.error("[ContentAgent] 生成失败：内容为空或拒绝响应")
            return {
                "content": "",
                "file_path": None,
                "error": "生成失败：模型未返回有效内容",
            }

        # 处理保存逻辑
        file_path = None
        if len(content) > MAX_INLINE_CONTENT_LENGTH:
            file_path = _save_content_to_file("content", topic, content)
            logger.info("[ContentAgent] 内容已保存到文件: %s", file_path)

        elapsed = time.perf_counter() - start_time
        logger.info("[ContentAgent] 执行结束: len=%d elapsed=%.2fs", len(content), elapsed)

        return {
            "content": content,
            "file_path": file_path,
            "error": None,
        }
