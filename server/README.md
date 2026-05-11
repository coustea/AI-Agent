# AI Learning Platform Backend

基于 FastAPI + LangChain + LangGraph 的全栈 AI 多智能体个性化学习平台后端。该系统集成了智能导师对话、自适应学习路径规划、多智能体资源生成、数字人交互以及领域驱动设计的记忆系统。

## 核心功能

### 1. 智能导师 (Tutor Agent)
- **多模态交互**：支持 SSE 流式文本回复，集成 GLM-4V / 讯飞星火进行图片理解。
- **文档感知**：支持 PDF、Word、Markdown 等多种格式文档上传与解析，实现 RAG 问答。
- **工具增强**：Agent 可自动调用百度搜索、学习资源生成、图片生成等工具。
- **实时绘图**：内置 Mermaid 渲染支持，可动态生成知识架构图。

### 2. 多智能体资源生成 (Resource Agents)
- **DAG 编排**：由 `CoordinatorAgent` 驱动的定向无环图任务流，多 Agent 协作。
- **专业子 Agent**：
  - **Mindmap Agent**：生成结构化思维导图（Markmap）。
  - **PPT Agent**：自动化生成教学演示文稿。
  - **Quiz Agent**：基于知识点生成分层练习题。
  - **Code Agent**：生成并验证示例代码，支持 Shell 执行。
  - **Content Agent**：分步撰写高质量教学文章（大纲 -> 正文）。
  - **Reading Agent**：推荐权威学习资源清单。

### 3. 学习路径规划 (Path Planner)
- **自适应规划**：根据用户画像与当前资源生成个性化学习路径。
- **动态反馈**：支持用户反馈调整，实现路径的即时重构与薄弱点强化。

### 4. 数字人交互 (Digital Human)
- **实时同步**：基于 WebSocket 的数字人驱动桥接（Avatar Bridge）。
- **语音集成**：深度集成讯飞 ASR（语音识别）与数字人视频流输出。
- **多感官教学**：支持数字人状态管理、流控及附件并行分析。

### 5. 记忆与画像系统 (Memory & Profile)
采用领域驱动设计（DDD）架构，提供清晰的领域边界和统一的公共 API。

#### 架构设计
```
memory/
├── layer.py             # MemoryLayer - 统一公共入口
├── prompts/             # Prompt 模板文件
├── core/                # 核心层：公共类型、基类、工具
├── session/             # 会话领域：会话管理
├── message/             # 消息领域：对话消息存储
├── summary/             # 概要领域：会话压缩与摘要
├── profile/             # 画像领域：8 维度用户画像
├── memory/              # 长期记忆领域：事实提取与沉淀
├── context/             # 上下文领域：上下文构建策略
└── pipeline/            # 流水线领域：后处理编排
```

#### 核心特性
- **三层存储架构**：
  - **短期记忆 (Message)**：基于 Session 的即时对话上下文，支持附件和工具调用记录。
  - **长期记忆 (Memory)**：事实提取、知识沉淀与自动去重，支持证据计数和版本追踪。
  - **用户画像 (Profile)**：8 维度（知识基础、学习目标、实践能力、学习偏好、稳定弱点、项目背景、交互规则、有效策略）动态构建。
- **会话压缩 (Summary)**：对话达到 token 阈值时自动触发 LLM 摘要，保留关键信息。
- **上下文构建 (Context)**：智能组装画像、长期记忆、会话概要和最近对话，支持 token 预算控制。
- **后处理流水线 (Pipeline)**：对话后自动触发记忆更新、画像构建和会话压缩。

#### 使用方式
外部模块应通过 `MemoryLayer` 访问记忆系统：
```python
from app.memory import MemoryLayer

layer = MemoryLayer(module="mentor")

# 会话管理
session = await layer.create_session(user_id=7, title="新对话")
messages = await layer.list_messages(user_id=7, session_id="s-1")

# 画像操作
profile = await layer.get_or_create_profile(user_id=7)
await layer.build_profile(user_id=7, session_id="s-1")

# 长期记忆
memory = await layer.get_or_create_long_term_memory(user_id=7)
await layer.update_long_term_memory(
    user_id=7, session_id="s-1",
    user_message="...", assistant_reply="..."
)

# 上下文构建
context = await layer.build_tutor_context(user_id=7, session_id="s-1")

# 后处理流水线
await layer.post_turn_pipeline(
    user_id=7, session_id="s-1",
    user_message="...", assistant_reply="..."
)
```

### 6. 学习评价 (Evaluation)
- **事件跟踪**：记录用户学习行为事件（阅读、练习、反馈）。
- **分析报告**：提供基于行为数据的学习摘要与评价汇总。

## 技术栈

- **核心框架**：Python 3.13 + FastAPI + SQLModel (SQLAlchemy Async)
- **AI 编排**：LangChain + LangGraph
- **数据库**：MySQL (aiomysql)
- **依赖管理**：uv
- **大模型支持**：
  - OpenAI (GPT-4o/o1)
  - 讯飞星火 (Spark Max/X/Vision/Image)
  - 智谱 AI (GLM-4V)
- **搜索增强**：DuckDuckGo
- **存储**：本地文件存储

## 目录结构

```text
app/
├── auth/           # 用户认证：JWT、权限校验、个人信息
├── chat/           # 智能导师：LangGraph Agent、SSE 路由、工具集
├── resource/       # 资源生成：多 Agent 编排、DAG 任务规划
├── avatar/         # 数字人：WS 桥接、ASR/TTS 集成、状态控制
├── evaluation/     # 学习评价：事件记录、行为分析
├── memory/         # 记忆层：DDD 架构的记忆与画像系统
│   ├── layer.py    # MemoryLayer 统一入口
│   ├── core/       # 核心层：公共类型和基类
│   ├── session/    # 会话领域
│   ├── message/    # 消息领域
│   ├── summary/    # 概要领域
│   ├── profile/    # 画像领域
│   ├── memory/     # 长期记忆领域
│   ├── context/    # 上下文领域
│   └── pipeline/   # 后处理流水线
├── infra/          # 基础设施：SQLModel 定义、异步 DB 引擎、LLM 工厂
└── shared/         # 共享模块：响应封装、存储服务、日志配置
```

## 快速开始

### 1. 环境准备
- 安装 **Python 3.13+**
- 安装 **uv**：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- 安装 **MySQL 8.0+**

### 2. 安装依赖
```bash
uv sync
```

### 3. 环境配置
复制 `.env.example` 并配置（详见下文）：
```bash
cp .env.example .env
```

### 4. 启动服务
```bash
# 开发模式（热重载）
uv run fastapi dev app/main.py

# 生产模式
uv run python app/main.py
```

## 环境变量说明

| 变量名 | 说明 | 示例 |
|---|---|---|
| `DB_HOST` | 数据库主机 | `localhost` |
| `DB_PORT` | 数据库端口 | `3306` |
| `DB_USER` | 数据库用户 | `root` |
| `DB_PASSWORD` | 数据库密码 | `your_password` |
| `DB_NAME` | 数据库名称 | `agent` |
| `OPENAI_API_KEY` | 主 LLM 密钥 | `sk-xxxx` |
| `OPENAI_API_BASE` | LLM API 基址 | `https://api.openai.com/v1` |
| `SPARK_MAX_API_PASSWORD` | 讯飞星火 API 密钥 | 用于模型调用 |
| `GLM_API_KEY` | 智谱 AI 密钥 | 用于多模态理解 |
| `JWT_SECRET_KEY` | JWT 加密密钥 | `openssl rand -hex 32` |

## API 主要端点

### 认证 & 用户 (`/api/v1/users`)
- `POST /` : 注册新用户
- `POST /auth` : 登录并获取 JWT
- `DELETE /auth` : 登出（移除 Token 白名单）
- `GET /me` : 获取当前用户信息
- `PATCH /me` : 更新用户信息

### AI 交互 (`/api/v1/ai`)
- `POST /chat/stream` : SSE 流式导师对话（支持文件/图片）
- `POST /chat/upload` : 上传对话附件
- `GET /chat/sessions` : 获取会话列表
- `POST /chat/sessions` : 创建新会话
- `DELETE /chat/sessions/{id}` : 删除会话
- `GET /chat/history` : 获取对话历史

### 资源生成 (`/api/v1/ai`)
- `POST /generate` : SSE 多智能体资源生成任务
- `GET /agents` : 获取可用 Agent 列表
- `GET /resources` : 获取已生成资源列表
- `GET /resources/{id}` : 获取单个资源详情

### 画像 & 记忆 (`/api/v1/ai`)
- `GET /profile` : 查询当前用户画像
- `GET /profile/history` : 获取画像版本历史

### 数字人 (`/api/v1/ai`)
- `GET /avatar/status` : 获取数字人状态
- `GET /avatar/stream` : 获取数字人视频流地址
- `POST /avatar/stop` : 停止数字人交互
- `WS /ws/avatar` : 数字人 WebSocket 交互（JWT 认证）

## 测试

```bash
# 运行所有测试
uv run pytest

# 运行记忆模块测试
uv run pytest tests/memory/ -v

# 运行单个测试文件
uv run pytest tests/memory/test_public_entrypoints.py -v
```

## 开发指南

### 记忆系统扩展

每个领域遵循相同的结构：
- `types.py` - 领域类型定义
- `store.py` - 数据库 CRUD 操作
- `service.py` - 业务逻辑
- `schemas.py` - API 请求/响应模型

新增领域时，在 `MemoryLayer` 中添加对应的 service 和公共方法。

### 代码规范

- 使用 `HttpResponse` 封装所有 API 响应
- 配置值通过 `app/config.py` 读取，不直接调用 `os.getenv()`
- 路径常量使用 `shared/paths.py` 中定义的变量
- LLM JSON 输出使用 `shared/json_utils.py` 解析

---
Generated with Claude Code.