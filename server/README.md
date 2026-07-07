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
- [视频渲染子系统](#视频渲染子系统)
- [记忆与画像](#记忆与画像)
- [RAG 知识库](#rag-知识库)
- [测试](#测试)
- [项目结构](#项目结构)
- [开发约定](#开发约定)
- [故障排查](#故障排查)

---

## 核心能力

- **AI 辅导对话** — SSE 流式输出，融合三层上下文（会话摘要 / 长期记忆 / 学习画像）实现因材施教；支持附件分析、联网搜索与教学图生成。
- **多智能体资源生成** — 一键生成教程、思维导图、题目、代码示例、阅读材料、PPT、讲解视频、动画讲解等多模态资源。
- **学习路径规划** — 课程级路径编排，节点内形成「教程 → 测验 → 辅助资源」的学习闭环，节点资源按需单智能体生成。
- **题库与错题本** — 编程题与客观题管理，答题事件自动归集错题。
- **数字人播报** — WebSocket 桥接讯飞数字人，ASR 实时识别 + 数字人播报互动。
- **首页仪表盘** — 学习数据聚合、学习进度追踪与个性化推荐。
- **GPU 加速视频渲染** — 检测到 NVIDIA GPU + NVENC 时自动启用 GPU 渲染（Ubuntu Linux 优先）。

## 技术栈

| 分类 | 选型 |
|------|------|
| Web 框架 | FastAPI · SQLModel · SQLAlchemy (async) |
| 多智能体编排 | LangGraph · LangChain |
| 数据库 | PostgreSQL · asyncpg |
| LLM 接入 | OpenAI 兼容 API · Anthropic · 智谱 AI |
| 视频渲染 | Remotion 4 · HyperFrames · FFmpeg (NVENC) |
| 语音合成 | Microsoft Edge-TTS · 讯飞星火 TTS |
| 向量检索 | ChromaDB + BM25 (jieba) · RRF 融合 · bge-m3 (OpenAI 兼容 API) |
| 包管理 | uv |

## 系统架构

### 领域模块

后端按业务领域拆分，每个领域遵循统一的分层结构：`api.py`（路由）→ `service.py`（编排）→ `schemas.py` / `request.py` / `response.py`（DTO）。

| 领域 | 职责 |
|------|------|
| `auth` | 注册 / 登录 / 登出，JWT 校验 + `ActiveToken` 白名单 |
| `chat` | SSE 辅导对话、附件分析、记忆与画像集成 |
| `resource` | 独立多智能体资源生成（不依赖学习路径上下文） |
| `path` | 学习路径规划与节点工作空间 |
| `profile` | 学习者画像推断（`GlobalProfile` / `CourseProfile`） |
| `evaluation` | 学习事件采集与会话汇总 |
| `dashboard` | 首页聚合与推荐 |
| `quiz` | 题库与错题本 |
| `avatar` | 数字人 REST 接口与 WebSocket 桥接 |
| `infra` | 数据库、SQLModel、日志、配置、Prompt、响应信封 |
| `shared` | 跨领域共享能力（视频渲染、动画渲染、工具函数） |

应用启动流程集中在 `app/main.py`：`create_app()` 配置 CORS 与异常处理，`lifespan()` 预热 Prompt 模板、初始化数据库并执行健康检查，`app/routes.py` 统一挂载全部 HTTP 与 WebSocket 路由。

### 三条核心运行链路

**1. 辅导对话链路（个性化主链路）**
`POST /api/v1/ai/chat/stream` → 创建 `ChatTurn` → 持久化用户消息与附件 → 组装多层上下文（历史 / 摘要块 / 长期记忆 / 画像 / 检索源）→ `TutorAgent`（LangGraph StateGraph：classify → 路由 → answer / search / attachment）→ SSE 流式回传 → 持久化回复 → 触发压缩与长期记忆抽取。

**2. 独立资源生成链路**
`POST /api/v1/ai/resources` → 持久化 `GeneratedResource` 任务 → 后台 LangGraph 父工作流（Planning → 并行 Worker → Review）→ 持久化 `GeneratedResourceItem` → 通过 SSE 推送进度。

**3. 学习路径链路**
`POST /api/v1/ai/path-plan` → 后台生成阶段与节点 → `GET .../nodes/{id}/workspace` 驱动节点工作空间 → 节点学习走 LangGraph learn workflow → 节点资源存入 `PathNodeResource` → 学习事件反馈画像与评估。

> **关键设计边界**：独立资源（`generated_resources`）与路径节点资源（`path_node_resources`）**共用 Agent 实现，但持久化模型、API 与详情页各自独立**。两者不可合并记录或混用接口。

## 快速开始

本节以 **Ubuntu 22.04 / 24.04** 为主线说明（视频渲染管线的主要目标平台）。Windows / macOS 仅需替换对应包管理命令，不再赘述。

### 环境要求

按用途分为「必需」「视频功能必需」「可选」三档：

| 依赖 | 版本 | 档位 | 用途 |
|------|------|------|------|
| Python | ≥ 3.13 | 必需 | 后端运行时 |
| uv | 最新 | 必需 | Python 包 / 虚拟环境管理 |
| PostgreSQL | ≥ 12 | 必需 | 主数据库 |
| Python 构建工具链 | — | 必需 | 编译 `asyncpg` / `faiss-cpu` / `greenlet` 等 C 扩展 |
| FFmpeg / FFprobe | ≥ 4.0 | 视频功能必需 | Remotion / HyperFrames 渲染（含软件编码） |
| Node.js | ≥ 18 | 视频功能必需 | Remotion 渲染（`npx tsx`） |
| Ollama + bge-m3 | — | 可选 | 向量检索（`knowledge.enabled: true` 时启用） |
| NVIDIA 驱动 + NVENC | — | 可选 | GPU 加速视频编码（无则自动回退 CPU） |

> 仅运行核心对话与资源生成时，装齐「必需」档即可；视频生成、向量检索、数字人按需追加。

### 1. 安装系统依赖（apt）

```bash
sudo apt update

# Python 构建工具链：asyncpg / faiss-cpu / greenlet 等需要 C 编译器与 libpq 头文件
sudo apt install -y build-essential python3-dev libpq-dev libffi-dev libssl-dev \
                    pkg-config curl git

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql

# FFmpeg / FFprobe（含软件编码器）
sudo apt install -y ffmpeg
```

### 2. 安装 Python 3.13 与 uv

```bash
# Python 3.13（Ubuntu 22.04 默认源为 3.10，需 deadsnakes PPA；24.04 可省略 PPA）
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.13 python3.13-venv python3.13-dev

# uv（Astral 官方安装脚本）
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"     # 激活 uv 到当前 shell
```

### 3. 安装 Node.js 18（视频渲染才需要）

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
node -v   # 验证 ≥ 18
```

### 4. 安装项目 Python 依赖

```bash
cd server
uv sync            # 自动创建 .venv 并按 pyproject.toml 安装全部依赖
```

### 5. 初始化数据库

```bash
# 创建角色与数据库（用户名/密码需与 config.yaml → database.url 对应）
sudo -u postgres psql -c "CREATE USER coustea WITH PASSWORD 'Aa123456';"
sudo -u postgres psql -c "CREATE DATABASE agent OWNER coustea;"

# 导入初始 schema（建表 + 索引）
psql "postgresql://coustea:Aa123456@127.0.0.1:5432/agent" -f init_schema.sql
```

> 也可用仓库自带的 `docker-compose.yml` 以容器方式运行 PostgreSQL，首次启动会自动挂载 `init_schema.sql` 执行初始化。

### 6. 配置 `config.yaml`

填入真实凭据（详见下节 [配置](#配置)）。最简启动只需保证 `database.url`、`jwt.secret_key`、`models.{base_url, api_key, model_name}` 三项有效。

### 7. 启动服务

```bash
uv run fastapi dev app/main.py --port 9999    # 开发模式（热重载）
# 或
uv run python app/main.py                     # 生产模式
```

启动成功后访问交互式 API 文档：<http://localhost:9999/docs>

### 可选：启用视频 GPU 渲染（Ubuntu + NVIDIA）

```bash
# 1. 安装 NVIDIA 驱动（重启生效）
sudo ubuntu-drivers autoinstall
sudo reboot

# 2. 验证 NVENC 硬件编码器可用
ffmpeg -hide_banner -encoders | grep nvenc    # 应列出 h264_nvenc / hevc_nvenc 等
nvidia-smi                                    # 确认驱动与显存

# 3. 初始化 Remotion 前端依赖（首次渲染前一次性执行）
cd video-render
npm install
npx remotion --version                        # 验证 4.0.478
cd ..
```

无 GPU 环境无需任何额外操作，渲染管线会自动回退 `swiftshader` / CPU 软件渲染。

### 可选：启用向量检索（Ollama + bge-m3）

```bash
curl -fsSL https://ollama.com/install.sh | sh    # 安装 Ollama
systemctl --user enable --now ollama
ollama pull bge-m3                               # 拉取向量模型
```

随后确认 `config.yaml → knowledge.enabled: true` 即可生效。首次启动时若索引不存在且 `auto_build: true`，后台自动构建。

## RAG 知识库

知识库采用 **ChromaDB（向量）+ BM25（关键词）混合检索 + RRF 融合**，嵌入模型通过 OpenAI 兼容 API 接入（默认 bge-m3，1024 维）。

### 目录结构

```
server/app/rag/
├── data/
│   ├── source/              ← 源文档（按课程编号目录存放，只读）
│   │   ├── 01-计算机基础/
│   │   ├── 02-编程语言/
│   │   ├── ...
│   │   └── 11-通识与面试/
│   └── index/               ← 构建产物（ChromaDB + BM25 + manifest，可随时删除重建）
│       ├── chroma.sqlite3
│       ├── bm25_index.pkl
│       └── manifest.json
├── load.py                  ← 文档加载（.md/.txt/.pdf）
├── metadata.py              ← 元数据推断（课程名、标题、章节）
├── splitter.py              ← 文档分割
├── embeddings.py            ← 嵌入模型封装（含熔断器）
├── retriever.py             ← 混合检索 + RRF 融合
├── bm25.py                  ← BM25 索引（jieba 分词 + rank_bm25）
└── indexing/
    └── build.py             ← 离线索引构建器（唯一构建入口）
```

### 前提条件

1. **嵌入服务在线** — 任何 OpenAI 兼容的嵌入 API 均可，默认使用 llama.cpp 本地部署 bge-m3：

   ```bash
   # 示例：llama.cpp 启动嵌入服务
   /path/to/llama-server -m bge-m3-Q8_0.gguf \
     --embedding --alias bge-m3:latest --port 10000 -ngl 999
   ```

   也可使用 Ollama 或远程 API，只需在 `config.yaml` 中配置对应的 `embed_base_url`。

2. **源文档就位** — `app/rag/data/source/` 下按课程编号目录存放 `.md`/`.txt`/`.pdf` 文件。

3. **config.yaml 配置正确** — `knowledge` 配置组与嵌入服务匹配：

   ```yaml
   knowledge:
     enabled: true
     embed_model: "bge-m3:latest"           # 嵌入模型名称（需与嵌入服务一致）
     embed_base_url: "http://127.0.0.1:10000/v1"  # 嵌入服务地址
     top_k: 4
     max_context_chars: 6000
     auto_build: true                        # 启动时索引不存在则自动构建
   ```

### 手动构建索引

```bash
cd server

# 标准构建（batch-size=16）
uv run python -m app.rag.indexing.build

# GPU 加速构建（加大批量，约快 4 倍）
uv run python -m app.rag.indexing.build --batch-size 64

# 仅检查索引健康状态（不构建）
uv run python -m app.rag.indexing.build --check-only
```

**可选参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--batch-size` | 16 | 嵌入批量大小，GPU 可用时建议 64 |
| `--source-dir` | `app/rag/data/source` | 源文档目录 |
| `--output-dir` | `app/rag/data/index` | 索引输出目录 |
| `--check-only` | — | 只检查索引健康，不执行构建 |

### 构建流程

```
加载文档 → 元数据推断 → 文档分割 → 重置熔断器 → ChromaDB 存储 → BM25 索引 → 写 manifest → 验证 → 原子替换
```

安全机制：先构建到临时目录 `index.building-<uuid>`，验证通过后原子替换正式目录；任一步失败则删除临时目录，现有索引不受影响。

### 启动时自动检查

应用启动时（`app/main.py` lifespan）自动执行索引健康检查，日志以 `[KB]` 前缀输出：

| 状态 | 日志 | 行为 |
|------|------|------|
| 索引就绪 | `[KB] Index ready: N chunks, embedding_model=...` | 正常运行 |
| 嵌入模型变更 | `[KB] Embedding model changed (config=...), index needs rebuild` | **自动触发后台重建**（即使 `auto_build: false`） |
| 索引不存在 + `auto_build: true` | `[KB] Index not ready (reason: ...), auto-building in background...` | 后台自动构建 |
| 索引不存在 + `auto_build: false` | `[KB] Index not ready and auto_build disabled` | 仅警告，检索不可用 |
| 构建成功 | `[KB] Auto-build succeeded: N chunks, embedding_model=...` | 正常运行 |
| 构建失败 | `[KB] Auto-build failed: ...` | 仅日志，不影响服务启动 |
| 知识库禁用 | `[KB] Knowledge base disabled by config` | 跳过检查 |

### 切换嵌入模型

只需修改 `config.yaml` 中的 `knowledge.embed_model` 和 `knowledge.embed_base_url`，**无需改代码**：

1. 修改 `config.yaml` → `knowledge.embed_model` 为新模型名称
2. 重启服务 → 启动时检测到 `embedding_model_mismatch` → 自动触发重建
3. 重建完成后日志输出 `[KB] Auto-build succeeded`

> 嵌入客户端不使用缓存（`embeddings.py` 无 `lru_cache`），配置修改后立即生效。

### 课程推断规则

源文档的课程名从文件路径自动推断，支持编号目录格式：

- `01-计算机基础/02-计算机网络/xxx.md` → `course="计算机网络"`
- `03-人工智能/01-机器学习入门/xxx.md` → `course="机器学习"`

路径片段 → 课程名映射定义在 `app/rag/metadata.py` 的 `_COURSE_DIR_MAP`。新增课程目录时需在此字典中添加对应条目。

### 故障排查

| 症状 | 排查方向 |
|------|----------|
| 构建报 "No matching documents found" | 确认 `app/rag/data/source/` 下有 `.md`/`.txt`/`.pdf` 文件 |
| 构建报嵌入超时 / 连接拒绝 | 确认嵌入服务运行中：`curl http://127.0.0.1:10000/v1/models` |
| 构建中断后再次构建失败 | 熔断器可能已打开，构建器会自动重置；若仍失败等待 5 分钟冷却 |
| 检索返回 "unavailable" | 检查 `knowledge.enabled: true`；索引是否存在；嵌入服务是否在线 |
| 检索结果课程名全为空 | 检查源文档路径是否在 `_COURSE_DIR_MAP` 覆盖的目录下 |
| 索引体积过大 | 正常：65229 chunks ≈ 660MB（ChromaDB 530MB + BM25 129MB） |

## 配置

所有运行时配置集中在 **`config.yaml`**（本项目不使用 `.env`）。核心配置组与必填标注：

| 配置组 | 必填 | 说明 |
|--------|------|------|
| `app` | 否 | host / port / debug |
| `database` | **是** | PostgreSQL 连接 URL、连接池 |
| `jwt` | **是** | `secret_key`（≥ 32 字符）/ algorithm / expire_days |
| `models` | **是** | 主 LLM 的 `base_url` / `api_key` / `model_name` / 各场景 temperature |
| `models.vision` | 否 | 图片理解模型（缺失则跳过图片分析） |
| `spark` / `spark_tts` | 否 | 讯飞星火 TTS（缺失则自动回退 Edge-TTS） |
| `avatar` | 否 | 讯飞数字人 + ASR（缺失则数字人功能不可用） |
| `search` | 否 | Tavily / 讯飞搜索密钥（缺失则关闭联网搜索） |
| `knowledge` | 否 | Ollama + bge-m3 向量检索（`enabled: false` 可整体关闭） |
| `memory` | 否 | 会话压缩与长期记忆抽取阈值（有合理默认值） |
| `chat` | 否 | 文件上传限制、历史长度（有合理默认值） |
| `paths_config` | 否 | 测验题量、及格分 |
| `video` | 否 | 渲染超时、并发数、Chromium GL 后端（默认 `angle`） |

最小可启动配置示例（只列必填三项）：

```yaml
database:
  url: "postgresql+asyncpg://coustea:Aa123456@127.0.0.1:5432/agent"
jwt:
  secret_key: "至少-32-个字符的随机字符串"        # 必须 ≥ 32 字符
models:
  base_url: "https://api.openai.com/v1"          # 或任意 OpenAI 兼容端点
  api_key: "sk-xxx"
  model_name: "gpt-4o"
```

> `config.yaml` 中其余可选配置组即使留空或缺失，对应功能会优雅降级，不会阻塞核心服务启动。

## API 参考

所有响应统一使用 `HttpResponse` 信封：

```json
{ "code": 200, "message": "...", "data": {} }
```

| 前缀 | 领域 | 主要能力 |
|------|------|----------|
| `/api/v1/users` | auth | 注册 / 登录 / 登出 / 当前用户 |
| `/api/v1/ai/chat` | chat | SSE 流式对话、附件上传、会话与画像接口 |
| `/api/v1/ai/resources` | resource | 独立资源生成、状态查询、详情、历史、Agent 列表、SSE |
| `/api/v1/ai/path-plan` | path | 路径生成、当前/历史路径、节点工作空间、节点教程/测验/资源 |
| `/api/v1/ai/cartoon` | cartoon | 动画讲解视频生成 |
| `/api/v1/ai/dashboard` | dashboard | 首页聚合与推荐 |
| `/api/v1/ai/evaluation` | evaluation | 学习事件、评估汇总 |
| `/api/v1/ai/quiz-bank` | quiz | 题库管理 |
| `/api/v1/ai/wrong-questions` | quiz | 错题本 |
| `/api/v1/ai/avatar` | avatar | 数字人 REST 接口 |
| `/ws/avatar` | websocket | 数字人 WebSocket（`?token=JWT` 鉴权） |

> 路由的权威来源是 `app/routes.py` 与各领域 `api.py`；完整端点签名以 `/docs` 的 OpenAPI 文档为准。

## 视频渲染子系统

后端包含两条独立的视频渲染管线，均检测到 NVIDIA GPU 时自动启用 GPU 加速。

### Remotion 讲解视频

- **入口**：`app/resource/agents/video.py` → `app/shared/video/agent.py`
- **渲染器**：`app/shared/video/renderer.py` → `video-render/scripts/render.ts`
- **流程**：素材提取 → 场景节奏规划 → 逐场景脚本撰写 → TTS 合成 → `npx tsx scripts/render.ts` 渲染 MP4
- **GPU 路径**：Chromium GL 后端 `angle`（Remotion 官方推荐的 GPU 后端）+ FFmpeg `hardwareAcceleration` 启用 NVENC 硬件编码
- **无 GPU 兜底**：自动回退 `swiftshader` 软件渲染，保证 headless 环境也能出帧

首次渲染前需初始化前端依赖：

```bash
cd video-render
npm install
npx remotion --version    # 验证 Remotion 4.0.478
```

### HyperFrames 动画讲解

- **入口**：`app/resource/agents/cartoon.py` → `app/shared/cartoon/pipeline.py`
- **渲染器**：`app/shared/cartoon/renderer.py` → `npx hyperframes render`
- **GPU 路径**：`--browser-gpu`（浏览器 GPU 合成）+ `--gpu`（NVENC 编码）
- **自动环境调优**：物理核心数、可用内存、NVIDIA 检测；低内存（≤ 8GB）自动降级为单 worker
- **失败回退**：GPU 渲染失败时自动以 CPU 模式重试

### TTS 语音合成

| 后端 | 适用场景 | 是否需要密钥 |
|------|----------|--------------|
| 讯飞星火 TTS | 高质量配音（讲解视频默认） | 是（`config.yaml → spark_tts`） |
| Microsoft Edge-TTS | 免费 / 测试 / 动画讲解 | 否（需联网，随 `uv sync` 自动安装） |

## 记忆与画像

个性化能力建立在三层记忆架构之上，由对话 token 数 / 消息数阈值触发：

| 层级 | 存储表 | 作用 |
|------|--------|------|
| 会话压缩 | `chat_session_summary_blocks` | 近期对话 → 压缩摘要块 |
| 长期记忆 | `chat_long_term_memories` | 抽取可复用的学习者事实 |
| 学习画像 | `global_profiles` / `course_profiles` | 由记忆 + 学习事件构建多维度画像 |

> 修改个性化行为时，应**联合检查** `chat`、`profile`、`evaluation` 三个领域，而非孤立看待。

## 测试

```bash
uv run pytest                         # 全部测试
uv run pytest tests/chat -q           # 指定模块
uv run pytest tests/resource -q
uv run pytest tests/path -q
uv run pytest -x                      # 首个失败即停止
uv run pytest tests/chat/test_history.py -q -k summary   # 单一用例
```

> 已知预存失败（无需调试）：`tests/chat/test_reasoning_agent.py`，`FakeLlm` 缺少 `astream` 属性。

## 项目结构

```
server/
├── app/
│   ├── auth/            # 认证（JWT + ActiveToken 白名单）
│   ├── chat/            # 辅导对话（SSE + 三层记忆）
│   │   └── memory/      # 会话压缩、长期记忆、画像构建
│   ├── resource/        # 独立资源生成（多智能体工作流）
│   ├── path/            # 学习路径规划与节点学习
│   ├── profile/         # 学习者画像
│   ├── evaluation/      # 学习事件与评估
│   ├── dashboard/       # 首页仪表盘
│   ├── quiz/            # 题库与错题本
│   ├── avatar/          # 数字人桥接
│   ├── shared/          # 跨领域共享（video / cartoon / utils）
│   ├── infra/           # 数据库、模型、配置、日志、Prompt
│   ├── main.py          # 应用入口
│   └── routes.py        # 路由挂载
├── tests/               # pytest 测试
├── config.yaml          # 运行配置（唯一配置来源）
├── init_schema.sql      # 数据库初始化 SQL
└── pyproject.toml       # Python 依赖声明
```

## 开发约定

- **配置**：统一从 `config.yaml` 读取，不硬编码、不使用 `.env`。
- **Schema 同步**：结构变更需**同时**更新 `init_schema.sql` 与 `app/infra/models.py`；新增表必须加入 `REGISTERED_MODELS` 元组，否则 `init_db()` 不会创建。
- **数据库会话**：请求处理器使用 `get_session()`（调用方手动提交）；后台任务使用 `session_scope()`（自动提交/回滚）。鉴权依赖 `get_session()`，**勿替换为 `session_scope()`**。
- **LLM 访问**：通过 `get_llm()` 单例，统一使用 OpenAI 兼容 API。
- **响应格式**：所有 API 返回 `HttpResponse` 信封 `{code, message, data}`。
- **Prompt 模板**：各模块 `prompts/*.md`，支持 `{variable}` 占位替换，应用启动时预热。
- **代码风格**：4 空格缩进、type hints、`snake_case`、Google Python Style Guide。

## 故障排查

| 症状 | 排查方向 |
|------|----------|
| 启动数据库错误 | 检查 `config.yaml → database.url`；确认 PostgreSQL 运行中；确认已执行 `init_schema.sql` |
| 首页 500 | 检查 dashboard 聚合查询是否访问了不存在的表或字段 |
| 路径规划异常 | 检查 `learning_paths` 子表结构；确认节点资源未误走独立资源域 |
| 视频渲染失败 | 确认 FFmpeg 已安装；`video-render/` 已 `npm install`；Remotion 版本为 4.0.478 |
| GPU 未生效 | `ffmpeg -encoders \| grep nvenc` 确认 NVENC；`nvidia-smi` 确认驱动；查看日志中 GL 后端选择记录 |
| TTS 无声 | 检查 `spark_tts` 配置；Edge-TTS 需要联网 |
| 向量检索失效 | 确认嵌入服务运行中（`curl <embed_base_url>/models`）；`knowledge.enabled: true`；索引已构建（`app/rag/data/index/manifest.json` 存在） |
| 数字人连接失败 | 检查 `avatar.*` 配置完整、WebSocket 地址正确、JWT 有效 |
| 前端 API 500 | 确认 Vite 代理端口（默认 9999）与后端一致 |
