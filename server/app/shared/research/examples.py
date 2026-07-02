"""ResearchAgent 使用示例。

展示如何在 chat、resource、path 等模块中调用 ResearchAgent。
"""

# ============================================================================
# 示例 1: 基本使用
# ============================================================================

from app.shared.research import ResearchAgent, ResearchTask

async def example_basic_usage():
    """基本使用示例。"""

    # 1. 创建 ResearchAgent
    agent = ResearchAgent()

    # 2. 创建搜索任务
    task = ResearchTask(
        query="Python 异步编程最佳实践",
        objective="收集教程和最佳实践文档",
    )

    # 3. 执行搜索，获取报告
    report = await agent.run(task)

    # 4. 使用结果
    if report.has_usable_evidence:
        print(f"搜索成功！\n{report.context}")
    else:
        print(f"搜索失败: {report.errors}")


# ============================================================================
# 示例 2: 在 chat 模块中使用
# ============================================================================

async def example_chat_usage():
    """在 chat 模块的 search_node 中使用。"""

    from app.shared.research import ResearchAgent, ResearchTask

    # 创建 agent（可以注入事件回调）
    async def handle_research_event(event):
        """处理搜索事件，用于 SSE 推送。"""
        status = event["status"]
        tool_name = event["tool_name"]
        # 发送 SSE 事件给前端
        print(f"工具 {tool_name} 状态: {status}")

    agent = ResearchAgent(event_handler=handle_research_event)

    # 执行搜索
    task = ResearchTask(
        query="TCP 三次握手",
        objective="为教学回答收集课程知识和网页证据",
    )
    report = await agent.run(task)

    # chat 模块后续处理：
    # - 将 report.evidence 存入 ChatMessage
    # - 将 report.context 用于生成回答
    # - chat 自己负责持久化，ResearchAgent 不存储

    return report


# ============================================================================
# 示例 3: 在 resource 模块中使用
# ============================================================================

async def example_resource_usage():
    """在 resource 模块的 BaseResourceAgent 中使用。"""

    from app.shared.research import ResearchAgent, ResearchTask

    # 创建 agent
    agent = ResearchAgent()

    # 执行搜索（用于资源生成）
    task = ResearchTask(
        query="Python 生成器教程",
        objective="为代码资源生成收集参考资料",
    )
    report = await agent.run(task)

    # resource 模块后续处理：
    # - 将 report.context 用于资源生成（如代码、PPT、思维导图）
    # - resource 不持久化搜索结果，只持久化生成的资源

    return report.context  # 返回搜索内容，供资源生成使用


# ============================================================================
# 示例 4: 在 path 模块中使用
# ============================================================================

async def example_path_usage():
    """在 path 模块的 PathPlannerAgent 中使用。"""

    from app.shared.research import ResearchAgent, ResearchTask

    # 创建 agent
    agent = ResearchAgent()

    # 执行搜索（用于路径规划）
    task = ResearchTask(
        query="系统学习 Python",
        objective="为个性化学习路径收集课程结构参考",
    )
    report = await agent.run(task)

    # path 模块后续处理：
    # - 将 report.context 用于路径规划
    # - path 不持久化搜索结果，只持久化规划的路径

    return report.context  # 返回搜索内容，供路径规划使用


# ============================================================================
# 示例 5: 自定义工具和模型
# ============================================================================

async def example_custom_usage():
    """自定义工具和模型。"""

    from app.shared.research import ResearchAgent, ResearchTask
    from app.infra.tool_excute import Tool
    from pydantic import BaseModel, Field

    # 定义自定义工具
    class CustomArgs(BaseModel):
        query: str = Field(description="Search query")

    async def custom_search(query: str) -> str:
        """自定义搜索实现。"""
        return "自定义搜索结果..."

    custom_tools = [
        Tool("custom_search", "自定义搜索", CustomArgs, custom_search),
    ]

    # 使用自定义工具和模型
    from app.infra.llm import get_llm
    llm = get_llm()

    agent = ResearchAgent(
        model=llm.model,
        tools=custom_tools,
        system_prompt="请简洁总结搜索结果，不超过 200 字。",
    )

    task = ResearchTask(query="自定义查询")
    report = await agent.run(task)

    return report


# ============================================================================
# 总结: ResearchAgent 的使用模式
# ============================================================================

"""
ResearchAgent 使用要点：

1. 创建方式：
   - 默认创建: ResearchAgent()
   - 自定义: ResearchAgent(model=..., tools=..., event_handler=...)

2. 调用方式：
   - 创建任务: ResearchTask(query="...")
   - 执行搜索: await agent.run(task)
   - 获取报告: ResearchReport(context, evidence, errors)

3. 边界清晰：
   - ResearchAgent: 只搜索和总结，不存储
   - 调用方: 负责存储和使用结果

4. 适用场景：
   - chat: 搜索证据用于教学回答
   - resource: 搜索内容用于资源生成
   - path: 搜索参考用于路径规划

5. 工具集：
   - 免费工具: DDG, SearXNG, Wikipedia, ArXiv, GitHub, StackOverflow
   - 已配置: Tavily, Spark
   - 抓取: curl, webfetch

6. 特点：
   - 多引擎并发，竞速返回
   - 大模型总结，提高质量
   - 无状态，每次调用独立
"""