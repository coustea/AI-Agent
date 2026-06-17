"""
虚拟人数据模型 — 从 request.py 和 response.py 重新导出，保持向后兼容。
"""

from app.avatar.request import AvatarGenerateRequest
from app.avatar.response import AvatarBridgeResponse

__all__ = ["AvatarGenerateRequest", "AvatarBridgeResponse"]
