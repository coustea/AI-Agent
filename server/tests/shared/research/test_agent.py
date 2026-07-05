"""ResearchAgent 单元测试。"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.shared.research.agent import ResearchAgent
from app.shared.research.schemas import ResearchTask, ResearchReport


@pytest.mark.asyncio
async def test_research_agent_with_valid_query():
    """测试 ResearchAgent 处理有效查询。"""

    # 创建模拟的搜索结果
    mock_results = [
        "Python 异步编程使用 async/await 语法...",
        "DuckDuckGo 搜索结果:\n1. Python Async Tutorial\n链接: https://example.com",
    ]

    # 创建模拟模型
    mock_model = AsyncMock()
    mock_model.ainvoke = AsyncMock(return_value=MagicMock(content="总结: Python 异步编程核心要点..."))

    # 创建模拟工具
    mock_tools = []

    # 创建 ResearchAgent
    agent = ResearchAgent(
        model=mock_model,
        tools=mock_tools,
    )

    # 创建任务
    task = ResearchTask(query="Python 异步编程")

    # 注意: 这个测试需要真实工具，这里只是验证结构
    # 实际测试会在集成测试中进行

    assert agent.system_prompt is not None
    assert len(agent.tools) > 0  # 默认工具列表


@pytest.mark.asyncio
async def test_research_task_validation():
    """测试 ResearchTask 参数验证。"""

    # 正常任务
    task = ResearchTask(query="Python 异步编程")
    assert task.query == "Python 异步编程"
    assert task.depth == "standard"
    assert task.sources == {"web"}

    # 空查询应该失败
    with pytest.raises(ValueError):
        ResearchTask(query="")

    # 查询会被 trim
    task_with_spaces = ResearchTask(query="  Python 编程  ")
    assert task_with_spaces.query == "Python 编程"


def test_research_report_structure():
    """测试 ResearchReport 结构。"""

    report = ResearchReport(
        query="Python 异步编程",
        context="总结内容...",
        evidence=[
            {
                "source_type": "web",
                "summary": "核心要点",
                "confidence": 0.8,
            }
        ],
        errors=[],
    )

    assert report.query == "Python 异步编程"
    assert report.has_usable_evidence is True
    assert len(report.evidence) == 1


def test_research_report_no_evidence():
    """测试 ResearchReport 没有证据的情况。"""

    report = ResearchReport(
        query="查询",
        context="",
        evidence=[],
        errors=[{"stage": "search", "code": "failed", "message": "搜索失败"}],
    )

    assert report.has_usable_evidence is False
    assert len(report.errors) == 1


def test_is_valid_result():
    """测试搜索结果有效性检查。"""

    agent = ResearchAgent()

    # 有效结果
    assert agent._is_valid_result("这是一段有效的搜索结果内容，长度足够") is True

    # 无效结果 - 太短
    assert agent._is_valid_result("短文本") is False

    # 无效结果 - 失败标记
    assert agent._is_valid_result("搜索不可用") is False
    assert agent._is_valid_result("未找到结果") is False

    # 无效结果 - 异常
    assert agent._is_valid_result(Exception("错误")) is False