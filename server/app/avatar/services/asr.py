"""讯飞语音识别 (ASR) 客户端 — 支持实时流式语音识别。

通过 WebSocket 连接讯飞 IAT（实时语音转写）服务，
接收音频数据块并返回识别文本结果。
"""

import asyncio
import base64
import json

import websockets

from app.avatar.services import xfyun_auth
from app.config import ASR_API_KEY, ASR_API_SECRET, ASR_APP_ID, AVATAR_IAT_URL, ASR_VAD_EOS
from app.infra.logging import get_logger

logger = get_logger(__name__)


# 讯飞实时语音识别（IAT）客户端 — 支持流式语音识别
class IatClient:
    """讯飞实时语音识别客户端。"""

    # 初始化 ASR 客户端：生成带签名的鉴权 WebSocket URL
    def __init__(self):
        # 构造带签名鉴权的讯飞 IAT WebSocket 连接地址
        self.auth_url = xfyun_auth.assemble_auth_url(
            AVATAR_IAT_URL, 'GET', ASR_API_KEY, ASR_API_SECRET
        )

    # 对音频队列执行流式语音识别：发送音频帧并返回识别文本
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
            # 建立与讯飞 ASR 服务的 WebSocket 连接
            async with websockets.connect(self.auth_url) as ws:
                # 构造启动帧（status=0），携带语言、VAD、标点等识别参数
                start_params = {
                    "common": {"app_id": ASR_APP_ID},
                    "business": {
                        "language": "zh_cn",
                        "domain": "iat",
                        "accent": "mandarin",
                        "vad_eos": ASR_VAD_EOS,  # VAD 结束静默时长（毫秒）
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
                # 发送启动帧，通知服务端开始一次识别会话
                await ws.send(json.dumps(start_params))

                # 启动后台任务持续接收识别结果
                recv_task = asyncio.create_task(self._receive_results(ws))

                # 持续从音频队列取出音频块并发送（None 表示结束）
                while True:
                    try:
                        audio_chunk = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
                        # None 为结束信号，退出循环
                        if audio_chunk is None:
                            break

                        # 将 PCM 音频字节编码为 base64 后放入中间帧
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
                        # 队列超时无新数据，继续等待而非退出
                        continue

                # 发送结束帧（status=2），告知服务端音频流结束
                end_frame = {
                    "data": {
                        "status": 2,  # 2=末帧
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": ""
                    }
                }
                await ws.send(json.dumps(end_frame))

                # 阻塞等待识别结果接收任务返回最终文本
                result_text = await recv_task
                return result_text

        except Exception as e:
            # 识别过程异常，记录并向上抛出 RuntimeError
            logger.error(f"语音识别失败: {e}")
            raise RuntimeError(f"Speech recognition failed: {e}")

    # 持续接收并解析识别结果，直到收到 status=2 的最终结果
    async def _receive_results(self, ws):
        result_text = ""

        try:
            # 逐条接收服务端推送的识别消息
            async for message in ws:
                data = json.loads(message)
                code = data.get('code', -1)

                # 非零 code 表示讯飞 API 返回错误，直接抛出异常
                if code != 0:
                    error_msg = data.get('message', 'Unknown error')
                    logger.error(f"ASR 错误: code={code}, message={error_msg}")
                    raise RuntimeError(f"ASR error: {error_msg}")

                result = data.get('data', {}).get('result', {})
                ws_list = result.get('ws', [])

                # 遍历词片（ws→cw）拼接出本轮识别文本
                for ws_item in ws_list:
                    for cw in ws_item.get('cw', []):
                        word = cw.get('w', '')
                        result_text += word

                if ws_list:
                    logger.debug(f"中间识别结果: {result_text}")

                # status=2 表示已收到最终结果，结束接收循环
                if data.get('data', {}).get('status') == 2:
                    logger.info(f"最终识别结果: {result_text}")
                    break

            # 返回累计的完整识别文本
            return result_text

        except RuntimeError:
            # 已封装为 RuntimeError 的 API 错误，原样抛出
            raise
        except Exception as e:
            # 其他异常统一包装为 RuntimeError 向上传递
            logger.error(f"接收识别结果失败: {e}")
            raise RuntimeError(f"Failed to receive recognition results: {e}")
