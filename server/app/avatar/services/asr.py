"""讯飞语音识别 (ASR) 客户端 — 支持实时流式语音识别。

通过 WebSocket 连接讯飞 IAT（实时语音转写）服务，
接收音频数据块并返回识别文本结果。
"""

import asyncio
import base64
import json

import websockets

from app.avatar.services import xfyun_auth
from app.config import ASR_API_KEY, ASR_API_SECRET, ASR_APP_ID, AVATAR_IAT_URL
from app.infra.logging import get_logger

logger = get_logger(__name__)


class IatClient:
    """讯飞实时语音识别客户端。"""

    def __init__(self):
        """初始化 ASR 客户端 — 生成带签名的鉴权 URL。"""
        self.auth_url = xfyun_auth.assemble_auth_url(
            AVATAR_IAT_URL, 'GET', ASR_API_KEY, ASR_API_SECRET
        )

    async def recognize_stream(self, audio_queue):
        """对音频队列执行流式语音识别。

        Args:
            audio_queue: asyncio.Queue，包含音频数据块（bytes），None 为结束信号。

        Returns:
            识别出的文本字符串。

        Raises:
            RuntimeError: 识别失败时抛出。
        """
        result_text = ""

        try:
            async with websockets.connect(self.auth_url) as ws:
                # 发送启动帧（status=0）
                start_params = {
                    "common": {"app_id": ASR_APP_ID},
                    "business": {
                        "language": "zh_cn",
                        "domain": "iat",
                        "accent": "mandarin",
                        "vad_eos": 1000,  # VAD 结束静默时长（毫秒）
                        "ptt": 1,         # 开启标点符号
                        "pd": "0",        # 说话人分离模式
                        "nunum": 0,       # 数字转写为阿拉伯数字
                        "dwa": "wpgs"     # 开启动态修正
                    },
                    "data": {
                        "status": 0,  # 0=首帧
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": ""
                    }
                }
                await ws.send(json.dumps(start_params))

                # 启动结果接收任务
                recv_task = asyncio.create_task(self._receive_results(ws))

                # 持续发送音频数据块
                while True:
                    try:
                        audio_chunk = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
                        if audio_chunk is None:  # 结束信号
                            break

                        # 将 PCM 音频数据编码为 base64
                        audio_b64 = base64.b64encode(audio_chunk).decode()
                        frame = {
                            "data": {
                                "status": 1,  # 1=中间帧
                                "format": "audio/L16;rate=16000",
                                "encoding": "raw",
                                "audio": audio_b64
                            }
                        }
                        await ws.send(json.dumps(frame))
                    except asyncio.TimeoutError:
                        continue

                # 发送结束帧（status=2）
                end_frame = {
                    "data": {
                        "status": 2,  # 2=末帧
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": ""
                    }
                }
                await ws.send(json.dumps(end_frame))

                # 等待最终识别结果
                result_text = await recv_task
                return result_text

        except Exception as e:
            logger.error(f"Speech recognition failed: {e}")
            raise RuntimeError(f"Speech recognition failed: {e}")

    async def _receive_results(self, ws):
        """持续接收并解析识别结果 — 直到收到 status=2 的最终结果。"""
        result_text = ""

        try:
            async for message in ws:
                data = json.loads(message)
                code = data.get('code', -1)

                # 非零 code 表示 API 错误
                if code != 0:
                    error_msg = data.get('message', 'Unknown error')
                    logger.error(f"ASR error: code={code}, message={error_msg}")
                    raise RuntimeError(f"ASR error: {error_msg}")

                result = data.get('data', {}).get('result', {})
                ws_list = result.get('ws', [])

                # 从识别结果中提取词语
                for ws_item in ws_list:
                    for cw in ws_item.get('cw', []):
                        word = cw.get('w', '')
                        result_text += word

                if ws_list:
                    logger.debug(f"Intermediate result: {result_text}")

                # status=2 表示最终结果，退出循环
                if data.get('data', {}).get('status') == 2:
                    logger.info(f"Final recognition result: {result_text}")
                    break

            return result_text

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Failed to receive recognition results: {e}")
            raise RuntimeError(f"Failed to receive recognition results: {e}")
