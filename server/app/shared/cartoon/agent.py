"""基于工具循环的 HyperFrames 教学视频生产：创作、视觉修复与 CLI 渲染。"""
from __future__ import annotations

import asyncio
import json
import shlex
from collections.abc import Awaitable, Callable
from functools import partial
from pathlib import Path
from typing import Any, TypeVar
from uuid import uuid4

from app.infra.llm import get_llm_client
from app.shared.cartoon.schemas import (
    CartoonArtifact,
    CartoonGenerationConfig,
    CartoonGenerationError,
    CartoonInput,
)
from app.shared.cartoon.tts import build_speech_tool
from app.shared.tools.builtin import build_builtin_tools
from app.shared.tools.registry import ToolRegistry, format_tool_output
from app.shared.tools.skills import build_load_skill_tool

_T = TypeVar("_T")

_PROJECT = Path(__file__).resolve().parents[4]
_CLI = _PROJECT / "node_modules/.bin/hyperframes"

SKILLS = ("hyperframes", "hyperframes-cli", "hyperframes-registry", "media-use")

SYSTEM = f"""你是教学视频创作 agent。用文件工具创作，用 bash 执行 HyperFrames CLI，用 view_image 检查截图并修复。
工作目录为本次独立视频目录。已安装 CLI：{shlex.quote(str(_CLI))}；不要重新安装依赖。
GSAP 文件：{_PROJECT}/node_modules/gsap/dist/gsap.min.js，可复制到 assets/vendor/。
先 load_skill 读取 hyperframes 主技能，再按需读取格式、CLI、教学视频和媒体参考。
CLI 的 --help 是当前版本参数的依据。用本地 CLI 路径执行技能中的 hyperframes 命令。
自主完成整个视频，包括最终 MP4，不需要等用户批准预览或选择方案；不要发布到外部服务。
自由规划场景，写 PLAN.md 即可，不要求固定卡片模板或固定场景数。
使用 synthesize_speech 生成真实中文旁白，按返回时长编排动画与字幕，禁止用静音代替旁白。
用 CLI check 检查并修复错误；snapshot 截取各场景关键帧、复杂运动中间帧和转场。
调用 view_image 审查截图，问题包含文字遮挡、字幕冲突、画面空白、讲解内容和图示是否一致。
修复后重新截图检查，视觉修复最多两轮；失败必须如实处理。
通过 bash 调 CLI render --strict 生成 video.mp4，然后用 ffprobe 检查。任何源文件修改后重新渲染。
最终交付 index.html、video.mp4、captions.vtt，以及 result.json（title 字符串、scene_count 正整数）。
字幕必须是真实旁白内容的 WebVTT，同时在视频里可见。音频和媒体使用本地文件。
可用技能（按需用 load_skill 读取，不要在开始前假设其内容）：
- hyperframes：视频创作主流程与场景规范
- hyperframes-cli：CLI 命令、渲染与排错
- hyperframes-registry：现成视觉组件
- media-use：配音、音乐、图标等素材获取
"""


def _build_tools(workdir: Path, configuration: CartoonGenerationConfig) -> ToolRegistry:
    """装配动画视频 agent 的工具集：文件工具 + 4 个 HyperFrames 技能 + 中文旁白合成。"""
    return ToolRegistry([
        *build_builtin_tools(workdir, timeout_s=900),
        build_load_skill_tool(only=SKILLS),
        build_speech_tool(workdir, voice=configuration.voice, pace=configuration.pace),
    ])


async def _agent_loop(
    messages: list[dict[str, Any]],
    registry: ToolRegistry,
    *,
    system: str,
    deliver: Callable[[ToolRegistry], Awaitable[_T]] | None = None,
    required_tools: tuple[str, ...] = (),
    max_steps: int = 50,
    timeout_s: float = 1800.0,
    temperature: float = 0.2,
) -> _T:
    """驱动工具调用循环，直到交付校验通过或预算耗尽。"""
    client, spec = get_llm_client("text")
    tool_schemas = registry.openai_schemas()
    satisfied: set[str] = set()

    async with asyncio.timeout(timeout_s):
        for _ in range(max_steps):
            response = await client.chat.completions.create(
                model=spec.model_name, messages=messages, temperature=temperature,
                tools=tool_schemas, tool_choice="auto",
            )
            msg = response.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))

            if msg.tool_calls:
                for call in msg.tool_calls:
                    # 顺序执行，避免写文件、截图与渲染之间发生竞态。
                    try:
                        raw_res = await registry.execute(call.function.name, call.function.arguments)
                        result = format_tool_output(raw_res)
                    except Exception as exc:
                        result = f"Error: {exc}"
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
                    if not result.startswith(("[Error]", "Error")):
                        satisfied.add(call.function.name)
                continue

            if deliver is None:
                return msg.content  # type: ignore[return-value]

            missing = [name for name in required_tools if name not in satisfied]
            if missing:
                messages.append({
                    "role": "user",
                    "content": f"交付检查失败，请修复：尚未成功调用 {', '.join(missing)}",
                })
                continue
            try:
                return await deliver(registry)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                messages.append({"role": "user", "content": f"交付检查失败，请修复：{exc}"})

    raise CartoonGenerationError("视频制作达到最大工具轮数", stage="generate")


async def _collect_artifact(workdir: Path, registry: ToolRegistry) -> CartoonArtifact:
    """核验输出目录下的视频与字幕产物完整性并构建 CartoonArtifact。"""
    for name in ("index.html", "video.mp4", "captions.vtt", "result.json"):
        path = workdir / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"缺少非空产物：{name}")
    if not (workdir / "captions.vtt").read_text().lstrip().startswith("WEBVTT"):
        raise ValueError("captions.vtt 必须是 WebVTT")
    result = await registry.execute(
        "bash", {"command": "ffprobe -v error -show_streams -show_format -of json video.mp4"}
    )
    if result.get("exit_code") != 0:
        raise ValueError(f"视频读取失败：{result}")
    probe = json.loads(result["stdout"])
    kinds = {stream["codec_type"] for stream in probe.get("streams", [])}
    if not {"video", "audio"} <= kinds:
        raise ValueError("视频必须同时包含画面和旁白音轨")
    metadata = json.loads((workdir / "result.json").read_text())
    return CartoonArtifact(
        title=metadata["title"], scene_count=metadata["scene_count"],
        duration_ms=round(float(probe["format"]["duration"]) * 1000),
        output_dir=workdir, html_path=workdir / "index.html",
        video_path=workdir / "video.mp4", caption_path=workdir / "captions.vtt",
    )


async def generate(input: CartoonInput) -> CartoonArtifact:
    """在指定输出目录下生成完整动画视频产物包。"""
    workdir = input.output_dir.resolve() / uuid4().hex
    workdir.mkdir(parents=True)
    try:
        return await _agent_loop(
            [{"role": "user", "content": input.brief.model_dump_json()}],
            _build_tools(workdir, input.brief.configuration),
            system=SYSTEM,
            deliver=partial(_collect_artifact, workdir),
            required_tools=("view_image",),
            max_steps=50,
            timeout_s=1800.0,
        )
    except CartoonGenerationError:
        raise
    except Exception as exc:
        raise CartoonGenerationError(f"视频制作失败：{exc}", stage="generate") from exc
