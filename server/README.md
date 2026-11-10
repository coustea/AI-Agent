# Mentorly 后端服务 (`server/`)

Mentorly 后端基于 **Python 3.13+ · FastAPI · SQLModel (SQLAlchemy 2.0 Async) · MySQL (`aiomysql`)** 构建，提供用户认证、AI 辅导对话、多模态资源生成、学习路径规划、题库与错题本、7 维学习者画像、学习评估与混合检索知识库（RAG）服务。

> **架构设计原则**：
> 1. **自研轻量 Agent 运行时**：`TutorAgent` 采用无跨轮状态的 ReAct 循环 (`run_tutor_agent`) + `RunHooks` 内存快照状态机；`ResourceLeadAgent` 采用标准 Plan-and-Execute 主规划与工具装配循环；学习路径采用两阶段自定义工作流，**不依赖 LangGraph**（LangChain 仅用于 RAG 离线文档切分）。
> 2. **清晰分层与单事务持久化**：每个业务模块遵循 `api.py`（HTTP/SSE 路由）→ `service.py`（业务编排与事务落库）→ `schemas.py`（Pydantic 强类型契约）。
> 3. **领域边界隔离**：`resource`（独立资源生成）与 `path`（学习路径节点资源）复用 `shared` 中的底层 Agent 与工具基础设施，但拥有完全独立的数据表、API、文本与多媒体适配器及生命周期管理。
> 4. **全链路可观测性**：基于 Loguru 与 ContextVars 实现全局协程级链路追踪（`X-Request-ID` 透传、用户打标、异步任务隔离、工具参数易读提炼与结果摘要打印），消灭黑盒调用。

完整项目概览与前端说明请参见 [根目录 README](../README.md) 与 [前端 README](../src/README.md)。

---

## 技术栈

| 类别 | 技术选型 |
|------|----------|
| **Web 框架与 ORM** | FastAPI · SQLModel · SQLAlchemy 2.0 Async · Pydantic v2 |
| **数据库与驱动** | MySQL 8.0+ · `aiomysql`（测试环境支持 `aiosqlite`） |
| **鉴权与安全** | PyJWT（HS256）· Passlib (`bcrypt`) · 全局 `JWTMiddleware` |
| **大模型接入** | OpenAI Async SDK（统一封装 `LLM`：支持文本模型 `text` 与视觉模型 `vision`） |
| **全链路日志与追踪** | 原生 Loguru · `TraceLoggingMiddleware` (`X-Request-ID`) · ContextVars (`trace_id`, `user`) · 工具入参及结果摘要引擎 |
| **Agent 核心** | `run_tutor_agent` (Chat 导师) · `run_resource_lead_agent` (多模态资源总监) · `ToolRegistry` · `SkillLoader` |
| **课件与视频生产** | PptxGenJS · LibreOffice (`soffice`) · Poppler (`pdftoppm`) · HyperFrames CLI · Edge TTS (7.3.1+ Sec-MS-GEC v2) · FFmpeg / `ffprobe` |
| **测试工具** | `pytest` · `pytest-asyncio` · `vulture` |

---

## 目录结构

```text
server/
├── app/
│   ├── auth/                 # 用户注册、登录、JWT 鉴权、个人资料更新、头像上传
│   ├── chat/                 # AI 辅导对话模块
│   │   ├── api.py            # HTTP 与 SSE 路由 (/api/v1/ai/chat/*)
│   │   ├── service.py        # prepare_chat_run / execute_chat_run / save_run_result / 会话与历史管理
│   │   ├── context.py        # 历史加载、孤立 tool_calls 清洗、长输出裁剪、摘要/策略/AGENT.md 动态注入
│   │   ├── agent.py          # run_tutor_agent 无状态 ReAct 循环，返回 AgentResult(answer, new_messages)
│   │   ├── hooks.py          # RunHooks 状态容器与单槽位 SSE 通知队列、工具调用描述
│   │   ├── memory.py         # 会话滚动摘要压缩 (compress_session) 与 7 类长期记忆更新 (update_long_term_memory)
│   │   ├── tools.py          # 12 个 TutorAgent 工具装配与子智能体内部进度回调桥接
│   │   ├── files.py          # 上传附件安全存储、沙箱路径解析与文档解析 (PDF/Word/Excel/CSV/MD)
│   │   ├── schemas.py        # ChatRequest / AgentInput / RunState / RunStep / encode_chat_sse 等契约
│   │   └── prompts/          # tutor_agent.md / compression.md / ltm_update.md
│   ├── resource/             # 独立多模态资源生成模块 (Plan-and-Execute)
│   │   ├── api.py            # 资源任务创建、状态查询、全量快照 SSE 推流 (/api/v1/ai/resources/*)
│   │   ├── service.py        # 资源生命周期、任务落库、状态机更新与产物持久化
│   │   ├── agent.py          # run_resource_lead_agent 主规划总设计师智能体循环
│   │   ├── tools.py          # build_resource_tools：7 类子智能体专属工具 (讲义/脑图/测验/代码/阅读/PPT/视频)
│   │   ├── hooks.py          # ResourceRunHooks 运行快照状态机与单槽位 SSE 队列
│   │   └── schemas.py        # ResourceGenerationRequest / ResourcePreferences / ResourceRunState 等契约
│   ├── path/                 # 学习路径规划与节点学习模块
│   │   ├── api.py            # 路径创建、规划 SSE、节点工作区、教程/测验/节点资源接口
│   │   ├── workflows.py      # PathPlannerAgent (research → strategist) 与 NodeLearningAgent 工作流
│   │   ├── service.py        # 路径、节点、教程、测验与节点辅助资源编排服务
│   │   ├── text_resource.py  # Path 节点轻量文本辅助资源 (mindmap/code/reading) 生成适配器
│   │   ├── ppt.py / cartoon.py # Path 节点级 PPT 课件与教学视频生成适配器
│   │   └── event.py / events.py # PathEvents 实时进度通道
│   ├── profile/              # 7 维学习者画像模块 (Onboarding、维度推理评分、AGENT.md 生成、首页推荐与雷达图)
│   ├── quiz/                 # 408 题库检索、客观题提交判分、主观题单题/批量 AI 审阅、错题本管理
│   ├── evaluation/           # 学习行为事件、页面会话时长、7 天窗口事实聚合、评估报告与辅导策略更新
│   ├── shared/               # 跨模块 Agent 共享底座
│   │   ├── tools/            # ToolRegistry、sandbox 路径防护、SkillLoader 与 7 个内置沙箱工具 (builtin/)
│   │   ├── ppt/              # PPTAgent (PptxGenJS + LibreOffice + 逐页视觉审查)
│   │   └── cartoon/          # CartoonAgent (HyperFrames CLI + Edge TTS + 关键帧视觉审查 + ffprobe 校验)
│   ├── infra/                # 数据库连接 (database.py)、26 张表定义 (models.py)、LLM 客户端 (llm.py)、原生 Loguru 日志 (logging.py)
│   ├── middleware/           # TraceLoggingMiddleware (X-Request-ID 全局追踪与耗时)、JWTMiddleware (身份解析与打标)
│   ├── config.py             # config.yaml 解析与路径辅助函数
│   ├── exceptions.py         # 全局异常处理器
│   ├── response.py           # HttpResponse 统一 JSON 响应封装
│   ├── routes.py             # 路由集中注册
│   └── main.py               # FastAPI 应用入口与 lifespan 生命周期
├── skills/                   # Agent 技能包 (pptx / hyperframes / hyperframes-cli / hyperframes-registry / media-use)
├── tests/                    # pytest 测试套件 (171 项测试，覆盖全业务模块)
├── config.example.yaml       # 配置文件模板
├── docker-compose.yml        # 本地开发 MySQL 8.4 容器配置
└── pyproject.toml            # Python 依赖与 pytest 配置
```

---

## 快速启动

```bash
cd server

# 1. 同步 Python 依赖（需 Python >= 3.13）
uv sync

# 2. 复制并编辑配置文件
cp config.example.yaml config.yaml
# 必填项：database.url、jwt.secret_key、models.text

# 3. 启动 MySQL（可选用内置 docker compose）
docker compose up -d mysql

# 4. 启动开发服务器（端口 9999）
uv run fastapi dev app/main.py --port 9999
```

- Swagger UI 文档：<http://127.0.0.1:9999/docs>
- 生产环境启动：
  ```bash
  uv run uvicorn app.main:app --host 0.0.0.0 --port 9999
  ```

---

## 数据库与会话约定

- **唯一权威模型**：所有 26 张 SQLModel 表定义在 [`app/infra/models.py`](file:///Users/apple/Code/Python/software/server/app/infra/models.py)，并注册在 `REGISTERED_MODELS` 元组中。
- **自动建表说明**：应用启动时 `init_db()` 执行 `SQLModel.metadata.create_all` 创建缺失表，但**不会修改已有表结构**。开发期调整字段后需重建数据库。
- **会话使用模式**：
  - 路由请求级依赖注入使用 `Depends(get_session)`（`expire_on_commit=False`）。
  - 后台任务与独立事务块使用 `async with session_scope() as db:`（自动提交/回滚）。
  - 认证统一由 `JWTMiddleware` 全局拦截与注入，接口内部通过免参的 `get_current_user()` 读取 `UserClaims` 上下文。

---

## 测试

```bash
cd server

# 运行全部测试
uv run pytest

# 遇到首个失败即停止
uv run pytest -x

# 运行指定模块测试（如 chat 模块）
uv run pytest tests/chat -q
```

---

## 核心 Agent 运行机制

### 1. AI 辅导导师 (`run_tutor_agent`)
- **执行范式**：无跨轮状态的 ReAct 循环。接收由用户历史对话、清洗后的孤立工具调用、长输出截断、滚动摘要及 7 维学情画像（AGENT.md）构成的上下文。
- **状态流转**：通过 `RunHooks` 单槽位非阻塞队列将执行状态以 SSE 实时推送到前端：
  - `start` / `title`：任务初始化与会话标题命名
  - `step_start` / `step_done`：思考规划与步骤完成
  - `tool_start` / `tool_done`：12 种沙箱工具调用与进度上报
  - `artifact_preview` / `artifact_ready`：多模态课件/教学视频产物实时注入
  - `delta`：最终解答文本平滑流式推送

### 2. 多智能体多模态资源生成 (`run_resource_lead_agent`)
- **执行范式**：基于 **Plan-and-Execute** 架构的中心化主规划循环。
- **白名单装配机制**：
  - 前端用户自选所需智能体团队（`selected_agents`，如讲义、脑图、测验、代码、扩展阅读、PPT 课件、教学视频）。
  - 后端仅将已勾选智能体的生成工具（`generate_courseware`、`generate_mindmap` 等）注册并注入到 `ResourceLeadAgent` 的可用工具集中。
  - 主规划智能体首先生成整体教研蓝图，随后严格按计划调用已装配的工具并行/串行生产。未勾选的智能体工具在运行时被物理阻断，杜绝无意义消耗与越权调用。
- **产物与事件统一快照**：通过 `ResourceRunHooks` 向 SSE 推送完整的 `ResourceRunState` 快照（包含各子智能体状态、步骤日志、产物明细与错误信息），前端渲染即所得。

### 3. 学习路径规划 (`PathPlannerAgent`)
- **执行范式**：两阶段流水线（`research` 领域探查 → `strategist` 课程架构师）。
- **节点辅助资源**：节点内的文本型辅助资源（思维导图、案例代码、拓展阅读）由 `PathTextResourceAdapter` 按需实时生成；多媒体课件与视频适配调用底层 PPT 与 Cartoon Agent。
- **架构隔离**：与独立资源生成模块（`resource`）在数据表、API 路由、前端视图上完全物理与逻辑隔离。

---

## 全链路日志与追踪体系

系统采用原生 **Loguru** 全面替换标准库 `logging`，实现端到端的透明可观测性：

```text
2026-11-10 21:30:15 | INFO     | app.middleware.trace:dispatch:35 - [Req] [c4e2a1b9] user=42 POST /api/v1/ai/resources/ -> 200 OK (15ms)
2026-11-10 21:30:16 | INFO     | app.resource.agent:run_resource_lead_agent:120 - [ResourceLeadAgent] [c4e2a1b9] 第 1/15 轮: 主规划思考中...
2026-11-10 21:30:18 | INFO     | app.resource.agent:run_resource_lead_agent:142 - [ResourceLeadAgent] [c4e2a1b9] 工具 [1/2] generate_courseware 调用: topic='MySQL 索引底层原理', depth='deep'
2026-11-10 21:30:25 | INFO     | app.resource.agent:run_resource_lead_agent:160 - [ResourceLeadAgent] [c4e2a1b9] 工具 [1/2] generate_courseware 执行成功 (耗时 6850ms): 产物生成成功，包含 3280 字符 Markdown 核心讲义
```

1. **全局追踪透传**：
   - 请求发起时由 `TraceLoggingMiddleware` 解析或生成全局唯一的 `X-Request-ID`（截取前 8 位短标识便于控制台阅读），绑定至 `ContextVar`。
   - `JWTMiddleware` 鉴权成功后自动将 `user_id` 注入上下文，后续所有链路日志自动附带 `[trace_id]` 与 `user=xx`。
2. **工具调用与执行摘要**：
   - 核心工具注册层提供 `summarize_tool_args` 与 `summarize_tool_result`，对复杂或长文本入参进行结构化提炼（隐藏长 base64、截断过长 prompt、突出主题/核心选项）。
   - 执行完毕后打印毫秒级耗时及简短产物指标（字符数、页数、时长或关键数据），彻底消除 Agent 执行黑盒。

---

## 多媒体外部依赖准备

生产 PPT 课件与教学视频需要系统预装以下多媒体套件：

| 工具 | 推荐安装方式 (macOS / Ubuntu) | 作用 |
|------|--------------------------------|------|
| **Node.js** (>= 18) | `brew install node` / `apt install nodejs` | 驱动 PptxGenJS 课件脚本与 HyperFrames CLI 视频渲染 |
| **LibreOffice** | `brew install --cask libreoffice` / `apt install libreoffice` | 将 `.pptx` 无损转换为 `.pdf`（用于课件预览及多模态视觉质检） |
| **Poppler** (`pdftoppm`) | `brew install poppler` / `apt install poppler-utils` | 将 PDF 逐页栅格化为高分辨率 PNG 图像供视觉模型审阅 |
| **Edge-TTS** (>= 7.3.1) | 由 `uv sync` 自动安装 | 微软最新 `Sec-MS-GEC v2` 动态握手协议的高品质教学语音旁白合成 |
| **FFmpeg** & **ffprobe** | `brew install ffmpeg` / `apt install ffmpeg` | 视频流合并、音频拼接、关键帧抽取与时长媒体元数据校验 |

