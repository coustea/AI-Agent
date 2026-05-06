# -*- coding: utf-8 -*-
"""
AvatarBridgeManager ??RealtimeBridge 

?Avatar Bridge  (:8765) 
 per-user ?WebSocket SRvatarController ?
"""

import asyncio
import json
from typing import Optional

from fastapi import WebSocketDisconnect
from app.infra.logging import get_logger

logger = get_logger(__name__)


class RealtimeBridge:
    """per-user  WS SRvatarAgent"""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.session_id: str = ""
        self.frontend_ws = None  # WebSocket 
        self.is_listening = False
        self.current_audio_queue: Optional[asyncio.Queue] = None

        # 
        self._avatar_controller = None
        self._asr_loop_task = None

        # VAD ?
        self._vad_eos = 1000
        self._consecutive_empty = 0
        self._empty_rate = 0.0
        self._round_metrics: list[dict] = []
        self._audio_chunk_counter = 0

    async def _ensure_avatar_controller(self):
        if self._avatar_controller is None:
            from app.avatar.services.avatar_ctrl import AvatarController
            self._avatar_controller = AvatarController()
            await self._avatar_controller.connect(
                on_reconnect_callback=self._on_avatar_reconnect
            )
            # 
            asyncio.create_task(
                self._avatar_controller.receive_messages(self._on_avatar_event)
            )
            # 
            for _ in range(40):  #  20 ?
                if self._avatar_controller.is_ready:
                    break
                await asyncio.sleep(0.5)

    async def _on_avatar_reconnect(self, stream_info: dict):
        """Avatar reconnect callback."""
        await self._send_to_frontend({
            "type": "stream_info",
            "data": stream_info,
        })

    async def _on_avatar_event(self, event_type: str, data: dict):
        """Avatar """
        if event_type == "stream_info":
            await self._send_to_frontend({
                "type": "stream_info",
                "data": data,
            })

    async def handle_frontend(self, ws):
        """ WebSocket """
        self.frontend_ws = ws

        #  AvatarController 
        try:
            await self._ensure_avatar_controller()
        except Exception as e:
            logger.warning("[Bridge] AvatarController ? %s", e)

        # 
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
                except WebSocketDisconnect:
                    logger.info("[Bridge] ")
                    break
                except Exception as e:
                    logger.error("[Bridge] : %s", e)
                    if self.frontend_ws is not None:
                        try:
                            await self._send_to_frontend({"type": "error", "content": str(e)})
                        except Exception:
                            break
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error("[Bridge] handle_frontend : %s", e, exc_info=True)
        finally:
            if self._avatar_controller:
                try:
                    await self._avatar_controller.stop()
                except Exception:
                    logger.debug("[Bridge] avatar stop on disconnect failed", exc_info=True)
            self.frontend_ws = None

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
            await self._handle_start_vad()
        elif msg_type == "stop_vad":
            await self._handle_stop_vad()
        elif msg_type == "switch_session":
            self.session_id = data.get("session_id", "")

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
        # ?1280 40ms @ 16kHz?
        import time
        for i in range(0, len(pcm_bytes), 1280):
            chunk = pcm_bytes[i:i + 1280]
            await self.current_audio_queue.put((time.monotonic(), chunk))

    async def _handle_audio_end(self):
        """Handle end of audio input."""
        if self.current_audio_queue:
            await self.current_audio_queue.put(None)

    async def _handle_text_input(self, data: dict):
        """Handle text input and run avatar agent."""
        text = data.get("text", "")
        if not text:
            return
        image_urls, file_urls = self._extract_attachment_urls(data)
        need_diagram = bool(data.get("need_diagram", False))
        await self._handle_user_text(
            text,
            source="text",
            image_urls=image_urls,
            file_urls=file_urls,
            need_diagram=need_diagram,
        )

    async def _handle_stop_speaking(self):
        """Stop avatar speaking."""
        if self._avatar_controller:
            await self._avatar_controller.stop()

    async def _handle_clear_history(self):
        """Clear current session chat history."""
        from app.avatar.bridge.state import MessageType
        from app.memory import MemoryLayer

        memory_layer = MemoryLayer(module_name="avatar")

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
        from app.config import ASR_SPARK_APP_ID, ASR_SPARK_API_KEY, ASR_SPARK_API_SECRET, IAT_URL
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
        from app.config import ASR_SPARK_APP_ID, ASR_SPARK_API_KEY, ASR_SPARK_API_SECRET, IAT_URL

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

        #  VAD
        vad_eos = self._compute_adaptive_vad_eos()

        auth_url = assemble_auth_url(IAT_URL, 'GET', ASR_SPARK_API_KEY, ASR_SPARK_API_SECRET)
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
                await self._send_to_frontend({"type": "asr_result", "content": result_text})
                await self._handle_user_text(result_text, source="asr")
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
            for ws_item in result.get('ws', []):
                for cw in ws_item.get('cw', []):
                    result_text += cw.get('w', '')
            if data.get('data', {}).get('status') == 2:
                break
        return result_text

    async def _send_audio_to_asr(self, ws, first_chunk: bytes, vad_eos: int) -> dict:
        """Send ASR audio stream with first frame carrying first audio chunk."""
        import base64
        from app.config import ASR_SPARK_APP_ID

        # First frame: status=0 with first chunk audio (align with working demo/common iat usage)
        first_audio_b64 = base64.b64encode(first_chunk).decode()
        start_params = {
            "common": {"app_id": ASR_SPARK_APP_ID},
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
        source: str = "text",
        image_urls: Optional[list[str]] = None,
        file_urls: Optional[list[str]] = None,
        need_diagram: bool = False,
    ):
        """Core pipeline: user text -> agent -> frontend + avatar."""
        from app.avatar.agent import AvatarAgent
        from app.chat.service import get_avatar_chat_usecases
        from app.memory import MemoryLayer

        image_urls = list(dict.fromkeys(image_urls or []))
        file_urls = list(dict.fromkeys(file_urls or []))
        memory_layer = MemoryLayer(module_name="avatar")
        attachments_payload = None
        if image_urls or file_urls:
            attachments_payload = json.dumps(
                {"image_urls": image_urls, "file_urls": file_urls},
                ensure_ascii=False,
            )

        if not self.session_id:
            # 
            session = await memory_layer.create_session(user_id=self.user_id)
            self.session_id = session.id

        # 1. 
        await memory_layer.save_message(
            user_id=self.user_id,
            session_id=self.session_id,
            role="user",
            content=user_text,
            attachments=attachments_payload,
        )

        # 2.  ChatUseCases ?
        chat_uc = get_avatar_chat_usecases()
        agent = AvatarAgent()
        full_response = ""
        event_count = 0
        async for event in chat_uc.stream_chat_events(
            user_id=self.user_id,
            user_message=user_text,
            session_id=self.session_id,
            image_urls=image_urls,
            file_urls=file_urls,
            need_diagram=need_diagram,
            stream_runner=agent.chat_stream,
            input_source=source,
        ):
            event_count += 1
            # ?WebSocket 
            if not self.frontend_ws:
                logger.warning("[Bridge] WebSocket disconnected, stop processing events")
                break

            event_type = str(event.get("event", ""))
            payload = event.get("data")
            logger.info("[Bridge] event#%d type=%s payload_type=%s preview=%s",
                        event_count, event_type, type(payload).__name__,
                        str(payload)[:120] if payload else "None")

            if event_type == "text_chunk":
                content = str(payload or "")
                full_response += content
                # ?
                if self.frontend_ws:
                    await self._send_to_frontend({"type": "assistant_chunk", "content": content})

            elif event_type == "tool_result":
                if self.frontend_ws:
                    await self._send_to_frontend({"type": "tool_result", "data": payload})

            elif event_type == "tool_error":
                if self.frontend_ws:
                    await self._send_to_frontend({"type": "tool_error", "data": payload})

            elif event_type == "diagram":
                if self.frontend_ws:
                    await self._send_to_frontend({"type": "diagram", "data": payload})

            elif event_type == "complete":
                if not full_response and isinstance(payload, dict):
                    full_response = str(payload.get("full_response", "") or "")

        logger.info("[Bridge] stream ended events=%d full_response_len=%d", event_count, len(full_response))

        # 
        if self.frontend_ws:
            await self._send_to_frontend({"type": "assistant_complete"})

        # ?
        if full_response.strip() and self._avatar_controller and self.frontend_ws:
            asyncio.create_task(self._avatar_controller.speak(full_response.strip()))

        # 4. 
        if full_response and self.frontend_ws:
            await memory_layer.save_message(
                user_id=self.user_id,
                session_id=self.session_id,
                role="assistant",
                content=full_response,
            )

        # 5. ?+ ?
        if self.frontend_ws:
            asyncio.create_task(self._post_avatar_pipeline(user_text, full_response))

    async def _post_avatar_pipeline(self, user_msg: str, assistant_msg: str):
        """Run async memory/profile post-processing."""
        from app.memory import MemoryLayer

        if not self.session_id:
            return

        try:
            await MemoryLayer(module_name="avatar").post_turn_pipeline(
                user_id=self.user_id,
                session_id=self.session_id,
                user_message=user_msg,
                assistant_reply=assistant_msg,
            )
        except Exception as e:
            logger.error("[Bridge] : %s", e)

    async def _send_to_frontend(self, data: dict):
        """Send message to frontend websocket."""
        if self.frontend_ws:
            try:
                await self.frontend_ws.send_json(data)
            except Exception as e:
                logger.error("[Bridge] ? %s", e)
                # WebSocket ?
                self.frontend_ws = None

    async def close(self):
        """Close bridge resources."""
        self.is_listening = False
        if self._asr_loop_task and not self._asr_loop_task.done():
            self._asr_loop_task.cancel()
        if self._avatar_controller:
            await self._avatar_controller.close()


class AvatarBridgeManager:
    """ RealtimeBridge """

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
                logger.error("[Bridge] cleanup_all : %s", err)
        cleaned = len(bridges) - failed
        logger.info("[Bridge] cleanup_all : total=%s cleaned=%s failed=%s", len(bridges), cleaned, failed)
        return cleaned


# ?
avatar_bridge_manager = AvatarBridgeManager()






