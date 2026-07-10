"""
虚拟人数据模型 — 从 request.py 和 response.py 重新导出，保持向后兼容。
"""

# 从 request.py / response.py 重新导出数据模型，保持向后兼容
from app.avatar.request import AvatarGenerateRequest
from app.avatar.response import AvatarBridgeResponse

# 对外暴露的模型名列表
__all__ = ["AvatarGenerateRequest", "AvatarBridgeResponse"]
