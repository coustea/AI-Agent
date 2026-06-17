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
- 支持内容、思维导图、题目、代码示例、阅读材料、PPT
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

## 前端说明

前端位于 `src/`。

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

### 前端启动

```bash
npm install
npm run dev
```

### 前端构建

```bash
npm run build
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

### 后端启动

```bash
cd server
uv sync
uv run fastapi dev app/main.py --port 9999
```

### 配置

后端所有配置在 `server/config.yaml`，关键配置项：

| 配置族 | 说明 |
|--------|------|
| `app` | 应用端口、调试模式 |
| `database` | PostgreSQL 连接串 |
| `jwt` | JWT 密钥、过期时间 |
| `models` | LLM API 地址、密钥、模型名 |
| `vision` | 视觉模型（独立配置） |
| `spark` | 星火 WebSocket API |
| `avatar` | 讯飞数字人 |
| `search` | Tavily / 星火搜索 |
| `knowledge` | 向量检索（Ollama + ChromaDB） |
| `memory` | 记忆压缩参数 |
| `chat` | 附件限制参数 |

**注意**：不要在公开环境提交真实密钥。

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

## 开发命令

### 前端

```bash
npm run dev      # 启动开发服务器
npm run build    # 类型检查 + 构建
npm run preview  # 预览构建产物
```

### 后端

```bash
cd server
uv sync                                              # 安装依赖
uv run fastapi dev app/main.py --port 9999           # 开发服务器
uv run pytest                                         # 全部测试
uv run pytest tests/chat -q                           # 指定模块测试
uv run pytest -x                                      # 首个失败即停止
```

## 端口配置

| 服务 | 端口 |
|------|------|
| Frontend (Vite) | 5173 |
| Backend (FastAPI) | 9999 |
| API Docs (Swagger) | 9999/docs |

Vite 代理：`/api` → `http://127.0.0.1:9999`，`/ws` → `ws://127.0.0.1:9999`

## 推荐阅读顺序

1. 本文件 `README.md`
2. [server/README.md](server/README.md)
3. [src/app/router/routes.ts](src/app/router/routes.ts)（前端路由）
4. [server/app/main.py](server/app/main.py)（后端入口）
5. [server/app/routes.py](server/app/routes.py)（后端路由挂载）
6. [server/init_schema.sql](server/init_schema.sql)（数据库结构）
