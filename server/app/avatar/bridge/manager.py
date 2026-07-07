# -*- coding: utf-8 -*-
"""数字人实时桥接模块 — 连接前端 WebSocket、ASR 语音识别和数字人播报。

核心职责:
  - 管理前端 WebSocket 连接和消息路由
  - 处理音频流(VAD 模式下的持续语音识别)
  - 调用共享的 chat 服务获取 AI 回复
  - 驱动数字人(Avatar)进行 TTS 播报

RealtimeBridge:单用户桥接实例,持有 WebSocket、ASR 队列和 Avatar 控制器
AvatarBridgeManager:管理所有用户的 Bridge 实例(全局单例)
"""

import asyncio
import base64
import json
import re
import time
import uuid
from typing import Optional

from fastapi import WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.avatar.bridge.state import MessageType
from app.avatar.services import AvatarController
from app.avatar.services.streaming_asr import AdaptiveVADController, StreamingASRSession
from app.chat.memory.service import get_chat_memory_service
from app.chat.service import chat, get_chat_usecases
from app.config import ASR_VAD_EOS
from app.infra.logging import get_logger

logger = get_logger(__name__)


class RealtimeBridge:
    """单用户数字人桥接 — 将前端 I/O 连接到共享的无状态辅导服务。"""

    def __init__(self, user_id: int, username: str = ""):
        self.user_id = user_id
        self.username = username
        # 当前会话 ID — 由首次对话时自动创建
        self.session_id: str = ""
        # 前端 WebSocket 连接引用
        self.frontend_ws = None
        # VAD 监听模式标志
        self.is_listening = False
        # 音频输入队列（VAD 模式下持续接收 PCM 音频块）
        self.current_audio_queue: Optional[asyncio.Queue] = None

        # 数字人控制器实例
        self._avatar_controller = None
        # ASR 持续监听的后台任务
        self._asr_loop_task = None

        # Turn tracking - 用于串线保护
        self._current_turn_id: Optional[str] = None

        # Adaptive VAD controller
        self._vad_controller = AdaptiveVADController(base_vad_eos=ASR_VAD_EOS)

        # Audio chunk tracking
        self._audio_chunk_counter = 0   # 音频块计数器
        self._last_asr_text: str = ""   # 上一次 ASR 识别结果（用于去重）
        self._last_asr_at: float = 0.0  # 上一次 ASR 结果的时间戳

        # Turn defaults
        self._speech_rate: float = 1.0  # TTS 语速（0.8~1.5）
        self._need_diagram_default: bool = False  # 默认是否生成教学图
        self._enable_search_default: bool = False  # 默认是否启用联网搜索
        # 对话锁 — 串行化 turn 处理，避免并发冲突
        self._turn_lock = asyncio.Lock()
        # Pending ASR 文本缓冲区 — 当有 turn 在执行时，后续 ASR 片段追加到这里
        # 当前 turn 完成后，会将 buffer 中的文本合并为下一个 turn 的输入
        self._pending_asr_texts: list[str] = []
        # 重连标志 — 为 True 时 stream_info 由 _reconnect_avatar 统一发送（带 reconnected 标记）
        self._reconnecting: bool = False
        # 重连锁 — 防止多个 connection_lost 回调同时触发多个重连流程
        self._reconnect_lock = asyncio.Lock()

    @staticmethod
    def _repair_text_encoding(text: str) -> str:
        """Best-effort repair for mojibake like '鎮ㄥソ' -> '您好'."""
        if not text:
            return text
        # Typical mojibake markers when UTF-8 text is mis-decoded as GBK.
        mojibake_pattern = r"[\u93b4\u6d63\u9359\u9427\u93c9\u3127\u746d\u7487\u8bd8\uE1EC\u8bf7\u951b\u9286\u95c2\u68f0]"
        if not re.search(mojibake_pattern, text):
            return text
        candidates = [text]
        for src in ("gbk", "gb18030", "latin1"):
            try:
                fixed = text.encode(src).decode("utf-8")
                candidates.append(fixed)
            except Exception:
                continue

        def score(s: str) -> int:
            good = len(re.findall(r"[\u4e00-\u9fff]", s))
            bad = s.count("�")
            mojibake_hits = len(re.findall(mojibake_pattern, s))
            return good - bad - mojibake_hits

        return max(candidates, key=score)

    async def _ensure_avatar_controller(self):
        need_recreate = False
        if self._avatar_controller is None:
            need_recreate = True
        else:
            try:
                if self._avatar_controller._ws_closed:
                    need_recreate = True
            except Exception:
                need_recreate = True

        if need_recreate:
            await self._send_digital_human_state("avatar_connecting", "Connecting to Avatar service")
            if self._avatar_controller is not None:
                try:
                    await self._avatar_controller.close()
                except Exception:
                    logger.debug("[Bridge] close stale avatar controller failed", exc_info=True)
            self._avatar_controller = AvatarController()
            await self._avatar_controller.connect(
                on_reconnect_callback=self._on_avatar_reconnect
            )
            # 等待 Avatar 就绪
            asyncio.create_task(
                self._avatar_controller.receive_messages(self._on_avatar_event)
            )
            # 等待最多 20 秒
            for _ in range(40):
                if self._avatar_controller.is_ready:
                    break
                await asyncio.sleep(0.5)

            if self._avatar_controller.is_ready:
                await self._send_digital_human_state("avatar_ready", "Avatar service ready")
            else:
                await self._send_digital_human_state("error", "Avatar connection timeout")

    async def _on_avatar_reconnect(self, stream_info: dict):
        """Avatar reconnect callback."""
        if not self._frontend_ws_ready():
            return
        await self._send_to_frontend({
            "type": "stream_info",
            "data": stream_info,
        })

    async def _on_avatar_event(self, event_type: str, data: dict, turn_id: Optional[str] = None):
        """Avatar 事件回调。

        Args:
            event_type: 事件类型 (stream_info, tts_start, tts_end, connection_lost)
            data: 事件数据
            turn_id: 关联的 turn_id (tts_start/tts_end 会有, stream_info 没有)
        """
        if not self._frontend_ws_ready():
            return
        if event_type == "stream_info":
            # 重连期间 stream_info 由 _reconnect_avatar 统一发送（带 reconnected 标记）
            if self._reconnecting:
                logger.debug("[Bridge] Skipping stream_info forward during reconnect (will be sent with reconnected flag)")
                return
            await self._send_to_frontend({
                "type": "stream_info",
                "data": data,
            })
        elif event_type == "tts_start":
            # 使用 Avatar 回调传来的 turn_id，而不是 bridge 当前 turn_id
            await self._send_to_frontend({
                "type": "avatar_speaking",
                "data": data,
                "turn_id": turn_id,
            })
            # 发送 speaking 状态
            await self._send_to_frontend({
                "type": "digital_human_state",
                "state": "speaking",
                "message": "Avatar is speaking",
                "turn_id": turn_id,
            })
        elif event_type == "tts_end":
            # 使用 Avatar 回调传来的 turn_id
            await self._send_to_frontend({
                "type": "avatar_stopped",
                "data": data,
                "turn_id": turn_id,
            })
        elif event_type == "connection_lost":
            # Avatar WebSocket 连接断开 — 尝试自动重连
            reason = data.get("reason", "unknown") if isinstance(data, dict) else "unknown"
            logger.warning("[Bridge] Avatar connection lost (reason=%s), attempting auto-reconnect", reason)
            await self._send_digital_human_state("avatar_connecting", "数字人连接断开，正在重连...")
            # 异步重连，不阻塞当前事件处理
            # 使用锁防止多个 connection_lost 事件同时触发多个重连流程
            if not self._reconnect_lock.locked():
                asyncio.create_task(self._reconnect_avatar())
            else:
                logger.info("[Bridge] Reconnect already in progress, skipping duplicate trigger")

    async def _reconnect_avatar(self):
        """Avatar 连接断开后的自动重连 — 带退避重试。

        重连条件：前端 WebSocket 仍然存活（用户还在页面上）。
        如果前端已断开则放弃重连，等下次用户连接时重新初始化。

        调用方应先检查 _reconnect_lock.locked() 避免重复触发。
        """
        async with self._reconnect_lock:
            self._reconnecting = True
            max_retries = 5
            try:
                for attempt in range(1, max_retries + 1):
                    # 每次重试前检查前端是否还在线
                    if not self._frontend_ws_ready():
                        logger.info("[Bridge] Frontend disconnected, aborting avatar reconnect")
                        return

                    # 如果 turn 正在执行，等它完成再重连（避免打断正在进行的对话）
                    if self._turn_lock.locked():
                        logger.info("[Bridge] Turn in progress, waiting before reconnect attempt %d", attempt)
                        await asyncio.sleep(2)
                        continue

                    delay = min(2 ** attempt, 30)  # 指数退避: 2, 4, 8, 16, 30
                    logger.info(
                        "[Bridge] Avatar reconnect attempt %d/%d (delay=%ds)",
                        attempt, max_retries, delay,
                    )
                    await asyncio.sleep(delay)

                    # 再次检查前端
                    if not self._frontend_ws_ready():
                        logger.info("[Bridge] Frontend disconnected during reconnect wait, aborting")
                        return

                    try:
                        # 关闭旧的 controller
                        if self._avatar_controller is not None:
                            try:
                                await self._avatar_controller.close()
                            except Exception:
                                logger.debug("[Bridge] close stale avatar controller failed", exc_info=True)

                        # 创建新的 controller 并连接
                        self._avatar_controller = AvatarController()
                        await self._avatar_controller.connect(
                            on_reconnect_callback=self._on_avatar_reconnect
                        )
                        # 启动消息接收循环
                        asyncio.create_task(
                            self._avatar_controller.receive_messages(self._on_avatar_event)
                        )

                        # 等待 Avatar 就绪（最多 20 秒）
                        for _ in range(40):
                            if self._avatar_controller.is_ready:
                                break
                            await asyncio.sleep(0.5)

                        if self._avatar_controller.is_ready:
                            logger.info("[Bridge] Avatar reconnected successfully on attempt %d", attempt)
                            await self._send_digital_human_state("avatar_ready", "数字人重连成功")
                            # 重连成功后发送带 reconnected 标记的 stream_info，
                            # 让前端销毁旧播放器并重新初始化
                            if self._avatar_controller._last_stream_info:
                                await self._send_to_frontend({
                                    "type": "stream_info",
                                    "data": self._avatar_controller._last_stream_info,
                                    "reconnected": True,
                                })
                            return
                        else:
                            logger.warning("[Bridge] Avatar reconnect attempt %d: ready timeout", attempt)

                    except Exception as e:
                        logger.warning("[Bridge] Avatar reconnect attempt %d failed: %s", attempt, e)

                # 所有重试都失败
                logger.error("[Bridge] Avatar reconnect failed after %d attempts", max_retries)
                await self._send_digital_human_state("error", "数字人重连失败，请刷新页面重试")
            finally:
                self._reconnecting = False

    async def handle_frontend(self, ws):
        """处理前端 WebSocket 连接 — 主消息循环。"""
        self.frontend_ws = ws
        # 每次新连接重置 session_id，避免跨模块会话复用
        self.session_id = ""
        # 确保 AvatarController 已初始化
        try:
            await self._ensure_avatar_controller()
        except Exception as e:
            logger.warning("[Bridge] AvatarController 初始化失败: %s", e)

        # 发送已缓存的流信息（Avatar 重连场景）
        if self._avatar_controller and self._avatar_controller._last_stream_info:
            await self._send_to_frontend({
                "type": "stream_info",
                "data": self._avatar_controller._last_stream_info,
            })

        try:
            # 持续接收前端消息并路由处理
            while True:
                try:
                    message = await ws.receive_text()
                    data = json.loads(message)
                    await self._route_message(data)
                except asyncio.CancelledError:
                    logger.info("[Bridge] frontend loop cancelled")
                    raise
                except WebSocketDisconnect:
                    logger.info("[Bridge] 前端断开连接")
                    break
                except Exception as e:
                    logger.error("[Bridge] 处理消息异常: %s", e)
                    # WebSocket 状态异常（如 accept 失败）应立即退出循环
                    if isinstance(e, RuntimeError) and "accept" in str(e).lower():
                        logger.warning("[Bridge] websocket state invalid, break receive loop")
                        break
                    if self.frontend_ws is not None:
                        try:
                            await self._send_to_frontend({"type": "error", "content": str(e)})
                        except Exception:
                            break
        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            logger.info("[Bridge] handle_frontend cancelled")
            raise
        except Exception as e:
            logger.error("[Bridge] handle_frontend : %s", e, exc_info=True)
        finally:
            # 连接断开时清理 Avatar 资源
            if self._avatar_controller:
                try:
                    await self._avatar_controller.stop()
                except Exception:
                    logger.debug("[Bridge] avatar stop on disconnect failed", exc_info=True)
            self.frontend_ws = None

    def _frontend_ws_ready(self) -> bool:
        ws = self.frontend_ws
        if ws is None:
            return False
        try:
            return (
                ws.client_state == WebSocketState.CONNECTED
                and ws.application_state == WebSocketState.CONNECTED
            )
        except Exception:
            return False

    async def _send_digital_human_state(self, state: str, message: str = ""):
        """Send digital_human_state event to frontend.

        States: idle, avatar_connecting, avatar_ready, listening, recognizing, thinking, speaking, error
        """
        await self._send_to_frontend({
            "type": "digital_human_state",
            "state": state,
            "message": message,
            "turn_id": self._current_turn_id,
        })

    async def _start_new_turn(self) -> str:
        """Start a new turn - generate turn_id and send turn_start event.

        Returns:
            str: The new turn_id
        """
        self._current_turn_id = str(uuid.uuid4())
        await self._send_to_frontend({
            "type": "turn_start",
            "turn_id": self._current_turn_id,
        })
        return self._current_turn_id

    async def _send_event_with_turn_id(self, event_type: str, **kwargs):
        """Send event with current turn_id attached (if available)."""
        data = {"type": event_type, **kwargs}
        if self._current_turn_id:
            data["turn_id"] = self._current_turn_id
        await self._send_to_frontend(data)

    async def _route_message(self, data: dict):
        """前端消息路由 — 根据消息类型分发到对应的处理方法。"""
        msg_type = data.get("type", "")

        if msg_type == MessageType.AUDIO_CHUNK:
            # 音频数据块 → 放入 ASR 队列
            await self._handle_audio_chunk(data)
        elif msg_type == MessageType.AUDIO_END:
            # 音频结束 → 向 ASR 队列发送 None 终止符
            await self._handle_audio_end()
        elif msg_type == MessageType.TEXT_INPUT:
            # 文本输入 → 直接调用 chat 服务
            await self._handle_text_input(data)
        elif msg_type == MessageType.STOP_SPEAKING:
            # 停止播报 → 中断 Avatar TTS
            await self._handle_stop_speaking()
        elif msg_type == MessageType.CLEAR_HISTORY:
            # 清除历史 → 删除当前 session 的消息记录
            await self._handle_clear_history()
        elif msg_type == "start_vad":
            # 启动 VAD 监听模式
            if "need_diagram" in data:
                self._handle_set_need_diagram(data)
            self._handle_capability_flags(data)
            await self._handle_start_vad()
        elif msg_type == "stop_vad":
            # 停止 VAD 监听模式
            await self._handle_stop_vad()
        elif msg_type == "switch_session":
            # 切换会话 ID
            self.session_id = data.get("session_id", "")
        elif msg_type == "set_speech_rate":
            # 设置 TTS 语速
            self._handle_set_speech_rate(data)
        elif msg_type == "set_need_diagram":
            # 设置是否生成教学图
            self._handle_set_need_diagram(data)

    def _handle_set_speech_rate(self, data: dict):
        """Handle speech rate update from frontend."""
        raw = data.get("speech_rate", 1.0)
        try:
            rate = float(raw)
        except (TypeError, ValueError):
            rate = 1.0
        self._speech_rate = max(0.8, min(1.5, rate))

    def _handle_set_need_diagram(self, data: dict):
        """Handle default need_diagram flag for ASR-driven turns."""
        self._need_diagram_default = bool(data.get("need_diagram", False))

    def _handle_capability_flags(self, data: dict):
        """Keep text-mode tutoring capabilities active for ASR-driven turns."""
        if isinstance(data.get("session_id"), str) and data["session_id"].strip():
            self.session_id = data["session_id"].strip()
        if "enable_search" in data:
            self._enable_search_default = bool(data.get("enable_search"))

    @staticmethod
    def _normalize_url_list(value) -> list[str]:
        """Normalize websocket attachment payload into url list."""
        urls: list[str] = []
        if isinstance(value, str):
            urls.extend([u.strip() for u in value.split(",") if u.strip()])
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    text = item.strip()
                    if text:
                        urls.append(text)
                    continue
                if isinstance(item, dict):
                    raw = item.get("url") or item.get("image_url") or item.get("file_url")
                    if isinstance(raw, str) and raw.strip():
                        urls.append(raw.strip())
        return list(dict.fromkeys(urls))

    def _extract_attachments(self, data: dict) -> list[str]:
        """Extract all attachment URLs from websocket text_input payload."""
        attachments: list[str] = []

        # Legacy fields: normalize and merge
        for key in ("image_urls", "imageUrls", "image_url", "imageUrl",
                     "file_urls", "fileUrls", "file_url", "fileUrl"):
            for url in self._normalize_url_list(data.get(key)):
                attachments.append(url)

        # Unified attachments field: accepts string URLs or dicts with "url"
        raw = data.get("attachments")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, str) and item.strip():
                    attachments.append(item.strip())
                elif isinstance(item, dict):
                    url = item.get("url")
                    if isinstance(url, str) and url.strip():
                        attachments.append(url.strip())

        return list(dict.fromkeys(attachments))

    async def _handle_audio_chunk(self, data: dict):
        """Handle audio chunk from frontend."""
        audio_b64 = data.get("audio", "")
        if not audio_b64 or not self.current_audio_queue:
            return
        pcm_bytes = base64.b64decode(audio_b64)
        self._audio_chunk_counter += 1
        if self._audio_chunk_counter % 25 == 0:
            logger.info(
                "[Bridge] audio_chunk recv count=%s bytes=%s queue_size=%s",
                self._audio_chunk_counter,
                len(pcm_bytes),
                self.current_audio_queue.qsize(),
            )
        # 音频块切分（1280 字节 = 40ms @ 16kHz）
        for i in range(0, len(pcm_bytes), 1280):
            chunk = pcm_bytes[i:i + 1280]
            await self.current_audio_queue.put((time.monotonic(), chunk))

    async def _handle_audio_end(self):
        """Handle end of audio input."""
        if self.current_audio_queue:
            await self.current_audio_queue.put(None)

    async def _handle_text_input(self, data: dict):
        """Handle text input and dispatch it to the shared tutor pipeline."""
        text = data.get("text", "")
        if not text:
            return
        logger.info("[Bridge] recv text_input len=%s", len(str(text)))
        # Allow per-message speech rate override from frontend.
        if "speech_rate" in data:
            self._handle_set_speech_rate(data)
        attachments = self._extract_attachments(data)
        need_diagram = bool(data.get("need_diagram", False))
        self._need_diagram_default = need_diagram
        self._handle_capability_flags(data)
        await self._handle_user_text(
            text,
            attachments=attachments,
            need_diagram=need_diagram,
            enable_search=self._enable_search_default,
        )

    async def _handle_stop_speaking(self):
        """Stop avatar speaking."""
        if self._avatar_controller:
            await self._avatar_controller.stop()
        await self._send_to_frontend({"type": "avatar_stopped"})

    async def _handle_clear_history(self):
        """Clear current session chat history."""
        if not self.session_id:
            await self._send_to_frontend(
                {
                    "type": MessageType.HISTORY_CLEARED,
                    "data": {"session_id": "", "deleted_count": 0},
                }
            )
            return

        memory_svc = get_chat_memory_service()
        deleted_count = await memory_svc.delete_short_term_messages(user_id=self.user_id, session_id=self.session_id)
        await memory_svc.reset_session_counters(user_id=self.user_id, session_id=self.session_id)
        logger.info(
            "[Bridge] ? user=%s session=%s deleted=%s",
            self.user_id,
            self.session_id,
            deleted_count,
        )
        await self._send_to_frontend(
            {
                "type": MessageType.HISTORY_CLEARED,
                "data": {
                    "session_id": self.session_id,
                    "deleted_count": deleted_count,
                },
            }
        )

    async def _handle_start_vad(self):
        """Start VAD listening mode."""
        self.is_listening = True
        self.current_audio_queue = asyncio.Queue()
        self._audio_chunk_counter = 0
        if self._asr_loop_task is None or self._asr_loop_task.done():
            self._asr_loop_task = asyncio.create_task(self._continuous_listen_loop())
        await self._send_to_frontend({"type": "vad_state", "data": {"listening": True}})
        await self._send_digital_human_state("listening", "Listening for speech")

    async def _handle_stop_vad(self):
        """Stop VAD listening mode."""
        self.is_listening = False
        if self.current_audio_queue:
            await self.current_audio_queue.put(None)
        if self._asr_loop_task and not self._asr_loop_task.done():
            self._asr_loop_task.cancel()
        await self._send_to_frontend({"type": "vad_state", "data": {"listening": False}})
        await self._send_digital_human_state("idle", "Stopped listening")

    async def _continuous_listen_loop(self):
        """Continuous ASR loop."""
        while self.is_listening:
            try:
                await self._single_recognition_round()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("[Bridge] ASR continuous listen error: %s", e)
                await self._send_event_with_turn_id("error", content=f"语音识别异常: {e}")
                await asyncio.sleep(0.5)

    async def _single_recognition_round(self):
        """Run one ASR recognition round using StreamingASRSession."""
        if not self.current_audio_queue:
            return

        # 发送 recognizing 状态
        await self._send_digital_human_state("recognizing", "Processing speech")

        # Compute adaptive VAD EOS
        vad_eos = self._vad_controller.compute_vad_eos()

        # Create ASR session
        asr_session = StreamingASRSession(
            audio_queue=self.current_audio_queue,
            vad_eos=vad_eos,
        )

        try:
            # Run ASR recognition
            result_text = await asr_session.run()

            # Record metrics for adaptive VAD
            self._vad_controller.record_round(
                chunk_count=asr_session.chunk_count,
                timeout_hit=asr_session.timeout_hit,
                has_result=bool((result_text or "").strip()),
            )

            logger.info(
                "[Bridge] ASR round done chunks=%s timeout_hit=%s has_result=%s len=%s",
                asr_session.chunk_count,
                asr_session.timeout_hit,
                bool((result_text or "").strip()),
                len(result_text or ""),
            )

            if result_text:
                normalized = str(result_text).strip()
                if normalized:
                    now_ts = time.monotonic()
                    is_dup = normalized == self._last_asr_text
                    recent_dup = is_dup and (now_ts - self._last_asr_at < 1.6)
                    if not recent_dup:
                        self._last_asr_text = normalized
                        self._last_asr_at = now_ts
                        await self._send_to_frontend({"type": "asr_result", "content": normalized})
                        # 如果当前有 turn 正在执行（锁被持有），将文本追加到 pending buffer
                        # 而不是创建新 turn，避免前端 turn_id 过滤导致事件丢失
                        if self._turn_lock.locked():
                            logger.info(
                                "[Bridge] Turn in progress, buffering ASR text: '%s' (pending=%d)",
                                normalized[:30], len(self._pending_asr_texts),
                            )
                            self._pending_asr_texts.append(normalized)
                        else:
                            # Keep ASR loop responsive: do not block next round on LLM pipeline.
                            asyncio.create_task(
                                self._handle_user_text(
                                    normalized,
                                    need_diagram=self._need_diagram_default,
                                    enable_search=self._enable_search_default,
                                )
                            )
        except Exception as e:
            logger.error("[Bridge] ASR session failed: %s", e)
            await self._send_event_with_turn_id("error", content=f"语音识别异常: {e}")

    async def _handle_user_text(
        self,
        user_text: str,
        attachments: Optional[list[str]] = None,
        need_diagram: bool = False,
        enable_search: bool = False,
    ):
        """串行化 turn 处理 — 获取锁后再发送 turn_start，避免前端 turn_id 过滤问题。

        关键修复：在获取锁之后才发送 turn_start，确保前端 activeTurnId 与实际执行
        的 turn 一致。之前的实现在等锁前就发送 turn_start，导致多个排队 turn 的
        turn_start 覆盖前端的 activeTurnId，使正在执行的 turn 事件被前端过滤掉。
        """
        async with self._turn_lock:
            # 合并 pending ASR 文本缓冲区
            merged_text = user_text
            if self._pending_asr_texts:
                # 检查是否与 pending 文本重复
                for pending in self._pending_asr_texts:
                    if pending not in merged_text:
                        merged_text += pending
                logger.info(
                    "[Bridge] Merged %d pending ASR texts into turn (original='%s' merged='%s')",
                    len(self._pending_asr_texts),
                    user_text[:30],
                    merged_text[:50],
                )
                self._pending_asr_texts.clear()

            # 在锁内生成并发送 turn_id，确保前端 activeTurnId 与实际 turn 一致
            new_turn_id = str(uuid.uuid4())
            self._current_turn_id = new_turn_id
            await self._send_to_frontend({
                "type": "turn_start",
                "turn_id": new_turn_id,
            })
            logger.info("[Bridge] Sent turn_start turn_id=%s (after acquiring lock)", new_turn_id)

            # 新 turn 开始时打断旧播报
            # 检查多个状态：is_speaking、sentence_queue 非空、_playback_task 未完成
            if self._avatar_controller:
                avatar = self._avatar_controller
                has_pending_playback = (
                    avatar.is_speaking
                    or not avatar.sentence_queue.empty()
                    or (avatar._playback_task is not None and not avatar._playback_task.done())
                )
                if has_pending_playback:
                    logger.info(
                        "[Bridge] Interrupting old Avatar播报 for new turn (speaking=%s, queue=%s, task=%s)",
                        avatar.is_speaking,
                        avatar.sentence_queue.qsize(),
                        avatar._playback_task is not None and not avatar._playback_task.done(),
                    )
                    await avatar.stop()
                    await self._send_digital_human_state("idle", "Old speech interrupted")

            logger.info("[Bridge] Acquired lock, processing turn_id=%s", new_turn_id)

            await self._run_user_text_turn(
                user_text=merged_text,
                attachments=attachments,
                need_diagram=need_diagram,
                enable_search=enable_search,
            )

            # Turn 完成后清空 pending buffer — 这些文本只是 VAD 分片产生的噪音，
            # 不应该自动创建新 turn。用户下一轮说话会触发新的 ASR 识别。
            if self._pending_asr_texts:
                logger.info(
                    "[Bridge] Discarding %d pending ASR texts (VAD fragment noise): %s",
                    len(self._pending_asr_texts),
                    [t[:20] for t in self._pending_asr_texts],
                )
                self._pending_asr_texts.clear()

    async def _run_user_text_turn(
        self,
        user_text: str,
        attachments: Optional[list[str]] = None,
        need_diagram: bool = False,
        enable_search: bool = False,
    ):
        """执行一轮完整的对话 turn：调用 chat 服务 → 流式处理事件 → 触发 Avatar 播报。"""
        # 合并附件 URL 并去重
        merged_attachments = list(dict.fromkeys(attachments or []))
        chat_uc = get_chat_usecases()
        # 自动创建会话（首次对话时）
        if not self.session_id:
            session = await chat_uc.create_session(user_id=self.user_id)
            self.session_id = str(session["id"])

        attachment_records = [{"url": url} for url in merged_attachments]
        user_message = await chat_uc.create_user_message(
            user_id=self.user_id,
            session_id=self.session_id,
            text=user_text,
            attachments=attachment_records,
        )
        user_message_id = user_message.id
        if user_message_id is None:
            raise RuntimeError("保存用户消息失败")

        # 发送 thinking 状态
        await self._send_digital_human_state("thinking", "Processing user input")

        full_response = ""
        event_count = 0
        stream_failed = False
        fail_reason = ""
        last_diagram_payload = None
        diagram_forwarded = False
        try:
            async def _consume_stream_events():
                """消费 chat 服务的 SSE 事件流，转发 token/status/error/diagram 事件。"""
                nonlocal event_count, full_response, last_diagram_payload, diagram_forwarded
                nonlocal stream_failed, fail_reason
                async for event in chat(
                    user_message_id=user_message_id,
                    user_id=self.user_id,
                    username=self.username or f"user_{self.user_id}",
                    session_id=self.session_id,
                    user_input=user_text,
                    attachments=merged_attachments,
                    need_teaching_diagram=need_diagram,
                    enable_web_search=enable_search,
                ):
                    event_count += 1
                    if not self.frontend_ws:
                        logger.warning("[Bridge] WebSocket disconnected, stop processing events")
                        break

                    event_type = str(event.get("event", ""))
                    payload = event.get("data")
                    logger.info("[Bridge] event#%d type=%s payload_type=%s preview=%s",
                                event_count, event_type, type(payload).__name__,
                                str(payload)[:120] if payload else "None")

                    if event_type == "token":
                        # 流式 token → 修复编码后转发给前端
                        content = self._repair_text_encoding(str(payload or ""))
                        if content:
                            full_response += content
                            if self.frontend_ws:
                                await self._send_event_with_turn_id("assistant_chunk", content=content)

                    elif event_type == "status":
                        # 状态事件 → 转发给前端
                        if self.frontend_ws and isinstance(payload, dict):
                            await self._send_event_with_turn_id("status", data=payload)

                    elif event_type == "agent_status":
                        # Agent 思考过程事件 → 转发给前端显示思考进度
                        if self.frontend_ws and isinstance(payload, dict):
                            await self._send_event_with_turn_id("status", data=payload)

                    elif event_type == "error":
                        # 错误事件 → 标记失败并通知前端
                        stream_failed = True
                        fail_reason = str(payload or "数字人回答失败，请重试")
                        if self.frontend_ws:
                            await self._send_digital_human_state("error", fail_reason)
                            await self._send_event_with_turn_id("error", content=fail_reason)

                    elif event_type == "diagram":
                        # 教学图事件 → 缓存并转发给前端
                        last_diagram_payload = payload
                        if self.frontend_ws and not diagram_forwarded:
                            await self._send_event_with_turn_id("diagram", data=payload)
                            diagram_forwarded = True

                    elif event_type == "done":
                        # 完成事件 → 提取最终回复和教学图
                        if isinstance(payload, dict):
                            maybe_text = self._repair_text_encoding(
                                str(payload.get("full_response", "") or payload.get("response", "") or "")
                            )
                            if maybe_text and not full_response:
                                full_response = maybe_text
                                if self.frontend_ws:
                                    await self._send_event_with_turn_id("assistant_chunk", content=full_response)
                            resources = payload.get("resources")
                            diagram_payload = None
                            if isinstance(resources, dict):
                                diagram_payload = resources.get("teaching_diagram") or resources.get("diagram")
                            if not diagram_payload:
                                diagram_payload = payload.get("teaching_diagram") or payload.get("diagram")
                            if diagram_payload:
                                last_diagram_payload = diagram_payload
                            if diagram_payload and self.frontend_ws and not diagram_forwarded:
                                await self._send_event_with_turn_id("diagram", data=diagram_payload)
                                diagram_forwarded = True

            # 执行事件流消费（不设固定超时，长回复+教学图可能超过 120s）
            await _consume_stream_events()
        except asyncio.CancelledError:
            stream_failed = True
            fail_reason = "cancelled"
            logger.info(
                "[Bridge] stream cancelled user=%s session=%s",
                self.user_id,
                self.session_id,
            )
            raise
        except Exception as exc:
            stream_failed = True
            fail_reason = str(exc)
            logger.exception("[Bridge] stream failed user=%s session=%s", self.user_id, self.session_id)
            if self.frontend_ws:
                await self._send_digital_human_state("error", str(exc))
                await self._send_event_with_turn_id("error", content=f"数字人回答失败: {fail_reason}")
        finally:
            logger.info(
                "[Bridge] stream ended events=%d full_response_len=%d failed=%s",
                event_count,
                len(full_response),
                stream_failed,
            )

            # 流结束后始终发送完成标记
            if self.frontend_ws:
                if last_diagram_payload is not None and not diagram_forwarded:
                    await self._send_event_with_turn_id("diagram", data=last_diagram_payload)
                await self._send_event_with_turn_id("assistant_complete")

            # 触发数字人 TTS 播报（异步执行，不阻塞响应）
            if full_response.strip() and self._avatar_controller:
                logger.info(
                    "[Bridge] trigger avatar speak len=%s ws_alive=%s",
                    len(full_response.strip()),
                    bool(self.frontend_ws),
                )
                # 不在这里发送 speaking 状态，等 tts_start 回调时再发送
                asyncio.create_task(
                    self._avatar_controller.speak(
                        full_response.strip(),
                        speech_rate=self._speech_rate,
                        turn_id=self._current_turn_id,
                    )
                )

    async def _send_to_frontend(self, data: dict):
        """Send message to frontend websocket."""
        if not self._frontend_ws_ready():
            return
        try:
            await self.frontend_ws.send_json(data)
        except Exception as e:
            logger.error("[Bridge] send frontend failed: %s", e)
            # WebSocket may already be closed/invalid
            self.frontend_ws = None

    async def close(self):
        """Close bridge resources."""
        self.is_listening = False
        if self._asr_loop_task and not self._asr_loop_task.done():
            self._asr_loop_task.cancel()
        if self._avatar_controller:
            await self._avatar_controller.close()


class AvatarBridgeManager:
    """管理所有用户的 RealtimeBridge 实例（全局单例）。

    每个用户对应一个 Bridge 实例，通过 user_id 索引。
    使用 per-user 锁确保并发安全。
    """

    def __init__(self):
        self._bridges: dict[int, RealtimeBridge] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def _get_lock(self, user_id: int) -> asyncio.Lock:
        """获取或创建用户级别的异步锁。"""
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    async def get_or_create_bridge(self, user_id: int, username: str = "") -> RealtimeBridge:
        """获取或创建用户的 Bridge 实例（线程安全）。"""
        lock = self._get_lock(user_id)
        async with lock:
            if user_id not in self._bridges:
                bridge = RealtimeBridge(user_id=user_id, username=username)
                self._bridges[user_id] = bridge
            return self._bridges[user_id]

    async def get_status(self, user_id: int) -> dict:
        """查询用户的 Bridge 状态（连接状态、监听状态等）。"""
        bridge = self._bridges.get(user_id)
        if not bridge:
            return {"connected": False, "state": "idle"}
        return {
            "connected": bridge.frontend_ws is not None,
            "state": "idle",
            "session_id": bridge.session_id,
            "is_listening": bridge.is_listening,
        }

    async def get_stream_info(self, user_id: int) -> dict | None:
        """获取用户的 Avatar 视频流信息。"""
        bridge = self._bridges.get(user_id)
        if not bridge or not bridge._avatar_controller:
            return None
        return bridge._avatar_controller._last_stream_info

    async def stop(self, user_id: int):
        """停止用户的 Avatar 播报。"""
        bridge = self._bridges.get(user_id)
        if bridge and bridge._avatar_controller:
            await bridge._avatar_controller.stop()

    async def cleanup(self, user_id: int):
        """清理用户的 Bridge 实例（断开连接、释放资源）。"""
        bridge = self._bridges.pop(user_id, None)
        self._locks.pop(user_id, None)
        if bridge:
            await bridge.close()


# 全局单例 — 所有路由共享同一个 BridgeManager
avatar_bridge_manager = AvatarBridgeManager()
