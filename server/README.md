# Mentorly 后端服务 (`server/`)

Mentorly 后端基于 **Python 3.13+ · FastAPI · SQLModel (SQLAlchemy 2.0 Async) · MySQL (`aiomysql`)** 构建，提供用户认证、AI 辅导对话、多模态资源生成、学习路径规划、题库与错题本、7 维学习者画像、学习评估与混合检索知识库（RAG）服务。

> **架构设计原则**：
> 1. **自研轻量 Agent 运行时**：`TutorAgent` 采用无跨轮状态的 ReAct 循环 (`run_tutor_agent`) + `RunHooks` 内存快照状态机；资源生成采用四阶段 `asyncio` DAG 编排；学习路径采用两阶段自定义工作流，**不依赖 LangGraph**（LangChain 仅用于 RAG 离线文档切分）。
> 2. **清晰分层与单事务持久化**：每个业务模块遵循 `api.py`（HTTP/SSE 路由）→ `service.py`（业务编排与事务落库）→ `schemas.py`（Pydantic 契约）。
> 3. **领域边界隔离**：`resource`（独立资源生成）与 `path`（学习路径节点资源）复用 `shared` 中的底层 Agent 与工具基础设施，但拥有完全独立的数据表、API 与生命周期管理。

完整项目概览与前端说明请参见 [根目录 README](../README.md) 与 [前端 README](../src/README.md)。

---

## 技术栈

| 类别 | 技术选型 |
|------|----------|
| **Web 框架与 ORM** | FastAPI · SQLModel · SQLAlchemy 2.0 Async · Pydantic v2 |
| **数据库与驱动** | MySQL 8.0+ · `aiomysql`（测试环境支持 `aiosqlite`） |
| **鉴权与安全** | PyJWT（HS256）· Passlib (`bcrypt`) · 全局 `JWTMiddleware` |
| **大模型接入** | OpenAI Async SDK（统一封装 `LLM`：支持文本模型 `text` 与视觉模型 `vision`） |
| **Agent 核心** | `run_tutor_agent` · `RunHooks` · `ToolRegistry` · `SkillLoader` · 无状态子智能体 (`run_subagent`) |
| **课件与视频生产** | PptxGenJS · LibreOffice (`soffice`) · Poppler (`pdftoppm`) · HyperFrames CLI · Edge TTS · FFmpeg / `ffprobe` |
| **测试工具** | `pytest` · `pytest-asyncio` |

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
│   │   ├── hooks.py          # RunHooks 状态容器与单槽位 SSE 通知队列、工具调用中文描述映射
│   │   ├── memory.py         # 会话滚动摘要压缩 (compress_session) 与 7 类长期记忆更新 (update_long_term_memory)
│   │   ├── tools.py          # 13 个 TutorAgent 工具装配与 PPT/视频子智能体进度回调绑定
│   │   ├── files.py          # 上传附件存储、路径越界防护与 PDF/Docx/Excel/CSV/文本解析
│   │   ├── schemas.py        # ChatRequest / AgentInput / RunState / RunStep / encode_chat_sse 等契约
│   │   └── prompts/          # tutor_agent.md / compression.md / ltm_update.md
│   ├── resource/             # 独立多模态资源生成模块
│   │   ├── api.py            # 资源任务创建、状态查询、断点续传 SSE、资源列表与详情
│   │   ├── orchestrator.py   # 四阶段 DAG 编排 (Planning → Base 并行 → Aggregation 并行 → Finalize)
│   │   ├── catalog.py        # 7 类资源 Agent 静态元数据目录 (content/mindmap/quiz/code/reading/ppt/cartoon)
│   │   ├── validator.py      # 产物结构确定性校验与上游核心素材提取 (extract_core_content)
│   │   ├── event.py          # 数据库序号持久化的 ResourceEvents SSE 广播通道
│   │   ├── service.py        # 资源任务、AgentRun 与事件持久化服务
│   │   ├── schemas.py        # ResourceGenerationRequest / ResourcePlan / Quiz 确定性蓝图等契约
│   │   └── agents/           # planning 及 7 类资源生成 Agent 实现
│   ├── path/                 # 学习路径规划与节点学习模块
│   │   ├── api.py            # 路径创建、规划 SSE、节点工作区、教程/测验/节点资源接口
│   │   ├── workflows.py      # PathPlannerAgent (research → strategist) 与 NodeLearningAgent 节点学习工作流
│   │   ├── service.py        # 路径、节点、教程、测验与节点辅助资源编排服务
│   │   ├── ppt.py / cartoon.py # 路径节点级 PPT 与教学视频生成适配
│   │   └── event.py          # PathEvents 实时进度通道
│   ├── profile/              # 7 维学习者画像模块 (Onboarding、维度推理评分、AGENT.md 生成、首页推荐与雷达图)
│   ├── quiz/                 # 408 题库检索、客观题提交判分、主观题单题/批量 AI 审阅、错题本管理
│   ├── evaluation/           # 学习行为事件、页面会话时长、7 天窗口事实聚合、评估报告与辅导策略更新
│   ├── shared/               # 跨模块 Agent 共享底座
│   │   ├── tools/            # ToolRegistry、sandbox 路径防护、SkillLoader、subagent 及 7 个 builtin 工具
│   │   ├── ppt/              # PPTAgent (PptxGenJS + LibreOffice + 逐页视觉审查)
│   │   └── cartoon/          # CartoonAgent (HyperFrames CLI + Edge TTS + 关键帧视觉审查 + ffprobe 校验)
│   ├── infra/                # 数据库连接 (database.py)、26 张表定义 (models.py)、LLM 客户端 (llm.py)、日志与种子数据
│   ├── middleware/           # JWTMiddleware
│   ├── config.py             # config.yaml 解析与路径辅助函数
│   ├── exceptions.py         # 全局异常处理器
│   ├── response.py           # HttpResponse 统一 JSON 响应封装
│   ├── routes.py             # 路由集中注册
│   └── main.py               # FastAPI 应用入口与 lifespan 生命周期
├── skills/                   # Agent 技能包 (pptx / hyperframes / hyperframes-cli / hyperframes-registry / media-use)
├── tests/                    # pytest 测试套件 (按业务模块划分)
├── config.example.yaml       # 配置文件模板
├── docker-compose.yml        # 本地开发 MySQL 8.4 容器配置
└── pyproject.toml            # 项目依赖与 pytest 配置
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
