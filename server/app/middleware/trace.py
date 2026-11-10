"""全链路请求追踪与 HTTP 访问日志中间件。

负责在请求生命周期入口注入 Trace ID，记录请求入参、响应状态及执行耗时，
并在响应头回显 X-Request-ID，实现端到端链路可观测性。
"""

from __future__ import annotations

import time
from typing import Any
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.infra.logging import (
    get_logger,
    reset_trace_context,
    set_trace_context,
)

logger = get_logger("http.trace")

# 静态资源前缀：仅在 DEBUG 级别打印，避免静态资源请求刷屏
_STATIC_PREFIXES: tuple[str, ...] = (
    "/static/",
    "/favicon.ico",
)


class TraceLoggingMiddleware(BaseHTTPMiddleware):
    """全链路 HTTP 追踪与请求日志中间件。"""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """拦截 HTTP 请求，注入链路上下文并记录访问日志。"""
        # 1. 提取或生成链路追踪标识 Trace ID
        trace_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Trace-ID")
            or f"req-{uuid.uuid4().hex[:12]}"
        )

        # 2. 绑定协程上下文
        tokens = set_trace_context(trace_id=trace_id, user="anonymous")

        # 3. 提取请求元数据
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        query = str(request.query_params)
        path_with_query = f"{path}?{query}" if query else path

        # 排除静态资源的高频普通打印
        is_static = any(path.startswith(prefix) for prefix in _STATIC_PREFIXES)

        if not is_static:
            logger.info("--> HTTP {} {} from {}", method, path_with_query, client_ip)
        else:
            logger.debug("--> HTTP {} {}", method, path_with_query)

        start_time = time.perf_counter()

        try:
            response: Response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # 4. 回显追踪请求头
            response.headers["X-Request-ID"] = trace_id

            # 5. 记录响应访问日志
            status_code = response.status_code
            if not is_static:
                if status_code >= 500:
                    logger.error(
                        "<-- HTTP {} {} -> {} ({:.2f}ms)",
                        method,
                        path,
                        status_code,
                        elapsed_ms,
                    )
                elif status_code >= 400:
                    logger.warning(
                        "<-- HTTP {} {} -> {} ({:.2f}ms)",
                        method,
                        path,
                        status_code,
                        elapsed_ms,
                    )
                else:
                    logger.info(
                        "<-- HTTP {} {} -> {} ({:.2f}ms)",
                        method,
                        path,
                        status_code,
                        elapsed_ms,
                    )
            else:
                logger.debug(
                    "<-- HTTP {} {} -> {} ({:.2f}ms)",
                    method,
                    path,
                    status_code,
                    elapsed_ms,
                )

            return response

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "<-- HTTP {} {} 处理发生未捕获异常 ({:.2f}ms): {}",
                method,
                path,
                elapsed_ms,
                exc,
            )
            raise exc

        finally:
            reset_trace_context(tokens)
