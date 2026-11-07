"""JWT 认证中间件：负责全局统一提取 Token 并将 UserClaims 注入请求上下文。"""

from __future__ import annotations

import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.auth.schemas import UserClaims
from app.config import JWT_ALGO, JWT_SECRET
from app.infra.logging import get_logger

logger = get_logger(__name__)


class JWTMiddleware(BaseHTTPMiddleware):
    """全局 JWT 统一拦截与身份上下文注入中间件。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        """拦截请求，统一从 Header 或 Query 参数中提取并校验 Token，挂载 UserClaims。"""
        token: str | None = None

        # 1. 提取 Token：优先 Authorization Header (Bearer)，回落 Query 参数 (token)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        if not token:
            token = request.query_params.get("token")

        # 2. 校验并解析 Token
        claims: UserClaims | None = None
        if token:
            try:
                payload = jwt.decode(
                    token,
                    JWT_SECRET or "dev-secret-change-in-production-long-enough",
                    algorithms=[JWT_ALGO],
                )
                claims = UserClaims.model_validate(payload)
            except jwt.ExpiredSignatureError:
                logger.debug("[JWTMiddleware] Token 已过期: path=%s", request.url.path)
            except (jwt.PyJWTError, Exception) as exc:
                logger.debug("[JWTMiddleware] Token 无效: path=%s reason=%s", request.url.path, exc)

        # 3. 将解析出的身份挂载至请求上下文
        request.state.user = claims

        return await call_next(request)
