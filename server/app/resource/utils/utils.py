"""
资源生成模块工具函数。

保留画像加载、文件保存、Markdown 提取等核心工具。
AgentContextBuilder 已移除 — 各 Agent 自带 _build_input()。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger
from app.utils.paths import RESOURCE_DIR

logger = get_logger(__name__)


# =============================================================================
# 画像加载
# =============================================================================

_memory_service = None


def _get_memory_service():
    """获取 MemoryService 单例。"""
    global _memory_service
    if _memory_service is None:
        from app.memory import MemoryService
        _memory_service = MemoryService(module="mentor")
    return _memory_service


async def load_user_profile(user_id: int) -> dict:
    """加载用户基础信息和画像。

    Returns:
        包含 user_data 和 profile_data 的字典，用于构建 Agent 上下文。
    """
    from sqlmodel.ext.asyncio.session import AsyncSession
    from app.infra.database import engine
    from app.infra.models import User

    # 加载用户基础信息
    user_data = {"user_id": user_id}
    async with AsyncSession(engine) as session:
        user = await session.get(User, user_id)
        if user:
            user_data = {
                "user_id": user.id,
                "username": user.username,
            }
            logger.info("[Profile] 已读取用户基础信息: user_id=%s", user_id)

    # 加载画像
    profile_data = {}
    profile = await _get_memory_service().get_profile(user_id=user_id)
    if profile:
        profile_data = profile.model_dump(exclude_none=True)
        updated_at = profile_data.get("updated_at")
        if updated_at is not None:
            profile_data["updated_at"] = updated_at.isoformat()

        # 从 profile_json.student_profile 提取 major/grade/school
        profile_json = profile_data.get("profile_json") or {}
        student_profile = profile_json.get("student_profile") or {}
        if student_profile:
            user_data["major"] = student_profile.get("major")
            user_data["grade"] = student_profile.get("grade")
            user_data["school"] = student_profile.get("school")

        logger.info("[Profile] 已读取用户画像: user_id=%s fields=%s", user_id, list(profile_data.keys()))

    return {"user_data": user_data, "profile_data": profile_data}


# =============================================================================
# 画像格式化 (用于 prompt)
# =============================================================================


def format_learner_profile_for_prompt(learner_profile: dict[str, Any] | None) -> str:
    """将学习者画像字典渲染为 prompt 可读的文本块。"""
    if not learner_profile:
        return ""

    profile_json = learner_profile.get("profile_json")
    profile_data = learner_profile.get("profile_data")
    if not isinstance(profile_json, dict) and isinstance(profile_data, dict):
        profile_json = profile_data.get("profile_json")
    if isinstance(profile_json, dict):
        return json.dumps(profile_json, ensure_ascii=False, indent=2)

    user_data = learner_profile.get("user_data")
    lines: list[str] = []
    if isinstance(user_data, dict):
        for key, label in (
            ("major", "专业"),
            ("grade", "年级"),
            ("school", "学校"),
            ("username", "用户名"),
        ):
            value = user_data.get(key)
            if value:
                lines.append(f"- {label}: {value}")
    for key, label in (
        ("major", "专业"),
        ("grade", "年级"),
        ("school", "学校"),
        ("current_focus", "当前关注"),
        ("learning_style", "学习偏好"),
    ):
        value = learner_profile.get(key)
        if value:
            lines.append(f"- {label}: {value}")
    return "\n".join(lines).strip()


# =============================================================================
# 文件保存
# =============================================================================


def save_resource_file(
    topic: str,
    content: str,
    user_id: int,
    resource_id: int,
    ext: str = "md",
    prefix: str | None = None,
    agent_type: str | None = None,
) -> str:
    """保存资源文件到统一路径: workplace/resource/{user_id}/{resource_id}/{agent_type}/{topic}.{ext}"""
    safe_topic = re.sub(r'[\\/*?:"<>|]', "", topic).strip()[:50]
    if not safe_topic:
        safe_topic = "untitled"

    if agent_type:
        target_dir = RESOURCE_DIR / str(user_id) / str(resource_id) / agent_type
    else:
        target_dir = RESOURCE_DIR / str(user_id) / str(resource_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_prefix = re.sub(r'[\\/*?:"<>|]', "", prefix or "").strip()
    filename = f"{safe_prefix}_{safe_topic}.{ext}" if safe_prefix else f"{safe_topic}.{ext}"
    filepath = target_dir / filename

    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


# =============================================================================
# Markdown 提取与规范化
# =============================================================================

_MARKDOWN_FENCE_RE = re.compile(r"```(?:markdown|md)?\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)


def extract_markdown_from_llm_output(content: str) -> str:
    """从 LLM 输出中提取 Markdown 内容（剥离围栏并规范化缩进）。"""
    raw = (content or "").strip()
    if not raw:
        return ""

    match = _MARKDOWN_FENCE_RE.search(raw)
    if match:
        raw = match.group(1).strip()

    return _normalize_markdown_indent(raw)


def _normalize_markdown_indent(markdown_text: str) -> str:
    """规范化 Markdown 缩进，确保一级分支顶格。"""
    lines = markdown_text.splitlines()
    bullet_indents = [
        len(line) - len(line.lstrip(" "))
        for line in lines
        if line.lstrip(" ").startswith("- ")
    ]
    if not bullet_indents:
        return markdown_text.strip()

    min_indent = min(bullet_indents)
    if min_indent == 0:
        return markdown_text.strip()

    normalized = []
    for line in lines:
        if line.startswith(" " * min_indent):
            normalized.append(line[min_indent:])
        else:
            normalized.append(line)
    return "\n".join(normalized).strip()


# =============================================================================
# LLM 摘要生成
# =============================================================================


async def generate_summary_with_llm(markdown: str, learning_need: str = "") -> str:
    """使用 LLM 为学习资源生成文本摘要。"""
    from langchain_core.messages import HumanMessage
    from app.infra.llm import get_llm

    if not markdown or not markdown.strip():
        return ""

    prompt = f"""请为以下学习内容生成一段简洁的摘要（100-150字），概括核心知识点：

学习主题：{learning_need[:100] if learning_need else "未指定"}

内容：
{markdown[:3000]}

要求：
1. 摘要要简洁，突出核心概念
2. 不要使用 Markdown 格式，直接输出纯文本
3. 不要添加额外解释"""

    try:
        llm = get_llm()
        response = await llm.ainvoke(
            [HumanMessage(content=prompt)],
            temperature=0.3,
        )
        summary = response.content if hasattr(response, "content") else str(response)
        return summary.strip()
    except Exception:
        return ""
