"""Agent 元数据常量和默认配置。

AGENT_META          — 每个 agent 的名称、图标、描述
AGENT_DEFAULT_ORDER — agent 默认排序
AGENT_DEFAULT_ENABLED — 默认启用的 agent 列表
"""

from __future__ import annotations

# 各 Agent 的展示元数据：名称、图标、描述
AGENT_META: dict[str, dict[str, str]] = {
    "content": {"name": "课程内容", "icon": "Document", "description": "专业课程讲解文档"},
    "mindmap": {"name": "思维导图", "icon": "Mindmap", "description": "知识结构思维导图"},
    "quiz": {"name": "练习题", "icon": "Quiz", "description": "练习习题"},
    "code": {"name": "代码示例", "icon": "Code", "description": "代码实操案例"},
    "reading": {"name": "拓展阅读", "icon": "Reading", "description": "拓展阅读推荐"},
    "ppt": {"name": "PPT文稿", "icon": "DataBoard", "description": "PPT文稿生成"},
    "video": {"name": "讲解视频", "icon": "Video", "description": "带配音和字幕的 MP4 讲解视频"},
    "cartoon": {"name": "动画讲解", "icon": "FilmStrip", "description": "知识点动画、配音与字幕同步的 MP4 教学视频"},
}

# 前端展示与校验的默认 Agent 顺序
AGENT_DEFAULT_ORDER: list[str] = ["content", "mindmap", "quiz", "code", "reading", "ppt", "cartoon", "video"]
# 默认启用（开放）的 Agent 列表
AGENT_DEFAULT_ENABLED: list[str] = ["content", "mindmap", "quiz", "code", "reading", "ppt", "cartoon", "video"]
# 至少需选中的 Agent 数量下限
MIN_SELECTED_AGENTS = 3
