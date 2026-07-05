from __future__ import annotations

import pytest

from app.chat.tools.search import _redact_url_query_secrets


class TestRedactUrlQuerySecrets:
    def test_no_secrets(self):
        text = "https://example.com/search?q=hello"
        assert _redact_url_query_secrets(text) == text

    def test_api_key_redacted(self):
        text = "https://example.com?key=secret123&q=test"
        result = _redact_url_query_secrets(text)
        assert "secret123" not in result
        assert "[REDACTED]" in result

    def test_token_redacted(self):
        text = "url?token=abc123xyz"
        result = _redact_url_query_secrets(text)
        assert "abc123xyz" not in result
        assert "[REDACTED]" in result

    def test_multiple_params(self):
        text = "url?key=secret1&token=secret2"
        result = _redact_url_query_secrets(text)
        assert "secret1" not in result
        assert "secret2" not in result

    def test_no_marker_returns_unchanged(self):
        text = "just some normal text"
        assert _redact_url_query_secrets(text) == text

    def test_exception_input(self):
        exc = Exception("api_key=myscretkey123 failed")
        result = _redact_url_query_secrets(exc)
        assert "myscretkey123" not in result
        assert "[REDACTED]" in result
