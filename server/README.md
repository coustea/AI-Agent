# AI Learning Platform - Server

基于多智能体架构的个性化学习资源生成系统后端。

## 技术栈

- **Python 3.13** + **uv** 包管理
- **FastAPI** - Web 框架
- **LangChain** - LLM 编排
- **LangGraph** - 多智能体图编排
- **SQLModel** - ORM

## 项目结构

```
app/
  main.py                     # FastAPI 入口
  core/                       # 共享基础设施
    config.py                 # 配置管理
    database.py               # 数据库连接
    llm.py                    # LLM 客户端
    security.py               # 内容安全过滤
    streaming.py              # SSE 流式输出
    dependencies.py           # FastAPI 依赖注入
    types.py                  # 共享类型/枚举
  models/                     # SQLModel 数据模型
  modules/                    # 功能模块
    profile_builder/          # 对话式学习画像构建
    resource_generator/       # 多智能体资源生成
      agents/                 # 子智能体（文档/思维导图/题库/阅读/视频/代码）
    path_planner/             # 学习路径规划
    tutor/                    # 智能辅导
    assessment/               # 学习效果评估
  api/v1/                     # 路由聚合
tests/                        # 测试
```

## 快速开始

```bash
# 安装依赖
uv sync

# 启动开发服务
uv run fastapi dev app/main.py

# 或使用 uvicorn
uv run uvicorn app.main:app --reload
```

启动后访问 `http://localhost:8000/docs` 查看 API 文档。

## 环境变量

复制 `.env.example` 为 `.env` 并填写：

```
DATABASE_URL=sqlite:///./data.db
LLM_API_KEY=your-api-key
LLM_MODEL_NAME=your-model-name
```

## 开源依赖

| 项目 | 协议 | 用途 |
|------|------|------|
| FastAPI | MIT | Web 框架 |
| LangChain | MIT | LLM 编排 |
| LangGraph | MIT | 多智能体图编排 |
| SQLModel | MIT | ORM |
