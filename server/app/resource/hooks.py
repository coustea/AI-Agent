"""Resource 模块运行观察钩子 (app.resource.hooks)。

对齐 chat.RunHooks 架构：负责维护快照状态机与多模态产物收集，
并通过极轻量的订阅队列唤醒 SSE 推送，主循环不耦合任何外部副作用。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.infra.llm import ToolCall
from app.infra.logging import get_logger
from app.resource.schemas import (
    ResourceArtifact,
    ResourceRunPhase,
    ResourceRunState,
    ResourceStep,
    TerminalStatus,
)

logger = get_logger(__name__)


def _extract_resource_artifact(call_id: str, tool_name: str, raw: Any) -> ResourceArtifact | None:
    """从工具返回值中提取标准化的 ResourceArtifact 产物模型。"""
    if not isinstance(raw, dict):
        return None

    status = raw.get("status")
    if status not in ("ok", "success") and not raw.get("pptx_url") and not raw.get("video_url"):
        # 工具未能成功生成有效产物
        return None

    # 根据工具名称推导 kind 与类型
    if tool_name in ("generate_ppt_deck", "ppt"):
        kind = "ppt"
        file_type = "pptx"
        url = raw.get("pptx_url") or raw.get("file_url")
        preview_urls = raw.get("preview_urls") or []
        content = None
    elif tool_name in ("generate_teaching_video", "cartoon"):
        kind = "cartoon"
        file_type = "mp4"
        url = raw.get("video_url") or raw.get("file_url")
        preview_urls = []
        content = None
    elif tool_name == "generate_quiz":
        kind = "quiz"
        file_type = "json"
        url = None
        preview_urls = []
        content = raw.get("content")
    elif tool_name == "generate_reading":
        kind = "reading"
        file_type = "json"
        url = None
        preview_urls = []
        content = raw.get("content")
    elif tool_name == "generate_mindmap":
        kind = "mindmap"
        file_type = "markdown"
        url = None
        preview_urls = []
        content = raw.get("content")
    elif tool_name == "generate_code":
        kind = "code"
        file_type = "markdown"
        url = None
        preview_urls = []
        content = raw.get("content")
    else:
        kind = "content"
        file_type = "markdown"
        url = None
        preview_urls = []
        content = raw.get("content")

    title = str(raw.get("title") or f"{kind} 教学资源")
    summary = str(raw.get("summary") or "")

    return ResourceArtifact(
        id=f"art-{kind}-{call_id}",
        kind=kind,
        title=title,
        file_type=file_type,
        url=url,
        preview_urls=preview_urls,
        content=content,
        summary=summary,
        metadata={k: v for k, v in raw.items() if isinstance(v, (str, int, float, bool, list, dict))},
    )


class ResourceRunHooks:
    """Resource 主 Agent 运行状态容器与观察钩子。"""

    def __init__(self, run_id: str, resource_id: int) -> None:
        """初始化运行快照容器、计时器与订阅者集合。"""
        self.state = ResourceRunState(run_id=run_id, resource_id=resource_id)
        self.task: asyncio.Task[None] | None = None
        self.cancel_requested = False
        self.started_at = time.monotonic()
        self._subscribers: set[asyncio.Queue[None]] = set()
        self._current_steps: dict[str, ResourceStep] = {}

    def snapshot(self) -> ResourceRunState:
        """复制当前状态快照，计算最新累计耗时。"""
        copied = self.state.model_copy(deep=True)
        if copied.status in {"queued", "running"}:
            copied.total_elapsed_ms = int((time.monotonic() - self.started_at) * 1000)
        return copied

    def subscribe(self) -> asyncio.Queue[None]:
        """注册容量为 1 的通知队列；当产生新快照时通知调用方。"""
        queue: asyncio.Queue[None] = asyncio.Queue(maxsize=1)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[None]) -> None:
        """注销断开的订阅者队列。"""
        self._subscribers.discard(queue)

    def publish(self) -> None:
        """非阻塞唤醒所有处于等待中的快照订阅者。"""
        for queue in self._subscribers:
            if not queue.full():
                queue.put_nowait(None)

    def set_phase(self, phase: ResourceRunPhase, label: str) -> None:
        """更新当前执行阶段并通知订阅者。"""
        self.state.status = "running"
        self.state.phase = phase
        self.state.phase_label = label
        self.publish()

    def on_text(self, delta: str) -> None:
        """流式追加主 Agent 规划思考文本。"""
        self.state.thought_text += delta
        self.publish()

    def on_tool_start(self, call: ToolCall) -> None:
        """子智能体工具调用开始钩子。"""
        tool_name = call.name
        title_map = {
            "generate_lecture_content": "核心概念讲义编写",
            "generate_mindmap": "思维导图与知识架构绘制",
            "generate_quiz": "随堂测验与实践试题编制",
            "generate_code": "工程代码案例研发",
            "generate_reading": "文献材料与学术资料策展",
            "generate_ppt_deck": "演示课件视觉设计制作",
            "generate_teaching_video": "教学动画与分镜视频生成",
        }
        step_title = title_map.get(tool_name, f"执行 {tool_name}")
        step = ResourceStep(
            id=call.id,
            tool_name=tool_name,
            title=step_title,
            status="running",
            progress=10,
            message="正在初始化子智能体任务...",
            elapsed_ms=0,
        )
        self._current_steps[call.id] = step
        self.state.steps.append(step)
        self.state.phase = "generating"
        self.state.phase_label = f"子智能体正在推进: {step_title}"
        self.publish()

    async def on_subagent_progress(self, tool_name: str, message: str, progress: int = 50) -> None:
        """子智能体内部进度推进通知（如 PPT 逐页渲染或动画音频合成）。"""
        for step in self._current_steps.values():
            if step.tool_name == tool_name and step.status == "running":
                step.message = message
                step.progress = max(step.progress, progress)
                break
        self.publish()

    def on_tool_end(self, call: ToolCall, raw: Any, output_text: str) -> None:
        """子智能体工具调用完成钩子。"""
        step = self._current_steps.get(call.id)
        if step is not None:
            step.status = "completed"
            step.progress = 100
            step.message = "子智能体产物已交付"

        artifact = _extract_resource_artifact(call.id, call.name, raw)
        if artifact is not None:
            # 去重或追加产物
            self.state.artifacts = [
                a for a in self.state.artifacts if a.kind != artifact.kind
            ]
            self.state.artifacts.append(artifact)
            logger.info("已捕获教学资源产物: kind=%s title=%s", artifact.kind, artifact.title)

        self.publish()

    def on_tool_failed(self, call: ToolCall, error: str) -> None:
        """子智能体执行失败钩子。"""
        step = self._current_steps.get(call.id)
        if step is not None:
            step.status = "failed"
            step.message = f"执行失败: {error}"
        self.publish()

    def result_state(self, status: TerminalStatus, error: str = "") -> ResourceRunState:
        """设置终态并生成最终交付快照。"""
        self.state.status = status
        self.state.phase = "completed" if status == "completed" else "failed"
        self.state.phase_label = "资源制作完成" if status == "completed" else "生成失败"
        self.state.error = error
        self.state.total_elapsed_ms = int((time.monotonic() - self.started_at) * 1000)
        return self.snapshot()
