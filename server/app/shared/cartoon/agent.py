"""基于 HyperFrames CLI 与多模态工具循环的教学动画视频创作智能体。"""

from __future__ import annotations

import asyncio
import json
import shlex
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.infra.llm import get_llm_client
from app.infra.logging import get_logger
from app.shared.cartoon.schemas import (
    CartoonArtifact,
    CartoonBrief,
    CartoonGenerationError,
)
from app.shared.cartoon.tts import build_speech_tool
from app.shared.tools.builtin import build_builtin_tools
from app.shared.tools.registry import (
    ToolRegistry,
    format_tool_output,
    summarize_tool_args,
    summarize_tool_result,
)
from app.shared.tools.skills import build_load_skill_tool, get_skill_loader

ProgressCallback = Callable[[str, int], Awaitable[None]]

logger = get_logger(__name__)

SKILLS = ("hyperframes", "hyperframes-cli", "hyperframes-registry", "media-use")


def _describe_video_step(name: str, raw_args: str) -> str:
    """将视频生成过程中的工具调用转换为可读的进度说明。"""
    try:
        args = json.loads(raw_args or "{}")
    except Exception:
        args = {}
    if name == "load_skill":
        skill = args.get("name") or "hyperframes"
        ref = args.get("reference")
        return f"读取技能规范: {skill}{f' ({ref})' if ref else ''}"
    if name == "synthesize_speech":
        out = Path(str(args.get("output_path") or "旁白")).name
        return f"合成中文语音旁白: {out}"
    if name in {"write", "edit"}:
        path = Path(str(args.get("path") or "场景文件")).name
        return f"编写视频场景与字幕文件: {path}"
    if name == "view_image":
        path = Path(str(args.get("path") or "关键帧")).name
        return f"视觉模型审查画面截图: {path}"
    if name == "bash":
        cmd = str(args.get("command") or "")
        if "render" in cmd:
            return "渲染合成 MP4 视频"
        if "snapshot" in cmd:
            return "截取关键帧画面以供审查"
        if "check" in cmd:
            return "校验 HyperFrames 时间轴与结构"
        if "ffprobe" in cmd:
            return "检验输出音视频流完整性"
        return "执行视频构建命令"
    return f"执行视频创作工具: {name}"


class CartoonAgent:
    """基于 HyperFrames CLI 与工具调用的教学动画视频生成智能体。"""

    def __init__(self) -> None:
        """初始化动画视频 Agent，配置工作环境与 LLM 客户端。"""
        self.loader = get_skill_loader()
        self.project = Path(__file__).resolve().parents[4]
        self.cli = self.project / "node_modules/.bin/hyperframes"
        self.client, self.spec = get_llm_client("text")
        self.system = f"""你是教学视频创作 agent。用文件工具创作，用 bash 执行 HyperFrames CLI，用 view_image 检查截图并修复。
工作目录为本次独立视频目录。已安装 CLI：{shlex.quote(str(self.cli))}；不要重新安装依赖。
GSAP 文件：{self.project}/node_modules/gsap/dist/gsap.min.js，可复制到 assets/vendor/。
先 load_skill 读取 hyperframes 主技能，再按需读取格式、CLI、教学视频和媒体参考。
CLI 的 --help 是当前版本参数的依据。用本地 CLI 路径执行技能中的 hyperframes 命令。
自主完成整个视频，包括最终 MP4，不需要等用户批准预览或选择方案；不要发布到外部服务。
自由规划场景，写 PLAN.md 即可，不要求固定卡片模板或固定场景数。
使用 synthesize_speech 生成真实中文旁白，按返回时长编排动画与字幕，禁止用静音代替旁白。
用 CLI check 检查并修复错误；snapshot 截取各场景关键帧、复杂运动中间帧和转场。
调用 view_image 审查截图，问题包含文字遮挡、字幕冲突、画面空白、讲解内容和图示是否一致。
修复后重新截图检查；遇到渲染或排版问题及时修复。
通过 bash 调 CLI render --strict 生成 video.mp4，然后用 ffprobe 检查。任何源文件修改后重新渲染。
最终交付 index.html、video.mp4、captions.vtt，以及可选的 result.json（title 字符串、scene_count 正整数）。
字幕必须是真实旁白内容的 WebVTT，同时在视频里可见。音频和媒体使用本地文件。
可用技能：
{self.loader.get_descriptions(only=SKILLS)}"""

    async def generate(
        self,
        brief: CartoonBrief,
        output_dir: Path,
        *,
        progress: ProgressCallback | None = None,
    ) -> CartoonArtifact:
        """在指定输出目录下生成完整动画视频产物包。"""
        logger.info("[CartoonAgent] 开始生成视频: title={} output_dir={}", brief.title, output_dir)
        try:
            async with asyncio.timeout(1800):
                workdir = output_dir.resolve() / uuid4().hex
                workdir.mkdir(parents=True, exist_ok=True)
                registry = ToolRegistry([
                    *build_builtin_tools(workdir, timeout_s=900),
                    build_load_skill_tool(self.loader, only=SKILLS),
                    build_speech_tool(workdir, voice=brief.configuration.voice, pace=brief.configuration.pace),
                ])
                artifact = await self._run(brief, workdir, registry, progress)
                logger.info(
                    "[CartoonAgent] 视频生成完成: title={} duration={:.1f}s scenes={} video={}",
                    getattr(artifact, "title", ""),
                    getattr(artifact, "duration_seconds", 0.0),
                    getattr(artifact, "scene_count", 0),
                    getattr(artifact, "video_path", ""),
                )
                return artifact
        except CartoonGenerationError as exc:
            logger.error("[CartoonAgent] 视频生成失败 (stage={}): title={} error={}", exc.stage, brief.title, exc)
            raise
        except TimeoutError:
            logger.error("[CartoonAgent] 视频生成超时 (>1800s): title={}", brief.title)
            raise CartoonGenerationError("视频生成超时 (>1800s)", stage="generate")
        except Exception as exc:
            logger.exception("[CartoonAgent] 视频生成异常: title={}", brief.title)
            raise CartoonGenerationError(f"视频制作失败：{exc}", stage="generate") from exc

    async def _run(
        self,
        brief: CartoonBrief,
        workdir: Path,
        registry: ToolRegistry,
        progress: ProgressCallback | None,
    ) -> CartoonArtifact:
        """驱动工具循环执行动画编排、语音合成、渲染与物理核验。"""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system},
            {"role": "user", "content": brief.model_dump_json()},
        ]
        tools = registry.openai_schemas()
        max_total_steps = 60
        revisions = 0
        max_revisions = 2

        for step in range(max_total_steps):
            response = await self.client.chat.completions.create(
                model=self.spec.model_name,
                messages=messages,
                temperature=0.2,
                tools=tools,
                tool_choice="auto",
            )
            msg = response.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))
            tool_calls = getattr(msg, "tool_calls", None) or []
            content_str = getattr(msg, "content", None) or ""
            logger.info(
                "[CartoonAgent] 第 {}/{} 轮: tool_calls={} text_len={}",
                step + 1, max_total_steps, len(tool_calls), len(content_str),
            )
            if content_str:
                thought_preview = content_str.strip().replace("\n", " ")
                if len(thought_preview) > 120:
                    thought_preview = f"{thought_preview[:117]}..."
                logger.info("[CartoonAgent] 思考规划: {}", thought_preview)

            if tool_calls:
                logger.info("[CartoonAgent] 本轮待执行工具数量: {}", len(tool_calls))
                for idx, call in enumerate(tool_calls, 1):
                    if progress:
                        await progress(
                            _describe_video_step(call.function.name, call.function.arguments),
                            min(90, 8 + step * 2),
                        )
                    args_summary = summarize_tool_args(call.function.name, call.function.arguments)
                    logger.info(
                        "[CartoonAgent]   -> [{}/{}] 调用工具: {} | 参数: {}",
                        idx, len(tool_calls), call.function.name, args_summary,
                    )
                    start_t = time.perf_counter()
                    try:
                        raw_res = await registry.execute(call.function.name, call.function.arguments)
                        result = format_tool_output(raw_res)
                        cost_ms = round((time.perf_counter() - start_t) * 1000)
                        res_summary = summarize_tool_result(call.function.name, raw_res)
                        logger.info(
                            "[CartoonAgent]   <- [{}/{}] 工具完成: {} (耗时 {}ms) | 结果: {}",
                            idx, len(tool_calls), call.function.name, cost_ms, res_summary,
                        )
                    except Exception as exc:
                        cost_ms = round((time.perf_counter() - start_t) * 1000)
                        result = f"Error: {exc}"
                        logger.warning(
                            "[CartoonAgent]   ❌ [{}/{}] 工具失败: {} (耗时 {}ms) | 错误: {}",
                            idx, len(tool_calls), call.function.name, cost_ms, exc,
                        )
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
                continue

            # 模型未再发起工具调用，进入最终物理构建与校验
            if progress:
                await progress("正在核验视频物理完整性与音画参数...", 92)

            try:
                artifact = await self._build_and_verify(brief.title, workdir, registry)
                if progress:
                    await progress("视频渲染与质量核验完成", 100)
                return artifact
            except (ValueError, OSError, KeyError, TypeError) as exc:
                revisions += 1
                logger.warning(
                    "[CartoonAgent] 物理核验未通过 (第 {}/{} 次修复): {}", revisions, max_revisions, exc,
                )
                if revisions > max_revisions:
                    raise CartoonGenerationError(f"视频交付核验未通过，已达最大修复次数：{exc}", stage="verify") from exc
                messages.append({
                    "role": "user",
                    "content": f"视频物理交付检查失败，请修复后重新渲染：{exc}",
                })

        raise CartoonGenerationError("视频制作达到最大工具轮数", stage="generate")

    async def _build_and_verify(
        self,
        fallback_title: str,
        workdir: Path,
        registry: ToolRegistry,
    ) -> CartoonArtifact:
        """核验输出目录下的视频与字幕产物物理完整性并构建 CartoonArtifact。"""
        for name in ("index.html", "video.mp4", "captions.vtt"):
            path = workdir / name
            if not path.is_file() or path.stat().st_size == 0:
                raise ValueError(f"缺少必要非空产物：{name}")

        caption_text = (workdir / "captions.vtt").read_text(encoding="utf-8").lstrip()
        if not caption_text.startswith("WEBVTT"):
            raise ValueError("captions.vtt 必须以 WEBVTT 开头")
        if "-->" not in caption_text:
            raise ValueError("captions.vtt 必须包含有效的时间轴时间戳 (-->)")

        result = await registry.execute(
            "bash", {"command": "ffprobe -v error -show_streams -show_format -of json video.mp4"}
        )
        if result.get("exit_code") != 0:
            logger.error(
                "[CartoonAgent] ffprobe 失败 (exit={})\nstderr: {}",
                result.get("exit_code"), result.get("stderr"),
            )
            raise ValueError(f"视频读取失败：{result.get('stderr') or result}")

        probe = json.loads(result["stdout"])
        streams = probe.get("streams", [])
        kinds = {s.get("codec_type") for s in streams}
        if not {"video", "audio"} <= kinds:
            raise ValueError("视频必须同时包含画面流 (video) 和旁白音轨 (audio)")

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
        width = int(video_stream.get("width", 1920))
        height = int(video_stream.get("height", 1080))

        raw_duration = probe.get("format", {}).get("duration")
        if not raw_duration:
            raise ValueError("无法解析视频播放时长")
        duration_seconds = round(float(raw_duration), 2)
        if duration_seconds <= 0:
            raise ValueError("视频时长必须大于 0 秒")

        title = fallback_title
        scene_count = 1
        result_file = workdir / "result.json"
        if result_file.is_file():
            try:
                meta = json.loads(result_file.read_text(encoding="utf-8"))
                title = str(meta.get("title") or fallback_title)
                scene_count = max(1, int(meta.get("scene_count", 1)))
            except Exception:
                pass

        return CartoonArtifact(
            title=title,
            duration_seconds=duration_seconds,
            scene_count=scene_count,
            width=width,
            height=height,
            html_path=workdir / "index.html",
            video_path=workdir / "video.mp4",
            caption_path=workdir / "captions.vtt",
        )


async def generate(
    brief: CartoonBrief,
    output_dir: Path,
    *,
    progress: ProgressCallback | None = None,
) -> CartoonArtifact:
    """在指定输出目录下生成完整动画视频产物包。"""
    return await CartoonAgent().generate(brief, output_dir, progress=progress)


__all__ = ["CartoonAgent", "ProgressCallback", "generate"]
