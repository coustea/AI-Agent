"""TutorAgent —— 通用学习答疑智能体（内置 ReAct 循环、Prompt 构建与工具调用持久化）。"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
import re
import time
from typing import Any, AsyncIterator
from uuid import uuid4

from sqlmodel import select

from app.chat.attachment import analyze_attachments
from app.chat.schemas import TutorInput, normalize_tool_result
from app.chat.stream import build_workflow_activity_payload
from app.chat.tools import build_tutor_tools
from app.evaluation.guidance import get_effective_guidance_strategy
from app.infra.database import session_scope
from app.infra.llm import (
    AIMessage,
    HumanMessage,
    LLM,
    Message,
    SystemMessage,
    TextDelta,
    ToolCall,
    ToolMessage,
    TurnDone,
)
from app.infra.logging import get_logger
from app.infra.models import UserProfile
from app.infra.prompts import prompts
from app.shared.tools import ToolRegistry

logger = get_logger(__name__)

DomainEvent = dict[str, Any]

VOICE_DIAGRAM_MAX_CHARS = 96
_IMAGE_UNSUPPORTED_REPLY = (
    "抱歉，当前模型暂不支持直接读取图片。请将图片中的关键内容以文字描述发送，我会尽力帮助你。"
)

_VOICE_ORAL_PROMPT = """

## 数字人口语回答模式
当前回答将由数字人直接播报。请优先使用简短、自然、可直接朗读的口语：
- 闲聊、问候或简单事实问题，默认用 1—3 句回答，不列清单。
- 一般讲解先给核心结论，整体尽量控制在 120 个中文字以内。
- 只有用户明确要求详细讲解、分步骤、代码或完整方案时，才扩展长度。
- 涉及定义、性质、公式、复杂度和算法步骤时必须保证事实准确。
- 只输出一个连续自然段，不使用 Markdown 标题、表格或项目列表。
- 避免冗长开场白。
"""

_LLM_IMAGE_UNSUPPORTED_RE = re.compile(
    r'ERROR:\s*Cannot read ".+?".*?does not support image input.*?Inform the user\.?',
    re.IGNORECASE | re.DOTALL,
)

_TOOL_LABELS: dict[str, str] = {
    "get_learner_profile": "读取学习者画像",
    "get_long_term_memory": "检索长期记忆",
    "search_knowledge": "检索课程知识库",
    "generate_ppt_deck": "生成教学课件 (PPTX)",
    "generate_teaching_video": "制作动画讲解视频",
}


def strip_llm_image_error(text: str) -> tuple[str, bool]:
    """检测并剥离『模型不支持图片』的错误文本。"""
    if _LLM_IMAGE_UNSUPPORTED_RE.search(text):
        return _LLM_IMAGE_UNSUPPORTED_RE.sub("", text).strip(), True
    return text, False


def condense_voice_answer(text: str, max_chars: int = VOICE_DIAGRAM_MAX_CHARS) -> str:
    """语音场景下截断长回答，避免朗读冗长。"""
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip("，。；、 ") + "。"


async def _load_agent_md(user_id: int) -> str:
    """读取用户 AGENT.md 学习档案；缺失或异常时返回空串。"""
    try:
        async with session_scope() as db:
            result = await db.execute(
                select(UserProfile.agent_md).where(UserProfile.user_id == user_id)
            )
            return (result.scalar_one_or_none() or "").strip()
    except Exception:
        return ""


async def build_system_prompt(ctx: TutorInput) -> str:
    """构建静态 System Prompt（保护 Prompt Caching 前缀）。"""
    prompt = prompts.get("chat").render("tutor_agent")
    if ctx.voice_mode:
        prompt += _VOICE_ORAL_PROMPT
    return prompt


async def build_dynamic_context(ctx: TutorInput) -> str:
    """把每轮变化的内容聚合成一段动态上下文，附在 user 消息末尾。"""
    blocks: list[str] = [f"[当前日期]\n{datetime.now().date().isoformat()}"]

    if ctx.session_summary:
        blocks.append(f"[会话摘要]\n{ctx.session_summary}")

    if ctx.attachments:
        blocks.append(
            f"[附件信息]\n附件 {len(ctx.attachments)} 个\n"
            f"{ctx.attachment_context or '暂无预分析内容。'}"
        )

    if ctx.video_mode:
        blocks.append(
            "[本轮必须生成视频]\n"
            "学生已在前端勾选视频，本轮必须调用 generate_teaching_video 工具产出一个教学视频。\n"
            "视频生成成功后，用 2-3 句话简要说明视频讲了什么，不要再长篇复述内容。"
        )
    elif ctx.diagram_mode == "required":
        blocks.append(
            "[本轮必须生成图解]\n"
            "学生已在前端勾选图解，本轮回答必须包含一个 ```mermaid 代码块。\n"
            "图解放在回答开头或紧接结论之后，正文用 2-4 句话简要说明关键点，不要长篇展开。"
        )

    async with session_scope() as db:
        strategy = await get_effective_guidance_strategy(db, ctx.user_id)
    if strategy:
        blocks.append(
            "[辅导策略]\n"
            f"本期结论: {strategy.get('conclusion')}\n"
            f"推荐单次时长: {strategy.get('recommended_session_minutes')} 分钟\n"
            f"辅导风格: {strategy.get('tutoring_style')}\n"
            f"重点关注主题: {'、'.join(strategy.get('focus_topics', [])) or '无'}\n"
            f"策略依据: {strategy.get('reason')}"
        )

    agent_md = await _load_agent_md(ctx.user_id)
    if agent_md:
        blocks.append(f"[我的学习档案]\n{agent_md}")

    return "\n\n".join(blocks)


async def build_messages(ctx: TutorInput) -> list[Message]:
    """构建完整的本轮消息列表（System + 历史 + 本轮 User）。"""
    system_prompt = await build_system_prompt(ctx)
    human_content = ctx.question
    dynamic = await build_dynamic_context(ctx)
    if dynamic:
        human_content = f"{human_content}\n\n{dynamic}"
    return [SystemMessage(system_prompt), *ctx.history_messages, HumanMessage(human_content)]


def _build_tool_activity_payload(
    *,
    tool_call_id: str,
    tool_name: str,
    status: str,
    args: dict[str, Any],
    output: str = "",
    error: str = "",
) -> dict[str, Any]:
    title = _TOOL_LABELS.get(tool_name, f"调用工具 {tool_name}")
    if status == "running":
        msg = f"正在执行：{title}..."
    elif status == "failed":
        msg = f"{title}执行失败：{error[:120]}"
    else:
        msg = f"{title}已完成"
    return {
        "activity_id": f"tool:{tool_call_id}",
        "kind": "tool",
        "stage": tool_name,
        "status": status,
        "tool_name": tool_name,
        "title": title,
        "summary": str(args.get("topic") or args.get("query") or args.get("reason") or "")[:100],
        "message": msg,
        "detail": {
            "args": args,
            "output": output[:500] if output else "",
            "error": error[:200] if error else "",
        },
    }


class TutorAgent:
    """通用学习答疑智能体 —— 直接驱动流式 ReAct 循环与工具执行。"""

    def __init__(
        self,
        memory_service: Any | None = None,
        *,
        max_steps: int = 8,
        max_tool_rounds: int = 6,
        total_timeout_s: float = 300.0,
    ) -> None:
        from app.chat.memory.service import get_chat_memory_service

        self.memory_service = memory_service or get_chat_memory_service()
        self.max_steps = max_steps
        self.max_tool_rounds = max_tool_rounds
        self.total_timeout_s = total_timeout_s

    async def chat(self, input: TutorInput) -> AsyncIterator[DomainEvent]:
        """执行一次辅导对话，逐事件产出领域事件（供 ChatService 转发为 SSE）。"""
        started = time.time()
        tool_invocations: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        errors: list[str] = []
        video_payload: dict[str, Any] | None = None

        logger.info(
            "[TutorAgent] 开始: user_id=%s session_id=%s question_len=%d history=%d voice=%s",
            input.user_id,
            input.session_id,
            len(input.question),
            len(input.history_messages),
            input.voice_mode,
        )

        yield {"event": "message_start", "data": {}}

        # ── 1. 附件预处理 ──
        if input.attachments:
            queue: list[DomainEvent] = []

            async def emit(payload: DomainEvent) -> None:
                queue.append(payload)

            attachment = await analyze_attachments(
                attachments=input.attachments,
                user_id=input.user_id,
                username=input.username,
                session_id=input.session_id,
                user_message_id=input.user_message_id,
                memory_service=self.memory_service,
                emit=emit,
            )
            for event in queue:
                yield event
            input.attachment_context = attachment.text
            errors.extend(attachment.errors)

        # ── 2. 构建消息上下文与工具注册表 ──
        messages = await build_messages(input)
        tools = build_tutor_tools(input)
        tool_registry = ToolRegistry(tools=tools) if tools else None
        tool_schemas = tool_registry.get_tools_description() if tool_registry else None

        llm = LLM(provider="text", temperature=0.7, max_tokens=8192)
        tool_round = 0
        final_answer = ""

        # ── 3. 直接运行流式 ReAct Agent Loop ──
        try:
            async with asyncio.timeout(self.total_timeout_s):
                for step in range(1, self.max_steps + 1):
                    await self._save_activity(
                        input,
                        build_workflow_activity_payload(
                            stage="thinking",
                            activity_id=f"thinking-iteration-{step}",
                            title="分析思考过程",
                            message=f"第 {step} 次推理：正在分析问题并规划回答策略...",
                            status="running",
                        ),
                    )

                    force_final = tool_round >= self.max_tool_rounds
                    text_parts: list[str] = []
                    done: TurnDone | None = None

                    async for item in llm.stream(
                        messages,
                        tools=None if force_final else tool_schemas,
                        tool_choice="none" if force_final else None,
                    ):
                        if isinstance(item, TextDelta):
                            text_parts.append(item.text)
                            yield {"event": "token", "data": item.text}
                        elif isinstance(item, TurnDone):
                            done = item

                    if done is None:
                        raise RuntimeError("模型流式输出异常中断（未收到 TurnDone）")

                    turn_text = done.text if done.text else "".join(text_parts)
                    tool_calls = done.tool_calls or ()

                    # ── 无工具调用：生成最终回答并结束循环 ──
                    if not tool_calls:
                        answer, has_image_error = strip_llm_image_error(turn_text)
                        if has_image_error:
                            answer = _IMAGE_UNSUPPORTED_REPLY
                        if input.voice_mode:
                            answer = condense_voice_answer(answer)

                        await self._save_activity(
                            input,
                            build_workflow_activity_payload(
                                stage="thinking",
                                activity_id=f"thinking-iteration-{step}",
                                title="思考完成",
                                message=f"第 {step} 次推理完成，开始生成回答",
                                status="done",
                            ),
                        )
                        final_answer = answer
                        break

                    # ── 有工具调用：推送开始活动 -> 并行执行工具 -> 推送结束活动并回灌上下文 ──
                    messages.append(AIMessage(turn_text, tool_calls=tool_calls))
                    for call in tool_calls:
                        tc_id = call.id or f"call-{uuid4().hex}"
                        running_act = _build_tool_activity_payload(
                            tool_call_id=tc_id,
                            tool_name=call.name,
                            status="running",
                            args=dict(call.args or {}),
                        )
                        await self._save_activity(input, running_act)
                        yield {"event": "agent_status", "data": running_act}

                    step_results = await asyncio.gather(
                        *(
                            self._execute_tool_call(call, input, tool_registry)
                            for call in tool_calls
                        )
                    )
                    for inv, call_sources, call_error in step_results:
                        tool_invocations.append(inv)
                        sources.extend(call_sources)
                        if call_error:
                            errors.append(call_error)
                        raw_res = inv.get("result_payload")
                        if (
                            inv.get("tool_name") == "generate_teaching_video"
                            and isinstance(raw_res, dict)
                            and raw_res.get("video_url")
                        ):
                            video_payload = raw_res

                        done_act = _build_tool_activity_payload(
                            tool_call_id=inv["tool_call_id"],
                            tool_name=inv["tool_name"],
                            status="failed" if inv["status"] == "failed" else "done",
                            args=inv["payload"],
                            output=inv["result_text"],
                            error=call_error or "",
                        )
                        await self._save_activity(input, done_act)
                        yield {"event": "agent_status", "data": done_act}

                        messages.append(
                            ToolMessage(
                                inv["result_text"] or f"[{inv['tool_name']} 无输出]",
                                tool_call_id=inv["tool_call_id"],
                            )
                        )
                    tool_round += 1
                else:
                    raise RuntimeError(f"Agent [tutor] 超过最大推理步数 ({self.max_steps})")

        except TimeoutError:
            err_msg = f"Agent [tutor] 运行超时 (>{self.total_timeout_s}s)"
            logger.warning("[TutorAgent] %s", err_msg)
            yield {"event": "error", "data": err_msg}
            return
        except Exception as exc:
            logger.exception("[TutorAgent] 运行失败")
            yield {"event": "error", "data": str(exc)}
            return

        logger.info(
            "[TutorAgent] 完成: user_id=%s session_id=%s answer_len=%d tools=%d elapsed=%.2fs",
            input.user_id,
            input.session_id,
            len(final_answer),
            len(tool_invocations),
            time.time() - started,
        )

        yield {
            "event": "status",
            "data": {"stage": "answer_done", "message": "回答已生成，正在保存..."},
        }
        yield {
            "event": "done",
            "data": {
                "final_answer": final_answer,
                "sources": sources,
                "tool_invocations": tool_invocations,
                "video": video_payload,
                "errors": errors,
            },
        }

    async def _execute_tool_call(
        self,
        call: ToolCall,
        ctx: TutorInput,
        tool_registry: ToolRegistry | None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], str | None]:
        """执行单个工具调用，持久化 assistant/tool 消息并提取结果与来源。"""
        tool_call_id = call.id or f"call-{uuid4().hex}"
        args = dict(call.args or {})
        assistant_message_id: int | None = None
        tool_message_id: int | None = None

        if self.memory_service:
            try:
                msg = await self.memory_service.save_message(
                    user_id=ctx.user_id,
                    session_id=ctx.session_id,
                    user_message_id=ctx.user_message_id,
                    role="assistant",
                    content=[],
                    tool_calls=[{"id": tool_call_id, "name": call.name, "args": args}],
                )
                assistant_message_id = getattr(msg, "id", None)
            except Exception as exc:
                logger.warning("[TutorAgent] 保存工具请求消息失败: %s", exc)

        call_sources: list[dict[str, Any]] = []
        call_error: str | None = None
        raw_result: Any = None

        try:
            if tool_registry is None:
                raise RuntimeError(f"工具不可用: {call.name}")
            raw_result = await tool_registry.execute(
                {"id": tool_call_id, "name": call.name, "args": args}
            )
            normalized = normalize_tool_result(raw_result)
            result_text = normalized.text
            if not result_text and raw_result is not None:
                result_text = json.dumps(raw_result, ensure_ascii=False, default=str)

            meta_status = normalized.metadata.get("status")
            if meta_status == "empty":
                status = "empty"
            elif meta_status == "unavailable":
                status = "failed"
            else:
                status = "ok" if result_text.strip() else "empty"

            if status == "ok":
                call_sources = [s.model_dump() for s in normalized.sources]
        except Exception as exc:
            logger.warning("[TutorAgent] 工具 %s 执行失败: %s", call.name, exc)
            status = "failed"
            call_error = f"{call.name}: {exc}"
            result_text = f"工具调用失败: {exc}"

        if self.memory_service:
            try:
                msg = await self.memory_service.save_message(
                    user_id=ctx.user_id,
                    session_id=ctx.session_id,
                    user_message_id=ctx.user_message_id,
                    role="tool",
                    content=[{"type": "text", "text": result_text}],
                    tool_call_id=tool_call_id,
                )
                tool_message_id = getattr(msg, "id", None)
            except Exception as exc:
                logger.warning("[TutorAgent] 保存工具结果消息失败: %s", exc)

        invocation = {
            "tool_call_id": tool_call_id,
            "tool_name": call.name,
            "payload": args,
            "result_payload": raw_result,
            "result_text": result_text,
            "status": status,
            "assistant_message_id": assistant_message_id,
            "tool_message_id": tool_message_id,
        }
        return invocation, call_sources, call_error

    async def _save_activity(self, ctx: TutorInput, payload: dict[str, Any]) -> None:
        if not self.memory_service:
            return
        try:
            await self.memory_service.upsert_activity(
                user_id=ctx.user_id,
                session_id=ctx.session_id,
                user_message_id=ctx.user_message_id,
                payload=payload,
            )
        except Exception as exc:
            logger.warning("[TutorAgent] 持久化活动失败: %s", exc)


__all__ = [
    "TutorAgent",
    "VOICE_DIAGRAM_MAX_CHARS",
    "build_dynamic_context",
    "build_messages",
    "build_system_prompt",
    "condense_voice_answer",
    "strip_llm_image_error",
]
