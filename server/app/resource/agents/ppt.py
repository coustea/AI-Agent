"""PPT 智能体 — 内部多智能体流水线输出结构化 JSON。

输出格式为 PptPayload JSON，内部流水线：
  1. MaterialAgent — 素材提取
  2. OutlineAgent — 大纲规划（含前端模板合约）
  3. SlideAgent — 并发写页
  4. PayloadBuilder — 确定性载荷构建
"""

from __future__ import annotations

from pydantic import BaseModel

from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import WorkerResult, WorkerState

# Re-export all models from ppt_models so existing imports keep working:
#   from app.resource.agents.ppt import PptPayload, PptSlide, ...
from app.resource.agents.ppt_models import (  # noqa: F401
    ThemeType, LayoutType, BlockType,
    BaseBlock, BlockHeading, BlockText, BlockCallout, BlockCode,
    BlockBigNumber, BlockFormula, BlockTimeline, BlockTerminal,
    TimelineStep, SlideBlock,
    PptSlide, PptPayload,
    ResourceAgentId, SlideRole,
    MaterialArtifact, MaterialBundle, MaterialDigest,
    DeckConstraints, BlockContract, SlideContract, DeckOutline,
    RenderedBlock, SlideDraft,
)

logger = get_logger(__name__)


class PptConfig(BaseModel):
    template_id: ThemeType
    topic: str | None = None
    author: str | None = None
    date: str | None = None


@register_agent
class PptAgent(BaseResourceAgent):
    """PPT 生成 Agent — 内部多智能体流水线输出结构化 JSON。"""

    agent_id = "ppt"
    agent_name = "PPT 生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)

    async def run(self, state: WorkerState) -> WorkerResult:
        """PPT 生成主流程：素材提取 → 大纲规划 → 并发写页 → 载荷构建。"""
        if self.emitter:
            await self.emitter.emit_agent(self.agent_id, status="running", message="正在生成在线预览 PPT", progress=10)

        try:
            result = await self._execute(state)
        except Exception as exc:
            logger.error("PptAgent 生成异常: %s", exc, exc_info=True)
            if self.emitter:
                await self.emitter.emit_agent(self.agent_id, status="failed", message=f"PPT 生成异常: {exc}", progress=0)
            raise

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id,
                status="finished" if result.success else "failed",
                message=result.summary if result.success else (result.error or "PPT 生成失败"),
                progress=100 if result.success else 0,
            )
        return result

    async def _execute(self, state: WorkerState) -> WorkerResult:
        """核心生成逻辑：内部多智能体流水线 → 页数校验 → 序列化 JSON。"""
        from app.resource.agents.ppt_internal import (
            MaterialAgent, OutlineAgent, SlideAgent, write_slides_concurrently,
        )
        from app.resource.agents.ppt_builder import PayloadBuilder
        from app.resource.agents.ppt_sources import build_material_bundle
        from app.resource.agents.ppt_models import DeckConstraints, MaterialBundle

        config = state.agent_config or {}
        page_count = int(config.get("page_count") or config.get("slide_count") or 6)
        difficulty = config.get("difficulty") or "intermediate"

        # Parse or build MaterialBundle
        material_bundle_data = config.get("material_bundle")
        if material_bundle_data and isinstance(material_bundle_data, dict):
            bundle = MaterialBundle.model_validate(material_bundle_data)
        else:
            # Fallback: build minimal bundle from WorkerState for standalone/direct use
            bundle = build_material_bundle(
                learning_need=state.learning_need,
                learning_scenario=state.learning_scenario,
                profile=state.profile,
                blueprint=state.blueprint.model_dump(mode="json") if state.blueprint else None,
                instruction=state.instruction.model_dump(mode="json") if state.instruction else None,
            )

        # Map difficulty to DeckConstraints difficulty
        constraint_difficulty = difficulty
        if constraint_difficulty == "intermediate":
            constraint_difficulty = "normal"
        elif constraint_difficulty == "beginner":
            constraint_difficulty = "easy"
        elif constraint_difficulty == "advanced":
            constraint_difficulty = "hard"

        constraints = DeckConstraints(
            page_count=page_count,
            difficulty=constraint_difficulty,
        )

        logger.info(
            "PptAgent 启动内部流水线: page_count=%d difficulty=%s bundle_artifacts=%d",
            page_count, difficulty, len(bundle.artifacts),
        )

        # Phase 1: Material extraction
        if self.emitter:
            await self.emitter.emit_agent(self.agent_id, status="running", message="正在提取教学素材", progress=20)
        material_agent = MaterialAgent()
        digest = await material_agent.run(bundle)

        # Phase 2: Outline and template contract planning
        if self.emitter:
            await self.emitter.emit_agent(self.agent_id, status="running", message="正在规划 PPT 结构", progress=35)
        outline_agent = OutlineAgent()
        outline = await outline_agent.run(digest, constraints)

        # Phase 3: Concurrent slide writing
        if self.emitter:
            await self.emitter.emit_agent(self.agent_id, status="running", message="正在生成幻灯片内容", progress=50)
        slide_agent = SlideAgent()
        drafts = await write_slides_concurrently(slide_agent, outline, digest, concurrency=4)

        # Phase 4: Deterministic payload building
        if self.emitter:
            await self.emitter.emit_agent(self.agent_id, status="running", message="正在构建最终载荷", progress=85)
        payload_builder = PayloadBuilder()
        payload = payload_builder.build(outline, drafts)

        # Page count validation — preserve existing behavior
        actual_count = len(payload.slides)
        logger.info(
            "PptAgent 流水线完成: template_id=%s slides=%d layouts=%s",
            payload.template_id, actual_count,
            [s.layout for s in payload.slides[:3]],
        )

        if actual_count != page_count:
            error = f"PPT 页数与预期不符：期望 {page_count} 页，实际 {actual_count} 页"
            logger.warning(error)
            return WorkerResult(
                success=False,
                error=error,
                title=f"{state.learning_need[:32]} - PPT",
                summary=error,
                summary_data={"page_count": actual_count, "expected_page_count": page_count},
                metadata={
                    "engine": "ppt_json",
                    "agent_id": "ppt",
                    "delivery_mode": "preview",
                    "schema_version": "ppt/v2",
                    "template_id": payload.template_id,
                    "page_count": actual_count,
                    "expected_page_count": page_count,
                    "difficulty": difficulty,
                    "internal_pipeline": "material/outline/slides/payload",
                },
            )

        content = payload.model_dump_json(indent=2)
        return WorkerResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{state.learning_need[:32]} - PPT",
            summary=f"生成 {actual_count} 页在线预览 PPT",
            summary_data={"page_count": actual_count},
            metadata={
                "engine": "ppt_json",
                "agent_id": "ppt",
                "delivery_mode": "preview",
                "schema_version": "ppt/v2",
                "template_id": payload.template_id,
                "page_count": actual_count,
                "difficulty": difficulty,
                "internal_pipeline": "material/outline/slides/payload",
            },
        )
