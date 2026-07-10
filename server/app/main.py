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

from app.config import KB_AUTO_BUILD, KB_ENABLED, KB_EMBED_MODEL, WORKPLACE_DIR
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

    # 知识库索引检查 + 自动构建
    log = get_logger("main")
    if not KB_ENABLED:
        log.info("[KB] 知识库已在配置中禁用")
    else:
        try:
            health = check_index_health()
            if health.ready:
                log.info(
                    "[KB] 索引就绪: %d 个分块, 嵌入模型=%s",
                    health.chunk_count,
                    KB_EMBED_MODEL,
                )
            else:
                needs_rebuild = KB_AUTO_BUILD
                # 嵌入模型变更 → 必须重建（即使 auto_build=False 也提示）
                if "embedding_model_mismatch" in health.reason:
                    log.warning(
                        "[KB] 嵌入模型已变更 (配置=%s), 索引需要重建 (原因: %s)",
                        KB_EMBED_MODEL,
                        health.reason,
                    )
                    needs_rebuild = True
                else:
                    log.info(
                        "[KB] 索引未就绪 (原因: %s)%s",
                        health.reason,
                        ", 正在后台自动构建..." if needs_rebuild else "",
                    )

                if needs_rebuild:
                    import threading
                    from app.rag.indexing.build import build_index

                    # 后台线程：检查嵌入模型可用后构建知识库索引并重置检索缓存
                    def _bg_build() -> None:
                        log.info("[KB] 自动构建开始 (嵌入模型=%s)...", KB_EMBED_MODEL)

                        # 先检查嵌入模型是否可用，不可用则跳过构建
                        from app.rag.embeddings import embed_query

                        test_embedding = embed_query("test")
                        if test_embedding is None:
                            log.error(
                                "[KB] 自动构建已跳过: 嵌入模型不可用。"
                                "请检查嵌入服务配置 (knowledge.embed_base_url)。"
                            )
                            return

                        try:
                            build_index()
                            # 重置 BM25 懒加载单例，使后续检索能加载新索引
                            from app.rag.bm25 import reset_bm25_index
                            reset_bm25_index()
                            # 验证构建结果
                            post_health = check_index_health()
                            if post_health.ready:
                                log.info(
                                    "[KB] 自动构建成功: %d 个分块, 嵌入模型=%s",
                                    post_health.chunk_count,
                                    KB_EMBED_MODEL,
                                )
                            else:
                                log.error(
                                    "[KB] 自动构建完成但健康检查失败: %s",
                                    post_health.reason,
                                )
                        except Exception as exc:
                            log.error("[KB] 自动构建失败: %s", exc, exc_info=True)

                    t = threading.Thread(target=_bg_build, daemon=True)
                    t.start()
                else:
                    log.warning(
                        "[KB] 索引未就绪且自动构建已禁用, 知识检索不可用"
                    )
        except Exception as exc:
            log.error("[KB] 索引检查失败: %s", exc, exc_info=True)

    # yield 将控制权交给 FastAPI 应用，开始处理请求
    yield

    # 应用关闭时的清理逻辑（暂未实现）


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

