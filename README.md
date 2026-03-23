# ReAct Agent Framework - 完全解耦架构

<div align="center">

**基于 LangGraph 的 ReAct 模式智能体框架 + FastAPI 用户认证系统**

[完全解耦架构](#architecture) • [快速开始](#quick-start) • [API 文档](#api) • [示例](src/agent/main.py)

</div>

---

## 📖 简介

ReAct Agent Framework 是一个现代化、模块化、可扩展的智能体框架，实现了经典的 **ReAct（Reasoning + Acting）模式**。采用**完全解耦架构**设计，Agent 与服务层完全分离，支持独立部署和测试。

```
📚 Retrieve → 🤔 Think → 🛠️ Plan → ⚡ Act → 👀 Reflect → (循环)
```

### 核心特性

| 特性 | 描述 |
|------|------|
| 🔄 **5 节点工作流** | Retrieve → Think → Plan → Act → Reflect 完整闭环 |
| 🏗️ **完全解耦架构** | Agent 与 API 服务层、存储层完全解耦 |
| 🧩 **模块化设计** | 工具、技能、提示词完全解耦 |
| 📝 **SOP 驱动** | 业务知识通过 Markdown 管理，无需修改代码 |
| 🔐 **用户认证系统** | JWT + Redis Token 管理，MySQL 用户存储 |
| 🌐 **RESTful API** | FastAPI 构建的标准 REST 接口 |
| 📊 **流式输出** | 实时查看智能体的思考过程和决策 |

---

## 🏗️ 架构设计

### 完全解耦架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent 层 (完全独立)                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              LangGraph StateGraph                         │  │
│  │  Retrieve → Think → Plan → Act → Reflect → Think ...     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      服务层 (API + 存储)                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │   Redis Session │◄──►│   Agent       │◄──►│   MySQL     │  │
│  │   Service       │    │   Service     │    │   User      │  │
│  └─────────────────┘    └─────────────────┘    └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 解耦设计亮点

- **Agent 独立性**: Agent 完全不依赖任何存储或服务层
- **依赖注入**: 通过接口实现松耦合
- **记忆抽象**: 通过 MemoryInterface 协议管理记忆存储
- **服务层集成**: 通过服务层接口连接 Agent 与存储

### 5 节点工作流

| 节点 | 职责 | 完全解耦 |
|------|------|----------|
| **📚 Retrieve** | 加载业务 SOP（仅从本地文件系统） | ✅ |
| **🤔 Think** | 意图理解与情境分析 | ✅ |
| **🛠️ Plan** | 决策工具调用或生成答案 | ✅ |
| **⚡ Act** | 执行工具（通过 ToolNode） | ✅ |
| **👀 Reflect** | 评估结果并决定继续/结束 | ✅ |

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.10 或更高版本
- **MySQL**: 5.7 或更高版本
- **Redis**: 6.0 或更高版本
- **包管理器**: [uv](https://github.com/astral-sh/uv)（推荐）或 pip

### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
# OpenAI / LLM
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.deepseek.com/v1

# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_NAME=agent
DB_USER=root
DB_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# JWT
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=168

# API
API_HOST=0.0.0.0
API_PORT=9999
```

### 3. 初始化数据库

在 MySQL 中运行初始化脚本：

```bash
mysql -u root -p < src/api/scripts/init_db.sql
```

### 4. 启动服务

```bash
# 启动 API 服务
uvicorn src.api.main:app --reload --port 9999

# 或运行 Agent 演示
python src/agent/main.py
```

访问 `http://localhost:9999/docs` 查看 Swagger API 文档。

---

## 🔐 用户认证 API

### RESTful 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/users` | 注册用户 |
| GET | `/api/users/me` | 获取当前用户信息 |
| PATCH | `/api/users/me/password` | 修改密码 |
| POST | `/api/auth/login` | 登录 |
| DELETE | `/api/auth/logout` | 登出 |

### 统一响应格式

```json
{
    "code": 200,
    "message": "success",
    "data": {
        "access_token": "eyJ...",
        "token_type": "bearer",
        "expires_in": 604800,
        "user": {
            "username": "testuser",
            "created_at": "2024-01-01T00:00:00"
        }
    }
}
```

---

## 🤖 Agent 工具系统

### 内置工具 (7个)

| 工具 | 功能 | 用途 |
|------|------|------|
| **shell_exec** | 安全执行 Shell 命令 | 系统操作、脚本执行 |
| **web_fetch** | 获取网页内容 | 信息检索、文档阅读 |
| **file_append** | 文件追加写入 | 日志记录、数据保存 |
| **file_read** | 文件读取 | 读取配置、数据加载 |
| **file_list** | 目录列表 | 文件管理、内容浏览 |
| **data_analyze** | 数据分析 | CSV/Excel 分析处理 |
| **web_search** | 网络搜索 | 实时信息获取 |

### 内置技能 (12个)

| 技能 | 功能 | 用途 |
|------|------|------|
| **word-document-processor** | Word 文档处理 | 文档创建、编辑 |
| **baidu-search-1.1.3** | 百度搜索 | 中文信息检索 |
| **excel-automation** | Excel 自动化 | 数据处理、报表生成 |
| **weather-1.0.0** | 天气查询 | 实时天气信息 |
| **pdf** | PDF 处理 | 文档转换、内容提取 |
| **self-improving-agent-3.0.5** | 自我改进 | 智能优化 |
| **financial-calculator** | 金融计算 | 投资分析、财务计算 |
| **design-md** | 设计文档生成 | 技术文档、规范生成 |
| **desktop-control-1.0.0** | 桌面控制 | 系统管理 |
| **tavily-search** | 网络搜索 | 专业搜索 |
| **tam-sam-som-calculator** | 市场规模计算 | 商业分析 |
| **ocr-document-processor** | OCR 文档处理 | 图像转文本 |

---

## 📦 核心组件

### Agent 模块 (`src/agent/`)

| 组件 | 描述 |
|------|------|
| `core/agent.py` | 5 节点 LangGraph 工作流（完全解耦） |
| `core/llm.py` | LLM 封装层 |
| `tools/builtin/` | 内置工具实现 |
| `skills/` | 业务知识库（SKILL.md） |
| `prompts/` | 工作流提示词 |

### API 模块 (`src/api/`)

| 组件 | 描述 |
|------|------|
| `db/engine.py` | MySQL + Redis 连接管理 |
| `db/models.py` | SQLAlchemy 数据模型 |
| `router/` | FastAPI 路由（users, auth, agent） |
| `services/` | 业务逻辑层（AgentService, SessionService） |
| `schemas/` | Pydantic 请求/响应模型 |
| `utils/` | 工具函数（JWT, 密码加密） |

---

## 📂 项目结构

```
agent/
├── src/
│   ├── agent/                    # ReAct Agent 模块（完全独立）
│   │   ├── core/
│   │   │   ├── agent.py          # 5 节点工作流（完全解耦）
│   │   │   ├── llm.py            # LLM 封装
│   │   │   └── __init__.py       # 模块初始化
│   │   ├── tools/                # 工具系统
│   │   │   ├── builtin/          # 内置工具
│   │   │   │   ├── shell_execute.py
│   │   │   │   ├── web_fetch.py
│   │   │   │   ├── file_write.py
│   │   │   │   ├── file_read.py
│   │   │   │   ├── file_list.py
│   │   │   │   ├── data_analyzer.py
│   │   │   │   └── web_search.py
│   │   │   └── __init__.py       # 工具初始化
│   │   ├── skills/               # 技能系统
│   │   │   ├── baidu-search-1.1.3/
│   │   │   ├── excel-automation/
│   │   │   ├── word-document-processor/
│   │   │   ├── pdf/
│   │   │   ├── tavily-search/
│   │   │   ├── financial-calculator/
│   │   │   ├── weather-1.0.0/
│   │   │   ├── design-md/
│   │   │   ├── desktop-control-1.0.0/
│   │   │   ├── self-improving-agent-3.0.5/
│   │   │   ├── tam-sam-som-calculator/
│   │   │   ├── ocr-document-processor/
│   │   │   └── skills-lock.json
│   │   ├── prompts/              # 工作流提示词
│   │   │   ├── 01_think.md
│   │   │   ├── 02_plan.md
│   │   │   ├── 03_act.md
│   │   │   └── 04_reflect.md
│   │   └── __init__.py           # Agent 模块初始化
│   │
│   └── api/                      # FastAPI 模块（服务层）
│       ├── core/
│       │   ├── config.py         # 配置管理
│       │   ├── dependencies.py   # 依赖注入
│       │   └── error_handlers.py # 错误处理
│       ├── db/
│       │   ├── engine.py         # 数据库引擎
│       │   ├── models.py         # 数据模型
│       │   └── repositories/     # 数据仓库
│       ├── router/
│       │   ├── auth.py           # 认证路由
│       │   ├── users.py          # 用户路由
│       │   ├── sessions.py       # 会话路由
│       │   └── agent.py          # Agent 路由
│       ├── services/
│       │   ├── agent.py          # Agent 服务（通过依赖注入连接 Agent）
│       │   ├── auth.py           # 认证服务
│       │   ├── user.py           # 用户服务
│       │   ├── redis_service.py  # Redis 服务
│       │   ├── redis_session_service.py # Redis 会话服务
│       │   └── user_memory_service.py   # 用户记忆服务
│       ├── schemas/
│       │   ├── auth.py           # 认证模型
│       │   └── response.py       # 统一响应
│       ├── utils/
│       │   ├── jwt.py            # JWT 工具
│       │   └── security.py       # 安全工具
│       ├── scripts/
│       │   └── init_db.sql       # 数据库初始化
│       └── main.py               # FastAPI 入口
│
├── .env                          # 环境变量
├── .env.example                  # 环境变量示例
├── pyproject.toml                # 项目配置
├── README.md                     # 本文件
└── uv.lock                       # 依赖锁定
```

---

## 🛠️ 开发指南

### 代码格式化

```bash
ruff format .
ruff check .
ruff check . --fix
```

### 测试

```bash
pytest
pytest tests/test_agent.py
pytest --cov=src --cov-report=term-missing
```

### 添加新工具

1. 在 `src/agent/tools/builtin/` 创建新工具文件
2. 使用 `@tool` 装饰器定义工具函数
3. 在 `src/agent/tools/builtin/__init__.py` 中导出工具
4. 工具会自动被 Agent 加载

### 添加新技能

1. 在 `src/agent/skills/` 创建新技能目录
2. 在目录中创建 `SKILL.md` 文件
3. 技能会自动被 Agent 加载

---

## 🔒 安全性

### 认证安全
- ✅ JWT Token 签名验证
- ✅ Token 存储在 Redis（支持主动失效）
- ✅ 密码使用 bcrypt 加密
- ✅ Token 7 天过期

### 命令执行安全
- ✅ 危险命令黑名单（rm, rmdir, mkfs, etc.）
- ✅ 超时控制（默认 30 秒）
- ✅ 输出截断（防止内存溢出）

### 网络安全
- ✅ 代理设置验证
- ✅ SSL 证书验证
- ✅ 请求超时控制

---

## 🌐 支持的 LLM 模型

| 提供商 | 模型 | 配置示例 |
|--------|------|----------|
| **OpenAI** | GPT-4, GPT-3.5 | `base_url="https://api.openai.com/v1"` |
| **DeepSeek** | deepseek-chat | `base_url="https://api.deepseek.com/v1"` |
| **Ollama** | 本地模型 | `base_url="http://localhost:11434/v1"` |

---

## 🚀 部署

### 生产环境部署

```bash
# 1. 同步依赖
uv sync --locked

# 2. 启动服务
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:9999
```

### Docker 部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync

COPY . .
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "9999"]
```

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [FastAPI](https://fastapi.tiangolo.com/)
- [ReAct Paper](https://arxiv.org/abs/2210.03629)
- [OpenClaw](https://github.com/openclaw/openclaw)

---

<div align="center">

**Made with ❤️ by the ReAct Agent Team**

</div>