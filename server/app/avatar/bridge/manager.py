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
from app.avatar.services.audio_ingress import AudioIngress
from app.avatar.services.streaming_asr import AdaptiveVADController, StreamingASRSession
from app.chat.memory.service import get_chat_memory_service
from app.chat.service import chat, get_chat_usecases
from app.config import ASR_VAD_EOS
from app.infra.logging import get_logger

logger = get_logger(__name__)

AUDIO_QUEUE_MAX_CHUNKS = 512
AUDIO_MESSAGE_MAX_BYTES = 64 * 1024
ASR_AUDIO_FRAME_BYTES = 1280
CHAT_STREAM_IDLE_TIMEOUT_SECONDS = 75.0
DIAGRAM_STREAM_IDLE_TIMEOUT_SECONDS = 30.0
DIAGRAM_STREAM_TOTAL_TIMEOUT_SECONDS = 30.0
ASR_READY_TIMEOUT_SECONDS = 15.0
# Give the browser one short render window after publishing the final
# transcript. This makes the visible order deterministic: transcript first,
# then turn_start/thinking, even when a quick reply finishes almost instantly.
ASR_TRANSCRIPT_RENDER_GRACE_SECONDS = 0.12

_TRANSIENT_ASR_ERROR_MARKERS = (
    "connectionreseterror",
    "connection reset",
    "connection closed",
    "disconnected",
    "unexpected eof",
    "upstream reset",
)

_PYTHON_ASR_HOMOPHONES = re.compile(r"(?:排分|派森|拍森|排森|拍分)", re.IGNORECASE)
_PROGRAMMING_CONTEXT = re.compile(
    r"(?:Python|Java|C\+\+|编程|程序|代码|开发|语法|算法|数据结构)",
    re.IGNORECASE,
)
_ENGLISH_HOW_ONLY = re.compile(r"^\s*how[.!?。！？]?\s*$", re.IGNORECASE)
_CHINESE_TEXT = re.compile(r"[\u3400-\u9fff]")


def normalize_asr_technical_terms(text: str, previous_text: str = "") -> str:
    """Correct a small set of high-confidence CS term homophones."""
    normalized = _PYTHON_ASR_HOMOPHONES.sub("Python", str(text or ""))
    context = f"{previous_text} {normalized}"
    if _PROGRAMMING_CONTEXT.search(context):
        normalized = normalized.replace("阵法", "语法")
    if _ENGLISH_HOW_ONLY.fullmatch(normalized) and _CHINESE_TEXT.search(previous_text):
        normalized = "好"
    return normalized


def _is_transient_asr_error(error: Exception) -> bool:
    message = f"{type(error).__name__}: {error}".lower()
    return any(marker in message for marker in _TRANSIENT_ASR_ERROR_MARKERS)


# 清理 LLM 输出文本中的 Markdown 标记，使文本适合 TTS 朗读
def _clean_text_for_tts(text: str) -> str:
    """清理 LLM 输出文本，去除 Markdown 格式标记，使其适合 TTS 朗读。

    讯飞 TTS 引擎不理解 Markdown，如果直接发送：
    - **加粗** → 朗读"星号星号加粗星号星号"
    - ### 标题 → 朗读"井号井号井号标题"
    - `代码` → 朗读"反引号代码反引号"
    - [链接](url) → 朗读"左方括号链接右方括号左圆括号url右圆括号"
    - 多个换行 → 可能导致播报断裂（"跳段说"）

    同时去除可能导致"重音"（重复朗读）的字符：
    - 重复标点（！！！→ ！）
    - 省略号（……→ 。）
    - 波浪号、星号等特殊符号
    """
    if not text:
        return ""

    # 1. 去除图片语法 ![alt](url)
    text = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'\1', text)

    # 2. 去除链接语法 [text](url)，保留文本
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # 3. 去除加粗/斜体标记 **text** / __text__ / *text* / _text_
    # 先处理 ** 和 __（加粗）
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # 再处理 * 和 _（斜体）
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'(?<![\\])_(.+?)_(?![\w])', r'\1', text)

    # 4. 去除标题标记 # ## ### 等
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # 5. 去除行内代码 `code`
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # 6. 去除代码块 ```...```
    text = re.sub(r'```[\s\S]*?```', '', text)

    # 7. 去除列表标记（- / * / 1. 等），保留文本
    text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)

    # 8. 去除引用标记 >
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)

    # 9. 去除水平分割线 --- / *** / ___
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    # 10. 去除 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)

    # 11. 去除残留的 Markdown 特殊符号（可能导致 TTS 朗读特殊字符）
    # 去除独立的星号（不是乘号语境）
    text = re.sub(r'(?<!\w)\*+(?!\w)', '', text)
    # 去除波浪号
    text = re.sub(r'~+', '', text)
    # 去除反引号残留
    text = re.sub(r'`+', '', text)

    # 12. 去除可能导致重音的重复标点
    # 重复的感叹号/问号 → 只保留一个（中英文都处理）
    text = re.sub(r'([!！?？])\1+', r'\1', text)
    # 中文省略号 → 句号
    text = re.sub(r'……+', '。', text)
    # 英文省略号 → 句号
    text = re.sub(r'\.{3,}', '。', text)
    # 重复的句号 → 单个
    text = re.sub(r'。+', '。', text)

    # 13. 多个换行合并为一个，单个换行替换为逗号
    # 讯飞 TTS 对换行符处理不稳定，可能导致重音或跳段
    # 用逗号替代换行，让 TTS 在段落间自然停顿
    text = re.sub(r'\n{2,}', '，', text)
    text = re.sub(r'\n', '，', text)

    # 14. 去除首尾空白
    text = text.strip()

    # 15. 合并多余空格（连续空格可能导致 TTS 异常停顿或重音）
    text = re.sub(r' {2,}', ' ', text)

    return text


# 单用户数字人桥接实例 — 持有 WebSocket、ASR 队列和 Avatar 控制器
class RealtimeBridge:
    """单用户数字人桥接 — 将前端 I/O 连接到共享的无状态辅导服务。"""

    # 初始化桥接实例：用户身份、会话管理、音频队列、VAD、Avatar 控制器
    def __init__(self, user_id: int, username: str = ""):
        self.user_id = user_id
        self.username = username
        # 当前会话 ID — 由首次对话时自动创建
        self.session_id: str = ""
        # 前端 WebSocket 连接引用
        self.frontend_ws = None
        self._frontend_owner: object | None = None
        # VAD 监听模式标志
        self.is_listening = False
        # 音频输入队列（VAD 模式下持续接收 PCM 音频块）
        self.current_audio_queue: Optional[asyncio.Queue] = None
        self._audio_ingress = AudioIngress(
            frame_bytes=ASR_AUDIO_FRAME_BYTES,
            queue_size=AUDIO_QUEUE_MAX_CHUNKS,
        )

        # 数字人控制器实例
        self._avatar_controller = None
        self._avatar_init_lock = asyncio.Lock()
        self._avatar_receive_task: asyncio.Task | None = None
        self._background_tasks: set[asyncio.Task] = set()
        # ASR 持续监听的后台任务
        self._asr_loop_task = None
        self._asr_ready_ack_task: asyncio.Task | None = None
        self._vad_generation = 0
        self._vad_ack_generation: int | None = None
        self._active_vad_session_id: str | None = None

        # Turn tracking - 用于串线保护
        self._current_turn_id: Optional[str] = None
        # Adaptive VAD controller
        self._vad_controller = AdaptiveVADController(base_vad_eos=ASR_VAD_EOS)

        # Audio chunk tracking
        self._last_asr_text: str = ""   # 上一次 ASR 识别结果（用于去重）
        self._last_asr_at: float = 0.0  # 上一次 ASR 结果的时间戳
        self._asr_connection_retry_count = 0

        # Turn defaults
        self._speech_rate: float = 1.0  # TTS 语速（0.8~1.5）
        self._need_diagram_default: bool = False  # 默认是否生成教学图
        self._need_video_default: bool = False  # 默认是否仅生成视频
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

    @property
    def _audio_frame_buffer(self) -> bytearray:
        return self._audio_ingress.remainder

    @property
    def _audio_chunk_counter(self) -> int:
        return self._audio_ingress.callbacks

    @property
    def _audio_dropped_chunks(self) -> int:
        return self._audio_ingress.dropped

    def _bind_audio_ingress_queue(self) -> None:
        if self._audio_ingress.queue is not self.current_audio_queue:
            self._audio_ingress.queue = self.current_audio_queue

    # 修复文本乱码：当 UTF-8 文本被误编码为 GBK 时尝试恢复
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

    def bind_frontend(self, ws) -> object:
        """Bind a frontend socket and return an ownership token for cleanup."""
        owner = object()
        self.frontend_ws = ws
        self._frontend_owner = owner
        self.session_id = ""
        return owner

    def owns_frontend(self, owner: object) -> bool:
        return self._frontend_owner is owner

    def _spawn_background(self, coroutine, *, label: str) -> asyncio.Task:
        task = asyncio.create_task(coroutine)
        self._background_tasks.add(task)

        def _done(completed: asyncio.Task) -> None:
            self._background_tasks.discard(completed)
            if completed.cancelled():
                return
            try:
                exc = completed.exception()
            except asyncio.CancelledError:
                return
            if exc is not None:
                logger.error("[Bridge] background task failed label=%s: %s", label, exc)

        task.add_done_callback(_done)
        return task

    async def _stop_avatar_receiver(self) -> None:
        task = self._avatar_receive_task
        self._avatar_receive_task = None
        if task is None or task.done() or task is asyncio.current_task():
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    def _start_avatar_receiver(self, controller) -> None:
        if self._avatar_receive_task is not None and not self._avatar_receive_task.done():
            return
        self._avatar_receive_task = asyncio.create_task(
            controller.receive_messages(self._on_avatar_event)
        )

    # 确保 Avatar 控制器已初始化并连接就绪，必要时重建
    async def _ensure_avatar_controller(self):
        async with self._avatar_init_lock:
            need_recreate = False
            if self._avatar_controller is None:
                need_recreate = True
            else:
                try:
                    if self._avatar_controller._ws_closed:
                        need_recreate = True
                except Exception:
                    need_recreate = True

            if not need_recreate:
                self._start_avatar_receiver(self._avatar_controller)
                last_stream_info = getattr(self._avatar_controller, "_last_stream_info", None)
                if self._avatar_controller.is_ready and last_stream_info:
                    # The controller outlives individual frontend WebSockets. A
                    # newly attached page won't receive another provider-side
                    # stream_info event, so replay the cached stream metadata.
                    await self._send_to_frontend({
                        "type": "stream_info",
                        "data": last_stream_info,
                        "reused": True,
                    })
                    await self._send_digital_human_state(
                        "avatar_ready",
                        "Avatar service ready",
                    )
                return

            await self._send_digital_human_state("avatar_connecting", "Connecting to Avatar service")
            await self._stop_avatar_receiver()
            if self._avatar_controller is not None:
                try:
                    await self._avatar_controller.close()
                except Exception:
                    logger.debug("[Bridge] close stale avatar controller failed", exc_info=True)

            controller = AvatarController()
            self._avatar_controller = controller
            await controller.connect(on_reconnect_callback=self._on_avatar_reconnect)
            self._start_avatar_receiver(controller)

            # 等待最多 20 秒
            for _ in range(40):
                if controller.is_ready:
                    break
                await asyncio.sleep(0.5)

            if controller.is_ready:
                await self._send_digital_human_state("avatar_ready", "Avatar service ready")
            else:
                await self._send_digital_human_state("error", "Avatar connection timeout")

    # Avatar 重连回调：重连成功后向前端发送新的流信息
    async def _on_avatar_reconnect(self, stream_info: dict):
        if not self._frontend_ws_ready():
            return
        await self._send_to_frontend({
            "type": "stream_info",
            "data": stream_info,
        })

    # Avatar 事件回调：处理 stream_info、tts_start/end、error、connection_lost
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
                "type": "digital_human_state",
                "state": "avatar_ready",
                "message": "Avatar service ready",
                "turn_id": turn_id,
            })
            await self._send_to_frontend({
                "type": "avatar_stopped",
                "data": data,
                "turn_id": turn_id,
            })
        elif event_type == "avatar_error":
            code = data.get("code", "unknown") if isinstance(data, dict) else "unknown"
            message = data.get("message", "Avatar service error") if isinstance(data, dict) else "Avatar service error"
            error_message = f"Avatar service error {code}: {message}"
            logger.error("[Bridge] Avatar service returned error: %s", error_message)
            await self._send_digital_human_state("error", error_message)
            await self._send_event_with_turn_id("error", content=error_message)
        elif event_type == "connection_lost":
            # Avatar WebSocket 连接断开 — 尝试自动重连
            reason = data.get("reason", "unknown") if isinstance(data, dict) else "unknown"
            logger.warning("[Bridge] Avatar connection lost (reason=%s), attempting auto-reconnect", reason)
            # Provider disconnects don't always carry tts_end. Close the active
            # playback lifecycle before entering reconnect so the frontend can
            # release its speaking state and resume continuous VAD after Ready.
            await self._send_to_frontend({
                "type": "avatar_stopped",
                "data": {
                    "fallback": True,
                    "connection_lost": True,
                    "reason": reason,
                },
                "turn_id": self._current_turn_id,
            })
            await self._send_digital_human_state("avatar_connecting", "数字人连接断开，正在重连...")
            # 异步重连，不阻塞当前事件处理
            # 使用锁防止多个 connection_lost 事件同时触发多个重连流程
            if not self._reconnect_lock.locked():
                asyncio.create_task(self._reconnect_avatar())
            else:
                logger.info("[Bridge] Reconnect already in progress, skipping duplicate trigger")

    # Avatar 自动重连：带指数退避重试，前端断开则放弃
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
                        async with self._avatar_init_lock:
                            await self._stop_avatar_receiver()
                            if self._avatar_controller is not None:
                                try:
                                    await self._avatar_controller.close()
                                except Exception:
                                    logger.debug("[Bridge] close stale avatar controller failed", exc_info=True)

                            controller = AvatarController()
                            self._avatar_controller = controller
                            await controller.connect(on_reconnect_callback=self._on_avatar_reconnect)
                            self._start_avatar_receiver(controller)

                            # 等待 Avatar 就绪（最多 20 秒）
                            for _ in range(40):
                                if controller.is_ready:
                                    break
                                await asyncio.sleep(0.5)

                        if controller.is_ready:
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

    # 处理前端 WebSocket 连接 — 主消息循环
    async def handle_frontend(self, ws, owner: object | None = None):
        if owner is None:
            owner = self.bind_frontend(ws)
        elif not self.owns_frontend(owner):
            return
        # 确保 AvatarController 已初始化
        try:
            await self._ensure_avatar_controller()
        except Exception as e:
            logger.warning("[Bridge] AvatarController 初始化失败: %s", e)
            # 通知前端 Avatar 服务不可用，避免黑屏
            await self._send_digital_human_state("error", "数字人服务暂时不可用，请稍后重试")
            await self._send_to_frontend({
                "type": "error",
                "content": "数字人服务连接失败，请检查网络后刷新页面重试",
            })

        # A newer frontend connection superseded this one while Avatar was connecting.
        if not self.owns_frontend(owner):
            return

        try:
            # 持续接收前端消息并路由处理
            while self.owns_frontend(owner):
                try:
                    message = await ws.receive()
                    if message.get("type") == "websocket.disconnect":
                        break
                    audio_bytes = message.get("bytes")
                    if audio_bytes is not None:
                        await self._handle_audio_bytes(audio_bytes)
                        continue
                    text_message = message.get("text")
                    if text_message is not None:
                        await self._route_message(json.loads(text_message))
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
            # Only the active frontend owner may stop shared Avatar resources.
            if self.owns_frontend(owner):
                if self._avatar_controller:
                    try:
                        await self._avatar_controller.stop()
                    except Exception:
                        logger.debug("[Bridge] avatar stop on disconnect failed", exc_info=True)
                self.frontend_ws = None

    # 检查前端 WebSocket 连接状态是否仍有效
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

    # 向前端发送数字人状态事件（idle/connecting/ready/listening/recognizing/thinking/speaking/error）
    async def _send_digital_human_state(self, state: str, message: str = ""):
        await self._send_to_frontend({
            "type": "digital_human_state",
            "state": state,
            "message": message,
            "turn_id": self._current_turn_id,
        })


    # 发送带当前 turn_id 的事件到前端（若无则跳过）
    async def _send_event_with_turn_id(self, event_type: str, **kwargs):
        data = {"type": event_type, **kwargs}
        if self._current_turn_id:
            data["turn_id"] = self._current_turn_id
        await self._send_to_frontend(data)

    # 前端消息路由：根据消息类型分发到对应的处理方法
    async def _route_message(self, data: dict):
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
            await self._handle_start_vad(data.get("vad_session_id"))
        elif msg_type == "stop_vad":
            # 停止 VAD 监听模式
            await self._handle_stop_vad(data.get("vad_session_id"))
        elif msg_type == "switch_session":
            # 切换会话 ID
            self.session_id = data.get("session_id", "")
        elif msg_type == "set_speech_rate":
            # 设置 TTS 语速
            self._handle_set_speech_rate(data)
        elif msg_type == "set_need_diagram":
            # 设置是否生成教学图
            self._handle_set_need_diagram(data)

    # 处理前端传来的语速设置，限制在 0.8~1.5 范围
    def _handle_set_speech_rate(self, data: dict):
        raw = data.get("speech_rate", 1.0)
        try:
            rate = float(raw)
        except (TypeError, ValueError):
            rate = 1.0
        self._speech_rate = max(0.8, min(1.5, rate))

    # 处理前端传来的教学图生成标志
    def _handle_set_need_diagram(self, data: dict):
        self._need_diagram_default = bool(data.get("need_diagram", False))

    # 处理会话 ID 和能力标志（联网搜索等）保持 ASR 驱动的能力激活
    def _handle_capability_flags(self, data: dict):
        if isinstance(data.get("session_id"), str) and data["session_id"].strip():
            self.session_id = data["session_id"].strip()
        if "enable_search" in data:
            self._enable_search_default = bool(data.get("enable_search"))
        if "need_video" in data:
            self._need_video_default = bool(data.get("need_video"))

    # 统一化附件 URL 列表：支持字符串、列表、字典多种格式
    @staticmethod
    def _normalize_url_list(value) -> list[str]:
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

    # 从 WebSocket text_input 消息中提取所有附件 URL（兼容多字段格式）
    def _extract_attachments(self, data: dict) -> list[str]:
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

    # 处理前端传来的音频数据块：跨消息聚合为 40ms 的完整 PCM 帧
    async def _handle_audio_chunk(self, data: dict):
        audio_b64 = data.get("audio", "")
        if not self.is_listening or not audio_b64 or not self.current_audio_queue:
            return
        if self._avatar_controller and self._avatar_controller.is_speaking:
            return
        try:
            pcm_bytes = base64.b64decode(audio_b64, validate=True)
        except (ValueError, TypeError):
            logger.warning("[Bridge] ignored invalid base64 audio chunk")
            return
        await self._handle_audio_bytes(pcm_bytes)

    async def _handle_audio_bytes(self, pcm_bytes: bytes) -> None:
        """Accept one raw mono 16-bit PCM browser callback."""
        if not self.is_listening or not pcm_bytes or not self.current_audio_queue:
            return
        if self._avatar_controller and self._avatar_controller.is_speaking:
            return
        if len(pcm_bytes) > AUDIO_MESSAGE_MAX_BYTES:
            logger.warning("[Bridge] ignored oversized audio chunk bytes=%s", len(pcm_bytes))
            return
        self._bind_audio_ingress_queue()
        stats = self._audio_ingress.accept(pcm_bytes)
        if stats.callbacks == 1 or stats.callbacks % 25 == 0:
            logger.info(
                "[Bridge] audio frame recv callbacks=%s bytes=%s frames=%s queued=%s",
                stats.callbacks,
                len(pcm_bytes),
                stats.frames,
                stats.queued,
            )


    def _restore_asr_audio(self, items: list[tuple[float, bytes] | None]) -> None:
        """Put frames consumed by a failed ASR connection before newer audio."""
        self._bind_audio_ingress_queue()
        restored = self._audio_ingress.restore(items)
        if restored:
            logger.info("[Bridge] restored ASR audio items=%s", restored)

    # 处理音频输入结束信号：向队列发送 None 终止符
    async def _handle_audio_end(self):
        if self.current_audio_queue:
            self._bind_audio_ingress_queue()
            stats = self._audio_ingress.finish()
            if stats.callbacks:
                logger.info(
                    "[Bridge] audio end callbacks=%s frames=%s queued=%s dropped=%s",
                    stats.callbacks,
                    stats.frames,
                    stats.queued,
                    stats.dropped,
                )
                await self._send_digital_human_state("recognizing", "Processing speech")

    @staticmethod
    def _put_audio_end(queue: asyncio.Queue) -> None:
        AudioIngress.end_queue(queue)

    # 处理文本输入：提取文本、附件、语速等参数，分派到辅导管线
    async def _handle_text_input(self, data: dict):
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
        need_video = bool(data.get("need_video", False))
        self._need_video_default = need_video
        self._handle_capability_flags(data)
        await self._handle_user_text(
            text,
            attachments=attachments,
            need_diagram=need_diagram,
            need_video=need_video,
            enable_search=self._enable_search_default,
        )

    # 停止数字人播报：发送 stop 指令并通知前端
    async def _handle_stop_speaking(self):
        if self._avatar_controller:
            await self._avatar_controller.stop()
        await self._send_digital_human_state("avatar_ready", "Avatar service ready")
        await self._send_to_frontend({"type": "avatar_stopped"})

    # 清除当前会话的聊天历史记录
    async def _handle_clear_history(self):
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

    # 启动 VAD 语音活动检测监听模式
    async def _handle_start_vad(self, vad_session_id: str | None = None):
        await self._cancel_asr_ready_ack()
        previous_queue = self.current_audio_queue
        self._vad_generation += 1
        generation = self._vad_generation
        session_id = (
            vad_session_id.strip()
            if isinstance(vad_session_id, str) and vad_session_id.strip()
            else f"server-{generation}"
        )
        self._active_vad_session_id = session_id
        self._vad_ack_generation = None
        previous_task = self._asr_loop_task
        self._asr_loop_task = None
        if previous_queue is not None:
            self._put_audio_end(previous_queue)
        if previous_task is not None and not previous_task.done():
            previous_task.cancel()
            await asyncio.gather(previous_task, return_exceptions=True)

        self.is_listening = True
        self.current_audio_queue = self._audio_ingress.start()
        self._asr_connection_retry_count = 0
        asr_ready_event = asyncio.Event()
        asr_task = asyncio.create_task(
            self._continuous_listen_loop(generation, session_id, asr_ready_event)
        )
        self._asr_loop_task = asr_task
        owner = self._frontend_owner
        self._asr_ready_ack_task = asyncio.create_task(
            self._ack_vad_when_asr_ready(
                generation=generation,
                vad_session_id=session_id,
                asr_task=asr_task,
                ready_event=asr_ready_event,
                owner=owner,
            )
        )

    async def _ack_vad_when_asr_ready(
        self,
        *,
        generation: int,
        vad_session_id: str,
        asr_task: asyncio.Task,
        ready_event: asyncio.Event,
        owner: object | None,
    ) -> None:
        current_task = asyncio.current_task()
        try:
            try:
                await asyncio.wait_for(
                    ready_event.wait(),
                    timeout=ASR_READY_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                # Resolve a timeout/ready race in favor of a completed connection.
                if not ready_event.is_set():
                    is_current = (
                        generation == self._vad_generation
                        and vad_session_id == self._active_vad_session_id
                        and self._asr_loop_task is asr_task
                        and self.is_listening
                    )
                    if is_current:
                        owner_is_current = owner is None or self.owns_frontend(owner)
                        logger.error("[Bridge] ASR upstream connection timed out")
                        await self._stop_vad_input(
                            expected_generation=generation,
                            vad_session_id=vad_session_id,
                        )
                        if owner_is_current:
                            await self._send_event_with_turn_id(
                                "error",
                                content="语音识别服务连接超时，请重试。",
                                vad_session_id=vad_session_id,
                            )
                    return

            is_current = (
                generation == self._vad_generation
                and vad_session_id == self._active_vad_session_id
                and self._asr_loop_task is asr_task
                and self.is_listening
            )
            if not is_current:
                return
            if owner is not None and not self.owns_frontend(owner):
                await self._stop_vad_input(
                    expected_generation=generation,
                    vad_session_id=vad_session_id,
                )
                return

            await self._send_to_frontend(
                {
                    "type": "vad_state",
                    "vad_session_id": vad_session_id,
                    "data": {"listening": True},
                }
            )
            self._vad_ack_generation = generation
            await self._send_digital_human_state("listening", "Listening for speech")
        except asyncio.CancelledError:
            return
        finally:
            if self._asr_ready_ack_task is current_task:
                self._asr_ready_ack_task = None

    async def _cancel_asr_ready_ack(self) -> None:
        task = self._asr_ready_ack_task
        self._asr_ready_ack_task = None
        if task is None or task.done() or task is asyncio.current_task():
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    # 停止 VAD 监听模式
    async def _handle_stop_vad(self, vad_session_id: str | None = None):
        stopped = await self._stop_vad_input(vad_session_id=vad_session_id)
        if stopped:
            await self._send_digital_human_state("idle", "Stopped listening")

    # 停止接受麦克风音频输入并取消 ASR 循环任务
    async def _stop_vad_input(
        self,
        *,
        expected_generation: int | None = None,
        vad_session_id: str | None = None,
    ) -> bool:
        if expected_generation is not None and expected_generation != self._vad_generation:
            return False
        if (
            vad_session_id is not None
            and self._active_vad_session_id is not None
            and vad_session_id != self._active_vad_session_id
        ):
            return False

        stopped_session_id = self._active_vad_session_id or vad_session_id
        self.is_listening = False
        self._vad_generation += 1
        self._vad_ack_generation = None
        self._active_vad_session_id = None
        await self._cancel_asr_ready_ack()
        audio_queue = self.current_audio_queue
        self.current_audio_queue = None
        if audio_queue:
            self._put_audio_end(audio_queue)
        self._audio_ingress.close()
        if self._asr_loop_task and not self._asr_loop_task.done():
            current_task = asyncio.current_task()
            if self._asr_loop_task is not current_task:
                self._asr_loop_task.cancel()
                await asyncio.gather(self._asr_loop_task, return_exceptions=True)
        self._asr_loop_task = None
        event = {"type": "vad_state", "data": {"listening": False}}
        if stopped_session_id:
            event["vad_session_id"] = stopped_session_id
        await self._send_to_frontend(event)
        return True

    # 持续 ASR 监听循环：数字人说话时暂停以避免拾取 TTS 回声
    async def _continuous_listen_loop(
        self,
        generation: int,
        vad_session_id: str,
        ready_event: asyncio.Event | None = None,
    ):
        while self.is_listening and generation == self._vad_generation:
            try:
                # 如果数字人正在说话，暂停 ASR 识别
                # 避免麦克风拾取到 TTS 回声导致错误识别
                if self._avatar_controller and self._avatar_controller.is_speaking:
                    await asyncio.sleep(0.3)
                    continue

                await self._single_recognition_round(
                    ready_event,
                    expected_generation=generation,
                    vad_session_id=vad_session_id,
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("[Bridge] ASR continuous listen error: %s", e)
                # Initial connection failures are retried behind the readiness gate.
                # The frontend receives one timeout only if all retries fail.
                if (
                    self._vad_ack_generation == generation
                    and self._active_vad_session_id == vad_session_id
                ):
                    await self._send_event_with_turn_id(
                        "error",
                        content=f"语音识别异常: {e}",
                        vad_session_id=vad_session_id,
                    )
                await asyncio.sleep(0.5)

    # 单轮 ASR 识别：保留用户开口音频 → 创建 StreamingASRSession → 处理结果
    async def _single_recognition_round(
        self,
        ready_event: asyncio.Event | None = None,
        *,
        expected_generation: int | None = None,
        vad_session_id: str | None = None,
    ):
        """Run one ASR recognition round using StreamingASRSession.

        如果数字人正在说话，跳过本轮识别以避免拾取 TTS 回声。
        """
        if not self.current_audio_queue:
            return

        # 如果数字人正在说话，跳过本轮识别
        if self._avatar_controller and self._avatar_controller.is_speaking:
            logger.debug("[Bridge] Skipping ASR round: avatar is speaking")
            await asyncio.sleep(0.3)
            return

        # 发送 recognizing 状态
        # Compute adaptive VAD EOS
        vad_eos = self._vad_controller.compute_vad_eos()

        # Create ASR session
        async def publish_partial(text: str) -> None:
            if expected_generation is not None and (
                expected_generation != self._vad_generation
                or vad_session_id != self._active_vad_session_id
            ):
                return
            event = {"type": "asr_partial", "content": text}
            if vad_session_id:
                event["vad_session_id"] = vad_session_id
            await self._send_to_frontend(event)

        asr_session = StreamingASRSession(
            audio_queue=self.current_audio_queue,
            vad_eos=vad_eos,
            ready_event=ready_event,
            partial_callback=publish_partial,
        )

        try:
            # Run ASR recognition
            result_text = await asr_session.run()
            self._asr_connection_retry_count = 0

            if expected_generation is not None and (
                expected_generation != self._vad_generation
                or vad_session_id != self._active_vad_session_id
            ):
                return

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
                raw_asr_text = str(result_text).strip()
                normalized = normalize_asr_technical_terms(
                    raw_asr_text,
                    self._last_asr_text,
                ).strip()
                if normalized:
                    if normalized != raw_asr_text:
                        logger.info(
                            "[Bridge] ASR technical terms normalized input_len=%s output_len=%s",
                            len(raw_asr_text),
                            len(normalized),
                        )
                    now_ts = time.monotonic()
                    is_dup = normalized == self._last_asr_text
                    recent_dup = is_dup and (now_ts - self._last_asr_at < 1.6)
                    if not recent_dup:
                        # 单字“好/对/是/嗯”也是有效的连续对话输入，仅过滤纯标点或空白。
                        if not re.search(r"[\w\u3400-\u9fff]", normalized):
                            logger.debug("[Bridge] Ignoring non-verbal ASR result: '%s'", normalized)
                        else:
                            self._last_asr_text = normalized
                            self._last_asr_at = now_ts
                            stopped = await self._stop_vad_input(
                                expected_generation=expected_generation,
                                vad_session_id=vad_session_id,
                            )
                            if not stopped:
                                return
                            result_event = {"type": "asr_result", "content": normalized}
                            if vad_session_id:
                                result_event["vad_session_id"] = vad_session_id
                            await self._send_to_frontend(result_event)
                            await asyncio.sleep(ASR_TRANSCRIPT_RENDER_GRACE_SECONDS)
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
                                self._spawn_background(
                                    self._handle_user_text(
                                        normalized,
                                        need_diagram=self._need_diagram_default,
                                        need_video=self._need_video_default,
                                        enable_search=self._enable_search_default,
                                    ),
                                    label="voice-turn",
                                )
                return

            if asr_session.chunk_count == 0:
                # An idle preconnected ASR socket expired before the user spoke.
                # Reconnect behind the same VAD session; ending the frontend
                # session here creates a race that can discard the user's first
                # frames exactly when they start speaking.
                logger.debug("[Bridge] idle ASR connection expired; reconnecting transparently")
                return
            stopped = await self._stop_vad_input(
                expected_generation=expected_generation,
                vad_session_id=vad_session_id,
            )
            if not stopped:
                return
            empty_event = {"type": "asr_empty"}
            if vad_session_id:
                empty_event["vad_session_id"] = vad_session_id
            await self._send_to_frontend(empty_event)
        except Exception as e:
            take_replay_items = getattr(asr_session, "take_replay_items", None)
            replay_items = take_replay_items() if callable(take_replay_items) else []
            self._restore_asr_audio(replay_items)
            if (
                _is_transient_asr_error(e)
                and self.is_listening
                and self.current_audio_queue is not None
                and self._asr_connection_retry_count < 1
            ):
                self._asr_connection_retry_count += 1
                logger.warning(
                    "[Bridge] transient ASR connection failure; retrying once: %s",
                    e,
                )
                await asyncio.sleep(0.25)
                return

            self._asr_connection_retry_count = 0
            logger.error("[Bridge] ASR session failed: %s", e)
            stopped = await self._stop_vad_input(
                expected_generation=expected_generation,
                vad_session_id=vad_session_id,
            )
            if stopped:
                await self._send_event_with_turn_id(
                    "error",
                    content=f"语音识别异常: {e}",
                    vad_session_id=vad_session_id,
                )

    # 串行化 turn 处理：获取锁后合并 pending 文本、打断旧播报、执行新 turn
    async def _handle_user_text(
        self,
        user_text: str,
        attachments: Optional[list[str]] = None,
        need_diagram: bool = False,
        need_video: bool = False,
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
                need_video=need_video,
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

    # 执行一轮完整的对话 turn：调用 chat 服务 → 流式处理事件 → 触发 Avatar 播报
    async def _run_user_text_turn(
        self,
        user_text: str,
        attachments: Optional[list[str]] = None,
        need_diagram: bool = False,
        need_video: bool = False,
        enable_search: bool = False,
    ):
        """执行一轮完整的对话 turn：调用 chat 服务 → 流式处理事件 → 触发 Avatar 播报。"""
        turn_started_at = time.perf_counter()
        turn_id = self._current_turn_id
        diagram_requested = bool(need_diagram)
        # 合并附件 URL 并去重
        merged_attachments = list(dict.fromkeys(attachments or []))
        chat_uc = get_chat_usecases()
        # 自动创建会话（首次对话时）
        if not self.session_id:
            session = await get_chat_memory_service().create_session(user_id=self.user_id)
            self.session_id = str(session.id)

        attachment_records = [{"url": url} for url in merged_attachments]
        user_message = await chat_uc.create_user_message(
            user_id=self.user_id,
            username=self.username or f"user_{self.user_id}",
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
        tts_pending_text = ""
        tts_has_queued_content = False
        first_llm_text_at: float | None = None
        first_tts_queued_at: float | None = None
        event_count = 0
        stream_failed = False
        fail_reason = ""
        try:
            async def _queue_complete_tts_response() -> None:
                """Submit the complete answer to Avatar as one uninterrupted TTS request."""
                nonlocal tts_pending_text, tts_has_queued_content, first_tts_queued_at
                controller = self._avatar_controller
                if controller is None:
                    return
                speech_text = _clean_text_for_tts(tts_pending_text)
                tts_pending_text = ""
                if not speech_text:
                    return
                await controller.speak(
                    speech_text,
                    speech_rate=self._speech_rate,
                    turn_id=turn_id,
                )
                tts_has_queued_content = True
                first_tts_queued_at = time.perf_counter()
                logger.info(
                    "[BridgeLatency] complete Avatar response queued in %.3fs turn_id=%s chars=%d",
                    first_tts_queued_at - turn_started_at,
                    turn_id,
                    len(speech_text),
                )

            async def _forward_assistant_chunk(content: str, *, append_to_response: bool = True) -> None:
                """Forward text tokens while buffering one complete TTS utterance."""
                nonlocal full_response, tts_pending_text, first_llm_text_at
                if not content:
                    return
                if first_llm_text_at is None:
                    first_llm_text_at = time.perf_counter()
                    logger.info(
                        "[BridgeLatency] first LLM text in %.3fs turn_id=%s",
                        first_llm_text_at - turn_started_at,
                        turn_id,
                    )
                if append_to_response:
                    full_response += content
                if self.frontend_ws:
                    await self._send_event_with_turn_id("assistant_chunk", content=content)
                tts_pending_text += content

            async def _consume_stream_events():
                """消费 chat 服务的 SSE 事件流，转发 token/status/error/diagram 事件。"""
                nonlocal event_count, full_response
                nonlocal stream_failed, fail_reason
                event_stream = chat(
                    user_message_id=user_message_id,
                    user_id=self.user_id,
                    username=self.username or f"user_{self.user_id}",
                    session_id=self.session_id,
                    user_input=user_text,
                    attachments=merged_attachments,
                    diagram_mode="required" if diagram_requested else "auto",
                    voice_mode=True,
                )
                try:
                    while True:
                        try:
                            event = await asyncio.wait_for(
                                anext(event_stream),
                                timeout=(
                                    DIAGRAM_STREAM_IDLE_TIMEOUT_SECONDS
                                    if diagram_requested
                                    else CHAT_STREAM_IDLE_TIMEOUT_SECONDS
                                ),
                            )
                        except StopAsyncIteration:
                            break
                        except asyncio.TimeoutError as exc:
                            stream_failed = True
                            fail_reason = "回答生成长时间没有进展，请重试"
                            raise RuntimeError(fail_reason) from exc

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
                                await _forward_assistant_chunk(content)

                        elif event_type == "status":
                            # 状态事件 → 转发给前端
                            if self.frontend_ws and isinstance(payload, dict):
                                await self._send_event_with_turn_id("status", data=payload)

                        elif event_type == "agent_status":
                            # Agent 思考过程事件 → 转发给前端显示思考进度
                            if self.frontend_ws and isinstance(payload, dict):
                                await self._send_event_with_turn_id("status", data=payload)

                        elif event_type == "error":
                            # 对话执行失败不等于 Avatar 传输失败。仅结束当前
                            # turn，播放器与连续语音连接保持可用。
                            stream_failed = True
                            fail_reason = str(payload or "数字人回答失败，请重试")
                            if self.frontend_ws:
                                await self._send_event_with_turn_id("error", content=fail_reason)

                        elif event_type == "done":
                            # 完成事件 → 提取最终回复和教学图
                            if isinstance(payload, dict):
                                maybe_text = self._repair_text_encoding(
                                    str(payload.get("full_response", "") or payload.get("response", "") or "")
                                )
                                if maybe_text and not full_response:
                                    await _forward_assistant_chunk(maybe_text)
                finally:
                    aclose = getattr(event_stream, "aclose", None)
                    if callable(aclose):
                        await aclose()

            # Diagram turns have a total response budget as well as the per-event
            # idle timeout. Repeated format/diagram repairs must not keep a
            # digital-human turn in the thinking state indefinitely.
            try:
                if diagram_requested:
                    await asyncio.wait_for(
                        _consume_stream_events(),
                        timeout=DIAGRAM_STREAM_TOTAL_TIMEOUT_SECONDS,
                    )
                else:
                    await _consume_stream_events()
            except asyncio.TimeoutError as exc:
                stream_failed = True
                fail_reason = "回答生成长时间没有进展，请重试"
                raise RuntimeError(fail_reason) from exc
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
            diagram_timeout_fallback = diagram_requested and "长时间没有进展" in fail_reason
            if self.frontend_ws and not diagram_timeout_fallback:
                await self._send_event_with_turn_id("error", content=f"数字人回答失败: {fail_reason}")
        finally:
            generated_timeout_response = False

            if not full_response.strip():
                full_response = (
                    "抱歉，刚才的回答生成超时了，请再说一次。"
                    if "长时间没有进展" in fail_reason
                    else "抱歉，刚才没有生成有效回答，请再说一次。"
                )
                generated_timeout_response = True

            if generated_timeout_response:
                await _forward_assistant_chunk(full_response, append_to_response=False)

            logger.info(
                "[Bridge] stream ended events=%d full_response_len=%d failed=%s",
                event_count,
                len(full_response),
                stream_failed,
            )

            # The user requested one uninterrupted utterance: only now, after the
            # complete answer is available, submit a single TTS request.
            await _queue_complete_tts_response()

            # 流结束后始终发送完成标记
            if self.frontend_ws:
                await self._send_event_with_turn_id("assistant_complete")

            if tts_has_queued_content:
                logger.info(
                    "[Bridge] queued complete Avatar speech response_len=%s ws_alive=%s total_queue_time=%.3fs",
                    len(full_response.strip()),
                    bool(self.frontend_ws),
                    (first_tts_queued_at or time.perf_counter()) - turn_started_at,
                )

    # 向前端 WebSocket 发送 JSON 消息（如果连接已关闭则静默忽略）
    async def _send_to_frontend(self, data: dict):
        if not self._frontend_ws_ready():
            return
        try:
            await self.frontend_ws.send_json(data)
        except Exception as e:
            logger.error("[Bridge] send frontend failed: %s", e)
            # WebSocket may already be closed/invalid
            self.frontend_ws = None

    # 关闭桥接资源：停止 ASR 循环、关闭 Avatar 控制器
    async def close(self):
        self.is_listening = False
        self._vad_generation += 1
        self._vad_ack_generation = None
        self._active_vad_session_id = None
        self._audio_ingress.close()
        await self._cancel_asr_ready_ack()
        if self._asr_loop_task and not self._asr_loop_task.done():
            self._asr_loop_task.cancel()
            await asyncio.gather(self._asr_loop_task, return_exceptions=True)
        self._asr_loop_task = None
        background_tasks = [
            task for task in self._background_tasks
            if task is not asyncio.current_task() and not task.done()
        ]
        for task in background_tasks:
            task.cancel()
        if background_tasks:
            await asyncio.gather(*background_tasks, return_exceptions=True)
        self._background_tasks.clear()
        await self._stop_avatar_receiver()
        if self._avatar_controller:
            await self._avatar_controller.close()
        self._avatar_controller = None
        self.frontend_ws = None
        self._frontend_owner = None


# 全局 AvatarBridgeManager 单例 — 管理所有用户的 RealtimeBridge 实例
class AvatarBridgeManager:
    """管理所有用户的 RealtimeBridge 实例（全局单例）。

    每个用户对应一个 Bridge 实例，通过 user_id 索引。
    使用 per-user 锁确保并发安全。
    """

    # 初始化用户 Bridge 字典和 per-user 锁字典
    def __init__(self):
        self._bridges: dict[int, RealtimeBridge] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    # 获取或创建用户级别的异步锁（确保并发安全）
    def _get_lock(self, user_id: int) -> asyncio.Lock:
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]


    async def attach_frontend(self, user_id: int, ws, username: str = "") -> tuple[RealtimeBridge, object]:
        """Atomically bind the latest frontend connection for a user."""
        lock = self._get_lock(user_id)
        previous_ws = None
        async with lock:
            bridge = self._bridges.get(user_id)
            if bridge is None:
                bridge = RealtimeBridge(user_id=user_id, username=username)
                self._bridges[user_id] = bridge
            previous_ws = bridge.frontend_ws
            owner = bridge.bind_frontend(ws)

        if previous_ws is not None and previous_ws is not ws:
            try:
                await previous_ws.close(code=1000, reason="superseded by a newer connection")
            except Exception:
                pass
        return bridge, owner

    # 查询用户的 Bridge 状态：连接状态、会话 ID、监听状态
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

    # 获取用户的 Avatar 视频流信息
    async def get_stream_info(self, user_id: int) -> dict | None:
        bridge = self._bridges.get(user_id)
        if not bridge or not bridge._avatar_controller:
            return None
        return bridge._avatar_controller._last_stream_info

    # 停止用户的 Avatar 播报
    async def stop(self, user_id: int):
        bridge = self._bridges.get(user_id)
        if bridge and bridge._avatar_controller:
            await bridge._avatar_controller.stop()

    # 清理用户的 Bridge 实例：从字典移除并关闭连接
    async def cleanup(
        self,
        user_id: int,
        bridge: RealtimeBridge | None = None,
        owner: object | None = None,
    ):
        lock = self._get_lock(user_id)
        target = None
        async with lock:
            current = self._bridges.get(user_id)
            if current is None:
                return
            if bridge is not None and current is not bridge:
                return
            if owner is not None and not current.owns_frontend(owner):
                return
            target = self._bridges.pop(user_id)

        await target.close()


# 全局单例 — 所有路由共享同一个 BridgeManager
avatar_bridge_manager = AvatarBridgeManager()
