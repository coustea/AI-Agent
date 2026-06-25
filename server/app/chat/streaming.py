"""SSE token event streaming helpers for chat responses.

流式输出层：将 LLM 回答文本分块推送给前端，支持安全过滤缓冲。
两层设计：
  ResponseStreamer — 基础分块流，直接将文本按 chunk_size 切片
  SafetyBufferedResponseStreamer — 带安全检查缓冲区，防止敏感词被跨 chunk 切断
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, NamedTuple

from app.config import SAFETY_SENSITIVE_TERMS


class SafetyResult(NamedTuple):
    has_violation: bool
    sanitized_text: str


class ContentSafetyFilter:
    def __init__(self):
        self.sensitive_terms = SAFETY_SENSITIVE_TERMS
        if self.sensitive_terms:
            self.sensitive_patterns = [
                re.compile("|".join(re.escape(term) for term in self.sensitive_terms), re.IGNORECASE)
            ]
            self.stream_guard_chars = max(1, max(len(term) for term in self.sensitive_terms) - 1)
        else:
            self.sensitive_patterns = []
            self.stream_guard_chars = 0

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


class ResponseStreamer:
    """基础 SSE 流 — 将完整回答文本按固定大小分块输出。"""

    def __init__(self, chunk_size: int = 1024) -> None:
        # 每个 SSE event 的最大字符数，确保不超出网络缓冲区
        self.chunk_size = max(1, chunk_size)  # 至少 1 字符，防止零切片

    async def stream_answer(self, answer: str, *, skip_blank: bool = True) -> AsyncIterator[dict[str, str]]:
        """将回答文本分块 yield 为 SSE 事件。"""
        # 空回答或纯空白回答直接跳过（skip_blank=True 时）
        if not answer or (skip_blank and not answer.strip()):
            return

        # 按 chunk_size 步长切片，逐块 yield
        for start in range(0, len(answer), self.chunk_size):
            chunk = answer[start : start + self.chunk_size]
            if chunk:
                # SSE 事件格式：event: token 表示文本块，前端据此拼接完整回答
                yield {"event": "token", "data": chunk}


# 安全检查回调类型：接收文本，返回 SafetyResult（含 has_violation 和 sanitized_text）
SafetyCheck = Callable[[str], Awaitable[Any]]


class SafetyBufferedResponseStreamer:
    """带安全缓冲的 SSE 流 — 解决敏感词被 chunk 切断导致绕过过滤的问题。

    核心思路：在尾部保留 guard_chars 个字符作为缓冲区，
    待下一批文本到达时一起做安全检查，避免 "色"+"情" 被两个 chunk 分别放过。
    """

    def __init__(
        self,
        *,
        response_streamer: ResponseStreamer,  # 底层 SSE 流，负责实际分块输出
        safety_check: SafetyCheck,  # 安全过滤回调，如 ContentSafetyFilter.check
        guard_chars: int,  # 尾部缓冲字符数，通常为最长敏感词长度 - 1
    ) -> None:
        self._response_streamer = response_streamer  # 底层流
        self._safety_check = safety_check  # 安全检查函数
        self._guard_chars = max(0, guard_chars)  # 缓冲区大小，防止负值
        self._pending_text = ""  # 待处理的累积文本（含缓冲区）
        self._has_non_blank_text = False  # 是否已出现过非空白文本（用于跳过前导空白）

    async def push(self, text: str) -> AsyncIterator[dict[str, str]]:
        """推入新文本块，触发安全检查并输出安全部分。"""
        if not text:
            return
        # 标记是否出现过非空白内容
        if text.strip():
            self._has_non_blank_text = True
        # 累积到待处理缓冲区
        self._pending_text += text
        # 排空缓冲区（保留尾部 guard_chars 作为安全缓冲）
        async for event in self._drain(keep_tail=True):
            yield event

    async def flush(self) -> AsyncIterator[dict[str, str]]:
        """刷新所有剩余文本 — 流结束时调用，不再保留尾部缓冲。"""
        async for event in self._drain(keep_tail=False):
            yield event

    async def _drain(self, *, keep_tail: bool) -> AsyncIterator[dict[str, str]]:
        """核心排空逻辑：对累积文本做安全检查，输出安全部分，保留尾部缓冲。"""
        if not self._pending_text:
            return

        # 对累积文本做安全过滤检查
        safety_result = await self._safety_check(self._pending_text)
        # 如果有违规，使用脱敏后的文本；否则使用原始文本
        safe_text = (
            safety_result.sanitized_text
            if getattr(safety_result, "has_violation", False)
            else self._pending_text
        )
        # 如果还在累积且全是空白，继续等待后续文本（避免输出无意义的空白）
        if keep_tail and not self._has_non_blank_text and not safe_text.strip():
            self._pending_text = safe_text
            return

        # 计算需要保留的尾部字符数（作为下一批的安全缓冲）
        keep_count = min(self._guard_chars, len(safe_text)) if keep_tail else 0
        # 分离：emit_text = 要输出的部分，_pending_text = 保留在缓冲区的部分
        emit_text = safe_text[:-keep_count] if keep_count else safe_text
        self._pending_text = safe_text[-keep_count:] if keep_count else ""

        # 跳过空输出或前导空白（直到出现第一个非空白字符才开始输出）
        if not emit_text or (not self._has_non_blank_text and not emit_text.strip()):
            return

        # 通过底层 ResponseStreamer 分块输出安全文本
        async for event in self._response_streamer.stream_answer(emit_text, skip_blank=False):
            yield event
