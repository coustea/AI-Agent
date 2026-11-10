"""工具调用入参提取与结果摘要结构化日志测试 (tests/shared/test_tool_logging.py)。"""

from __future__ import annotations

import json
from app.shared.tools.registry import summarize_tool_args, summarize_tool_result


def test_summarize_tool_args_load_skill() -> None:
    """验证 load_skill 工具入参的提炼。"""
    res1 = summarize_tool_args("load_skill", {"name": "hyperframes", "reference": "references/format.md"})
    assert "skill='hyperframes'" in res1
    assert "ref='references/format.md'" in res1

    res2 = summarize_tool_args("load_skill", '{"name": "hyperframes-cli"}')
    assert "skill='hyperframes-cli'" in res2


def test_summarize_tool_args_bash() -> None:
    """验证 bash 命令入参的提炼与截断。"""
    res = summarize_tool_args("bash", {"command": "npm run build --prefix ."})
    assert "npm run build" in res


def test_summarize_tool_args_synthesize_speech() -> None:
    """验证语音合成工具入参的提炼。"""
    res = summarize_tool_args("synthesize_speech", {
        "text": "这是一段测试教学动画旁白讲解内容，字数比较长。",
        "output_path": "assets/audio/s01.mp3",
    })
    assert "assets/audio/s01.mp3" in res
    assert "共 23 字" in res


def test_summarize_tool_args_resource_agents() -> None:
    """验证资源主智能体调度子工具的入参提炼。"""
    res_lecture = summarize_tool_args("generate_lecture_content", {
        "topic": "Transformer 架构",
        "learning_goal": "掌握自注意力机制计算过程",
    })
    assert "Transformer 架构" in res_lecture

    res_quiz = summarize_tool_args("generate_quiz", {
        "topic": "Python 异步编程",
        "difficulty": "advanced",
    })
    assert "advanced" in res_quiz


def test_summarize_tool_result_bash() -> None:
    """验证 bash 执行结果摘要提取。"""
    res = summarize_tool_result("bash", {"exit_code": 0, "stdout": "Build success\nFinished in 2s", "stderr": ""})
    assert "exit=0" in res
    assert "Build success" in res


def test_summarize_tool_result_speech() -> None:
    """验证语音合成结果摘要提取。"""
    res = summarize_tool_result("synthesize_speech", {"audio_path": "assets/audio/s01.mp3", "duration_ms": 3500})
    assert "audio='assets/audio/s01.mp3'" in res
    assert "duration=3500ms" in res


def test_summarize_tool_result_skills() -> None:
    """验证技能读取结果摘要提取。"""
    res = summarize_tool_result("load_skill", {"status": "ok", "text": "<skill name=\"hyperframes\">..."})
    assert "status=ok" in res
    assert "字符" in res
