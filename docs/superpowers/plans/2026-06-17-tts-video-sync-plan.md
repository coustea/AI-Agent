# TTS Voiceover Integration & Scene Duration Synchronization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Microsoft Edge-TTS into the backend `VideoAgent` pipeline to automatically generate voiceover audio and synchronize each scene's duration with the generated audio length, preventing animations from transitioning before speech finishes.

**Architecture:** 
1. Use `edge-tts` to synthesize speech asynchronously.
2. Store synthesized MP3 files under `server/workplace/video_audio/`.
3. Use `mutagen` to inspect the exact duration of generated MP3s.
4. Calculate and set contiguous timings (`start_ms`, `duration_ms`) dynamically in the payload based on audio duration.
5. Serve the files via a new FastAPI endpoint `/api/v1/ai/video/audio/{filename}`.

**Tech Stack:** edge-tts, mutagen, fastapi, pydantic, pytest

---

### Task 1: Add Dependencies

**Files:**
- Modify: [pyproject.toml](file:///Users/apple/Code/software/server/pyproject.toml)

- [ ] **Step 1: Add mutagen and edge-tts to dependency list**

Modify the `dependencies` list in `server/pyproject.toml` to add `edge-tts>=6.1.12` and `mutagen>=1.47.0`.

```toml
    "edge-tts>=6.1.12",
    "mutagen>=1.47.0",
```

- [ ] **Step 2: Run uv sync to update virtual environment**

Run:
```bash
rtk proxy uv sync
```
Expected: Successfully installs edge-tts, mutagen, and update lockfile.

- [ ] **Step 3: Commit**

```bash
rtk proxy git add server/pyproject.toml server/uv.lock
rtk proxy git commit -m "chore: add edge-tts and mutagen dependencies"
```

---

### Task 2: Implement TtsService

**Files:**
- Create: [tts.py](file:///Users/apple/Code/software/server/app/resource/infra/tts.py)
- Create: [test_video_tts.py](file:///Users/apple/Code/software/server/tests/resource/test_video_tts.py)

- [ ] **Step 1: Write a test for TtsService**

Create `server/tests/resource/test_video_tts.py` with the following content:

```python
import os
import pytest
from pathlib import Path
from app.config import WORKPLACE_DIR
from app.resource.infra.tts import TtsService

@pytest.mark.asyncio
async def test_tts_synthesis_and_duration():
    output_dir = WORKPLACE_DIR / "test_audio"
    file_path = output_dir / "test_scene.mp3"
    
    if file_path.exists():
        os.remove(file_path)
        
    try:
        text = "中华人民共和国，测试语音合成。"
        duration = await TtsService.synthesize(text, file_path)
        
        assert file_path.exists(), "TTS file should be created"
        assert duration > 0.0, "Duration should be positive"
        assert isinstance(duration, float)
    finally:
        if file_path.exists():
            os.remove(file_path)
        if output_dir.exists():
            os.rmdir(output_dir)
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
rtk proxy uv run pytest server/tests/resource/test_video_tts.py
```
Expected: Fail with `ModuleNotFoundError: No module named 'app.resource.infra.tts'`

- [ ] **Step 3: Implement TtsService**

Create `server/app/resource/infra/tts.py` with:

```python
from __future__ import annotations

import os
from pathlib import Path
import edge_tts
from mutagen.mp3 import MP3
from app.infra.logging import get_logger

logger = get_logger(__name__)

class TtsService:
    @staticmethod
    async def synthesize(text: str, file_path: Path, voice: str = "zh-CN-XiaoxiaoNeural") -> float:
        """Synthesize text to MP3 and return its duration in seconds."""
        if not text or not text.strip():
            logger.warning("Empty text passed to TtsService. Skip synthesis.")
            return 0.0

        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("Starting TTS synthesis for text (len=%d) to %s", len(text), file_path)
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(file_path))
        
        if not file_path.exists():
            raise FileNotFoundError(f"Failed to generate TTS file at {file_path}")
            
        # Parse MP3 duration using mutagen
        audio = MP3(str(file_path))
        duration = audio.info.length
        logger.info("TTS synthesis complete. Duration: %.2fs", duration)
        return duration
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
rtk proxy uv run pytest server/tests/resource/test_video_tts.py
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk proxy git add server/app/resource/infra/tts.py server/tests/resource/test_video_tts.py
rtk proxy git commit -m "feat: implement TtsService with edge-tts and mutagen duration parsing"
```

---

### Task 3: Implement FastAPI Audio Serving Endpoint

**Files:**
- Modify: [api.py](file:///Users/apple/Code/software/server/app/resource/api.py)
- Create: [test_video_audio_api.py](file:///Users/apple/Code/software/server/tests/resource/test_video_audio_api.py)

- [ ] **Step 1: Write an integration test for the new endpoint**

Create `server/tests/resource/test_video_audio_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.app import create_app
from app.config import WORKPLACE_DIR

client = TestClient(create_app())

def test_serve_audio_file():
    audio_dir = WORKPLACE_DIR / "video_audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    test_file = audio_dir / "test_endpoint.mp3"
    
    with open(test_file, "wb") as f:
        f.write(b"fake audio data")
        
    try:
        response = client.get("/api/v1/ai/video/audio/test_endpoint.mp3")
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"
        assert response.content == b"fake audio data"
        
        # Test directory traversal protection
        response_traversal = client.get("/api/v1/ai/video/audio/../config.yaml")
        assert response_traversal.status_code == 400
        
        # Test not found
        response_not_found = client.get("/api/v1/ai/video/audio/non_existent.mp3")
        assert response_not_found.status_code == 404
    finally:
        if test_file.exists():
            test_file.unlink()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
rtk proxy uv run pytest server/tests/resource/test_video_audio_api.py
```
Expected: Fail with status code 404 (not found) for the GET endpoint request.

- [ ] **Step 3: Implement the HTTP endpoint in api.py**

Modify `server/app/resource/api.py` to add the endpoint route at the end of the file:

```python
@router.get("/video/audio/{filename}")
async def get_video_audio(filename: str):
    """Serve generated video audio files."""
    from app.config import WORKPLACE_DIR
    from fastapi.responses import FileResponse
    
    # Simple directory traversal checks
    if ".." in filename or "/" in filename or "\\" in filename:
        return HttpResponse.error(code=400, message="Illegal filename")
        
    file_path = WORKPLACE_DIR / "video_audio" / filename
    if not file_path.exists():
        return HttpResponse.error(code=404, message="Audio file not found")
        
    return FileResponse(path=str(file_path), media_type="audio/mpeg")
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
rtk proxy uv run pytest server/tests/resource/test_video_audio_api.py
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk proxy git add server/app/resource/api.py server/tests/resource/test_video_audio_api.py
rtk proxy git commit -m "feat: add video audio serving endpoint to resource api router"
```

---

### Task 4: Update VideoScene and SceneDraft Models

**Files:**
- Modify: [video.py](file:///Users/apple/Code/software/server/app/resource/agents/video.py:98-150)

- [ ] **Step 1: Add audio_src field to Pydantic models**

Modify `SceneDraft` and `VideoScene` in `server/app/resource/agents/video.py` to add `audio_src`:

```python
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
    audio_src: str | None = None
    source_agents: list[str] = Field(default_factory=list)
```

And update `VideoScene`:

```python
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
    audio_src: str | None = None
    source_agents: list[str] = Field(default_factory=list)
```

- [ ] **Step 2: Run pytest to verify model syntax is correct**

Run:
```bash
rtk proxy uv run pytest server/tests/resource/test_video_agent.py
```
Expected: PASS (existing tests verify parsing still works)

- [ ] **Step 3: Commit**

```bash
rtk proxy git add server/app/resource/agents/video.py
rtk proxy git commit -m "refactor: add audio_src field to SceneDraft and VideoScene models"
```

---

### Task 5: Integrate TTS Synthesis and Synchronization in VideoAgent Pipeline

**Files:**
- Modify: [video.py](file:///Users/apple/Code/software/server/app/resource/agents/video.py)

- [ ] **Step 1: Mock TtsService in existing unit tests to prevent network queries**

To keep tests offline, modify `server/tests/resource/test_video_agent.py` to mock `TtsService.synthesize`.
Add this fixture/setup in `test_video_agent_generates_json_from_previous_results` around line 155:

```python
    # Mock TtsService.synthesize to return 10 seconds duration
    from app.resource.infra.tts import TtsService
    async def fake_tts_synthesize(text, file_path, voice="zh-CN-XiaoxiaoNeural"):
        return 10.0
    monkeypatch.setattr(TtsService, "synthesize", fake_tts_synthesize)
```

Let's check if the existing tests still pass.
Run:
```bash
rtk proxy uv run pytest server/tests/resource/test_video_agent.py
```
Expected: PASS

- [ ] **Step 2: Update _write_scene_node to call edge-tts**

In `server/app/resource/agents/video.py`, import `TtsService` and update `_write_scene_node` to synthesize voiceover and set duration:

```python
    async def _write_scene_node(self, state: VideoSceneWriteState) -> dict[str, Any]:
        async with self._scene_semaphore:
            writer = SceneWriterAgent()
            draft = await writer.run(state["contract"], state["digest"], state["constraints"])
            
            # Determine prefix for unique audio files
            input_data = state.get("input_data") or state.get("digest") # wait, let's look at how we get input_data
```
Wait, let's verify what `VideoSceneWriteState` contains.
In `video.py`:
```python
class VideoSceneWriteState(TypedDict):
    contract: SceneContract
    digest: VideoMaterialDigest
    constraints: VideoConstraints
```
So we don't have direct access to `input_data.resource_id` in `VideoSceneWriteState`.
But wait! We can pass `resource_id` or `prefix` inside the state!
Let's check `VideoGraphState`:
```python
class VideoGraphState(TypedDict, total=False):
    # Inputs
    input_data: ResourceInput
    config: dict[str, Any]
    constraints: VideoConstraints
    
    # Intermediate artifacts
    digest: VideoMaterialDigest
    outline: VideoOutline
    drafts: Annotated[list[SceneDraft], _add_scene_drafts]
```
Wait! `_route_scenes` creates the states for each `write_scene` node:
```python
    def _route_scenes(self, state: VideoGraphState) -> list[Send]:
        outline: VideoOutline = state["outline"]
        digest: VideoMaterialDigest = state["digest"]
        constraints: VideoConstraints = state["constraints"]
        return [
            Send("write_scene", {
                "contract": scene,
                "digest": digest,
                "constraints": constraints,
            })
            for scene in outline.scenes
        ]
```
Ah! We can add a field to `VideoSceneWriteState`: `resource_id: int | None = None` and populate it in `_route_scenes` from `state["input_data"].resource_id`!
Let's verify this. Yes, this is extremely clean.
Let's see:
```python
class VideoSceneWriteState(TypedDict):
    contract: SceneContract
    digest: VideoMaterialDigest
    constraints: VideoConstraints
    resource_id: int | None
```
And in `_route_scenes`:
```python
    def _route_scenes(self, state: VideoGraphState) -> list[Send]:
        outline: VideoOutline = state["outline"]
        digest: VideoMaterialDigest = state["digest"]
        constraints: VideoConstraints = state["constraints"]
        resource_id = state["input_data"].resource_id if "input_data" in state else None
        return [
            Send("write_scene", {
                "contract": scene,
                "digest": digest,
                "constraints": constraints,
                "resource_id": resource_id,
            })
            for scene in outline.scenes
        ]
```
Then inside `_write_scene_node`:
```python
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
            
            # Edge-TTS synthesis
            duration_s = await TtsService.synthesize(draft.narration, file_path)
            
            # Add 500ms safety buffer, but keep a minimum of 4 seconds
            duration_ms = max(int(duration_s * 1000) + 500, 4000)
            
            draft.audio_src = f"/api/v1/ai/video/audio/{filename}"
            # Store the computed duration_ms directly on draft's extra attribute or similar.
            # But wait, SceneDraft doesn't have duration_ms! Let's check SceneDraft fields:
            # scene_id, index, title, narration, captions, on_screen_text, visual_prompt, visual_type, interaction_prompt, visual, source_agents, audio_src.
            # Yes! We need to add duration_ms: int = 0 to SceneDraft so we can pass it to the payload builder!
```
Wait! Let's double check if `SceneDraft` can have `duration_ms`.
Yes, we can add `duration_ms: int = 0` to `SceneDraft`! That is extremely clean.
Let's add it to `SceneDraft` model as well in Task 4!

- [ ] **Step 3: Update VideoPayloadBuilder to re-align timings**

Update `VideoPayloadBuilder.build` in `server/app/resource/agents/video.py`:
```python
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
            # Use the duration_ms generated by TTS if available, else fall back to outline planned duration
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
                    captions=constraints.include_captions and draft.captions or [],
                    on_screen_text=draft.on_screen_text,
                    visual_prompt=draft.visual_prompt,
                    interaction_prompt=draft.interaction_prompt,
                    visual=draft.visual or {},
                    audio_src=draft.audio_src,
                    source_agents=draft.source_agents or contract.required_sources,
                )
            )
            cursor_ms += duration_ms

        # Re-align total duration to be ceiling seconds
        import math
        total_ms = cursor_ms
        duration_seconds = (total_ms + 999) // 1000
        target_total_ms = duration_seconds * 1000
        diff_ms = target_total_ms - total_ms
        
        # Distribute the padding to the last scene
        if scenes and diff_ms > 0:
            scenes[-1].duration_ms += diff_ms
            
        # Recheck contiguous start times
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
```

- [ ] **Step 4: Run existing tests to verify all pass**

Run:
```bash
rtk proxy uv run pytest server/tests/resource/test_video_agent.py
```
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
rtk proxy git add server/app/resource/agents/video.py server/tests/resource/test_video_agent.py
rtk proxy git commit -m "feat: integrate Edge-TTS and timing synchronization in VideoAgent pipeline"
```
