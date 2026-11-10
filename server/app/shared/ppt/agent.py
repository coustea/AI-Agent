"""教学 PPT 课件创作智能体 —— 基于 PptxGenJS、LibreOffice 与多模态工具循环。"""

from __future__ import annotations

import asyncio
import re
import shlex
import sys
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from app.infra.llm import get_llm_client
from app.infra.logging import get_logger
from app.shared.ppt.schemas import PPTArtifact, PPTBrief, PPTGenerationError
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


class PPTAgent:
    """基于 PptxGenJS 与命令行工具链的教学课件生成智能体。"""

    def __init__(self) -> None:
        """初始化课件 Agent，加载 pptx 技能并配置 LLM 客户端。"""
        self.loader = get_skill_loader()
        self.skill = self.loader.skills_dir / "pptx"
        self.project = Path(__file__).resolve().parents[4]
        self.client, self.spec = get_llm_client("text")
        self.system = f"""你是教学 PPT 创作 agent，使用 PptxGenJS 创建可编辑的课件。
先 load_skill(name='pptx') 阅读官方技能，技能根目录为 {self.skill}。
依赖已由部署安装，不要在任务中安装。Python 使用 {sys.executable}。
用文件工具写 deck.cjs，bash 执行 node deck.cjs，输出 deck.pptx。
自由规划教学内容与版式，必要时写 PLAN.md；不要用整页截图代替原生文本、图表和形状。
遵循用户偏好，中文字体使用实际安装的中文字体。为页面添加有教学价值的演讲备注。
若系统有中文字体但预览中文字消失，用 bash 将所用字体文件复制到 lo-profile/user/fonts/，再重新转换和审查；不要仅修改字体名称。
通过 bash 调用技能目录内 scripts/office/validate.py 校验，使用 LibreOffice 和 pdftoppm 渲染预览图。
制作过程中可用 view_image 查看 previews/slide-*.png 进行版式自检，及时修复文字溢出或遮挡。
完成后直接交付，不等待用户确认，不发布外部服务。
{self.loader.get_descriptions(only=['pptx'])}"""

    async def generate(
        self,
        brief: PPTBrief,
        output_dir: Path,
        *,
        progress: ProgressCallback | None = None,
    ) -> PPTArtifact:
        """根据课件大纲在指定输出目录下生成完整可编辑 PPTX 课件包。"""
        logger.info("[PPTAgent] 开始生成课件: title={} output_dir={}", brief.title, output_dir)
        try:
            async with asyncio.timeout(1800):
                workdir = output_dir.resolve() / uuid4().hex
                workdir.mkdir(parents=True, exist_ok=True)
                # 建立项目根 node_modules 软链接以供 CommonJS 依赖查找
                node_modules_target = self.project / "node_modules"
                link_path = workdir / "node_modules"
                if not link_path.exists() and node_modules_target.is_dir():
                    link_path.symlink_to(node_modules_target, target_is_directory=True)

                registry = ToolRegistry([
                    *build_builtin_tools(workdir, timeout_s=300),
                    build_load_skill_tool(self.loader, only=["pptx"]),
                ])
                artifact = await self._run(brief, workdir, registry, progress)
                logger.info(
                    "[PPTAgent] 课件生成完成: title={} slides={} pptx={}",
                    getattr(artifact, "title", ""),
                    getattr(artifact, "slide_count", 0),
                    getattr(artifact, "pptx_path", ""),
                )
                return artifact
        except PPTGenerationError as exc:
            logger.error("[PPTAgent] 课件生成失败: title={} error={}", brief.title, exc)
            raise
        except TimeoutError:
            logger.error("[PPTAgent] 课件生成超时 (>1800s): title={}", brief.title)
            raise PPTGenerationError("课件生成超时 (>1800s)")
        except Exception as exc:
            logger.exception("[PPTAgent] 课件生成异常: title={}", brief.title)
            raise PPTGenerationError(f"课件生成失败：{exc}") from exc

    async def _run(
        self,
        brief: PPTBrief,
        workdir: Path,
        registry: ToolRegistry,
        progress: ProgressCallback | None,
    ) -> PPTArtifact:
        """驱动工具循环执行课件编写、编译与物理产物核验。"""
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
                "[PPTAgent] 第 {}/{} 轮: tool_calls={} text_len={}",
                step + 1, max_total_steps, len(tool_calls), len(content_str),
            )
            if content_str:
                thought_preview = content_str.strip().replace("\n", " ")
                if len(thought_preview) > 120:
                    thought_preview = f"{thought_preview[:117]}..."
                logger.info("[PPTAgent] 思考规划: {}", thought_preview)

            if tool_calls:
                logger.info("[PPTAgent] 本轮待执行工具数量: {}", len(tool_calls))
                for idx, call in enumerate(tool_calls, 1):
                    if progress:
                        await progress(f"正在制作课件：{call.function.name}", min(90, 10 + step))
                    args_summary = summarize_tool_args(call.function.name, call.function.arguments)
                    logger.info(
                        "[PPTAgent]   -> [{}/{}] 调用工具: {} | 参数: {}",
                        idx, len(tool_calls), call.function.name, args_summary,
                    )
                    start_t = time.perf_counter()
                    try:
                        raw_res = await registry.execute(call.function.name, call.function.arguments)
                        result = format_tool_output(raw_res)
                        cost_ms = round((time.perf_counter() - start_t) * 1000)
                        res_summary = summarize_tool_result(call.function.name, raw_res)
                        logger.info(
                            "[PPTAgent]   <- [{}/{}] 工具完成: {} (耗时 {}ms) | 结果: {}",
                            idx, len(tool_calls), call.function.name, cost_ms, res_summary,
                        )
                    except Exception as exc:
                        cost_ms = round((time.perf_counter() - start_t) * 1000)
                        result = f"Error: {exc}"
                        logger.warning(
                            "[PPTAgent]   ❌ [{}/{}] 工具失败: {} (耗时 {}ms) | 错误: {}",
                            idx, len(tool_calls), call.function.name, cost_ms, exc,
                        )
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
                continue

            # 模型未再发起工具调用，进入最终物理构建与校验
            if progress:
                await progress("正在核验课件物理完整性与渲染预览图...", 92)

            try:
                artifact = await self._build_and_verify(brief.title, workdir, registry)
                if progress:
                    await progress("课件生成与质量核验完成", 100)
                return artifact
            except (ValueError, OSError, KeyError, BadZipFile) as exc:
                revisions += 1
                logger.warning(
                    "[PPTAgent] 物理核验未通过 (第 {}/{} 次修复): {}", revisions, max_revisions, exc,
                )
                if revisions > max_revisions:
                    raise PPTGenerationError(f"课件交付核验未通过，已达最大修复次数：{exc}") from exc
                messages.append({
                    "role": "user",
                    "content": f"课件物理交付检查失败，请修复 deck.cjs 并重新运行 node：{exc}",
                })

        raise PPTGenerationError("课件制作达到最大工具轮数")

    async def _build_and_verify(
        self,
        title: str,
        workdir: Path,
        registry: ToolRegistry,
    ) -> PPTArtifact:
        """执行最终可信构建：OOXML 校验、LibreOffice 转 PDF 及 Poppler 逐页渲染。"""
        deck = workdir / "deck.pptx"
        if not deck.is_file() or deck.stat().st_size == 0:
            raise ValueError("deck.pptx 未生成或文件为空，请运行 node deck.cjs")

        with ZipFile(deck) as archive:
            count = sum(bool(re.fullmatch(r"ppt/slides/slide\d+\.xml", name)) for name in archive.namelist())
        if not count:
            raise ValueError("PPTX 没有包含任何幻灯片页面")

        previews = workdir / "previews"
        previews.mkdir(exist_ok=True)
        for path in previews.glob("slide-*.png"):
            path.unlink()
        (workdir / "deck.pdf").unlink(missing_ok=True)

        python = shlex.quote(sys.executable)
        commands = [
            f"{python} {shlex.quote(str(self.skill / 'scripts/office/validate.py'))} deck.pptx",
            f"{python} {shlex.quote(str(self.skill / 'scripts/office/soffice.py'))} -env:UserInstallation={(workdir / 'lo-profile').as_uri()} --headless --convert-to pdf --outdir . deck.pptx",
            "pdftoppm -png -r 120 deck.pdf previews/slide",
        ]
        for command in commands:
            result = await registry.execute("bash", {"command": command})
            if result.get("exit_code") != 0:
                logger.error(
                    "[PPTAgent] 构建命令失败 (exit={}): {}\nstderr: {}",
                    result.get("exit_code"), command, result.get("stderr"),
                )
                raise ValueError(f"构建命令执行失败：{command}\n{result.get('stderr') or result}")

        images = sorted(previews.glob("slide-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
        pdf = workdir / "deck.pdf"
        if len(images) != count or not pdf.is_file() or pdf.stat().st_size == 0:
            logger.error(
                "[PPTAgent] 渲染产物不完整: slides={} images={} pdf_ok={}",
                count, len(images), pdf.is_file(),
            )
            raise ValueError("渲染产物不完整，页数与幻灯片数不匹配")

        return PPTArtifact(
            title=title,
            pptx_path=deck,
            pdf_path=pdf,
            preview_paths=images,
            slide_count=count,
        )


__all__ = ["PPTAgent", "ProgressCallback"]
