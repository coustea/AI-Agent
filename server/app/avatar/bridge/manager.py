# -*- coding: utf-8 -*-
"""Digital-human realtime bridge for the shared TutorAgent chat pipeline.

The bridge owns WebSocket, ASR and avatar playback concerns only. Tutoring
decisions run through ``app.chat.service`` and its stateless ``TutorAgent``.
"""

import asyncio
import json
import re
from typing import Optional

from fastapi import WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.infra.logging import get_logger

logger = get_logger(__name__)


class RealtimeBridge:
    """Connect digital-human I/O to the shared stateless tutoring service."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.session_id: str = ""
        self.frontend_ws = None  # WebSocket 
        self.is_listening = False
        self.current_audio_queue: Optional[asyncio.Queue] = None

        # Avatar 控制器
        self._avatar_controller = None
        self._asr_loop_task = None

        # VAD 参数
        self._vad_eos = 1000
        self._consecutive_empty = 0
        self._empty_rate = 0.0
        self._round_metrics: list[dict] = []
        self._audio_chunk_counter = 0
        self._last_asr_text: str = ""
        self._last_asr_at: float = 0.0
        self._speech_rate: float = 1.0
        self._need_diagram_default: bool = False
        self._enable_search_default: bool = False
        self._generate_video_default: bool = False
        self._enable_long_term_memory_default: bool = False
        self._history_default: Optional[list[dict]] = None
        self._turn_lock = asyncio.Lock()

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
            if self._avatar_controller is not None:
                try:
                    await self._avatar_controller.close()
                except Exception:
                    logger.debug("[Bridge] close stale avatar controller failed", exc_info=True)
            from app.avatar.services.avatar_ctrl import AvatarController
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

    async def _on_avatar_reconnect(self, stream_info: dict):
        """Avatar reconnect callback."""
        if not self._frontend_ws_ready():
            return
        await self._send_to_frontend({
            "type": "stream_info",
            "data": stream_info,
        })

    async def _on_avatar_event(self, event_type: str, data: dict):
        """Avatar 事件回调。"""
        if not self._frontend_ws_ready():
            return
        if event_type == "stream_info":
            await self._send_to_frontend({
                "type": "stream_info",
                "data": data,
            })

    async def handle_frontend(self, ws):
        """处理前端 WebSocket 连接。"""
        self.frontend_ws = ws
        # Avoid reusing stale session id across different module pipelines.
        self.session_id = ""
        # 确保 AvatarController 已初始化
        try:
            await self._ensure_avatar_controller()
        except Exception as e:
            logger.warning("[Bridge] AvatarController 初始化失败: %s", e)

        # 发送已缓存的流信息
        if self._avatar_controller and self._avatar_controller._last_stream_info:
            await self._send_to_frontend({
                "type": "stream_info",
                "data": self._avatar_controller._last_stream_info,
            })

        try:
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
                    # Fatal websocket state errors should break the receive loop,
                    # otherwise we'll spin and spam logs.
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

    async def _route_message(self, data: dict):
        """Route frontend message by type."""
        from app.avatar.bridge.state import MessageType

        msg_type = data.get("type", "")

        if msg_type == MessageType.AUDIO_CHUNK:
            await self._handle_audio_chunk(data)
        elif msg_type == MessageType.AUDIO_END:
            await self._handle_audio_end()
        elif msg_type == MessageType.TEXT_INPUT:
            await self._handle_text_input(data)
        elif msg_type == MessageType.STOP_SPEAKING:
            await self._handle_stop_speaking()
        elif msg_type == MessageType.CLEAR_HISTORY:
            await self._handle_clear_history()
        elif msg_type == "start_vad":
            if "need_diagram" in data:
                self._handle_set_need_diagram(data)
            self._handle_capability_flags(data)
            await self._handle_start_vad()
        elif msg_type == "stop_vad":
            await self._handle_stop_vad()
        elif msg_type == "switch_session":
            self.session_id = data.get("session_id", "")
        elif msg_type == "set_speech_rate":
            self._handle_set_speech_rate(data)
        elif msg_type == "set_need_diagram":
            self._handle_set_need_diagram(data)

    def _handle_set_speech_rate(self, data: dict):
        """Handle speech rate update from frontend."""
        raw = data.get("speech_rate", 1.0)
        try:
            rate = float(raw)
        except (TypeError, ValueError):
            rate = 1.0
        self._speech_rate = max(0.5, min(2.0, rate))

    def _handle_set_need_diagram(self, data: dict):
        """Handle default need_diagram flag for ASR-driven turns."""
        self._need_diagram_default = bool(data.get("need_diagram", False))

    def _handle_capability_flags(self, data: dict):
        """Keep text-mode tutoring capabilities active for ASR-driven turns."""
        if isinstance(data.get("session_id"), str) and data["session_id"].strip():
            self.session_id = data["session_id"].strip()
        if isinstance(data.get("history"), list):
            self._history_default = data["history"]
        if "enable_search" in data:
            self._enable_search_default = bool(data.get("enable_search"))
        if "generate_video" in data:
            self._generate_video_default = bool(data.get("generate_video"))
        if "enable_long_term_memory" in data:
            self._enable_long_term_memory_default = bool(data.get("enable_long_term_memory"))

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

    def _extract_attachment_urls(self, data: dict) -> tuple[list[str], list[str]]:
        """Extract image/file urls from websocket text_input payload."""
        image_urls = (
            self._normalize_url_list(data.get("image_urls"))
            or self._normalize_url_list(data.get("imageUrls"))
            or self._normalize_url_list(data.get("image_url"))
            or self._normalize_url_list(data.get("imageUrl"))
        )
        file_urls = (
            self._normalize_url_list(data.get("file_urls"))
            or self._normalize_url_list(data.get("fileUrls"))
            or self._normalize_url_list(data.get("file_url"))
            or self._normalize_url_list(data.get("fileUrl"))
        )

        attachments = data.get("attachments")
        if isinstance(attachments, list):
            for item in attachments:
                if not isinstance(item, dict):
                    continue
                url = item.get("url")
                kind = str(item.get("type", "")).lower()
                if not isinstance(url, str) or not url.strip():
                    continue
                if kind == "image":
                    image_urls.append(url.strip())
                elif kind in {"file", "document", "doc"}:
                    file_urls.append(url.strip())

        return list(dict.fromkeys(image_urls)), list(dict.fromkeys(file_urls))

    async def _handle_audio_chunk(self, data: dict):
        """Handle audio chunk from frontend."""
        import base64
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
        import time
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
        image_urls, file_urls = self._extract_attachment_urls(data)
        need_diagram = bool(data.get("need_diagram", False))
        self._need_diagram_default = need_diagram
        self._handle_capability_flags(data)
        raw_history = data.get("history")
        history = raw_history if isinstance(raw_history, list) else None
        await self._handle_user_text(
            text,
            image_urls=image_urls,
            file_urls=file_urls,
            need_diagram=need_diagram,
            enable_search=self._enable_search_default,
            generate_video=self._generate_video_default,
            enable_long_term_memory=self._enable_long_term_memory_default,
            history=history,
        )

    async def _handle_stop_speaking(self):
        """Stop avatar speaking."""
        if self._avatar_controller:
            await self._avatar_controller.stop()

    async def _handle_clear_history(self):
        """Clear current session chat history."""
        from app.avatar.bridge.state import MessageType
        from app.memory import MemoryService
        from app.chat import CHAT_MODULE_NAME

        memory_layer = MemoryService(module=CHAT_MODULE_NAME)

        if not self.session_id:
            await self._send_to_frontend(
                {
                    "type": MessageType.HISTORY_CLEARED,
                    "data": {"session_id": "", "deleted_count": 0},
                }
            )
            return

        deleted_count = await memory_layer.delete_short_term_messages(
            user_id=self.user_id,
            session_id=self.session_id,
        )
        await memory_layer.reset_session_counters(user_id=self.user_id, session_id=self.session_id)
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

    async def _handle_stop_vad(self):
        """Stop VAD listening mode."""
        self.is_listening = False
        if self.current_audio_queue:
            await self.current_audio_queue.put(None)
        if self._asr_loop_task and not self._asr_loop_task.done():
            self._asr_loop_task.cancel()
        await self._send_to_frontend({"type": "vad_state", "data": {"listening": False}})

    async def _continuous_listen_loop(self):
        """Continuous ASR loop."""
        from app.avatar.services.asr import IatClient
        from app.avatar.services.xfyun_auth import assemble_auth_url
        from app.config import ASR_APP_ID, ASR_API_KEY, ASR_API_SECRET, AVATAR_IAT_URL
        import websockets, json, base64, time

        while self.is_listening:
            try:
                await self._single_recognition_round()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("[Bridge] ASR : %s", e)
                await self._send_to_frontend({
                    "type": "error",
                    "content": f"语音识别异常: {e}",
                })
                await asyncio.sleep(0.5)

    async def _single_recognition_round(self):
        """Run one ASR recognition round."""
        import websockets, json, base64, time, asyncio
        from app.avatar.services.xfyun_auth import assemble_auth_url
        from app.config import ASR_APP_ID, ASR_API_KEY, ASR_API_SECRET, AVATAR_IAT_URL

        if not self.current_audio_queue:
            return

        # 
        now_ts = time.monotonic()
        pruned = 0
        temp = []
        while not self.current_audio_queue.empty():
            try:
                item = self.current_audio_queue.get_nowait()
                if item is None:
                    temp.append(None)
                    break
                ts, chunk = item
                # Keep a larger recent-audio window to avoid dropping valid speech
                # when the ASR round loop is slightly delayed.
                if now_ts - ts < 2.0:
                    temp.append((ts, chunk))
                else:
                    pruned += 1
            except asyncio.QueueEmpty:
                break
        for item in temp:
            await self.current_audio_queue.put(item)

        if pruned:
            logger.debug("[Bridge] ? %d", pruned)

        # Wait for first audio chunk before opening ASR websocket.
        # This avoids frequent "server read msg timeout" when user is not speaking yet.
        try:
            first_item = await asyncio.wait_for(self.current_audio_queue.get(), timeout=15.0)
        except asyncio.TimeoutError:
            return

        if first_item is None:
            return

        _, first_chunk = first_item

        # VAD 参数
        vad_eos = self._compute_adaptive_vad_eos()

        auth_url = assemble_auth_url(AVATAR_IAT_URL, 'GET', ASR_API_KEY, ASR_API_SECRET)
        async with websockets.connect(auth_url) as ws:
            send_task = asyncio.create_task(self._send_audio_to_asr(ws, first_chunk, vad_eos))
            recv_task = asyncio.create_task(self._receive_asr_result(ws))

            result_text = await recv_task

            if not send_task.done():
                send_task.cancel()
            send_result = await asyncio.gather(send_task, return_exceptions=True)
            send_summary = send_result[0] if send_result else {"chunk_count": 0, "timeout_hit": False}
            if not isinstance(send_summary, dict):
                send_summary = {"chunk_count": 0, "timeout_hit": False}

            chunk_count = int(send_summary.get("chunk_count", 0))
            timeout_hit = bool(send_summary.get("timeout_hit", False))
            has_result = bool((result_text or "").strip())
            self._record_asr_round_metrics(chunk_count=chunk_count, timeout_hit=timeout_hit, has_result=has_result)
            logger.info(
                "[Bridge] ASR round done chunks=%s timeout_hit=%s has_result=%s len=%s",
                chunk_count,
                timeout_hit,
                has_result,
                len(result_text or ""),
            )

            if result_text:
                normalized = str(result_text).strip()
                if normalized:
                    import time
                    now_ts = time.monotonic()
                    is_dup = normalized == self._last_asr_text
                    recent_dup = is_dup and (now_ts - self._last_asr_at < 1.6)
                    if not recent_dup:
                        self._last_asr_text = normalized
                        self._last_asr_at = now_ts
                        await self._send_to_frontend({"type": "asr_result", "content": normalized})
                        # Keep ASR loop responsive: do not block next round on LLM pipeline.
                        asyncio.create_task(
                            self._handle_user_text(
                                normalized,
                                need_diagram=self._need_diagram_default,
                                enable_search=self._enable_search_default,
                                generate_video=self._generate_video_default,
                                enable_long_term_memory=self._enable_long_term_memory_default,
                                history=self._history_default,
                            )
                        )
            else:
                self._consecutive_empty += 1

    async def _receive_asr_result(self, ws) -> str:
        """Receive ASR result text."""
        result_text = ""
        async for message in ws:
            data = json.loads(message)
            if data.get('code', -1) != 0:
                break
            result = data.get('data', {}).get('result', {})
            status = data.get('data', {}).get('status')
            current_text = ""
            for ws_item in result.get('ws', []):
                for cw in ws_item.get('cw', []):
                    current_text += cw.get('w', '')
            # iFlytek iat round messages are usually full-sentence snapshots, not deltas.
            # Use overwrite mode to avoid repeated concatenation.
            if current_text:
                if status == 2:
                    if current_text.strip() and len(current_text.strip()) > 1:
                        result_text = current_text
                else:
                    result_text = current_text
            if status == 2:
                break
        return result_text.strip()

    async def _send_audio_to_asr(self, ws, first_chunk: bytes, vad_eos: int) -> dict:
        """Send ASR audio stream with first frame carrying first audio chunk."""
        import base64
        from app.config import ASR_APP_ID

        # First frame: status=0 with first chunk audio (align with working demo/common iat usage)
        first_audio_b64 = base64.b64encode(first_chunk).decode()
        start_params = {
            "common": {"app_id": ASR_APP_ID},
            "business": {
                "language": "zh_cn",
                "domain": "iat",
                "accent": "mandarin",
                "vad_eos": vad_eos,
                "ptt": 1,
                "pd": "0",
                "nunum": 0,
                "dwa": "wpgs",
            },
            "data": {
                "status": 0,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": first_audio_b64,
            },
        }
        await ws.send(json.dumps(start_params))
        chunk_count = 1
        timeout_hit = False
        await asyncio.sleep(0.04)

        while True:
            try:
                item = await asyncio.wait_for(self.current_audio_queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                timeout_hit = True
                break

            if item is None:
                break

            _, chunk = item
            audio_b64 = base64.b64encode(chunk).decode()
            frame = {
                "data": {
                    "status": 1,
                    "format": "audio/L16;rate=16000",
                    "encoding": "raw",
                    "audio": audio_b64,
                }
            }
            await ws.send(json.dumps(frame))
            chunk_count += 1
            await asyncio.sleep(0.04)

        end_frame = {"data": {"status": 2, "format": "audio/L16;rate=16000", "encoding": "raw", "audio": ""}}
        await ws.send(json.dumps(end_frame))
        return {"chunk_count": chunk_count, "timeout_hit": timeout_hit}

    def _compute_adaptive_vad_eos(self) -> int:
        """Compute adaptive VAD timeout."""
        vad = self._vad_eos
        if self._consecutive_empty >= 3:
            vad += 180
        if self._empty_rate >= 0.6:
            vad += 120
        if len(self._round_metrics) >= 3:
            avg_chunks = sum(m.get("chunk_count", 0) for m in self._round_metrics[-5:]) / min(5, len(self._round_metrics))
            if avg_chunks >= 26 and self._empty_rate <= 0.35:
                vad -= 120
            elif avg_chunks >= 18 and self._empty_rate <= 0.45:
                vad -= 60
        return max(800, min(1800, vad))

    def _record_asr_round_metrics(self, chunk_count: int, timeout_hit: bool, has_result: bool):
        """Record ASR round metrics."""
        if has_result:
            self._consecutive_empty = 0
        total = len(self._round_metrics) + 1
        empty_count = sum(1 for m in self._round_metrics if not m.get("has_result"))
        if not has_result:
            empty_count += 1
        self._empty_rate = empty_count / total
        self._round_metrics.append({"chunk_count": chunk_count, "timeout_hit": timeout_hit, "has_result": has_result})
        if len(self._round_metrics) > 20:
            self._round_metrics = self._round_metrics[-20:]

    async def _handle_user_text(
        self,
        user_text: str,
        image_urls: Optional[list[str]] = None,
        file_urls: Optional[list[str]] = None,
        need_diagram: bool = False,
        enable_search: bool = False,
        generate_video: bool = False,
        enable_long_term_memory: bool = False,
        history: Optional[list[dict]] = None,
    ):
        """Serialize turns so one frontend response stream maps to one answer."""
        async with self._turn_lock:
            await self._run_user_text_turn(
                user_text=user_text,
                image_urls=image_urls,
                file_urls=file_urls,
                need_diagram=need_diagram,
                enable_search=enable_search,
                generate_video=generate_video,
                enable_long_term_memory=enable_long_term_memory,
                history=history,
            )

    async def _run_user_text_turn(
        self,
        user_text: str,
        image_urls: Optional[list[str]] = None,
        file_urls: Optional[list[str]] = None,
        need_diagram: bool = False,
        enable_search: bool = False,
        generate_video: bool = False,
        enable_long_term_memory: bool = False,
        history: Optional[list[dict]] = None,
    ):
        """Run one completed turn through chat service and avatar playback."""
        from app.chat.service import get_chat_usecases
        from app.chat import CHAT_MODULE_NAME
        from app.chat.request import ChatHistoryMessage
        from app.memory import MemoryService

        image_urls = list(dict.fromkeys(image_urls or []))
        file_urls = list(dict.fromkeys(file_urls or []))
        # Keep memory module aligned with text AI pipeline to avoid
        # cross-module session permission errors.
        memory_layer = MemoryService(module=CHAT_MODULE_NAME)
        if not self.session_id:
            # 创建新会话
            session = await memory_layer.create_session(user_id=self.user_id)
            self.session_id = session.id

        # Use the same service-owned persistence and TutorAgent path as text chat.
        chat_uc = get_chat_usecases()
        normalized_history: list[ChatHistoryMessage] = []
        for item in history or []:
            try:
                normalized_history.append(ChatHistoryMessage(**item))
            except Exception:
                logger.debug("[Bridge] ignored malformed history item=%s", item)
        if not normalized_history:
            stored_messages = await memory_layer.list_messages(
                user_id=self.user_id,
                session_id=self.session_id,
                only_unexpired=False,
            )
            normalized_history = [
                ChatHistoryMessage(role=message.role, content=message.content)
                for message in stored_messages
                if message.role in {"user", "assistant"} and str(message.content).strip()
            ]
        if not normalized_history or normalized_history[-1].role != "user":
            normalized_history.append(ChatHistoryMessage(role="user", content=user_text))
        full_response = ""
        event_count = 0
        stream_failed = False
        fail_reason = ""
        last_diagram_payload = None
        diagram_forwarded = False
        try:
            async def _consume_stream_events():
                nonlocal event_count, full_response, last_diagram_payload, diagram_forwarded
                async for event in chat_uc.stream_chat_events(
                    user_id=self.user_id,
                    user_message=user_text,
                    history=normalized_history,
                    session_id=self.session_id,
                    image_urls=image_urls,
                    file_urls=file_urls,
                    need_teaching_diagram=need_diagram,
                    enable_search=enable_search,
                    generate_video=generate_video,
                    enable_long_term_memory=enable_long_term_memory,
                    persist=True,
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

                    if event_type == "text_chunk":
                        content = self._repair_text_encoding(str(payload or ""))
                        full_response += content
                        if self.frontend_ws:
                            await self._send_to_frontend({"type": "assistant_chunk", "content": content})
                    elif event_type == "token":
                        content = self._repair_text_encoding(str(payload or ""))
                        if content:
                            full_response += content
                            if self.frontend_ws:
                                await self._send_to_frontend({"type": "assistant_chunk", "content": content})

                    elif event_type == "tool_result":
                        if self.frontend_ws:
                            await self._send_to_frontend({"type": "tool_result", "data": payload})

                    elif event_type == "tool_error":
                        if self.frontend_ws:
                            await self._send_to_frontend({"type": "tool_error", "data": payload})

                    elif event_type == "diagram":
                        last_diagram_payload = payload
                        if self.frontend_ws and not diagram_forwarded:
                            await self._send_to_frontend({"type": "diagram", "data": payload})
                            diagram_forwarded = True

                    elif event_type == "complete":
                        if not full_response and isinstance(payload, dict):
                            full_response = self._repair_text_encoding(
                                str(payload.get("full_response", "") or "")
                            )
                            if full_response and self.frontend_ws:
                                await self._send_to_frontend({"type": "assistant_chunk", "content": full_response})
                        if isinstance(payload, dict):
                            diagram_payload = payload.get("teaching_diagram") or payload.get("diagram")
                            if diagram_payload:
                                last_diagram_payload = diagram_payload
                            if diagram_payload and self.frontend_ws and not diagram_forwarded:
                                await self._send_to_frontend({"type": "diagram", "data": diagram_payload})
                                diagram_forwarded = True
                    elif event_type == "done":
                        if isinstance(payload, dict):
                            maybe_text = self._repair_text_encoding(
                                str(payload.get("full_response", "") or payload.get("response", "") or "")
                            )
                            if maybe_text and not full_response:
                                full_response = maybe_text
                                if self.frontend_ws:
                                    await self._send_to_frontend({"type": "assistant_chunk", "content": full_response})
                            resources = payload.get("resources")
                            diagram_payload = None
                            if isinstance(resources, dict):
                                diagram_payload = resources.get("teaching_diagram") or resources.get("diagram")
                            if not diagram_payload:
                                diagram_payload = payload.get("teaching_diagram") or payload.get("diagram")
                            if diagram_payload:
                                last_diagram_payload = diagram_payload
                            if diagram_payload and self.frontend_ws and not diagram_forwarded:
                                await self._send_to_frontend({"type": "diagram", "data": diagram_payload})
                                diagram_forwarded = True

            # Do not enforce a fixed timeout here.
            # Long answers + diagram generation can legitimately exceed 60~120s.
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
                await self._send_to_frontend({"type": "error", "content": f"数字人回答失败: {fail_reason}"})
        finally:
            logger.info(
                "[Bridge] stream ended events=%d full_response_len=%d failed=%s",
                event_count,
                len(full_response),
                stream_failed,
            )

            # Always send completion marker when frontend socket is still alive.
            if self.frontend_ws:
                if last_diagram_payload is not None and not diagram_forwarded:
                    await self._send_to_frontend({"type": "diagram", "data": last_diagram_payload})
                await self._send_to_frontend({"type": "assistant_complete"})

            # 4. 触发数字人播报
            if full_response.strip() and self._avatar_controller:
                logger.info(
                    "[Bridge] trigger avatar speak len=%s ws_alive=%s",
                    len(full_response.strip()),
                    bool(self.frontend_ws),
                )
                asyncio.create_task(
                    self._avatar_controller.speak(
                        full_response.strip(),
                        speech_rate=self._speech_rate,
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
    """管理所有用户的 RealtimeBridge 实例。"""

    def __init__(self):
        self._bridges: dict[int, RealtimeBridge] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def _get_lock(self, user_id: int) -> asyncio.Lock:
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    async def get_or_create_bridge(self, user_id: int) -> RealtimeBridge:
        lock = self._get_lock(user_id)
        async with lock:
            if user_id not in self._bridges:
                bridge = RealtimeBridge(user_id=user_id)
                self._bridges[user_id] = bridge
            return self._bridges[user_id]

    async def get_status(self, user_id: int) -> dict:
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
        bridge = self._bridges.get(user_id)
        if not bridge or not bridge._avatar_controller:
            return None
        return bridge._avatar_controller._last_stream_info

    async def stop(self, user_id: int):
        bridge = self._bridges.get(user_id)
        if bridge and bridge._avatar_controller:
            await bridge._avatar_controller.stop()

    async def cleanup(self, user_id: int):
        bridge = self._bridges.pop(user_id, None)
        self._locks.pop(user_id, None)
        if bridge:
            await bridge.close()

    async def cleanup_all(self) -> int:
        """Cleanup all user bridges and return cleaned count."""
        bridges = list(self._bridges.values())
        self._bridges.clear()
        self._locks.clear()

        if not bridges:
            return 0

        results = await asyncio.gather(
            *(bridge.close() for bridge in bridges),
            return_exceptions=True,
        )
        failed = 0
        for err in results:
            if isinstance(err, Exception):
                failed += 1
                logger.error("[Bridge] cleanup_all 失败: %s", err)
        cleaned = len(bridges) - failed
        logger.info("[Bridge] cleanup_all : total=%s cleaned=%s failed=%s", len(bridges), cleaned, failed)
        return cleaned


# 全局单例
avatar_bridge_manager = AvatarBridgeManager()
