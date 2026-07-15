"""Realtime speech-recognition client used by the digital-human bridge."""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import websockets

from app.avatar.services.endpoint_resolver import WebSocketTarget, endpoint_resolver
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
ASR_EMPTY_FINAL_TIMEOUT_SECONDS = 2.5
ASR_MAX_NODE_ATTEMPTS = 3
ASR_REPLAY_FRAME_SECONDS = 0.02


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
        targets = await endpoint_resolver.resolve_candidates(AVATAR_IAT_URL)
        try:
            primary_target = targets[0]
            logger.info(
                "[ASR] live node=%s",
                primary_target.host if primary_target is not None else "system-dns",
            )
            try:
                result = await self._run_live_attempt(auth_url, primary_target)
            except Exception as exc:
                endpoint_resolver.report_failure(AVATAR_IAT_URL, primary_target)
                logger.warning(
                    "[ASR] live node failed node=%s error=%s",
                    primary_target.host if primary_target is not None else "system-dns",
                    type(exc).__name__,
                )
                if len(targets) <= 1:
                    raise
                result = None
            if result and result.strip():
                endpoint_resolver.report_success(AVATAR_IAT_URL, primary_target)
                self._consumed_items.clear()
                return result
            endpoint_resolver.report_failure(AVATAR_IAT_URL, primary_target)

            replay_chunks = [
                item[1] for item in self._consumed_items if item is not None
            ]
            retry_targets = targets[1:ASR_MAX_NODE_ATTEMPTS]
            if not replay_chunks or not retry_targets:
                return result

            result = await self._race_replay_targets(
                auth_url,
                retry_targets,
                replay_chunks,
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
        finally:
            logger.info(
                "[ASR] session completed frames=%d timeout=%s result_len=%d",
                self.chunk_count,
                self.timeout_hit,
                len(self._results.usable_text),
            )

    async def _run_live_attempt(
        self,
        auth_url: str,
        target: WebSocketTarget | None,
    ) -> str | None:
        async with self._connect(auth_url, target) as websocket:
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
            return await self._stream(websocket, first_chunk)

    async def _run_replay_attempt(
        self,
        auth_url: str,
        target: WebSocketTarget | None,
        chunks: list[bytes],
    ) -> str | None:
        async with self._connect(auth_url, target) as websocket:
            receiver = asyncio.create_task(self._receive_result(websocket))
            try:
                await self._send_replay_audio(websocket, chunks)
                return await self._await_final_result(receiver)
            finally:
                if not receiver.done():
                    receiver.cancel()
                await asyncio.gather(receiver, return_exceptions=True)

    async def _race_replay_targets(
        self,
        auth_url: str,
        targets: tuple[WebSocketTarget | None, ...],
        chunks: list[bytes],
    ) -> str | None:
        """Replay one utterance on alternate nodes concurrently.

        Empty provider responses are node-specific and used to make retries
        take one full utterance plus timeout per node. Isolated sessions avoid
        sharing WPGS assembly state while the first usable transcript wins.
        """

        async def replay(
            attempt: int,
            target: WebSocketTarget | None,
        ) -> tuple[
            WebSocketTarget | None,
            str | None,
            ASRResultAssembler,
            Exception | None,
        ]:
            logger.warning(
                "[ASR] empty response; racing %d frames on alternate node attempt=%d",
                len(chunks),
                attempt,
            )
            logger.info(
                "[ASR] replay node=%s",
                target.host if target is not None else "system-dns",
            )
            replay_session = StreamingASRSession(
                asyncio.Queue(),
                vad_eos=self.vad_eos,
            )
            try:
                result = await replay_session._run_replay_attempt(
                    auth_url,
                    target,
                    chunks,
                )
                return target, result, replay_session._results, None
            except Exception as exc:
                return target, None, replay_session._results, exc

        tasks = {
            asyncio.create_task(replay(attempt, target))
            for attempt, target in enumerate(targets, start=2)
        }
        pending = set(tasks)
        try:
            while pending:
                done, pending = await asyncio.wait(
                    pending,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in done:
                    target, result, assembler, error = task.result()
                    if error is not None:
                        endpoint_resolver.report_failure(AVATAR_IAT_URL, target)
                        logger.warning(
                            "[ASR] alternate node failed node=%s error=%s",
                            target.host if target is not None else "system-dns",
                            type(error).__name__,
                        )
                        continue
                    if result and result.strip():
                        endpoint_resolver.report_success(AVATAR_IAT_URL, target)
                        self._results = assembler
                        for pending_task in pending:
                            pending_task.cancel()
                        await asyncio.gather(*pending, return_exceptions=True)
                        return result
                    endpoint_resolver.report_failure(AVATAR_IAT_URL, target)
            return None
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _connect(auth_url: str, target: WebSocketTarget | None):
        connect_kwargs = target.connect_kwargs() if target is not None else {}
        return websockets.connect(
            auth_url,
            open_timeout=8,
            close_timeout=ASR_CLOSE_TIMEOUT_SECONDS,
            **connect_kwargs,
        )

    async def _stream(self, websocket, first_chunk: bytes) -> str | None:
        await websocket.send(json.dumps(self._start_frame(first_chunk)))
        receiver = asyncio.create_task(self._receive_result(websocket))
        await asyncio.sleep(0)
        sender = asyncio.create_task(self._send_audio(websocket))
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
            return await self._await_final_result(receiver)
        finally:
            for task in (sender, receiver):
                if not task.done():
                    task.cancel()
            await asyncio.gather(sender, receiver, return_exceptions=True)

    async def _send_audio(self, websocket) -> ASRSendMetrics:
        # Browser capture is the real-time clock. Sending the same PCM duration
        # again here would add one full utterance of latency after audio_end.
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

    async def _send_replay_audio(
        self,
        websocket,
        chunks: list[bytes],
    ) -> None:
        if not chunks:
            return
        await websocket.send(json.dumps(self._start_frame(chunks[0])))
        if len(chunks) > 1:
            await asyncio.sleep(ASR_REPLAY_FRAME_SECONDS)
        for index, chunk in enumerate(chunks[1:], start=1):
            await websocket.send(json.dumps(self._audio_frame(chunk)))
            if index < len(chunks) - 1:
                await asyncio.sleep(ASR_REPLAY_FRAME_SECONDS)
        await websocket.send(json.dumps(self._end_frame()))

    async def _await_final_result(self, receiver: asyncio.Task) -> str | None:
        timeout = (
            ASR_FINAL_TIMEOUT_SECONDS
            if self._results.usable_text
            else ASR_EMPTY_FINAL_TIMEOUT_SECONDS
        )
        try:
            return await asyncio.wait_for(asyncio.shield(receiver), timeout=timeout)
        except asyncio.TimeoutError:
            transcript = self._results.usable_text
            logger.warning(
                "[ASR] provider final timeout after %.1fs partial_len=%d",
                timeout,
                len(transcript),
            )
            return transcript or None

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

    def _start_frame(self, chunk: bytes) -> dict:
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
                "audio": base64.b64encode(chunk).decode(),
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
