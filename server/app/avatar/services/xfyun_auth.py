"""讯飞 WebSocket 鉴权工具 — HMAC-SHA256 签名 + Base64 编码。

用于 ASR（语音识别）和 Avatar（虚拟人）服务的 WebSocket 连接鉴权。
按讯飞开放平台规范构造签名：host + date + request-line → HMAC-SHA256 → Base64。
"""

import base64
import hashlib
import hmac
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time


class AssembleHeaderException(Exception):
    """鉴权头构造失败异常。"""

    def __init__(self, msg: str):
        self.message = msg


class Url:
    """解析后的 URL 组件。"""

    def __init__(self, host: str, path: str, schema: str):
        self.host = host
        self.path = path
        self.schema = schema


def _parse_url(request_url: str) -> Url:
    """将完整 URL 解析为 host、path、schema 组件。"""
    stidx = request_url.index("://")
    host = request_url[stidx + 3:]
    schema = request_url[:stidx + 3]
    edidx = host.index("/")
    if edidx <= 0:
        raise AssembleHeaderException(f"invalid request url: {request_url}")
    path = host[edidx:]
    host = host[:edidx]
    return Url(host, path, schema)


def assemble_auth_url(request_url: str, method: str = "GET", api_key: str = "", api_secret: str = "") -> str:
    """构建带鉴权参数的讯飞 WebSocket URL。

    签名流程：
      1. 构造签名原文：host + date + HTTP方法 + 路径 + HTTP/1.1
      2. 使用 api_secret 进行 HMAC-SHA256 签名
      3. 将签名结果 Base64 编码
      4. 构造 authorization 头（含 api_key、算法、签名）
      5. 将 authorization、date、host 作为查询参数追加到 URL

    Args:
        request_url: 讯飞 WebSocket 服务的原始 URL。
        method: HTTP 方法（WebSocket 通常为 "GET"）。
        api_key: 讯飞 API Key。
        api_secret: 讯飞 API Secret。

    Returns:
        带鉴权查询参数的完整 URL。
    """
    u = _parse_url(request_url)
    host = u.host
    path = u.path
    # 获取当前时间并格式化为 HTTP 日期格式
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    # 构造签名原文
    signature_origin = f"host: {host}\ndate: {date}\n{method} {path} HTTP/1.1"
    # HMAC-SHA256 签名
    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature_sha = base64.b64encode(signature_sha).decode(encoding="utf-8")
    # 构造 authorization 头
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature_sha}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(encoding="utf-8")
    # 拼接查询参数
    values = {
        "host": host,
        "date": date,
        "authorization": authorization,
    }

    return request_url + "?" + urlencode(values)
