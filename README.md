# AI 学习平台

> 多智能体个性化学习资源平台 — 智能辅导对话、多模态资源生成、学习路径规划、学习者画像、算法可视化

## 项目简介

本项目是一个面向教育场景的全栈 AI 学习平台，通过多智能体协作提供个性化的学习体验。系统支持 AI 辅导对话、自动生成多模态学习资源（教程、思维导图、题目、代码示例、PPT 课件、动画讲解等）、智能规划学习路径、进行算法可视化，并基于学习行为构建学习者画像实现因材施教。

### 核心特性

- **智能辅导对话** - 基于三层记忆架构（会话摘要、长期记忆、学习画像）的个性化对话，支持 Markdown 渲染、公式排版及 Mermaid 图表展示。
- **多智能体资源生成** - 一键生成教程、思维导图、习题、代码示例、拓展阅读材料、PPT 演示课件、动画讲解等。
- **学习路径规划** - 自动规划课程级学习路径，节点内通过「教程 → 测验 → 辅助资源」形成学习闭环。
- **算法可视化** - 提供官方算法模板与自定义 Python 代码插装执行，生成追踪 Trace 并支持单步动画播放与交互。
- **学习者画像** - 基于对话、学习事件、题目表现及学习时长沉淀 8 维度动态学习画像。
- **题库与错题本** - 提供系统题库管理、答题自动评分，并将错题自动归集到错题本，提供针对性巩固练习。

### 技术栈

**前端**
- **核心框架**：Vue 3.5 + TypeScript 5.9 + Vue Router 4.6
- **构建工具**：Vite 7.2 + Tailwind CSS 4.3 + `@tailwindcss/vite`
- **UI 组件库**：shadcn-vue + PrimeVue 4.5.5 + Radix Vue (Reka UI)
- **可视化与画板**：ECharts 6.0 + markmap + D3.js + GSAP 3.15（动画）
- **编辑器**：Monaco Editor（代码编辑与对比）
- **数据传输**：Axios + SSE 流式通信
- **文档渲染**：remark + rehype + KaTeX + Shiki

**后端**
- **核心框架**：FastAPI + SQLModel (SQLAlchemy Async)
- **多智能体编排**：LangGraph + LangChain
- **数据存储**：MySQL + `aiomysql` (异步驱动)
- **大模型接入**：OpenAI 兼容 API（主模型：Astron-code-latest 等；视觉模型：GLM-4.6v-flash 等）
- **向量检索库**：ChromaDB + BM25 + bge-m3（双路混合检索与 RRF 融合）
- **动画渲染**：HyperFrames 0.7 + Playwright（动画与 PPT 网页快照渲染生成 MP4）
- **语音技术**：Edge-TTS + 讯飞星火语音合成/识别 (ASR/TTS)

---

## 目录结构

- [src/](src/) - 前端源码目录
  - [src/app/](src/app/) - 应用入口、布局 (MainLayout) 与路由配置
  - [src/features/](src/features/) - 业务域功能模块
    - [auth/](src/features/auth/) - 认证（登录/注册/引导弹窗）
    - [chat/](src/features/chat/) - 智能辅导对话组件
    - [dashboard/](src/features/dashboard/) - 首页仪表盘与概览
    - [resource/](src/features/resource/) - 独立资源生成域
    - [learning-path/](src/features/learning-path/) - 学习路径规划与节点工作空间
    - [profile/](src/features/profile/) - 学习者画像雷达图及偏好设置
    - [question-bank/](src/features/question-bank/) - 题库答题练习
    - [evaluation/](src/features/evaluation/) - 学习数据上报与事件 API 封装
    - [learning-assessment/](src/features/learning-assessment/) - 学习评估与历史看板视图
    - [algorithm-visualization/](src/features/algorithm-visualization/) - 算法可视化画板与代码运行
  - [src/shared/](src/shared/) - 共享模块（API 封装、通用 UI 组件、Markdown 渲染、数据模型等）
- [server/](server/) - 后端源码目录
  - [server/app/](server/app/) - API 逻辑代码
    - [auth/](server/app/auth/) - 用户认证与令牌白名单
    - [chat/](server/app/chat/) - 辅导对话与三层记忆管理
    - [resource/](server/app/resource/) - 独立资源生成（多智能体规划并行工作流）
    - [path/](server/app/path/) - 学习路径规划、节点管理及仪表盘聚合
    - [profile/](server/app/profile/) - 学习者画像多维属性服务
    - [evaluation/](server/app/evaluation/) - 学习事件采集、时长计算与学习评估生成
    - [quiz/](server/app/quiz/) - 题库管理、提交判分与错题本
    - [algorithm_visualizer/](server/app/algorithm_visualizer/) - 算法模板、插装运行、Trace 构建及运行时
    - [rag/](server/app/rag/) - ChromaDB 向量索引与混合检索
    - [shared/](server/app/shared/) - 课件 (PPT) 与动画 (Cartoon) 渲染管线、通用子 Agent 工具、ASR/TTS 桥接
    - [infra/](server/app/infra/) - 基础设施（数据库连接、SQLModel 定义、配置加载、日志处理）
    - [main.py](server/app/main.py) - 后端主程序入口
    - [routes.py](server/app/routes.py) - 业务路由集中注册中心
  - [server/tests/](server/tests/) - 后端 pytest 单元测试目录
  - [server/config.yaml](server/config.yaml) - 后端运行时配置文件
  - [server/pyproject.toml](server/pyproject.toml) - Python 依赖定义

---

## 环境要求

### 必需环境

| 依赖 | 版本要求 | 用途 |
|------|---------|------|
| **Python** | ≥ 3.13 | 后端服务运行时 |
| **uv** | 最新版 | Python 包依赖及虚拟环境管理器 |
| **Node.js** | ≥ 22 | 前端构建与 HyperFrames 动画渲染 CLI |
| **npm** | 与 Node.js 匹配 | 前端包依赖管理 |
| **MySQL** | ≥ 8.0.13 | 关系型数据库（存储用户、对话、路径、画像等数据） |
| **Playwright** | 适配系统版本 | HyperFrames 引擎与 PPT 网页快照渲染底层浏览器依赖 |
| **FFmpeg + FFprobe** | ≥ 4.0 | 视频/动画编码、音频拼接及格式转换 |

### 可选环境

| 依赖 | 用途 | 配置位置 |
|------|------|----------|
| **Ollama + bge-m3** | 用于混合检索（RAG）向量嵌入服务 | `config.yaml` -> `knowledge` |
| **NVIDIA GPU + NVENC** | GPU 硬件加速动画视频编码（无则自动回退至 CPU 软件编码） | 系统自动检测 |


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
# 1. 确保 MySQL 服务已启动
# 2. 创建名称为 agent 的数据库（排序规则保持大小写敏感）
mysql -u root -p -e "CREATE DATABASE agent CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs;"
# 3. 启动后端服务时，系统会自动执行 init_db() 建表与种子数据检查，无需手动执行 SQL
```

### 5. 配置运行时参数

编辑后端 [server/config.yaml](server/config.yaml) 文件，配置必要的密钥及服务地址。系统统一定义两类模型配置（文本模型 `text` 与视觉模型 `vision`）：

```yaml
# 应用配置
app:
  host: "127.0.0.1"
  port: 9999

# 数据库连接
database:
  url: "mysql+aiomysql://用户名:密码@127.0.0.1:3306/agent"

# JWT 认证配置（需保证 secret_key 至少 32 位）
jwt:
  secret_key: "your-secret-key-at-least-32-characters-long"
  algorithm: "HS256"

# LLM 大模型配置（统一管理文本与多模态视觉模型）
models:
  text:
    base_url: "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"  # 文本模型 API 地址
    api_key: "your-api-key"
    model_name: "astron-code-latest"
    timeout: 300
    max_retries: 2
  vision:
    base_url: "https://open.bigmodel.cn/api/paas/v4/"  # 视觉模型 API 地址
    api_key: "your-api-key"
    model_name: "glm-4.6v-flash"
    timeout: 300
    max_retries: 2
```

### 6. 启动服务

**启动后端服务**（在 `server/` 目录中）

```bash
uv run fastapi dev app/main.py --port 9999
```

后端 API Swagger 文档地址：`http://localhost:9999/docs`

**启动前端服务**（在项目根目录中）

```bash
npm run dev
```

前端界面访问地址：`http://localhost:5173`

---

## 核心业务流程

平台内部包含三条隔离的核心业务链路，分别由其独立数据模型及 API 支撑：

### 1. 智能辅导对话（chat 域）

智能对话建立在**短期历史、压缩摘要块、长期记忆**三层上下文之上。

```
用户提问 → 组装多层上下文 (历史/摘要块/长期记忆/RAG源) → 触发画像加载
        → TutorAgent (流式 ReAct 循环：思考/工具决策 → 动态调用工具/图表生成)
        → SSE 流式输出 (agent_status / tool_call / activity / text_delta)
        → 存储对话与产物 → 判定并异步触发会话压缩与长期记忆更新
```

- **核心端点**：`POST /api/v1/ai/chat/messages`
- **关键机制**：直接流式 ReAct 循环、实时工具执行状态与活动卡片、联网搜索、知识库检索 (RAG)、Mermaid/SVG 教学图生成、消息附件（文档与图片）异步视觉分析、视频与 PPT 产物标签 (`<artifact>`) 自动解析。

### 2. 独立资源生成（resource 域）

用户直接向 AI 发起多模态资源生成请求（例如直接生成主题 PPT、动画讲解等），不依赖学习路径上下文。

```
POST /api/v1/ai/resources → 创建 Resource 任务 → 异步触发 DAG 多智能体编排
                          → 大纲 Planning → 并行调用 Content/Mindmap/Quiz/PPT/Cartoon Worker
                          → 上游教程素材无缝向后传递 (Handoffs) → 独立无状态 Subagent 执行
                          → SSE 进度实时推送 → 生成 GeneratedResourceItem 产物
```

- **生成类型**：教程、思维导图、选择题与判断题、示例代码、阅读材料、PPT 演示课件、动画讲解。
- **关联表**：`generated_resources` / `generated_resource_items` / `generated_resource_agent_runs`。
- **前端页面**：`/resource-generator`、`/ai/resources/history`、`/resource-detail/:id`。

### 3. 学习路径规划（path 域）

根据用户给定的学习目标及已掌握的知识点，智能规划阶段式学习路径，进行渐进式闭环学习。

```
POST /api/v1/ai/path-plan → 生成 LearningPath (含多阶段及关联 PathNode)
                          → 激活路径 → 前端工作空间渲染首个 available 节点
                          → 点击开始学习 → 异步生成 Tutorial 教程大纲与正文
                          → 触发 5 道测验题 (Quiz) 生成 → 答题提交并自动评分
                          → 判定节点状态更新 (completed / completed_with_gaps)
                          → （可选）生成思维导图/代码/PPT/动画等节点辅助资源
```

- **节点状态流转**：`locked` (未解锁) → `available` (可学习) → `in_progress` (学习中) → `completed` (已完成) 或 `completed_with_gaps` (有薄弱点已完成)。
- **核心表**：`learning_paths`、`path_nodes`、`path_node_tutorials`、`path_node_questions`、`path_node_resources`。
- **前端页面**：`/path-planner`、`/path-planner/overview/:id`、`/path-planner/node/:nodeId`。

> [!IMPORTANT]
> **设计边界**：独立资源（`resource` 域）与路径节点资源（`path` 域）虽共用生成 Agent 底层，但其 API 接口、数据表实体及前端展示页均严格独立隔离，数据互不交叉。

---

## 前端页面路由

路由配置在 [src/app/router/routes.ts](src/app/router/routes.ts) 中，已登录页面外层挂载在 `MainLayout` 中：

| 页面路由 | 页面组件 | 是否需要登录 | 功能描述 |
|----------|----------|:------------:|----------|
| `/login` | `Login.vue` | 否 | 用户登录页 |
| `/register` | `Register.vue` | 否 | 用户注册页 |
| `/onboarding` | `OnboardingDialog.vue` | 否 | 首次登录问卷引导弹窗 |
| `/dashboard` | `Home.vue` | **是** | 个人首页，包含推荐、画像雷达、快捷动作 |
| `/tutor` | `Tutor.vue` | **是** | 智能辅导对话与多模态交互 |
| `/resource-generator` | `ResourceGenerator.vue` | **是** | 独立资源规划生成界面 |
| `/resource-detail/:id` | `ResourceResult.vue` | **是** | 独立资源生成进度及总览 |
| `/resource-detail/:id/:type` | `ResourceItemDetail.vue` | **是** | 独立资源具体项（PPT课件/动画等）详情展示 |
| `/ai/resources/history` | `ResourceHistory.vue` | **是** | 独立多模态资源生成历史记录 |
| `/path-planner` | `PathPlanCreate.vue` | **是** | 创建/规划新的个性化学习路径 |
| `/path-planner/overview/:id?`| `PathPlanOverview.vue` | **是** | 单条学习路径节点及概览看板 |
| `/path-planner/node/:nodeId` | `PathNodeStudy.vue` | **是** | 路径节点工作空间（学习教程、答题测试、生成补充资源） |
| `/path-planner/history` | `PathPlanHistory.vue` | **是** | 学习路径规划历史记录列表 |
| `/question-bank` | `QuestionBank.vue` | **是** | 学科题库测试与错题本回顾 |
| `/profile` | `Profile.vue` | **是** | 学习者个人中心及画像大盘 |
| `/assessment` | `LearningAssessment.vue` | **是** | 周期性学习评估报告与历史查看 |
| `/algorithm-visualizer` | `AlgorithmVisualization.vue` | **是** | 算法代码插装 Trace 运行与动态动画可视化播放 |

---

## 后端 API 路由

路由注册在 [server/app/routes.py](server/app/routes.py)，所有接口均返回格式一致的信封：`{code, message, data}`。

| API 请求路径前缀 | 关联领域 | 端点主要功能 |
|------------------|:--------:|--------------|
| `/api/v1/users` | auth | 注册 (`POST `)、登录 (`POST /auth`)、登出 (`POST /auth/logout`)、获取当前用户信息 (`GET /me`)、更新资料 (`PATCH /me`)、上传用户头像 (`POST /me/avatar`)。 |
| `/api/v1/ai/chat` | chat | 创建/删除会话 (`POST/DELETE /chat/sessions`)、SSE 流式对话 (`POST /chat/messages`)、上传文件/图片分析 (`POST /chat/upload`)、会话关联视频生成 (`POST /chat/videos`)。 |
| `/api/v1/ai/resources` | resource | 触发生成 (`POST /resources`)、获取资源详情 (`GET /resources/{id}`)、轮询状态与进度事件流 (`GET /resources/{id}/{status|events}`)、最近生成列表 (`GET /dashboard/recent-resources`)。 |
| `/api/v1/ai/path-plan` | path | 创建路径规划 (`POST /path-plan`)、继续学习仪表盘 (`GET /dashboard/continue-learning`)、路径历史 (`GET /path-plan/history`)、节点工作空间 (`GET /path-plan/nodes/{id}/workspace`)、生成教程 (`POST /path-plan/nodes/{id}/tutorial`)、触发测验题 (`POST /path-plan/nodes/{id}/questions`)、提交测试评分 (`POST /path-plan/nodes/{id}/quiz-submit`)、生成节点辅助资源 (`POST /path-plan/nodes/{id}/resources/{type}`)、上报学习事件与评估 (`POST /path-plan/{id}/events` 与 `GET /path-plan/{id}/evaluation`)。 |
| `/api/v1/ai/profile` | profile | 获取个人画像指标与历史证据 (`GET /profile`)、更新设置 (`PATCH /profile`)、获取 Onboarding 设置及快速动作 (`GET/PATCH /profile/onboarding` & `GET /dashboard/quick-actions`)、获取推荐课程及画像雷达数据 (`GET /dashboard/recommendation` & `GET /dashboard/profile-radar`)。 |
| `/api/v1/ai/quiz` | quiz | 获取随机练习题目 (`GET /quiz`)、提交答题选项 (`POST /quiz/submit`)、获取个人答题统计指标与历史 (`GET /quiz/stats` & `GET /quiz/history`)、复习回顾 (`POST /quiz/review`)。 |
| `/api/v1/ai/wrong` | quiz | 获取错题列表 (`GET /wrong`)、随机抽题练习 (`GET /wrong/random`)、移除/彻底删除错题 (`DELETE /wrong/{id}`)、归档已掌握错题 (`POST /wrong/{id}/archive`)。 |
| `/api/v1/ai/evaluation` | evaluation | 手动上报学习事件 (`POST /evaluation/events`)、离开页面上报时长会话 (`POST /evaluation/sessions`)、触发/获取学习评估报告 (`POST/GET /evaluation/assessments/*`)、个人中心多图表数据聚合 (`GET /evaluation/dashboard`)。 |
| `/api/v1/ai/algorithm-visualizer` | visualizer | 获取支持的可视化语言 (`GET /algorithm-visualizer/languages`)、列出官方算法模板 (`GET /algorithm-visualizer/algorithms`)、获取算法源码及模板输入 (`GET /algorithm-visualizer/templates`)、自定义代码编译插装契约 (`POST /algorithm-visualizer/custom-contract`)、代码编译及 Trace 运行 (`POST /algorithm-visualizer/run`) |

---

## 记忆与画像架构

平台的个性化智能诊断与辅导策略建立在三层记忆架构之上：

| 记忆层级 | 物理表 | 触发与处理机制 | 画像/记忆作用 |
|----------|--------|----------------|--------------|
| **1. 消息摘要分块** | `chat_session_summary_blocks` | 触发时机：当单会话的消息数量或已用 Token 超过预设阈值。在后台增量摘要，并与原有摘要合并更新。 | 提炼近期多次会话的概要，压缩上下文，避免超长 Token 消耗大模型窗口。 |
| **2. 长期事实提取** | `chat_long_term_memories` | 触发时机：当单会话以结束或交互轮次足够时。系统使用大模型从近期对话的上下文事实中过滤非易逝性事实（如“喜欢图形化说明”、“擅长 Python 链表”）。 | 提供用户个人非易逝性的背景描述及长周期学习事实，直接作为 Tutor 交互先验。 |
| **3. 动态学习画像** | `user_profiles` <br> `user_profile_dimensions` | 触发时机：用户在平台中的对话交互、视频观看、题库测试、路径流转等动作会产生学习事件上报，由画像逻辑定时重算多维度数值与证据事实。 | 维护 Goal（目标）、Preference（偏好）、Style（风格）、Proficiency（熟练度）等 8 维度画像，驱动个性化出题与生成策略。 |

---

## 向量检索知识库 (RAG)

向量检索采用 **ChromaDB (向量检索) + BM25 (Jieba 分词的关键词检索)** 的双路检索架构，最后通过倒数排名融合 (RRF) 汇总输出 Top-K 的文档片段作为 AI Tutor 的辅助知识源。

### 启用知识库

1. **安装本地向量服务 (Ollama)** 并拉取 `bge-m3` 模型（如无需本地向量检索，可将 embedding 接口替换为 OpenAI 兼容的云端 API）：
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull bge-m3
   ollama serve
   ```
2. 在 [server/config.yaml](server/config.yaml) 中启用并配置知识库配置组：
   ```yaml
   knowledge:
     enabled: true
     embed_model: "bge-m3:latest"
     embed_base_url: "http://127.0.0.1:11434/v1"
     embed_api_key: "ollama"
     top_k: 4
     max_context_chars: 6000
   ```
3. 导入或者把你的源文档放置于 `server/app/rag/data/source/` 目录中，在 [server/](server/) 目录下执行脚本进行离线索引构建：
   ```bash
   uv run python -m app.rag.indexing.build
   ```

---

## 动画与课件渲染系统

对于生成的 PPT 与动画讲解，系统基于网页前端技术栈实现了脱离 GUI 界面的无头浏览器快照与渲染管线。

### 1. 网页 PPT 演示生成
PPTAgent 使用 PptxGenJS 工具循环生成可编辑的 `deck.pptx`，加载 `server/skills/pptx` 官方技能。通过 LibreOffice → PDF → PNG 进行逐页视觉审查，前端显示图片预览并提供 PPTX/PDF 下载。部署依赖和技能来源见 `server/skills/README.md`。

### 2. HyperFrames 动画讲解生成
动画智能体（`CartoonAgent`）将学习大纲拆分为若干分镜，为每个分镜生成语音播报脚本：
- **音频合成**：调用 Edge-TTS 或讯飞星火语音合成 API 将脚本合成为 `.mp3` 音频文件。
- **动画合成**：系统将分镜字幕、场景元素样式及动画时间序列导出为 HyperFrames 动作指令集。
- **后台渲染**：调用 Puppeteer 无头浏览器加载渲染页面，Playwright 执行 HyperFrames 播放并在后台利用 FFmpeg 实时编码录制为带有声音及字幕的高清 `.mp4` 视频文件。
- **环境降级**：引擎启动时会自动检测 CPU 核心数、内存及 GPU 环境。若物理系统内存不足（如 ≤8GB），将自动降级为单线程 CPU 渲染，若检测到 NVIDIA GPU + NVENC 编码器，则会自动使用 GPU 硬件加速以缩短渲染时长。

---

## 调试与单元测试

### 后端测试

后端采用 `pytest` + `pytest-asyncio` 进行覆盖测试。测试代码结构与 `app/` 模块结构一一映射。

```bash
cd server

# 运行所有单元测试
uv run pytest

# 运行指定模块测试
uv run pytest tests/chat -q

# 遇到第一个失败的用例立刻停止
uv run pytest -x
```

### 前端测试与构建验证

前端采用 `vitest` 进行组件与数据逻辑测试，使用 `vue-tsc` 执行全量类型检查。

```bash
# 运行前端全部单元测试
npm run test:run

# 执行前端全量类型检查与生产构建
npm run build
```

> [!NOTE]
> 数据库测试会在测试启动时自动创建临时 SQLite 表或模拟 Session，不污染物理运行数据库。

---

## 常见故障排查

| 问题现象 | 排查步骤及方向 |
|----------|----------------|
| **后台服务启动报错 `aiomysql` 错误** | 确认 MySQL 处于运行状态，并在 [server/config.yaml](server/config.yaml) 中核对 `database.url` 的用户名、密码及端口号。表结构在启动时按 [app/infra/models.py](server/app/infra/models.py) 自动创建，无需手工导入。 |
| **前端请求接口提示 500 / 跨域** | 检查 Vite 本地服务器的代理端口。`vite.config.ts` 中的 proxy 默认会将 `/api` 代理至 `http://127.0.0.1:9999`。若后端启动了其他端口，请修改 `VITE_API_PROXY_TARGET` 环境变量。 |
| **聊天或资源生成进度假死/无反应** | 大模型调用超时导致。请检查国内大模型代理服务的网络联通性，并在 `config.yaml` 对应大模型下调大 `timeout` 限制或增加 `max_retries` 重试。 |
| **视频/动画生成卡在 `rendering` 状态** | 确认系统里已全局安装了 `ffmpeg` 及 `ffprobe` 工具，且版本不低于 4.0；确认已在 `server` 目录执行过 `npm ci` 完整下载了 HyperFrames 和无头浏览器依赖。各个操作系统的详细动画渲染配置步骤请参阅 `server/README.md`。 |
| **大模型回答无法生成公式与图表** | 检查大模型输出流的格式。TutorAgent 依赖 Prompt 约束生成标准的 LaTeX (`$...$` 与 `$$...$$`) 及 Mermaid 代码块。可在 `server/app/infra/prompts/` 下微调提示词规范。 |

---

## License

本项目遵循 [MIT](LICENSE) 许可协议。
