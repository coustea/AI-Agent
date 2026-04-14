# 多智能体个性化学习资源平台 - 后端服务

基于 FastAPI + LangGraph 的多智能体学习平台后端，提供 AI 导师对话、用户画像构建、多格式学习资源生成、知识库检索等能力。

## 技术栈

- **Python 3.13** + **uv** 包管理
- **FastAPI** + Uvicorn
- **SQLModel** + SQLAlchemy Async + MySQL (aiomysql)
- **LangChain** + **LangGraph** 状态图编排
- **星火大模型** (主模型) + **GLM-4V** (图片理解) + **Ollama Embeddings** (知识库)

## 目录结构

```text
server/
├── app/
│   ├── main.py                    # FastAPI 入口，路由注册与生命周期
│   ├── core/
│   │   ├── engine.py              # MySQL 异步引擎、init_db、APP_DEBUG
│   │   ├── security.py            # JWT 签发/校验、bcrypt 密码、白名单
│   │   ├── response.py            # HttpResponse 统一响应 {code, message, data}
│   │   ├── dependencies.py        # get_session 依赖
│   │   └── logging.py             # 日志配置
│   ├── models/                    # SQLModel 数据模型
│   │   ├── user.py                # User
│   │   ├── auth.py                # ActiveToken (JWT 白名单)
│   │   ├── common.py              # ChatMessage, UserMemory, ChatSession
│   │   ├── profile_builder.py     # UserProfile, UserProfileHistory
│   │   └── resource.py            # GeneratedResource
│   ├── modules/
│   │   ├── auth/                  # 注册、登录、登出、用户信息
│   │   ├── chat/                  # AI 导师对话 (TutorAgent + LangGraph)
│   │   ├── profile/               # 用户画像查询与历史版本
│   │   ├── resource/              # 多智能体资源生成 (SSE)
│   │   ├── knowledge_base/        # Markdown 知识库导入与向量检索
│   │   ├── assessment/            # 评估模块
│   │   └── path_planner/          # 学习路径规划
│   ├── services/
│   │   └── memory.py              # 统一记忆服务 (短期/长期/画像)
│   ├── utils/
│   │   ├── plugin_manager.py      # 工具与技能插件管理
│   │   ├── mcp_manager.py         # MCP 外部工具服务管理
│   │   ├── spark_image.py         # 星火图片理解 WebSocket API
│   │   └── paths.py               # 路径常量
│   └── scripts/                   # 运维脚本
├── workplace/                     # 运行产物 (上传文件、生成文件)
├── logs/                          # 日志输出
├── .env                           # 环境变量
├── langgraph.json                 # LangGraph CLI 配置
├── pyproject.toml
└── uv.lock
```

## 快速开始

### 1. 环境要求

- Python 3.13+
- MySQL 8.0+
- [uv](https://docs.astral.sh/uv/) 包管理器
- Ollama (仅知识库功能需要，模型: `bge-m3:latest`)

### 2. 安装依赖

```bash
cd server
uv sync
```

### 3. 配置环境变量

编辑 `.env`：

```dotenv
# 应用配置
APP_DEBUG=false              # true 时启动会重建所有表，仅开发环境
SERVER_HOST=0.0.0.0
SERVER_PORT=9999

# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=agent

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# 主模型 (星火 Pro)
OPENAI_API_BASE=https://spark-api-open.xf-yun.com/v1/
OPENAI_API_KEY=your-key
OPENAI_MODEL=generalv3.5

# 轻量模型 (星火 Lite，用于意图分类)
FAST_LLM_API_KEY=your-key
FAST_LLM_MODEL=general

# GLM 图片理解
GLM_API_KEY=your-key
GLM_VISION_MODEL=glm-4v-flash

# 星火图片理解 WebSocket
SPARK_IMAGE_APPID=your-appid
SPARK_IMAGE_API_KEY=your-key
SPARK_IMAGE_API_SECRET=your-secret

# 路径配置
WORKPLACE_DIR=workplace
LOGS_DIR=logs
KNOWLEDGE_BASE_DIR=data
```

### 4. 启动服务

```bash
# 开发模式 (热重载)
uv run fastapi dev app/main.py

# 生产模式
uv run python app/main.py
```

- 默认监听：`http://0.0.0.0:9999`
- Swagger 文档：`http://localhost:9999/docs`

### 5. 启动 LangGraph Studio (可选)

```bash
uv run langgraph dev
```

- API：`http://127.0.0.1:2024`
- Studio UI：`https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`

## API 概览

### 认证 (`/api/v1/users`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/` | 注册 |
| POST | `/auth` | 登录 (返回 JWT) |
| DELETE | `/auth` | 登出 (移除白名单) |
| GET | `/me` | 当前用户信息 |
| PATCH | `/me` | 更新用户信息 |

### AI 导师对话 (`/api/v1/ai/chat`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/stream` | 流式对话 (form-data，支持文件上传) |
| POST | `/upload` | 上传图片/文档 |
| GET | `/uploads/{owner_id}/{session_id}/{filename}` | 鉴权读取上传文件 |
| GET | `/sessions` | 会话列表 |
| POST | `/sessions` | 创建新会话 |
| DELETE | `/sessions/{session_id}` | 归档会话 |
| GET | `/history` | 聊天历史 |

### 用户画像 (`/api/v1/ai`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/profile` | 当前用户画像 |
| GET | `/profile/history` | 画像历史版本 |

### 资源生成 (`/api/v1/ai`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/generate` | SSE 流式生成学习资源 |
| GET | `/agents` | 可用子智能体列表 |
| GET | `/resources` | 资源历史 |
| GET | `/resources/{resource_id}` | 资源详情 |

已注册子智能体：`mindmap` `content` `code` `quiz` `reading` `media` `ppt`

### 知识库 (`/api/v1/knowledge`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/import` | 后台异步导入 |
| POST | `/import/sync` | 同步导入 |
| POST | `/search` | 向量检索 |
| GET | `/collections` | 集合列表 |

## 多智能体架构

### TutorAgent (导师对话)

核心对话引擎，基于 LangGraph 状态图实现三路路由：

```text
用户消息 → classify (意图分类)
           ├─ direct → 直接回答 (主模型)
           ├─ vision → 图片理解 (星火优先 → GLM 回退)
           └─ tool_needed → Agent 循环 (工具调用)
```

- **意图分类**：轻量模型判断走哪条路径
- **图片理解**：星火 WebSocket API 识别 → 主 LLM 统一风格回复；失败回退 GLM-4V 多模态
- **工具循环**：支持本地工具 (文件操作、代码执行) + MCP 技能插件

### 记忆系统

三层记忆架构，由 `MemoryService` 统一管理：

| 层级 | 存储 | 说明 |
|------|------|------|
| 短期记忆 | `chat_messages` 表 | 原始对话记录 |
| 长期记忆 | `user_memory` 表 | LLM 提炼的稳定事实 (偏好/目标/薄弱点等) |
| 用户画像 | `user_profile` 表 | 8 维度结构化学习画像，带版本快照 |

后处理流水线：每轮对话后累积 token → 触发事实提取 → 触发画像更新。

### 资源生成

`resource_router` 通过 SSE 流式生成多种格式的学习资源，由 `langgraph_dev.py` 中注册的子 graph 执行。

## 调用示例

### 登录

```bash
curl -X POST http://localhost:9999/api/v1/users/auth \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"123456"}'
```

### 流式对话 (纯文本)

```bash
curl -N -X POST http://localhost:9999/api/v1/ai/chat/stream \
  -H "Authorization: Bearer <TOKEN>" \
  -F "message=请解释快速排序" \
  -F "session_id=<SESSION_ID>"
```

### 流式对话 (带图片)

```bash
curl -N -X POST http://localhost:9999/api/v1/ai/chat/stream \
  -H "Authorization: Bearer <TOKEN>" \
  -F "message=这张图片是什么" \
  -F "session_id=<SESSION_ID>" \
  -F "files=@/path/to/image.png"
```

### 生成学习资源

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

### 导入知识库

```bash
curl -X POST http://localhost:9999/api/v1/knowledge/import/sync \
  -H "Authorization: Bearer <TOKEN>" \
  -H 'Content-Type: application/json' \
  -d '{"directory_path":"doc","collection_name":"knowledge_base"}'
```

## 数据模型

| 表名 | 说明 |
|------|------|
| `user` | 用户信息 |
| `active_token` | JWT 白名单 |
| `chat_sessions` | 会话 (含 token 计数器) |
| `chat_messages` | 聊天消息 (含附件/工具调用记录) |
| `user_memory` | 长期记忆事实 |
| `user_profile` | 8 维度学习画像 |
| `user_profile_history` | 画像版本快照 |
| `generated_resource` | 生成的学习资源 |

## 注意事项

- `APP_DEBUG=true` 启动时会 `DROP ALL + CREATE ALL`，仅用于可丢弃数据的开发环境
- 对话接口使用 `form-data` 格式，支持直接上传文件
- 图片理解链路：星火 WebSocket 优先，失败自动回退 GLM-4V
- 知识库需要本地运行 Ollama 并拉取 `bge-m3:latest` 模型
