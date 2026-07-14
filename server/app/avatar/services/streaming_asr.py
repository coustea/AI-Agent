"""Realtime speech-recognition client used by the digital-human bridge."""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import websockets

from app.avatar.services.endpoint_resolver import endpoint_resolver
from app.avatar.services.xfyun_auth import assemble_auth_url
from app.config import (
    ASR_API_KEY,
    ASR_API_SECRET,
    ASR_APP_ID,
    ASR_VAD_EOS,
    AVATAR_IAT_URL,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)

FIRST_AUDIO_TIMEOUT_SECONDS = 8.0
AUDIO_INPUT_TIMEOUT_SECONDS = 3.0
ASR_CLOSE_TIMEOUT_SECONDS = 0.25
ASR_FINAL_TIMEOUT_SECONDS = 8.0


class ASRResultAssembler:
    """Apply Xfyun WPGS append/replace frames to one stable transcript."""

    def __init__(self) -> None:
        self._segments: dict[int, str] = {}
        self.latest_text = ""
        self.best_text = ""
        self.published_text = ""

    def consume(self, result: dict) -> str:
        current_text = "".join(
            candidates[0].get("w", "")
            for item in result.get("ws", [])
            if (candidates := item.get("cw", []))
            and isinstance(candidates[0], dict)
        )

        segment_number = self._segment_number(result.get("sn"))
        if result.get("pgs") == "rpl":
            replace_range = result.get("rg")
            try:
                start, end = (int(value) for value in replace_range)
            except (TypeError, ValueError):
                start = end = None
            if start is not None and end is not None:
                for segment_id in range(start, end + 1):
                    self._segments.pop(segment_id, None)
                self.latest_text = self._joined_segments().strip()

        if current_text:
            if segment_number is None:
                self.latest_text = current_text.strip()
            else:
                self._segments[segment_number] = current_text
                self.latest_text = self._joined_segments().strip()
        if self.latest_text:
            self.best_text = self.latest_text
        return self.latest_text

    @property
    def usable_text(self) -> str:
        return self.latest_text or self.best_text

    def should_publish(self, text: str) -> bool:
        if not text or text == self.published_text:
            return False
        self.published_text = text
        return True

    def _joined_segments(self) -> str:
        return "".join(self._segments[key] for key in sorted(self._segments))

    @staticmethod
    def _segment_number(value: object) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None


@dataclass(frozen=True)
class ASRSendMetrics:
    chunk_count: int
    timeout_hit: bool


class StreamingASRSession:
    """Own one upstream ASR socket from readiness through final transcript."""

    def __init__(
        self,
        audio_queue: asyncio.Queue,
        vad_eos: int = ASR_VAD_EOS,
        ready_event: asyncio.Event | None = None,
        partial_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self.audio_queue = audio_queue
        self.vad_eos = vad_eos
        self.ready_event = ready_event
        self.partial_callback = partial_callback
        self.chunk_count = 0
        self.timeout_hit = False
        self._results = ASRResultAssembler()
        self._consumed_items: list[tuple[float, bytes] | None] = []

    def take_replay_items(self) -> list[tuple[float, bytes] | None]:
        items = self._consumed_items
        self._consumed_items = []
        return items

    async def run(self) -> str | None:
        auth_url = assemble_auth_url(
            AVATAR_IAT_URL,
            "GET",
            ASR_API_KEY,
            ASR_API_SECRET,
        )
        target = await endpoint_resolver.resolve(AVATAR_IAT_URL)
        connect_kwargs = target.connect_kwargs() if target is not None else {}
        try:
            async with websockets.connect(
                auth_url,
                open_timeout=8,
                close_timeout=ASR_CLOSE_TIMEOUT_SECONDS,
                **connect_kwargs,
            ) as websocket:
                if self.ready_event is not None:
                    self.ready_event.set()

                try:
                    first_item = await asyncio.wait_for(
                        self.audio_queue.get(),
                        timeout=FIRST_AUDIO_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    logger.debug("[ASR] no audio before idle connection timeout")
                    return None

                if first_item is None:
                    return None

                self._consumed_items.append(first_item)
                _, first_chunk = first_item
                result = await self._stream(websocket, first_chunk)
                logger.info(
                    "[ASR] session completed frames=%d timeout=%s result_len=%d",
                    self.chunk_count,
                    self.timeout_hit,
                    len(result or ""),
                )
                if result and result.strip():
                    self._consumed_items.clear()
                return result
        except Exception as exc:
            error_name = type(exc).__name__
            logger.error("[ASR] session failed: %s: %r", error_name, exc)
            raise RuntimeError(
                f"ASR session failed: {error_name}: {exc!r}"
            ) from exc

    async def _stream(self, websocket, first_chunk: bytes) -> str | None:
        await websocket.send(json.dumps(self._start_frame()))
        receiver = asyncio.create_task(self._receive_result(websocket))
        await asyncio.sleep(0)
        sender = asyncio.create_task(self._send_audio(websocket, first_chunk))
        try:
            done, _ = await asyncio.wait(
                (sender, receiver),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if receiver in done:
                return receiver.result()

            metrics = sender.result()
            self.chunk_count = metrics.chunk_count
            self.timeout_hit = metrics.timeout_hit
            try:
                return await asyncio.wait_for(
                    asyncio.shield(receiver),
                    timeout=ASR_FINAL_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                transcript = self._results.usable_text
                logger.warning(
                    "[ASR] provider final timeout after %.1fs partial_len=%d",
                    ASR_FINAL_TIMEOUT_SECONDS,
                    len(transcript),
                )
                return transcript or None
        finally:
            for task in (sender, receiver):
                if not task.done():
                    task.cancel()
            await asyncio.gather(sender, receiver, return_exceptions=True)

    async def _send_audio(self, websocket, first_chunk: bytes) -> ASRSendMetrics:
        # Browser capture is the real-time clock. Sending the same PCM duration
        # again here would add one full utterance of latency after audio_end.
        await websocket.send(json.dumps(self._audio_frame(first_chunk)))
        chunk_count = 1
        self.chunk_count = chunk_count
        timeout_hit = False

        while True:
            try:
                item = await asyncio.wait_for(
                    self.audio_queue.get(),
                    timeout=AUDIO_INPUT_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                timeout_hit = True
                self.timeout_hit = True
                logger.debug("[ASR] audio input timed out; closing utterance")
                break

            if item is None:
                self._consumed_items.append(None)
                break

            self._consumed_items.append(item)
            _, chunk = item
            await websocket.send(json.dumps(self._audio_frame(chunk)))
            chunk_count += 1
            self.chunk_count = chunk_count

        await websocket.send(json.dumps(self._end_frame()))
        return ASRSendMetrics(chunk_count=chunk_count, timeout_hit=timeout_hit)

    async def _receive_result(self, websocket) -> str:
        async for message in websocket:
            data = json.loads(message)
            code = data.get("code", -1)
            if code != 0:
                message_text = data.get("message", "Unknown error")
                raise RuntimeError(
                    f"ASR API error: code={code} message={message_text}"
                )

            payload = data.get("data", {})
            candidate = self._results.consume(payload.get("result", {}))
            if (
                self.partial_callback is not None
                and self._results.should_publish(candidate)
            ):
                await self.partial_callback(candidate)
            if payload.get("status") == 2:
                return self._results.usable_text

        return self._results.usable_text

    def _start_frame(self) -> dict:
        return {
            "common": {"app_id": ASR_APP_ID},
            "business": {
                "language": "zh_cn",
                "domain": "iat",
                "accent": "mandarin",
                "vad_eos": self.vad_eos,
                "ptt": 1,
                "pd": "0",
                "nunum": 1,
                "dwa": "wpgs",
            },
            "data": {
                "status": 0,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": "",
            },
        }

    @staticmethod
    def _audio_frame(chunk: bytes) -> dict:
        return {
            "data": {
                "status": 1,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": base64.b64encode(chunk).decode(),
            }
        }

    @staticmethod
    def _end_frame() -> dict:
        return {
            "data": {
                "status": 2,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": "",
            }
        }


class AdaptiveVADController:
    """Keep provider EOS conservative; browser VAD owns normal turn ending."""

    def __init__(self, base_vad_eos: int = ASR_VAD_EOS) -> None:
        self.base_vad_eos = base_vad_eos
        self.consecutive_empty = 0
        self.empty_rate = 0.0
        self.round_metrics: list[dict] = []

    def compute_vad_eos(self) -> int:
        return max(1000, min(1800, self.base_vad_eos))

    def record_round(
        self,
        chunk_count: int,
        timeout_hit: bool,
        has_result: bool,
    ) -> None:
        self.consecutive_empty = 0 if has_result else self.consecutive_empty + 1
        self.round_metrics.append(
            {
                "chunk_count": chunk_count,
                "timeout_hit": timeout_hit,
                "has_result": has_result,
            }
        )
        self.round_metrics = self.round_metrics[-20:]
        if self.round_metrics:
            empty_count = sum(
                1 for metric in self.round_metrics if not metric["has_result"]
            )
            self.empty_rate = empty_count / len(self.round_metrics)

    def reset(self) -> None:
        self.consecutive_empty = 0
        self.empty_rate = 0.0
        self.round_metrics = []
