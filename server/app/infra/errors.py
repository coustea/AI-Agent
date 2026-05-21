"""统一异常定义。

所有模块共用的业务异常，由全局异常处理器统一捕获。
"""

from __future__ import annotations


class AppError(Exception):
    """应用异常基类。"""

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class ServiceError(AppError):
    """外部服务不可用（LLM、数据库等）。"""


class NotFoundError(AppError):
    """资源不存在。"""


class ForbiddenError(AppError):
    """权限不足。"""
