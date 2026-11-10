"""无跨轮状态的模型与工具循环；运行环境由调用方准备，观察钩子由外部注入。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from app.infra.llm import AIMessage, LLM, Message, TextDelta, ToolCall, ToolMessage, TurnDone
from app.infra.logging import get_logger
from app.shared.tools import ToolRegistry, format_tool_output

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
        "[ChatAgent] 启动辅导循环: 历史=%d 条 工具=%d 个 max_steps=%d",
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
            logger.error("[ChatAgent] 第 %d/%d 轮模型流式输出异常中断", round_index + 1, max_steps)
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
            logger.error("[ChatAgent] 第 %d/%d 轮模型未生成任何回答", round_index + 1, max_steps)
            raise RuntimeError("模型未生成回答")

        ai_msg = AIMessage(answer, tool_calls=calls)
        messages.append(ai_msg)
        new_messages.append(ai_msg)
        hooks.on_model_end(ai_msg)
        logger.info(
            "[ChatAgent] 第 %d/%d 轮完成: tool_calls=%d answer_len=%d",
            round_index + 1, max_steps, len(calls), len(answer),
        )

        if not calls:
            logger.info("[ChatAgent] 辅导循环正常结束: 总轮数=%d 回答长度=%d", round_index + 1, len(answer))
            return AgentResult(answer=answer, new_messages=new_messages)

        for call in calls:
            hooks.on_tool_start(call)
            logger.info("[ChatAgent] 执行工具 %s: args=%s", call.name, call.raw_arguments or call.args)
            try:
                raw = await registry.execute(call.name, dict(call.args or {}))
            except Exception as exc:
                raw = {"status": "failed", "text": f"工具执行失败: {exc}"}
                logger.warning("[ChatAgent] 工具 %s 执行失败: %s", call.name, exc)
            output_text = format_tool_output(raw)
            logger.info("[ChatAgent] 工具 %s 完成 (输出 %d 字符)", call.name, len(output_text))
            hooks.on_tool_end(call, raw, output_text)

            tool_msg = ToolMessage(output_text, tool_call_id=call.id)
            messages.append(tool_msg)
            new_messages.append(tool_msg)

    logger.error("[ChatAgent] 超过最大推理步数 (%d)", max_steps)
    raise RuntimeError(f"超过最大推理步数 ({max_steps})")
