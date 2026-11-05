"""CartoonAgent — 基于无状态流 + HyperFrames + TTS 的教学视频生成智能体。

工作流（全流程基于 output_dir 文件系统流转，无内存 state 闭包）：
1. 导演主智能体 (CartoonAgent) 按需加载 ``hyperframes`` skill，规划 3-5 个连贯场景的分镜蓝图。
2. 调用 ``init_storyboard_and_tts`` 为每个场景合成 TTS 旁白音频，测量毫秒级时长并落盘 ``STORYBOARD.json``、``captions.vtt``、``index.html`` 与 ``compositions/sXX.html`` 骨架。
3. 调用共享无状态 ``subagent(prompts=[...])`` 工具并行派生子智能体，每个子智能体在全新 ``messages=[]`` 上下文中编写 ``compositions/sXX.html`` 视觉与镜头动效，并调用 ``verify_scene`` 验证契约。
4. 调用 ``check_and_render_video`` 执行 HyperFrames 契约审计、渲染 1080p MP4 视频并运行 ffprobe 音视频流确定性校验，落盘 ``audit.json``。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.infra.llm import get_llm_client
from app.infra.logging import get_logger
from app.shared.cartoon.renderer import CartoonMedia
from app.shared.cartoon.schemas import (
    CartoonArtifact,
    CartoonBrief,
    CartoonGenerationError,
    VideoDesignPlan,
)
from app.shared.cartoon.tool import build_cartoon_planner_tools
from app.shared.tools import ToolRegistry, get_skill_loader

logger = get_logger(__name__)


class CartoonAgent:
    """无状态流 HyperFrames 教学视频生产智能体。"""

    def __init__(self, *, media: CartoonMedia | None = None) -> None:
        self._media = media or CartoonMedia()

    async def generate(self, brief: CartoonBrief, output_dir: Path) -> CartoonArtifact:
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "compositions").mkdir(parents=True, exist_ok=True)

        self._media.install_runtime(output_dir)

        skill_loader = get_skill_loader()
        skill_catalog = skill_loader.describe_skills(only=["hyperframes", "hyperframes-cli"])
        prompt_context = self._format_brief_context(brief)

        planner_tools = build_cartoon_planner_tools(
            output_dir=output_dir,
            skill_loader=skill_loader,
            brief=brief,
            media=self._media,
        )

        system_prompt = (
            "你是 HyperFrames 教学视频总导演智能体 (CartoonAgent)，采用无状态子智能体架构制作 1920x1080 动画讲解视频。\n\n"
            "可用技能 (Skills):\n"
            f"{skill_catalog}\n\n"
            "必须严格遵循以下执行流程：\n"
            "1. 调用 `load_skill(name='hyperframes', reference='format.md')` 了解 HyperFrames 组合契约。\n"
            "2. 调用 `init_storyboard_and_tts` 规划 3~5 个教学场景，合成每个场景的真实 TTS 音频并获取精确时长，从 `skills/hyperframes/templates/` 复制生成 `index.html` 与 `compositions/sXX.html` 骨架。\n"
            "   - 相邻两个场景的 `visual_style` 不得重复（在 `concept_hero`、`architecture_flow`、`code_walkthrough`、`comparison_split`、`summary_recap` 间轮换）。\n"
            "   - 每个场景的 `narration` 必须是自然流畅、适合口播讲解的中文句子（2~3 句，约 45~90 字）。\n"
            "3. 调用 `subagent(prompts=[...])`（每个场景一条包含 scene_id、duration_sec、visual_style、title、visual_cards 的子任务提示词），并行让无状态子智能体为每个 `compositions/sXX.html` 编写针对性的 SVG/HTML 视觉布局与镜头动效并通过 `verify_scene` 校验。\n"
            "4. 调用 `check_and_render_video` 渲染并验证最终 `video.mp4`。"
        )

        storyboard_file = output_dir / "STORYBOARD.json"
        audit_file = output_dir / "audit.json"
        video_file = output_dir / "video.mp4"

        async def _verify_producer_done() -> str | None:
            if not storyboard_file.is_file():
                return "You have not called `init_storyboard_and_tts` yet."
            if not audit_file.is_file() or not video_file.is_file():
                check_tool = next(t for t in planner_tools if t.name == "check_and_render_video")
                out = await check_tool.handler()  # type: ignore[misc]
                if not audit_file.is_file() or not video_file.is_file():
                    return str(out)
            audit_data = json.loads(audit_file.read_text(encoding="utf-8"))
            if not audit_data.get("ok"):
                return f"HyperFrames audit not passed: {audit_data}"
            return None

        client, spec = get_llm_client("text")
        registry = ToolRegistry(planner_tools)
        tool_schemas = registry.get_tools_description()

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_context},
        ]

        try:
            async with asyncio.timeout(600.0):
                for _ in range(1, 13):
                    response = await client.chat.completions.create(
                        model=spec.model_name,
                        messages=messages,
                        temperature=0.12,
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
                        gate_error = await _verify_producer_done()
                        if gate_error:
                            messages.append({
                                "role": "user",
                                "content": f"[Quality Gate Failed]\n{gate_error}\n请立即调用工具修复。",
                            })
                            continue
                        break

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
        except TimeoutError:
            raise CartoonGenerationError("动画视频总制作超时 (>600s)", stage="storyboard", problems=["超限超时"])
        except Exception as exc:
            if isinstance(exc, CartoonGenerationError):
                raise
            raise CartoonGenerationError(f"动画视频制作异常: {exc}", stage="storyboard", problems=[str(exc)]) from exc

        if not storyboard_file.is_file():
            raise CartoonGenerationError("动画主规划循环未完成分镜与语音规划", stage="storyboard", problems=["未完成分镜规划"])

        if not audit_file.is_file() or not video_file.is_file():
            check_tool = next(t for t in planner_tools if t.name == "check_and_render_video")
            render_msg = await check_tool.handler()  # type: ignore[misc]
            if not audit_file.is_file() or not video_file.is_file():
                raise CartoonGenerationError(
                    f"HyperFrames 渲染或质量门失败: {render_msg}",
                    stage="render",
                    problems=[str(render_msg)],
                )

        plan_obj = VideoDesignPlan.model_validate_json(storyboard_file.read_text(encoding="utf-8"))
        return CartoonArtifact(
            title=plan_obj.title,
            duration_ms=plan_obj.total_duration_ms,
            scene_count=len(plan_obj.scenes),
            output_dir=output_dir,
            html_path=output_dir / "index.html",
            video_path=video_file,
            caption_path=output_dir / "captions.vtt",
            lesson_path=output_dir / "lesson.json",
            timeline_path=output_dir / "timeline.json",
            audit_path=audit_file,
        )

    @staticmethod
    def _format_brief_context(brief: CartoonBrief) -> str:
        materials = "\n\n".join(brief.source_materials[:6]) or "请围绕主题深入讲解核心概念、运行机制与总结要点。"
        kp = "、".join(brief.knowledge_points[:12]) or "核心原理与流程"
        return (
            f"【HyperFrames 动画教学视频任务】\n"
            f"- 教学主题: {brief.learning_need}\n"
            f"- 核心知识点: {kp}\n"
            f"- 深度配置: depth={brief.configuration.lesson_depth.value}, pace={brief.configuration.pace}\n\n"
            f"【源教学素材】\n{materials[:10_000]}"
        )


__all__ = ["CartoonAgent"]
