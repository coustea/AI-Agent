"""Bounded PCM framing for one browser speech-recognition turn."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

AudioQueueItem = tuple[float, bytes] | None


@dataclass(frozen=True)
class AudioIngressStats:
    callbacks: int
    frames: int
    dropped: int
    queued: int


class AudioIngress:
    """Convert arbitrary browser PCM messages into 40ms ASR frames."""

    def __init__(self, *, frame_bytes: int = 1280, queue_size: int = 512) -> None:
        self.frame_bytes = frame_bytes
        self.queue_size = queue_size
        self.queue: asyncio.Queue[AudioQueueItem] | None = None
        self.remainder = bytearray()
        self.callbacks = 0
        self.frames = 0
        self.dropped = 0

    def start(self) -> asyncio.Queue[AudioQueueItem]:
        self.close()
        self.queue = asyncio.Queue(maxsize=self.queue_size)
        self.remainder.clear()
        self.callbacks = 0
        self.frames = 0
        self.dropped = 0
        return self.queue

    def accept(self, pcm: bytes) -> AudioIngressStats:
        if self.queue is None or not pcm:
            return self.stats
        self.callbacks += 1
        self.remainder.extend(pcm)
        while len(self.remainder) >= self.frame_bytes:
            frame = bytes(self.remainder[:self.frame_bytes])
            del self.remainder[:self.frame_bytes]
            self._offer((time.monotonic(), frame))
            self.frames += 1
        return self.stats


    def finish(self) -> AudioIngressStats:
        if self.queue is None:
            return self.stats
        if self.remainder:
            self._offer((time.monotonic(), bytes(self.remainder)))
            self.remainder.clear()
            self.frames += 1
        self._offer(None)
        return self.stats

    def restore(self, items: list[AudioQueueItem]) -> int:
        if self.queue is None or not items:
            return 0
        pending: list[AudioQueueItem] = []
        while True:
            try:
                pending.append(self.queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        combined = [*items, *pending]
        limit = self.queue.maxsize
        if limit > 0 and len(combined) > limit:
            has_end = combined[-1] is None
            combined = combined[:limit]
            if has_end:
                combined[-1] = None
        for item in combined:
            self.queue.put_nowait(item)
        return len(combined)

    def close(self) -> None:
        if self.queue is not None:
            self.end_queue(self.queue)
        self.queue = None
        self.remainder.clear()

    @property
    def stats(self) -> AudioIngressStats:
        return AudioIngressStats(
            callbacks=self.callbacks,
            frames=self.frames,
            dropped=self.dropped,
            queued=self.queue.qsize() if self.queue is not None else 0,
        )

    def _offer(self, item: AudioQueueItem) -> None:
        queue = self.queue
        if queue is None:
            return
        if queue.full():
            try:
                queue.get_nowait()
                self.dropped += 1
            except asyncio.QueueEmpty:
                pass
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            self.dropped += 1

    @staticmethod
    def end_queue(queue: asyncio.Queue[AudioQueueItem]) -> None:
        while queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        try:
            queue.put_nowait(None)
        except asyncio.QueueFull:
            pass
