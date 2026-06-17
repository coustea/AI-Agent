"""资源模块工具函数。"""

import json
from typing import Any


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
