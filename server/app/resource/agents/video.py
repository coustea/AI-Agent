"""Video resource agent.

Single-file implementation by design:
  1. VideoMaterialAgent extracts material from upstream resources.
  2. VideoOutlineAgent plans scene contracts.
  3. SceneWriterAgent writes scenes concurrently.
  4. VideoPayloadBuilder constructs validated preview JSON.
"""

from __future__ import annotations

import asyncio
import json
import operator
from typing import Any, Annotated, Literal, Union, TypedDict

from pydantic import BaseModel, Field, model_validator
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import outline_coverage_summary
from app.resource.schemas import AgentResult, NodeInput, ResourceInput

logger = get_logger(__name__)

VideoStyle = Literal["explainer", "lecture", "screencast", "case_walkthrough"]
VideoVoice = Literal["teacher", "coach", "concise"]
AspectRatio = Literal["16:9", "9:16", "1:1"]
SceneRole = Literal["hook", "concept", "example", "process", "misconception", "practice", "recap"]
VisualType = Literal["card", "diagram", "code", "screencast", "timeline", "comparison", "quiz"]


class VideoConstraints(BaseModel):
    duration_seconds: int = Field(default=180, ge=60, le=600)
    scene_count: int = Field(default=6, ge=3, le=12)
    style: VideoStyle = "explainer"
    voice: VideoVoice = "teacher"
    aspect_ratio: AspectRatio = "16:9"
    include_captions: bool = True
    output_format: Literal["preview"] = "preview"


class VideoMaterialDigest(BaseModel):
    topic: str
    audience: str = ""
    learning_goal: str = ""
    core_concepts: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    process_steps: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    practice_prompts: list[str] = Field(default_factory=list)
    visual_opportunities: list[str] = Field(default_factory=list)
    source_map: dict[str, list[str]] = Field(default_factory=dict)


class SceneContract(BaseModel):
    scene_id: str
    index: int = Field(ge=1)
    role: SceneRole
    title: str
    duration_seconds: int = Field(ge=10)
    learning_objective: str
    visual_type: VisualType = "card"
    content_hint: str
    required_sources: list[str] = Field(default_factory=list)


class VideoOutline(BaseModel):
    title: str
    topic: str
    duration_seconds: int = Field(ge=60)
    style: VideoStyle = "explainer"
    aspect_ratio: AspectRatio = "16:9"
    narrative: str = ""
    scenes: list[SceneContract]

    @model_validator(mode="after")
    def validate_outline(self) -> "VideoOutline":
        if not self.scenes:
            raise ValueError("video outline must contain scenes")
        indexes = [scene.index for scene in self.scenes]
        if indexes != list(range(1, len(self.scenes) + 1)):
            raise ValueError("scene indexes must be contiguous from 1")
        if self.scenes[0].role != "hook":
            raise ValueError("first scene role must be hook")
        if self.scenes[-1].role != "recap":
            raise ValueError("last scene role must be recap")
        total = sum(scene.duration_seconds for scene in self.scenes)
        if total != self.duration_seconds:
            raise ValueError("scene durations must equal video duration_seconds")
        return self


class SceneDraft(BaseModel):
    scene_id: str
    index: int = Field(ge=1)
    title: str
    narration: str
    captions: list[str] = Field(default_factory=list)
    on_screen_text: list[str] = Field(default_factory=list)
    visual_prompt: str
    visual_type: VisualType = "card"
    interaction_prompt: str = ""
    visual: dict[str, Any] = Field(default_factory=dict)
    source_agents: list[str] = Field(default_factory=list)
    audio_src: str | None = None
    duration_ms: int = 0



class VideoAsset(BaseModel):
    asset_id: str
    type: Literal["image_prompt", "diagram_prompt", "code", "text"]
    description: str
    source_scene_id: str


class VideoScene(BaseModel):
    scene_id: str
    index: int = Field(ge=1)
    role: SceneRole
    title: str
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)
    visual_type: VisualType = "card"
    narration: str
    captions: list[str] = Field(default_factory=list)
    on_screen_text: list[str] = Field(default_factory=list)
    visual_prompt: str
    interaction_prompt: str = ""
    visual: dict[str, Any] = Field(default_factory=dict)
    source_agents: list[str] = Field(default_factory=list)
    audio_src: str | None = None



class VideoPayload(BaseModel):
    schema_version: Literal["video/v1"] = "video/v1"
    title: str
    topic: str
    duration_seconds: int = Field(ge=60)
    aspect_ratio: AspectRatio = "16:9"
    style: VideoStyle = "explainer"
    voice: VideoVoice = "teacher"
    language: str = "zh-CN"
    scenes: list[VideoScene]
    assets: list[VideoAsset] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_payload(self) -> "VideoPayload":
        indexes = [scene.index for scene in self.scenes]
        if indexes != list(range(1, len(self.scenes) + 1)):
            raise ValueError("scene indexes must be contiguous from 1")
        expected_start = 0
        for scene in self.scenes:
            if scene.start_ms != expected_start:
                raise ValueError("scene timings must be contiguous")
            expected_start += scene.duration_ms
        if expected_start != self.duration_seconds * 1000:
            raise ValueError("scene timings must equal video duration_seconds")
        return self


def _safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _result_excerpt(result: AgentResult, limit: int = 4000) -> dict[str, Any]:
    content = result.content or ""
    if len(content) > limit:
        content = f"{content[:limit]}\n\n[内容已截断]"
    return {
        "title": result.title,
        "summary": result.summary,
        "file_type": result.file_type,
        "content": content,
        "metadata": result.metadata,
    }


VIDEO_SOURCE_AGENT_IDS = {"content", "mindmap", "quiz", "code", "reading"}


def _input_context(input_data: ResourceInput, config: dict[str, Any]) -> dict[str, Any]:
    handoffs = {
        agent_id: handoff.model_dump(mode="json")
        for agent_id, handoff in input_data.upstream_handoffs.items()
        if agent_id in VIDEO_SOURCE_AGENT_IDS
    }
    return {
        "learning_need": input_data.learning_need,
        "learning_scenario": input_data.learning_scenario,
        "profile": input_data.profile,
        "teaching_plan": input_data.teaching_plan.model_dump(mode="json") if input_data.teaching_plan else {},
        "upstream_handoffs": handoffs,
        "config": config,
    }


class VideoMaterialAgent:
    async def run(self, input_data: ResourceInput, config: dict[str, Any]) -> VideoMaterialDigest:
        context = _input_context(input_data, config)
        fallback_topic = input_data.teaching_plan.topic if input_data.teaching_plan else input_data.learning_need
        if not context["upstream_handoffs"]:
            return VideoMaterialDigest(
                topic=fallback_topic,
                audience="自学学习者",
                learning_goal=input_data.learning_need,
                facts=[input_data.learning_need],
                visual_opportunities=["标题卡片"],
                source_map={"facts": ["learning_need"]},
            )

        prompt = prompts.get("resource").get("video_material")
        message = f"{prompt}\n\n输入 JSON:\n{_safe_json(context)}"
        from app.infra.llm import get_llm

        llm = get_llm()
        return await llm.ainvoke_json(VideoMaterialDigest, message)


def _duration_plan(total: int, count: int) -> list[int]:
    base = total // count
    durations = [base for _ in range(count)]
    durations[-1] += total - sum(durations)
    return durations


class VideoOutlineAgent:
    async def run(self, digest: VideoMaterialDigest, constraints: VideoConstraints) -> VideoOutline:
        if not digest.core_concepts and not digest.facts:
            durations = _duration_plan(constraints.duration_seconds, constraints.scene_count)
            scenes = [
                SceneContract(scene_id=f"scene-{idx}", index=idx, role="hook" if idx == 1 else "recap" if idx == constraints.scene_count else "concept", title=f"{digest.topic} {idx}", duration_seconds=durations[idx - 1], learning_objective=digest.learning_goal or digest.topic, visual_type="card", content_hint=digest.topic, required_sources=["learning_need"])
                for idx in range(1, constraints.scene_count + 1)
            ]
            return VideoOutline(title=f"{digest.topic}讲解", topic=digest.topic, duration_seconds=constraints.duration_seconds, style=constraints.style, aspect_ratio=constraints.aspect_ratio, narrative=digest.learning_goal, scenes=scenes)

        prompt = prompts.get("resource").get("video_outline")
        payload = {"digest": digest.model_dump(mode="json"), "constraints": constraints.model_dump(mode="json")}
        message = f"{prompt}\n\n输入 JSON:\n{_safe_json(payload)}"
        from app.infra.llm import get_llm

        llm = get_llm()
        return await llm.ainvoke_json(VideoOutline, message)


class SceneWriterAgent:
    async def run(self, contract: SceneContract, digest: VideoMaterialDigest, constraints: VideoConstraints) -> SceneDraft:
        prompt = prompts.get("resource").get("video_scene")
        payload = {
            "digest": digest.model_dump(mode="json"),
            "scene_contract": contract.model_dump(mode="json"),
            "constraints": constraints.model_dump(mode="json"),
        }
        message = f"{prompt}\n\n输入 JSON:\n{_safe_json(payload)}"
        from app.infra.llm import get_llm

        llm = get_llm()
        return await llm.ainvoke_json(SceneDraft, message)




class VideoPayloadBuilder:
    def build(
        self,
        outline: VideoOutline,
        drafts: list[SceneDraft],
        constraints: VideoConstraints,
        digest: VideoMaterialDigest,
    ) -> VideoPayload:
        draft_by_id = {draft.scene_id: draft for draft in drafts}
        scenes: list[VideoScene] = []
        cursor_ms = 0
        for contract in outline.scenes:
            draft = draft_by_id[contract.scene_id]
            # Use generated duration_ms or fallback to contract planned duration
            duration_ms = getattr(draft, "duration_ms", 0) or (contract.duration_seconds * 1000)
            scenes.append(
                VideoScene(
                    scene_id=contract.scene_id,
                    index=contract.index,
                    role=contract.role,
                    title=draft.title or contract.title,
                    start_ms=cursor_ms,
                    duration_ms=duration_ms,
                    visual_type=draft.visual_type,
                    narration=draft.narration,
                    captions=draft.captions if constraints.include_captions else [],
                    on_screen_text=draft.on_screen_text,
                    visual_prompt=draft.visual_prompt,
                    interaction_prompt=draft.interaction_prompt,
                    visual=draft.visual or {},
                    audio_src=draft.audio_src,
                    source_agents=draft.source_agents or contract.required_sources,
                )
            )
            cursor_ms += duration_ms

        # Adjust total duration and last scene padding to satisfy model validators
        total_ms = cursor_ms
        duration_seconds = (total_ms + 999) // 1000
        target_total_ms = duration_seconds * 1000
        diff_ms = target_total_ms - total_ms
        
        if scenes and diff_ms > 0:
            scenes[-1].duration_ms += diff_ms
            
        # Re-align contiguous start times
        expected_start = 0
        for scene in scenes:
            scene.start_ms = expected_start
            expected_start += scene.duration_ms

        source_agent_ids = sorted({agent for scene in scenes for agent in scene.source_agents})
        return VideoPayload(
            title=outline.title,
            topic=outline.topic or digest.topic,
            duration_seconds=duration_seconds,
            aspect_ratio=constraints.aspect_ratio,
            style=constraints.style,
            voice=constraints.voice,
            scenes=scenes,
            assets=[
                VideoAsset(
                    asset_id=f"asset-{scene.index}",
                    type="diagram_prompt" if scene.visual_type in {"diagram", "timeline", "comparison"} else "image_prompt",
                    description=scene.visual_prompt,
                    source_scene_id=scene.scene_id,
                )
                for scene in scenes
            ],
            metadata={
                "source_agent_ids": source_agent_ids,
                "internal_pipeline": "material/outline/scenes/payload",
                "delivery_mode": "preview",
            },
        )


class VideoSceneWriteState(TypedDict):
    contract: SceneContract
    digest: VideoMaterialDigest
    constraints: VideoConstraints
    resource_id: int | None


def _add_scene_drafts(left: list[SceneDraft] | None, right: list[SceneDraft] | None) -> list[SceneDraft]:
    if left is None:
        left = []
    if right is None:
        right = []
    return left + right


class VideoGraphState(TypedDict, total=False):
    # Inputs
    input_data: ResourceInput
    config: dict[str, Any]
    constraints: VideoConstraints

    # Intermediate artifacts
    digest: VideoMaterialDigest
    outline: VideoOutline
    drafts: Annotated[list[SceneDraft], _add_scene_drafts]

    # Final outputs
    payload: VideoPayload
    error: str


@register_agent
class VideoAgent(BaseResourceAgent):
    """Video 生成 Agent。输出结构化预览 JSON，不渲染二进制视频。"""

    agent_id = "video"
    agent_name = "讲解视频"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self._scene_semaphore = asyncio.Semaphore(4)

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        config = input_data.agent_config or {}
        title_prefix = input_data.learning_need[:32]
        result = await self._run_pipeline(
            input_data=input_data,
            config=config,
            title_prefix=title_prefix,
        )
        if result.success:
            coverage = outline_coverage_summary(input_data.teaching_plan, input_data.upstream_handoffs)
            result.metadata["teaching_plan_outline_ids"] = coverage["teaching_plan_outline_ids"]
            result.metadata["covered_source_outline_ids"] = coverage["covered_source_outline_ids"]
            result.metadata["missing_source_outline_ids"] = coverage["missing_source_outline_ids"]
        await self.emit_finish(result)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        """路径节点场景：从 NodeInput 构建素材并执行嵌套子图。"""
        from app.resource.schemas import DownstreamContext, DownstreamMaterial, ReusableAssets

        content_materials = []
        if input_data.tutorial_markdown:
            content_materials.append(
                DownstreamMaterial(
                    outline_id="node-outline-1",
                    type="explanation",
                    summary=input_data.tutorial_markdown[:450] + "...",
                    key_points=input_data.knowledge_points[:8] if input_data.knowledge_points else [],
                )
            )

        mock_handoffs = {
            "content": DownstreamContext(
                source_agent="content",
                title=input_data.node_title,
                one_sentence_summary=input_data.tutorial_summary or f"关于 {input_data.node_title} 的学习教程",
                materials=content_materials,
                reusable_assets=ReusableAssets(
                    examples=[f"学习侧重点：{focus}" for focus in input_data.generation_focus] if input_data.generation_focus else [],
                    visual_ideas=input_data.knowledge_points or [],
                ),
            )
        }

        resource_input = ResourceInput(
            learning_need=input_data.node_title,
            learning_scenario="path_learning",
            profile=input_data.profile or {},
            agent_name="video",
            agent_config=input_data.agent_config or {},
            upstream_handoffs=mock_handoffs,
        )

        result = await self._run_pipeline(
            input_data=resource_input,
            config=resource_input.agent_config,
            title_prefix=input_data.node_title,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.emit_finish(result)
        return result

    def _build_graph(self) -> Any:
        if not hasattr(self, "_cached_graph"):
            workflow = StateGraph(VideoGraphState)

            workflow.add_node("extract_material", self._material_node)
            workflow.add_node("plan_outline", self._outline_node)
            workflow.add_node("write_scene", self._write_scene_node)
            workflow.add_node("build_payload", self._payload_node)

            workflow.add_edge(START, "extract_material")
            workflow.add_edge("extract_material", "plan_outline")
            workflow.add_conditional_edges("plan_outline", self._route_scenes, ["write_scene"])
            workflow.add_edge("write_scene", "build_payload")
            workflow.add_edge("build_payload", END)

            self._cached_graph = workflow.compile()
        return self._cached_graph

    async def _material_node(self, state: VideoGraphState) -> dict[str, Any]:
        await self.emit_start("正在提取视频素材", progress=20)
        digest = await VideoMaterialAgent().run(state["input_data"], state["config"])
        return {"digest": digest}

    async def _outline_node(self, state: VideoGraphState) -> dict[str, Any]:
        await self.emit_start("正在规划视频结构", progress=35)
        outline = await VideoOutlineAgent().run(state["digest"], state["constraints"])
        if len(outline.scenes) != state["constraints"].scene_count:
            raise ValueError(
                f"视频场景数与预期不符：期望 {state['constraints'].scene_count}，实际 {len(outline.scenes)}"
            )
        return {"outline": outline}

    def _route_scenes(self, state: VideoGraphState) -> list[Send]:
        outline: VideoOutline = state["outline"]
        digest: VideoMaterialDigest = state["digest"]
        constraints: VideoConstraints = state["constraints"]
        resource_id = state["input_data"].resource_id if "input_data" in state and hasattr(state["input_data"], "resource_id") else None
        return [
            Send("write_scene", {
                "contract": scene,
                "digest": digest,
                "constraints": constraints,
                "resource_id": resource_id,
            })
            for scene in outline.scenes
        ]

    async def _write_scene_node(self, state: VideoSceneWriteState) -> dict[str, Any]:
        async with self._scene_semaphore:
            writer = SceneWriterAgent()
            draft = await writer.run(state["contract"], state["digest"], state["constraints"])
            
            # Synthesize TTS
            from app.resource.infra.tts import TtsService
            from app.config import WORKPLACE_DIR
            
            res_id = state.get("resource_id")
            prefix = f"res_{res_id}" if res_id else f"digest_{abs(hash(state['digest'].topic)) % 10000}"
            filename = f"{prefix}_scene_{draft.scene_id}.mp3"
            file_path = WORKPLACE_DIR / "video_audio" / filename
            
            try:
                duration_s = await TtsService.synthesize(draft.narration, file_path)
                # Add 500ms safety buffer, but keep a minimum of 4 seconds
                draft.duration_ms = max(int(duration_s * 1000) + 500, 4000)
                draft.audio_src = f"/api/v1/ai/video/audio/{filename}"
            except Exception as e:
                logger.error("TTS synthesis failed for scene %s: %s", draft.scene_id, e)
                # Fallback to contract planned duration
                draft.duration_ms = state["contract"].duration_seconds * 1000
                draft.audio_src = None
                
            return {"drafts": [draft]}

    async def _payload_node(self, state: VideoGraphState) -> dict[str, Any]:
        await self.emit_start("正在构建视频预览载荷", progress=85)
        payload = VideoPayloadBuilder().build(
            state["outline"], state["drafts"], state["constraints"], state["digest"]
        )
        return {"payload": payload}

    async def _run_pipeline(
        self,
        *,
        input_data: ResourceInput,
        config: dict,
        title_prefix: str,
    ) -> AgentResult:
        constraints = VideoConstraints.model_validate(config)
        try:
            graph = self._build_graph()
            initial_state = VideoGraphState(
                input_data=input_data,
                config=config,
                constraints=constraints,
                drafts=[],
            )
            final_state = await graph.ainvoke(initial_state)
            payload = final_state.get("payload")
            if not payload:
                raise ValueError("Video generation graph failed to build final payload")
        except Exception as exc:
            logger.error("VideoAgent 生成异常: %s", exc, exc_info=True)
            return AgentResult(
                success=False,
                error=str(exc),
                title=f"{title_prefix} - 视频",
                summary=f"视频生成异常: {exc}",
                metadata={
                    "engine": "video_json",
                    "agent_id": "video",
                    "schema_version": "video/v1",
                    "delivery_mode": "preview",
                    "internal_pipeline": "material/outline/scenes/payload",
                },
            )

        content = payload.model_dump_json(indent=2)
        source_handoff_agent_ids = sorted(input_data.upstream_handoffs.keys()) if input_data.upstream_handoffs else sorted({agent for scene in payload.scenes for agent in scene.source_agents})
        return AgentResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{title_prefix} - 视频",
            summary=f"生成 {len(payload.scenes)} 段结构化讲解视频脚本",
            metrics={
                "scene_count": len(payload.scenes),
                "duration_seconds": payload.duration_seconds,
            },
            metadata={
                "engine": "video_json",
                "agent_id": "video",
                "schema_version": "video/v1",
                "delivery_mode": "preview",
                "duration_seconds": payload.duration_seconds,
                "scene_count": len(payload.scenes),
                "aspect_ratio": payload.aspect_ratio,
                "style": payload.style,
                "source_handoff_agent_ids": source_handoff_agent_ids,
                "internal_pipeline": "material/outline/scenes/payload",
            },
        )

    async def generate_from_tutor_context(self, tutor_context: dict[str, Any]) -> AgentResult:
        """Reserved tutor-facing adapter. Not wired to chat or tutor routes yet."""
        learning_need = str(
            tutor_context.get("learning_need")
            or tutor_context.get("question")
            or tutor_context.get("topic")
            or ""
        ).strip()
        if not learning_need:
            return AgentResult(
                success=False,
                error="tutor_context 缺少 learning_need/question/topic",
                metadata={"agent_id": "video", "reserved_for_tutor": True},
            )
        from app.resource.schemas import DownstreamContext
        raw_handoffs = tutor_context.get("upstream_handoffs") or {}
        normalized_handoffs: dict[str, DownstreamContext] = {}
        for agent_id, value in raw_handoffs.items():
            if isinstance(value, DownstreamContext):
                normalized_handoffs[agent_id] = value
            elif isinstance(value, dict):
                try:
                    normalized_handoffs[agent_id] = DownstreamContext.model_validate(value)
                except Exception:
                    pass
        return await self.generate_resource(
            ResourceInput(
                learning_need=learning_need,
                learning_scenario=tutor_context.get("learning_scenario") or "self_study",
                agent_name="video",
                agent_config=tutor_context.get("agent_config") if isinstance(tutor_context.get("agent_config"), dict) else {},
                profile=tutor_context.get("profile") if isinstance(tutor_context.get("profile"), dict) else {},
                upstream_handoffs=normalized_handoffs,
            )
        )
