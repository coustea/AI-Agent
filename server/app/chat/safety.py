"""Content safety filter — regex-based sensitive term detection and sanitization.

Extracted from service.py to break the circular import between agent.py and service.py.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from app.config import SAFETY_SENSITIVE_TERMS


class SafetyResult(NamedTuple):
    has_violation: bool
    sanitized_text: str


class ContentSafetyFilter:
    def __init__(self):
        self.sensitive_terms = SAFETY_SENSITIVE_TERMS
        self.sensitive_patterns = [
            re.compile("|".join(re.escape(term) for term in self.sensitive_terms), re.IGNORECASE)
        ]
        self.stream_guard_chars = max(1, max(len(term) for term in self.sensitive_terms) - 1)

    async def check(self, text: str) -> SafetyResult:
        if not text:
            return SafetyResult(has_violation=False, sanitized_text=text)
        sanitized = text
        has_violation = False
        for pattern in self.sensitive_patterns:
            if pattern.search(sanitized):
                has_violation = True
                sanitized = pattern.sub("***", sanitized)
        return SafetyResult(has_violation=has_violation, sanitized_text=sanitized)


safety_filter = ContentSafetyFilter()