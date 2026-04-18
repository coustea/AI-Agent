"""星火图片生成服务。

封装讯飞 HiDream 图片生成 API，提供线程池化的异步调用接口。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from time import mktime
from typing import Any, Optional
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time

import requests

from app.config import SPARK_IMAGE_APPID, SPARK_IMAGE_API_KEY, SPARK_IMAGE_API_SECRET
from app.infra.logging import get_logger
from app.shared.paths import WORKPLACE_DIR

logger = get_logger(__name__)

HIDREAM_MAX_CONCURRENCY = 2


@dataclass
class ImageGenerateResult:
    success: bool
    task_id: Optional[str] = None
    urls: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    raw_response: Optional[dict[str, Any]] = None
    decoded_text: Optional[str] = None
    error: Optional[str] = None


@dataclass
class _ImageTask:
    prompt: str
    image_path: Optional[str] = None
    aspect_ratio: str = "1:1"
    negative_prompt: str = ""
    img_count: int = 1
    resolution: str = "2k"
    save_subdir: str = "generated_images"
    timeout_seconds: int = 180
    poll_interval: float = 2.0
    future: Future = field(default_factory=Future)


class SparkImageGenerator:
    """星火 HiDream 图片生成客户端（线程池化）。

    - 从 config 读取密钥
    - 任务队列 + worker 线程控制并发
    - 输出到 WORKPLACE_DIR / {save_subdir}
    """

    _CREATE_URL = "https://cn-huadong-1.xf-yun.com/v1/private/s3fd61810/create"
    _QUERY_URL = "https://cn-huadong-1.xf-yun.com/v1/private/s3fd61810/query"

    def __init__(self, max_concurrency: int = HIDREAM_MAX_CONCURRENCY, request_timeout: int = 60) -> None:
        self.appid = SPARK_IMAGE_APPID
        self.api_key = SPARK_IMAGE_API_KEY
        self.api_secret = SPARK_IMAGE_API_SECRET

        if not all([self.appid, self.api_key, self.api_secret]):
            raise ValueError("星火图片生成缺少配置: SPARK_IMAGE_GENERATION_APPID/API_KEY/APP_SECRET")

        self.request_timeout = request_timeout
        # 官网能力上限为 2 并发，这里做硬约束，防止误配置把服务压垮。
        requested = max(1, int(max_concurrency))
        self.max_concurrency = min(requested, HIDREAM_MAX_CONCURRENCY)
        if self.max_concurrency != requested:
            logger.warning(
                "[图片生成] 并发已限制为 %s（请求值=%s）",
                self.max_concurrency,
                requested,
            )

        self._task_queue: queue.Queue[Optional[_ImageTask]] = queue.Queue()
        self._closed = False
        self._active_count = 0
        self._active_lock = threading.Lock()
        self._workers: list[threading.Thread] = []
        for i in range(self.max_concurrency):
            w = threading.Thread(target=self._worker_loop, name=f"spark-image-{i}", daemon=True)
            w.start()
            self._workers.append(w)

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

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
        """提交图片生成任务，返回 Future。"""
        if self._closed:
            future = Future()
            future.set_result(ImageGenerateResult(success=False, error="图片生成服务已关闭，无法继续提交任务"))
            return future

        task = _ImageTask(
            prompt=prompt,
            image_path=image_path,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt,
            img_count=img_count,
            resolution=resolution,
            save_subdir=save_subdir,
            timeout_seconds=timeout_seconds,
        )
        self._task_queue.put(task)
        logger.debug("[图片生成] 任务入队，队列长度=%s", self._task_queue.qsize())
        return task.future

    def shutdown(self, wait: bool = True) -> None:
        if self._closed:
            return
        self._closed = True
        for _ in self._workers:
            self._task_queue.put(None)
        if wait:
            self._task_queue.join()
            for w in self._workers:
                w.join()

    # ------------------------------------------------------------------
    # Worker
    # ------------------------------------------------------------------

    def _worker_loop(self) -> None:
        while True:
            task = self._task_queue.get()
            try:
                if task is None:
                    return
                with self._active_lock:
                    self._active_count += 1
                result = self._execute(task)
                task.future.set_result(result)
            except Exception as exc:
                if task is not None:
                    task.future.set_result(ImageGenerateResult(success=False, error=str(exc)))
            finally:
                with self._active_lock:
                    self._active_count = max(0, self._active_count - (0 if task is None else 1))
                self._task_queue.task_done()

    def _execute(self, task: _ImageTask) -> ImageGenerateResult:
        task_id = self.create_task(
            prompt=task.prompt,
            image_path=task.image_path,
            aspect_ratio=task.aspect_ratio,
            negative_prompt=task.negative_prompt,
            img_count=task.img_count,
            resolution=task.resolution,
        )
        logger.info("[图片生成] 任务已创建 task_id=%s", task_id)

        query_result = self._poll_result(task_id, interval=task.poll_interval, max_wait=task.timeout_seconds)
        decoded_text = query_result.get("decoded_text")
        raw_response = query_result.get("raw_response", {})

        urls, image_bytes_list = self._extract_images(decoded_text)

        save_dir = WORKPLACE_DIR / task.save_subdir
        save_dir.mkdir(parents=True, exist_ok=True)

        paths: list[str] = []
        for idx, img_bytes in enumerate(image_bytes_list, start=1):
            fp = save_dir / f"{task_id}_{idx}.png"
            fp.write_bytes(img_bytes)
            paths.append(str(fp.resolve()))

        if paths:
            logger.info("[图片生成] 保存完成 task_id=%s 文件数=%d", task_id, len(paths))

        return ImageGenerateResult(
            success=True,
            task_id=task_id,
            urls=urls,
            paths=paths,
            raw_response=raw_response,
            decoded_text=decoded_text,
        )

    # ------------------------------------------------------------------
    # 星火 API 底层
    # ------------------------------------------------------------------

    def _create_url(self, url: str) -> str:
        """与官网样例 `create_url` 一致的鉴权 URL 生成逻辑。"""
        host = urlparse(url).netloc
        path = urlparse(url).path
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        sig_origin = f"host: {host}\ndate: {date}\nPOST {path} HTTP/1.1"
        sig = hmac.new(self.api_secret.encode(), sig_origin.encode(), digestmod=hashlib.sha256).digest()
        sig_b64 = base64.b64encode(sig).decode()

        auth_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{sig_b64}"'
        )
        auth = base64.b64encode(auth_origin.encode()).decode()

        return url + "?" + urlencode({"authorization": auth, "date": date, "host": host})

    def _get_headers(self, url: str) -> dict[str, str]:
        """与官网样例 `get_headers` 对齐。"""
        return {
            "content-type": "application/json",
            "host": urlparse(url).netloc,
            "app_id": self.appid,
        }

    def _gen_create_request_data(self, text_b64: str) -> dict[str, Any]:
        """与官网样例 `gen_create_request_data` 对齐。"""
        return {
            "header": {
                "app_id": self.appid,
                "status": 3,
                "channel": "default",
                "callback_url": "default",
            },
            "parameter": {
                "oig": {
                    "result": {
                        "encoding": "utf8",
                        "compress": "raw",
                        "format": "json",
                    },
                }
            },
            "payload": {
                "oig": {
                    "text": text_b64,
                },
            },
        }

    def create_task(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        aspect_ratio: str = "1:1",
        negative_prompt: str = "",
        img_count: int = 1,
        resolution: str = "2k",
    ) -> str:
        """创建 HiDream 任务并返回 task_id（官网样例 create_task 封装版）。"""
        images: list[str] = []
        if image_path:
            with open(image_path, "rb") as f:
                images.append(base64.b64encode(f.read()).decode())

        text_payload = {
            "image": images,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "negative_prompt": negative_prompt,
            "img_count": img_count,
            "resolution": resolution,
        }
        text_b64 = base64.b64encode(json.dumps(text_payload, ensure_ascii=False).encode()).decode()
        body = self._gen_create_request_data(text_b64)

        resp = requests.post(
            self._create_url(self._CREATE_URL),
            data=json.dumps(body, ensure_ascii=False),
            headers=self._get_headers(self._CREATE_URL),
            timeout=self.request_timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        code = data.get("header", {}).get("code")
        if code != 0:
            raise RuntimeError(f"创建图片任务失败: {data}")

        task_id = data.get("header", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"未返回 task_id: {data}")
        return task_id

    def query_task(self, task_id: str) -> dict[str, Any]:
        """查询任务状态（官网样例 query_task 封装版）。"""
        body = {"header": {"app_id": self.appid, "task_id": task_id}}
        resp = requests.post(
            self._create_url(self._QUERY_URL),
            data=json.dumps(body, ensure_ascii=False),
            headers=self._get_headers(self._QUERY_URL),
            timeout=self.request_timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _poll_result(self, task_id: str, interval: float = 2.0, max_wait: int = 180) -> dict[str, Any]:
        start = time.time()
        while True:
            if time.time() - start > max_wait:
                raise TimeoutError(f"图片生成超时 task_id={task_id}")

            data = self.query_task(task_id)

            header = data.get("header", {})
            code = header.get("code")
            if code != 0:
                raise RuntimeError(f"查询图片任务失败: {data}")

            status = str(header.get("task_status", ""))
            if status == "3":
                encoded = (data.get("payload", {}).get("result", {}).get("text", ""))
                decoded = None
                if encoded:
                    try:
                        decoded = base64.b64decode(encoded).decode("utf-8")
                    except UnicodeDecodeError:
                        decoded = base64.b64decode(encoded).decode("utf-8", errors="ignore")
                return {"task_id": task_id, "raw_response": data, "decoded_text": decoded}

            if status in {"1", "2", "4"}:
                time.sleep(interval)
                continue

            raise RuntimeError(f"未知图片任务状态: {data}")

    # ------------------------------------------------------------------
    # 图片提取
    # ------------------------------------------------------------------

    def _extract_images(self, decoded_text: Optional[str]) -> tuple[list[str], list[bytes]]:
        if not decoded_text:
            return [], []
        try:
            obj = json.loads(decoded_text)
        except Exception:
            return [], []

        urls: list[str] = []
        images: list[bytes] = []

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                for k, v in node.items():
                    kl = str(k).lower()
                    if kl in {"url", "img_url", "image_url"} and isinstance(v, str) and v.startswith(("http://", "https://")):
                        urls.append(v)
                    if kl in {"image", "img", "base64", "img_base64"} and isinstance(v, str):
                        img = self._try_decode_b64(v)
                        if img:
                            images.append(img)
                    walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)
            elif isinstance(node, str):
                if node.startswith(("http://", "https://")):
                    urls.append(node)
                else:
                    img = self._try_decode_b64(node)
                    if img:
                        images.append(img)

        walk(obj)
        urls = list(dict.fromkeys(urls))
        unique: list[bytes] = []
        seen: set[str] = set()
        for b in images:
            h = hashlib.md5(b).hexdigest()
            if h not in seen:
                seen.add(h)
                unique.append(b)
        return urls, unique

    @staticmethod
    def _try_decode_b64(value: str) -> Optional[bytes]:
        if not value or len(value) < 100:
            return None
        if "," in value and "base64" in value[:50]:
            value = value.split(",", 1)[1]
        try:
            raw = base64.b64decode(value, validate=False)
        except Exception:
            return None
        if raw.startswith((b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"RIFF")):
            return raw
        return None


# ---------------------------------------------------------------------------
# 模块级单例（懒加载）
# ---------------------------------------------------------------------------
_generator: Optional[SparkImageGenerator] = None
_generator_lock = threading.Lock()


def get_image_generator() -> Optional[SparkImageGenerator]:
    """获取图片生成器单例。配置不完整时返回 None。"""
    global _generator
    if _generator is not None:
        return _generator

    appid = SPARK_IMAGE_APPID
    api_key = SPARK_IMAGE_API_KEY
    api_secret = SPARK_IMAGE_API_SECRET
    if not all([appid, api_key, api_secret]):
        return None

    with _generator_lock:
        if _generator is None:
            _generator = SparkImageGenerator()
            logger.info("[图片生成] 服务初始化完成")
    return _generator
