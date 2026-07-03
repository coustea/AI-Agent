"""数字人控制模块 — 管理与讯飞 Avatar 服务的 WebSocket 连接和 TTS 播报。

AvatarController 职责：
  - 连接讯飞虚拟人 WebSocket 服务
  - 接收视频流信息（stream_info）和 TTS 事件
  - 管理播报队列（sentence_queue），串行执行 TTS
  - 支持重试、心跳保连、停止播报等操作
"""

import asyncio
import json
import uuid
from typing import Optional

import websockets

from app.avatar.services import xfyun_auth
from app.config import (
    AVATAR_ANCHOR,
    AVATAR_API_KEY,
    AVATAR_API_SECRET,
    AVATAR_APP_ID,
    AVATAR_URL,
    AVATAR_VCN,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)


class AvatarController:
    """讯飞虚拟人控制器 — 管理 WebSocket 连接和 TTS 播报队列。"""

    # 最大重试次数
    MAX_RETRIES = 3
    # 重试间隔（秒）
    RETRY_DELAY = 0.5
    # 心跳保活间隔（秒）
    KEEPALIVE_INTERVAL = 10

    def __init__(self):
        self.ws = None
        self.is_ready = False
        self.is_speaking = False
        # 句子播报队列 — 支持多个句子串行播报
        self.sentence_queue = asyncio.Queue()
        self._playback_task = None
        self._keepalive_task = None
        self._on_reconnect_callback = None
        self._last_stream_info = None
        self._event_callback = None
        # 当前播报的 turn_id — 用于回调时绑定正确的 turn
        self._current_speak_turn_id: Optional[str] = None

    @property
    def _ws_closed(self) -> bool:
        """检查 WebSocket 是否已关闭（兼容不同 websockets 版本）。"""
        if self.ws is None:
            return True
        if hasattr(self.ws, "state"):
            from websockets.protocol import State
            return self.ws.state != State.OPEN
        return getattr(self.ws, "closed", True)

    async def connect(self, on_reconnect_callback=None):
        """连接到讯飞 Avatar 服务 — 发送启动指令并启动心跳。"""
        self._on_reconnect_callback = on_reconnect_callback

        try:
            # 生成带签名的鉴权 URL
            auth_url = xfyun_auth.assemble_auth_url(
                AVATAR_URL, "GET", AVATAR_API_KEY, AVATAR_API_SECRET
            )
            self.ws = await websockets.connect(auth_url)

            # 发送启动指令（含虚拟人 ID、TTS 声音、视频分辨率等参数）
            start_msg = {
                "header": {
                    "app_id": AVATAR_APP_ID,
                    "request_id": str(uuid.uuid4()),
                    "ctrl": "start",
                },
                "parameter": {
                    "tts": {"vcn": AVATAR_VCN},
                    "avatar": {
                        "stream": {"protocol": "xrtc"},
                        "avatar_id": AVATAR_ANCHOR,
                        "width": 720,
                        "height": 1280,
                    },
                },
            }
            await self.ws.send(json.dumps(start_msg))
            logger.info("Avatar service connected")

            # 启动心跳保活任务
            if self._keepalive_task is None or self._keepalive_task.done():
                self._keepalive_task = asyncio.create_task(self._keepalive_loop())

        except Exception as e:
            logger.error(f"Failed to connect to avatar service: {e}")
            raise RuntimeError(f"Failed to connect to avatar service: {e}")

    async def receive_messages(self, callback):
        """持续接收 Avatar 服务的事件消息（stream_info、tts_start、tts_end）。

        Args:
            callback: 回调函数，签名为 async (event_type: str, data: dict, turn_id: Optional[str])
        """
        if not self.ws:
            raise RuntimeError("Avatar not connected")

        self._event_callback = callback

        try:
            logger.debug("Starting to listen for avatar messages...")
            async for message in self.ws:
                data = json.loads(message)
                logger.debug(f"Received avatar message: {data.get('header', {})}")

                # 非零 code 表示 API 错误
                if data["header"]["code"] != 0:
                    logger.error(f"Avatar error: {data}")
                    continue

                payload = data.get("payload", {})
                if "avatar" not in payload:
                    continue

                avatar_data = payload["avatar"]
                event_type = avatar_data.get("event_type")

                if event_type == "stream_info":
                    # 视频流就绪 — 标记 Avatar 可用，触发回调
                    self.is_ready = True
                    self._last_stream_info = avatar_data
                    # stream_info 不关联特定 turn
                    await callback("stream_info", avatar_data, None)
                    logger.info(
                        f"Avatar video stream ready: {avatar_data.get('stream_url')}"
                    )
                    # 如果队列中有待播报的句子，立即开始播放
                    if (not self.sentence_queue.empty()) and (
                        self._playback_task is None or self._playback_task.done()
                    ):
                        logger.info("Avatar ready: resume queued speech playback")
                        self._playback_task = asyncio.create_task(self._process_queue())

                elif event_type == "tts_start":
                    # TTS 开始播报 — 使用当前播报的 turn_id
                    self.is_speaking = True
                    turn_id = self._current_speak_turn_id
                    await callback("tts_start", avatar_data, turn_id)
                    logger.debug(f"Avatar started speaking (turn_id: {turn_id})")

                elif event_type == "tts_end":
                    # TTS 播报结束 — 使用当前播报的 turn_id
                    self.is_speaking = False
                    turn_id = self._current_speak_turn_id
                    await callback("tts_end", avatar_data, turn_id)
                    logger.debug(f"Avatar finished speaking (turn_id: {turn_id})")

            logger.warning("Avatar message loop exited normally (connection closed)")

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Avatar connection closed: {e}")
        except Exception as e:
            logger.error(f"Failed to receive avatar messages: {e}", exc_info=True)
            raise RuntimeError(f"Failed to receive avatar messages: {e}")

    async def speak(self, text: str, speech_rate: float = 1.0, turn_id: Optional[str] = None):
        """将文本加入播报队列 — Avatar 就绪后自动开始播放。

        Args:
            text: 要播报的文本
            speech_rate: 语速 (0.8~1.5)
            turn_id: 关联的 turn_id，用于回调时绑定正确的 turn
        """
        if not text:
            logger.warning("Empty text, skipping speech")
            return

        # 限制语速在 0.8~1.5 范围内
        safe_rate = max(0.8, min(1.5, float(speech_rate)))
        # 将 turn_id 存入队列，但不在入队时设置 _current_speak_turn_id
        # _current_speak_turn_id 只在 _process_queue() 取出当前项时设置
        await self.sentence_queue.put((text, safe_rate, turn_id))
        logger.debug(
            f"Sentence queued: {text[:30]}... (queue size: {self.sentence_queue.qsize()}, turn_id: {turn_id})"
        )

        # Avatar 未就绪时仅入队，等待 stream_info 事件后自动播放
        if not self.is_ready:
            logger.debug("Avatar not ready, sentence queued for later")
            return

        # 启动队列处理任务
        if self._playback_task is None or self._playback_task.done():
            self._playback_task = asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """串行处理播报队列 — 逐句发送 TTS 指令并等待播报完成。

        改进的等待机制：
        1. 发送 text_driver 后等待 tts_start 事件（最长 3 秒超时）
        2. 收到 tts_start 后等待 tts_end 事件（最长 30 秒超时）
        3. 未收到 tts_start 时也不立即发送下一句，避免重叠
        """
        logger.info("Starting to process sentence queue")

        while not self.sentence_queue.empty():
            sentence, speech_rate, turn_id = await self.sentence_queue.get()
            # 设置当前播报的 turn_id
            self._current_speak_turn_id = turn_id

            # 带重试的 TTS 发送
            success = await self._speak_with_retry(sentence, speech_rate)

            if not success:
                logger.error(
                    f"Sentence failed after {self.MAX_RETRIES} retries: {sentence[:30]}..."
                )
                continue

            logger.debug(f"Avatar speech dispatched: {sentence[:30]}... (turn_id: {turn_id})")

            # Wait for tts_start event (max 3 seconds)
            wait_start_count = 30  # 3 seconds at 0.1s per iteration
            while not self.is_speaking and wait_start_count > 0:
                await asyncio.sleep(0.1)
                wait_start_count -= 1

            if not self.is_speaking:
                # tts_start not received within timeout
                logger.warning(
                    f"tts_start timeout (3s) for: {sentence[:30]}... - waiting extra 1.5s before next sentence"
                )
                # Don't immediately send next sentence - wait to avoid overlap
                await asyncio.sleep(1.5)
                self._current_speak_turn_id = None
                continue

            # Wait for tts_end event (max 30 seconds)
            wait_end_timeout = 300  # 30 seconds at 0.1s per iteration
            while self.is_speaking and wait_end_timeout > 0:
                await asyncio.sleep(0.1)
                wait_end_timeout -= 1

            if self.is_speaking:
                logger.warning(
                    f"Avatar speech timeout (30s), forcing end: {sentence[:30]}..."
                )
                self.is_speaking = False

            logger.debug(f"Sentence completed: {sentence[:30]}... (turn_id: {turn_id})")
            # 清除当前播报的 turn_id
            self._current_speak_turn_id = None

        logger.info("Sentence queue processing completed")

    async def _speak_with_retry(self, text: str, speech_rate: float = 1.0) -> bool:
        """带重试机制的 TTS 发送。"""
        for attempt in range(self.MAX_RETRIES):
            try:
                await self._speak_immediate(text, speech_rate)
                return True
            except Exception as e:
                logger.warning(
                    f"Speech failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)

        return False

    async def _speak_immediate(self, text: str, speech_rate: float = 1.0):
        """立即发送 TTS 播报指令（无重试）。"""
        if not self.ws or self._ws_closed:
            logger.warning("Avatar connection lost, skipping speech (no auto-reconnect)")
            raise RuntimeError("Avatar connection lost, cannot send speech command")

        # 构造 text_driver 指令 — 语速范围 40~75（对应 0.8~1.5 倍速）
        text_msg = {
            "header": {
                "app_id": AVATAR_APP_ID,
                "request_id": str(uuid.uuid4()),
                "ctrl": "text_driver",
            },
            "parameter": {
                "tts": {
                    "vcn": AVATAR_VCN,
                    "speed": int(max(0.8, min(1.5, speech_rate)) * 50),
                },
                "avatar_dispatch": {"interactive_mode": 1},
            },
            "payload": {"text": {"content": text}},
        }

        try:
            await self.ws.send(json.dumps(text_msg))
            logger.info(f"Avatar speaking: {text[:50]}...")
        except Exception as e:
            logger.error(f"Failed to send speech command: {e}")
            self.ws = None
            self.is_ready = False
            raise RuntimeError(f"Failed to send speech command: {e}")

    async def stop(self):
        """停止播报并清空队列 — 发送 stop 控制指令。"""
        # 清空播报队列
        while not self.sentence_queue.empty():
            try:
                self.sentence_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # 取消正在执行的播放任务
        if self._playback_task and not self._playback_task.done():
            self._playback_task.cancel()

        if not self.ws or self._ws_closed:
            return

        # 发送 stop 控制指令
        stop_msg = {
            "header": {
                "app_id": AVATAR_APP_ID,
                "request_id": str(uuid.uuid4()),
                "ctrl": "stop",
            }
        }

        try:
            await self.ws.send(json.dumps(stop_msg))
            self.is_speaking = False
            logger.info("Avatar stopped, queue cleared")
        except websockets.exceptions.ConnectionClosedOK:
            self.is_speaking = False
            logger.debug("Avatar stop skipped: websocket already closed normally")
        except Exception as e:
            logger.error(f"Failed to stop avatar: {e}")

    async def close(self):
        """关闭 Avatar WebSocket 连接并停止心跳。"""
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()

        if self.ws:
            await self.ws.close()
            logger.info("Avatar connection closed")

    async def _keepalive_loop(self):
        """心跳保活循环 — 定期 ping 检测连接是否存活。"""
        try:
            while True:
                await asyncio.sleep(self.KEEPALIVE_INTERVAL)

                if self.ws and not self._ws_closed:
                    try:
                        pong = await self.ws.ping()
                        await asyncio.wait_for(pong, timeout=10)
                        logger.debug("Heartbeat successful")
                    except asyncio.TimeoutError:
                        logger.warning("Heartbeat timeout, connection may be lost")
                    except Exception as e:
                        logger.warning(f"Heartbeat failed: {e}")
        except asyncio.CancelledError:
            logger.info("Heartbeat task stopped")
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")
