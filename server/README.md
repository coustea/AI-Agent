# Backend Guide

这个目录是项目的 FastAPI 后端，实现认证、聊天、学习路径、资源生成、学习评估、画像、题库和数字人能力。

## 目录概览

```text
server/
├── app/                # 后端源码
├── tests/              # pytest 测试
├── config.yaml         # 运行配置
├── init_schema.sql     # 数据库初始化脚本
├── pyproject.toml      # Python 依赖
├── uv.lock             # 依赖锁文件
└── README.md
```

## 技术栈

- Python 3.13+
- FastAPI
- SQLModel / SQLAlchemy Async
- PostgreSQL + asyncpg
- LangChain
- LangGraph
- uv

## 主要模块

后端业务代码位于 [server/app](/Users/apple/Code/software/server/app)。

### `auth`

认证和用户信息：

- 注册
- 登录
- JWT 校验
- 当前用户信息

### `chat`

智能辅导对话：

- SSE 流式回复
- 文件上传
- 会话管理
- 图片/文档分析
- 搜索增强

### `resource`

独立多智能体资源生成域：

- 多智能体资源任务
- 单智能体资源任务
- 状态查询
- SSE 事件流
- 独立资源历史与详情

### `path`

学习路径规划域：

- 学习路径生成
- 路径历史
- 节点学习空间
- 节点教程
- 节点题目
- 节点辅助资源
- 路径内学习评估

注意：`path` 域与 `resource` 域已经拆分，二者只允许在底层 agent 复用层面有交集，业务记录、展示接口和数据库记录不应混用。

### `evaluation`

学习行为事件与学习评估：

- 学习事件上报
- 用户学习画像增量更新
- 学习信号聚合

### `dashboard`

首页数据聚合：

- 当前路径
- 最近资源
- 最近学习事件
- 推荐动作

### `memory`

用户画像、长期记忆、上下文构建。

### `quiz`

题库与导入逻辑：

- 选择题
- 编程题
- 数据导入

### `avatar`

数字人相关能力。

### `infra`

基础设施：

- 数据库会话
- ORM 模型
- LLM 工厂
- 日志

## 启动方式

### 1. 安装依赖

```bash
cd /Users/apple/Code/software/server
uv sync
```

### 2. 配置 `config.yaml`

后端通过 [server/config.yaml](/Users/apple/Code/software/server/config.yaml) 读取配置，不走 `.env`。

至少要确认这些配置可用：

- `database.url`
- `jwt.secret_key`
- `models.base_url`
- `models.api_key`
- `models.model_name`

如果要启用额外能力，还需要对应配置：

- `models.vision.*`
- `spark.*`
- `avatar.*`
- `search.tavily_key`

### 3. 启动开发服务

```bash
uv run fastapi dev app/main.py
```

默认地址：

- API: `http://localhost:9999`
- Docs: `http://localhost:9999/docs`

## 数据库

### 结构来源

数据库结构脚本：

- [server/init_schema.sql](/Users/apple/Code/software/server/init_schema.sql)

后端启动时不会自动创建完整表结构，默认认为数据库结构已经按 SQL 脚本准备好。后端负责：

- 建立连接
- 执行 CRUD
- 按需导入学校、题库、编程题数据

### 核心表

#### 认证与用户

- `users`
- `active_tokens`

#### 聊天与记忆

- `chat_sessions`
- `chat_messages`
- `user_profiles`
- `user_memories`

#### 独立资源生成

- `generated_resources`
- `generated_resource_items`

#### 学习路径

- `learning_paths`
- `path_nodes`
- `path_node_tutorials`
- `path_node_questions`
- `path_node_resources`

#### 学习评估

- `learning_events`
- `learning_sessions`

#### 题库

- `quiz_questions`
- 相关编程题表

## 启动时会做什么

应用入口在 [server/app/main.py](/Users/apple/Code/software/server/app/main.py)。

服务启动时会：

1. 初始化 prompts
2. 校验数据库连接
3. 执行健康检查
4. 按需导入学校数据
5. 按需导入题库数据
6. 按需导入编程题数据

## API 路由概览

### `/api/v1/users`

- 用户注册
- 登录
- 登出
- 当前用户信息

### `/api/v1/ai/chat/*`

- 聊天流
- 会话
- 历史
- 附件上传

### `/api/v1/ai/resources*`

独立资源生成域：

- `POST /resources`
- `POST /resources/single`
- `GET /resources`
- `GET /resources/{id}`
- `GET /resources/{id}/status`
- `GET /resources/{id}/events`

### `/api/v1/ai/path-plan*`

学习路径域：

- `POST /path-plan`
- `GET /path-plan/active`
- `GET /path-plan/history`
- `POST /path-plan/{path_id}/activate`
- `GET /path-plan/{path_id}`
- `GET /path-plan/nodes/{node_id}/workspace`
- `POST /path-plan/nodes/{node_id}/questions`
- `POST /path-plan/nodes/{node_id}/quiz-submit`
- `POST /path-plan/nodes/{node_id}/resources`
- `GET /path-plan/resources`
- `GET /path-plan/resources/{resource_id}`
- `POST /path-plan/{path_id}/events`
- `GET /path-plan/{path_id}/evaluation`

### `/api/v1/ai/dashboard/*`

- 首页聚合数据

### `/api/v1/ai/profile*`

- 用户画像
- 历史画像

### `/api/v1/ai/evaluation*`

- 学习事件
- 学习摘要

## 路径规划与资源生成的边界

这是当前后端设计里最重要的一条规则。

### 独立资源生成

适用于：

- 用户直接说“给我生成一个教程/导图/PPT/代码示例”
- 不依赖某条学习路径的上下文

特点：

- 使用 `generated_resources`
- 详情页是独立资源详情
- API 走 `/resources`

### 路径节点资源

适用于：

- 用户已经在某条学习路径里
- 围绕某个节点生成思维导图、PPT、代码示例
- 节点内题目和教程的学习闭环

特点：

- 使用 `path_node_resources`
- 属于路径节点学习空间
- API 走 `/path-plan`

不要把这两种资源写进同一张记录表，也不要用同一组展示接口。

## 测试

### 运行全部测试

```bash
uv run pytest
```

### 运行部分测试

```bash
uv run pytest tests/path -q
uv run pytest tests/resource -q
uv run pytest tests/dashboard -q
```

## 常用开发命令

```bash
uv sync
uv run fastapi dev app/main.py
uv run pytest
```

## 开发约定

### 1. 配置读取

统一从 [server/app/config.py](/Users/apple/Code/software/server/app/config.py) 读取，不要在业务代码里直接硬编码配置。

### 2. 数据库初始化

结构变更优先修改：

- [server/init_schema.sql](/Users/apple/Code/software/server/init_schema.sql)
- [server/app/infra/models.py](/Users/apple/Code/software/server/app/infra/models.py)

### 3. 路径规划重构时的注意点

- 不要再引入旧 `course_path_*` 风格兼容逻辑
- 不要把路径资源和独立资源重新合并
- 不要为旧接口保留无意义的转发壳

### 4. 测试策略

优先为这些层补测试：

- API 层
- Service 层
- 路径规划与资源分离的回归场景

## 故障排查

### 启动时报数据库错误

先检查：

1. `config.yaml` 的 `database.url`
2. PostgreSQL 是否已启动
3. 是否已经执行过 `init_schema.sql`

### 首页 500

优先检查：

- dashboard 聚合查询是否访问了不存在的表/字段
- 最近一次路径规划或资源生成重构是否改坏了聚合模型

### 路径规划异常

优先检查：

- `learning_paths` 及其子表结构
- `/api/v1/ai/path-plan/*` 接口是否和前端字段一致
- 节点教程、题目、资源是否仍然误走了独立资源域
