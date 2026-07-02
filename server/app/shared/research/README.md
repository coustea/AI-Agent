# ResearchAgent - 共享搜索子 Agent

## 概述

ResearchAgent 是一个独立的搜索子 Agent，提供统一的搜索能力给整个系统的所有 agent 使用。

**核心特点：**
- 只负责搜索和总结，不存储数据
- 多引擎并发搜索，确保结果全面可靠
- 大模型总结搜索结果，提高质量
- 无状态，每次调用独立

## 文件结构

```
app/shared/research/
├── __init__.py          # 公开接口导出
├── agent.py             # ResearchAgent 实现
├── schemas.py           # 数据模型定义
├── search_tools.py      # 搜索工具实现（免费）
├── tools.py             # 工具注册表
├── examples.py          # 使用示例
└── README.md            # 本文档
```

## 搜索工具清单

### 免费搜索引擎（9个）
1. DuckDuckGo Search - 免费，无需 API Key
2. DuckDuckGo Instant Answer - 即时答案和定义
3. SearXNG - 开源聚合引擎（聚合 Google、Bing、DDG、Wikipedia）
4. Wikipedia - 百科搜索（支持英文和中文）
5. ArXiv - 学术论文搜索
6. GitHub - 代码仓库搜索
7. StackOverflow - 技术问答搜索
8. Tavily - AI 优化搜索（已配置 Key）
9. Spark - 讯飞星火中文语义搜索（已配置 Key）

### 内容抓取工具（2个）
1. curl_fetch - curl 命令抓取网页
2. webfetch - HTTP GET 抓取网页

## 使用方式

### 1. 基本使用

```python
from app.shared.research import ResearchAgent, ResearchTask

# 创建 agent
agent = ResearchAgent()

# 创建任务
task = ResearchTask(query="Python 异步编程")

# 执行搜索
report = await agent.run(task)

# 使用结果
if report.has_usable_evidence:
    print(report.context)
```

### 2. 在 chat 模块中使用

```python
# chat/agent/nodes.py
from app.shared.research import ResearchAgent, ResearchTask

async def search_node(state):
    agent = ResearchAgent()
    task = ResearchTask(query=state["question"])
    report = await agent.run(task)

    # chat 自己存储结果
    state["search_context"] = report.context
    state["evidence"] = report.evidence
```

### 3. 在 resource 模块中使用

```python
# resource/agents/base.py
from app.shared.research import ResearchAgent, ResearchTask

class BaseResourceAgent:
    async def search(self, query: str) -> str:
        agent = ResearchAgent()
        task = ResearchTask(query=query)
        report = await agent.run(task)
        return report.context  # 返回搜索内容
```

### 4. 在 path 模块中使用

```python
# path/workflows.py
from app.shared.research import ResearchAgent, ResearchTask

class PathPlannerAgent:
    async def _research(self, request):
        agent = ResearchAgent()
        task = ResearchTask(query=request.topic)
        report = await agent.run(task)
        return report.context  # 用于路径规划
```

## 数据模型

### ResearchTask（搜索任务）
```python
class ResearchTask(BaseModel):
    query: str                  # 搜索查询（必填）
    objective: str = ""         # 搜索目标（可选）
    depth: ResearchDepth        # 搜索深度（quick/standard/deep）
    sources: set[ResearchSource] # 搜索来源（默认 {"web"}）
```

### ResearchReport（搜索报告）
```python
class ResearchReport(BaseModel):
    query: str                  # 原始查询
    context: str                # 大模型总结的搜索结果
    evidence: list[ResearchEvidence]  # 证据列表
    sources: list[ResearchSourceItem] # 来源列表
    invocations: list[ResearchInvocation] # 工具调用记录
    errors: list[ResearchError] # 错误记录
```

## 设计边界

### ResearchAgent 负责：
- ✅ 搜索执行（调用搜索工具）
- ✅ 结果过滤（质量保证）
- ✅ 大模型总结（提炼信息）
- ✅ 返回报告（结构化输出）

### ResearchAgent 不负责：
- ❌ 数据存储（不写数据库）
- ❌ 缓存管理（不写 Redis）
- ❌ 业务逻辑（不依赖业务模块）
- ❌ 消息历史（不依赖 memory）

### 调用方负责：
- chat: 存储 ChatMessage.evidence
- resource: 使用搜索内容生成资源
- path: 使用搜索内容规划路径

## 测试

```bash
# 运行导入测试
uv run pytest tests/shared/research/test_import.py -v

# 运行单元测试
uv run pytest tests/shared/research/test_agent.py -v
```

## 特性总结

1. **多引擎并发**：9 个搜索引擎并发调用，竞速返回
2. **失败隔离**：单个引擎失败不影响整体
3. **质量保证**：大模型总结搜索结果，提高信息质量
4. **无状态**：每次调用独立，不依赖外部状态
5. **统一接口**：整个系统都可以调用 `ResearchAgent.run(task)`
