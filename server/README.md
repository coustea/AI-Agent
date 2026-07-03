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
| 视频渲染 | Remotion 4.0, HyperFrames, FFmpeg |
| TTS 配音 | Edge-TTS, 讯飞星火 TTS |

## 视频渲染模块

后端包含两条独立的视频渲染管线，均需要 FFmpeg 支持。

### 1. Remotion 讲解视频

**入口**：`app/resource/agents/video.py` → `app/shared/video/agent.py`

**渲染器**：`app/shared/video/renderer.py` → `video-render/` (Remotion 项目)

**依赖**：
- FFmpeg / FFprobe（必须）
- Node.js 18+（必须）
- Remotion 4.0.478（video-render/package.json）

**工作流程**：
1. `VideoMaterialAgent` 提取教学材料要点
2. `VideoDirectorAgent` 规划场景节奏
3. `SceneWriterAgent` 为每个场景撰写脚本与视觉 cue
4. `VideoTtsService`（讯飞 TTS 或 Edge-TTS）生成配音 MP3
5. `RemotionVideoRenderer` 调用 `npx tsx scripts/render.ts` 渲染 MP4

**配置**（`config.yaml`）：
```yaml
video:
  render_timeout_seconds: 900  # 单视频最大渲染时长
  concurrency: 4                # Remotion 并发
  chromium_gl: angle            # Chromium GL 后端
```

**验证 FFmpeg 安装**：
```bash
ffmpeg -version      # 需能看到 libx264、aac 编码器
ffprobe -version     # 用于探测音视频流信息
```

**初始化 video-render**：
```bash
cd video-render
npm install
# 验证 Remotion CLI
npx remotion --version
```

### 2. HyperFrames 动画讲解

**入口**：`app/resource/agents/cartoon.py` → `app/shared/cartoon/pipeline.py`

**渲染器**：`app/shared/cartoon/renderer.py` → `npx hyperframes render`

**依赖**：
- FFmpeg（必须，推荐带 NVENC）
- Node.js 18+（必须）
- HyperFrames CLI（自动通过 npx 调用）

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

### FFmpeg 安装指南

**macOS**：
```bash
brew install ffmpeg
# 验证
ffmpeg -version
```

**Ubuntu/Debian**：
```bash
sudo apt update
sudo apt install ffmpeg
# 验证
ffmpeg -version
```

**带 NVENC 支持的 FFmpeg（Linux + NVIDIA GPU）**：
```bash
# 安装 NVIDIA 驱动后
sudo apt install ffmpeg
# 验证 NVENC 支持
ffmpeg -encoders | grep nvenc
# 应看到：h264_nvenc, hevc_nvenc
```

**Windows**：
从 https://ffmpeg.org/download.html 下载预编译版本，解压后添加到 PATH。

## TTS 配音服务

视频渲染管线支持两种 TTS 后端：

### 讯飞星火 TTS（默认）

配置（`config.yaml`）：
```yaml
spark_tts:
  app_id: "your-app-id"
  api_key: "your-api-key"
  api_secret: "your-api-secret"
```

使用场景：讲解视频（`voice: teacher`）

### Microsoft Edge TTS（免费）

无需密钥，通过 `edge-tts` Python 包调用：

```bash
# 已在 pyproject.toml 中声明
uv sync  # 自动安装 edge-tts>=7.2.8
```

使用场景：动画讲解视频（`voice: teacher`）、离线/测试环境

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
│   ├── app.py               # FastAPI 应用工厂
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
- PostgreSQL 12+
- **Node.js 18+**（视频渲染必需）
- **FFmpeg & FFprobe**（视频渲染必需）
- [uv](https://docs.astral.sh/uv/)（Python 包管理器）
- **Ollama + bge-m3**（可选，向量检索）

### 1. 安装依赖

**系统依赖**：
```bash
# macOS
brew install ffmpeg node ollama  # ollama 为可选

# Ubuntu/Debian
sudo apt install ffmpeg nodejs npm
# 可选：curl -fsSL https://ollama.ai/install.sh | sh

# 验证
ffmpeg -version
ffprobe -version
node --version  # >= 18.0.0
```

**Python 依赖**：
```bash
cd server
uv sync
```

**Remotion 项目**（讲解视频渲染）：
```bash
cd video-render
npm install
```

**Ollama embedding 模型**（可选）：
```bash
ollama pull bge-m3:latest
ollama serve
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
| `/api/v1/ai/resource` | resource | 资源生成（含 video、cartoon 智能体），状态查询，事件流 |
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
| 认证 | `users`, `active_tokens`, `schools` |
| 对话 | `chat_sessions`, `chat_turns`, `chat_messages`, `chat_session_summary_blocks`, `chat_long_term_memories`, `chat_attachment_analyses`, `chat_uploaded_files`, `chat_message_attachments`, `chat_tool_invocations`, `chat_turn_transcripts` |
| 画像 | `global_profiles`, `course_profiles` |
| 资源生成 | `generated_resources`, `generated_resource_items` |
| 学习路径 | `learning_paths`, `path_nodes`, `path_node_tutorials`, `path_node_questions`, `path_node_resources` |
| 评估 | `learning_events`, `learning_sessions` |
| 题库 | `quiz_questions`, `wrong_questions` |

数据库结构变更需同步修改 `init_schema.sql` 和 `infra/models.py`，新表必须加入 `REGISTERED_MODELS` 元组。

## Prompt 系统

每个模块拥有独立的 `prompts/` 目录，使用 `.md` 模板文件：

- `chat/prompts/` — 辅导系统指令, 回答策略, 搜索指令, 教学图
- `chat/memory/prompts/` — 压缩, 长期记忆更新
- `path/prompts/` — 路径规划, 教程, 题目生成
- `resource/prompts/` — 各 Agent 指令（planning, content, mindmap, quiz, code, reading, ppt, review, video）

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

- `tests/chat/test_reasoning_agent.py` — `FakeLlm` 缺少 `astream` 属性

## 开发约定

- 配置统一从 `config.yaml` 读取，不硬编码、不使用 `.env`
- 数据库结构变更同步修改 `init_schema.sql` 和 `infra/models.py`
- 新表必须加入 `REGISTERED_MODELS` 元组
- `get_session()` 用于 FastAPI 依赖注入（手动提交），`session_scope()` 用于后台任务（自动提交/回滚）
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
