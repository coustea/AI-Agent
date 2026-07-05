"""Path 模块搜索工具测试 — 基于 ToolExcute 架构。

测试覆盖：
  - PathPlannerAgent 搜索工具配置
  - ToolExcute.invoke 和 execute_all 在 Path 中的使用
"""

from __future__ import annotations

import pytest
from types import SimpleNamespace

from app.infra.tool_excute import Tool, ToolExcute
from app.path.schemas import CreateLearningPathRequest


# ── 搜索结果可用性测试 ──


def test_search_result_guard_filters_unavailable_or_failed_results() -> None:
    from app.path.workflows import is_usable_search_result

    assert is_usable_search_result("Tavily 搜索不可用: 未配置 TAVILY_KEY") is False
    assert is_usable_search_result("DuckDuckGo 搜索失败: timeout") is False
    assert is_usable_search_result("未找到相关搜索结果") is False
    assert is_usable_search_result("1. Python 官方教程\n链接: https://docs.python.org/") is True


# ── PathPlannerAgent 搜索工具测试 ──


class TestPathPlannerSearchTools:
    def test_search_tools_are_configured_correctly(self):
        """验证 PathPlannerAgent 的搜索工具配置正确。"""
        from app.path.workflows import PathPlannerAgent
        from app.chat.tools.search import SearchQueryArgs

        # 直接实例化 agent（需要 llm 参数）
        class FakeLlm:
            def create_tool_excute(self, tools):
                return ToolExcute(model=None, tools=tools)

        agent = PathPlannerAgent.__new__(PathPlannerAgent)
        agent.llm = FakeLlm()
        agent.__init__()

        tool_names = [t.name for t in agent.search_tools]
        assert "duckduckgo_search" in tool_names
        assert "duckduckgo_instant_answer" in tool_names
        assert "tavily_search" in tool_names
        assert "spark_search" in tool_names

        # 验证所有工具使用 SearchQueryArgs
        for tool in agent.search_tools:
            assert tool.args_model == SearchQueryArgs

    @pytest.mark.asyncio
    async def test_tool_excute_invoke_returns_tool_calls(self):
        """验证 ToolExcute.invoke 正确解析模型响应中的 tool_calls。"""
        from app.chat.tools.search import SearchQueryArgs, duckduckgo_search

        class FakeModel:
            async def ainvoke(self, messages, **kwargs):
                return SimpleNamespace(
                    tool_calls=[
                        {"id": "call-1", "name": "duckduckgo_search", "args": {"query": "Python 学习路径"}},
                    ]
                )

        tool_excute = ToolExcute(
            model=FakeModel(),
            tools=[
                Tool("duckduckgo_search", "Search.", SearchQueryArgs, duckduckgo_search),
            ],
        )

        response, tool_calls = await tool_excute.invoke([])
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "duckduckgo_search"
        assert tool_calls[0]["args"]["query"] == "Python 学习路径"

    @pytest.mark.asyncio
    async def test_tool_excute_execute_all_runs_concurrently(self):
        """验证 execute_all 并发执行多个工具调用。"""
        import asyncio
        from pydantic import BaseModel, Field

        execution_order = []

        class QueryArgs(BaseModel):
            query: str = Field(description="Search query.")

        async def slow_search(query: str) -> str:
            execution_order.append("slow-start")
            await asyncio.sleep(0.02)
            execution_order.append("slow-end")
            return f"slow: {query}"

        async def fast_search(query: str) -> str:
            execution_order.append("fast-start")
            execution_order.append("fast-end")
            return f"fast: {query}"

        tool_excute = ToolExcute(
            model=None,
            tools=[
                Tool("slow", "Slow search.", QueryArgs, slow_search),
                Tool("fast", "Fast search.", QueryArgs, fast_search),
            ],
        )

        calls = [
            {"name": "slow", "args": {"query": "a"}},
            {"name": "fast", "args": {"query": "b"}},
        ]

        results = await tool_excute.execute_all(calls)

        # 验证并发：slow-start 应在 slow-end 之前出现 fast-start
        assert execution_order.index("slow-start") < execution_order.index("fast-start")
        assert execution_order.index("fast-end") < execution_order.index("slow-end")
        assert len(results) == 2


# ── 兜底路径生成测试 ──


def test_repair_generated_plan_recovers_empty_final_output_from_macro_stages() -> None:
    from app.path.schemas import AgentLearningPathPlan, AgentStage, validate_path_plan
    from app.path.workflows import repair_generated_plan_from_macro_stages

    plan = AgentLearningPathPlan.model_construct(
        title="Python 学习路径",
        stages=[],
        nodes=[],
    )
    stages = [
        AgentStage(stage_id="stage-1", title="基础入门"),
        AgentStage(stage_id="stage-2", title="实践应用"),
    ]

    repaired = repair_generated_plan_from_macro_stages(
        plan=plan,
        macro_stages=stages,
        request=CreateLearningPathRequest(goal="系统学习 Python 编程", topic="Python"),
    )
    validate_path_plan(repaired)

    assert [stage.stage_id for stage in repaired.stages] == ["stage-1", "stage-2"]
    assert [node.stage_id for node in repaired.nodes] == ["stage-1", "stage-2"]
    assert repaired.nodes[0].prerequisites == []
    assert repaired.nodes[1].prerequisites == [repaired.nodes[0].node_id]