"""Chat Agent 核心运行时 —— 基于 learn-claude-code s01/s02/s04 的直白单循环与实时透明状态流。"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import json
import time
from typing import Any
from uuid import uuid4

from sqlmodel import func, select

from app.chat.context import build_turn_messages
from app.chat.memory import estimate_token_count, extract_content_text, now_utc, run_post_turn_memory_jobs
from app.chat.schemas import (
    DiagramMode,
    RunArtifact,
    RunEvent,
    RunEventName,
    RunPhase,
    RunState,
    RunStatus,
    RunStep,
    SourceItem,
    SubStep,
    TERMINAL_STATUSES,
)
from app.chat.tools import build_tutor_tools, describe_tool_call
from app.infra.database import session_scope
from app.infra.llm import (
    AIMessage,
    LLM,
    TextDelta,
    ToolCall,
    ToolMessage,
    TurnDone,
)
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatRun as ChatRunRow, ChatSession
from app.shared.tools import ToolRegistry

logger = get_logger(__name__)

_MAX_PREVIEW_CHARS = 800


class RunCancelled(Exception):
    """当用户主动请求停止生成时，在循环检查点抛出的协作式取消异常。"""


def _truncate(value: Any, limit: int = _MAX_PREVIEW_CHARS) -> str:
    """将任意文本截断到可读预览长度。"""
    text = str(value or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _format_args_preview(args: Mapping[str, Any]) -> str:
    """将工具调用参数格式化为紧凑可读的 JSON 预览字符串。"""
    if not args:
        return ""
    try:
        return _truncate(json.dumps(dict(args), ensure_ascii=False, indent=2, default=str), 600)
    except Exception:
        return _truncate(str(args), 600)


def _as_tool_text(raw: Any) -> str:
    """将工具任意返回值提取为回灌给 LLM 的纯文本。"""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, Mapping):
        for key in ("text", "message", "content"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                return val
        return json.dumps(dict(raw), ensure_ascii=False, default=str)
    return str(raw)


# ===========================================================================
# 1. RunStream —— 单次运行的实时状态机、内存广播与数据库检查点持久化
# ===========================================================================

_active_streams: dict[str, "RunStream"] = {}


class RunStream:
    """管理单次 Agent 运行的完整实时状态，负责向在线 SSE 队列广播并同步写回 ChatRun 表。"""

    def __init__(self, run_id: str) -> None:
        """初始化运行流状态机与订阅者集合。"""
        self.run_id = run_id
        self.started_at = time.monotonic()
        self.cancelled = False
        self.state = RunState(
            run_id=run_id,
            sequence=0,
            status="queued",
            phase="queued",
            phase_label="等待处理",
        )
        self._subscribers: set[asyncio.Queue[RunEvent]] = set()
        self._lock = asyncio.Lock()

    def elapsed_ms(self) -> int:
        """计算自运行启动以来的毫秒耗时。"""
        return max(0, int((time.monotonic() - self.started_at) * 1000))

    async def subscribe(self) -> tuple[asyncio.Queue[RunEvent], RunEvent]:
        """注册一个新的 SSE 监听队列，并立即生成包含当前完整状态的 run.snapshot 事件。"""
        queue: asyncio.Queue[RunEvent] = asyncio.Queue(maxsize=512)
        async with self._lock:
            self._subscribers.add(queue)
            self.state.total_elapsed_ms = self.elapsed_ms()
            snapshot = RunEvent(
                run_id=self.run_id,
                sequence=self.state.sequence,
                event="run.snapshot",
                data=self.state.model_dump(),
            )
        return queue, snapshot

    async def unsubscribe(self, queue: asyncio.Queue[RunEvent]) -> None:
        """移除已断开的 SSE 监听队列。"""
        async with self._lock:
            self._subscribers.discard(queue)

    async def _broadcast(self, event: RunEventName, data: dict[str, Any]) -> RunEvent:
        """递增序号并向所有在线订阅队列广播事件。"""
        async with self._lock:
            self.state.sequence += 1
            self.state.total_elapsed_ms = self.elapsed_ms()
            ev = RunEvent(
                run_id=self.run_id,
                sequence=self.state.sequence,
                event=event,
                data=data,
            )
            queues = list(self._subscribers)
        for q in queues:
            try:
                q.put_nowait(ev)
            except asyncio.QueueFull:
                logger.warning("[RunStream] 队列已满，丢弃事件: run_id=%s event=%s", self.run_id, event)
        return ev

    async def set_phase(
        self,
        phase: RunPhase,
        phase_label: str,
        *,
        status: RunStatus = "running",
        persist: bool = False,
    ) -> None:
        """切换 Agent 当前顶层工作阶段并广播 phase.changed 事件。"""
        self.state.status = status
        self.state.phase = phase
        self.state.phase_label = phase_label
        await self._broadcast(
            "phase.changed",
            {"phase": phase, "phase_label": phase_label, "status": status},
        )
        if persist:
            await self.persist_checkpoint()

    async def upsert_step(self, step: RunStep, *, persist: bool = False) -> None:
        """插入或原地更新一条执行步骤，并广播 step.upsert 事件。"""
        idx = next((i for i, s in enumerate(self.state.steps) if s.step_id == step.step_id), -1)
        if idx >= 0:
            self.state.steps[idx] = step
        else:
            self.state.steps.append(step)
        await self._broadcast("step.upsert", step.model_dump())
        if persist:
            await self.persist_checkpoint()

    async def append_sub_step(
        self,
        parent_step_id: str,
        title: str,
        progress: int | None = None,
    ) -> None:
        """向正在运行的子智能体步骤追加一条内部实时子步骤，并将前序子步骤标记为完成。"""
        target = next((s for s in self.state.steps if s.step_id == parent_step_id), None)
        if target is None:
            return
        for prev in target.sub_steps:
            if prev.status == "running":
                prev.status = "completed"
        if not target.sub_steps or target.sub_steps[-1].title != title:
            target.sub_steps.append(
                SubStep(
                    id=f"{parent_step_id}:sub:{len(target.sub_steps) + 1}",
                    title=title,
                    status="running",
                )
            )
        if progress is not None:
            target.progress = max(target.progress or 0, min(99, progress))
        target.elapsed_ms = max(0, int((time.time() - target.started_at) * 1000))
        self.state.phase_label = f"{target.title} · {title}"
        await self._broadcast(
            "phase.changed",
            {
                "phase": self.state.phase,
                "phase_label": self.state.phase_label,
                "status": self.state.status,
            },
        )
        await self._broadcast("step.upsert", target.model_dump())

    async def append_text_delta(self, delta: str) -> None:
        """追加流式回答文本片段并广播 text.delta 事件。"""
        if not delta:
            return
        self.state.content += delta
        await self._broadcast("text.delta", {"delta": delta})

    async def add_artifact(self, artifact: RunArtifact) -> None:
        """记录产出的可下载产物（PPT/视频）并广播 artifact.created 事件。"""
        kept = [a for a in self.state.artifacts if a.id != artifact.id]
        self.state.artifacts = [*kept, artifact]
        await self._broadcast("artifact.created", artifact.model_dump())

    async def finish(
        self,
        status: RunStatus,
        *,
        phase_label: str,
        error: str = "",
    ) -> None:
        """收敛所有未结束步骤的状态，持久化最终快照并广播 run.finished 终态事件。"""
        now_ts = time.time()
        for step in self.state.steps:
            if step.status == "running":
                step.status = "completed" if status == "completed" else ("cancelled" if status == "cancelled" else "failed")
                step.elapsed_ms = max(step.elapsed_ms, int((now_ts - step.started_at) * 1000))
            for sub in step.sub_steps:
                if sub.status == "running":
                    sub.status = "completed" if status == "completed" else "failed"

        self.state.status = status
        self.state.phase = status  # type: ignore[assignment]
        self.state.phase_label = phase_label
        self.state.error = error
        self.state.total_elapsed_ms = self.elapsed_ms()

        await self.persist_checkpoint(finished=True)
        await self._broadcast(
            "run.finished",
            {
                "status": self.state.status,
                "phase": self.state.phase,
                "phase_label": self.state.phase_label,
                "content": self.state.content,
                "error": self.state.error,
                "total_elapsed_ms": self.state.total_elapsed_ms,
                "steps": [s.model_dump() for s in self.state.steps],
                "artifacts": [a.model_dump() for a in self.state.artifacts],
                "sources": [s.model_dump() for s in self.state.sources],
            },
        )

    async def persist_checkpoint(self, *, finished: bool = False) -> None:
        """将当前内存中的 RunState 刷写到数据库 chat_runs 行。"""
        try:
            async with session_scope() as db:
                row = await db.get(ChatRunRow, self.run_id)
                if row is None:
                    return
                row.status = self.state.status
                row.phase = self.state.phase
                row.phase_label = self.state.phase_label[:200]
                row.content = self.state.content
                row.error = self.state.error
                row.total_elapsed_ms = self.state.total_elapsed_ms
                row.steps = [s.model_dump() for s in self.state.steps]
                row.artifacts = [a.model_dump() for a in self.state.artifacts]
                row.sources = [s.model_dump() for s in self.state.sources]
                if finished:
                    row.finished_at = now_utc()
                db.add(row)
        except Exception as exc:
            logger.warning("[RunStream] 持久化运行快照失败: run_id=%s err=%s", self.run_id, exc)


# ===========================================================================
# 2. 运行状态查询、预订与中断管理
# ===========================================================================


def get_active_stream(run_id: str) -> RunStream | None:
    """获取当前进程内正在活跃执行的 RunStream。"""
    return _active_streams.get(run_id)


def request_cancel_run(run_id: str) -> bool:
    """向活跃运行发送取消信号，使其在下一个流式/工具检查点退出。"""
    stream = _active_streams.get(run_id)
    if stream is None:
        return False
    stream.cancelled = True
    return True


async def reserve_run(
    *,
    run_id: str,
    user_id: int,
    session_id: str,
    user_message_id: int,
) -> RunStream:
    """在数据库登记 queued 状态的运行行并创建内存 RunStream，确保前端拿到 run_id 即可订阅。"""
    stream = RunStream(run_id)
    _active_streams[run_id] = stream
    async with session_scope() as db:
        db.add(
            ChatRunRow(
                id=run_id,
                session_id=session_id,
                user_id=user_id,
                user_message_id=user_message_id,
                status="queued",
                phase="queued",
                phase_label="等待处理",
            )
        )
    return stream


def row_to_run_state(row: ChatRunRow) -> RunState:
    """将数据库 ChatRun 行反序列化为前端所需的 RunState 快照。"""
    active = _active_streams.get(row.id)
    if active is not None:
        active.state.total_elapsed_ms = active.elapsed_ms()
        return active.state.model_copy(deep=True)

    raw_steps = row.steps if isinstance(row.steps, list) else []
    raw_artifacts = row.artifacts if isinstance(row.artifacts, list) else []
    raw_sources = row.sources if isinstance(row.sources, list) else []
    return RunState(
        run_id=row.id,
        sequence=len(raw_steps) + 1,
        status=row.status,  # type: ignore[arg-type]
        phase=(row.phase or row.status),  # type: ignore[arg-type]
        phase_label=row.phase_label or ("已完成" if row.status == "completed" else row.status),
        content=row.content or "",
        error=row.error or "",
        total_elapsed_ms=int(row.total_elapsed_ms or 0),
        steps=[RunStep(**item) for item in raw_steps if isinstance(item, dict)],
        artifacts=[RunArtifact(**item) for item in raw_artifacts if isinstance(item, dict)],
        sources=[SourceItem(**item) for item in raw_sources if isinstance(item, dict)],
    )


async def load_run_state(run_id: str) -> RunState | None:
    """优先从活跃内存流、其次从数据库读取指定运行的最新 RunState。"""
    active = _active_streams.get(run_id)
    if active is not None:
        active.state.total_elapsed_ms = active.elapsed_ms()
        return active.state.model_copy(deep=True)
    async with session_scope() as db:
        row = await db.get(ChatRunRow, run_id)
        if row is None:
            return None
        return row_to_run_state(row)


async def has_active_run(user_id: int, session_id: str) -> bool:
    """检查同一会话是否有尚未结束的运行，防止并发重入。"""
    async with session_scope() as db:
        result = await db.execute(
            select(func.count())
            .select_from(ChatRunRow)
            .where(
                ChatRunRow.user_id == user_id,
                ChatRunRow.session_id == session_id,
                ChatRunRow.status.in_(["queued", "running"]),
            )
        )
        return int(result.scalar_one() or 0) > 0


async def mark_interrupted_runs() -> int:
    """服务启动时将上次进程遗留的 queued/running 运行标记为 interrupted。"""
    async with session_scope() as db:
        result = await db.execute(
            select(ChatRunRow).where(ChatRunRow.status.in_(["queued", "running"]))
        )
        runs = list(result.scalars().all())
        for run in runs:
            run.status = "interrupted"
            run.phase = "interrupted"
            run.phase_label = "服务重启，运行已中断"
            run.error = "服务重启，运行已中断"
            db.add(run)
        return len(runs)


# ===========================================================================
# 3. 消息持久化辅助与产物提取
# ===========================================================================


async def _save_model_message(
    *,
    user_id: int,
    session_id: str,
    run_id: str,
    role: str,
    text: str = "",
    tool_calls: list[dict[str, Any]] | None = None,
    tool_call_id: str | None = None,
) -> None:
    """将模型产生的 assistant 或 tool 消息写入 chat_messages 并更新会话 token 计数。"""
    try:
        content = [{"type": "text", "text": text}] if text else []
        async with session_scope() as db:
            chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
            if chat_session is None:
                return
            msg = ChatMessage(
                session_id=session_id,
                run_id=run_id,
                role=role,
                content=content,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id,
            )
            db.add(msg)
            tokens = estimate_token_count(extract_content_text(content))
            chat_session.summary_token_count = int(chat_session.summary_token_count or 0) + tokens
            chat_session.ltm_token_count = int(chat_session.ltm_token_count or 0) + tokens
            chat_session.ltm_message_count = int(chat_session.ltm_message_count or 0) + 1
            chat_session.updated_at = now_utc()
            db.add(chat_session)
    except Exception as exc:
        logger.warning("[ChatAgent] 保存消息失败: run_id=%s role=%s err=%s", run_id, role, exc)


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
    """从知识库检索工具的返回字典中提取结构化引用来源列表。"""
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


# ===========================================================================
# 4. 核心 Agent 单循环 (learn-claude-code s01 + s02 + s04)
# ===========================================================================


async def run_tutor_agent(
    *,
    run_id: str,
    user_id: int,
    username: str,
    session_id: str,
    user_message_id: int,
    question: str,
    attachments: list[str] | None = None,
    diagram_mode: DiagramMode = "auto",
    video_mode: bool = False,
    max_steps: int = 8,
    max_tool_rounds: int = 6,
    timeout_s: float = 1800.0,
) -> RunState:
    """驱动一次完整的 Tutor Agent 循环：准备上下文 → 多轮思考与工具调用 → 流式输出回答 → 触发记忆管线。"""
    stream = _active_streams.get(run_id)
    if stream is None:
        stream = RunStream(run_id)
        _active_streams[run_id] = stream

    # 记录当前活跃的子智能体 step_id，以便把内部进度精准挂载到对应步骤下
    active_subagent_steps: dict[str, str] = {}

    async def _on_subagent_progress(tool_name: str, message: str, pct: int) -> None:
        """接收 PPT/教学视频子智能体的内部进度并实时广播给前端。"""
        step_id = active_subagent_steps.get(tool_name)
        if step_id:
            await stream.append_sub_step(step_id, message, progress=pct)

    try:
        async with asyncio.timeout(timeout_s):
            # ── 阶段 1：准备上下文与工具箱 ──────────────────────────────
            await stream.set_phase("preparing", "正在装载会话上下文与学习档案...", status="running", persist=True)
            messages = await build_turn_messages(
                user_id=user_id,
                session_id=session_id,
                user_message_id=user_message_id,
                question=question,
                attachments=list(attachments or []),
                diagram_mode=diagram_mode,
                video_mode=video_mode,
            )
            tools = build_tutor_tools(
                user_id=user_id,
                username=username,
                session_id=session_id,
                on_subagent_progress=_on_subagent_progress,
            )
            registry = ToolRegistry(tools=tools)
            tool_schemas = registry.openai_schemas()
            llm = LLM(provider="text", temperature=0.7, max_tokens=8192)
            tool_rounds = 0

            # ── 阶段 2：ReAct 核心循环 (s01: One loop is all you need) ──
            for step_idx in range(1, max_steps + 1):
                if stream.cancelled:
                    raise RunCancelled("用户停止生成")

                think_id = f"think:{step_idx}"
                think_title = "理解问题与规划方案" if step_idx == 1 else f"第 {step_idx} 轮深入分析与规划"
                think_sub = "分析提问意图，决定是否需要检索知识库、查阅档案或解析附件" if step_idx == 1 else "结合上一步工具返回结果，规划下一步行动"
                think_step = RunStep(
                    step_id=think_id,
                    kind="thinking",
                    title=think_title,
                    subtitle=think_sub,
                    status="running",
                )
                await stream.set_phase("thinking", f"正在{think_title}...", status="running")
                await stream.upsert_step(think_step)

                # 若上一轮流式输出过过渡文字而后又调了工具，新一轮重置正文缓冲
                if step_idx > 1 and stream.state.content:
                    stream.state.content = ""

                force_final = tool_rounds >= max_tool_rounds
                done: TurnDone | None = None
                streaming_started = False

                async for item in llm.stream(
                    messages,
                    tools=None if force_final else tool_schemas,
                    tool_choice="none" if force_final else None,
                ):
                    if stream.cancelled:
                        raise RunCancelled("用户停止生成")
                    if isinstance(item, TextDelta) and item.text:
                        if not streaming_started:
                            streaming_started = True
                            think_step.status = "completed"
                            think_step.elapsed_ms = max(1, int((time.time() - think_step.started_at) * 1000))
                            think_step.subtitle = "已完成思考，开始输出回答"
                            await stream.upsert_step(think_step)
                            await stream.set_phase("streaming", "正在生成回答...", status="running")
                        await stream.append_text_delta(item.text)
                    elif isinstance(item, TurnDone):
                        done = item

                if done is None:
                    raise RuntimeError("模型流式输出异常中断")

                # 完成思考步骤计时
                if think_step.status == "running":
                    think_step.status = "completed"
                    think_step.elapsed_ms = max(1, int((time.time() - think_step.started_at) * 1000))
                    if done.tool_calls:
                        names = "、".join(describe_tool_call(tc.name, tc.args or {})[1] for tc in done.tool_calls)
                        think_step.subtitle = f"决定执行：{names}"
                    await stream.upsert_step(think_step)

                # 若模型未请求工具调用，说明最终回答已生成完毕，退出循环
                if not done.tool_calls:
                    answer = (done.text or stream.state.content).strip()
                    if answer:
                        await _save_model_message(
                            user_id=user_id,
                            session_id=session_id,
                            run_id=run_id,
                            role="assistant",
                            text=answer,
                        )
                    await stream.finish("completed", phase_label="回答完成")
                    asyncio.create_task(
                        run_post_turn_memory_jobs(
                            user_id=user_id,
                            session_id=session_id,
                            user_message=question,
                            assistant_reply=answer or "内容已生成",
                        )
                    )
                    return stream.state

                # ── 阶段 3：并行执行本轮工具调用 (s02 & s04) ──────────────
                normalized_calls = [
                    (
                        tc.id or f"call-{uuid4().hex[:10]}",
                        ToolCall(
                            id=tc.id or f"call-{uuid4().hex[:10]}",
                            name=tc.name,
                            args=dict(tc.args or {}),
                            raw_arguments=tc.raw_arguments,
                        ),
                    )
                    for tc in done.tool_calls
                ]
                messages.append(AIMessage(done.text or "", tool_calls=[c for _, c in normalized_calls]))
                await _save_model_message(
                    user_id=user_id,
                    session_id=session_id,
                    run_id=run_id,
                    role="assistant",
                    text=done.text or "",
                    tool_calls=[
                        {"id": cid, "name": c.name, "args": dict(c.args or {})}
                        for cid, c in normalized_calls
                    ],
                )

                tool_steps: dict[str, RunStep] = {}
                for cid, call in normalized_calls:
                    kind, title, subtitle = describe_tool_call(call.name, call.args)
                    step_obj = RunStep(
                        step_id=f"tool:{cid}",
                        kind=kind,
                        title=title,
                        subtitle=subtitle,
                        status="running",
                        tool_name=call.name,
                        input_preview=_format_args_preview(call.args),
                        progress=5 if kind == "subagent" else None,
                    )
                    tool_steps[cid] = step_obj
                    if kind == "subagent":
                        active_subagent_steps[call.name] = step_obj.step_id
                    await stream.upsert_step(step_obj)

                first_title = next(iter(tool_steps.values())).title
                phase_msg = (
                    f"正在{first_title}..."
                    if len(tool_steps) == 1
                    else f"正在并行执行 {len(tool_steps)} 项工具 ({first_title} 等)..."
                )
                await stream.set_phase("tool_calling", phase_msg, status="running", persist=True)

                async def _exec_one(call_id: str, call: ToolCall) -> tuple[str, ToolCall, str, str, Any]:
                    """执行单个工具并返回 (call_id, call, text, status, raw)。"""
                    if stream.cancelled:
                        raise RunCancelled("用户停止生成")
                    try:
                        raw = await registry.execute(call.name, dict(call.args or {}))
                        status = "failed" if isinstance(raw, dict) and raw.get("status") == "failed" else "ok"
                        return call_id, call, _as_tool_text(raw), status, raw
                    except Exception as exc:
                        logger.warning("[ChatAgent] 工具 %s 执行失败: %s", call.name, exc)
                        return call_id, call, f"工具执行失败: {exc}", "failed", None

                results = await asyncio.gather(*(_exec_one(cid, c) for cid, c in normalized_calls))

                for cid, call, text_out, status_str, raw_out in results:
                    active_subagent_steps.pop(call.name, None)
                    step_obj = tool_steps[cid]
                    step_obj.status = "failed" if status_str == "failed" else "completed"
                    step_obj.elapsed_ms = max(1, int((time.time() - step_obj.started_at) * 1000))
                    step_obj.output_preview = _truncate(text_out)
                    if status_str == "failed":
                        step_obj.error = _truncate(text_out, 300)
                    else:
                        if step_obj.kind == "subagent":
                            step_obj.progress = 100
                        for sub in step_obj.sub_steps:
                            if sub.status == "running":
                                sub.status = "completed"

                    if status_str == "ok":
                        new_sources = _extract_sources(raw_out)
                        if new_sources:
                            stream.state.sources.extend(new_sources)
                        artifact = _extract_artifact(cid, call.name, raw_out)
                        if artifact is not None:
                            await stream.add_artifact(artifact)

                    await stream.upsert_step(step_obj)
                    await _save_model_message(
                        user_id=user_id,
                        session_id=session_id,
                        run_id=run_id,
                        role="tool",
                        text=text_out,
                        tool_call_id=cid,
                    )
                    messages.append(
                        ToolMessage(
                            text_out or f"[{call.name} 执行完毕]",
                            tool_call_id=cid,
                        )
                    )

                await stream.persist_checkpoint()
                tool_rounds += 1

            raise RuntimeError(f"超过最大推理步数 ({max_steps})")

    except RunCancelled:
        logger.info("[ChatAgent] 运行已取消: run_id=%s", run_id)
        await stream.finish("cancelled", phase_label="已停止生成", error="用户停止生成")
        return stream.state
    except TimeoutError:
        msg = f"运行超时 (>{int(timeout_s)}s)"
        logger.warning("[ChatAgent] %s: run_id=%s", msg, run_id)
        await stream.finish("failed", phase_label="运行超时", error=msg)
        return stream.state
    except Exception as exc:
        logger.exception("[ChatAgent] 运行异常: run_id=%s", run_id)
        await stream.finish("failed", phase_label="运行失败", error=str(exc))
        return stream.state
    finally:
        _active_streams.pop(run_id, None)


__all__ = [
    "RunCancelled",
    "RunStream",
    "TERMINAL_STATUSES",
    "get_active_stream",
    "has_active_run",
    "load_run_state",
    "mark_interrupted_runs",
    "request_cancel_run",
    "reserve_run",
    "row_to_run_state",
    "run_tutor_agent",
]
