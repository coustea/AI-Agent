# -*- coding: utf-8 -*-
"""Streaming ASR client for real-time speech recognition.

从 manager.py 抽取的 ASR WebSocket 逻辑，用于简化 bridge manager 的职责。

StreamingASRSession: 单次 ASR 识别会话
AdaptiveVADController: 自适应 VAD 参数控制器
"""

import asyncio
import base64
import json

import websockets

from app.avatar.services.xfyun_auth import assemble_auth_url
from app.config import ASR_API_KEY, ASR_API_SECRET, ASR_APP_ID, AVATAR_IAT_URL, ASR_VAD_EOS
from app.infra.logging import get_logger

logger = get_logger(__name__)


class StreamingASRSession:
    """Single ASR recognition session handler.

    处理一次完整的 ASR 识别流程：
    1. 从音频队列获取音频块
    2. 连接讯飞 ASR WebSocket
    3. 发送音频流
    4. 接收识别结果
    """

    def __init__(
        self,
        audio_queue: asyncio.Queue,
        vad_eos: int = ASR_VAD_EOS,
    ):
        self.audio_queue = audio_queue
        self.vad_eos = vad_eos
        self.chunk_count = 0
        self.timeout_hit = False

    async def run(self) -> str | None:
        """Execute one ASR recognition round. Returns recognized text or None.

        Returns:
            str | None: 识别出的文本，如果无结果则返回 None

        Raises:
            RuntimeError: ASR 连接或处理失败
        """
        # Wait for first audio chunk
        try:
            first_item = await asyncio.wait_for(self.audio_queue.get(), timeout=15.0)
        except asyncio.TimeoutError:
            logger.debug("[ASR] No audio chunk received within timeout")
            return None

        if first_item is None:
            return None

        _, first_chunk = first_item

        # Connect to ASR WebSocket with auth
        auth_url = assemble_auth_url(AVATAR_IAT_URL, 'GET', ASR_API_KEY, ASR_API_SECRET)

        try:
            async with websockets.connect(auth_url) as ws:
                send_task = asyncio.create_task(self._send_audio(ws, first_chunk))
                recv_task = asyncio.create_task(self._receive_result(ws))

                result = await recv_task

                if not send_task.done():
                    send_task.cancel()
                send_result = await asyncio.gather(send_task, return_exceptions=True)

                # Extract metrics
                if isinstance(send_result[0], dict):
                    self.chunk_count = send_result[0].get("chunk_count", 0)
                    self.timeout_hit = send_result[0].get("timeout_hit", False)

                logger.info(
                    "[ASR] Session completed chunks=%d timeout=%s result_len=%d",
                    self.chunk_count,
                    self.timeout_hit,
                    len(result or ""),
                )

                return result
        except Exception as e:
            logger.error("[ASR] Session failed: %s", e)
            raise RuntimeError(f"ASR session failed: {e}")

    async def _send_audio(self, ws, first_chunk: bytes) -> dict:
        """Send audio stream to ASR WebSocket.

        Args:
            ws: WebSocket connection
            first_chunk: First audio chunk (already retrieved from queue)

        Returns:
            dict: Metrics about the sending process (chunk_count, timeout_hit)
        """
        # Send start frame with first chunk
        first_b64 = base64.b64encode(first_chunk).decode()
        start_params = {
            "common": {"app_id": ASR_APP_ID},
            "business": {
                "language": "zh_cn",
                "domain": "iat",
                "accent": "mandarin",
                "vad_eos": self.vad_eos,
                "ptt": 1,      # Enable punctuation
                "pd": "0",     # Speaker separation mode
                "nunum": 0,    # Convert numbers to Arabic
                "dwa": "wpgs", # Enable dynamic correction
            },
            "data": {
                "status": 0,  # 0 = first frame
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": first_b64,
            },
        }
        await ws.send(json.dumps(start_params))
        chunk_count = 1
        timeout_hit = False
        await asyncio.sleep(0.04)  # Inter-frame delay

        # Send middle frames
        while True:
            try:
                item = await asyncio.wait_for(self.audio_queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                timeout_hit = True
                logger.debug("[ASR] Audio queue timeout, sending end frame")
                break

            if item is None:
                break

            _, chunk = item
            audio_b64 = base64.b64encode(chunk).decode()
            frame = {
                "data": {
                    "status": 1,  # 1 = middle frame
                    "format": "audio/L16;rate=16000",
                    "encoding": "raw",
                    "audio": audio_b64,
                }
            }
            await ws.send(json.dumps(frame))
            chunk_count += 1
            await asyncio.sleep(0.04)

        # Send end frame
        end_frame = {
            "data": {
                "status": 2,  # 2 = last frame
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": "",
            }
        }
        await ws.send(json.dumps(end_frame))

        return {"chunk_count": chunk_count, "timeout_hit": timeout_hit}

    async def _receive_result(self, ws) -> str:
        """Receive ASR result from WebSocket.

        Args:
            ws: WebSocket connection

        Returns:
            str: Recognized text (stripped)
        """
        result_text = ""
        async for message in ws:
            data = json.loads(message)
            code = data.get('code', -1)

            # Non-zero code indicates API error
            if code != 0:
                error_msg = data.get('message', 'Unknown error')
                logger.error("[ASR] API error: code=%d message=%s", code, error_msg)
                break

            result = data.get('data', {}).get('result', {})
            status = data.get('data', {}).get('status')

            current_text = ""
            for ws_item in result.get('ws', []):
                for cw in ws_item.get('cw', []):
                    current_text += cw.get('w', '')

            # iFlytek IAT messages are usually full-sentence snapshots, not deltas
            # Use overwrite mode to avoid repeated concatenation
            if current_text:
                if status == 2:
                    # Final result - only update if meaningful
                    if current_text.strip() and len(current_text.strip()) > 1:
                        result_text = current_text
                else:
                    result_text = current_text

            if status == 2:
                break

        return result_text.strip()


class AdaptiveVADController:
    """Adaptive VAD timeout controller.

    根据历史 ASR 轮次的表现动态调整 VAD 结束静默时长：
    - 空识别率高 → 增加 VAD timeout，避免过早结束
    - 有效语音多且速度快 → 减少 VAD timeout，提高响应速度
    """

    def __init__(self, base_vad_eos: int = ASR_VAD_EOS):
        self.base_vad_eos = base_vad_eos
        self.consecutive_empty = 0
        self.empty_rate = 0.0
        self.round_metrics: list[dict] = []

    def compute_vad_eos(self) -> int:
        """Compute adaptive VAD timeout based on metrics.

        Returns:
            int: Computed VAD EOS value in milliseconds (clamped to 800-1800)
        """
        vad = self.base_vad_eos

        # Increase timeout if many empty rounds (user not speaking clearly)
        if self.consecutive_empty >= 3:
            vad += 180
        if self.empty_rate >= 0.6:
            vad += 120

        # Decrease timeout if user speaks a lot and quickly
        if len(self.round_metrics) >= 3:
            avg_chunks = sum(
                m.get("chunk_count", 0) for m in self.round_metrics[-5:]
            ) / min(5, len(self.round_metrics))

            if avg_chunks >= 26 and self.empty_rate <= 0.35:
                vad -= 120
            elif avg_chunks >= 18 and self.empty_rate <= 0.45:
                vad -= 60

        return max(800, min(1800, vad))

    def record_round(self, chunk_count: int, timeout_hit: bool, has_result: bool):
        """Record ASR round metrics for adaptive calculation.

        Args:
            chunk_count: Number of audio chunks sent this round
            timeout_hit: Whether the audio queue timed out
            has_result: Whether recognition produced non-empty text
        """
        if has_result:
            self.consecutive_empty = 0
        else:
            self.consecutive_empty += 1

        total = len(self.round_metrics) + 1
        empty_count = sum(1 for m in self.round_metrics if not m.get("has_result"))
        if not has_result:
            empty_count += 1
        self.empty_rate = empty_count / total

        self.round_metrics.append({
            "chunk_count": chunk_count,
            "timeout_hit": timeout_hit,
            "has_result": has_result,
        })

        # Keep only last 20 rounds
        if len(self.round_metrics) > 20:
            self.round_metrics = self.round_metrics[-20:]

    def reset(self):
        """Reset all metrics to initial state."""
        self.consecutive_empty = 0
        self.empty_rate = 0.0
        self.round_metrics = []