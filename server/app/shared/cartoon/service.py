"""动画讲解视频服务 — 统一入口。

提供两个公开接口：
- generate_resource(ResourceInput) → AgentResult  # 多智能体资源生成入口
- generate_for_path(PathResourceRequest) → AgentResult  # 路径规划入口

文件保存路径规范：
- Resource: storage/{username}/resource/{resource_id}/cartoon/
- Path: storage/{username}/path/{path_id}/{node_id}/cartoon/
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

from app.config import WORKPLACE_DIR
from app.infra.logging import get_logger
from app.shared.cartoon.cartoon import CartoonGenerationError, CartoonVideoAgent
from app.shared.cartoon.renderer import CartoonVideoRenderer

if TYPE_CHECKING:
    from app.path.schemas import PathResourceRequest
    from app.resource.schemas import AgentResult, ResourceInput

logger = get_logger(__name__)


@dataclass(frozen=True)
class _GenerateResult:
    """内部生成结果。"""
    title: str
    duration: float
    scene_count: int
    output_dir: Path
    html_path: Path
    video_path: Path | None
    video_url: str
    html_url: str


class CartoonService:
    """动画讲解视频服务 — 统一入口。

    两个公开接口：
    - generate_resource(): 多智能体资源生成入口
    - generate_for_path(): 路径规划入口

    文件保存路径规范：
    - Resource: storage/{username}/resource/{resource_id}/cartoon/
    - Path: storage/{username}/path/{path_id}/{node_id}/cartoon/
    """

    def __init__(
        self,
        *,
        agent: CartoonVideoAgent | None = None,
        renderer: CartoonVideoRenderer | None = None,
    ) -> None:
        self._agent = agent or CartoonVideoAgent()
        self._renderer = renderer or CartoonVideoRenderer()

    # =========================================================================
    # 公开接口
    # =========================================================================

    async def generate_resource(self, input_data: "ResourceInput") -> "AgentResult":
        """多智能体资源生成入口。

        路径格式: storage/{username}/resource/{resource_id}/cartoon/

        Args:
            input_data: 多智能体资源生成输入

        Returns:
            AgentResult: 统一输出结果
        """
        from app.resource.schemas import AgentResult

        username = input_data.username or "anonymous"
        resource_id = input_data.resource_id or 0
        learning_need = input_data.learning_need

        logger.info(
            "CartoonService.generate_resource 开始: username=%s resource_id=%s learning_need=%s",
            username, resource_id, learning_need[:50]
        )
        started = time.perf_counter()

        output_dir = WORKPLACE_DIR / username / "resource" / str(resource_id) / "cartoon"

        try:
            result = await self._generate(
                output_dir=output_dir,
                learning_need=learning_need,
                profile=input_data.profile,
            )
        except CartoonGenerationError as exc:
            return self._error_result(learning_need, exc, started)
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.error("CartoonService.generate_resource 异常: %s elapsed_ms=%d", exc, elapsed_ms, exc_info=True)
            return AgentResult(
                success=False,
                title=f"{learning_need} - 动画讲解视频",
                file_type="mp4",
                error=str(exc),
                metadata={"agent_id": "cartoon"},
            )

        return self._build_agent_result(result, started)

    async def generate_for_path(self, request: "PathResourceRequest") -> "AgentResult":
        """路径规划专用入口。

        路径格式: storage/{username}/path/{path_id}/{node_id}/cartoon/

        Args:
            request: 路径规划统一请求参数

        Returns:
            AgentResult: 统一输出结果
        """
        from app.resource.schemas import AgentResult

        tutorial = request.tutorial
        if tutorial is None:
            return AgentResult(
                success=False,
                title="动画视频生成失败",
                file_type="mp4",
                error="缺少教程内容",
            )

        username = request.username or "anonymous"
        path_id = request.path_id
        node_id = request.node_id
        learning_need = f"{request.node_title}: {tutorial.content_markdown[:2000]}"

        output_dir = WORKPLACE_DIR / username / "path" / str(path_id) / str(node_id) / "cartoon"

        try:
            result = await self._generate(
                output_dir=output_dir,
                learning_need=learning_need,
                profile=request.profile,
            )
        except Exception as exc:
            logger.exception("动画视频生成失败")
            return AgentResult(
                success=False,
                title="动画视频生成失败",
                file_type="mp4",
                error=str(exc),
            )

        return self._build_agent_result(result, time.perf_counter())

    # =========================================================================
    # 内部方法
    # =========================================================================

    async def _generate(
        self,
        *,
        output_dir: Path,
        learning_need: str,
        profile: dict[str, Any] | None = None,
        render_mp4: bool = True,
    ) -> _GenerateResult:
        """核心生成逻辑。"""
        temp_dir = output_dir.parent / f".{output_dir.name}.tmp"

        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Cartoon video 生成开始: output_dir=%s", output_dir)

        try:
            result = await self._agent.generate(
                learning_need=learning_need,
                output_dir=temp_dir,
                profile=profile or {},
            )

            lint_result = await self._renderer.lint(temp_dir)
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
                render_result = await self._renderer.render(temp_dir)
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

            if output_dir.exists():
                shutil.rmtree(output_dir)
            temp_dir.rename(output_dir)

            final_video_path = output_dir / video_path.name if video_path else None
            final_html_path = output_dir / result.html_path.name

            # 构建静态 URL
            video_url = ""
            html_url = ""
            if final_video_path and final_video_path.exists():
                video_url = f"/static/{final_video_path.relative_to(WORKPLACE_DIR)}"
            if final_html_path.exists():
                html_url = f"/static/{final_html_path.relative_to(WORKPLACE_DIR)}"

            logger.info(
                "Cartoon video 生成完成: output_dir=%s title=%s duration=%.1fs",
                output_dir, result.title, result.duration,
            )

            return _GenerateResult(
                title=result.title,
                duration=result.duration,
                scene_count=result.scene_count,
                output_dir=output_dir,
                html_path=final_html_path,
                video_path=final_video_path,
                video_url=video_url,
                html_url=html_url,
            )
        except Exception:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            raise

    def _build_agent_result(self, result: _GenerateResult, started: float) -> "AgentResult":
        """构建 AgentResult 输出。"""
        from app.resource.schemas import AgentResult

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        return AgentResult(
            success=True,
            title=f"{result.title} - 动画讲解视频",
            file_type="mp4",
            content="",
            summary=f"生成 {result.scene_count} 个场景、{result.duration:.1f} 秒动画讲解视频",
            metrics={
                "scene_count": result.scene_count,
                "duration_seconds": round(result.duration, 2),
                "elapsed_ms": elapsed_ms,
            },
            metadata={
                "engine": "hyperframes",
                "agent_id": "cartoon",
                "video_url": result.video_url,
                "html_url": result.html_url,
                "duration_seconds": result.duration,
                "scene_count": result.scene_count,
                "html_path": str(result.html_path),
                "video_path": str(result.video_path) if result.video_path else None,
            },
        )

    def _error_result(self, learning_need: str, exc: CartoonGenerationError, started: float) -> "AgentResult":
        """构建错误结果。"""
        from app.resource.schemas import AgentResult

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.error("CartoonService 生成失败: error=%s elapsed_ms=%d", exc, elapsed_ms)
        return AgentResult(
            success=False,
            title=f"{learning_need} - 动画讲解视频",
            file_type="mp4",
            error=str(exc),
            metadata={
                "agent_id": "cartoon",
                "problems": exc.audit.problems if exc.audit else [],
            },
        )

    # =========================================================================
    # 文件路径解析（供独立 API 使用，按 task_id 查找）
    # =========================================================================

    def resolve_html(self, task_id: str) -> Path:
        """通过 task_id 解析 HTML 文件路径（向后兼容独立 API）。"""
        # task_id 格式可能是 "path-node-{node_id}" 或 UUID
        return WORKPLACE_DIR / "cartoon_video" / self._safe_id(task_id) / "index.html"

    def resolve_video(self, task_id: str) -> Path:
        """通过 task_id 解析视频文件路径（向后兼容独立 API）。"""
        output_dir = WORKPLACE_DIR / "cartoon_video" / self._safe_id(task_id)
        for name in ("output.mp4", "video.mp4"):
            candidate = output_dir / name
            if candidate.is_file():
                return candidate
        mp4_files = sorted(output_dir.rglob("*.mp4"))
        return mp4_files[0] if mp4_files else output_dir / "output.mp4"

    def resolve_markdown(self, task_id: str) -> Path:
        """通过 task_id 解析 Markdown 文件路径（向后兼容独立 API）。"""
        return WORKPLACE_DIR / "cartoon_video" / self._safe_id(task_id) / "theory_video.md"

    def resolve_audit(self, task_id: str) -> Path:
        """通过 task_id 解析审计文件路径（向后兼容独立 API）。"""
        return WORKPLACE_DIR / "cartoon_video" / self._safe_id(task_id) / "audit.json"

    # =========================================================================
    # 工具方法
    # =========================================================================

    @staticmethod
    def _safe_id(value: str) -> str:
        """安全化 ID 字符串。"""
        safe = "".join(ch for ch in str(value) if ch.isalnum() or ch in {"-", "_"})
        return safe[:80] if safe else "unknown"

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