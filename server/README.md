# AI 学习平台 · 后端服务

基于 **FastAPI + LangGraph** 的多智能体个性化学习平台后端，提供 AI 辅导对话、多模态学习资源生成、学习路径规划、题库与数字人播报等能力。后端通过三层记忆与学习者画像驱动个性化教学，并将多智能体编排复用于独立资源生成与路径节点学习两条独立的业务链路。

---

## 目录

- [核心能力](#核心能力)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [配置](#配置)
- [API 参考](#api-参考)
- [动画与课件渲染系统](#动画与课件渲染系统)
  - [环境准备](#环境准备首次渲染前必做)
  - [HyperFrames 动画讲解](#hyperframes-动画讲解)
  - [TTS 语音合成](#tts-语音合成)
- [记忆与画像](#记忆与画像)
- [RAG 知识库](#rag-知识库)
- [测试](#测试)
- [项目结构](#项目结构)
- [开发约定](#开发约定)
- [故障排查](#故障排查)

---

## 核心能力

- **AI 辅导对话** — SSE 流式输出，融合三层上下文（会话摘要 / 长期记忆 / 学习画像）实现因材施教；支持附件分析、联网搜索与教学图生成。
- **多智能体资源生成** — 一键生成教程、思维导图、题目、代码示例、阅读材料、PPT 课件、动画讲解等多模态资源。
- **学习路径规划** — 课程级路径编排，节点内形成「教程 → 测验 → 辅助资源」的学习闭环，节点资源按需单智能体生成。
- **算法可视化** — 后端基于 Python 抽象语法树（AST）分析与代码插装，支持官方与自定义算法模板运行，生成包含作用域、变量状态、输出及调用栈的可视化 Trace 数据。
- **题库与错题本** — 编程题与客观题管理，答题事件自动归集错题。
- **数字人播报** — WebSocket 桥接讯飞数字人，ASR 实时识别 + 数字人播报互动。
- **动态学习评估** — 聚合用户学习时长与测验得分等事实，通过 LLM 异步生成周期性评估报告并更新辅导建议策略。
- **GPU 加速动画渲染** — 检测到 NVIDIA GPU + NVENC 时自动启用 GPU 渲染（Ubuntu Linux 优先，无则自动回退至 CPU 软件渲染）。

## 技术栈

| 分类 | 选型 |
|------|------|
| **Web 框架** | FastAPI · SQLModel · SQLAlchemy (async) |
| **多智能体编排** | LangGraph · LangChain |
| **数据库** | PostgreSQL · asyncpg |
| **LLM 接入** | OpenAI 兼容 API（主模型：Astron-code-latest 等；视觉模型：GLM-4.6v-flash 等） |
| **动画与课件渲染** | HyperFrames 0.7 · Playwright · FFmpeg (NVENC) |
| **语音技术** | Microsoft Edge-TTS · 讯飞星火 TTS / ASR |
| **向量检索** | ChromaDB + BM25 (jieba) · RRF 融合 · bge-m3 (Ollama / OpenAI 兼容 API) |
| **包管理** | uv |

## 系统架构

### 领域模块

后端按业务领域拆分，每个领域遵循统一的分层结构：`api.py`（路由）→ `service.py`（业务逻辑编排）→ `schemas.py`（数据契约/DTO）。

| 领域 | 职责 |
|------|------|
| [auth/](file:///Users/apple/Code/software/server/app/auth) | 注册 / 登录 / 登出，JWT 校验 + `ActiveToken` 白名单，用户头像上传 |
| [chat/](file:///Users/apple/Code/software/server/app/chat) | SSE 辅导对话、附件分析、会话与三层记忆集成、对话视频生成 |
| [resource/](file:///Users/apple/Code/software/server/app/resource) | 独立多智能体资源生成（规划、大纲 Planning → 并行生成 Worker → 审查 Review） |
| [path/](file:///Users/apple/Code/software/server/app/path) | 学习路径规划生成、阶段与节点状态流转、节点工作空间及可继续学习仪表盘聚合 |
| [profile/](file:///Users/apple/Code/software/server/app/profile) | 学习者画像动态推断（`UserProfile` / `UserProfileDimension`），Onboarding 首入问卷，推荐列表 |
| [evaluation/](file:///Users/apple/Code/software/server/app/evaluation) | 学习事件采集、时长会话统计与异步学习评估生成 |
| [quiz/](file:///Users/apple/Code/software/server/app/quiz) | 题库练习、随机测试、答题历史、错题本归集与归档 |
| [avatar/](file:///Users/apple/Code/software/server/app/avatar) | 数字人 Interact 服务状态获取、说话打断与清理，WebSocket 桥接 |
| [algorithm_visualizer/](file:///Users/apple/Code/software/server/app/algorithm_visualizer) | 编译运行、Python AST 代码插装、Trace 生成及输入契约 |
| [infra/](file:///Users/apple/Code/software/server/app/infra) | 基础设施层（ChromaDB/PostgreSQL、SQLModel 表映射、配置文件、日志处理、通用 Prompt） |
| [shared/](file:///Users/apple/Code/software/server/app/shared) | 跨领域共享渲染组件（动画 HTML 播放、PPT 演示大纲、研究代理、音效与 TTS） |

应用启动流程集中在 [app/main.py](file:///Users/apple/Code/software/server/app/main.py)：`create_app()` 配置 CORS 与全局异常处理，`lifespan()` 预热 Prompt 模板、初始化数据库并执行知识库（RAG）健康检查，[app/routes.py](file:///Users/apple/Code/software/server/app/routes.py) 统一挂载全部 HTTP 与 WebSocket 路由。

### 三条核心运行链路

**1. 辅导对话链路（个性化主链路）**
`POST /api/v1/ai/chat/messages` → 创建对话 → 持久化用户消息与附件 → 组装多层上下文（历史 / 摘要块 / 长期记忆 / RAG 源）→ `TutorAgent`（LangGraph StateGraph：分类识别 → 路由工具 → 生成回复）→ SSE 流式回传 → 持久化回复 → 触发压缩与长期记忆抽取。

**2. 独立资源生成链路**
`POST /api/v1/ai/resources` → 持久化 `GeneratedResource` 任务 → 后台 LangGraph 父工作流（Planning → 并行 Worker → Review）→ 持久化 `GeneratedResourceItem` 产物 → 通过 SSE 实时推送生成状态和进度。

**3. 学习路径链路**
`POST /api/v1/ai/path-plan` → 后台生成阶段与节点 → `GET .../nodes/{id}/workspace` 驱动节点工作空间 → 节点学习流程（教程 Tutorial 生成 → Quiz 测验测试 → 辅助资源按需生成）→ 学习事件反馈画像与评估。

> **关键设计边界**：独立资源（`generated_resources`）与路径节点资源（`path_node_resources`）**共用 Agent 实现，但其持久化模型、API 接口与展示详情页各自独立**。两者不可合并记录或混用接口。

## 快速开始

本节以 **Ubuntu 22.04 / 24.04** 或 **macOS** 平台为例进行说明。

### 环境要求

按用途分为「必需」「视频/动画渲染必需」「可选」三档：

| 依赖 | 版本 | 档位 | 用途 |
|------|------|------|------|
| **Python** | ≥ 3.13 | 必需 | 后端服务运行时 |
| **uv** | 最新 | 必需 | Python 虚拟环境与依赖包管理 |
| **PostgreSQL** | ≥ 12 | 必需 | 主数据库 |
| **Python 构建工具链** | — | 必需 | 编译 `asyncpg` / `faiss-cpu` / `greenlet` 等 C 扩展 |
| **FFmpeg / FFprobe** | ≥ 4.0 | 视频功能必需 | 动画音频拼接、视频编码及合并 |
| **Node.js** | ≥ 22 | 视频功能必需 | 运行 HyperFrames 动画生成 CLI（Playwright 驱动） |
| **Playwright / Chromium**| — | 视频功能必需 | 渲染动画帧及 PPT 生成快照 |
| **Ollama + bge-m3** | — | 可选 | 本地向量检索（`knowledge.enabled: true` 时启用） |
| **NVIDIA 驱动 + NVENC** | — | 可选 | GPU 硬件加速动画编码（无则自动回退至 CPU 软件编码） |

### 1. 安装系统依赖

**Ubuntu (apt):**
```bash
sudo apt update
sudo apt install -y build-essential python3-dev libpq-dev libffi-dev libssl-dev pkg-config curl git ffmpeg
```

**macOS (brew):**
```bash
brew install ffmpeg pkg-config
```

**Windows (winget):**
```powershell
winget install Gyan.FFmpeg
```

### 2. 安装 Python 3.13 与 uv

**Ubuntu:**
```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.13 python3.13-venv python3.13-dev

# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
```

**macOS:**
```bash
brew install python@3.13 uv
```

### 3. 安装 Node.js 22 (动画渲染必需)

HyperFrames CLI 要求 Node.js ≥ 22。

**Ubuntu:**
```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

**macOS:**
```bash
brew install node@22
```

**Windows (winget):**
```powershell
winget install OpenJS.NodeJS.LTS
```

### 4. 安装项目依赖并预备渲染环境

```bash
cd server

# 1. 安装 Python 依赖
uv sync

# 2. 安装 Playwright 所需无头浏览器依赖
uv run playwright install chromium

# 3. 安装项目本地 Node 依赖 (HyperFrames)
npm ci
# (注：如果缺少依赖可执行 npm install --save-exact hyperframes@0.7.58)

# 4. 下载 HyperFrames 渲染内核并验证
npx --no-install hyperframes browser ensure
npx --no-install hyperframes doctor
```

### 5. 初始化数据库

```bash
# 创建角色与数据库（需与 config.yaml -> database.url 一致）
# 以下使用默认示例用户 "coustea" / 密码 "Aa123456"
psql -U postgres -c "CREATE USER coustea WITH PASSWORD 'Aa123456';"
psql -U postgres -c "CREATE DATABASE agent OWNER coustea;"

# 导入建表及索引结构
psql "postgresql://coustea:Aa123456@127.0.0.1:5432/agent" -f init_schema.sql
```

### 6. 配置 `config.yaml`

编辑 [server/config.yaml](file:///Users/apple/Code/software/server/config.yaml)，填入数据库连接、LLM API 密钥以及其他的可选星火/数字人/搜索密钥。（详见下节 [配置](#配置)）。

### 7. 启动开发服务

```bash
uv run fastapi dev app/main.py --port 9999
```

访问交互式 API 调试文档：<http://localhost:9999/docs>

### 8. 启用动画 GPU 硬件加速 (可选，针对 Linux + NVIDIA)

在 Linux 环境下，如果机器配备了 NVIDIA GPU，系统能够基于 NVENC 编码器加速动画的渲染出帧：

```bash
# 确认驱动正常
nvidia-smi

# 确认 FFmpeg 已包含 h264_nvenc 硬件编码器
ffmpeg -hide_banner -encoders | grep h264_nvenc
```

---

## RAG 知识库

知识库采用 **ChromaDB（向量）+ BM25（关键词）混合检索 + RRF 融合**，默认以 `bge-m3` 模型作为嵌入端点。

### 目录结构

[app/rag/](file:///Users/apple/Code/software/server/app/rag)
- `data/`
  - `source/` ← 源文档（按课程子目录存放只读文档）
  - `index/` ← 构建产物（ChromaDB 向量数据 + BM25 序列化数据 + 索引描述 manifest）
- [load.py](file:///Users/apple/Code/software/server/app/rag/load.py) - 文档加载器（支持 `.md` / `.txt` / `.pdf`）
- [metadata.py](file:///Users/apple/Code/software/server/app/rag/metadata.py) - 文档元数据（标题、章节名、英文目录映射中文课程名）
- [splitter.py](file:///Users/apple/Code/software/server/app/rag/splitter.py) - 语义块切割
- [embeddings.py](file:///Users/apple/Code/software/server/app/rag/embeddings.py) - 向量化客户端与超时熔断器
- [retriever.py](file:///Users/apple/Code/software/server/app/rag/retriever.py) - 双路混合检索与 RRF 归一化融合
- [indexing/build.py](file:///Users/apple/Code/software/server/app/rag/indexing/build.py) - 知识库一键离线索引构建脚本

### 手动构建索引

保证向量服务（如本地 Ollama 运行且有拉取模型，或者配置了有效的云端 API）在线后，在 [server/](file:///Users/apple/Code/software/server) 目录下执行命令：

```bash
# 标准构建
uv run python -m app.rag.indexing.build

# GPU 环境可加大并发批量
uv run python -m app.rag.indexing.build --batch-size 64

# 仅检查现有索引的健康状态
uv run python -m app.rag.indexing.build --check-only
```

### 启动时自动检查

应用启动时（`app/main.py` lifespan）会自动进行索引的健康检查与预热加载：
- **索引完整可用**：正常载入。
- **发现嵌入模型不匹配**：若配置文件中的模型与已存 manifest 里的模型不一致，**会自动触发后台线程异步重建**。
- **未启用知识库**：通过配置参数 `knowledge.enabled: false` 显式跳过。

---

## 配置说明

所有运行时配置集中在 [server/config.yaml](file:///Users/apple/Code/software/server/config.yaml) 文件。核心配置结构如下：

| 配置键路径 | 是否必填 | 配置内容描述说明 |
|------------|:--------:|------------------|
| `app.host` / `app.port` | 否 | 服务监听地址与端口（默认 `127.0.0.1:9999`） |
| `database.url` | **是** | PostgreSQL 异步连接字符串，需以 `postgresql+asyncpg://` 开头 |
| `jwt.secret_key` | **是** | JWT 签名密钥（需防泄漏，长度至少 32 字符） |
| `models.main` | **是** | 系统最核心的主推理大语言模型连接参数（含 `base_url`, `api_key`, `model_name`） |
| `models.vision` | 否 | 用于上传图片消息识别及附件分析的视觉模型参数，不填则前端上传图片报错 |
| `spark` | 否 | 讯飞星火 Web API 基础凭证（用于语音识别 ASR 与语音合成 TTS） |
| `avatar` | 否 | 讯飞互动数字人配置项，含锚点 `anchor_id`、背景、IAT 以及交互端点等 |
| `search` | 否 | 联网搜索引擎 API 密钥（支持 `tavily_key` 或 `spark_key`） |
| `knowledge` | 否 | 知识库检索配置参数，包括 `embed_model` 名字及 `embed_base_url` 向量服务器等 |
| `memory` | 否 | 三层记忆微调参数，包括会话压缩的 Token/消息临界阈值 |

---

## API 参考

所有响应统一使用 `HttpResponse` 信封：`{ "code": 200, "message": "...", "data": {} }`。

| 请求 API 路径前缀 | 业务领域模块 | 接口主要能力 |
|-------------------|:------------:|--------------|
| `/api/v1/users` | auth | 注册、登录、登出、获取与更新当前登录用户信息、上传头像。 |
| `/api/v1/ai/chat` | chat | 对话会话（Session）增删改查、SSE 辅导流式对话、素材附件上传与视频生成。 |
| `/api/v1/ai/resources` | resource | 独立多智能体资源生成任务创建、获取状态/历史、资源大纲详情及最近推荐列表。 |
| `/api/v1/ai/path-plan` | path | 生成学习路径、获取节点工作空间与教程内容、节点习题测试及评分提交、获取评估详情。 |
| `/api/v1/ai/profile` | profile | 画像信息（8维度指标）与推断事实检索、Onboarding 数据补全、首页画像推荐。 |
| `/api/v1/ai/quiz` | quiz | 题库练习生成、评分判定、个人刷题历史、练习推荐。 |
| `/api/v1/ai/wrong` | quiz | 错题本列表、错题温习抽题测试、归档错题、删除错题。 |
| `/api/v1/ai/evaluation` | evaluation | 手动记录学习事件与会话时长、生成周期性评估报告及辅导策略。 |
| `/api/v1/ai/avatar` | avatar | 获取数字人 Interact 视频流地址、打断数字人发音、清理会话资源。 |
| `/api/v1/ai/algorithm-visualizer`| visualizer | 获取支持的可视化语言、获取模板代码及输入契约、自定义代码 AST 插装分析与 Trace 运行。 |
| `/ws/avatar` | websocket | 数字人专属语音对话 WebSocket 鉴权及交互端点。 |

---

## 动画与课件渲染系统

后端包含一条完整的基于 HTML 快照的视频渲染管线，检测到 NVIDIA GPU 时自动启用 NVENC 硬件编码进行 GPU 加速。

### 1. PPT 演示生成
`PPTAgent`（[app/resource/agents/ppt.py](file:///Users/apple/Code/software/server/app/resource/agents/ppt.py)）通过规划生成幻灯片内容，并在对应的用户静态资源目录生成一个可供前端渲染交互的网页 `slides.html`。

### 2. HyperFrames 动画讲解
动画讲解智能体（`CartoonAgent`）将学习大纲转化为分镜及解说词，再借助 TTS 和 HyperFrames 合成导出高清 `.mp4` 视频：
- **入口**：[app/resource/agents/cartoon.py](file:///Users/apple/Code/software/server/app/resource/agents/cartoon.py) → [app/shared/cartoon/pipeline.py](file:///Users/apple/Code/software/server/app/shared/cartoon/pipeline.py)。
- **运行器**：[app/shared/cartoon/composer.py](file:///Users/apple/Code/software/server/app/shared/cartoon/composer.py)（动作清单组装）→ [app/shared/cartoon/media.py](file:///Users/apple/Code/software/server/app/shared/cartoon/media.py)（调起 Playwright 浏览器加载页面并运行 HyperFrames 播放渲染）。
- **渲染器**：调用 `node_modules/.bin/hyperframes` 将渲染帧用 FFmpeg 录制合并为带有字幕及配音的高清视频。
- **降级保护**：启动时检测系统可用内存。如果物理机内存受限（≤8GB），渲染器会自动降级为单 Worker 模式以防止系统溢出宕机；检测到 GPU 会自动执行硬件编码加速。

### 3. TTS 语音合成

TTS 支持两种后端接入，具有不同的应用领域：
- **讯飞星火 TTS**：由 `spark` 配置组（`app_id`、`api_key`、`api_secret`）授权访问，生成自然的教学讲解语音。
- **Microsoft Edge-TTS**：免费后端，需要网络联通。当系统未配置 `spark` 凭证或服务离线时自动回退作为兜底方案。

---

## 单元测试

后端单元测试使用 `pytest` 进行覆盖测试。

```bash
cd server

# 运行所有可用单元测试
uv run pytest

# 仅运行 chat 模块相关的测试
uv run pytest tests/chat -q

# 仅运行 算法可视化 Trace 处理的测试 (或特定测试文件)
uv run pytest tests/algorithm_visualizer/test_runner.py -q
```

---

## 常见问题与排查方向

| 问题现象 | 排查方向 |
|----------|----------|
| **后端提示 `active_tokens` 或数据库字段不存在** | 检查物理表结构是否与最新 [server/app/infra/models.py](file:///Users/apple/Code/software/server/app/infra/models.py) 模型保持同步；如果是全新安装，重新执行 `psql -d agent -f init_schema.sql` 刷新结构。 |
| **画像推荐接口返回 500** | 确认已提交了 `onboarding` 首入设置，系统需要画像数据建立推荐先验；检查对应 `UserProfile` 在数据库中是否存在。 |
| **动画渲染失败或报无头浏览器缺失** | 确认已在 `server/` 下运行过 `uv run playwright install chromium` 安装 Playwright 对应的 Chromium 底层渲染包。 |
| **本地 Ollama 无法提供检索服务** | 检查 Ollama 服务监听的端口号。默认为 `11434`。如果 `config.yaml` 写的向量服务器地址不一致，请手动微调。 |
| **大模型响应失败或接口报 401** | 检查 `config.yaml` 中 `models.main` 配置的接口地址和 API 密钥拼写是否错误。目前 Astron 等大模型在部分国内云端可能需要代理。 |
