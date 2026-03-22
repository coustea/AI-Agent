# ReAct Agent Framework

<div align="center">

**基于 LangGraph 的 ReAct 模式智能体框架 + FastAPI 用户认证系统**

[5-Node Workflow](#architecture) • [快速开始](#quick-start) • [API 文档](#api) • [示例](src/agent/main.py)

</div>

---

## 📖 简介

ReAct Agent Framework 是一个模块化、可扩展的智能体框架，实现了经典的 **ReAct（Reasoning + Acting）模式**，并集成了 **FastAPI 用户认证系统**。

```
📚 Retrieve → 🤔 Think → 🛠️ Plan → ⚡ Act → 👀 Reflect → (循环)
```

### 核心特性

| 特性 | 描述 |
|------|------|
| 🔄 **5 节点工作流** | Retrieve → Think → Plan → Act → Reflect 完整闭环 |
| 🧩 **模块化设计** | 工具、技能、提示词完全解耦 |
| 📝 **SOP 驱动** | 业务知识通过 Markdown 管理，无需修改代码 |
| 🔐 **用户认证系统** | JWT + Redis Token 管理，MySQL 用户存储 |
| 🌐 **RESTful API** | FastAPI 构建的标准 REST 接口 |
| 📊 **流式输出** | 实时查看智能体的思考过程和决策 |

---

## 🏗️ 架构设计

### 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                         ReAct Agent                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              LangGraph StateGraph                         │  │
│  │  Retrieve → Think → Plan → Act → Reflect → Think ...     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 5 节点说明

| 节点 | 职责 | 提示词文件 |
|------|------|-----------|
| **📚 Retrieve** | 加载业务 SOP 和用户记忆 | 无（自动扫描） |
| **🤔 Think** | 意图理解与情境分析 | `01_think.md` |
| **🛠️ Plan** | 决策工具调用或生成答案 | `02_plan.md` + `03_act.md` |
| **⚡ Act** | 执行工具（通过 ToolNode） | 无（LangChain） |
| **👀 Reflect** | 评估结果并决定继续/结束 | `04_reflect.md` |

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

### 认证流程

```
登录 → 创建 JWT → 存 Redis (7天) → 返回 Token
验证 → 解码 JWT → 检查 Redis 是否存在
退出 → 从 Redis 删除 Token
```

---

## 📦 核心组件

### Agent 模块 (`src/agent/`)

| 组件 | 描述 |
|------|------|
| `core/agent.py` | 5 节点 LangGraph 工作流 |
| `core/llm.py` | LLM 封装层 |
| `tools/` | 工具集（shell_exec, web_fetch, file_append） |
| `skills/` | 业务知识（SKILL.md） |
| `prompts/` | 工作流提示词 |

### API 模块 (`src/api/`)

| 组件 | 描述 |
|------|------|
| `db/engine.py` | MySQL + Redis 连接管理 |
| `db/models.py` | SQLAlchemy 数据模型 |
| `router/` | FastAPI 路由（users, auth） |
| `services/` | 业务逻辑层 |
| `schemas/` | Pydantic 请求/响应模型 |
| `utils/` | 工具函数（JWT, 密码加密） |

---

## 📂 项目结构

```
agent/
├── src/
│   ├── agent/                    # ReAct Agent 模块
│   │   ├── core/
│   │   │   ├── agent.py          # 5 节点工作流
│   │   │   ├── llm.py            # LLM 封装
│   │   │   └── logger.py         # 日志系统
│   │   ├── prompts/              # 工作流提示词
│   │   ├── tools/                # 工具实现
│   │   └── skills/               # 业务知识库
│   │
│   └── api/                      # FastAPI 模块
│       ├── db/
│       │   ├── engine.py         # 数据库连接
│       │   ├── models.py         # 数据模型
│       │   └── base.py           # Base 类
│       ├── router/
│       │   ├── users.py          # 用户路由
│       │   └── auth.py           # 认证路由
│       ├── services/
│       │   ├── auth.py           # 认证服务
│       │   └── redis_service.py  # Redis 封装
│       ├── schemas/
│       │   ├── auth.py           # 认证 Schema
│       │   └── response.py       # 统一响应
│       ├── utils/
│       │   ├── jwt.py            # JWT 工具
│       │   └── security.py       # 密码加密
│       ├── scripts/
│       │   └── init_db.sql       # 数据库初始化
│       └── main.py               # FastAPI 入口
│
├── .env                          # 环境变量
├── pyproject.toml                # 项目配置
├── AGENTS.md                     # AI 编码指南
└── README.md                     # 本文件
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

---

## 🔒 安全性

### 认证安全
- ✅ JWT Token 签名验证
- ✅ Token 存储在 Redis（支持主动失效）
- ✅ 密码使用 bcrypt 加密
- ✅ Token 7 天过期

### Shell 命令安全
- ✅ 危险命令黑名单
- ✅ 超时控制
- ✅ 输出截断

---

## 🌐 支持的 LLM 模型

| 提供商 | 模型 | 配置示例 |
|--------|------|----------|
| **OpenAI** | GPT-4, GPT-3.5 | `base_url="https://api.openai.com/v1"` |
| **DeepSeek** | deepseek-chat | `base_url="https://api.deepseek.com/v1"` |
| **Ollama** | 本地模型 | `base_url="http://localhost:11434/v1"` |

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [FastAPI](https://fastapi.tiangolo.com/)
- [ReAct Paper](https://arxiv.org/abs/2210.03629)

---

<div align="center">

**Made with ❤️ by the ReAct Agent Team**

</div>