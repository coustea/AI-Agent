"""
内容创作 Agent。
简化实现：大模型仅输出 Markdown 文本，Python 代码处理保存逻辑。
"""

import asyncio
import re
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import CONTENT_AGENT_TIMEOUT_SECONDS
from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.utils import append_context, load_prompt
from app.shared.paths import RESOURCE_DIR

logger = get_logger(__name__)

# 文本长度阈值：超过此值则保存到文件
MAX_INLINE_CONTENT_LENGTH = 8000


def _save_content_directly(
    topic: str,
    content: str,
    user_id: int,
    resource_id: int,
) -> str:
    """直接保存内容到 workplace 目录（不使用工具）。

    路径格式: workplace/{user_id}/{resource_id}/{topic}.md

    Args:
        topic: 主题名称
        content: Markdown 内容
        user_id: 用户 ID
        resource_id: 资源 ID

    Returns:
        文件路径
    """
    import re
    safe_topic = re.sub(r'[\\/*?:"<>|]', "", topic).strip()[:50]
    if not safe_topic:
        safe_topic = "untitled"

    target_dir = RESOURCE_DIR / str(user_id) / str(resource_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{safe_topic}.md"
    filepath = target_dir / filename

    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


class ContentWriter:
    """内容创作 Agent：生成 Markdown 课程讲解文档。"""

    def __init__(self) -> None:
        self.name = "ContentAgent"
        self.agent_dir = Path(__file__).parent
        self.prompt_template = load_prompt(self.agent_dir)
        self.llm_manager = get_llm_manager()
        self.model_kwargs = {"temperature": 0.3}

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

    async def _generate_text(self, system_prompt: str, user_message: str) -> str:
        """调用模型直接生成文本内容。"""
        response = await self.llm_manager.ainvoke(
            "spark_x",
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ],
            model_kwargs=self.model_kwargs,
        )
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
        user_id: int = 0,
        resource_id: int = 0,
    ) -> dict[str, Any]:
        """生成 Markdown 内容。

        Args:
            topic: 主题
            course: 课程名称
            major: 专业
            gap: 知识薄弱点
            user_profile: 用户画像
            shared_memory: 共享记忆（黑板）
            user_id: 用户 ID，用于保存文件
            resource_id: 资源 ID，用于保存文件

        Returns:
            - content: Markdown 正文（始终返回）
            - file_path: 文件路径（仅当内容超过阈值时）
            - error: 错误信息（如果失败）
        """
        logger.info("[ContentAgent] 收到生成请求: topic=%s user_id=%s resource_id=%s", topic, user_id, resource_id)
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
            system_prompt = self._build_system_message(state)
            # 生成大纲
            outline = await asyncio.wait_for(
                self._generate_text(
                    system_prompt,
                    "请先为这份讲解文档生成一份详细的大纲（列出各章节标题及每节要点的简短描述）。",
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
                self._generate_text(
                    system_prompt,
                    content_request,
                ),
                timeout=timeout_seconds,
            )
        except Exception as exc:
            logger.exception("[ContentAgent] 内容生成失败")
            return {
                "success": False,
                "content": "",
                "outline": state.get("outline", ""),
                "file_path": None,
                "error": str(exc),
            }

        # 检查生成结果
        if not content or self._looks_like_refusal(content):
            logger.error("[ContentAgent] 生成失败：内容为空或拒绝响应")
            return {
                "success": False,
                "content": "",
                "outline": state.get("outline", ""),
                "file_path": None,
                "error": "生成失败：模型未返回有效内容",
            }

        # 处理保存逻辑：超过阈值则保存到文件
        file_path = None
        if len(content) > MAX_INLINE_CONTENT_LENGTH and user_id and resource_id:
            file_path = _save_content_directly(topic, content, user_id, resource_id)
            logger.info("[ContentAgent] 内容已保存到文件: %s", file_path)

        elapsed = time.perf_counter() - start_time
        logger.info("[ContentAgent] 执行结束: len=%d elapsed=%.2fs", len(content), elapsed)

        return {
            "success": True,
            "content": content,
            "outline": outline,
            "file_path": file_path,
            "error": None,
        }
