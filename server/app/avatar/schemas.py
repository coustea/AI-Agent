"""Avatar schemas — re-exported from request.py and response.py for backward compatibility."""

from app.avatar.request import AvatarGenerateRequest
from app.avatar.response import AvatarBridgeResponse

__all__ = ["AvatarGenerateRequest", "AvatarBridgeResponse"]
