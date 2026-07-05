"""FastAPI 应用入口文件。

负责创建和配置 FastAPI 应用实例，包括生命周期管理、中间件、异常处理、路由注册等。
支持通过命令行直接运行开发服务器。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import WORKPLACE_DIR
from app.exceptions import install_exception_handlers
from app.infra.database import check_all, init_db
from app.infra.logging import configure_logging
from app.infra.prompts import prompts
from app.routes import install_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 应用生命周期管理器。

    启动阶段（yield 之前）：
    1. 预热所有提示词模板（避免首次请求时的延迟）
    2. 初始化数据库连接（创建表、建立连接池）
    3. 执行数据库健康检查

    关闭阶段（yield 之后）：
    - 当前未实现清理逻辑，可在此添加关闭连接池等操作
    """
    # 预热所有提示词模板，将其编译并缓存
    prompts.warm_all()
    # 初始化数据库：创建表结构（如果不存在）
    await init_db()
    # 执行数据库连接检查，确保连接可用
    await check_all()

    # yield 将控制权交给 FastAPI 应用，开始处理请求
    yield

    # 应用关闭时的清理逻辑（暂未实现）


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。

    初始化步骤：
    1. 配置日志系统
    2. 创建 FastAPI 实例（绑定生命周期钩子）
    3. 添加 CORS 中间件（允许跨域请求）
    4. 安装全局异常处理器
    5. 注册所有 API 路由
    """
    # 配置日志输出格式和级别（统一输出关键日志）
    configure_logging()

    # 创建 FastAPI 实例，绑定 lifespan 生命周期管理器
    app = FastAPI(title="AI Learning Platform", lifespan=lifespan)

    # 添加 CORS 中间件，允许前端跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],        # 允许所有来源（生产环境应限制具体域名）
        allow_credentials=True,      # 允许携带 Cookie / Authorization
        allow_methods=["*"],         # 允许所有 HTTP 方法
        allow_headers=["*"],         # 允许所有请求头
    )

    # 注册全局异常处理器（AuthError、HTTPException 等）
    install_exception_handlers(app)

    # 确保 workplace 目录存在，并挂载静态文件目录
    WORKPLACE_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(WORKPLACE_DIR)), name="static")

    # 注册所有业务路由（auth、chat、resource、path 等）
    install_routes(app)

    return app


# 创建 FastAPI 应用实例（供 uvicorn / gunicorn 等 ASGI 服务器加载）
app = create_app()

