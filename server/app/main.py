"""FastAPI 应用入口文件。

负责创建和配置 FastAPI 应用实例，包括生命周期管理、中间件、异常处理、路由注册等。
支持通过命令行直接运行开发服务器。
"""

# 本模块是服务入口：定义应用生命周期、创建 FastAPI 实例并挂载路由/中间件/静态资源
from __future__ import annotations

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import KB_ENABLED, KB_EMBED_MODEL, WORKPLACE_DIR
from app.exceptions import install_exception_handlers
from app.infra.database import check_all, init_db
from app.infra.logging import configure_logging, get_logger
from app.infra.prompts import prompts
from app.routes import install_routes
from app.rag.retriever import check_index_health


@asynccontextmanager
# 应用生命周期管理器：启动阶段预热提示词、初始化数据库与知识库，关闭阶段暂留空
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

    # 知识库索引状态检查（不自动构建，构建请执行: python -m app.rag）
    log = get_logger("main")
    if not KB_ENABLED:
        log.info("[KB] 知识库已在配置中禁用")
    else:
        try:
            health = check_index_health()
            if health.ready:
                log.info(
                    "[KB] 知识检索可用: %d 个分块, 嵌入模型=%s",
                    health.chunk_count,
                    KB_EMBED_MODEL,
                )
            else:
                log.warning(
                    "[KB] 知识检索不可用 (原因: %s, 嵌入模型=%s)。"
                    "请执行 python -m app.rag 构建索引",
                    health.reason,
                    KB_EMBED_MODEL,
                )
        except Exception as exc:
            log.error("[KB] 索引检查失败: %s", exc, exc_info=True)

    log.info("[Main] 应用启动完成，开始接受请求")

    # yield 将控制权交给 FastAPI 应用，开始处理请求
    yield

    # 应用关闭时的清理逻辑
    log.info("[Main] 应用正在关闭，开始清理资源")


# 创建并配置 FastAPI 应用实例：日志、CORS、异常处理器、静态目录与路由注册
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
# 模块级应用实例，作为 ASGI 入口被服务器加载
app = create_app()


def main() -> None:
    """命令行入口：启动开发服务器。

    使用方式：
        python -m app.main
        python app/main.py

    生产环境请使用 uvicorn app.main:app --host 0.0.0.0 --port 9999
    """
    import uvicorn

    from app.config import HOST, PORT

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=True,
        reload_dirs=["app"],
    )


if __name__ == "__main__":
    main()

