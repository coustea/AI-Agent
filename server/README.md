# AI Learning Platform - 后端

FastAPI + LangGraph 多智能体学习平台后端。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI, SQLModel, SQLAlchemy Async |
| 多智能体 | LangGraph, LangChain |
| 数据库 | PostgreSQL (asyncpg) |
| LLM | OpenAI 兼容 API (ChatOpenAI) |
| 向量检索 | ChromaDB, FAISS, Ollama (bge-m3) |
| 包管理 | uv |

## 项目结构

```
server/
├── app/                     # 应用源码
│   ├── auth/                # 认证与用户管理（JWT + ActiveToken 白名单）
│   ├── chat/                # AI 辅导对话（SSE 流式）
│   ├── resource/            # 多智能体资源生成
│   ├── path/                # 学习路径规划
│   ├── memory/              # 记忆系统（短期/长期/画像）
│   ├── evaluation/          # 学习评估与事件
│   ├── dashboard/           # 首页仪表盘
│   ├── quiz/                # 题库与编程题
│   ├── avatar/              # 数字人（讯飞 WebSocket）
│   ├── profile/             # 用户画像
│   ├── infra/               # 基础设施（DB, LLM, 配置, 日志, 模型注册）
│   ├── prompts/             # 全局 Prompt 模板
│   ├── app_factory.py       # FastAPI 应用工厂
│   ├── lifecycle.py         # 启动生命周期
│   ├── routes.py            # 路由挂载
│   ├── ws_routes.py         # WebSocket 路由
│   └── main.py              # 入口
├── tests/                   # pytest 测试
├── config.yaml              # 运行配置
├── init_schema.sql          # 数据库初始化脚本
└── pyproject.toml           # Python 依赖
```

## 快速开始

### 前置条件

- Python 3.13+
- PostgreSQL
- [uv](https://docs.astral.sh/uv/)（Python 包管理器）

### 1. 安装依赖

```bash
cd server
uv sync
```

### 2. 配置

编辑 `config.yaml`，至少配置以下项：

```yaml
database:
  url: postgresql+asyncpg://user:pass@localhost:5432/dbname
jwt:
  secret_key: your-secret-key
models:
  base_url: https://api.openai.com/v1
  api_key: sk-xxx
  model_name: gpt-4o
```

可选配置：`models.vision`（视觉模型）、`search.tavily_key`（搜索）、`avatar.*`（数字人）、`knowledge.*`（向量检索）。

### 3. 初始化数据库

```bash
psql -d dbname -f server/init_schema.sql
```

### 4. 启动

```bash
uv run fastapi dev app/main.py --port 9999
```

- API 文档：http://localhost:9999/docs

## 多智能体架构

### 辅导对话（TutorAgent）

基于 LangGraph StateGraph，节点流程：`classify` → 路由分发 → `answer_node` / `search_node` / `attachment_answer` / `teaching_diagram_generate`。通过 SSE 流式输出，读取三层上下文（画像、长期记忆、对话历史）。

### 资源生成（Resource Agents）

两种编排模式：

- **多智能体模式**：PlanningAgent → 并行 Worker Agents → ReviewAgent → 存储
- **单智能体模式**：直接调用 `AGENT_REGISTRY[agent_id].run(state)`，用于路径节点内按需生成

已注册 Agent：`planning`、`content`、`mindmap`、`quiz`、`code`、`reading`、`ppt`、`review`。每个 Agent 继承 `BaseResourceAgent`，通过 `@register_agent` 注册。

### 记忆系统（MemoryService）

三层记忆架构：

- **SessionCompressor** — 短期对话 → 摘要压缩
- **LongTermMemoryExtractor** — 事实提取至 `UserLongTermMemory`
- **ProfileBuilder** — 8 维度画像构建（从记忆 + 事件）

由 `ChatSession` 的 token 计数阈值触发。

### 学习路径（Path Planner）

课程级学习路径规划 Agent，节点资源生成使用单智能体模式。路径内形成「教程 → 题目 → 辅助资源」的学习闭环。

### 数字人（Avatar Bridge）

WebSocket 桥接讯飞数字人服务，ASR → 数字人播报。前端通过 `ws://host:9999/ws/avatar?token=JWT` 连接。

## API 路由

| 前缀 | 模块 | 主要端点 |
|------|------|----------|
| `/api/v1/users` | auth | 注册, 登录, 登出, 用户信息 |
| `/api/v1/ai/chat` | chat | SSE 流式对话, 附件上传, 会话管理 |
| `/api/v1/ai/resource` | resource | 资源生成（多/单智能体）, 状态查询, 事件流 |
| `/api/v1/ai/path` | path | 路径规划, 节点工作空间, 教程/题目生成 |
| `/api/v1/ai/evaluation` | evaluation | 学习事件, 评估 |
| `/api/v1/ai/dashboard` | dashboard | 首页聚合数据 |
| `/api/v1/ai/quiz-bank` | quiz | 题库管理 |
| `/api/v1/ai/wrong-questions` | quiz | 错题本 |
| `/api/v1/ai/avatar` | avatar | 数字人 REST 接口 |
| `/ws/avatar` | websocket | 数字人 WebSocket |

所有 API 响应使用 `HttpResponse` 信封格式：`{code, message, data}`。

## 认证流程

1. 登录返回 JWT Token，前端存入 `localStorage`
2. 请求通过 `get_current_user` 依赖校验 JWT + `ActiveToken` 数据库白名单
3. 登出移除白名单 Token + 触发后台画像构建
4. WebSocket 认证使用查询参数 `?token=JWT`

## 核心数据表

| 领域 | 表 |
|------|-----|
| 认证 | `users`, `active_tokens` |
| 对话 | `chat_sessions`, `chat_messages`, `chat_session_summaries` |
| 记忆 | `user_long_term_memories`, `user_profiles`, `user_profile_histories` |
| 资源生成 | `generated_resources`, `generated_resource_items` |
| 学习路径 | `learning_paths`, `path_nodes`, `path_node_tutorials`, `path_node_questions`, `path_node_resources` |
| 评估 | `learning_events`, `learning_sessions` |
| 题库 | `quiz_questions`, `programming_problems` |

数据库结构变更需同步修改 `init_schema.sql` 和 `infra/models.py`，新表必须加入 `REGISTERED_MODELS` 元组。

## Prompt 系统

每个模块拥有独立的 `prompts/` 目录，使用 `.md` 模板文件：

- `chat/prompts/` — 辅导系统指令, 回答策略, 搜索指令, 教学图
- `memory/prompts/` — 压缩, 长期记忆更新, 画像
- `path/prompts/` — 路径规划, 教程, 题目生成
- `resource/prompts/` — 各 Agent 指令

模板支持 `{variable_name}` 变量替换，启动时通过 `warm_prompt_loaders()` 预加载缓存。

## 路径规划与资源生成的边界

> 这是本项目最重要的设计约束。

**独立资源生成**：用户直接请求"生成教程/导图/PPT"，不依赖学习路径上下文。数据存 `generated_resources`，API 走 `/resource`。

**路径节点资源**：用户在学习路径内，围绕节点生成资源。数据存 `path_node_resources`，API 走 `/path`。

两种资源不共用记录表和展示接口。

## 测试

```bash
# 全部测试
uv run pytest

# 指定模块
uv run pytest tests/chat -q
uv run pytest tests/resource -q
uv run pytest tests/path -q

# 首个失败即停止
uv run pytest -x
```

已知的预存在问题（不要浪费时间调试）：

- `tests/chat/test_agent_single_module_refactor.py` — 过时断言
- `tests/chat/test_onboarding_api.py` — 缺少 `background_tasks` 参数
- `tests/chat/test_reasoning_agent.py` — `FakeLlm` 缺少 `astream` 属性

## 开发约定

- 配置统一从 `config.yaml` 读取，不硬编码、不使用 `.env`
- 数据库结构变更同步修改 `init_schema.sql` 和 `infra/models.py`
- 新表必须加入 `REGISTERED_MODELS` 元组
- `get_session()` 用于 FastAPI 依赖注入（手动提交），`session_scope()` 用于后台任务（自动提交/回滚）
- `runtime_context(user_id, session_id)` ContextVar 在异步调用链中传递用户身份
- LLM 通过 `get_llm()` 单例访问，使用 OpenAI 兼容 API
- Python 代码遵循 Google Python Style Guide
- 4-space indent, type hints, snake_case modules
- 前端 `.vue` 文件使用 `<script setup lang="ts">`，禁止 Options API

## 故障排查

| 问题 | 排查方向 |
|------|----------|
| 启动数据库错误 | 检查 `config.yaml` 的 `database.url`、PostgreSQL 是否运行、是否执行过 `init_schema.sql` |
| 首页 500 | 检查 dashboard 聚合查询是否访问不存在的表/字段 |
| 路径规划异常 | 检查 `learning_paths` 子表结构、接口字段与前端是否一致、节点资源是否误走独立资源域 |
| 前端 API 500 | 检查 Vite 代理端口（9999）是否与后端一致 |
