"""通用无状态子智能体工具 (app.shared.tools.subagent) —— 基于 learn-claude-code s04_subagent。

核心原则：
1. 无状态流 (Stateless Flow)：每次调用 ``run_subagent`` 均创建全新的 ``messages = [system, user]``，不共享父智能体上下文与内存状态。
2. 沙箱工作区交互：子智能体仅通过文件系统工具（``read``, ``write``, ``edit``）及注入的领域校验工具读写工作区，执行完毕后上下文直接销毁，仅向父智能体返回纯文本摘要。
3. 禁止递归派生：子智能体工具表中绝不挂载 ``subagent`` 自身。
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.infra.llm import get_llm_client
from app.infra.logging import get_logger
from app.shared.tools.builtin import build_builtin_tools
from app.shared.tools.registry import Tool, ToolRegistry

logger = get_logger(__name__)

DEFAULT_SUBAGENT_SYSTEM_PROMPT = (
    "You are a stateless execution subagent working inside a sandboxed workspace directory.\n"
    "Complete the assigned task using the provided file and verification tools, "
    "and reply with a concise summary of what you created or modified and the verification result."
)


class SubagentArgs(BaseModel):
    """派生无状态子智能体的参数。"""

    prompts: list[str] = Field(
        min_length=1,
        description=(
            "一个或多个独立的子任务提示词列表。列表中的每个子任务都会在全新、无状态的独立上下文中并行执行，"
            "无论是批量并行编写全部页面/分镜，还是单独重修某一个页面/分镜（传入单元素列表），均调用此工具。"
        ),
    )


async def run_subagent(
    prompt: str,
    *,
    workdir: Path,
    system_prompt: str = DEFAULT_SUBAGENT_SYSTEM_PROMPT,
    extra_tools: Sequence[Tool] = (),
    max_iterations: int = 8,
    timeout_s: float = 120.0,
) -> str:
    """在全新的 messages 上下文中运行单个无状态子智能体循环，仅返回最终摘要文本。"""
    base_tools = build_builtin_tools(
        workdir,
        include_bash=False,
        include_view_image=False,
        include_glob_grep=False,
    )
    # 过滤掉任何名为 subagent 的工具，防止子智能体递归派生
    safe_extra = [t for t in extra_tools if t.name != "subagent"]
    registry = ToolRegistry([*base_tools, *safe_extra])
    tool_schemas = registry.get_tools_description()

    client, spec = get_llm_client("text")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    try:
        async with asyncio.timeout(timeout_s):
            for _ in range(max_iterations):
                response = await client.chat.completions.create(
                    model=spec.model_name,
                    messages=messages,
                    temperature=0.1,
                    tools=tool_schemas,
                    tool_choice="auto",
                )
                msg = response.choices[0].message
                raw_tool_calls = msg.tool_calls or []

                assistant_dict: dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.content or "",
                }
                if raw_tool_calls:
                    assistant_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments or "{}",
                            },
                        }
                        for tc in raw_tool_calls
                    ]
                messages.append(assistant_dict)

                if not raw_tool_calls:
                    return (msg.content or "").strip() or "Subagent task completed."

                async def _exec_tc(tc: Any) -> dict[str, Any]:
                    output = await registry.execute_as_text(
                        tc.function.name,
                        tc.function.arguments or "{}",
                        call_id=tc.id,
                    )
                    return {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": output[:40_000],
                    }

                tool_msgs = await asyncio.gather(*(_exec_tc(tc) for tc in raw_tool_calls))
                messages.extend(tool_msgs)

        return (messages[-1].get("content") or "").strip() or "Subagent reached max iterations."
    except TimeoutError:
        logger.warning("[Subagent] 执行超时 (>%ss): prompt=%s", timeout_s, prompt[:120])
        return f"Error: Subagent timed out after {timeout_s}s."
    except Exception as exc:
        logger.warning("[Subagent] 执行异常: %s", exc)
        return f"Error: Subagent failed with {type(exc).__name__}: {exc}"


def build_subagent_tool(
    workdir: Path,
    *,
    system_prompt: str = DEFAULT_SUBAGENT_SYSTEM_PROMPT,
    extra_tools: Sequence[Tool] = (),
    name: str = "subagent",
    description: str | None = None,
    max_iterations: int = 8,
    timeout_s: float = 120.0,
    max_concurrency: int = 4,
) -> Tool:
    """构造绑定到指定工作区的通用无状态 ``subagent`` 工具。"""
    sem = asyncio.Semaphore(max_concurrency)

    async def _handler(prompts: list[str]) -> str:
        async def _worker(idx: int, task_prompt: str) -> str:
            async with sem:
                summary = await run_subagent(
                    task_prompt,
                    workdir=workdir,
                    system_prompt=system_prompt,
                    extra_tools=extra_tools,
                    max_iterations=max_iterations,
                    timeout_s=timeout_s,
                )
                return f"[Subagent #{idx}] {summary}"

        results = await asyncio.gather(
            *(_worker(i, p) for i, p in enumerate(prompts, start=1))
        )
        return "\n".join(results)

    return Tool(
        name=name,
        description=description
        or (
            "Spawn one or more stateless subagents with fresh isolated context (messages=[]) "
            "to author, edit, and verify files in the workspace in parallel. "
            "Pass multiple prompts to execute all tasks concurrently, or a single-item list to fix one specific item."
        ),
        args_model=SubagentArgs,
        handler=_handler,
    )


__all__ = [
    "DEFAULT_SUBAGENT_SYSTEM_PROMPT",
    "SubagentArgs",
    "build_subagent_tool",
    "run_subagent",
]
