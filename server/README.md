# AI Learning Platform - Server

基于多智能体架构的个性化学习资源生成系统后端。

本项目利用 **LangGraph** 实现了复杂的扁平化 ReAct 多智能体工作流，配合自定义的 **ToolsManager**、**SkillsManager** 和 **MCPManager**，实现了智能体的按需授权、安全执行与专业技能注入。

## 技术栈

- **Python 3.13** + **uv** 包管理
- **FastAPI** - 高性能 Web 框架
- **SQLModel** - ORM（SQLAlchemy + Pydantic）
- **MySQL & Redis** - 关系型数据存储与 Token/缓存管理
- **LangChain / LangGraph** - 大语言模型编排与多智能体状态机
- **Model Context Protocol (MCP)** - 集成外部高级工具（如 markmap）

## 项目结构

```text
server/
├── app/
│   ├── main.py                     # FastAPI 入口，全局异常处理
│   ├── core/                       # 共享基础设施 (数据库、安全、日志等)
│   ├── models/                     # SQLModel 数据模型定义
│   ├── modules/                    # 核心业务与多智能体模块
│   │   ├── user/                   # 用户认证模块
│   │   ├── profile_builder/        # 用户画像构建
│   │   ├── resource_generator/     # 多智能体资源生成模块（核心）
│   │   │   ├── coordinator_agent.py   # 调度中心 Agent（并发调度子任务并推送 SSE）
│   │   │   ├── content_writer_agent.py # 生成长篇讲解文档
│   │   │   ├── code_agent.py           # 生成代码案例并在沙盒校验
│   │   │   ├── mindmap_agent.py        # 生成思维导图并调用 MCP 转换为 HTML
│   │   │   ├── quiz_agent.py           # 生成分层练习题
│   │   │   ├── media_agent.py          # 生成多模态分镜头脚本
│   │   │   ├── reading_agent.py        # 检索与推荐拓展阅读
│   │   │   ├── tools/                  # 智能体专用的基础工具 (如文件操作、安全 Shell)
│   │   │   └── skills/                 # 智能体专业技能 Prompt 库
│   └── utils/                      # 全局工具管理器
│       ├── tools_manager.py        # 工具分配与权限管理器 (按需加载)
│       ├── skills_manager.py       # 技能管理器 (加载 SKILL.md 注入 System Prompt)
│       └── mcp_manager.py          # MCP 服务管理器
├── workplace/                      # 智能体生成的文件输出目录 (代码、文档、导图等)
├── mcp/                            # MCP 服务的配置文件与本地服务库
├── logs/                           # 运行日志
├── .env                            # 环境变量
└── pyproject.toml
```

## 核心特性：多智能体架构

本项目在 `app/modules/resource_generator/` 下实现了一个强大的多智能体生成系统：

1.  **扁平化 ReAct 状态机 (LangGraph)**：
    彻底摒弃了黑盒化的“图套图”模式。所有 Agent（如 CodeAgent, MindmapAgent 等）均使用官方原生的 `ToolNode` 与自定义条件路由，在单一状态图中完成了“思考 -> 工具调用 -> 反思与校验 -> 输出”的闭环流转，透明且可控。
2.  **最小权限工具分配 (ToolsManager)**：
    工具不再全局广播。各 Agent 必须在初始化时声明 `REQUIRED_TOOLS` 和 `REQUIRED_MCP`。例如，只有 `CodeAgent` 能获得 `safe_shell` 工具，只有 `MindmapAgent` 能调用 `markmap` 工具。极大降低了 LLM 产生幻觉时的破坏力。
3.  **专家技能前置注入 (SkillsManager)**：
    避免了将数百字的 Prompt 伪装成 Tool 并在 Observation 中返回从而污染上下文的错误做法。Agent 启动时，由管理器读取对应的 `SKILL.md`，将其作为高权重的专家指令静态拼接至 System Prompt，确保 LLM 推理不被打断。
4.  **统一的数据出口**：
    生成的文档、代码、导图、题目等数据，在通过自动校验后，均会由 `file_saver` 工具安全落盘至 `server/workplace/` 下对应的分类目录中，并打上时间戳。

## 快速开始

### 1. 环境准备与依赖安装

请确保已安装 Python 3.13 和包管理器 `uv`。

```bash
# 切换到 server 目录并同步依赖
cd server
uv sync
```

### 2. 环境变量配置

请在 `server/` 目录下创建 `.env` 文件，可参考如下配置：

```env
APP_DEBUG=true

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=agent
DB_ECHO=false

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 大模型 API 配置 (用于多智能体)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### 3. 启动服务

```bash
# 启动开发服务
uv run fastapi dev app/main.py

# 或直接运行（默认端口 9999）
uv run python app/main.py
```

启动后，访问 [http://localhost:9999/docs](http://localhost:9999/docs) 可查看 Swagger API 接口文档。

## 日志管理

系统使用标准化的日志记录，日志输出到 `server/logs/` 目录（生产环境下不在控制台打印）：
- `app.log`：全量日志（INFO+），按天轮转，保留 30 天。
- `error.log`：错误日志（ERROR+），按 10MB 轮转，保留 10 份。
