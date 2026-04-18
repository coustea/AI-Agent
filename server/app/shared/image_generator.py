"""星火图片生成服务。

根据 demo/word2picture.py 重新封装，提供基于 v2.1/tti 接口的图片生成客户端。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from time import mktime
from typing import Any, Optional
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time

import requests
from app.config import (
    SPARK_IMAGE_GENERATION_APPID,
    SPARK_IMAGE_GENERATION_API_KEY,
    SPARK_IMAGE_GENERATION_APP_SECRET,
    WORKPLACE_DIR,
)
from app.infra.logging import get_logger
from app.shared.paths import WORKPLACE_DIR

logger = get_logger(__name__)

IMAGE_GENERATION_MAX_CONCURRENCY = 2


@dataclass
class ImageGenerateResult:
    success: bool
    task_id: Optional[str] = None
    urls: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    raw_response: Optional[dict[str, Any]] = None
    decoded_text: Optional[str] = None
    error: Optional[str] = None


class AssembleHeaderException(Exception):
    def __init__(self, msg):
        self.message = msg


class Url:
    def __init__(self, host, path, schema):
        self.host = host
        self.path = path
        self.schema = schema


def parse_url(requset_url: str) -> Url:
    stidx = requset_url.index("://")
    host = requset_url[stidx + 3:]
    schema = requset_url[:stidx + 3]
    edidx = host.index("/")
    if edidx <= 0:
        raise AssembleHeaderException("invalid request url:" + requset_url)
    path = host[edidx:]
    host = host[:edidx]
    return Url(host, path, schema)


def assemble_ws_auth_url(requset_url: str, method: str = "GET", api_key: str = "", api_secret: str = "") -> str:
    """生成鉴权 URL"""
    u = parse_url(requset_url)
    host = u.host
    path = u.path
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    
    signature_origin = f"host: {host}\ndate: {date}\n{method} {path} HTTP/1.1"
    signature_sha = hmac.new(
        api_secret.encode('utf-8'),
        signature_origin.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    
    signature_sha_b64 = base64.b64encode(signature_sha).decode(encoding='utf-8')
    authorization_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_b64}"'
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
    
    values = {
        "host": host,
        "date": date,
        "authorization": authorization
    }
    return requset_url + "?" + urlencode(values)


class SparkImageGenerator:
    """星火图片生成客户端（线程池化）。

    - 从 config 读取密钥
    - 基于 v2.1/tti 接口实现
    - 兼容原来的 generate 接口并返回 Future
    """

    _API_URL = "http://spark-api.cn-huabei-1.xf-yun.com/v2.1/tti"

    def __init__(self, max_concurrency: int = IMAGE_GENERATION_MAX_CONCURRENCY, request_timeout: int = 60) -> None:
        self.appid = SPARK_IMAGE_GENERATION_APPID
        self.api_key = SPARK_IMAGE_GENERATION_API_KEY
        self.api_secret = SPARK_IMAGE_GENERATION_APP_SECRET

        if not all([self.appid, self.api_key, self.api_secret]):
            raise ValueError("星火图片生成缺少配置: SPARK_IMAGE_GENERATION_APPID/API_KEY/APP_SECRET")

        self.request_timeout = request_timeout
        requested = max(1, int(max_concurrency))
        self.max_concurrency = min(requested, IMAGE_GENERATION_MAX_CONCURRENCY)
        
        self._executor = ThreadPoolExecutor(max_workers=self.max_concurrency)
        self._closed = False

    def get_body(self, text: str) -> dict[str, Any]:
        """生成请求 body 体"""
        return {
            "header": {
                "app_id": self.appid,
                "uid": "123456789"
            },
            "parameter": {
                "chat": {
                    "domain": "general",
                    "temperature": 0.5,
                    "max_tokens": 4096
                }
            },
            "payload": {
                "message": {
                    "text": [
                        {
                            "role": "user",
                            "content": text
                        }
                    ]
                }
            }
        }

    def generate(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        aspect_ratio: str = "1:1",
        negative_prompt: str = "",
        img_count: int = 1,
        resolution: str = "2k",
        save_subdir: str = "generated_images",
        timeout_seconds: int = 180,
    ) -> Future:
        """提交图片生成任务，返回 Future。为了兼容保留了其他无用参数。"""
        future = Future()
        if self._closed:
            future.set_result(ImageGenerateResult(success=False, error="图片生成服务已关闭"))
            return future

        # 闭包，将任务放到线程池执行
        def task():
            try:
                result = self._execute(prompt, save_subdir, timeout_seconds)
                future.set_result(result)
            except Exception as e:
                logger.exception("[图片生成] 任务执行异常")
                future.set_result(ImageGenerateResult(success=False, error=str(e)))

        self._executor.submit(task)
        return future

    def _execute(self, prompt: str, save_subdir: str, timeout: int) -> ImageGenerateResult:
        logger.info(f"[图片生成] 开始执行图生文请求, prompt: {prompt}")
        
        url = assemble_ws_auth_url(
            self._API_URL, 
            method='POST', 
            api_key=self.api_key, 
            api_secret=self.api_secret
        )
        content = self.get_body(prompt)
        
        # 发起请求并返回结果
        start_time = time.time()
        response = requests.post(
            url, 
            json=content, 
            headers={'content-type': "application/json"},
            timeout=timeout
        )
        response.raise_for_status()
        logger.info(f"[图片生成] 请求耗时: {time.time() - start_time:.2f}s")
        
        data = response.json()
        code = data.get('header', {}).get('code')
        if code != 0:
            error_msg = f"API 返回错误: {code}, {data}"
            logger.error(f"[图片生成] {error_msg}")
            return ImageGenerateResult(success=False, error=error_msg, raw_response=data)
        
        text_choices = data.get("payload", {}).get("choices", {}).get("text", [])
        if not text_choices:
            return ImageGenerateResult(success=False, error="未返回图片数据", raw_response=data)
            
        image_base64 = text_choices[0].get("content")
        if not image_base64:
            return ImageGenerateResult(success=False, error="未返回 base64 数据", raw_response=data)
            
        image_name = data.get('header', {}).get('sid', str(time.time()))
        
        save_dir = WORKPLACE_DIR / save_subdir
        save_dir.mkdir(parents=True, exist_ok=True)
        
        img_data = base64.b64decode(image_base64)
        file_path = save_dir / f"{image_name}.png"
        
        with open(file_path, 'wb') as f:
            f.write(img_data)
            
        resolved_path = str(file_path.resolve())
        logger.info(f"[图片生成] 图片已保存至 {resolved_path}")
        
        return ImageGenerateResult(
            success=True,
            task_id=image_name,
            paths=[resolved_path],
            raw_response=data
        )

    def shutdown(self, wait: bool = True) -> None:
        self._closed = True
        self._executor.shutdown(wait=wait)


_generator: Optional[SparkImageGenerator] = None
_generator_lock = threading.Lock()

def get_image_generator() -> Optional[SparkImageGenerator]:
    """获取图片生成器单例。配置不完整时返回 None。"""
    global _generator
    if _generator is not None:
        return _generator

    appid = SPARK_IMAGE_GENERATION_APPID
    api_key = SPARK_IMAGE_GENERATION_API_KEY
    api_secret = SPARK_IMAGE_GENERATION_APP_SECRET
    if not all([appid, api_key, api_secret]):
        return None

    with _generator_lock:
        if _generator is None:
            _generator = SparkImageGenerator()
            logger.info("[图片生成] 服务初始化完成")
    return _generator


if __name__ == "__main__":
    import logging
    import sys
    
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    gen = get_image_generator()
    if not gen:
        print("\n[错误] 无法获取图片生成器，请检查配置")
    else:
        test_prompt = "生成一张图：远处有着高山，山上覆盖着冰雪，近处有着一片湛蓝的湖泊，不要有水印"
        print(f"\n>>> 正在测试图片生成")
        print(f">>> Prompt: {test_prompt}")
        
        future = gen.generate(
            prompt=test_prompt,
            save_subdir="test_images"
        )
        
        print(">>> 任务已提交，等待处理...")
        try:
            result = future.result(timeout=200)
            if result.success:
                print(f"\n[成功] 图片生成完成！")
                print(f"Task ID: {result.task_id}")
                print(f"本地路径: {result.paths}")
            else:
                print(f"\n[失败] 生成出错: {result.error}")
        except Exception as e:
            print(f"\n[异常] 测试过程中发生错误: {e}")
        finally:
            print("\n>>> 正在关闭服务...")
            gen.shutdown(wait=True)
