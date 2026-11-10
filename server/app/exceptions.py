"""全局异常处理模块。

将各种异常统一转换为标准的 JSON 响应格式（HttpResponse 包装），
确保前端始终收到结构一致的错误信息，并在日志中完整追踪错误链路。
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.auth.security import AuthError
from app.infra.logging import get_logger
from app.response import HttpResponse

logger = get_logger("exceptions")


async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    """处理认证与授权业务异常，记录警告日志并返回格式化响应。"""
    logger.warning(
        "[Exception] AuthError: path={} message={} field={} code={}",
        request.url.path,
        exc.message,
        exc.field,
        exc.code,
    )
    data = {"field": exc.field} if exc.field else None
    return HttpResponse.error(code=exc.code, message=exc.message, data=data)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理 FastAPI 内置 HTTPException 并记录警告日志。"""
    logger.warning(
        "[Exception] HTTPException: path={} status={} detail={}",
        request.url.path,
        exc.status_code,
        exc.detail,
    )
    return HttpResponse.error(code=exc.status_code, message=str(exc.detail))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的服务端兜底异常，记录堆栈日志并返回 500 响应。"""
    logger.exception(
        "[Exception] 全局未捕获异常: path={} error={}",
        request.url.path,
        exc,
    )
    return HttpResponse.error(code=500, message="服务器内部错误，请稍后重试")


def install_exception_handlers(app: FastAPI) -> None:
    """向 FastAPI 应用注册全局异常处理器。"""
    app.add_exception_handler(AuthError, auth_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
