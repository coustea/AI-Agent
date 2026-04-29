"""
PPT Agent — 演示文稿 Agent。

基于模板占位符生成可直接使用的 PPTX 文件。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.schemas import WorkerResult, WorkerState
from app.resource.utils import read_agent_report
from app.resource.worker_agents.reporter_agent import ReporterAgent
from app.shared.json_utils import parse_first_json_object

logger = get_logger(__name__)


class PptAgent:
    """PPT 生成 Agent。"""

    def __init__(self, user_id: int, resource_id: int):
        self.user_id = user_id
        self.resource_id = resource_id
        self.llm_manager = get_llm_manager()
        self.server_dir = Path(__file__).resolve().parents[3]
        self.repo_dir = self.server_dir.parent
        self.template_dir = self.server_dir / "template" / "淡雅水墨主题教育模版"
        self.template_pptx = self.template_dir / "中国风.template.pptx"
        self.template_manifest = self.template_dir / "中国风.template.manifest.json"

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行 PPT 生成。"""
        try:
            if not self.template_pptx.exists() or not self.template_manifest.exists():
                return WorkerResult(success=False, error="模板或 manifest 不存在")

            workspace_dir = self._get_output_dir()
            workspace_dir.mkdir(parents=True, exist_ok=True)

            manifest = json.loads(self.template_manifest.read_text(encoding="utf-8"))
            slides_json = await self._build_slides_json(state, manifest)
            placeholder_map = await self._build_placeholder_mapping(state, manifest, slides_json)
            placeholder_map = self._postprocess_mapping(state.task, manifest, slides_json, placeholder_map)

            agent_name = state.agent_name or "ppt"
            mapping_path = workspace_dir / f"{agent_name}.mapping.json"
            mapping_path.write_text(json.dumps(placeholder_map, ensure_ascii=False, indent=2), encoding="utf-8")

            output_path = workspace_dir / f"{agent_name}.pptx"
            render_error = await self._render_with_automizer(mapping_path, output_path)
            if render_error:
                logger.warning("[PptAgent] automizer 渲染失败，回退旧渲染器: %s", render_error)
                fallback_error = await self._render_with_xml_replace(mapping_path, output_path)
                if fallback_error:
                    return WorkerResult(
                        success=False,
                        error=f"PPT 渲染失败: automizer={render_error}; fallback={fallback_error}",
                    )

            summary = {
                "template": str(self.template_pptx),
                "manifest": str(self.template_manifest),
                "mapping_file": str(mapping_path),
                "slides_generated": len(slides_json.get("slides", [])),
                "placeholders_filled": sum(1 for _, v in placeholder_map.items() if v.strip()),
            }

            # 后台异步生成执行报告
            asyncio.create_task(
                self._generate_report_async(state.task, json.dumps(summary, ensure_ascii=False))
            )

            return WorkerResult(
                success=True,
                content=json.dumps(summary, ensure_ascii=False, indent=2),
                artifact_path=str(output_path),
                artifact_dir=str(workspace_dir),
                file_type="pptx",
            )
        except Exception as exc:
            logger.exception("[PptAgent] 执行失败")

            # 后台异步生成失败报告
            asyncio.create_task(
                self._generate_report_async(state.task, "", error=str(exc))
            )

            return WorkerResult(success=False, error=str(exc))

    async def _generate_report_async(
        self,
        task: dict[str, Any],
        content: str,
        error: str | None = None,
    ) -> None:
        """后台异步生成执行报告。"""
        try:
            reporter = ReporterAgent()
            report_path, _ = await reporter.generate_report(
                user_id=self.user_id,
                resource_id=self.resource_id,
                agent_type="ppt",
                task=task,
                content=content,
                error=error,
            )
            logger.info("[PptAgent] 报告已生成: %s", report_path)
        except Exception as exc:
            logger.warning("[PptAgent] 报告生成失败: %s", exc)

    async def _build_slides_json(self, state: WorkerState, manifest: dict[str, Any]) -> dict[str, Any]:
        task = state.task

        # 读取依赖 Agent 的报告
        reference_content = ""
        if state.dependencies:
            for dep_name in state.dependencies:
                report = await read_agent_report(
                    self.user_id, self.resource_id, dep_name
                )
                if report:
                    reference_content += f"\n### {dep_name} 报告\n{report}\n"

        prompt = (
            "你是PPT内容规划助手。输出严格JSON："
            '{"slides":[{"slide_no":1,"title":"","subtitle":"","bullets":[""],"notes":""}]}\n'
            f"主题: {task.get('course', '')}\n"
            f"知识点: {task.get('gap', '')}\n"
            f"需求: {task.get('need', 'review')}\n"
            f"总页数: {manifest.get('slide_count', 10)}\n"
            f"参考内容: {reference_content[:4000]}"
        )
        try:
            response = await self.llm_manager.ainvoke(
                "deepseek",
                [HumanMessage(content=prompt)],
                model_kwargs={"temperature": 0.3},
            )
            content = response.content if hasattr(response, "content") else str(response)
            parsed = parse_first_json_object(content)
            if parsed and isinstance(parsed.get("slides"), list):
                return parsed
        except Exception:
            logger.warning("[PptAgent] slides_json LLM 生成失败，使用降级策略")

        return self._fallback_slides(task, manifest)

    async def _build_placeholder_mapping(
        self,
        state: WorkerState,
        manifest: dict[str, Any],
        slides_json: dict[str, Any],
    ) -> dict[str, str]:
        replacements = manifest.get("replacements", [])
        placeholders = [item.get("placeholder", "") for item in replacements if item.get("placeholder")]
        prompt = (
            "将 slides 内容映射到 placeholders。只输出JSON对象，key必须来自 placeholders。\n"
            f"placeholders: {json.dumps(placeholders, ensure_ascii=False)}\n"
            f"slides: {json.dumps(slides_json, ensure_ascii=False)}\n"
            "value 要简洁自然，适合教学汇报PPT。"
        )
        try:
            response = await self.llm_manager.ainvoke(
                "deepseek",
                [HumanMessage(content=prompt)],
                model_kwargs={"temperature": 0.2},
            )
            content = response.content if hasattr(response, "content") else str(response)
            parsed = parse_first_json_object(content)
            if isinstance(parsed, dict):
                mapping = {}
                for p in placeholders:
                    v = parsed.get(p, "")
                    mapping[p] = self._normalize_cell(v)
                if any(v for v in mapping.values()):
                    return mapping
        except Exception:
            logger.warning("[PptAgent] placeholder 映射 LLM 生成失败，使用降级策略")

        return self._fallback_mapping(state.task, manifest, slides_json)

    def _postprocess_mapping(
        self,
        task: dict[str, Any],
        manifest: dict[str, Any],
        slides_json: dict[str, Any],
        mapping: dict[str, str],
    ) -> dict[str, str]:
        """后处理映射，避免空白和文本溢出。"""
        slide_by_no = {
            int(item.get("slide_no", 0)): item
            for item in slides_json.get("slides", [])
            if isinstance(item, dict)
        }
        topic = task.get("course", "课程主题")
        gap = task.get("gap", "核心知识点")
        repaired: dict[str, str] = {}

        for item in manifest.get("replacements", []):
            placeholder = item.get("placeholder", "")
            original = str(item.get("original_text", "")).strip()
            slide_no = int(item.get("slide_index", 0))
            text_index = int(item.get("text_index", 0))

            value = str(mapping.get(placeholder, "")).strip()
            if not value:
                slide = slide_by_no.get(slide_no, {})
                bullets = slide.get("bullets", []) if isinstance(slide, dict) else []
                if text_index == 1:
                    value = str(slide.get("title") or topic)
                elif text_index == 2:
                    value = str(slide.get("subtitle") or gap)
                elif 3 <= text_index <= 6 and bullets:
                    value = str(bullets[(text_index - 3) % len(bullets)])
                else:
                    # 缺失值时优先回退原模板文本，避免出现空框
                    value = original or f"{topic}"

            # 按原模板文本长度限制，减少重叠
            original_len = max(len(original), 1)
            max_len = min(max(original_len * 2, 10), 40)
            if text_index == 1:
                max_len = min(max_len, 22)
            elif text_index == 2:
                max_len = min(max_len, 28)

            value = value.replace("\n", " ").strip()
            if len(value) > max_len:
                value = value[:max_len]

            repaired[placeholder] = self._normalize_cell(value)

        return repaired

    def _fallback_slides(self, task: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
        slide_count = int(manifest.get("slide_count", 10))
        topic = task.get("course", "课程主题")
        gap = task.get("gap", "核心知识点")
        need = task.get("need", "review")

        slides = []
        for i in range(1, slide_count + 1):
            slides.append(
                {
                    "slide_no": i,
                    "title": f"{topic} · 第{i}页",
                    "subtitle": f"学习目标：{gap}",
                    "bullets": [
                        f"围绕“{topic}”建立系统理解",
                        f"聚焦“{gap}”进行重点突破",
                        f"学习方式：{need}",
                    ],
                    "notes": f"第{i}页讲解：结合案例说明 {topic} 与 {gap}。",
                }
            )
        return {"slides": slides}

    def _fallback_mapping(
        self,
        task: dict[str, Any],
        manifest: dict[str, Any],
        slides_json: dict[str, Any],
    ) -> dict[str, str]:
        slide_by_no = {
            int(item.get("slide_no", 0)): item
            for item in slides_json.get("slides", [])
            if isinstance(item, dict)
        }
        topic = task.get("course", "课程主题")
        gap = task.get("gap", "核心知识点")

        mapping: dict[str, str] = {}
        for item in manifest.get("replacements", []):
            placeholder = item.get("placeholder", "")
            slide_no = int(item.get("slide_index", 0))
            text_index = int(item.get("text_index", 0))
            original = str(item.get("original_text", "")).strip()

            slide = slide_by_no.get(slide_no, {})
            bullets = slide.get("bullets", []) if isinstance(slide, dict) else []

            if text_index == 1:
                value = str(slide.get("title") or topic)
            elif text_index == 2:
                value = str(slide.get("subtitle") or gap)
            elif 3 <= text_index <= 6 and bullets:
                value = str(bullets[(text_index - 3) % len(bullets)])
            elif "目录" in original:
                value = "课程目录"
            elif "总结" in original:
                value = "课程总结"
            else:
                value = str(slide.get("notes") or f"{topic} · {gap}")

            mapping[placeholder] = self._normalize_cell(value)
        return mapping

    def _normalize_cell(self, value: Any) -> str:
        text = str(value or "").replace("\n", " ").strip()
        if len(text) > 80:
            return text[:80]
        return text

    async def _render_with_automizer(self, mapping_path: Path, output_path: Path) -> str | None:
        cmd = [
            "node",
            "server/app/tools/ppt-template/render-with-automizer.mjs",
            "--template-pptx",
            str(self.template_pptx),
            "--manifest",
            str(self.template_manifest),
            "--mapping-json",
            str(mapping_path),
            "--output",
            str(output_path),
        ]
        return await self._run_render_cmd(cmd)

    async def _render_with_xml_replace(self, mapping_path: Path, output_path: Path) -> str | None:
        cmd = [
            "node",
            "server/app/tools/ppt-template/render-from-template.mjs",
            "--template-pptx",
            str(self.template_pptx),
            "--mapping-json",
            str(mapping_path),
            "--output",
            str(output_path),
        ]
        return await self._run_render_cmd(cmd)

    async def _run_render_cmd(self, cmd: list[str]) -> str | None:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.repo_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return None
        return (stderr or stdout).decode("utf-8", errors="ignore")[:2000]

    def _get_output_dir(self) -> Path:
        return self.server_dir / "workplace" / "resource" / str(self.user_id) / str(self.resource_id)
