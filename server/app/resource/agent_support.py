from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def load_prompt(agent_dir: Path) -> str:
    prompt_path = agent_dir / "prompt.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"prompt 文件不存在: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def format_profile_fields(profile: dict[str, Any], fields: list[tuple[str, str]]) -> str:
    if not profile:
        return ""
    parts: list[str] = []
    for key, label in fields:
        value = profile.get(key)
        if value:
            parts.append(f"- {label}: {value}")
    return "\n".join(parts)


def append_context(
    system_prompt: str,
    *,
    state: dict[str, Any],
    format_user_profile: Callable[[dict[str, Any]], str] | None = None,
    extract_memory: Callable[[dict[str, Any]], str] | None = None,
) -> str:
    profile = state.get("user_profile", {}) or {}
    if format_user_profile:
        profile_str = format_user_profile(profile)
        if profile_str:
            system_prompt += f"\n\n## [学习者画像]\n{profile_str}"

    shared_memory = state.get("shared_memory", {}) or {}
    if extract_memory:
        memory_ctx = extract_memory(shared_memory)
        if memory_ctx:
            system_prompt += f"\n\n## [协作上下文]\n{memory_ctx}"

    kb_context = state.get("knowledge_base_context", "")
    if kb_context:
        system_prompt += f"\n\n## [知识库参考]\n{kb_context}"
    return system_prompt


def save_to_workplace(sub_dir: str, topic: str, content: str, ext: str = "md") -> str:
    from app.tools.registry import get as get_tool

    return get_tool("save_to_workplace").invoke(
        {"sub_dir": sub_dir, "topic": topic, "content": content, "ext": ext}
    )


def load_registered_tools(tool_names: list[str]) -> list[Any]:
    from app.tools import registry

    registry.ensure_loaded()
    return registry.get_many(tool_names)
