"""Tests for search tool provider guards."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import app.chat.tools.search as search_module
import pytest


@pytest.mark.asyncio
async def test_tavily_search_returns_unavailable_when_key_missing(monkeypatch) -> None:
    """未配置 Tavily key 时返回不可用提示。"""
    monkeypatch.setattr(search_module, "_tavily_search_client", None)
    result = await search_module.tavily_search("TCP 三次握手")
    assert "不可用" in result or "未配置" in result


@pytest.mark.asyncio
async def test_spark_search_redacts_secrets_from_errors(monkeypatch) -> None:
    """搜索异常文本里不能把密钥泄露给日志/前端。"""
    result = await search_module.spark_search("TCP 三次握手")
    assert "password=" not in result
    assert "api_key=" not in result
