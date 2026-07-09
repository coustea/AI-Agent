"""Application service for CartoonAgent video generation.

service 负责：
1. 创建输出目录；
2. 调用 CartoonAgent；
3. 调用 HyperFrames lint/render；
4. 暴露产物路径。
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger
from app.shared.cartoon.cartoon_agent import (
    CartoonAgent,
    CartoonGenerationError,
    CartoonGenerationResult,
)
from app.shared.cartoon.renderer import CartoonVideoRenderer

logger = get_logger(__name__)


@dataclass(frozen=True)
class CartoonVideoResult:
    task_id: str
    title: str
    duration: float
    scene_count: int
    output_dir: Path
    markdown_path: Path
    html_path: Path
    video_path: Path | None
    audit_path: Path


class CartoonVideoService:
    def __init__(
        self,
        *,
        base_output_dir: Path | None = None,
        agent: CartoonAgent | None = None,
        renderer: CartoonVideoRenderer | None = None,
    ) -> None:
        self.base_output_dir = base_output_dir or Path(
            os.getenv("CARTOON_OUTPUT_DIR", "storage/cartoon")
        )
        self.agent = agent or CartoonAgent()
        self.renderer = renderer or CartoonVideoRenderer()

    async def generate(
        self,
        *,
        task_id: str,
        learning_need: str,
        profile: dict[str, Any] | str | None = None,
        duration: int | None = None,
    ) -> CartoonVideoResult:
        output_dir = self.resolve_output_dir(task_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Cartoon 生成开始: task_id=%s", task_id)

        # Step 1: Generate via CartoonAgent
        result = await self.agent.generate(
            learning_need=learning_need,
            output_dir=output_dir,
            profile=profile,
        )

        # Step 2: Run HyperFrames lint
        lint_result = await self.renderer.lint(output_dir)
        if not lint_result.passed:
            logger.warning(
                "HyperFrames lint 失败: %s",
                "; ".join(lint_result.problems[:5]),
            )
            audit_data = {
                "passed": False,
                "problems": lint_result.problems,
                "stage": "hyperframes_lint",
            }
            (output_dir / "audit.json").write_text(
                json.dumps(audit_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            raise CartoonGenerationError(
                f"HyperFrames lint 失败: {'; '.join(lint_result.problems[:5])}",
                audit=lint_result,
            )

        # Step 3: Render MP4
        video_path: Path | None = None
        try:
            render_result = await self.renderer.render(output_dir)
            video_path = render_result.video_path
        except Exception as exc:
            logger.exception("Cartoon MP4 渲染失败")
            raise CartoonGenerationError(f"MP4 渲染失败: {exc}") from exc

        logger.info(
            "Cartoon 生成完成: task_id=%s title=%s duration=%.1fs video=%s",
            task_id,
            result.title,
            result.duration,
            video_path,
        )

        return CartoonVideoResult(
            task_id=task_id,
            title=result.title,
            duration=result.duration,
            scene_count=result.scene_count,
            output_dir=output_dir,
            markdown_path=result.markdown_path,
            html_path=result.html_path,
            video_path=video_path,
            audit_path=result.audit_path,
        )

    def resolve_output_dir(self, task_id: str) -> Path:
        clean_id = self._safe_task_id(task_id)
        return self.base_output_dir / clean_id

    def resolve_markdown(self, task_id: str) -> Path:
        return self.resolve_output_dir(task_id) / "cartoon.md"

    def resolve_html(self, task_id: str) -> Path:
        return self.resolve_output_dir(task_id) / "index.html"

    def resolve_video(self, task_id: str) -> Path:
        output_dir = self.resolve_output_dir(task_id)
        candidates = [
            output_dir / "output.mp4",
            output_dir / "video.mp4",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        mp4_files = sorted(output_dir.rglob("*.mp4"))
        return mp4_files[0] if mp4_files else output_dir / "output.mp4"

    def resolve_audit(self, task_id: str) -> Path:
        return self.resolve_output_dir(task_id) / "audit.json"

    def delete_task(self, task_id: str) -> bool:
        output_dir = self.resolve_output_dir(task_id)
        if not output_dir.exists():
            return False
        shutil.rmtree(output_dir)
        return True

    @staticmethod
    def _safe_task_id(task_id: str) -> str:
        value = "".join(ch for ch in task_id if ch.isalnum() or ch in {"-", "_"})
        if not value:
            raise ValueError("task_id 无效")
        return value[:80]
