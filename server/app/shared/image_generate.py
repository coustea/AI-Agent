# -*- coding: utf-8 -*-
"""
教学图生成器（优化稳定版）

增强：
1. LLM输出约束 + 清洗
2. 自动重试机制
3. prompt兜底
"""

import os
import uuid
import base64
import hashlib
import hmac
import requests
import time
import logging

from datetime import datetime
from queue import Queue
from threading import Thread, Semaphore, Lock
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time

from app.config import SPARK_IMAGE_APPID, SPARK_IMAGE_API_KEY, SPARK_IMAGE_API_SECRET, SPARK_IMAGE_PATCH_ID
from app.infra.llm import get_deepseek_chat_llm

logger = logging.getLogger(__name__)

PROMPT_ENGINEER_SYSTEM = """You are an expert prompt engineer.

Output STRICTLY a diagram prompt.

Rules:
- No explanation
- No meta text
- No markdown
- Single paragraph
- Use structured diagram description
- Use correct academic terminology
- Include relationships (flow / hierarchy)

Return ONLY the prompt.
"""


class ImageGeneratorAsync:

    def __init__(self, domain="xopqwentti20b", image_dir="./images", max_concurrency=5):
        self.app_id = SPARK_IMAGE_APPID
        self.api_key = SPARK_IMAGE_API_KEY
        self.api_secret = SPARK_IMAGE_API_SECRET
        self.patch_id = SPARK_IMAGE_PATCH_ID

        self.domain = domain

        self.base_url = "https://maas-api.cn-huabei-1.xf-yun.com/v2.1/tti"
        self.host = "maas-api.cn-huabei-1.xf-yun.com"
        self.path = "/v2.1/tti"

        self.image_dir = image_dir
        os.makedirs(self.image_dir, exist_ok=True)

        self.queue = Queue()
        self.semaphore = Semaphore(max_concurrency)

        self.tasks = {}
        self.lock = Lock()

        for _ in range(max_concurrency):
            Thread(target=self._worker, daemon=True).start()

    # ================= 签名 =================
    def _build_auth_url(self):
        now = datetime.now()
        date = format_date_time(now.timestamp())

        signature_origin = f"host: {self.host}\ndate: {date}\nPOST {self.path} HTTP/1.1"

        signature_sha = hmac.new(
            self.api_secret.encode(),
            signature_origin.encode(),
            hashlib.sha256
        ).digest()

        signature = base64.b64encode(signature_sha).decode()

        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode()).decode()

        params = {
            "host": self.host,
            "date": date,
            "authorization": authorization
        }

        return f"{self.base_url}?{urlencode(params)}"

    # ================= prompt清洗 =================
    def _sanitize_prompt(self, prompt: str) -> str:
        prompt = prompt.strip()

        # 去掉换行
        prompt = prompt.replace("\n", " ")

        # 太短兜底
        if len(prompt) < 20:
            return f"Educational diagram explaining {prompt}"

        # 强制包含 diagram
        if "diagram" not in prompt.lower():
            prompt += " diagram"

        return prompt

    # ================= LLM优化 =================
    def _optimize_prompt(self, content: str) -> str:
        try:
            llm = get_deepseek_chat_llm(temperature=0.3)

            resp = llm.invoke([
                {"role": "system", "content": PROMPT_ENGINEER_SYSTEM},
                {"role": "user", "content": content}
            ])

            optimized = resp.content.strip()
            optimized = self._sanitize_prompt(optimized)

            logger.info("Prompt优化成功")
            return optimized

        except Exception as e:
            logger.warning("Prompt优化失败: %s", e)

            # fallback
            return f"Educational diagram explaining {content} with clear structure and labeled relationships"

    # ================= 参数 =================
    def _chat_params(self):
        return {
            "domain": self.domain,
            "width": 1024,
            "height": 1024,
            "seed": 42,
            "num_inference_steps": 30,
            "guidance_scale": 7,
            "scheduler": "DPM++ 2M Karras"
        }

    def _negative(self):
        return (
            "messy, cluttered, blurry, realistic photo, human, "
            "3d render, complex background, unreadable text"
        )

    # ================= 保存 =================
    def _save(self, b64):
        name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}.png"
        path = os.path.join(self.image_dir, name)

        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))

        return path

    # ================= 单次调用 =================
    def _call_api_once(self, content):
        url = self._build_auth_url()

        prompt = self._optimize_prompt(content)

        data = {
            "header": {
                "app_id": self.app_id,
                "patch_id": [self.patch_id] if self.patch_id else []
            },
            "parameter": {"chat": self._chat_params()},
            "payload": {
                "message": {"text": [{"role": "user", "content": prompt}]},
                "negative_prompts": {"text": self._negative()}
            }
        }

        with self.semaphore:
            resp = requests.post(url, json=data)

        try:
            result = resp.json()
        except:
            raise Exception(resp.text)

        if "header" not in result:
            raise Exception(result)

        if result["header"]["code"] != 0:
            raise Exception(result["header"]["message"])

        return self._save(result["payload"]["choices"]["text"][0]["content"])

    # ================= 重试机制 =================
    def _call_api(self, content):
        for i in range(3):
            try:
                return self._call_api_once(content)
            except Exception as e:
                if "10008" in str(e):
                    time.sleep(1.5 * (i + 1))
                    continue
                raise e

        raise Exception("图像生成失败（多次重试）")

    # ================= worker =================
    def _worker(self):
        while True:
            tid, content = self.queue.get()

            try:
                path = self._call_api(content)
                with self.lock:
                    self.tasks[tid]["status"] = "done"
                    self.tasks[tid]["path"] = path
            except Exception as e:
                with self.lock:
                    self.tasks[tid]["status"] = "error"
                    self.tasks[tid]["error"] = str(e)

            self.queue.task_done()

    # ================= API =================
    def generate_async(self, content):
        tid = str(uuid.uuid4())

        with self.lock:
            self.tasks[tid] = {"status": "pending", "path": None, "error": None}

        self.queue.put((tid, content))
        return tid

    def get_result(self, tid):
        return self.tasks.get(tid, {"status": "not_found"})

    def wait(self, tid):
        while True:
            r = self.get_result(tid)
            if r["status"] != "pending":
                return r
            time.sleep(0.5)


# ================= main =================
def main():
    gen = ImageGeneratorAsync()

    tid = gen.generate_async("操作系统进程调度流程图")

    print("task:", tid)

    result = gen.wait(tid)

    print(result)


if __name__ == "__main__":
    main()