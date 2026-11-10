"""Resource 主规划与调度智能体循环 (app.resource.agent)。

完全复刻 chat.agent.run_tutor_agent 架构：
主 Agent 作为课程总监统筹全局，通过模型流式输出思考规划，调用子智能体工具逐一交付成果。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import uuid4

from app.infra.llm import AIMessage, LLM, Message, TextDelta, ToolCall, ToolMessage, TurnDone
from app.infra.logging import get_logger
from app.resource.hooks import ResourceRunHooks
from app.shared.tools import (
    ToolRegistry,
    format_tool_output,
    summarize_tool_args,
    summarize_tool_result,
)

logger = get_logger(__name__)


@dataclass(slots=True)
class ResourceAgentResult:
    """保存最终总结回答与本轮新增的对话/工具消息链。"""

    summary: str
    new_messages: list[Message]


async def run_resource_lead_agent(
    *,
    messages: list[Message],
    llm: LLM,
    registry: ToolRegistry,
    hooks: ResourceRunHooks,
    max_steps: int = 16,
    max_tool_rounds: int = 12,
) -> ResourceAgentResult:
    """执行标准教学资源主智能体循环：思考规划 -> 工具调用 -> 收集产物 -> 终态交付。"""
    messages = list(messages)
    new_messages: list[Message] = []
    tool_schemas = registry.openai_schemas()

    for round_index in range(max_steps):
        hooks.publish()
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
            raise RuntimeError("主规划智能体流式输出异常中断")

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
            raise RuntimeError("主规划智能体未生成任何有效规划或工具调用")

        ai_msg = AIMessage(answer, tool_calls=calls)
        messages.append(ai_msg)
        new_messages.append(ai_msg)

        if answer:
            thought_preview = answer.strip().replace("\n", " ")
            if len(thought_preview) > 120:
                thought_preview = f"{thought_preview[:117]}..."
            logger.info("[ResourceAgent] 主规划思考: {}", thought_preview)

        # 没有发起工具调用，说明规划与全部产物已交付完毕
        if not calls:
            logger.info("[ResourceAgent] 主规划智能体已完成全部教学资源调度与总结交付 (共 {} 步)", round_index + 1)
            return ResourceAgentResult(summary=answer, new_messages=new_messages)

        logger.info("[ResourceAgent] 第 {}/{} 轮调度 {} 个子智能体工具:", round_index + 1, max_steps, len(calls))

        # 逐一执行子智能体工具调用（严格限定仅允许调用已授权注册的工具）
        for idx, call in enumerate(calls, 1):
            args_summary = summarize_tool_args(call.name, call.args)
            logger.info(
                "[ResourceAgent]   -> [{}/{}] 调度子智能体: {} | 参数: {}",
                idx, len(calls), call.name, args_summary,
            )

            if call.name not in registry._tools:
                logger.warning(
                    "[ResourceAgent]   🚫 [{}/{}] 拦截未授权工具调用: {} (已授权工具: {})",
                    idx, len(calls), call.name, list(registry._tools.keys()),
                )
                denied_payload = {
                    "status": "forbidden",
                    "error": (
                        f"调用被拒绝：工具 '{call.name}' 未被学习者勾选授权。"
                        f"本次任务仅允许调用已授权的目标工具：{list(registry._tools.keys())}。"
                        "请严格按授权清单调度；若已全部生成完毕，请直接输出教学导学建议与总结完成交付。"
                    ),
                }
                output_text = format_tool_output(denied_payload)
                tool_msg = ToolMessage(output_text, tool_call_id=call.id)
                messages.append(tool_msg)
                new_messages.append(tool_msg)
                continue

            hooks.on_tool_start(call)
            start_t = time.perf_counter()
            try:
                raw = await registry.execute(call.name, dict(call.args or {}))
                output_text = format_tool_output(raw)
                cost_ms = round((time.perf_counter() - start_t) * 1000)
                res_summary = summarize_tool_result(call.name, raw)
                logger.info(
                    "[ResourceAgent]   <- [{}/{}] 子智能体交付完成: {} (耗时 {}ms) | 结果: {}",
                    idx, len(calls), call.name, cost_ms, res_summary,
                )
                hooks.on_tool_end(call, raw, output_text)
            except Exception as exc:
                cost_ms = round((time.perf_counter() - start_t) * 1000)
                logger.warning(
                    "[ResourceAgent]   ❌ [{}/{}] 子智能体执行失败: {} (耗时 {}ms) | 错误: {}",
                    idx, len(calls), call.name, cost_ms, exc,
                )
                raw = {"status": "failed", "error": str(exc)}
                output_text = format_tool_output(raw)
                hooks.on_tool_failed(call, str(exc))

            tool_msg = ToolMessage(output_text, tool_call_id=call.id)
            messages.append(tool_msg)
            new_messages.append(tool_msg)

    raise RuntimeError(f"超过最大执行轮次 ({max_steps})")
