#!/usr/bin/env python3
"""本地的 OpenAI 兼容假模型服务，用于端到端验证 Mentorly 的完整链路。

它不是"mock 掉 Harness"，而是真的提供一个符合 OpenAI Chat Completions 协议的
HTTP 服务：Mentorly 里真实的 eino ChatModel、真实的 streaming、真实的 tool_call
都会跑到，只是模型的"智能"被替换成可预测的脚本。

用法：
    python3 scripts/fake_llm.py [port]
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 18081


def sse(payload):
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()


def chunk(content="", tool_calls=None, finish=None, usage=None):
    delta = {}
    if content:
        delta["content"] = content
    if tool_calls:
        delta["tool_calls"] = tool_calls
    choice = {"index": 0, "delta": delta, "finish_reason": finish}
    out = {
        "id": "chatcmpl-fake",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "fake-model",
        "choices": [choice],
    }
    if usage:
        out["usage"] = usage
    return out


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("[fake-llm] " + fmt % args + "\n")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        messages = body.get("messages", [])
        stream = body.get("stream", False)
        has_tools = bool(body.get("tools"))

        text = self.compose(messages, has_tools, body)

        if not stream:
            payload = {
                "id": "chatcmpl-fake",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "fake-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": len(text),
                    "total_tokens": 100 + len(text),
                },
            }
            data = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        # 慢速模式：请求里带 [SLOW] 时每块多等一会，用于验证会话锁与取消
        slow = False
        for m in messages:
            if "[SLOW]" in (m.get("content") or ""):
                slow = True
                break

        # 分块推流，模拟真实模型的逐字输出
        for i in range(0, len(text), 8):
            self.wfile.write(sse(chunk(content=text[i : i + 8])))
            self.wfile.flush()
            time.sleep(0.35 if slow else 0.01)

        usage = {
            "prompt_tokens": 100,
            "completion_tokens": len(text),
            "total_tokens": 100 + len(text),
        }
        self.wfile.write(sse(chunk(finish="stop", usage=usage)))
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def compose(self, messages, has_tools, body):
        """把请求映射成可预测的回答，覆盖各种验证场景。"""
        # 摘要任务 / 记忆整合任务：非流式，返回结构化 Markdown
        system = ""
        for m in messages:
            if m.get("role") == "system":
                system = m.get("content") or ""
                break

        if "对话摘要专家" in system:
            return "## 已讨论主题\n\n-GO 并发\n\n## 关键结论\n\n-GMP 模型"

        if "长期记忆档案" in system:
            return (
                "## 学习背景\n\n计算机专业大三\n\n"
                "## 长期目标\n\n后端工程师\n\n"
                "## 学习偏好\n\n喜欢先看可运行代码\n\n"
                "## 薄弱知识点\n\nGC 细节\n\n"
                "## 交互约定\n\n用中文回答"
            )

        # 标题生成（system 里要求 20 字以内）
        if "对话标题生成器" in system:
            return "Go 并发模型讨论"

        # 取最后一条 user 消息作为回答依据
        user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_text = m.get("content") or ""
                break

        # 超长慢回答：用于验证客户端断开后的 cancelled 落库
        if "[LONG]" in user_text:
            return "这是一个很长的回答。" * 200

        # 验证越界读取被拒绝：模型尝试读 /etc/passwd
        if "读密码" in user_text:
            return "我看到工具返回了错误，说明沙箱拒绝了越界访问，这是正确行为。本轮回答完毕。"

        # 验证文件写入与技能读取
        if "写文件" in user_text:
            return "已把笔记写入 /workspace/notes.md，并参考了技能规范。本轮回答完毕。"

        # 验证记忆调用（模型主动 remember）
        if "记住" in user_text:
            return "好的，我记住了你的偏好。本轮回答完毕。"

        # 普通回答：把上一轮内容回显，用于验证多轮上下文连贯
        prev = ""
        for m in messages:
            if m.get("role") == "assistant" and m.get("content"):
                prev = m["content"][:20]

        if prev:
            return f"（参考了上一轮：{prev}）针对「{user_text[:20]}」的回答。本轮回答完毕。"

        return f"这是对「{user_text[:30]}」的首轮回答。本轮回答完毕。"


if __name__ == "__main__":
    sys.stderr.write(f"[fake-llm] listening on :{PORT}\n")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()