# AI Learning Platform - Server

基于 FastAPI + LangGraph 的个性化学习后端服务。

当前后端提供四类核心能力：
- 用户认证与会话管理（JWT + 白名单 token）
- AI 导师聊天（流式输出、附件读取、记忆管理）
- 多智能体学习资源生成（SSE）
- 知识库导入与检索（Markdown -> Chroma 向量库）

## 技术栈

- Python 3.13
- FastAPI
- SQLModel + SQLAlchemy Async + MySQL（aiomysql）
- LangChain + LangGraph + OpenAI-compatible LLM
- Chroma + Ollama Embeddings（知识库）
- uv（依赖与运行）

## 目录结构

```text
server/
├── app/
│   ├── main.py                  # FastAPI 入口
│   ├── core/                    # 基础设施（数据库、鉴权、日志、统一响应）
│   ├── models/                  # SQLModel 数据模型
│   ├── services/                # 通用服务（记忆服务）
│   ├── modules/
│   │   ├── auth/                # 注册/登录/登出/用户资料
│   │   ├── chat/                # AI 导师聊天 + 文件上传/读取
│   │   ├── profile/             # 用户画像查询与历史
│   │   ├── resource/            # 多智能体资源生成（SSE）
│   │   └── knowledge_base/      # 知识库导入与检索
│   ├── scripts/                 # 脚本（知识库导入）
│   └── utils/                   # 路径、插件管理等工具
├── doc/                         # 默认知识库文档目录（.md）
├── workplace/                   # 运行产物（上传文件/生成文件）
├── logs/                        # 日志输出
├── .env.example
├── pyproject.toml
└── uv.lock
```

## 快速开始

### 1. 环境要求

- Python 3.13
- MySQL（必需）
- Ollama（仅知识库功能需要）

### 2. 安装依赖

```bash
cd server
uv sync
```

### 3. 配置环境变量

复制 `.env.example` 到 `.env` 并按需修改：

```bash
cp .env.example .env
```

关键配置：
- `APP_DEBUG`：`true` 时启动会重建表（仅开发环境使用）
- `DB_*`：MySQL 连接参数
- `JWT_*`：JWT 配置
- `OPENAI_*`：主模型配置
- `FAST_LLM_*`：轻量模型配置（路由分类/任务规划）
- `SKILLS_DIR` / `WORKPLACE_DIR` / `LOGS_DIR` / `KNOWLEDGE_BASE_DIR`：路径配置

### 4. 启动服务

```bash
# 开发模式（热重载）
uv run fastapi dev app/main.py

# 生产风格启动
uv run python app/main.py
```

默认监听：`http://0.0.0.0:9999`

Swagger 文档：`http://localhost:9999/docs`

## API 概览

### 用户认证（`/api/v1/users`）

- `POST /api/v1/users`：注册
- `POST /api/v1/users/auth`：登录
- `DELETE /api/v1/users/auth`：登出
- `GET /api/v1/users/me`：当前用户信息
- `PATCH /api/v1/users/me`：更新当前用户信息

### 导师聊天（`/api/v1/ai/chat`）

- `POST /stream`：SSE 流式聊天
- `POST /upload`：上传图片/文档
- `GET /uploads/{owner_id}/{filename}`：鉴权下载上传文件
- `GET /sessions`：会话列表
- `POST /sessions`：新建会话
- `DELETE /sessions/{session_id}`：归档会话
- `GET /history`：会话历史

### 画像（`/api/v1/ai/profile`）

- `GET /profile`：当前画像
- `GET /profile/history`：画像历史版本

### 多智能体资源生成（`/api/v1/ai`）

- `POST /generate`：SSE 生成学习资源
- `GET /agents`：可用子智能体列表
- `GET /resources`：资源历史列表
- `GET /resources/{resource_id}`：资源详情

当前注册子智能体：`mindmap/content/code/quiz/reading/media/ppt`

### 知识库（`/api/v1/knowledge`）

- `POST /import`：后台异步导入知识库
- `POST /import/sync`：同步导入知识库
- `POST /search`：向量检索
- `GET /collections`：集合列表

## 调用示例

### 1) 登录获取 Token

```bash
curl -X POST http://localhost:9999/api/v1/users/auth \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"123456"}'
```

### 2) 流式聊天

```bash
curl -N -X POST http://localhost:9999/api/v1/ai/chat/stream \
  -H "Authorization: Bearer <TOKEN>" \
  -H 'Content-Type: application/json' \
  -d '{"message":"请解释快速排序"}'
```

### 3) 触发资源生成（SSE）

```bash
curl -N -X POST http://localhost:9999/api/v1/ai/generate \
  -H "Authorization: Bearer <TOKEN>" \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": 1,
    "learning_task": {
      "course": "数据结构",
      "gap": "二叉树遍历不熟",
      "need": "review",
      "extra": "希望带可运行代码"
    }
  }'
```

### 4) 导入知识库

```bash
curl -X POST http://localhost:9999/api/v1/knowledge/import/sync \
  -H "Authorization: Bearer <TOKEN>" \
  -H 'Content-Type: application/json' \
  -d '{"directory_path":"doc","collection_name":"knowledge_base"}'
```

或使用脚本：

```bash
uv run python -m app.scripts.import_knowledge
```

## 数据与运行目录

- 业务表：`user`、`active_token`、`chat_sessions`、`chat_messages`、`user_memory`、`user_profile`、`user_profile_history`、`generated_resource`
- 上传与产物：`workplace/`
- 日志：`logs/`
- 知识库持久化：默认 `./data`（由知识库服务管理）

## 开发与测试

```bash
# 语法快速检查
uv run python -m compileall app

# pytest（当前项目测试较少）
uv run pytest -q
```

## 注意事项

- `APP_DEBUG=true` 会在启动时 `drop_all + create_all`，仅用于可丢弃环境。
- 聊天上传文件通过鉴权接口访问，不再提供公开静态下载。
- 知识库默认使用 `OllamaEmbeddings(model="bge-m3:latest")`，请确保本地可用。
