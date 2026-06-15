"""应用生命周期管理模块。

通过 FastAPI 的 lifespan 上下文管理器，在应用启动时执行初始化操作，
在应用关闭时执行清理操作（当前仅实现启动阶段）。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infra.database import check_all, init_db
from app.infra.prompts import prompts


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
