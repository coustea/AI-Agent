from __future__ import annotations

from pathlib import Path

import pytest

from app.shared.video.agent import VideoAgent
from app.shared.video.schemas import (
    AudioSynthesis,
    CaptionWord,
    SceneContract,
    SceneDraft,
    SourceMaterial,
    VideoArtifact,
    VideoMaterialDigest,
    VideoOutline,
    VideoRequest,
    VideoStyleDecision,
    VisualBeatDraft,
)


class FakeMaterialAgent:
    async def extract(self, request: VideoRequest) -> VideoMaterialDigest:
        return VideoMaterialDigest(
            topic=request.topic,
            core_concepts=["进程", "状态转换"],
            source_map={"content": ["进程定义"]},
        )


class FakeDirector:
    async def plan(
        self,
        request: VideoRequest,
        digest: VideoMaterialDigest,
    ) -> VideoOutline:
        style = VideoStyleDecision(id="systems_dark", rationale="系统状态主题")
        roles = ["hook", "concept", "recap"]
        return VideoOutline(
            title="进程基础",
            topic=request.topic,
            narrative="从运行现象理解进程状态",
            style=style,
            scenes=[
                SceneContract(
                    scene_id=f"scene-{index}",
                    index=index,
                    role=role,
                    title=f"场景 {index}",
                    learning_objective="理解进程状态",
                    visual_type="concept_explain",
                    content_hint="解释进程定义",
                    source_ids=["content"],
                )
                for index, role in enumerate(roles, start=1)
            ],
        )


class FakeSceneWriter:
    async def write(self, *, request, digest, contract, style) -> SceneDraft:
        narration = f"第{contract.index}幕解释进程状态。"
        return SceneDraft(
            scene_id=contract.scene_id,
            index=contract.index,
            title=contract.title,
            narration=narration,
            visual_type=contract.visual_type,
            visual={"main_concept": "进程", "definition": narration},
            visual_beats=[
                VisualBeatDraft(
                    id=f"beat-{contract.index}",
                    kind="define",
                    target="definition",
                    text_anchor=narration,
                    summary="显示定义",
                )
            ],
        )


class FakeTts:
    async def synthesize(self, text: str, output_path: Path, voice: str) -> AudioSynthesis:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake mp3")
        return AudioSynthesis(
            path=output_path,
            duration_ms=2000,
            words=[CaptionWord(text=text, start_ms=0, end_ms=2000)],
        )


class FakeRenderer:
    def __init__(self) -> None:
        self.received_schema_version = ""

    async def render(self, plan, output_dir: Path) -> VideoArtifact:
        self.received_schema_version = plan.schema_version
        output = output_dir / "video.mp4"
        output.write_bytes(b"fake mp4")
        return VideoArtifact(
            plan=plan,
            mp4_path=output,
            public_url="/static/videos/job/video.mp4",
            duration_ms=plan.duration_ms,
            width=plan.render.width,
            height=plan.render.height,
            size_bytes=output.stat().st_size,
        )


@pytest.mark.asyncio
async def test_shared_video_agent_builds_audio_driven_plan_and_renders_mp4(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.shared.video.agent.WORKPLACE_DIR", tmp_path)
    renderer = FakeRenderer()
    agent = VideoAgent(
        material_agent=FakeMaterialAgent(),
        director=FakeDirector(),
        scene_writer=FakeSceneWriter(),
        tts=FakeTts(),
        renderer=renderer,
        tail_padding_ms=400,
    )
    request = VideoRequest(
        topic="操作系统进程",
        scene_count=3,
        materials=[
            SourceMaterial(
                source_id="content",
                source_type="course",
                content="进程是程序的一次执行过程。",
            )
        ],
        output_dir=tmp_path,
    )

    artifact = await agent.generate(request)

    assert renderer.received_schema_version == "video/v2"
    assert artifact.mp4_path.exists()
    assert [scene.start_ms for scene in artifact.plan.scenes] == [0, 2400, 4800]
    assert all(scene.duration_ms == 2400 for scene in artifact.plan.scenes)
    assert all(scene.captions[-1].end_ms == 2000 for scene in artifact.plan.scenes)
    assert all(scene.visual_cues[-1].end_ms == 2000 for scene in artifact.plan.scenes)
