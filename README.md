# AI Learning Platform

一个面向学习场景的全栈 AI 系统，包含：

- Vue 3 + TypeScript 前端
- FastAPI + SQLModel 后端
- 多智能体学习资源生成
- 学习路径规划与节点学习
- 智能辅导、用户画像、学习评估、题库

两类业务能力严格分离：

- **资源生成**（`resource` 域）：独立的多智能体资源生产链路
- **路径规划**（`path` 域）：先生成学习路径，再围绕路径节点按需生成教程、题目和辅助资源

## 目录结构

```text
software/
├── src/                 # 前端源码
│   ├── app/             # 路由、布局、入口
│   ├── features/        # 功能模块（auth, chat, dashboard, learning, profile, resource）
│   └── shared/          # 共享工具（API 客户端、认证、UI 组件、类型）
├── public/              # 前端静态资源
├── server/              # FastAPI 后端
│   ├── app/             # 应用源码
│   ├── tests/           # pytest 测试
│   ├── config.yaml      # 运行配置
│   └── init_schema.sql  # 数据库初始化脚本
├── video-render/        # Remotion 视频渲染项目
└── vite.config.ts       # Vite 配置（代理 /api → :9999）
```

## 核心能力

### 1. 智能辅导

- 流式对话（SSE）
- 文件/图片辅助分析
- 会话历史管理
- 学习画像驱动的上下文构建

### 2. 多智能体资源生成

- 多智能体并行生成（Planning → Worker → Review）
- 单智能体直接生成（路径节点内按需）
- 支持内容、思维导图、题目、代码示例、阅读材料、PPT、视频
- 任务状态查询与 SSE 事件流

### 3. 学习路径规划

- 用户输入学习目标生成路径（阶段 + 节点）
- 节点首次进入时生成教程
- 节点内固定 5 道选择题
- 错题知识点专项巩固，再强化教程
- 路径资源与独立资源完全分离

### 4. 用户画像与学习评估

- 基于聊天、学习事件、题目表现沉淀画像
- 聚合学习事件、学习时长、薄弱点
- 为首页和路径评估提供动态推荐信号

### 5. 题库与练习

- 通用题库与错题本
- 编程题与选择题导入
- 路径节点内 AI 在线生成题目

## 环境要求

### 必需环境

| 工具 | 版本要求 | 用途 |
|------|---------|------|
| **Python** | ≥ 3.13 | 后端运行环境 |
| **Node.js** | ≥ 18 (推荐 20+) | 前端构建、Remotion/HyperFrames 视频渲染 |
| **PostgreSQL** | ≥ 12 | 主数据库 |
| **FFmpeg** | 任意版本 | 视频渲染音视频处理 |
| **FFprobe** | 与 FFmpeg 同版本 | 音视频流探测 |
| **uv** | 最新版 | Python 包管理器 |
| **npm** | 与 Node.js 同版本 | 前端包管理 |

### 可选环境（用于特定功能）

| 工具 | 用途 | 配置位置 |
|------|------|----------|
| **Ollama + bge-m3** | 向量检索知识库 | `config.yaml` → `knowledge` |
| **NVIDIA GPU + NVENC** | GPU 加速视频编码（仅 Linux） | 自动检测 |

## 快速开始

### 1. 安装系统依赖

#### macOS

```bash
# 安装 Homebrew 包管理器（如未安装）
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装必需工具
brew install python@3.13 node@20 postgresql ffmpeg uv

# 验证安装
python3 --version    # 应 ≥ 3.13.0
node --version       # 应 ≥ 18.0.0
ffmpeg -version      # 应显示版本和编码器信息
ffprobe -version     # 应显示版本信息
psql --version       # 应 ≥ 12.0
uv --version         # 应显示版本信息
```

#### Ubuntu/Debian

```bash
# 安装必需工具
sudo apt update
sudo apt install -y python3.13 python3-pip nodejs npm postgresql ffmpeg

# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 验证安装
python3 --version
node --version
ffmpeg -version
ffprobe -version
psql --version
uv --version

# 如有 NVIDIA GPU，验证 NVENC 支持（可选）
ffmpeg -encoders | grep nvenc  # 应显示 h264_nvenc, hevc_nvenc
```

#### Windows

```powershell
# 使用 winget 安装（Windows 10/11）
winget install Python.Python.3.13
winget install OpenJS.NodeJS.LTS
winget install PostgreSQL.PostgreSQL
winget install Gyan.FFmpeg

# 手动安装 uv
# 从 https://docs.astral.sh/uv/ 下载安装脚本

# 验证安装
python --version
node --version
ffmpeg -version
ffprobe -version
psql --version
uv --version
```

### 2. 安装 Python 依赖

```bash
cd server
uv sync
```

这将自动安装 `server/pyproject.toml` 中定义的所有依赖，包括：

**核心框架**：
- `fastapi[standard]` - Web 框架
- `sqlmodel` - ORM
- `asyncpg` - PostgreSQL 异步驱动
- `langchain`, `langgraph` - 多智能体编排

**视频与 TTS**：
- `edge-tts>=7.2.8` - Microsoft Edge TTS（免费）
- `xfyunsdkspeech>=0.0.4` - 讯飞语音 SDK
- `mutagen>=1.47.0` - 音频元数据处理
- `playwright>=1.59.0` - 浏览器自动化（用于渲染）

**向量检索**：
- `chromadb>=0.6.3` - 向量数据库
- `langchain-chroma>=0.2.2` - LangChain ChromaDB 集成
- `langchain-ollama>=1.1.0` - Ollama embedding 集成
- `faiss-cpu>=1.13.2` - FAISS 向量检索

**文档处理**：
- `pymupdf>=1.27.2.2` - PDF 处理
- `python-docx>=1.2.0` - Word 文档
- `python-pptx>=1.0.2` - PowerPoint
- `openpyxl>=3.1.5` - Excel
- `beautifulsoup4>=4.14.3` - HTML 解析

### 3. 安装前端依赖

```bash
cd ..  # 回到项目根目录
npm install
```

这将安装 `package.json` 中定义的所有依赖，包括：

**核心框架**：
- `vue@3.5.24` - Vue 3
- `vue-router@4.6.4` - 路由
- `axios@1.14.0` - HTTP 客户端

**UI 组件**：
- `radix-vue@1.9.17`, `reka-ui@2.10.1` - UI 组件库
- `tailwindcss@4.3.1` - CSS 框架

**可视化与渲染**：
- `echarts@6.0.0`, `vue-echarts@8.0.1` - 图表
- `markmap-lib@0.18.12`, `markmap-view@0.18.12` - 思维导图
- `reveal.js@5.1.0` - 幻灯片演示
- `mp4-muxer@5.2.2` - 浏览器端 MP4 封装
- `pptxgenjs@4.0.1` - PowerPoint 生成
- `shiki@4.3.0` - 代码高亮

**Markdown 与数学**：
- `remark-parse@11.0.0`, `remark-rehype@11.1.2` - Markdown 处理
- `rehype-katex@7.0.1`, `katex@0.17.0` - LaTeX 渲染

### 4. 初始化 Remotion 视频渲染项目

```bash
cd video-render
npm install
cd ..
```

这将安装 Remotion 4.0.478 及相关依赖：
- `remotion@4.0.478` - 核心框架
- `@remotion/cli@4.0.478` - CLI 工具
- `@remotion/renderer@4.0.478` - 渲染引擎
- `@remotion/bundler@4.0.478` - 打包工具

### 5. 配置数据库

```bash
# macOS (Homebrew)
brew services start postgresql@14

# Ubuntu/Debian
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库
createdb agent

# 或使用 psql
psql -U postgres -c "CREATE DATABASE agent;"

# 初始化数据库表结构
psql -d agent -f server/init_schema.sql
```

### 6. 配置应用

编辑 `server/config.yaml`，配置以下必需项：

```yaml
# 数据库连接
database:
  url: "postgresql+asyncpg://用户名:密码@主机:5432/agent"

# JWT 认证
jwt:
  secret_key: "your-secret-key-min-32-characters"  # 必须至少 32 字符

# LLM 模型配置（必需）
models:
  base_url: "https://api.openai.com/v1"  # 或其他 OpenAI 兼容 API
  api_key: "sk-xxx"                       # API 密钥
  model_name: "gpt-4o"                    # 模型名称
```

**可选配置**：

```yaml
# 视觉模型（可选，用于图片理解）
models:
  vision:
    base_url: "https://open.bigmodel.cn/api/paas/v4/"
    api_key: "your-zhipu-api-key"
    model_name: "glm-4v-flash"

# 讯飞 TTS（可选，如不配置则使用免费的 Edge-TTS）
spark_tts:
  app_id: "your-app-id"
  api_key: "your-api-key"
  api_secret: "your-api-secret"

# 讯飞数字人（可选）
avatar:
  app_id: "your-app-id"
  api_key: "your-api-key"
  api_secret: "your-api-secret"
  url: "wss://avatar.cn-huadong-1.xf-yun.com/v1/interact"

# 搜索服务（可选）
search:
  tavily_key: "tvly-xxx"        # Tavily API Key
  spark_key: "xxx:xxx"          # 讯飞搜索密钥

# 向量检索知识库（可选）
knowledge:
  enabled: true
  collection: "langchain"
  embed_model: "bge-m3:latest"
  ollama_base_url: "http://127.0.0.1:11434"
```

### 7. 启动应用

#### 启动后端

```bash
cd server
uv run fastapi dev app/main.py --port 9999
```

访问 API 文档：http://localhost:9999/docs

#### 启动前端

```bash
# 在项目根目录
npm run dev
```

访问前端：http://localhost:5173

## 视频渲染模块

项目包含两条独立的视频渲染管线，均需要 FFmpeg 支持。

### 1. Remotion 讲解视频

**用途**：专业教学视频，包含场景切换、字幕、配音

**入口文件**：
- `server/app/resource/agents/video.py`
- `server/app/shared/video/agent.py`

**渲染器**：
- `server/app/shared/video/renderer.py`
- `video-render/` (Remotion 项目)

**工作流程**：
1. `VideoMaterialAgent` 提取教学材料要点
2. `VideoDirectorAgent` 规划场景节奏
3. `SceneWriterAgent` 撰写脚本与视觉 cue
4. `VideoTtsService` 生成配音 MP3（讯飞 TTS 或 Edge-TTS）
5. `RemotionVideoRenderer` 调用 `npx tsx scripts/render.ts` 渲染 MP4

**配置项** (`config.yaml`):
```yaml
video:
  render_timeout_seconds: 900  # 单视频最大渲染时长
  concurrency: 4                # Remotion 并发
  chromium_gl: angle            # Chromium GL 后端 (angle/swiftshader/egl)
```

**验证 FFmpeg 安装**：
```bash
ffmpeg -version      # 需能看到 libx264、aac 编码器
ffprobe -version     # 用于探测音视频流信息
```

### 2. HyperFrames 动画讲解

**用途**：手绘风格动画讲解视频

**入口文件**：
- `server/app/resource/agents/cartoon.py`
- `server/app/shared/cartoon/pipeline.py`

**渲染器**：
- `server/app/shared/cartoon/renderer.py`
- 命令：`npx --no-install hyperframes render`

**自动环境检测**：
- 物理核心数（macOS: `sysctl hw.physicalcpu`，Linux: CPU topology）
- 可用内存（macOS: `vm_stat`，Linux: `/proc/meminfo`）
- NVIDIA GPU（Linux: `nvidia-smi` + `h264_nvenc` 编码器）
- 低内存模式（≤8GB）自动降级为单 worker、CPU 渲染

**GPU 加速条件**（仅 Linux）：
1. `ffmpeg -encoders` 输出包含 `h264_nvenc`
2. `nvidia-smi` 查询到 GPU 设备
3. 可用内存 > 3GB

**渲染命令示例**：
```bash
npx --no-install hyperframes render . \
  --output video.mp4 \
  --fps 30 \
  --quality high \
  --workers 4 \
  --browser-gpu \
  --gpu
```

## TTS 配音服务

视频渲染管线支持两种 TTS 后端：

### Microsoft Edge TTS（默认，免费）

**特点**：
- 无需密钥配置
- Python 包 `edge-tts>=7.2.8` 已在 `pyproject.toml` 中声明
- 支持多种中文配音：`zh-CN-XiaoxiaoNeural`（晓晓）、`zh-CN-YunxiNeural`（云希）等

**使用场景**：讲解视频、动画视频、离线/测试环境

### 讯飞星火 TTS（可选）

**配置** (`config.yaml`):
```yaml
spark_tts:
  app_id: "your-app-id"
  api_key: "your-api-key"
  api_secret: "your-api-secret"
```

**使用场景**：需要高质量配音的专业教学视频

**切换逻辑**：如果 `spark_tts.app_id` 配置存在且非空，自动使用讯飞 TTS；否则使用 Edge-TTS。

## 向量检索知识库（可选）

用于从知识库检索相关内容辅助对话。

### 安装 Ollama 和 Embedding 模型

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# 启动 Ollama 服务
ollama serve

# 拉取 embedding 模型
ollama pull bge-m3:latest

# 验证服务
curl http://127.0.0.1:11434/api/tags  # 应返回模型列表
```

### 配置知识库

编辑 `server/config.yaml`：
```yaml
knowledge:
  enabled: true                    # 启用知识库
  collection: "langchain"          # ChromaDB 集合名称
  embed_model: "bge-m3:latest"     # Embedding 模型
  ollama_base_url: "http://127.0.0.1:11434"  # Ollama 服务地址
  top_k: 4                         # 检索返回文档数
```

## 数字人服务（可选）

用于讯飞数字人 WebSocket 桥接。

### 配置讯飞数字人

编辑 `server/config.yaml`：
```yaml
avatar:
  app_id: "your-app-id"
  api_key: "your-api-key"
  api_secret: "your-api-secret"
  url: "wss://avatar.cn-huadong-1.xf-yun.com/v1/interact"
  anchor_id: "111204004"           # 数字人形象 ID
  vcn: "x5_lingxiaoyue_flow"       # 虚拟通道号
```

### WebSocket 连接

前端通过以下地址连接：
```
ws://host:9999/ws/avatar?token=JWT_TOKEN
```

## API 路由

| 前缀 | 模块 | 主要端点 |
|------|------|----------|
| `/api/v1/users` | auth | 注册, 登录, 登出, 用户信息 |
| `/api/v1/ai/chat` | chat | SSE 流式对话, 附件上传, 会话管理 |
| `/api/v1/ai/resource` | resource | 资源生成（含 video、cartoon 智能体），状态查询，事件流 |
| `/api/v1/ai/path` | path | 路径规划, 节点工作空间, 教程/题目生成 |
| `/api/v1/ai/evaluation` | evaluation | 学习事件, 评估 |
| `/api/v1/ai/dashboard` | dashboard | 首页聚合数据 |
| `/api/v1/ai/quiz-bank` | quiz | 题库管理 |
| `/api/v1/ai/wrong-questions` | quiz | 错题本 |
| `/api/v1/ai/avatar` | avatar | 数字人 REST 接口 |
| `/ws/avatar` | websocket | 数字人 WebSocket |

所有 API 响应使用 `HttpResponse` 信封格式：`{code, message, data}`。

## 前端说明

### 主要页面

| 路由 | 说明 |
|------|------|
| `/login` | 登录 |
| `/register` | 注册 |
| `/dashboard` | 首页总览 |
| `/tutor` | 智能辅导 |
| `/resource-generator` | 独立资源生成 |
| `/resource-history` | 独立资源历史 |
| `/resource-detail/:id` | 独立资源详情 |
| `/path-planner` | 学习路径创建入口 |
| `/path-planner/overview/:id?` | 路径总览 |
| `/path-planner/node/:nodeId` | 节点学习页 |
| `/path-planner/history` | 路径历史 |
| `/path-resource-history` | 路径资源历史 |
| `/path-resource/:id` | 路径资源详情 |
| `/question-bank` | 题库 |
| `/profile` | 画像页 |

### 前端技术栈

- Vue 3 + TypeScript
- Vue Router
- Element Plus（UI 组件）
- ECharts / vue-echarts（图表）
- Axios（HTTP）
- markdown-it + KaTeX（Markdown/LaTeX 渲染）
- markmap（思维导图）
- highlight.js（代码高亮）
- mp4-muxer（浏览器端 MP4 封装）
- pptxgenjs（PowerPoint 生成）
- reveal.js（演示幻灯片）

### 前端启动

```bash
npm run dev      # 启动开发服务器
npm run build    # 类型检查 + 构建
npm run preview  # 预览构建产物
```

构建前会执行 `vue-tsc -b` 进行类型检查。如果构建失败，优先检查：
- TypeScript 类型错误
- 新增依赖是否已安装
- 组件是否引入了缺失模块

## 后端说明

后端位于 `server/`，详细说明见 [server/README.md](server/README.md)。

### 后端技术栈

- FastAPI + SQLModel / SQLAlchemy Async
- PostgreSQL（asyncpg 异步驱动）
- LangChain + LangGraph（多智能体编排）
- OpenAI 兼容 API
- ChromaDB / FAISS（向量检索）
- uv（Python 包管理）
- Remotion 4.0（讲解视频渲染）
- HyperFrames（动画视频渲染）
- FFmpeg / FFprobe（音视频处理）
- Edge-TTS / 讯飞 TTS（视频配音）

### 后端启动

```bash
cd server
uv sync                                              # 安装依赖
uv run fastapi dev app/main.py --port 9999           # 开发服务器
uv run pytest                                         # 全部测试
uv run pytest tests/chat -q                           # 指定模块测试
uv run pytest -x                                      # 首个失败即停止
```

## 业务边界

这是项目里最重要且最容易混淆的设计约束。

### 独立资源生成（resource 域）

用户直接请求"生成教程/导图/PPT"，不依赖学习路径上下文：

- 数据存 `generated_resources` / `generated_resource_items`
- 页面：`ResourceGenerator`、`ResourceHistory`、`ResourceDetail`
- 接口：`/api/v1/ai/resource/*`

### 路径节点资源（path 域）

用户在学习路径内，围绕节点生成资源：

- 数据存 `learning_paths`、`path_nodes`、`path_node_tutorials`、`path_node_questions`、`path_node_resources`
- 页面：`LearningPath*`、`PathResource*`
- 接口：`/api/v1/ai/path/*`

两条业务链路**不应**复用同一套记录展示页，也不应混用资源历史。

## 端口配置

| 服务 | 端口 |
|------|------|
| Frontend (Vite) | 5173 |
| Backend (FastAPI) | 9999 |
| API Docs (Swagger) | 9999/docs |
| Ollama (可选) | 11434 |
| PostgreSQL | 5432 |

Vite 代理：`/api` → `http://127.0.0.1:9999`，`/ws` → `ws://127.0.0.1:9999`

## 故障排查

| 问题 | 排查方向 |
|------|----------|
| 启动数据库错误 | 检查 `config.yaml` 的 `database.url`、PostgreSQL 是否运行、是否执行过 `init_schema.sql` |
| 首页 500 | 检查 dashboard 聚合查询是否访问不存在的表/字段 |
| 路径规划异常 | 检查 `learning_paths` 子表结构、接口字段与前端是否一致、节点资源是否误走独立资源域 |
| 前端 API 500 | 检查 Vite 代理端口（9999）是否与后端一致 |
| 视频渲染失败 | 检查 FFmpeg 是否安装、`video-render` 目录是否初始化（`npm install`）、Remotion 版本是否正确 |
| TTS 无声音 | 检查 `spark_tts` 配置是否正确，或检查网络连接（Edge-TTS 需联网） |
| 向量检索失效 | 检查 Ollama 服务是否启动、`bge-m3` 模型是否下载、`knowledge.enabled` 是否为 `true` |
| 数字人连接失败 | 检查 `avatar.*` 配置是否完整、WebSocket 地址是否正确、JWT Token 是否有效 |

## 推荐阅读顺序

1. 本文件 `README.md`
2. [server/README.md](server/README.md)
3. [src/app/router/routes.ts](src/app/router/routes.ts)（前端路由）
4. [server/app/main.py](server/app/main.py)（后端入口）
5. [server/app/routes.py](server/app/routes.py)（后端路由挂载）
6. [server/init_schema.sql](server/init_schema.sql)（数据库结构）
7. [server/config.yaml](server/config.yaml)（配置示例）