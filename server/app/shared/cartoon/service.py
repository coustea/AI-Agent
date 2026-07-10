"""Application service for theory animation video generation."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger
from app.shared.cartoon.cartoon import CartoonVideoAgent, CartoonGenerationError
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
        agent: CartoonVideoAgent | None = None,
        renderer: CartoonVideoRenderer | None = None,
    ) -> None:
        self.base_output_dir = base_output_dir or Path(os.getenv("CARTOON_VIDEO_OUTPUT_DIR", "storage/cartoon_video"))
        self.agent = agent or CartoonVideoAgent()
        self.renderer = renderer or CartoonVideoRenderer()

    async def generate(
        self,
        *,
        task_id: str,
        learning_need: str,
        profile: dict[str, Any] | None = None,
        duration: int | None = None,
        render_mp4: bool = True,
    ) -> CartoonVideoResult:
        final_dir = self.resolve_output_dir(task_id)
        temp_dir = self.base_output_dir / f".{self._safe_task_id(task_id)}.tmp"

        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        final_dir.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Theory video 生成开始: task_id=%s render_mp4=%s", task_id, render_mp4)

        try:
            result = await self.agent.generate(
                learning_need=learning_need,
                output_dir=temp_dir,
                profile=profile or {},
                target_duration=duration,
            )

            lint_result = await self.renderer.lint(temp_dir)
            self._update_audit(
                result.audit_path,
                "hyperframes_lint",
                {"passed": lint_result.passed, "problems": lint_result.problems},
            )
            if not lint_result.passed:
                raise CartoonGenerationError(
                    f"HyperFrames lint 失败: {'; '.join(lint_result.problems[:6])}",
                    audit=lint_result,
                )

            video_path: Path | None = None
            if render_mp4:
                render_result = await self.renderer.render(temp_dir)
                video_path = render_result.video_path
                self._update_audit(
                    result.audit_path,
                    "render",
                    {
                        "passed": True,
                        "problems": [],
                        "video_path": str(video_path),
                        "duration": render_result.duration,
                        "width": render_result.width,
                        "height": render_result.height,
                        "fps": render_result.fps,
                    },
                    overall_passed=True,
                )
            else:
                self._update_audit(
                    result.audit_path,
                    "render",
                    {"passed": True, "skipped": True, "problems": []},
                    overall_passed=True,
                )

            if final_dir.exists():
                shutil.rmtree(final_dir)
            temp_dir.rename(final_dir)

            final_video_path = final_dir / video_path.name if video_path is not None else None

            logger.info(
                "Theory video 生成完成: task_id=%s title=%s duration=%.1fs video=%s",
                task_id,
                result.title,
                result.duration,
                final_video_path,
            )

            return CartoonVideoResult(
                task_id=task_id,
                title=result.title,
                duration=result.duration,
                scene_count=result.scene_count,
                output_dir=final_dir,
                markdown_path=final_dir / result.markdown_path.name,
                html_path=final_dir / result.html_path.name,
                video_path=final_video_path,
                audit_path=final_dir / result.audit_path.name,
            )
        except Exception:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            raise

    def resolve_output_dir(self, task_id: str) -> Path:
        return self.base_output_dir / self._safe_task_id(task_id)

    def resolve_markdown(self, task_id: str) -> Path:
        return self.resolve_output_dir(task_id) / "theory_video.md"

    def resolve_html(self, task_id: str) -> Path:
        return self.resolve_output_dir(task_id) / "index.html"

    def resolve_video(self, task_id: str) -> Path:
        output_dir = self.resolve_output_dir(task_id)
        candidates = [output_dir / "output.mp4", output_dir / "video.mp4"]
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
        value = "".join(ch for ch in str(task_id) if ch.isalnum() or ch in {"-", "_"})
        if not value:
            raise ValueError("task_id 无效")
        return value[:80]

    @staticmethod
    def _update_audit(
        audit_path: Path,
        stage: str,
        stage_payload: dict[str, Any],
        *,
        overall_passed: bool | None = None,
    ) -> None:
        if audit_path.is_file():
            try:
                audit_data = json.loads(audit_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                audit_data = {}
        else:
            audit_data = {}

        stages = audit_data.setdefault("stages", {})
        stages[stage] = stage_payload

        if overall_passed is not None:
            audit_data["passed"] = overall_passed
        elif not stage_payload.get("passed", False):
            audit_data["passed"] = False

        audit_path.write_text(json.dumps(audit_data, ensure_ascii=False, indent=2), encoding="utf-8")