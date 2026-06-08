"""Xfyun (讯飞) authentication utility for HMAC-SHA256 WebSocket authentication.

Used by both ASR (IAT) and Avatar services.
"""

import base64
import hashlib
import hmac
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time


class AssembleHeaderException(Exception):
    """Exception raised when assembling authentication header fails."""

    def __init__(self, msg: str):
        self.message = msg


class Url:
    """Parsed URL components."""

    def __init__(self, host: str, path: str, schema: str):
        self.host = host
        self.path = path
        self.schema = schema


def _parse_url(request_url: str) -> Url:
    """Parse URL into components."""
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
    """Build authenticated request URL for Xfyun WebSocket services.

    Args:
        request_url: The WebSocket URL to authenticate.
        method: HTTP method (usually "GET" for WebSocket).
        api_key: Xfyun API Key.
        api_secret: Xfyun API Secret.

    Returns:
        Authenticated URL with query parameters.
    """
    u = _parse_url(request_url)
    host = u.host
    path = u.path
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    signature_origin = f"host: {host}\ndate: {date}\n{method} {path} HTTP/1.1"
    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature_sha = base64.b64encode(signature_sha).decode(encoding="utf-8")
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature_sha}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(encoding="utf-8")
    values = {
        "host": host,
        "date": date,
        "authorization": authorization,
    }

    return request_url + "?" + urlencode(values)
