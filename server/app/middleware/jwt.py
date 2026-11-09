"""JWT 认证中间件：负责全局统一提取 Token、拦截未授权请求并注入协程上下文。"""

from __future__ import annotations

import inspect
from contextvars import ContextVar
import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.auth.schemas import UserClaims
from app.config import JWT_ALGO, JWT_SECRET
from app.infra.logging import get_logger

logger = get_logger(__name__)

# 全局协程安全的用户上下文变量
current_user_ctx: ContextVar[UserClaims | None] = ContextVar("current_user", default=None)

# 免认证公开接口白名单
PUBLIC_EXACT_PATHS: frozenset[str] = frozenset({
    "/api/v1/users",             # POST 用户注册
    "/api/v1/users/auth",        # POST 用户登录
    "/api/v1/users/auth/logout", # POST 登出
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
})

PUBLIC_PREFIX_PATHS: tuple[str, ...] = (
    "/static/",
    "/docs",
    "/redoc",
)


def is_public_path(path: str) -> bool:
    """判断请求路径是否属于免认证公开接口。"""
    if path in PUBLIC_EXACT_PATHS:
        return True
    if any(path.startswith(prefix) for prefix in PUBLIC_PREFIX_PATHS):
        return True
    # 任何非 /api/v1/ 开头的非业务路径（如测试路由 /test-echo 或健康探针）放行
    if not path.startswith("/api/v1/"):
        return True
    return False


class JWTMiddleware(BaseHTTPMiddleware):
    """全局 JWT 统一拦截与身份上下文注入中间件。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        """拦截请求，校验受保护端点并挂载全局 UserClaims 上下文。"""
        # CORS OPTIONS 预检请求直接放行
        if request.method == "OPTIONS":
            return await call_next(request)

        # 若外部环境或测试已提前设置上下文，优先沿用
        claims: UserClaims | None = current_user_ctx.get()

        # 0. 支持测试环境通过 app.dependency_overrides 模拟登录
        if claims is None and hasattr(request.app, "dependency_overrides"):
            from app.auth.security import get_current_user
            override = request.app.dependency_overrides.get(get_current_user)
            if override is not None:
                res = override()
                if inspect.isawaitable(res):
                    res = await res
                if isinstance(res, UserClaims):
                    claims = res
                elif hasattr(res, "id") and hasattr(res, "username"):
                    claims = UserClaims(
                        id=res.id,
                        username=res.username,
                        email=getattr(res, "email", None),
                        role=getattr(res, "role", "user"),
                        onboarding_completed=getattr(res, "onboarding_completed", False),
                    )

        # 1. 提取 Token：优先 Authorization Header (Bearer)，回落 Query 参数 (token)
        if claims is None:
            token: str | None = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
            if not token:
                token = request.query_params.get("token")

            # 2. 校验并解析 Token
            if token:
                try:
                    payload = jwt.decode(
                        token,
                        JWT_SECRET or "dev-secret-change-in-production-long-enough",
                        algorithms=[JWT_ALGO],
                    )
                    claims = UserClaims.model_validate(payload)
                except Exception as exc:
                    logger.debug("[JWTMiddleware] Token 无效: path=%s reason=%s", request.url.path, exc)

        # 3. 校验受保护路由：非白名单且无合法身份时，直接在中间件层阻断返回 401
        path = request.url.path
        if not is_public_path(path) and claims is None:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "message": "未登录或登录已过期", "data": None},
            )

        # 4. 将解析出的身份挂载至请求上下文与协程 ContextVar
        request.state.user = claims
        token_ctx = current_user_ctx.set(claims)
        try:
            return await call_next(request)
        finally:
            current_user_ctx.reset(token_ctx)
