import httpx
import logging
from typing import Optional
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
async def web_fetch(url: str, method: str = "GET", headers: Optional[dict] = None, timeout: int = 30, max_chars: int = 20000) -> str:
    """异步从 URL 获取网页文本内容。支持 HTTP/HTTPS。非常适合阅读文章、文档或 API 响应。"""
    if not url.startswith(("http://", "https://")):
        return "Error: URL must start with http:// or https://"

    timeout = min(max(timeout, 1), 60)
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    if headers:
        default_headers.update(headers)

    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False, follow_redirects=True) as client:
            response = await client.request(method=method.upper(), url=url, headers=default_headers)
            response.raise_for_status()
            content = response.text

            if not content:
                return f"Success: URL fetched successfully, but the content is empty. (Status code: {response.status_code})"
            if len(content) > max_chars:
                return content[:max_chars] + f"\n\n... [Content truncated. Displaying first {max_chars} characters]"
            return content

    except httpx.TimeoutException:
        return f"Error: Request timed out after {timeout} seconds."
    except httpx.HTTPStatusError as e:
        return f"HTTP Error {e.response.status_code}: {e.response.reason_phrase}"
    except Exception as e:
        return f"Error fetching URL: {str(e)}"
