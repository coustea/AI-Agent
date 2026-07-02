from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.config import WORKPLACE_DIR
from app.resource.agents.ppt_pipeline.author import HTMLAuthor
from app.resource.agents.ppt_pipeline.director import StyleDirector
from app.resource.agents.ppt_pipeline.planner import BriefPlanner
from app.resource.agents.ppt_pipeline.repair import RepairAgent
from app.resource.agents.ppt_pipeline.schemas import (
    DeckBrief,
    SourcePack,
    StaticAudit,
    StyleDecision,
    VisualAudit,
)
from app.resource.agents.ppt_pipeline.storage import PresentationPublisher
from app.resource.agents.ppt_pipeline.validator import StaticValidator
from app.resource.agents.ppt_pipeline.visual_qa import BrowserVisualQA


ProgressCallback = Callable[[str, int], Awaitable[None]]


class PresentationGenerationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        static_audit: StaticAudit,
        visual_audit: VisualAudit,
    ):
        super().__init__(message)
        self.static_audit = static_audit
        self.visual_audit = visual_audit


class PresentationArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Path
    brief: DeckBrief
    style: StyleDecision
    slide_count: int
    repaired: bool


class PresentationPipeline:
    def __init__(
        self,
        *,
        planner: BriefPlanner | None = None,
        director: StyleDirector | None = None,
        author: HTMLAuthor | None = None,
        validator: StaticValidator | None = None,
        visual_qa: BrowserVisualQA | None = None,
        repairer: RepairAgent | None = None,
        publisher: PresentationPublisher | None = None,
    ):
        self.planner = planner or BriefPlanner()
        self.director = director or StyleDirector()
        self.author = author or HTMLAuthor()
        self.validator = validator or StaticValidator()
        self.visual_qa = visual_qa or BrowserVisualQA()
        self.repairer = repairer or RepairAgent()
        self.publisher = publisher or PresentationPublisher(
            WORKPLACE_DIR / "html_slides"
        )

    async def generate(
        self,
        source_pack: SourcePack,
        *,
        file_id: str,
        progress: ProgressCallback | None = None,
    ) -> PresentationArtifact:
        await self._progress(progress, "正在规划演示叙事与内容密度...", 20)
        brief = await self.planner.plan(source_pack)

        await self._progress(progress, "正在比较三种视觉方向并选择风格...", 35)
        style = await self.director.direct(brief=brief, source_pack=source_pack)

        await self._progress(progress, "正在创作完整的单文件 HTML 演示文稿...", 55)
        html = await self.author.author(
            source_pack=source_pack,
            brief=brief,
            style=style,
        )

        await self._progress(progress, "正在执行结构与浏览器视觉验收...", 72)
        static_audit, visual_audit = await self._audit(html, brief)
        repaired = False
        if not static_audit.passed or not visual_audit.passed:
            repaired = True
            await self._progress(progress, "正在根据验收结果进行一次定向修复...", 84)
            html = await self.repairer.repair(
                html=html,
                brief=brief,
                style=style,
                static_audit=static_audit,
                visual_audit=visual_audit,
            )
            static_audit, visual_audit = await self._audit(html, brief)

        if not static_audit.passed or not visual_audit.passed:
            raise PresentationGenerationError(
                "presentation failed validation after one repair",
                static_audit=static_audit,
                visual_audit=visual_audit,
            )

        await self._progress(progress, "正在原子发布验收通过的 HTML 文件...", 95)
        path = self.publisher.publish(file_id, html)
        return PresentationArtifact(
            path=path,
            brief=brief,
            style=style,
            slide_count=static_audit.slide_count,
            repaired=repaired,
        )

    async def _audit(
        self,
        html: str,
        brief: DeckBrief,
    ) -> tuple[StaticAudit, VisualAudit]:
        static_audit = self.validator.validate(html, brief)
        if not static_audit.passed:
            return static_audit, VisualAudit(passed=False, problems=[])
        return static_audit, await self.visual_qa.audit(html, brief)

    @staticmethod
    async def _progress(
        callback: ProgressCallback | None,
        message: str,
        percent: int,
    ) -> None:
        if callback is not None:
            await callback(message, percent)
