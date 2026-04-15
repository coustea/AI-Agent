# AI Learning Platform Backend

基于 FastAPI + LangGraph 的多智能体学习平台后端。

当前版本已经切到新主架构：

- `interface`：HTTP / SSE 入口
- `usecases`：用例编排
- `runtime`：Agent 运行时
- `agents`：聊天、画像、资源智能体
- `ports`：抽象接口
- `adapters`：数据库、鉴权、存储、外部服务适配

仓库里原来的 `app/api`、`app/application`、`app/modules` 已删除，README 仅描述现行结构。

## 功能

- JWT 用户认证
- AI 导师流式对话
- 图片 / 文档上传与会话内读取
- 用户画像构建与历史查询
- 多智能体学习资源生成
- SSE 流式资源生成事件

## 技术栈

- Python 3.13
- uv
- FastAPI
- SQLModel + SQLAlchemy Async + MySQL
- LangChain + LangGraph
- OpenAI-compatible LLM API
- GLM-4V / 星火图片理解

## 目录结构

```text
app/
├── main.py
├── bootstrap/          # 应用启动、容器、lifespan、环境加载
├── interface/http/     # FastAPI 路由与依赖
├── usecases/           # 认证、聊天、画像、资源生成用例
├── runtime/            # Chat / Profile / Resource 运行时
├── agents/             # 具体 Agent 实现与共享工具
├── adapters/           # DB / Auth / Storage / External adapters
├── ports/              # 抽象接口
├── domain/             # 领域服务
├── infrastructure/     # 基础设施实现（仍有部分过渡代码）
├── services/           # 旧 memory facade，仍在迁移中
├── shared/             # DTO / 共享结构
├── models/             # SQLModel 模型
└── utils/              # 纯工具与路径辅助
```

## 架构说明

主调用链：

```text
HTTP Request
  -> interface/http
  -> usecases
  -> runtime
  -> agents / ports
  -> adapters / domain / infrastructure
```

设计原则：

- Router 只处理协议、鉴权、参数校验
- UseCase 负责流程编排
- Runtime 负责 Agent 调用和流式输出
- Adapter 负责技术接入，不承载业务流程

当前仍在迁移中的部分：

- `app/services/memory.py`
- `app/infrastructure/*` 的部分能力

也就是说，入口层和主业务层已经是新架构，但底层还有少量兼容层未彻底收口。

## 环境要求

- Python `>=3.13`
- MySQL 8+
- `uv`

## 安装依赖

```bash
uv sync
```

## 环境变量

最少需要配置：

```dotenv
# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=9999
APP_DEBUG=false

# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=agent
DB_ECHO=false

# JWT
JWT_SECRET_KEY=replace_me
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# Main LLM
OPENAI_API_KEY=your_key
OPENAI_API_BASE=https://your-openai-compatible-endpoint
OPENAI_MODEL=gpt-4o-mini

# Fast / Classifier LLM
FAST_LLM_API_KEY=your_key
FAST_LLM_MODEL=general

# Vision
GLM_API_KEY=your_key
GLM_VISION_MODEL=glm-4v-flash

# Optional: Spark image understanding
SPARK_IMAGE_APPID=your_appid
SPARK_IMAGE_API_KEY=your_key
SPARK_IMAGE_API_SECRET=your_secret
```

说明：

- `DB_PASSWORD` 为必填，未配置时应用启动会失败
- `.env` 由 `app/main.py` 启动时统一加载
- `APP_DEBUG=true` 会在启动时重建表，只能用于临时开发库

## 启动

开发模式：

```bash
uv run fastapi dev app/main.py
```

生产模式：

```bash
uv run python app/main.py
```

默认地址：

- API: `http://127.0.0.1:9999`
- Swagger: `http://127.0.0.1:9999/docs`

## 测试与校验

运行测试：

```bash
uv run pytest -q
```

快速静态校验：

```bash
uv run python -m py_compile $(rg --files app -g '*.py')
```

## API 概览

### 用户认证

前缀：`/api/v1/users`

- `POST /api/v1/users`：注册
- `POST /api/v1/users/auth`：登录
- `DELETE /api/v1/users/auth`：登出
- `GET /api/v1/users/me`：当前用户
- `PATCH /api/v1/users/me`：更新当前用户

### 聊天

前缀：`/api/v1/ai/chat`

- `POST /api/v1/ai/chat/stream`：SSE 流式对话
- `POST /api/v1/ai/chat/upload`：单文件上传
- `GET /api/v1/ai/chat/uploads/{owner_id}/{session_id}/{filename}`：读取上传文件
- `GET /api/v1/ai/chat/sessions`：会话列表
- `POST /api/v1/ai/chat/sessions`：创建会话
- `DELETE /api/v1/ai/chat/sessions/{session_id}`：归档会话
- `GET /api/v1/ai/chat/history`：历史消息

### 用户画像

前缀：`/api/v1/ai`

- `GET /api/v1/ai/profile`：当前画像
- `GET /api/v1/ai/profile/history`：画像历史

### 学习资源

前缀：`/api/v1/ai`

- `POST /api/v1/ai/generate`：SSE 生成学习资源
- `GET /api/v1/ai/agents`：可用资源 Agent 列表
- `GET /api/v1/ai/resources`：资源历史
- `GET /api/v1/ai/resources/{resource_id}`：资源详情

## 运行时说明

### Chat Runtime

聊天运行时入口：

- `app/runtime/chat/tutor_runtime.py`
- `app/agents/chat/tutor_agent.py`

主要能力：

- 普通文本问答
- 图片理解
- 工具调用
- 会话级文件读取

### Resource Runtime

资源生成运行时入口：

- `app/runtime/resource/resource_runtime.py`
- `app/runtime/resource/coordinator.py`

当前已注册资源 Agent：

- `mindmap`
- `content`
- `code`
- `quiz`
- `reading`
- `ppt`

资源生成通过 `text/event-stream` 输出阶段事件。

## 示例

登录：

```bash
curl -X POST http://127.0.0.1:9999/api/v1/users/auth \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"123456"}'
```

文本流式对话：

```bash
curl -N -X POST http://127.0.0.1:9999/api/v1/ai/chat/stream \
  -H "Authorization: Bearer <TOKEN>" \
  -F "message=请解释快速排序"
```

带文件的流式对话：

```bash
curl -N -X POST http://127.0.0.1:9999/api/v1/ai/chat/stream \
  -H "Authorization: Bearer <TOKEN>" \
  -F "message=帮我分析这张图和这份文档" \
  -F "files=@/path/to/image.png" \
  -F "files=@/path/to/file.pdf"
```

生成学习资源：

```bash
curl -N -X POST http://127.0.0.1:9999/api/v1/ai/generate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "learning_task": {
      "course": "数据结构",
      "gap": "二叉树遍历",
      "need": "review",
      "extra": "需要配套练习题"
    },
    "selected_resources": ["mindmap", "content", "quiz"]
  }'
```

## 开发约定

- 新功能不要再放入旧 `modules` 风格目录
- 新入口统一放到 `interface/http`
- 业务流程放到 `usecases`
- 新的外部依赖接入优先放 `adapters`
- 如果要继续重构，优先收口 `services/memory.py`

## 当前状态

这是一个已经完成主入口切换、但仍处于重构中的代码库。

你在仓库里看到的新旧并存现象，含义应这样理解：

- `interface / usecases / runtime / agents / adapters / ports`：现行主结构
- `services / infrastructure`：仍待进一步拆分

如果要继续推进架构演进，建议优先做：

1. 去掉 `services/memory.py` facade
2. 把 `infrastructure.llm` 的工厂进一步上提到 `adapters`
3. 继续压缩 `agents` 对 legacy domain/service 的直接依赖
