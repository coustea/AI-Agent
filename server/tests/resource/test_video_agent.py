import json
import os
import ssl
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.resource.schemas import AgentResult, DownstreamContext, ResourceInput


def _valid_payload_dict():
    return {
        "schema_version": "video/v1",
        "title": "TCP 三次握手讲解",
        "topic": "TCP 三次握手",
        "duration_seconds": 180,
        "aspect_ratio": "16:9",
        "style": "explainer",
        "voice": "teacher",
        "language": "zh-CN",
        "scenes": [
            {
                "scene_id": "scene-1",
                "index": 1,
                "role": "hook",
                "title": "为什么连接需要三次确认",
                "start_ms": 0,
                "duration_ms": 30000,
                "visual_type": "title_intro",
                "narration": "如果只握手两次，历史报文可能让服务端误以为连接成立。",
                "captions": ["两次握手无法排除历史报文"],
                "on_screen_text": ["问题：为什么不是两次？"],
                "visual_prompt": "白底信息卡展示客户端和服务端的连接疑问",
                "interaction_prompt": "暂停 3 秒，让学习者先回答。",
                "visual": {"course": "计算机网络", "chapter": "传输层", "subtitle": "TCP连接建立"},
                "audio_src": "/static/videos/res_1/scene_scene-1.mp3",
                "source_agents": ["content"],
            },
            {
                "scene_id": "scene-2",
                "index": 2,
                "role": "concept",
                "title": "SYN、SYN+ACK、ACK",
                "start_ms": 30000,
                "duration_ms": 60000,
                "visual_type": "concept_explain",
                "narration": "客户端发送 SYN，服务端回复 SYN 加 ACK，客户端再确认 ACK。",
                "captions": ["SYN", "SYN+ACK", "ACK"],
                "on_screen_text": ["三次握手时序"],
                "visual_prompt": "左右两列分别是客户端和服务端，中间用三条箭头展示报文顺序",
                "interaction_prompt": "",
                "visual": {"main_concept": "三次握手", "definition": "TCP连接建立过程"},
                "audio_src": "/static/videos/res_1/scene_scene-2.mp3",
                "source_agents": ["content", "mindmap"],
            },
            {
                "scene_id": "scene-3",
                "index": 3,
                "role": "recap",
                "title": "总结",
                "start_ms": 90000,
                "duration_ms": 90000,
                "visual_type": "compare_summary",
                "narration": "三次握手的本质，是在不可靠网络里确认双方收发能力和初始序号。",
                "captions": ["确认双方收发能力", "同步初始序号"],
                "on_screen_text": ["结论：可靠连接从状态同步开始"],
                "visual_prompt": "总结卡片列出两个关键词：收发能力、序号同步",
                "interaction_prompt": "请用一句话解释第三次 ACK 的意义。",
                "visual": {"comparison_title": "总结", "conclusion": "可靠连接从状态同步开始"},
                "audio_src": "/static/videos/res_1/scene_scene-3.mp3",
                "source_agents": ["content"],
            },
        ],
        "assets": [],
        "metadata": {"source_agent_ids": ["content", "mindmap"]},
    }


def test_video_payload_validates_scene_timings():
    from app.resource.agents.video import VideoPayload

    payload = VideoPayload.model_validate(_valid_payload_dict())

    assert payload.schema_version == "video/v1"
    assert payload.scenes[0].start_ms == 0
    assert payload.scenes[-1].start_ms + payload.scenes[-1].duration_ms == 180_000


def test_video_payload_rejects_non_contiguous_timings():
    from app.resource.agents.video import VideoPayload

    payload = _valid_payload_dict()
    payload["scenes"][1]["start_ms"] = 45000

    with pytest.raises(ValidationError, match="contiguous"):
        VideoPayload.model_validate(payload)


def test_video_payload_rejects_caption_word_after_audio_end():
    from app.resource.agents.video import VideoPayload

    payload = _valid_payload_dict()
    payload["scenes"][0]["audio_duration_ms"] = 29_000
    payload["scenes"][0]["caption_words"] = [
        {"text": "尾部字幕", "start_ms": 28_500, "end_ms": 29_500}
    ]

    with pytest.raises(ValidationError, match="caption word timing exceeds audio duration"):
        VideoPayload.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "timed_item", "message"),
    [
        (
            "caption_chunks",
            {"text": "尾部字幕", "start_ms": 28_500, "end_ms": 29_500},
            "caption chunk timing exceeds audio duration",
        ),
        (
            "visual_cues",
            {
                "id": "late-cue",
                "kind": "recap",
                "start_ms": 28_500,
                "end_ms": 29_500,
            },
            "visual cue timing exceeds audio duration",
        ),
    ],
)
def test_video_payload_rejects_timed_content_after_audio_end(
    field, timed_item, message
):
    from app.resource.agents.video import VideoPayload

    payload = _valid_payload_dict()
    payload["scenes"][0]["audio_duration_ms"] = 29_000
    payload["scenes"][0][field] = [timed_item]

    with pytest.raises(ValidationError, match=message):
        VideoPayload.model_validate(payload)


def test_align_visual_cues_preserves_matched_anchor_when_another_anchor_fails():
    from app.resource.agents.video import (
        CaptionChunk,
        CaptionWord,
        VisualBeatDraft,
        align_visual_cues,
    )

    words = [
        CaptionWord(text="进程", start_ms=1_000, end_ms=1_500),
        CaptionWord(text="是", start_ms=1_500, end_ms=1_700),
        CaptionWord(text="程序", start_ms=1_700, end_ms=2_200),
    ]
    chunks = [CaptionChunk(text="进程是程序", start_ms=1_000, end_ms=2_200)]
    beats = [
        VisualBeatDraft(
            id="definition",
            kind="define",
            target="main_concept",
            text_anchor="进程是程序",
        ),
        VisualBeatDraft(
            id="example",
            kind="example",
            target="example",
            text_anchor="这个锚点不存在",
        ),
    ]

    cues = align_visual_cues(beats, words, chunks, audio_duration_ms=10_000)

    assert cues[0].id == "definition"
    assert cues[0].start_ms == 1_000
    assert cues[1].id == "example"
    assert cues[1].start_ms > cues[0].start_ms
    assert cues[-1].end_ms == 10_000


def test_spark_tts_ssl_context_verifies_server_certificate():
    from app.resource.infra.spark_tts import create_ssl_context

    context = create_ssl_context()

    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED


def test_spark_tts_estimated_captions_preserve_sentence_punctuation():
    from app.resource.infra.spark_tts import SparkTtsService

    captions = SparkTtsService._estimate_captions("进程开始。然后等待！", duration=8.0)

    assert "".join(caption.text for caption in captions) == "进程开始。然后等待！"
    assert captions[0].start_ms == 0
    assert captions[-1].end_ms == 8_000
    assert all(
        current.end_ms == following.start_ms
        for current, following in zip(captions, captions[1:])
    )


@pytest.mark.asyncio
async def test_video_agent_generates_json_from_previous_results(monkeypatch):
    from app.resource.agents import AGENT_REGISTRY
    from app.resource.agents.video import (
        SceneDraft,
        SceneWriterAgent,
        VideoAgent,
        VideoMaterialAgent,
        VideoMaterialDigest,
        VideoOutline,
        VideoOutlineAgent,
        SceneContract,
    )

    async def fake_material_run(self, input_data, config):
        return VideoMaterialDigest(
            topic="TCP 三次握手",
            audience="计算机网络学习者",
            learning_goal="理解三次握手的必要性",
            core_concepts=["SYN", "ACK", "状态同步"],
            facts=["三次握手同步双方初始序号"],
            examples=["历史 SYN 报文可能导致误连接"],
            process_steps=["SYN", "SYN+ACK", "ACK"],
            misconceptions=["两次握手已经足够"],
            practice_prompts=["解释第三次 ACK 的意义"],
            visual_opportunities=["时序图"],
            source_map={"facts": ["content"]},
        )

    async def fake_outline_run(self, digest, constraints):
        return VideoOutline(
            title="TCP 三次握手讲解",
            topic=digest.topic,
            duration_seconds=constraints.duration_seconds,
            style=constraints.style,
            aspect_ratio=constraints.aspect_ratio,
            narrative="从问题到流程再到总结",
            scenes=[
                SceneContract(scene_id="scene-1", index=1, role="hook", title="问题", duration_seconds=60, learning_objective="引入问题", visual_type="title_intro", content_hint="为什么不是两次", required_sources=["content"]),
                SceneContract(scene_id="scene-2", index=2, role="concept", title="流程", duration_seconds=60, learning_objective="解释流程", visual_type="concept_explain", content_hint="三次报文", required_sources=["content"]),
                SceneContract(scene_id="scene-3", index=3, role="recap", title="总结", duration_seconds=60, learning_objective="总结", visual_type="compare_summary", content_hint="回顾", required_sources=["content"]),
            ],
        )

    async def fake_scene_run(self, contract, digest, constraints):
        return SceneDraft(
            scene_id=contract.scene_id,
            index=contract.index,
            title=contract.title,
            narration=f"{contract.title} 旁白",
            captions=[contract.title],
            on_screen_text=[contract.learning_objective],
            visual_prompt=contract.content_hint,
            visual_type=contract.visual_type,
            interaction_prompt="",
            visual={"title": contract.title, "content": contract.content_hint},
            source_agents=contract.required_sources,
        )

    # Mock TtsService and SparkTtsService to return 19.6s duration
    from app.resource.infra.tts import TtsResult
    from app.resource.infra.spark_tts import SparkTtsService
    from app.resource.infra.tts import TtsService

    async def fake_tts_synthesize_with_captions(text, file_path, voice=None):
        return TtsResult(duration=19.6, captions=[])

    monkeypatch.setattr(TtsService, "synthesize_with_captions", fake_tts_synthesize_with_captions)
    monkeypatch.setattr(SparkTtsService, "synthesize_with_captions", fake_tts_synthesize_with_captions)

    # Mock get_audio_duration_ms to return 19600ms
    monkeypatch.setattr("app.resource.agents.video.get_audio_duration_ms", lambda file_path: 19600)

    monkeypatch.setattr(VideoMaterialAgent, "run", fake_material_run)
    monkeypatch.setattr(VideoOutlineAgent, "run", fake_outline_run)
    monkeypatch.setattr(SceneWriterAgent, "run", fake_scene_run)

    assert "video" in AGENT_REGISTRY

    agent = VideoAgent()
    result = await agent.generate_resource(
        ResourceInput(
            resource_id=1,
            learning_need="把 TCP 三次握手生成讲解视频",
            agent_name="video",
            agent_config={"duration_seconds": 180, "scene_count": 3},
            upstream_handoffs={
                "content": DownstreamContext(
                    source_agent="content",
                    title="课程内容",
                    one_sentence_summary="TCP 三次握手同步双方初始序号。",
                    covered_outline_ids=[],
                )
            },
        )
    )

    assert result.success is True
    assert result.file_type == "json"
    assert result.metadata["agent_id"] == "video"
    assert result.metadata["schema_version"] == "video/v1"
    parsed = json.loads(result.content)
    assert parsed["duration_seconds"] == 60  # 3 scenes × 20.0s each
    assert len(parsed["scenes"]) == 3


def test_video_payload_contract_uses_backend_video_v1_fields():
    payload = _valid_payload_dict()

    first_scene = payload["scenes"][0]

    assert "scene_id" in first_scene
    assert "duration_ms" in first_scene
    assert "narration" in first_scene
    assert "visual_prompt" in first_scene
    assert "visual_data" not in first_scene
    assert "imageUrl" not in first_scene


@pytest.mark.asyncio
async def test_video_agent_generate_node_path_learning(monkeypatch):
    from app.resource.agents.video import (
        SceneDraft,
        SceneWriterAgent,
        VideoAgent,
        VideoMaterialAgent,
        VideoMaterialDigest,
        VideoOutline,
        VideoOutlineAgent,
        SceneContract,
    )
    from app.resource.schemas import NodeInput

    async def fake_material_run(self, input_data, config):
        assert input_data.learning_scenario == "path_learning"
        assert "content" in input_data.upstream_handoffs
        return VideoMaterialDigest(
            topic="TCP 三次握手",
            audience="自学学习者",
            learning_goal="掌握 TCP 握手",
            core_concepts=["SYN", "ACK"],
            facts=["三次握手同步序号"],
            examples=["历史 SYN 报文"],
            process_steps=["SYN", "SYN+ACK", "ACK"],
            misconceptions=[],
            practice_prompts=[],
            visual_opportunities=[],
            source_map={"facts": ["content"]},
        )

    async def fake_outline_run(self, digest, constraints):
        return VideoOutline(
            title="TCP 三次握手讲解",
            topic=digest.topic,
            duration_seconds=constraints.duration_seconds,
            style=constraints.style,
            aspect_ratio=constraints.aspect_ratio,
            narrative="大纲",
            scenes=[
                SceneContract(scene_id="scene-1", index=1, role="hook", title="问题", duration_seconds=60, learning_objective="引入问题", visual_type="title_intro", content_hint="为什么不是两次", required_sources=["content"]),
                SceneContract(scene_id="scene-2", index=2, role="concept", title="流程", duration_seconds=60, learning_objective="解释流程", visual_type="concept_explain", content_hint="三次报文", required_sources=["content"]),
                SceneContract(scene_id="scene-3", index=3, role="recap", title="总结", duration_seconds=60, learning_objective="总结", visual_type="compare_summary", content_hint="回顾", required_sources=["content"]),
            ],
        )

    async def fake_scene_run(self, contract, digest, constraints):
        return SceneDraft(
            scene_id=contract.scene_id,
            index=contract.index,
            title=contract.title,
            narration=f"{contract.title} 旁白",
            captions=[contract.title],
            on_screen_text=[contract.learning_objective],
            visual_prompt=contract.content_hint,
            visual_type=contract.visual_type,
            interaction_prompt="",
            visual={"title": contract.title, "content": contract.content_hint},
            source_agents=contract.required_sources,
        )

    # Mock TtsService and SparkTtsService to return 19.6s duration
    from app.resource.infra.tts import TtsResult
    from app.resource.infra.spark_tts import SparkTtsService
    from app.resource.infra.tts import TtsService

    async def fake_tts_synthesize_with_captions(text, file_path, voice=None):
        return TtsResult(duration=19.6, captions=[])

    monkeypatch.setattr(TtsService, "synthesize_with_captions", fake_tts_synthesize_with_captions)
    monkeypatch.setattr(SparkTtsService, "synthesize_with_captions", fake_tts_synthesize_with_captions)

    # Mock get_audio_duration_ms to return 19600ms
    monkeypatch.setattr("app.resource.agents.video.get_audio_duration_ms", lambda file_path: 19600)

    monkeypatch.setattr(VideoMaterialAgent, "run", fake_material_run)
    monkeypatch.setattr(VideoOutlineAgent, "run", fake_outline_run)
    monkeypatch.setattr(SceneWriterAgent, "run", fake_scene_run)

    node_input = NodeInput(
        path_id=101,
        node_id=202,
        node_key="tcp-handshake",
        path_title="网络协议",
        path_goal="掌握握手",
        stage_id="stage-1",
        node_title="TCP 三次握手",
        difficulty="intermediate",
        mastery_target="理解三次报文交换",
        knowledge_points=["SYN", "ACK"],
        weak_knowledge_points=["第三次确认"],
        generation_focus=["时序描述"],
        tutorial_title="三次握手教程",
        tutorial_summary="教程摘要",
        tutorial_markdown="# 教程正文\n握手原理。",
        agent_config={"scene_count": 3},
    )

    agent = VideoAgent()
    result = await agent.generate_node(node_input)

    assert result.success is True
    assert result.file_type == "json"
    assert result.metadata["agent_id"] == "video"
    assert result.metadata["path_id"] == 101
    assert result.metadata["node_id"] == 202
