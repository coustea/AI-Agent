"""测试 ResearchAgent 是否可以正常导入和使用。"""

import pytest


def test_research_module_import():
    """测试 research 模块可以正常导入。"""

    from app.shared.research import (
        ResearchAgent,
        ResearchTask,
        ResearchReport,
        ResearchError,
    )

    assert ResearchAgent is not None
    assert ResearchTask is not None
    assert ResearchReport is not None


def test_research_agent_creation():
    """测试 ResearchAgent 可以正常创建。"""

    from app.shared.research import ResearchAgent

    # 创建 agent（使用默认配置）
    agent = ResearchAgent()

    assert agent is not None
    assert agent.tools is not None
    assert len(agent.tools) > 0  # 应该有默认搜索工具


def test_research_task_creation():
    """测试 ResearchTask 可以正常创建。"""

    from app.shared.research import ResearchTask

    task = ResearchTask(query="Python 异步编程")

    assert task.query == "Python 异步编程"
    assert task.depth == "standard"
    assert task.sources == {"web"}


def test_research_report_creation():
    """测试 ResearchReport 可以正常创建。"""

    from app.shared.research import ResearchReport, ResearchSourceItem

    report = ResearchReport(
        query="测试查询",
        sources=[
            ResearchSourceItem(
                source="duckduckgo",
                title="Python 异步编程",
                url="https://example.com",
                summary="摘要",
            ),
        ],
    )

    assert report.query == "测试查询"
    assert report.has_results is True
    assert len(report.sources) == 1
