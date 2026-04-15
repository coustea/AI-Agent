# 多智能体个性化学习资源平台

全栈项目：Vue 3 + TypeScript 前端 + FastAPI + SQLModel 后端。

基于 LangChain 构建多智能体系统，提供个性化学习辅导、用户画像构建、多模态资源生成等能力。

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

## 系统依赖

### OCR 图片识别（必需）

```bash
# Ubuntu / Debian
sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng

# macOS
brew install tesseract tesseract-lang

# 验证安装
tesseract --version
```

### Node.js（思维导图 MCP 服务需要）

```bash
nvm install --lts
node --version   # >= 18
```

## 环境变量

复制 `server/.env.example` 为 `server/.env`，填写以下配置：

| 变量 | 说明 | 示例 |
|------|------|------|
| `OPENAI_API_BASE` | LLM API 地址 | `https://spark-api-open.xf-yun.com/v1/` |
| `OPENAI_API_KEY` | LLM API 密钥 | `APIPassword` |
| `OPENAI_MODEL` | 主模型 | `generalv3.5` |
| `FAST_LLM_API_KEY` | 轻量模型密钥 | `APIPassword` |
| `FAST_LLM_MODEL` | 轻量模型名称 | `general` |
| `DB_HOST` / `DB_PORT` | MySQL 连接 | `localhost` / `3306` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | 随机字符串 |
| `NODE_PATH` | Node.js 可执行文件路径 | `/usr/bin/node` |

## 项目结构

```
server/app/
├── main.py              # FastAPI 入口，挂载各模块路由
├── config.py            # 环境变量配置
│
├── auth/                # 认证模块
│   ├── api.py           #   路由：注册、登录、登出、个人信息
│   ├── schemas.py       #   DTO：UserRegister、UserLogin、UserRead
│   ├── security.py      #   JWT + bcrypt、get_current_user 依赖
│   └── service.py       #   UserAccountStore、AuthUseCases
│
├── chat/                # 对话模块
│   ├── api.py           #   路由：SSE 流式聊天、文件上传、会话管理
│   ├── agent.py         #   TutorAgent（LangGraph StateGraph）
│   ├── context.py       #   ContextVar 用户上下文注入
│   ├── schemas.py       #   DTO：ChatMessageItem、UploadResponse
│   ├── service.py       #   ChatUseCases、TutorChatRuntime、SqlConversationStore
│   ├── prompt.md        #   Agent 系统提示词
│   ├── tools/           #   LangChain 工具（文件读取、资源生成）
│   ├── skills/          #   技能包（百度搜索、PDF、Word）
│   └── services/        #   辅助服务（文档分析、视觉、附件处理）
│
├── profile/             # 画像模块
│   ├── api.py           #   路由：画像查询、变更历史
│   ├── profile_agent.py #   ProfileBuilderAgent（8 维度画像提取）
│   ├── fact_agent.py    #   MemoryExtractionAgent（长期事实提取）
│   ├── schemas.py       #   DTO：ProfileResponse、ProfileHistoryItem
│   └── service.py       #   ProfileService、LearnerProfileRuntime、ProfileUseCases
│
├── resource/            # 资源生成模块
│   ├── api.py           #   路由：资源生成（SSE）、Agent 列表、资源查询
│   ├── coordinator.py   #   CoordinatorAgent（DAG 任务规划 + 分阶段编排）
│   ├── base_agent.py    #   BaseResourceAgent 抽象基类（LangGraph 循环）
│   ├── events.py        #   AgentEventEmitter（SSE 事件推送）
│   ├── exceptions.py    #   资源生成异常层级
│   ├── validation.py    #   JSON 提取、校验工具
│   ├── schemas.py       #   DTO：ResourceGenerateRequest
│   ├── service.py       #   ResourceService、ResourceGenerationRuntime
│   ├── agents/          #   6 个子 Agent（code、content、mindmap、ppt、quiz、reading）
│   ├── shared_tools/    #   共享工具（文件处理、代码运行、Shell 执行）
│   ├── skills/          #   技能包（百度搜索）
│   └── prompts/         #   Planner 提示词
│
├── memory/              # 记忆模块
│   ├── service.py       #   MemoryService 外观层（兼容旧接口）
│   ├── short_term.py    #   短期记忆（ChatMessage CRUD）
│   ├── long_term.py     #   长期记忆（UserMemory 读写、去重/合并）
│   ├── compression.py   #   短期→长期压缩（LLM 摘要）
│   ├── session.py       #   会话管理（ChatSession CRUD + token 累计）
│   └── helpers.py       #   文本标准化、token 估算
│
├── infra/               # 基础设施
│   ├── models.py        #   全部 SQLModel 表定义（User、ChatSession、UserMemory 等）
│   ├── database.py      #   MySQL 引擎、init_db()、get_session()
│   ├── llm.py           #   LLM 客户端工厂（get_llm、get_fast_llm）
│   └── logging.py       #   日志配置（文件轮转 + 控制台输出）
│
└── shared/              # 共享工具
    ├── response.py      #   HttpResponse 统一响应封装
    ├── paths.py         #   全局路径常量
    ├── storage.py       #   本地文件存储（上传、下载）
    ├── plugin_manager.py#   PluginManager（技能/工具动态加载）
    ├── spark_image.py   #   讯飞星火图片理解服务
    ├── sanitizers.py    #   ToolMessage 内容清理
    └── resource_cards.py#   资源卡片构建
```

## 架构设计

采用 **Feature Module Architecture**（功能模块架构），按业务域垂直划分模块：

- 每个模块自包含：`api.py`（路由）+ `service.py`（业务逻辑）+ `schemas.py`（数据模型）+ 模块特有文件
- 模块间通过直接导入服务单例协作，无 DI 容器
- `infra/` 和 `shared/` 提供跨模块基础设施

### 多智能体系统

```
用户请求 → TutorAgent (LangGraph)
              ├── 短期/长期记忆上下文
              ├── 用户画像注入
              ├── 工具调用（文件读取、资源生成）
              └── SSE 流式响应

资源生成 → CoordinatorAgent (DAG 编排)
              ├── Phase 1: mindmap + reading (并行)
              ├── Phase 2: content + quiz + code (并行)
              └── Phase 3: ppt
```

### API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/users` | 注册 |
| POST | `/api/v1/users/auth` | 登录 |
| DELETE | `/api/v1/users/auth` | 登出 |
| GET | `/api/v1/users/me` | 获取当前用户 |
| PATCH | `/api/v1/users/me` | 更新用户信息 |
| POST | `/api/v1/ai/chat/stream` | SSE 流式对话 |
| GET | `/api/v1/ai/chat/history` | 聊天记录 |
| GET | `/api/v1/ai/chat/sessions` | 会话列表 |
| POST | `/api/v1/ai/generate` | 资源生成（SSE） |
| GET | `/api/v1/ai/agents` | Agent 列表 |
| GET | `/api/v1/ai/profile` | 用户画像 |
| GET | `/api/v1/ai/profile/history` | 画像变更历史 |

## 常用命令

```bash
# 后端
cd server
uv sync                                    # 安装依赖
uv run fastapi dev app/main.py             # 开发服务器（热重载）
uv run python app/main.py                  # 生产服务器

# 前端
npm run dev        # 开发服务器
npm run build      # 生产构建
```
