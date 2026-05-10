"""
资源生成模块工具函数集合。

整合了 prompt 加载、画像格式化、依赖展开、Agent 注册表等通用工具。

注意：Workspace 文件产物系统相关函数已移至 worker_agents/utils.py。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger
from app.shared.paths import RESOURCE_DIR

logger = get_logger(__name__)

# =============================================================================
# Agent 配置常量
# =============================================================================

CORE_AGENTS = ["content"]
STRUCTURE_AGENTS = ["diagram", "mindmap"]
PRACTICE_AGENTS = ["code", "quiz"]
EXTENSION_AGENTS = ["reading"]
ALL_AGENTS = CORE_AGENTS + STRUCTURE_AGENTS + PRACTICE_AGENTS + EXTENSION_AGENTS


# =============================================================================
# Prompt 加载与上下文构建
# =============================================================================

def load_prompt(agent_dir: Path) -> str:
    """加载 Agent 的 prompt.md 文件。"""
    prompt_path = agent_dir / "prompt.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"prompt 文件不存在: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def format_profile_fields(profile: dict[str, Any], fields: list[tuple[str, str]]) -> str:
    """格式化画像字段为 Markdown 列表。"""
    if not profile:
        return ""
    parts: list[str] = []
    for key, label in fields:
        value = profile.get(key)
        if value:
            parts.append(f"- {label}: {value}")
    return "\n".join(parts)


# =============================================================================
# 文件保存与工具加载
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
    """保存资源文件到统一路径: workplace/resource/{user_id}/{resource_id}/{agent_type}/{topic}.{ext}

    Args:
        topic: 主题名称（用于生成文件名）
        content: 文件内容
        user_id: 用户 ID
        resource_id: 资源 ID
        ext: 文件扩展名
        prefix: 可选文件名前缀，用于隔离不同 Agent 的产物
        agent_type: Agent 类型（如 content, mindmap, quiz 等），如果提供则保存到子目录

    Returns:
        文件路径
    """
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
# 画像加载
# =============================================================================

_memory_layer = None


def _get_memory_layer():
    """获取 MemoryLayer 单例。"""
    global _memory_layer
    if _memory_layer is None:
        from app.memory import MemoryLayer
        _memory_layer = MemoryLayer(module="mentor")
    return _memory_layer


async def load_user_profile(user_id: int) -> dict:
    """加载用户基础信息和画像。

    Returns:
        包含 user_data 和 profile_data 的字典，用于构建 LearnerProfileSnapshot。
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
                "major": user.major,
                "grade": user.grade,
                "school": user.school,
            }
            logger.info("[Profile] 已读取用户基础信息: user_id=%s", user_id)

    # 加载画像
    profile_data = {}
    profile = await _get_memory_layer().get_profile(user_id=user_id)
    if profile:
        profile_data = profile.model_dump(exclude_none=True)
        updated_at = profile_data.get("updated_at")
        if updated_at is not None:
            profile_data["updated_at"] = updated_at.isoformat()
        logger.info("[Profile] 已读取用户画像: user_id=%s fields=%s", user_id, list(profile_data.keys()))

    return {"user_data": user_data, "profile_data": profile_data}


async def load_profile_snapshot(user_id: int):
    """加载用户画像快照。"""
    from app.resource.schemas import LearnerProfileSnapshot

    data = await load_user_profile(user_id)
    return LearnerProfileSnapshot.from_sources(**data)


def _parse_profile(profile) -> dict[str, str]:
    """从 JSON 画像中提取资源生成需要的关键信息。"""
    result: dict[str, str] = {}
    if not profile:
        return result

    if hasattr(profile, "profile_json") and profile.profile_json and profile.profile_json.get("dimensions"):
        dimensions = profile.profile_json.get("dimensions", {})
        student_profile = profile.profile_json.get("student_profile") or {}
        result["技术能力判断"] = dimensions.get("knowledge_foundation", {}).get("summary") or ""
        result["当前学习/项目背景"] = dimensions.get("learning_goal", {}).get("summary") or ""
        result["学习偏好"] = dimensions.get("interaction_preference", {}).get("summary") or ""
        result["当前薄弱点"] = dimensions.get("weakness_points", {}).get("summary") or ""
        result["兴趣方向"] = ""
        interests = student_profile.get("current_focus", [])
        if isinstance(interests, list):
            result["兴趣方向"] = ", ".join(interests)
        strategies = profile.profile_json.get("recommended_strategy", [])
        if isinstance(strategies, list):
            result["推荐辅导策略"] = "\n".join(strategies)
    return result


def format_profile_json_for_prompt(profile_json: dict[str, Any] | None) -> str:
    """Format JSON-first learner profile for prompts without Markdown conversion."""
    if not profile_json:
        return ""
    payload = dict(profile_json)
    return json.dumps(payload, ensure_ascii=False, indent=2)
