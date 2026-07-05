# ResearchAgent - 共享搜索子 Agent

## 概述

ResearchAgent 是一个独立的搜索子 Agent，提供统一的搜索能力给整个系统的所有 agent 使用。

**核心特点：**
- 只负责搜索，返回结构化结果
- 多引擎并发搜索，确保结果全面可靠
- 无状态，每次调用独立
- 不涉及 LLM 总结、存储或业务逻辑

## 文件结构

```
app/shared/research/
├── __init__.py          # 公开接口导出
├── agent.py             # ResearchAgent 实现
├── schemas.py           # 数据模型定义
├── search_tools.py      # 搜索工具实现
├── tools.py             # 工具注册表
├── delegate_tool.py     # 委托工具（供上层 Agent 注册）
└── README.md            # 本文档
```

## 搜索工具清单

### 免费搜索引擎（7个）
1. DuckDuckGo Search - 免费，无需 API Key
2. DuckDuckGo Instant Answer - 即时答案和定义
3. SearXNG - 开源聚合引擎（聚合 Google、Bing、DDG、Wikipedia）
4. Wikipedia - 百科搜索（支持英文和中文）
5. ArXiv - 学术论文搜索
6. GitHub - 代码仓库搜索
7. StackOverflow - 技术问答搜索

### 已配置的搜索引擎（2个）
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
if report.has_results:
    for source in report.sources:
        print(source.title, source.url, source.summary)
```

### 2. 作为委托工具使用（推荐）

```python
from app.shared.research import build_research_tool

tool = build_research_tool(enabled=True)
# 将 tool 注册到上层 Agent 的工具列表中
```

### 3. 在 resource 模块中使用

```python
from app.shared.research.agent import ResearchAgent
from app.shared.research.schemas import ResearchTask

agent = ResearchAgent()
report = await agent.run(ResearchTask(query="..."))
# report.sources 包含搜索结果列表
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
    sources: list[ResearchSourceItem] # 来源列表
    errors: list[ResearchError] # 错误记录

    @property
    def has_results(self) -> bool  # 是否有有效搜索结果
```

## 设计边界

### ResearchAgent 负责：
- ✅ 搜索执行（调用搜索工具）
- ✅ 结果过滤（质量保证）
- ✅ 去重（按 URL）
- ✅ 返回报告（结构化输出）

### ResearchAgent 不负责：
- ❌ LLM 总结（不做大模型摘要）
- ❌ 数据存储（不写数据库）
- ❌ 缓存管理（不写 Redis）
- ❌ 业务逻辑（不依赖业务模块）
- ❌ 知识库检索（不依赖 RAG）

### 调用方负责：
- chat: 使用搜索结果作为上下文
- resource: 使用搜索结果生成资源
- path: 使用搜索结果规划路径
