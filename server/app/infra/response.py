"""统一 HTTP 响应封装模块。

定义标准的 API 响应格式 {code, message, data}，
所有接口统一使用 HttpResponse.success() 和 HttpResponse.error() 返回。
"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel


class HttpResponse(BaseModel):
    """HTTP 响应信封模型。

    所有 API 响应都遵循此格式：
    {
        "code": 200,       // 业务状态码
        "message": "success", // 提示信息
        "data": {...}       // 响应数据（可选）
    }
    """
    # 业务状态码，默认 200
    code: int = 200
    # 提示信息
    message: str = "success"
    # 响应数据，可以是任意类型
    data: Any = None

    @staticmethod
    def success(data: Any = None, message: str = "success", status_code: int = 200) -> JSONResponse:
        """创建成功响应。

        Args:
            data: 响应数据
            message: 提示信息
            status_code: HTTP 状态码（创建资源时用 201）

        Returns:
            JSONResponse 对象
        """
        # 将 Pydantic 模型转为字典，mode="json" 确保 datetime 等类型正确序列化
        body = HttpResponse(code=200, message=message, data=data).model_dump(mode="json")
        return JSONResponse(status_code=status_code, content=body)

    @staticmethod
    def error(
        code: int = 500,
        message: str = "error",
        data: Any = None,
    ) -> JSONResponse:
        """创建错误响应。

        使用业务状态码作为 HTTP 状态码，保持信封格式一致。

        Args:
            code: 业务状态码（同时作为 HTTP 状态码）
            message: 错误提示信息
            data: 附加错误数据（可选）

        Returns:
            JSONResponse 对象
        """
        body = HttpResponse(code=code, message=message, data=data).model_dump(mode="json")
        return JSONResponse(status_code=code, content=body)
