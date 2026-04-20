"""ChatDoc SDK 异常定义。"""


class ChatDocError(Exception):
    """ChatDoc SDK 基础异常。"""

    def __init__(self, message: str, code: int | None = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ChatDocAuthError(ChatDocError):
    """认证相关错误。"""
    pass


class ChatDocAPIError(ChatDocError):
    """API 调用错误。"""

    def __init__(self, message: str, code: int, http_status: int | None = None):
        super().__init__(message, code)
        self.http_status = http_status


class ChatDocWebSocketError(ChatDocError):
    """WebSocket 连接错误。"""
    pass
