# AI 学习平台

> 多智能体个性化学习资源平台 — 智能辅导对话、多模态资源生成、学习路径规划、学习者画像

## 项目简介

本项目是一个面向教育场景的全栈 AI 学习平台，通过多智能体协作提供个性化的学习体验。系统支持 AI 辅导对话、自动生成多模态学习资源（教程、思维导图、题目、PPT、视频等）、智能规划学习路径，并基于学习行为构建学习者画像实现因材施教。

### 核心特性

- **智能辅导对话** - 基于三层记忆架构（会话摘要、长期记忆、学习画像）的个性化对话
- **多智能体资源生成** - 一键生成教程、思维导图、题目、代码示例、PPT、讲解视频等
- **学习路径规划** - 自动规划课程级学习路径，节点内形成学习闭环
- **学习者画像** - 基于对话、学习事件、题目表现沉淀多维画像
- **题库与错题本** - 编程题与客观题管理，自动归集错题
- **数字人播报** - WebSocket 桥接讯飞数字人，ASR 实时识别 + 数字人互动

### 技术栈

**前端**
- Vue 3.5 + TypeScript 5.9
- Vue Router 4.6 + Vite 7.2
- Tailwind CSS 4.3 + shadcn-vue
- ECharts 6.0 + markmap（可视化）
- Monaco Editor（代码编辑）
- Axios + SSE（API 通信）

**后端**
- FastAPI + SQLModel + SQLAlchemy Async
- LangGraph + LangChain（多智能体编排）
- PostgreSQL + asyncpg
- OpenAI 兼容 API（支持 GPT-4、智谱 AI 等）
- ChromaDB + BM25 + bge-m3（向量检索）
- Remotion 4.0 + HyperFrames（视频渲染）
- Edge-TTS / 讯飞 TTS（语音合成）

---

## 目录结构

```
software/
├── src/                      # 前端源码
│   ├── app/                  # 应用入口、布局、路由
│   ├── features/             # 功能模块（按业务域划分）
│   │   ├── auth/            # 认证（登录/注册）
│   │   ├── chat/            # 智能辅导对话
│   │   ├── dashboard/       # 首页仪表盘
│   │   ├── resource/        # 独立资源生成
│   │   ├── learning-path/   # 学习路径规划
│   │   ├── profile/         # 学习者画像
│   │   ├── question-bank/   # 题库
│   │   ├── evaluation/      # 学习评估
│   │   └── algorithm-visualization/  # 算法可视化
│   └── shared/               # 共享模块（API、UI 组件、工具函数）
│
├── server/                   # 后端源码
│   ├── app/                  # 应用代码
│   │   ├── auth/            # 用户认证
│   │   ├── chat/            # 辅导对话（SSE + 三层记忆）
│   │   ├── resource/        # 独立资源生成（多智能体工作流）
│   │   ├── path/            # 学习路径规划
│   │   ├── profile/         # 学习者画像
│   │   ├── evaluation/      # 学习事件与评估
│   │   ├── dashboard/       # 首页聚合
│   │   ├── quiz/            # 题库与错题本
│   │   ├── avatar/          # 数字人桥接
│   │   ├── rag/             # 向量检索知识库
│   │   ├── shared/          # 跨领域共享能力
│   │   ├── infra/           # 基础设施（DB、配置、日志）
│   │   ├── main.py          # 应用入口
│   │   └── routes.py        # 路由注册
│   ├── tests/                # pytest 测试
│   ├── config.yaml           # 运行时配置
│   ├── init_schema.sql       # 数据库初始化
│   └── pyproject.toml        # Python 依赖
│
├── vite.config.ts            # Vite 配置（代理 /api → :9999）
└── package.json              # 前端依赖
```

---

## 环境要求

### 必需环境

| 依赖 | 版本要求 | 用途 |
|------|---------|------|
| Python | ≥ 3.13 | 后端运行时 |
| uv | 最新版 | Python 包管理器 |
| Node.js | ≥ 18（推荐 20+） | 前端构建 |
| npm | 与 Node 同版本 | 前端包管理 |
| PostgreSQL | ≥ 12 | 主数据库 |
| FFmpeg + FFprobe | ≥ 4.0 | 视频渲染 |

### 可选环境

| 依赖 | 用途 | 配置位置 |
|------|------|----------|
| Ollama + bge-m3 | 向量检索知识库 | `config.yaml → knowledge` |
| NVIDIA GPU + NVENC | GPU 加速视频编码 | 自动检测 |

---

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd software
```

### 2. 安装前端依赖

```bash
npm install
```

### 3. 安装后端依赖

```bash
cd server
uv sync
```

### 4. 初始化数据库

```bash
# 启动 PostgreSQL（根据系统选择命令）
# macOS: brew services start postgresql@14
# Ubuntu: sudo systemctl start postgresql

# 创建数据库
createdb agent
# 或使用 psql
psql -U postgres -c "CREATE DATABASE agent;"

# 导入数据库 Schema
psql -d agent -f server/init_schema.sql
```

### 5. 配置应用

编辑 `server/config.yaml`，填写必要配置：

```yaml
# 数据库连接
database:
  url: "postgresql+asyncpg://用户名:密码@主机:5432/agent"

# JWT 认证（必须 ≥ 32 字符）
jwt:
  secret_key: "your-secret-key-at-least-32-characters-long"

# LLM 模型配置
models:
  base_url: "https://api.openai.com/v1"  # 或其他 OpenAI 兼容 API
  api_key: "sk-xxx"
  model_name: "gpt-4o"
```

### 6. 启动服务

**启动后端**（在 `server/` 目录）

```bash
uv run fastapi dev app/main.py --port 9999
# 或生产模式
uv run python app/main.py
```

访问 API 文档：http://localhost:9999/docs

**启动前端**（在项目根目录）

```bash
npm run dev
```

访问前端：http://localhost:5173

---

## 核心业务流程

### 三条独立业务链路

系统设计遵循**业务边界隔离**原则，三条核心链路各自独立：

#### 1. 智能辅导对话（chat 域）

```
用户提问 → 组装多层上下文（历史/摘要/长期记忆/画像/检索源）
        → TutorAgent（LangGraph：classify → 路由 → answer/search/attachment）
        → SSE 流式输出 → 持久化 → 触发压缩与长期记忆抽取
```

**核心能力**：
- 流式对话（SSE）
- 文件/图片辅助分析
- 会话历史管理
- 学习画像驱动的上下文构建
- 联网搜索与知识库检索

#### 2. 独立资源生成（resource 域）

用户直接请求"生成教程/导图/PPT"，不依赖学习路径上下文：

```
POST /api/v1/ai/resources → 持久化任务 → 后台 LangGraph 父工作流
                          → Planning → 并行 Worker → Review
                          → 持久化 GeneratedResourceItem → SSE 推送进度
```

**支持资源类型**：教程、思维导图、题目、代码示例、阅读材料、PPT、讲解视频、动画讲解

**数据存储**：`generated_resources` / `generated_resource_items`

**前端页面**：`/resource-generator`、`/ai/resources/history`、`/resource-detail/:id`

#### 3. 学习路径规划（path 域）

用户输入学习目标，系统自动规划学习路径：

```
POST /api/v1/ai/path-plan → 后台生成阶段与节点
                          → GET /nodes/{id}/workspace 驱动节点工作空间
                          → 节点学习（LangGraph learn workflow）
                          → 节点资源存入 PathNodeResource
                          → 学习事件反馈画像与评估
```

**核心特性**：
- 自动生成学习路径（阶段 + 节点）
- 节点首次进入时生成教程
- 节点内固定 5 道选择题
- 错题知识点专项巩固

**数据存储**：`learning_paths`、`path_nodes`、`path_node_tutorials`、`path_node_questions`、`path_node_resources`

**前端页面**：`/path-planner`、`/path-planner/overview/:id`、`/path-planner/node/:nodeId`

> **重要设计边界**：独立资源（resource 域）与路径节点资源（path 域）共用 Agent 实现，但**持久化模型、API 与前端页面各自独立**，不可混用。

---

## 前端页面路由

| 路由 | 说明 | 认证 |
|------|------|------|
| `/login` | 登录页面 | 否 |
| `/register` | 注册页面 | 否 |
| `/dashboard` | 首页仪表盘 | 是 |
| `/tutor` | 智能辅导对话 | 是 |
| `/resource-generator` | 独立资源生成 | 是 |
| `/ai/resources/history` | 独立资源历史 | 是 |
| `/resource-detail/:id` | 独立资源详情 | 是 |
| `/path-planner` | 学习路径创建 | 是 |
| `/path-planner/overview/:id?` | 路径总览 | 是 |
| `/path-planner/node/:nodeId` | 节点学习页 | 是 |
| `/path-planner/history` | 路径历史 | 是 |
| `/question-bank` | 题库 | 是 |
| `/profile` | 学习者画像 | 是 |
| `/assessment` | 学习评估 | 是 |
| `/algorithm-visualizer` | 算法可视化 | 是 |

---

## 后端 API 路由

所有 API 响应使用统一信封格式：`{code, message, data}`

| 前缀 | 领域 | 主要能力 |
|------|------|----------|
| `/api/v1/users` | auth | 注册 / 登录 / 登出 / 当前用户 |
| `/api/v1/ai/chat` | chat | SSE 流式对话、附件上传、会话管理 |
| `/api/v1/ai/resources` | resource | 独立资源生成、状态查询、详情、历史、SSE |
| `/api/v1/ai/path-plan` | path | 路径生成、节点工作空间、教程/测验/资源 |
| `/api/v1/ai/dashboard` | dashboard | 首页聚合与推荐 |
| `/api/v1/ai/evaluation` | evaluation | 学习事件、评估汇总 |
| `/api/v1/ai/quiz-bank` | quiz | 题库管理 |
| `/api/v1/ai/wrong-questions` | quiz | 错题本 |
| `/api/v1/ai/avatar` | avatar | 数字人 REST 接口 |
| `/ws/avatar` | websocket | 数字人 WebSocket（`?token=JWT`） |

> 路由的权威来源是 `server/app/routes.py` 与各领域 `api.py`；完整端点签名以 `/docs` 的 OpenAPI 文档为准。

---

## 记忆与画像架构

个性化能力建立在三层记忆架构之上：

| 层级 | 存储表 | 触发条件 | 作用 |
|------|--------|----------|------|
| 会话压缩 | `chat_session_summary_blocks` | 对话 token/消息数超阈值 | 近期对话 → 压缩摘要块 |
| 长期记忆 | `chat_long_term_memories` | 对话结束 | 抽取可复用的学习者事实 |
| 学习画像 | `global_profiles` / `course_profiles` | 记忆 + 学习事件 | 多维度画像（知识掌握、薄弱点、学习偏好） |

> 修改个性化行为时，应**联合检查** `chat`、`profile`、`evaluation` 三个领域。

---

## 向量检索知识库（RAG）

采用 **ChromaDB（向量）+ BM25（关键词）混合检索 + RRF 融合**，嵌入模型通过 OpenAI 兼容 API 接入（默认 bge-m3，1024 维）。

### 目录结构

```
server/app/rag/
├── data/
│   ├── source/              # 源文档（按课程编号目录存放）
│   └── index/               # 构建产物（ChromaDB + BM25 + manifest）
├── load.py                  # 文档加载
├── retriever.py             # 混合检索 + RRF 融合
└── indexing/build.py        # 离线索引构建器
```

### 启用知识库

1. **安装 Ollama 并下载 embedding 模型**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull bge-m3
ollama serve  # 启动服务
```

2. **配置 config.yaml**

```yaml
knowledge:
  enabled: true
  embed_model: "bge-m3:latest"
  embed_base_url: "http://127.0.0.1:11434/v1"
  top_k: 4
```

3. **构建索引**

```bash
cd server
uv run python -m app.rag.indexing.build
```

---

## 视频渲染系统

后端支持两种独立的视频渲染管线，均支持 GPU 加速（NVIDIA NVENC）：

### Remotion 讲解视频

- **入口**：`app/resource/agents/video.py` → `app/shared/video/agent.py`
- **流程**：素材提取 → 场景规划 → 脚本撰写 → TTS 合成 → Remotion 渲染 MP4
- **GPU 路径**：Chromium GL 后端 `angle` + FFmpeg NVENC 硬件编码
- **音频架构**：采用 manifest 合约避免竞态条件

### HyperFrames 动画讲解

- **入口**：`app/resource/agents/cartoon.py` → `app/shared/cartoon/pipeline.py`
- **流程**：脚本生成 → 场景绘制 → HyperFrames 渲染 MP4
- **GPU 路径**：`--browser-gpu` + `--gpu`（NVENC）
- **环境检测**：自动检测 CPU 核心数、内存、GPU；低内存（≤8GB）自动降级

### TTS 语音合成

| 后端 | 适用场景 | 需要密钥 |
|------|----------|----------|
| 讯飞星火 TTS | 高质量配音 | 是（`config.yaml → spark_tts`） |
| Microsoft Edge-TTS | 免费/测试/动画 | 否（需联网） |

---

## 开发指南

### 前端开发

```bash
npm run dev      # 启动开发服务器
npm run build    # 类型检查 + 构建
npm run preview  # 预览构建产物
npm run test     # 运行测试（vitest）
```

**路径别名**（`vite.config.ts`）：
- `@` → `./src`
- `@ppt-manifest` → `./server/app/resource/templates/ppt_manifest.json`

**Vite 代理**：
- `/api` → `http://127.0.0.1:9999`
- `/ws` → `ws://127.0.0.1:9999`
- `/static` → `http://127.0.0.1:9999`

### 后端开发

```bash
cd server

# 安装依赖
uv sync

# 开发服务器（热重载）
uv run fastapi dev app/main.py --port 9999

# 生产模式
uv run python app/main.py

# 运行测试
uv run pytest                       # 全部测试
uv run pytest tests/chat -q         # 指定模块
uv run pytest -x                    # 首个失败即停止
```

**数据库会话约定**：
- `get_session()` - FastAPI 依赖注入，调用方手动提交
- `session_scope()` - 后台任务，自动提交/回滚

**Schema 同步**：结构变更需**同时**更新 `init_schema.sql` 与 `app/infra/models.py`；新增表必须加入 `REGISTERED_MODELS`。

---

## 配置说明

所有运行时配置集中在 `server/config.yaml`，不使用 `.env`。

### 核心配置组

| 配置组 | 必填 | 说明 |
|--------|------|------|
| `database` | **是** | PostgreSQL 连接 URL |
| `jwt` | **是** | `secret_key`（≥ 32 字符） |
| `models` | **是** | LLM 的 `base_url` / `api_key` / `model_name` |
| `models.vision` | 否 | 图片理解模型 |
| `spark_tts` | 否 | 讯飞星火 TTS |
| `avatar` | 否 | 讯飞数字人 + ASR |
| `search` | 否 | Tavily / 讯飞搜索密钥 |
| `knowledge` | 否 | Ollama + bge-m3 向量检索 |
| `video` | 否 | 渲染超时、并发数、GL 后端 |

### 最小可启动配置

```yaml
database:
  url: "postgresql+asyncpg://user:password@127.0.0.1:5432/agent"

jwt:
  secret_key: "至少-32-个字符的随机字符串"

models:
  base_url: "https://api.openai.com/v1"
  api_key: "sk-xxx"
  model_name: "gpt-4o"
```

---

## 故障排查

| 问题 | 排查方向 |
|------|----------|
| 启动数据库错误 | 检查 `config.yaml → database.url`；确认 PostgreSQL 运行中；确认已执行 `init_schema.sql` |
| 首页 500 | 检查 dashboard 聚合查询是否访问不存在的表/字段 |
| 路径规划异常 | 检查 `learning_paths` 子表结构；确认节点资源未误走独立资源域 |
| 前端 API 500 | 确认 Vite 代理端口（9999）与后端一致 |
| 视频渲染失败 | 确认 FFmpeg 已安装；Node.js ≥ 22 |
| GPU 未生效 | `ffmpeg -encoders | grep h264_nvenc` 确认 NVENC |
| TTS 无声 | 检查 `spark_tts` 配置；Edge-TTS 需联网 |
| 向量检索失效 | 确认 Ollama 服务运行中；`knowledge.enabled: true` |
| 数字人连接失败 | 检查 `avatar.*` 配置完整；JWT 有效 |

---

## 端口配置

| 服务 | 端口 |
|------|------|
| Frontend (Vite) | 5173 |
| Backend (FastAPI) | 9999 |
| API Docs (Swagger) | 9999/docs |
| Ollama (可选) | 11434 |
| PostgreSQL | 5432 |

---

## 推荐阅读顺序

1. 本文件 `README.md`
2. [server/README.md](server/README.md) - 后端详细说明
3. [src/app/router/routes.ts](src/app/router/routes.ts) - 前端路由
4. [server/app/main.py](server/app/main.py) - 后端入口
5. [server/app/routes.py](server/app/routes.py) - 后端路由挂载
6. [server/init_schema.sql](server/init_schema.sql) - 数据库结构
7. [server/config.yaml](server/config.yaml) - 配置示例

---

## License

MIT
