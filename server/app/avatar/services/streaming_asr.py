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


# 单次 ASR 流式识别会话：消费音频队列 → 连接讯飞 → 收发音频与结果
class StreamingASRSession:
    """Single ASR recognition session handler.

    处理一次完整的 ASR 识别流程：
    1. 从音频队列获取音频块
    2. 连接讯飞 ASR WebSocket
    3. 发送音频流
    4. 接收识别结果
    """

    # 初始化会话：绑定音频队列、VAD 静默阈值，重置统计指标
    def __init__(
        self,
        audio_queue: asyncio.Queue,
        vad_eos: int = ASR_VAD_EOS,
    ):
        self.audio_queue = audio_queue
        self.vad_eos = vad_eos
        self.chunk_count = 0
        self.timeout_hit = False

    # 执行一轮 ASR 识别：等待首个音频块 → 建立连接 → 并发发送/接收 → 返回结果
    async def run(self) -> str | None:
        """Execute one ASR recognition round. Returns recognized text or None.

        Returns:
            str | None: 识别出的文本，如果无结果则返回 None

        Raises:
            RuntimeError: ASR 连接或处理失败
        """
        # 等待首个音频块（5 秒超时，超时即视为无人说话，返回 None）
        try:
            first_item = await asyncio.wait_for(self.audio_queue.get(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.debug("[ASR] No audio chunk received within timeout")
            return None

        # 收到结束信号则直接返回
        if first_item is None:
            return None

        # 解包时间戳与音频字节
        _, first_chunk = first_item

        # 构造带鉴权的讯飞 ASR WebSocket 地址
        auth_url = assemble_auth_url(AVATAR_IAT_URL, 'GET', ASR_API_KEY, ASR_API_SECRET)

        try:
            # 建立识别会话 WebSocket
            async with websockets.connect(auth_url) as ws:
                # 并发：一个任务发送音频流，一个任务接收识别结果
                send_task = asyncio.create_task(self._send_audio(ws, first_chunk))
                recv_task = asyncio.create_task(self._receive_result(ws))

                # 先等待识别结果
                result = await recv_task

                # 识别结束后取消仍在发送的任务并回收其统计指标
                if not send_task.done():
                    send_task.cancel()
                send_result = await asyncio.gather(send_task, return_exceptions=True)

                # 从发送任务结果中提取本轮回填的指标
                if isinstance(send_result[0], dict):
                    self.chunk_count = send_result[0].get("chunk_count", 0)
                    self.timeout_hit = send_result[0].get("timeout_hit", False)

                logger.info(
                    "[ASR] Session completed chunks=%d timeout=%s result_len=%d",
                    self.chunk_count,
                    self.timeout_hit,
                    len(result or ""),
                )

                # 返回本轮识别文本
                return result
        except Exception as e:
            logger.error("[ASR] Session failed: %s", e)
            raise RuntimeError(f"ASR session failed: {e}")

    # 向 ASR WebSocket 发送音频流：启动帧 → 中间帧 → 结束帧，返回发送指标
    async def _send_audio(self, ws, first_chunk: bytes) -> dict:
        """Send audio stream to ASR WebSocket.

        Args:
            ws: WebSocket connection
            first_chunk: First audio chunk (already retrieved from queue)

        Returns:
            dict: Metrics about the sending process (chunk_count, timeout_hit)
        """
        # 将首个音频块编码为 base64，构造并发送启动帧
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
        # 发送启动帧（status=0），携带首个音频块
        await ws.send(json.dumps(start_params))
        chunk_count = 1
        timeout_hit = False
        await asyncio.sleep(0.01)  # Minimal inter-frame delay for first frame

        # 循环发送中间帧（status=1），直到队列超时或收到结束信号
        while True:
            try:
                item = await asyncio.wait_for(self.audio_queue.get(), timeout=3.0)
            except asyncio.TimeoutError:
                # 队列 3 秒无数据，判定语音结束，准备发送结束帧
                timeout_hit = True
                logger.debug("[ASR] Audio queue timeout, sending end frame")
                break

            # 收到结束信号（None）则停止发送
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
            # 不添加帧间延时，尽快发送以降低延迟（队列本身随真实采集速率节流）

        # 发送结束帧（status=2），标识音频流结束
        end_frame = {
            "data": {
                "status": 2,  # 2 = last frame
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": "",
            }
        }
        # 发送结束帧并结束发送任务
        await ws.send(json.dumps(end_frame))

        # 返回本轮回填的发送指标（块数、是否触发超时）
        return {"chunk_count": chunk_count, "timeout_hit": timeout_hit}

    # 从 ASR WebSocket 接收识别结果：累加词片直到 status=2
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

            # 非零 code 表示讯飞接口错误，停止接收
            if code != 0:
                error_msg = data.get('message', 'Unknown error')
                logger.error("[ASR] API error: code=%d message=%s", code, error_msg)
                break

            result = data.get('data', {}).get('result', {})
            status = data.get('data', {}).get('status')

            # 累加本轮词片文本
            current_text = ""
            for ws_item in result.get('ws', []):
                for cw in ws_item.get('cw', []):
                    current_text += cw.get('w', '')

            # 讯飞 IAT 通常为整句快照而非增量，故用覆盖模式避免重复拼接
            if current_text:
                if status == 2:
                    # 最终结果：仅当文本有效（长度>1）才更新
                    if current_text.strip() and len(current_text.strip()) > 1:
                        result_text = current_text
                else:
                    result_text = current_text

            # status=2 表示最终结果，结束接收
            if status == 2:
                break

        # 返回去除首尾空白的识别文本
        return result_text.strip()


# 自适应 VAD 控制器：根据历史识别表现动态调整静默结束阈值
class AdaptiveVADController:
    """Adaptive VAD timeout controller.

    根据历史 ASR 轮次的表现动态调整 VAD 结束静默时长：
    - 空识别率高 → 增加 VAD timeout，避免过早结束
    - 有效语音多且速度快 → 减少 VAD timeout，提高响应速度
    """

    # 初始化：基准 VAD 阈值、连续空识别计数、空识别率、历史指标
    def __init__(self, base_vad_eos: int = ASR_VAD_EOS):
        self.base_vad_eos = base_vad_eos
        self.consecutive_empty = 0
        self.empty_rate = 0.0
        self.round_metrics: list[dict] = []

    # 根据历史指标计算自适应 VAD 静默阈值（800~1800 毫秒）
    def compute_vad_eos(self) -> int:
        """Compute adaptive VAD timeout based on metrics.

        Returns:
            int: Computed VAD EOS value in milliseconds (clamped to 800-1800)
        """
        # 以基准值为起点计算本次 VAD 静默阈值
        vad = self.base_vad_eos

        # 连续空识别较多时，加大超时避免过早截断用户说话
        if self.consecutive_empty >= 3:
            vad += 180
        if self.empty_rate >= 0.6:
            vad += 120

        # 用户说话多且快时，降低超时以提升响应速度
        if len(self.round_metrics) >= 3:
            avg_chunks = sum(
                m.get("chunk_count", 0) for m in self.round_metrics[-5:]
            ) / min(5, len(self.round_metrics))

            if avg_chunks >= 26 and self.empty_rate <= 0.35:
                vad -= 120
            elif avg_chunks >= 18 and self.empty_rate <= 0.45:
                vad -= 60

        # 阈值限制在 800~1800 毫秒之间
        return max(800, min(1800, vad))

    # 记录一轮 ASR 识别指标，更新空识别率和连续空识别计数
    def record_round(self, chunk_count: int, timeout_hit: bool, has_result: bool):
        """Record ASR round metrics for adaptive calculation.

        Args:
            chunk_count: Number of audio chunks sent this round
            timeout_hit: Whether the audio queue timed out
            has_result: Whether recognition produced non-empty text
        """
        # 更新连续空识别计数
        if has_result:
            self.consecutive_empty = 0
        else:
            self.consecutive_empty += 1

        # 重算整体空识别率
        total = len(self.round_metrics) + 1
        empty_count = sum(1 for m in self.round_metrics if not m.get("has_result"))
        if not has_result:
            empty_count += 1
        self.empty_rate = empty_count / total

        # 记录本轮指标用于后续自适应计算
        self.round_metrics.append({
            "chunk_count": chunk_count,
            "timeout_hit": timeout_hit,
            "has_result": has_result,
        })

        # 仅保留最近 20 轮，避免指标无限增长
        if len(self.round_metrics) > 20:
            self.round_metrics = self.round_metrics[-20:]

    # 重置所有统计指标到初始状态
    def reset(self):
        self.consecutive_empty = 0
        self.empty_rate = 0.0
        self.round_metrics = []