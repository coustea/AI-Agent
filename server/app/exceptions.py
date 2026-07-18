"""全局异常处理模块。

将各种异常统一转换为标准的 JSON 响应格式（HttpResponse 包装），
确保前端始终收到结构一致的错误信息。
"""

# 本模块定义全局异常处理器，将 AuthError 与 HTTPException 统一包装为标准响应
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.auth.security import AuthError
from app.infra.logging import get_logger
from app.infra.response import HttpResponse

logger = get_logger(__name__)


# 处理认证错误，将 AuthError 转换为 HTTP 401 标准响应
async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    """处理认证错误：将 AuthError 转换为 HTTP 401 标准响应。

    当 JWT Token 无效、过期或用户不存在时触发。
    """
    logger.warning("[Exception] AuthError: path=%s message=%s", request.url.path, exc.message)
    return HttpResponse.error(code=401, message=exc.message)


# 处理 FastAPI 内置 HTTPException，映射到统一错误响应格式
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理 FastAPI 内置 HTTPException。

    将 status_code 和 detail 映射到统一的错误响应格式。
    """
    logger.warning("[Exception] HTTPException: path=%s status=%s detail=%s", request.url.path, exc.status_code, exc.detail)
    return HttpResponse.error(code=exc.status_code, message=str(exc.detail))


# 向 FastAPI 应用注册全局异常处理器
def install_exception_handlers(app: FastAPI) -> None:
    """向 FastAPI 应用注册全局异常处理器。

    Args:
        app: FastAPI 应用实例
    """
    # 注册自定义认证错误处理器
    app.add_exception_handler(AuthError, auth_error_handler)
    # 注册 FastAPI 内置 HTTP 异常处理器
    app.add_exception_handler(HTTPException, http_exception_handler)
