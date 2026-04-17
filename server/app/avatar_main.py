# -*- coding: utf-8 -*-
"""
Avatar Bridge 独立进程入口

启动 WebSocket 服务 (:8765)，处理数字人实时交互。
与主服务 (:9999) 共享数据库和代码模块。

启动方式：
    cd server && python avatar_main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 修正路径：从 app/avatar_main.py 向上两级到 server 目录
SERVER_DIR = Path(__file__).resolve().parent.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import asyncio
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query

load_dotenv()

from app.infra.logging import get_logger, setup_logging
from app.infra.database import init_db
from app.auth.security import decode_token
from app.avatar.bridge.manager import avatar_bridge_manager
from app.config import AVATAR_BRIDGE_PORT

logger = get_logger(__name__)

avatar_app = FastAPI(title="Avatar Bridge Service")


@avatar_app.websocket("/ws/avatar")
async def avatar_websocket(
    ws: WebSocket,
    token: str = Query(..., description="JWT token"),
):
    """WebSocket 端点 — JWT 认证"""
    # 1. 验证 JWT
    try:
        user_id = decode_token(token)
    except Exception:
        await ws.close(code=4001, reason="认证失败")
        return

    # 2. 接受连接
    await ws.accept()
    logger.info("[AvatarBridge] 用户 %d 已连接", user_id)

    # 3. 获取/创建 bridge
    bridge = await avatar_bridge_manager.get_or_create_bridge(user_id)

    try:
        await bridge.handle_frontend(ws)
    except WebSocketDisconnect:
        logger.info("[AvatarBridge] 用户 %d 已断开", user_id)
    except Exception as e:
        logger.error("[AvatarBridge] 连接异常: %s", e)
    finally:
        # 不销毁 bridge，保留 AvatarController 连接
        pass


@avatar_app.get("/health")
async def health():
    return {"status": "ok", "service": "avatar-bridge"}


@avatar_app.on_event("startup")
async def startup():
    setup_logging()
    await init_db()
    logger.info("[AvatarBridge] 服务启动，端口 %d", AVATAR_BRIDGE_PORT)


if __name__ == "__main__":
    uvicorn.run(avatar_app, host="0.0.0.0", port=AVATAR_BRIDGE_PORT)
