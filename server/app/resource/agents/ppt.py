"""PPT 智能体 — 内部多智能体流水线输出结构化 JSON。

输出格式为 PptPayload JSON，内部流水线：
  1. MaterialAgent — 素材提取
  2. OutlineAgent — 大纲规划（含前端模板合约）
  3. SlideAgent — 并发写页
  4. PayloadBuilder — 确定性载荷构建
"""

from __future__ import annotations

from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import AgentResult, NodeInput, ResourceInput

# Re-export all models from ppt_models so existing imports keep working:
#   from app.resource.agents.ppt import PptPayload, PptSlide, ...
from app.resource.agents.ppt_models import (  # noqa: F401
    ThemeType, LayoutType, BlockType,
    BaseBlock, BlockHeading, BlockText, BlockCallout, BlockCode,
    BlockBigNumber, BlockFormula, BlockTimeline, BlockTerminal,
    TimelineStep, SlideBlock,
    PptSlide, PptPayload,
    ResourceAgentId, SlideRole,
    MaterialArtifact, MaterialBundle, MaterialDigest, NodeMaterialContext,
    DeckConstraints, BlockContract, SlideContract, DeckOutline,
    RenderedBlock, SlideDraft,
)

logger = get_logger(__name__)


@register_agent
class PptAgent(BaseResourceAgent):
    """PPT 生成 Agent — 内部多智能体流水线输出结构化 JSON。"""

    agent_id = "ppt"
    agent_name = "PPT 生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """多智能体场景：从 ResourceInput 构建素材 → 内部流水线。"""
        from app.resource.agents.ppt_sources import build_resource_material

        config = input_data.agent_config or {}
        material_bundle_data = config.get("material_bundle")
        if material_bundle_data and isinstance(material_bundle_data, dict):
            bundle = MaterialBundle.model_validate(material_bundle_data)
        else:
            bundle = build_resource_material(input_data)

        result = await self._run_pipeline(
            bundle=bundle,
            config=config,
            title_prefix=input_data.learning_need[:32],
        )
        await self.emit_finish(result)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        """路径节点场景：从 NodeInput 构建素材 → 内部流水线。"""
        from app.resource.agents.ppt_sources import build_node_material

        bundle = build_node_material(input_data)
        config = input_data.agent_config or {}
        # 路径节点场景用 node_title 作为标题前缀
        result = await self._run_pipeline(
            bundle=bundle,
            config=config,
            title_prefix=input_data.node_title,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.emit_finish(result)
        return result

    async def _run_pipeline(
        self,
        *,
        bundle: MaterialBundle,
        config: dict,
        title_prefix: str,
    ) -> AgentResult:
        """内部多智能体流水线：素材提取 → 大纲规划 → 并发写页 → 载荷构建。"""
        from app.resource.agents.ppt_internal import (
            MaterialAgent, OutlineAgent, SlideAgent, write_slides_concurrently,
        )
        from app.resource.agents.ppt_builder import PayloadBuilder
        from app.resource.agents.ppt_models import DeckConstraints

        page_count = int(config.get("page_count") or config.get("slide_count") or 6)
        difficulty = config.get("difficulty") or "intermediate"

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
            "PptAgent 启动内部流水线: page_count=%d difficulty=%s bundle_artifacts=%d source_type=%s",
            page_count, difficulty, len(bundle.artifacts), bundle.source_type,
        )

        try:
            # Phase 1: Material extraction
            await self.emit_start("正在提取教学素材", progress=20)
            material_agent = MaterialAgent()
            digest = await material_agent.run(bundle)

            # Phase 2: Outline and template contract planning
            await self.emit_start("正在规划 PPT 结构", progress=35)
            outline_agent = OutlineAgent()
            outline = await outline_agent.run(digest, constraints)

            # Phase 3: Concurrent slide writing
            await self.emit_start("正在生成幻灯片内容", progress=50)
            slide_agent = SlideAgent()
            drafts = await write_slides_concurrently(slide_agent, outline, digest, concurrency=4)

            # Phase 4: Deterministic payload building
            await self.emit_start("正在构建最终载荷", progress=85)
            payload_builder = PayloadBuilder()
            payload = payload_builder.build(outline, drafts)

        except Exception as exc:
            logger.error("PptAgent 生成异常: %s", exc, exc_info=True)
            return AgentResult(
                success=False,
                error=str(exc),
                title=f"{title_prefix} - PPT",
                summary=f"PPT 生成异常: {exc}",
                metadata={
                    "engine": "ppt_json",
                    "agent_id": "ppt",
                    "delivery_mode": "preview",
                    "schema_version": "ppt/v2",
                    "difficulty": difficulty,
                    "internal_pipeline": "material/outline/slides/payload",
                },
            )

        # Page count validation
        actual_count = len(payload.slides)
        logger.info(
            "PptAgent 流水线完成: template_id=%s slides=%d layouts=%s",
            payload.template_id, actual_count,
            [s.layout for s in payload.slides[:3]],
        )

        if actual_count != page_count:
            error = f"PPT 页数与预期不符：期望 {page_count} 页，实际 {actual_count} 页"
            logger.warning(error)
            return AgentResult(
                success=False,
                error=error,
                title=f"{title_prefix} - PPT",
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
        return AgentResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{title_prefix} - PPT",
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
