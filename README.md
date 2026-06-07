# AI Learning Platform

一个面向学习场景的全栈 AI 系统，包含：

- Vue 3 + TypeScript 前端
- FastAPI + SQLModel 后端
- 多智能体学习资源生成
- 学习路径规划与节点学习
- 智能辅导、用户画像、学习评估、题库

当前项目已经将两类能力明确分开：

- `资源生成`：独立的多智能体资源生产链路
- `路径规划`：先生成学习路径，再围绕路径节点按需生成教程、题目和辅助资源

## 目录结构

```text
software/
├── src/                 # 前端源码
├── public/              # 前端静态资源
├── server/              # FastAPI 后端
├── docs/                # 项目文档
├── dist/                # 前端构建产物
└── openspec/            # 变更设计与实现记录
```

## 核心能力

### 1. 智能辅导

- 流式对话
- 文件/图片辅助分析
- 会话历史管理
- 学习画像驱动的上下文构建

### 2. 多智能体资源生成

- 独立资源生成任务
- 单智能体资源生成任务
- 支持内容、思维导图、题目、代码示例、阅读材料、PPT
- 任务状态查询与 SSE 事件流

### 3. 学习路径规划

- 用户先输入学习目标生成路径
- 路径由阶段和节点组成
- 节点首次进入时生成教程
- 节点内固定 5 道选择题
- 先错题知识点专项巩固，再强化教程
- 路径资源记录与独立资源记录分离

### 4. 用户画像与学习评估

- 基于聊天、学习事件、题目表现沉淀画像
- 聚合学习事件、学习时长、薄弱点
- 为首页和路径评估提供动态推荐信号

### 5. 题库与练习

- 通用题库
- 编程题与选择题导入
- 路径节点内 AI 在线生成题目

## 前端说明

前端位于 [src](/Users/apple/Code/software/src)。

### 主要页面

- `/login`：登录
- `/register`：注册
- `/dashboard`：首页总览
- `/tutor`：智能辅导
- `/resource-generator`：独立资源生成
- `/resource-history` / `/resource-detail/:id`：独立资源历史与详情
- `/path-planner`：学习路径创建入口
- `/path-planner/overview/:id?`：路径总览
- `/path-planner/node/:nodeId`：节点学习页
- `/path-planner/history`：路径历史
- `/path-resource-history` / `/path-resource/:id`：路径资源历史与详情
- `/question-bank`：题库
- `/profile`：画像页

### 前端技术栈

- Vue 3
- TypeScript
- Vue Router
- Element Plus
- Axios
- ECharts

### 前端启动

```bash
npm install
npm run dev
```

默认开发地址：

- Frontend: `http://localhost:5173`

### 前端构建

```bash
npm run build
```

## 后端说明

后端位于 [server](/Users/apple/Code/software/server)。

后端详细说明见：

- [server/README.md](/Users/apple/Code/software/server/README.md)

### 后端技术栈

- FastAPI
- SQLModel / SQLAlchemy Async
- PostgreSQL
- LangChain
- LangGraph
- uv

### 后端启动

```bash
cd server
uv sync
uv run fastapi dev app/main.py
```

默认开发地址：

- Backend API: `http://localhost:9999`
- Swagger: `http://localhost:9999/docs`

## 当前业务边界

这是项目里最容易混淆、但现在必须保持清晰的部分。

### 独立资源生成

面向通用学习需求，走 `resource` 域：

- 任务记录存在 `GeneratedResource` / `GeneratedResourceItem`
- 页面是 `ResourceGenerator`、`ResourceHistory`、`ResourceDetail`
- 接口前缀是 `/api/v1/ai/resources`

### 路径规划资源

面向学习路径节点，走 `path` 域：

- 路径、节点、教程、题目、辅助资源独立存储
- 页面是 `LearningPath*` 和 `PathResource*`
- 接口前缀是 `/api/v1/ai/path-plan`

除了底层可复用的资源生成 agent 之外，两条业务链路不应复用同一套记录展示页，也不应混用资源历史。

## 配置与环境

### 前端

前端目前主要依赖 Vite 本地开发配置，无单独环境变量文档。

### 后端

后端配置文件是：

- [server/config.yaml](/Users/apple/Code/software/server/config.yaml)

其中包含：

- `app`
- `database`
- `jwt`
- `models`
- `spark`
- `avatar`
- `search`
- `knowledge`
- `memory`
- `chat`

注意：

- 不要在公开环境提交真实密钥
- 生产环境应替换 `config.yaml` 中的数据库、JWT 和模型配置

## 数据库

数据库结构初始化脚本位于：

- [server/init_schema.sql](/Users/apple/Code/software/server/init_schema.sql)

当前后端默认使用 PostgreSQL 异步驱动 `asyncpg`。

学习路径相关的核心表包括：

- `learning_paths`
- `path_nodes`
- `path_node_tutorials`
- `path_node_questions`
- `path_node_resources`

独立资源生成相关核心表包括：

- `generated_resources`
- `generated_resource_items`

## 开发命令

### 前端

```bash
npm run dev
npm run build
npm run preview
```

### 后端

```bash
cd server
uv sync
uv run fastapi dev app/main.py
uv run pytest
```

## 测试与验证

### 后端测试

```bash
cd server
uv run pytest
```

### 前端检查

```bash
npm run build
```

如果前端构建失败，优先检查：

- TypeScript 类型错误
- 新增依赖是否已安装
- 资源组件是否引入了缺失模块

## 推荐阅读顺序

如果你是第一次接手这个仓库，建议按这个顺序看：

1. [README.md](/Users/apple/Code/software/README.md)
2. [server/README.md](/Users/apple/Code/software/server/README.md)
3. [src/router/index.ts](/Users/apple/Code/software/src/router/index.ts)
4. [server/app/main.py](/Users/apple/Code/software/server/app/main.py)
5. [server/init_schema.sql](/Users/apple/Code/software/server/init_schema.sql)

## 额外说明

- 当前项目里存在历史设计文档、OpenSpec 变更记录和实验性目录，阅读时以真实代码路径为准
- 路径规划和多智能体资源生成正在持续拆边界，新增功能时不要再把两者的记录页、详情页和数据库记录混在一起
