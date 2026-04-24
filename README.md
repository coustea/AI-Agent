# 多智能体个性化学习资源平台

全栈项目：**Vue 3 + TypeScript** 前端 + **FastAPI + SQLModel** 后端。

基于 LangChain + LangGraph 构建多智能体系统，提供个性化学习辅导、用户画像构建、多模态资源生成等能力。

## 快速开始

### 前端

```bash
npm install
npm run dev        # http://localhost:5173
```

### 后端

```bash
cd server
uv sync            # 安装 Python 依赖
uv run fastapi dev app/main.py   # http://localhost:9999
```

API 文档：`http://localhost:9999/docs`

## 环境要求

- Python `>=3.13`
- Node.js `>=18`
- MySQL 8+
- [uv](https://docs.astral.sh/uv/)（Python 包管理）
- Tesseract OCR（图片文字识别）

### 安装 Tesseract OCR

```bash
# Ubuntu / Debian
sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng

# macOS
brew install tesseract tesseract-lang

# 验证
tesseract --version
```

## 环境变量

复制并编辑 `server/.env` 文件：

```dotenv
# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=9999
APP_DEBUG=false

# Database (MySQL)
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

# Main LLM (OpenAI-compatible)
OPENAI_API_KEY=your_key
OPENAI_API_BASE=https://your-openai-compatible-endpoint
OPENAI_MODEL=gpt-4o-mini

# Fast / Classifier LLM
FAST_LLM_API_KEY=your_key
FAST_LLM_MODEL=general

# Vision (GLM-4V)
GLM_API_KEY=your_key
GLM_VISION_MODEL=glm-4v-flash

# 讯飞星火图片理解
APPID=your_appid
APIKey=your_key
APISecret=your_secret
```

> `DB_PASSWORD` 必填，未配置时应用启动会失败。`APP_DEBUG=true` 会在启动时先 DROP 再 CREATE 表，仅用于开发。

## 项目结构

```
├── src/                          # Vue 3 前端
│   ├── api/                      # API 调用层
│   │   ├── auth.ts               #   认证接口（登录、注册、登出、用户信息）
│   │   └── ai.ts                 #   AI 接口（对话、画像、资源生成）
│   ├── layouts/
│   │   └── MainLayout.vue        #   沉浸式主布局（灵动岛 + 浮动 Dock）
│   ├── views/
│   │   ├── Home.vue              #   全景中心（仪表盘）
│   │   ├── Login.vue             #   登录
│   │   ├── Register.vue          #   注册
│   │   ├── Tutor.vue             #   AI 导师对话（SSE 流式）
│   │   ├── ResourceGenerator.vue #   多智能体资源生成
│   │   ├── PathPlanner.vue       #   学习路径规划
│   │   ├── Evaluation.vue        #   多维学情评估
│   │   └── digital-human/        #   数字人（预留）
│   ├── router/index.ts           # 路由配置 + 守卫
│   ├── utils/http.ts             # Axios 实例（拦截器 + token 注入）
│   └── main.ts                   # 入口
│
└── server/app/                   # FastAPI 后端
    ├── main.py                   # 应用入口，挂载各模块路由
    ├── config.py                 # 环境变量配置（typed settings）
    │
    ├── auth/                     # 认证模块
    │   ├── api.py                #   路由：注册、登录、登出、个人信息 CRUD
    │   ├── schemas.py            #   DTO：UserRegister、UserLogin、UserRead、UserUpdate
    │   ├── security.py           #   JWT 创建/吊销、bcrypt、get_current_user 依赖
    │   └── service.py            #   UserAccountStore、AuthUseCases
    │
    ├── chat/                     # 对话模块
    │   ├── api.py                #   路由：SSE 流式聊天、文件上传、会话 CRUD、历史查询
    │   ├── agent.py              #   TutorAgent（LangGraph StateGraph 多工具循环）
    │   ├── context.py            #   ContextVar 用户上下文注入
    │   ├── schemas.py            #   DTO：ChatMessageItem、UploadResponse、ResourceCard 等
    │   ├── service.py            #   ChatUseCases、TutorChatRuntime、SqlConversationStore
    │   ├── prompt.md             #   Agent 系统提示词模板
    │   ├── tools/                #   LangChain 工具（文件读取、学习资源生成）
    │   ├── skills/               #   技能包（百度搜索、PDF 解析、Word 文档）
    │   └── services/             #   辅助服务（文档分析、视觉理解、附件处理）
    │
    ├── profile/                  # 画像模块
    │   ├── api.py                #   路由：画像查询、变更历史
    │   ├── profile_agent.py      #   ProfileBuilderAgent（8 维度画像提取）
    │   ├── fact_agent.py         #   MemoryExtractionAgent（长期事实提取与去重）
    │   ├── schemas.py            #   DTO：ProfileResponse、ProfileHistoryItem
    │   └── service.py            #   ProfileService、LearnerProfileRuntime、ProfileUseCases
    │
    ├── resource/                 # 资源生成模块
    │   ├── api.py                #   路由：资源生成（SSE）、Agent 列表、资源查询
    │   ├── coordinator.py        #   CoordinatorAgent（DAG 任务规划 + 分阶段并行编排）
    │   ├── base_agent.py         #   BaseResourceAgent 抽象基类（LangGraph agent→tools→validate 循环）
    │   ├── events.py             #   AgentEventEmitter（asyncio.Queue → SSE 事件流）
    │   ├── exceptions.py         #   资源生成异常层级（ResourceAgentError 体系）
    │   ├── validation.py         #   JSON 提取、内容校验工具函数
    │   ├── schemas.py            #   DTO：LearningTask、ResourceGenerateRequest
    │   ├── service.py            #   ResourceService、ResourceGenerationRuntime、ResourceUseCases
    │   ├── agents/               #   6 个子 Agent
    │   │   ├── code/             #     代码生成（含 Shell 执行工具）
    │   │   ├── content/          #     内容写作（大纲 → 正文）
    │   │   ├── mindmap/          #     思维导图（MCP markmap → HTML）
    │   │   ├── ppt/              #     PPT 生成
    │   │   ├── quiz/             #     分层练习题生成
    │   │   └── reading/          #     推荐阅读清单
    │   ├── shared_tools/         #   共享工具（文件处理、代码运行、Shell 执行）
    │   ├── skills/               #   技能包（百度搜索）
    │   └── prompts/              #   Planner 提示词模板
    │
    ├── memory/                   # 记忆模块
    │   ├── service.py            #   MemoryService 外观层（委托给子服务）
    │   ├── short_term.py         #   短期记忆（ChatMessage CRUD、过期清理）
    │   ├── long_term.py          #   长期记忆（UserMemory 读写、去重/合并、按类型查询）
    │   ├── compression.py        #   短期→长期压缩（LLM 批量摘要）
    │   ├── session.py            #   会话管理（ChatSession CRUD + token 累计阈值触发）
    │   └── helpers.py            #   文本标准化、token 估算
    │
    ├── infra/                    # 基础设施
    │   ├── models.py             #   SQLModel 表定义（User、ChatSession、ChatMessage、UserMemory 等 7 张表）
    │   ├── database.py           #   MySQL 异步引擎（aiomysql）、init_db()、get_session()
    │   ├── llm.py                #   LLM 客户端工厂（get_llm、get_fast_llm）
    │   └── logging.py            #   日志配置（按天轮转 + 错误日志 + 控制台）
    │
    └── shared/                   # 共享工具
        ├── response.py           #   HttpResponse 统一响应 {code, message, data}
        ├── paths.py              #   全局路径常量
        ├── storage.py            #   本地文件存储（上传、下载、权限校验）
        ├── plugin_manager.py     #   PluginManager（从 SKILL.md 动态加载技能/工具）
        ├── spark_image.py        #   讯飞星火图片理解 WebSocket 客户端
        ├── sanitizers.py         #   ToolMessage 内容清理
        └── resource_cards.py     #   资源卡片构建
```

## 架构设计

### Feature Module Architecture

按业务域垂直划分模块，每个模块自包含：

```
模块/
├── api.py        # FastAPI 路由 + 依赖注入
├── service.py    # 业务逻辑 + 运行时 + 持久化
├── schemas.py    # Pydantic 请求/响应模型
└── *.py          # 模块特有文件（Agent、工具、提示词等）
```

调用链：`HTTP Request → api.py → service.py → Agent / infra / memory`

模块间通过直接导入服务单例协作，无 DI 容器。

### 多智能体系统

```
用户消息 → TutorAgent (LangGraph StateGraph)
            ├── 三层上下文：用户画像 + 长期记忆 + 短期聊天
            ├── 工具调用：文件读取、学习资源生成、百度搜索
            ├── 图片理解：讯飞星火 / GLM-4V
            └── SSE 流式输出

资源请求 → CoordinatorAgent (DAG 分阶段编排)
            ├── Phase 1: mindmap + reading (并行)
            ├── Phase 2: content + quiz + code (并行)
            ├── Phase 3: ppt
            └── 每个 Agent: BaseResourceAgent → tools → validate → retry
```

### 记忆系统

```
短期记忆 (ChatMessage)
    ↓ 达到阈值 (30条) 或 token 累计
压缩服务 (LLM 摘要)
    ↓
长期记忆 (UserMemory)
    ├── summary: 对话批量总结
    ├── fact: 用户事实（去重 + evidence_count）
    ├── preference / goal / weakness: 画像维度
    └── 过期自动忽略

会话服务 (ChatSession)
    ├── memory_token_count → 触发事实提取 (80 tokens)
    └── profile_token_count → 触发画像更新 (120 tokens)
```

### 认证流程

- 登录返回 JWT token，前端存入 `localStorage`
- `get_current_user` 依赖验证 JWT + 检查 `ActiveToken` 数据库白名单
- 登出移除 token 白名单 + 触发后台画像构建

### 前端架构

- Vue 3 Composition API（`<script setup lang="ts">`）
- Element Plus UI 组件库
- ECharts 图表（画像雷达图、学习趋势图）
- Vite 开发服务器代理 `/api` → `http://localhost:9999`
- Axios 拦截器自动注入 token，401 自动跳转登录页

## API 路由

### 用户认证 — `/api/v1/users`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/` | 注册 |
| POST | `/auth` | 登录 |
| DELETE | `/auth` | 登出（触发画像构建） |
| GET | `/me` | 获取当前用户 |
| PATCH | `/me` | 更新用户信息 |

### AI 对话 — `/api/v1/ai`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat/stream` | SSE 流式对话（支持多模态） |
| POST | `/chat/upload` | 单文件上传 |
| GET | `/chat/uploads/{owner_id}/{session_id}/{filename}` | 读取上传文件 |
| GET | `/chat/sessions` | 会话列表 |
| POST | `/chat/sessions` | 创建会话 |
| DELETE | `/chat/sessions/{session_id}` | 归档会话 |
| GET | `/chat/history` | 历史消息 |

### 用户画像 — `/api/v1/ai`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/profile` | 当前画像（8 维度） |
| GET | `/profile/history` | 画像变更历史 |

### 资源生成 — `/api/v1/ai`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/generate` | SSE 生成学习资源 |
| GET | `/agents` | 可用资源 Agent 列表 |
| GET | `/resources` | 资源历史列表 |
| GET | `/resources/{resource_id}` | 资源详情 |

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

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + TypeScript + Vite 7 |
| UI | Element Plus + ECharts |
| 后端 | FastAPI + SQLModel + aiomysql |
| AI | LangChain + LangGraph |
| 数据库 | MySQL 8+ |
| 包管理 | npm（前端）、uv（后端） |

## 常用命令

```bash
# 后端
cd server
uv sync                                    # 安装依赖
uv run fastapi dev app/main.py             # 开发服务器（热重载）
uv run python app/main.py                  # 生产服务器
uv run pytest -q                           # 运行测试

# 前端
npm run dev        # 开发服务器 http://localhost:5173
npm run build      # 生产构建（含 TypeScript 类型检查）
npm run preview    # 预览生产构建
```

## 开发约定

- 新功能放入对应业务模块（auth / chat / profile / resource / memory）
- 每个模块自包含：`api.py` + `service.py` + `schemas.py`
- 共享基础设施放 `infra/`，通用工具放 `shared/`
- 所有 API 响应使用 `HttpResponse` 统一封装 `{code, message, data}`
- 模块级单例模式，通过 `get_current_user` / `get_session` 依赖注入
- Agent 提示词模板存为 `.md` 文件放在各模块的 `prompts/` 或 `prompt` 目录下
- LLM 配置使用 OpenAI-compatible API（`OPENAI_API_BASE`）