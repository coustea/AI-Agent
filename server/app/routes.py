"""路由注册模块。

集中管理所有 API 路由的注册，按业务模块分组挂载到不同的 URL 前缀下。
"""

from __future__ import annotations

from fastapi import FastAPI

# 导入各业务模块的路由
# 用户认证路由
from app.auth.api import router as auth_router
# 数字人路由
from app.avatar.api import router as avatar_router
# AI 聊天路由
from app.chat.api import router as chat_router
# 仪表盘路由
from app.dashboard.api import router as dashboard_router
# 评估路由
from app.evaluation.api import router as evaluation_router
# 学习路径路由
from app.path.api import router as path_router
# 学习资源路由
from app.resource.api import router as resource_router
# WebSocket 路由
from app.ws import router as websocket_router

# 测验与错题本路由
from app.profile.api import router as profile_router
from app.quiz.api import router as quiz_router
from app.shared.cartoon.api import router as cartoon_router


def install_routes(app: FastAPI) -> None:
    """向 FastAPI 应用注册所有业务路由。

    每个路由模块挂载到对应的 URL 前缀下，并添加 tags 标签
    用于 Swagger/OpenAPI 文档分组。

    Args:
        app: FastAPI 应用实例
    """
    # 用户认证模块：/api/v1/users/*
    app.include_router(auth_router, prefix="/api/v1/users", tags=["users"])
    # AI 聊天模块：/api/v1/ai/chat/*
    app.include_router(chat_router, prefix="/api/v1/ai", tags=["ai"])
    # 仪表盘模块：/api/v1/ai/dashboard/*
    app.include_router(dashboard_router, prefix="/api/v1/ai", tags=["dashboard"])
    # 学习资源模块：/api/v1/ai/resource/*
    app.include_router(resource_router, prefix="/api/v1/ai", tags=["resource"])
    # 学习路径模块：/api/v1/ai/path/*
    app.include_router(path_router, prefix="/api/v1/ai", tags=["path"])
    # 学习评估模块：/api/v1/ai/evaluation/*
    app.include_router(evaluation_router, prefix="/api/v1/ai", tags=["evaluation"])
    # 数字人模块：/api/v1/ai/avatar/*
    app.include_router(avatar_router, prefix="/api/v1/ai", tags=["avatar"])
    # 测验与错题本模块：/api/v1/ai/quiz-bank/*, /api/v1/ai/wrong-questions/*
    app.include_router(profile_router, prefix="/api/v1/ai", tags=["profile"])
    app.include_router(quiz_router, prefix="/api/v1/ai", tags=["quiz"])
    # 动画卡通视频生成模块：/api/v1/ai/cartoon/*
    app.include_router(cartoon_router, prefix="/api/v1/ai/cartoon", tags=["cartoon"])
    # WebSocket 模块：/ws/*
    app.include_router(websocket_router)
