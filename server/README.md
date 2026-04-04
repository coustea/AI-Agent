# AI Learning Platform - Server

基于多智能体架构的个性化学习资源生成系统后端。

## 技术栈

- **Python 3.13** + **uv** 包管理
- **FastAPI** - Web 框架
- **SQLModel** - ORM（SQLAlchemy + Pydantic）
- **MySQL** - 数据库（PyMySQL 驱动）
- **Redis** - Token 白名单管理
- **PyJWT + bcrypt** - 认证与密码加密
- **LangChain / LangGraph** - LLM 编排与多智能体（规划中）

## 项目结构

```
server/
├── app/
│   ├── main.py                     # FastAPI 入口，全局异常处理
│   ├── core/                       # 共享基础设施
│   │   ├── engine.py               # MySQL + Redis 连接，数据库初始化
│   │   ├── security.py             # JWT 认证、密码哈希、get_current_user
│   │   ├── logging.py              # 日志配置（文件输出，按天/大小轮转）
│   │   ├── response.py             # HttpResponse 统一响应封装
│   │   └── dependencies.py         # get_session 依赖注入
│   ├── models/                     # SQLModel 数据模型
│   │   ├── user.py                 # 用户表
│   │   ├── common.py               # 用户记忆表
│   │   └── profile_builder.py      # 用户画像表、画像历史表
│   └── modules/                    # 功能模块
│       ├── user/                   # 用户认证模块
│       │   ├── router.py           # RESTful 路由
│       │   ├── service.py          # 业务逻辑
│       │   └── schemas.py          # 请求/响应模型
│       ├── profile_builder/        # 对话式学习画像构建（规划中）
│       ├── resource_generator/     # 多智能体资源生成（规划中）
│       ├── path_planner/           # 学习路径规划（规划中）
│       ├── tutor/                  # 智能辅导（规划中）
│       └── assessment/             # 学习效果评估（规划中）
├── logs/                           # 日志文件（gitignore）
├── .env                            # 环境变量
└── pyproject.toml
```

## 快速开始

```bash
# 安装依赖
uv sync

# 启动开发服务
uv run fastapi dev app/main.py

# 或直接运行（端口 9999）
uv run python app/main.py
```

启动后访问 http://localhost:9999/docs 查看 API 文档。

## API 路由

所有路由挂载在 `/api/v1` 下：

| 方法   | 路径                    | 说明             | 需认证 |
|--------|-------------------------|------------------|--------|
| POST   | /api/v1/users           | 注册新用户       | 否     |
| POST   | /api/v1/users/auth      | 登录             | 否     |
| DELETE | /api/v1/users/auth      | 登出             | 是     |
| GET    | /api/v1/users/me        | 获取当前用户信息 | 是     |
| PATCH  | /api/v1/users/me        | 更新当前用户信息 | 是     |

所有响应使用统一格式：`{"code": 200, "message": "...", "data": {...}}`

## 环境变量

`.env` 文件放在 `server/` 目录下：

```env
# 应用配置（true 时启动会重建所有表，生产环境设为 false）
APP_DEBUG=true

# 数据库
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=agent
DB_ECHO=false

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7
```

## 日志

日志输出到 `server/logs/` 目录（仅文件，不输出到控制台）：

- `app.log` — 全量日志（INFO+），按天轮转，保留 30 天
- `error.log` — 错误日志（ERROR+），按 10MB 轮转，保留 10 份

## 开源依赖

| 项目      | 协议 | 用途         |
|-----------|------|--------------|
| FastAPI   | MIT  | Web 框架     |
| SQLModel  | MIT  | ORM          |
| PyJWT     | MIT  | JWT 认证     |
| passlib   | MIT  | 密码哈希     |
| redis     | MIT  | Redis 客户端 |
| LangChain | MIT  | LLM 编排     |
| LangGraph | MIT  | 多智能体编排 |
