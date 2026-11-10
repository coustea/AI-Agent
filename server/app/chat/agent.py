"""无跨轮状态的模型与工具循环；运行环境由调用方准备，观察钩子由外部注入。"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from app.infra.llm import AIMessage, LLM, Message, TextDelta, ToolCall, ToolMessage, TurnDone
from app.infra.logging import get_logger
from app.shared.tools import (
    ToolRegistry,
    format_tool_output,
    summarize_tool_args,
    summarize_tool_result,
)

if TYPE_CHECKING:
    from app.chat.hooks import RunHooks

logger = get_logger(__name__)


@dataclass(slots=True)
class AgentResult:
    """保存最终回答和本轮新增的模型、工具消息。"""

    answer: str
    new_messages: list[Message]


async def run_tutor_agent(
    *,
    messages: list[Message],
    llm: LLM,
    registry: ToolRegistry,
    hooks: RunHooks,
    max_steps: int = 8,
    max_tool_rounds: int = 6,
) -> AgentResult:
    """执行标准 learn-claude-code 循环：请求模型 -> 执行工具 -> 追加消息，返回最终结果与新增消息链。"""
    messages = list(messages)
    new_messages: list[Message] = []
    tool_schemas = registry.openai_schemas()
    logger.info(
        "[ChatAgent] 启动辅导循环: 历史={} 条 工具={} 个 max_steps={}",
        len(messages), len(tool_schemas), max_steps,
    )

    for round_index in range(max_steps):
        hooks.on_model_start(round_index + 1)
        done: TurnDone | None = None
        round_text = ""
        force_final = round_index >= max_tool_rounds

        async for item in llm.stream(
            messages,
            tools=None if force_final else tool_schemas,
            tool_choice="none" if force_final else None,
        ):
            if isinstance(item, TextDelta) and item.text:
                round_text += item.text
                hooks.on_text(item.text)
            elif isinstance(item, TurnDone):
                done = item

        if done is None:
            logger.error("[ChatAgent] 第 {}/{} 轮模型流式输出异常中断", round_index + 1, max_steps)
            raise RuntimeError("模型流式输出异常中断")

        calls = [
            ToolCall(
                id=call.id or f"call-{uuid4().hex[:10]}",
                name=call.name,
                args=dict(call.args or {}),
                raw_arguments=call.raw_arguments,
            )
            for call in done.tool_calls
        ]
        answer = (done.text or round_text).strip()
        if not calls and not answer:
            logger.error("[ChatAgent] 第 {}/{} 轮模型未生成任何回答", round_index + 1, max_steps)
            raise RuntimeError("模型未生成回答")

        ai_msg = AIMessage(answer, tool_calls=calls)
        messages.append(ai_msg)
        new_messages.append(ai_msg)
        hooks.on_model_end(ai_msg)
        logger.info(
            "[ChatAgent] 第 {}/{} 轮完成: tool_calls={} answer_len={}",
            round_index + 1, max_steps, len(calls), len(answer),
        )
        if answer:
            thought_preview = answer.strip().replace("\n", " ")
            if len(thought_preview) > 120:
                thought_preview = f"{thought_preview[:117]}..."
            logger.info("[ChatAgent] 导师回复/规划: {}", thought_preview)

        if not calls:
            logger.info("[ChatAgent] 辅导循环正常结束: 总轮数={} 回答长度={}", round_index + 1, len(answer))
            return AgentResult(answer=answer, new_messages=new_messages)

        logger.info("[ChatAgent] 第 {}/{} 轮发起 {} 个工具调用:", round_index + 1, max_steps, len(calls))
        for idx, call in enumerate(calls, 1):
            args_summary = summarize_tool_args(call.name, call.args)
            logger.info(
                "[ChatAgent]   -> [{}/{}] 调用工具: {} | 参数: {}",
                idx, len(calls), call.name, args_summary,
            )
            hooks.on_tool_start(call)
            start_t = time.perf_counter()
            try:
                raw = await registry.execute(call.name, dict(call.args or {}))
                output_text = format_tool_output(raw)
                cost_ms = round((time.perf_counter() - start_t) * 1000)
                res_summary = summarize_tool_result(call.name, raw)
                logger.info(
                    "[ChatAgent]   <- [{}/{}] 工具执行完成: {} (耗时 {}ms) | 结果: {}",
                    idx, len(calls), call.name, cost_ms, res_summary,
                )
                hooks.on_tool_end(call, raw, output_text)
            except Exception as exc:
                cost_ms = round((time.perf_counter() - start_t) * 1000)
                logger.warning(
                    "[ChatAgent]   ❌ [{}/{}] 工具执行失败: {} (耗时 {}ms) | 错误: {}",
                    idx, len(calls), call.name, cost_ms, exc,
                )
                raw = {"status": "failed", "text": f"工具执行失败: {exc}"}
                output_text = format_tool_output(raw)
                hooks.on_tool_end(call, raw, output_text)

            tool_msg = ToolMessage(output_text, tool_call_id=call.id)
            messages.append(tool_msg)
            new_messages.append(tool_msg)

    logger.error("[ChatAgent] 超过最大推理步数 ({})", max_steps)
    raise RuntimeError(f"超过最大推理步数 ({max_steps})")
