"""验证 Resource 模块各 SubAgent 提示词契约规范 (tests/resource/test_prompt_contracts.py)。"""

from __future__ import annotations

import inspect
from app.resource.schemas import ResourceGenerationRequest
from app.resource.tools import build_resource_tools


def test_resource_subagent_prompts_contract() -> None:
    """验证讲义与思维导图 SubAgent 工具包含教学目标与深入浅出的讲授原则。"""
    req = ResourceGenerationRequest(topic="TCP 协议", target_resources=["content", "mindmap"])
    tools = build_resource_tools(request=req)
    tool_map = {t.name: t for t in tools}

    assert "generate_lecture_content" in tool_map
    lecture_source = inspect.getsource(tool_map["generate_lecture_content"].handler)
    assert "资深课程主讲导师" in lecture_source
    assert "教学目标" in lecture_source

    assert "generate_mindmap" in tool_map
    mindmap_source = inspect.getsource(tool_map["generate_mindmap"].handler)
    assert "知识图谱架构师" in mindmap_source
    assert "Mermaid" in mindmap_source
