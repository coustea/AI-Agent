"""A single tool loop authors, validates and visually reviews editable PPTX files."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shlex
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from app.infra.llm import get_llm_client
from app.shared.ppt.schemas import PPTArtifact, PPTBrief, PPTGenerationError
from app.shared.tools.builtin import build_builtin_tools
from app.shared.tools.registry import ToolRegistry, format_tool_output
from app.shared.tools.skills import build_load_skill_tool, get_skill_loader

ProgressCallback = Callable[[str, int], Awaitable[None]]


def fingerprint(path: Path) -> str:
    """计算指定文件的 SHA-256 哈希摘要值。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PPTAgent:
    """无状态流 python-pptx 教学课件生成智能体。"""

    def __init__(self) -> None:
        """初始化 PPT 创作 Agent、加载 pptx 技能并构造系统提示词。"""
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
通过 bash 调用技能目录内 scripts/office/validate.py 校验，使用 LibreOffice 和 pdftoppm 渲染。
退出前系统会对当前 deck.pptx 重新校验并渲染 previews/slide-*.png，返回必须审查的文件。
逐页用 view_image 检查文字溢出、遮挡、图表、内容完整性和可读性；修复 deck.cjs 后重新运行 node。
不要修改预览图片掩盖问题。修复最多两轮，仍有严重问题请明确报告失败，不要宣称成功。
完成后直接交付，不等待用户确认，不发布外部服务。
{self.loader.get_descriptions(only=['pptx'])}"""

    async def generate(self, brief: PPTBrief, output_dir: Path, *, progress: ProgressCallback | None = None) -> PPTArtifact:
        """根据课件大纲在指定输出目录下生成完整可编辑 PPTX 课件包。"""
        try:
            async with asyncio.timeout(1800):
                workdir = output_dir.resolve() / uuid4().hex
                workdir.mkdir(parents=True)
                # Resolve CommonJS dependencies even when storage is outside the repository.
                (workdir / "node_modules").symlink_to(self.project / "node_modules", target_is_directory=True)
                registry = ToolRegistry([
                    *build_builtin_tools(workdir, timeout_s=300),
                    build_load_skill_tool(self.loader, only=["pptx"]),
                ])
                return await self._run(brief, workdir, registry, progress)
        except PPTGenerationError:
            raise
        except Exception as exc:
            raise PPTGenerationError(f"课件生成失败：{exc}") from exc

    async def _run(
        self, brief: PPTBrief, workdir: Path, registry: ToolRegistry,
        progress: ProgressCallback | None,
    ) -> PPTArtifact:
        """驱动工具调用循环执行 PPTX 编写、命令行审计与逐页视觉审查。"""
        messages = [{"role": "system", "content": self.system}, {"role": "user", "content": brief.model_dump_json()}]
        prepared_hash = ""
        source_hash = ""
        previews: dict[Path, str] = {}
        reviewed: set[Path] = set()
        revisions = 0
        tools = registry.openai_schemas()
        for step in range(60):
            response = await self.client.chat.completions.create(
                model=self.spec.model_name, messages=messages, temperature=0.2,
                tools=tools, tool_choice="auto",
            )
            msg = response.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))
            if msg.tool_calls:
                for call in msg.tool_calls:
                    if progress:
                        await progress(f"正在制作课件：{call.function.name}", min(90, 10 + step))
                    try:
                        raw_res = await registry.execute(call.function.name, call.function.arguments)
                        result = format_tool_output(raw_res)
                    except Exception as exc:
                        result = f"Error: {exc}"
                    if call.function.name == "view_image" and not result.startswith(("[Error]", "Error")):
                        args = json.loads(call.function.arguments)
                        path = (workdir / args["path"]).resolve()
                        if (path in previews and path.is_file() and fingerprint(path) == previews[path]
                                and fingerprint(workdir / "deck.pptx") == prepared_hash):
                            reviewed.add(path)
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
                continue
            try:
                deck = workdir / "deck.pptx"
                current_hash = fingerprint(deck)
                current_source = fingerprint(workdir / "deck.cjs")
                if prepared_hash and current_source != source_hash and current_hash == prepared_hash:
                    raise ValueError("deck.cjs 已修改但 PPTX 未更新，请运行 node deck.cjs")
                if current_hash != prepared_hash or any(not p.is_file() or fingerprint(p) != h for p, h in previews.items()):
                    if revisions >= 3:
                        raise PPTGenerationError("视觉修复轮数已用尽")
                    artifact = await self._prepare(brief.title, workdir, self.skill, registry)
                    prepared_hash = fingerprint(deck)
                    source_hash = current_source
                    previews = {p.resolve(): fingerprint(p) for p in artifact.preview_paths}
                    pdf_hash = fingerprint(artifact.pdf_path)
                    reviewed.clear()
                    revisions += 1
                missing = set(previews) - reviewed
                if missing:
                    raise ValueError("请逐页调用 view_image 审查实际渲染图：" + ", ".join(str(p.relative_to(workdir)) for p in sorted(missing)))
                if fingerprint(artifact.pdf_path) != pdf_hash:
                    prepared_hash = ""
                    raise ValueError("PDF 已改变，需要重新渲染审查")
                if progress:
                    await progress("课件生成与逐页审查完成", 100)
                return artifact
            except (ValueError, OSError, KeyError, BadZipFile) as exc:
                messages.append({"role": "user", "content": f"交付检查失败，请修复：{exc}"})
        raise PPTGenerationError("课件生成达到最大工具轮数")

    @staticmethod
    async def _prepare(title: str, workdir: Path, skill: Path, registry: ToolRegistry) -> PPTArtifact:
        """Validate the actual final deck and render fresh review images through CLI tools."""
        with ZipFile(workdir / "deck.pptx") as archive:
            count = sum(bool(re.fullmatch(r"ppt/slides/slide\d+\.xml", name)) for name in archive.namelist())
        if not count:
            raise ValueError("PPTX 没有幻灯片")
        previews = workdir / "previews"
        previews.mkdir(exist_ok=True)
        for path in previews.glob("slide-*.png"):
            path.unlink()
        (workdir / "deck.pdf").unlink(missing_ok=True)
        python = shlex.quote(sys.executable)
        commands = [
            f"{python} {shlex.quote(str(skill / 'scripts/office/validate.py'))} deck.pptx",
            f"{python} {shlex.quote(str(skill / 'scripts/office/soffice.py'))} -env:UserInstallation={ (workdir / 'lo-profile').as_uri() } --headless --convert-to pdf --outdir . deck.pptx",
            "pdftoppm -png -r 120 deck.pdf previews/slide",
        ]
        for command in commands:
            result = await registry.execute("bash", {"command": command})
            if result.get("exit_code") != 0:
                raise ValueError(f"命令失败：{command}\n{result}")
        images = sorted(previews.glob("slide-*.png"), key=lambda p: int(p.stem.split('-')[-1]))
        if len(images) != count or not (workdir / "deck.pdf").is_file() or any(p.stat().st_size == 0 for p in images):
            raise ValueError("渲染产物不完整，页数不匹配")
        return PPTArtifact(title=title, pptx_path=workdir / "deck.pptx", pdf_path=workdir / "deck.pdf",
                           preview_paths=images, slide_count=count)
