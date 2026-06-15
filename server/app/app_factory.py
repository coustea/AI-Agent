"""FastAPI 应用工厂模块。

负责创建和配置 FastAPI 应用实例，包括中间件、异常处理、路由注册等。
采用工厂模式，便于测试和多环境部署。
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import DEBUG
from app.exceptions import install_exception_handlers
from app.infra.logging import configure_logging
from app.lifecycle import lifespan
from app.routes import install_routes


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。

    初始化步骤：
    1. 配置日志系统
    2. 创建 FastAPI 实例（绑定生命周期钩子）
    3. 添加 CORS 中间件（允许跨域请求）
    4. 安装全局异常处理器
    5. 注册所有 API 路由
    """
    # 配置日志输出格式和级别
    configure_logging(debug=DEBUG)

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

    # 注册所有业务路由（auth、chat、resource、path 等）
    install_routes(app)

    return app
