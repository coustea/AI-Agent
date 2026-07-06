"""ResearchAgent 单元测试。"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.shared.research.agent import ResearchAgent
from app.shared.research.schemas import ResearchTask, ResearchReport, ResearchSourceItem


@pytest.mark.asyncio
async def test_research_agent_with_valid_query():
    """测试 ResearchAgent 可以正常创建。"""

    agent = ResearchAgent(tools=[])

    assert agent.tools is not None
    assert agent.event_handler is None


@pytest.mark.asyncio
async def test_research_task_validation():
    """测试 ResearchTask 参数验证。"""

    task = ResearchTask(query="Python 异步编程")
    assert task.query == "Python 异步编程"
    assert task.depth == "standard"
    assert task.sources == {"web"}

    with pytest.raises(ValueError):
        ResearchTask(query="")

    task_with_spaces = ResearchTask(query="  Python 编程  ")
    assert task_with_spaces.query == "Python 编程"


def test_research_report_structure():
    """测试 ResearchReport 结构。"""

    report = ResearchReport(
        query="Python 异步编程",
        sources=[
            ResearchSourceItem(
                source="duckduckgo",
                title="Python Async Tutorial",
                url="https://example.com",
                summary="核心要点",
            ),
        ],
        errors=[],
    )

    assert report.query == "Python 异步编程"
    assert report.has_results is True
    assert len(report.sources) == 1


def test_research_report_no_sources():
    """测试 ResearchReport 没有搜索结果的情况。"""

    from app.shared.research.schemas import ResearchError

    report = ResearchReport(
        query="查询",
        sources=[],
        errors=[ResearchError(stage="search", code="failed", message="搜索失败")],
    )

    assert report.has_results is False
    assert len(report.errors) == 1


def test_is_valid_result():
    """测试搜索结果有效性检查。"""

    agent = ResearchAgent()

    assert agent._is_valid_result(("tool", "This is a valid search result that is long enough to pass the minimum length threshold of fifty characters and should return True")) is True
    assert agent._is_valid_result(("tool", "短文本")) is False
    assert agent._is_valid_result(("tool", "搜索不可用")) is False
    assert agent._is_valid_result(("tool", "未找到结果")) is False
    assert agent._is_valid_result(Exception("错误")) is False
