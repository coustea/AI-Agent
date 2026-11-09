"""运行观察钩子：记录真实执行状态，并唤醒 SSE 订阅者读取最新快照。"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import json
import time
from typing import Any

from app.chat.schemas import RunArtifact, RunPhase, RunState, RunStep, SourceItem, SubStep, TerminalStatus
from app.chat.memory import LTM_CATEGORY_NAMES
from app.infra.llm import Message, ToolCall

_MAX_PREVIEW_CHARS = 800


def _truncate(value: Any, limit: int = _MAX_PREVIEW_CHARS) -> str:
    """将任意文本截断到可读预览长度。"""
    text = str(value or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _extract_artifact(call_id: str, tool_name: str, raw: Any) -> RunArtifact | None:
    """从 PPT 或教学视频工具的返回字典中提取可下载产物。"""
    if not isinstance(raw, dict):
        return None
    url = raw.get("video_url") or raw.get("pptx_url") or raw.get("file_url")
    if not isinstance(url, str) or not url:
        return None
    kind = "video" if raw.get("video_url") else "ppt"
    return RunArtifact(
        id=f"{kind}:{call_id}",
        kind=kind,
        title=str(raw.get("title") or tool_name),
        url=url,
        preview_url=raw.get("preview_url"),
        metadata={k: v for k, v in raw.items() if isinstance(v, (str, int, float, bool))},
    )


def _extract_sources(raw: Any) -> list[SourceItem]:
    """从工具返回字典中提取结构化引用来源列表。"""
    if not isinstance(raw, dict):
        return []
    raw_sources = raw.get("sources")
    if not isinstance(raw_sources, list):
        return []
    items: list[SourceItem] = []
    for item in raw_sources:
        if isinstance(item, dict):
            items.append(SourceItem(**{k: v for k, v in item.items() if k in SourceItem.model_fields}))
        elif isinstance(item, SourceItem):
            items.append(item)
    return items


class RunHooks:
    """每次运行独立的状态容器；队列仅保存更新通知，不积压文本或旧事件。"""

    def __init__(self, run_id: str) -> None:
        """初始化运行快照、取消标记与订阅集合。"""
        self.state = RunState(run_id=run_id)
        self.task: asyncio.Task[None] | None = None
        self.cancel_requested = False
        self.started_at = time.monotonic()
        self.model_step: RunStep | None = None
        self.tool_step: RunStep | None = None
        self._subscribers: set[asyncio.Queue[None]] = set()

    def snapshot(self) -> RunState:
        """复制当前状态，避免订阅者持有后续会变化的步骤对象。"""
        state = self.state.model_copy(deep=True)
        if state.status in {"queued", "running"}:
            state.total_elapsed_ms = int((time.monotonic() - self.started_at) * 1000)
        return state

    def subscribe(self) -> asyncio.Queue[None]:
        """注册容量为一的通知队列；调用方随后读取当前快照。"""
        queue: asyncio.Queue[None] = asyncio.Queue(maxsize=1)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[None]) -> None:
        """移除断开的订阅者。"""
        self._subscribers.discard(queue)

    def publish(self) -> None:
        """合并尚未消费的更新通知；全过程不让出事件循环。"""
        for queue in self._subscribers:
            if not queue.full():
                queue.put_nowait(None)

    def set_phase(self, phase: RunPhase, label: str) -> None:
        """记录已实际进入的执行阶段并通知订阅者。"""
        self.state.status = "running"
        self.state.phase = phase
        self.state.phase_label = label
        self.publish()

    def on_model_start(self, round_number: int) -> None:
        """模型请求发出前记录轮次，清空上一轮临时输出。"""
        self.state.content = ""
        self.model_step = RunStep(
            step_id=f"model:{round_number}",
            title=f"第 {round_number} 次模型调用",
            subtitle="等待模型响应",
        )
        self.state.steps.append(self.model_step)
        self.set_phase("waiting_model", "等待模型响应")

    def on_text(self, delta: str) -> None:
        """收到实际文本片段后追加内容；模型步骤保持运行直到响应结束。"""
        self.state.content += delta
        self.state.phase = "streaming"
        self.state.phase_label = "正在接收模型输出"
        if self.model_step is not None:
            self.model_step.subtitle = "正在接收模型输出"
        self.publish()

    def on_model_end(self, message: Message) -> None:
        """模型响应结束后记录输出和工具调用数量。"""
        self.state.content = message.content
        if self.model_step is not None:
            self.model_step.status = "completed"
            self.model_step.elapsed_ms = int((time.time() - self.model_step.started_at) * 1000)
            self.model_step.subtitle = (
                f"请求调用 {len(message.tool_calls)} 个工具" if message.tool_calls else "模型输出结束"
            )
        self.publish()

    def on_tool_start(self, call: ToolCall) -> None:
        """工具执行前记录调用 ID、名称和参数。"""
        title, subtitle = describe_tool_call(call.name, dict(call.args))
        self.tool_step = RunStep(
            step_id=f"tool:{call.id}",
            title=title,
            subtitle=subtitle,
            tool_name=call.name,
            input_preview=_truncate(json.dumps(dict(call.args), ensure_ascii=False, indent=2), 600),
        )
        self.state.steps.append(self.tool_step)
        self.set_phase("tool_calling", f"正在执行：{title}")

    async def on_subagent_progress(self, tool_name: str, message: str) -> None:
        """记录子智能体实际报告的活动。"""
        step = self.tool_step
        if step is None or step.tool_name != tool_name:
            return
        if not step.sub_steps or step.sub_steps[-1].title != message:
            step.sub_steps.append(SubStep(id=f"{step.step_id}:{len(step.sub_steps)}", title=message))
        self.state.phase_label = f"{step.title} · {message}"
        self.publish()

    def on_tool_end(self, call: ToolCall, raw: Any, output_text: str) -> None:
        """工具返回后记录真实结果、错误、引用和产物。"""
        step = self.tool_step
        if step is None:
            raise RuntimeError("工具尚未开始")
        failed = isinstance(raw, Mapping) and (
            raw.get("status") == "failed"
            or raw.get("success") is False
            or raw.get("exit_code", 0) not in (0, None)
        )
        step.status = "failed" if failed else "completed"
        step.elapsed_ms = int((time.time() - step.started_at) * 1000)
        step.output_preview = _truncate(output_text)
        step.error = _truncate(output_text, 300) if failed else ""
        if not failed:
            self.state.sources.extend(_extract_sources(raw))
            artifact = _extract_artifact(call.id, call.name, raw)
            if artifact is not None:
                self.state.artifacts.append(artifact)
        self.tool_step = None
        self.publish()

    def result_state(self, status: TerminalStatus, error: str = "") -> RunState:
        """构建待持久化的终态副本；保存完成前不向订阅者宣布结束。"""
        state = self.snapshot()
        for step in state.steps:
            if step.status == "running":
                step.status = "completed" if status == "completed" else (
                    "cancelled" if status == "cancelled" else "failed"
                )
                step.elapsed_ms = int((time.time() - step.started_at) * 1000)
        state.status = status
        state.phase = status
        state.phase_label = {
            "completed": "回答完成",
            "failed": "运行失败",
            "cancelled": "已停止生成",
            "interrupted": "运行已中断",
        }[status]
        state.error = error
        return state

def _short(value: Any, limit: int = 72) -> str:
    """将任意值转换为单行简短摘要。"""
    text = " ".join(str(value or "").strip().split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def describe_tool_call(name: str, args: dict[str, Any]) -> tuple[str, str]:
    """将工具名称与参数映射为前端可直观展示的 (中文标题, 调用说明)。"""
    if name == "get_learner_profile":
        reason = _short(args.get("reason") or "个性化背景与薄弱点")
        return "查阅学习者画像", reason

    if name == "get_long_term_memory":
        cat = str(args.get("category") or "").strip()
        cat_cn = LTM_CATEGORY_NAMES.get(cat, cat)
        reason = _short(args.get("reason") or cat_cn or "历史学习记录与偏好")
        sub = f"{cat_cn} · {reason}" if cat_cn and cat_cn not in reason else reason
        return "读取长期学习记忆", sub

    if name == "view_image":
        raw_path = str(args.get("path") or "图片")
        filename = raw_path.rsplit("/", 1)[-1]
        question = _short(args.get("question") or "识别画面细节与文字信息", 60)
        return f"视觉理解图片 · {filename}", question

    if name in {"read_document", "read"}:
        raw_path = str(args.get("path") or "文档")
        filename = raw_path.rsplit("/", 1)[-1]
        return "读取文件内容", filename

    if name in {"glob", "grep"}:
        pattern = _short(args.get("pattern") or args.get("path") or "*")
        return "搜索工作区文件", f"匹配：{pattern}"

    if name in {"write", "edit"}:
        raw_path = str(args.get("path") or "文件")
        filename = raw_path.rsplit("/", 1)[-1]
        return "编写工作区文件", filename

    if name == "bash":
        cmd = _short(args.get("command") or "", 64)
        return "执行命令与环境检查", cmd

    if name == "generate_ppt_deck":
        topic = _short(args.get("topic") or "教学课件", 48)
        return "生成 PPT 教学课件", f"主题：{topic}"

    if name == "generate_teaching_video":
        topic = _short(args.get("topic") or "教学动画视频", 48)
        return "制作教学动画视频", f"主题：{topic}"

    return f"执行工具 {name}", _short(args, 60)
