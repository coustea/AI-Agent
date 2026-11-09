"""Resource 模块工具集合 (app.resource.tools)。

将课件制作 (PPT) 与概念动画 (Cartoon) 统一包装为标准的 Tool 规范，
供 SubAgent 在执行多模态任务节点时直接调用。
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from app.resource.schemas import AgentResult
from app.shared.cartoon.tool import build_cartoon_tool
from app.shared.ppt.tool import build_ppt_tool
from app.shared.tools.registry import Tool

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int], Awaitable[None]]


def build_resource_toolbox(
    *,
    username: str = "anonymous",
    resource_id: str = "default",
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Tool]:
    """构建供 SubAgent 执行调用的多模态资源生成工具字典。"""
    ppt_tool = build_ppt_tool(
        username=username,
        session_id=resource_id,
        progress=progress_callback,
    )
    cartoon_tool = build_cartoon_tool(
        username=username,
        resource_id=resource_id,
        progress=progress_callback,
    )
    return {
        ppt_tool.name: ppt_tool,
        cartoon_tool.name: cartoon_tool,
        # 兼容简写别名
        "generate_ppt_deck": ppt_tool,
        "generate_teaching_video": cartoon_tool,
        "ppt": ppt_tool,
        "cartoon": cartoon_tool,
    }


async def execute_tool_for_task(
    tool_name: str,
    args: dict[str, Any],
    toolbox: dict[str, Tool],
) -> AgentResult:
    """根据任务声明分派执行指定的工具，并将结果封装为标准化 AgentResult。"""
    tool = toolbox.get(tool_name)
    if tool is None:
        return AgentResult(
            success=False,
            title="工具执行失败",
            file_type="json",
            error=f"未找到指定的工具: {tool_name}",
        )

    try:
        raw_result = await tool.handler(**args)
        if not isinstance(raw_result, dict):
            raw_result = {"status": "ok", "result": raw_result}

        # 判断是 PPT 还是 Cartoon
        if tool.name == "generate_ppt_deck" or tool_name in ("generate_ppt_deck", "ppt"):
            title = str(raw_result.get("title") or args.get("topic") or "教学课件")
            slide_count = raw_result.get("slide_count", 0)
            return AgentResult(
                success=True,
                title=title,
                file_type="pptx",
                summary=f"已成功生成 {slide_count} 页交互式演示课件",
                metrics={"slide_count": slide_count},
                metadata=raw_result,
            )
        elif tool.name == "generate_teaching_video" or tool_name in ("generate_teaching_video", "cartoon"):
            title = str(raw_result.get("title") or args.get("topic") or "教学动画视频")
            duration = raw_result.get("duration", 0)
            return AgentResult(
                success=True,
                title=title,
                file_type="mp4",
                summary=f"已成功生成教学动画视频 (时长约 {duration} 秒)",
                metrics={"duration": duration},
                metadata=raw_result,
            )
        else:
            return AgentResult(
                success=True,
                title=str(raw_result.get("title") or tool_name),
                file_type="json",
                content=raw_result,
                metadata=raw_result,
            )
    except Exception as exc:
        logger.exception("工具 %s 执行异常: %s", tool_name, exc)
        return AgentResult(
            success=False,
            title=f"{tool_name} 执行失败",
            file_type="json",
            error=str(exc),
            metadata={"tool_name": tool_name},
        )
