"""Harness 钩子实现 — 循环之外的全部职责都落在这里。

每个钩子只做一件事，且都通过 ``ChatRunEvents`` 对外发声：

    prepare()       附件分析 + 上下文构建（循环开始前调用一次）
    run_started     发 run.started，把运行置为 running
    step_started    首轮发 turn.started，之后发思考活动
    text_delta      增量文本转 text.delta
    turn_finished   发 text.completed
    tools_started   整批 tool_calls 落一条 assistant 消息 + 逐个 running 活动
    tool_finished   单条 tool 消息落库 + 活动终态 + 产物/来源收集
    run_finished    最终回答落库 + run.completed + 后台记忆任务
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlmodel import select

from app.chat.attachment import analyze_attachments
from app.chat.harness.events import ChatActivity, ChatRunEvents, RunArtifact
from app.chat.harness.hooks import HookBus
from app.chat.harness.loop import ToolResult
from app.chat.memory.service import get_chat_memory_service, run_background_memory_jobs
from app.evaluation.guidance import get_effective_guidance_strategy
from app.infra.database import session_scope
from app.infra.llm import HumanMessage, Message, SystemMessage, ToolCall, load_prompt
from app.infra.logging import get_logger
from app.infra.models import ChatRun, UserProfile

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "tutor_agent.md"
_MAX_ACTIVITY_OUTPUT = 800


@dataclass(slots=True)
class RunContext:
    """一次运行的不可变输入与可变的收集器。"""

    run_id: str
    user_id: int
    username: str
    session_id: str
    user_message_id: int
    question: str
    attachments: list[str] = field(default_factory=list)
    diagram_mode: str = "auto"
    video_mode: bool = False
    session_summary: str = ""
    history: list[Message] = field(default_factory=list)
    attachment_context: str = ""
    # 运行期收集
    sources: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    tool_invocations: list[dict[str, Any]] = field(default_factory=list)


class ChatRunHandlers:
    """把运行上下文翻译成事件、消息与数据库写入。"""

    def __init__(self, ctx: RunContext, events: ChatRunEvents) -> None:
        """绑定运行上下文与事件发布器。"""
        self.ctx = ctx
        self.events = events
        self.memory = get_chat_memory_service()

    def bind(self, bus: HookBus) -> None:
        """把全部钩子注册到总线。"""
        bus.on("run_started", self.on_run_started)
        bus.on("step_started", self.on_step_started)
        bus.on("text_delta", self.on_text_delta)
        bus.on("turn_finished", self.on_turn_finished)
        bus.on("tools_started", self.on_tools_started)
        bus.on("tool_finished", self.on_tool_finished)
        bus.on("run_finished", self.on_run_finished)

    # ------------------------------------------------------------------
    # 循环开始前的准备（附件分析必须在构建上下文之前完成）
    # ------------------------------------------------------------------

    async def prepare(self) -> list[Message]:
        """分析附件、组装本轮消息链，返回交给循环的初始消息。"""
        if self.ctx.attachments:
            attachment = await analyze_attachments(
                attachments=self.ctx.attachments,
                user_id=self.ctx.user_id,
                username=self.ctx.username,
                session_id=self.ctx.session_id,
                run_id=self.ctx.run_id,
                memory_service=self.memory,
                emit=self._emit_attachment_activity,
            )
            self.ctx.attachment_context = attachment.text
            self.ctx.errors.extend(attachment.errors)
        return await self.build_messages()

    async def _emit_attachment_activity(self, payload: dict[str, Any]) -> None:
        """把附件分析进度转成 activity.updated 事件。"""
        await self.events.emit("activity.updated", payload)

    async def build_messages(self) -> list[Message]:
        """构建完整消息链（System + 历史 + 本轮 User）。"""
        dynamic = await self._build_dynamic_context()
        human = self.ctx.question
        if dynamic:
            human = f"{human}\n\n{dynamic}"
        return [
            SystemMessage(load_prompt(_PROMPT_PATH)),
            *self.ctx.history,
            HumanMessage(human),
        ]

    async def _build_dynamic_context(self) -> str:
        """把每轮变化的上下文聚合成一段附在 user 消息末尾的文本。"""
        blocks: list[str] = [f"[当前日期]\n{datetime.now().date().isoformat()}"]
        if self.ctx.session_summary:
            blocks.append(f"[会话摘要]\n{self.ctx.session_summary}")
        if self.ctx.attachments:
            blocks.append(
                f"[附件信息]\n学生上传了附件共 {len(self.ctx.attachments)} 个。\n"
                f"{self.ctx.attachment_context or '若包含图片，必须调用 view_image 工具读取图片内容再回答。'}"
            )
        if self.ctx.video_mode:
            blocks.append(
                "[本轮必须生成视频]\n"
                "学生已在前端勾选视频，本轮必须调用 generate_teaching_video 工具产出一个教学视频。\n"
                "视频生成成功后，用 2-3 句话简要说明视频讲了什么，不要再长篇复述内容。"
            )
        elif self.ctx.diagram_mode == "required":
            blocks.append(
                "[本轮必须生成图解]\n"
                "学生已在前端勾选图解，本轮回答必须包含一个 ```mermaid 代码块。\n"
                "图解放在回答开头或紧接结论之后，正文用 2-4 句话简要说明关键点，不要长篇展开。"
            )
        async with session_scope() as db:
            strategy = await get_effective_guidance_strategy(db, self.ctx.user_id)
        if strategy:
            blocks.append(
                "[辅导策略]\n"
                f"本期结论: {strategy.get('conclusion')}\n"
                f"推荐单次时长: {strategy.get('recommended_session_minutes')} 分钟\n"
                f"辅导风格: {strategy.get('tutoring_style')}\n"
                f"重点关注主题: {'、'.join(strategy.get('focus_topics', [])) or '无'}\n"
                f"策略依据: {strategy.get('reason')}"
            )
        agent_md = await self._load_agent_md()
        if agent_md:
            blocks.append(f"[我的学习档案]\n{agent_md}")
        return "\n\n".join(blocks)

    async def _load_agent_md(self) -> str:
        """读取用户 AGENT.md 学习档案；缺失或异常时返回空串。"""
        try:
            async with session_scope() as db:
                result = await db.execute(
                    select(UserProfile.agent_md).where(UserProfile.user_id == self.ctx.user_id)
                )
                return (result.scalar_one_or_none() or "").strip()
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # 循环内钩子
    # ------------------------------------------------------------------

    async def on_run_started(self) -> None:
        """标记运行开始。"""
        async with session_scope() as db:
            run = await db.get(ChatRun, self.ctx.run_id)
            if run is not None:
                run.status = "running"
                db.add(run)
                await db.commit()
        await self.events.emit("run.started", {})

    async def on_step_started(self, step: int) -> None:
        """首轮发 turn.started，之后每轮推送一条思考活动。"""
        if step == 1:
            await self.events.emit("turn.started", {})
            return
        await self.events.emit(
            "activity.updated",
            ChatActivity(
                activity_id="thinking",
                kind="agent",
                title=f"第 {step} 轮推理",
                status="running",
                detail={"input": "正在分析上一步结果并规划下一步"},
            ).model_dump(),
        )

    async def on_text_delta(self, text: str) -> None:
        """把模型增量文本转成 text.delta。"""
        await self.events.emit("text.delta", {"delta": text})

    async def on_turn_finished(self, text: str) -> None:
        """模型不再请求工具，发布最终文本。"""
        await self.events.emit("text.completed", {"content": text})

    async def on_tools_started(self, calls: list[tuple[str, ToolCall]]) -> None:
        """整批 tool_calls 落一条 assistant 消息，并为每个调用发 running 活动。"""
        await self._save_tool_request(calls)
        for call_id, call in calls:
            await self.events.emit(
                "activity.updated",
                ChatActivity(
                    activity_id=f"tool:{call_id}",
                    kind="tool",
                    title=f"调用 {call.name}",
                    status="running",
                    detail={"input": _preview_args(call.args)},
                ).model_dump(),
            )

    async def on_tool_finished(self, result: ToolResult) -> None:
        """落库单条 tool 消息、发布活动终态，并收集来源与产物。"""
        status = "failed" if result.status == "failed" else "completed"
        if result.status == "ok" and isinstance(result.raw, dict):
            self.ctx.sources.extend(result.raw.get("sources") or [])
        await self._save_tool_response(result)
        self.ctx.tool_invocations.append(
            {
                "tool_call_id": result.call_id,
                "tool_name": result.name,
                "payload": result.args,
                "status": result.status,
            }
        )
        await self.events.emit(
            "activity.updated",
            ChatActivity(
                activity_id=f"tool:{result.call_id}",
                kind="tool",
                title=f"调用 {result.name}",
                status=status,
                detail={
                    "input": _preview_args(result.args),
                    "output": _truncate(result.text),
                    "error": result.text if result.status == "failed" else "",
                },
            ).model_dump(),
        )
        await self._collect_artifact(result)

    async def on_run_finished(self, answer: str) -> None:
        """最终回答落库、发布 run.completed，并触发后台记忆任务。"""
        await self._save_assistant(answer)
        await self.events.emit(
            "run.completed",
            {
                "content": answer,
                "sources": self.ctx.sources,
                "artifacts": self.ctx.artifacts,
                "errors": self.ctx.errors,
            },
        )
        await run_background_memory_jobs(
            self.memory,
            user_id=self.ctx.user_id,
            session_id=self.ctx.session_id,
            user_message=self.ctx.question,
            assistant_reply=answer or "内容已生成并保存",
        )

    # ------------------------------------------------------------------
    # 数据库写入
    # ------------------------------------------------------------------

    async def _save_tool_request(self, calls: list[tuple[str, ToolCall]]) -> None:
        """把本轮全部 tool_calls 合并为一条 assistant 消息。"""
        try:
            await self.memory.save_message(
                user_id=self.ctx.user_id,
                session_id=self.ctx.session_id,
                run_id=self.ctx.run_id,
                role="assistant",
                content=[],
                tool_calls=[
                    {"id": call_id, "name": call.name, "args": dict(call.args or {})}
                    for call_id, call in calls
                ],
            )
        except Exception as exc:
            logger.warning("[ChatRun] 保存工具请求消息失败: %s", exc)

    async def _save_tool_response(self, result: ToolResult) -> None:
        """把单次工具结果落库为一条 tool 消息。"""
        try:
            await self.memory.save_message(
                user_id=self.ctx.user_id,
                session_id=self.ctx.session_id,
                run_id=self.ctx.run_id,
                role="tool",
                content=[{"type": "text", "text": result.text}],
                tool_call_id=result.call_id,
            )
        except Exception as exc:
            logger.warning("[ChatRun] 保存工具响应消息失败: %s", exc)

    async def _save_assistant(self, answer: str) -> None:
        """把最终回答落库为一条 assistant 消息。"""
        if not answer.strip():
            return
        try:
            await self.memory.save_message(
                user_id=self.ctx.user_id,
                session_id=self.ctx.session_id,
                run_id=self.ctx.run_id,
                role="assistant",
                content=[{"type": "text", "text": answer}],
            )
        except Exception as exc:
            logger.warning("[ChatRun] 保存助手回复失败: %s", exc)

    async def _collect_artifact(self, result: ToolResult) -> None:
        """从工具结果里提取可下载产物并发布 artifact.created。"""
        payload = result.raw if isinstance(result.raw, dict) else None
        if not payload:
            return
        url = payload.get("video_url") or payload.get("pptx_url") or payload.get("file_url")
        if not isinstance(url, str) or not url:
            return
        kind = "video" if payload.get("video_url") else "ppt"
        artifact = RunArtifact(
            id=f"{kind}:{result.call_id}",
            kind=kind,
            title=str(payload.get("title") or result.name),
            url=url,
            preview_url=payload.get("preview_url"),
            metadata={k: v for k, v in payload.items() if isinstance(v, (str, int, float, bool))},
        )
        self.ctx.artifacts.append(artifact.model_dump())
        await self.events.emit("artifact.created", artifact.model_dump())


def _preview_args(args: dict[str, Any]) -> str:
    """把工具参数压成一行摘要。"""
    try:
        return _truncate(json.dumps(args, ensure_ascii=False, default=str))
    except Exception:
        return ""


def _truncate(text: str, limit: int = _MAX_ACTIVITY_OUTPUT) -> str:
    """截断过长文本，保留可读前缀。"""
    value = str(text or "")
    return value if len(value) <= limit else value[:limit] + "..."


__all__ = ["ChatRunHandlers", "RunContext"]
