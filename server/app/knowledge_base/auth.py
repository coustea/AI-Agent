"""ChatDoc API 签名认证模块。"""

import base64
import hashlib
import hmac
import time
from typing import Any


class ChatDocAuth:
    """讯飞 ChatDoc API 签名认证。

    签名算法：
    1. MD5(appId + timestamp) 生成原始签名
    2. HMAC-SHA1(apiSecret, 原始签名) 加密
    3. Base64 编码得到最终签名
    """

    def __init__(self, app_id: str, api_secret: str):
        """初始化认证信息。

        Args:
            app_id: 讯飞开放平台应用 ID
            api_secret: 讯飞开放平台 API Secret
        """
        self.app_id = app_id
        self.api_secret = api_secret

    def _get_origin_signature(self, timestamp: str) -> str:
        """生成原始签名（MD5）。"""
        data = (self.app_id + timestamp).encode("utf-8")
        return hashlib.md5(data).hexdigest()

    def get_signature(self, timestamp: str) -> str:
        """生成最终签名。

        Args:
            timestamp: Unix 时间戳字符串

        Returns:
            Base64 编码的签名
        """
        origin = self._get_origin_signature(timestamp)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            origin.encode("utf-8"),
            digestmod=hashlib.sha1,
        ).digest()
        return base64.b64encode(signature).decode("utf-8")

    def get_headers(self, timestamp: str | None = None) -> dict[str, str]:
        """获取认证请求头。

        Args:
            timestamp: Unix 时间戳，默认使用当前时间

        Returns:
            包含 appId, timestamp, signature 的请求头
        """
        ts = timestamp or str(int(time.time()))
        return {
            "appId": self.app_id,
            "timestamp": ts,
            "signature": self.get_signature(ts),
        }

    def get_ws_url(self, base_url: str, timestamp: str | None = None) -> str:
        """生成带签名的 WebSocket URL。

        Args:
            base_url: WebSocket 基础 URL
            timestamp: Unix 时间戳，默认使用当前时间

        Returns:
            带签名参数的完整 WebSocket URL
        """
        ts = timestamp or str(int(time.time()))
        signature = self.get_signature(ts)
        return f"{base_url}?appId={self.app_id}&timestamp={ts}&signature={signature}"
