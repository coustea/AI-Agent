# TTS Voiceover Integration & Scene Duration Synchronization Design

## Problem Description
Currently, the backend `VideoAgent` (`server/app/resource/agents/video.py`) generates a structured video plan JSON but does not produce any narration audio. 
The Remotion rendering project (`src/video-render`) has support for scene-specific `<Audio>` overlays through the `audio_src` field in scenes, but this field is currently empty in backend-generated outputs.

Furthermore:
1. **Timing Mismatch**: Scene durations are currently planned statically (e.g. 10s or 15s per scene). If a voiceover (TTS) generated for a scene's `narration` text takes longer than this planned duration, the Remotion video will transition to the next scene before the TTS finishes speaking, cutting off the audio.
2. **Subtitles Alignment**: Subtitles must align with the actual audio duration.
3. **Audio Serving**: Remotion and Vue-based players need a reliable HTTP API endpoint to access the generated audio files.

---

## Goals
- **Automatic TTS Synthesis**: Integrate Microsoft Edge-TTS in the backend `VideoAgent` pipeline to synthesize audio files (`.mp3`) for every scene's `narration` text.
- **Dynamic Timing Synchronization**: Adjust each scene's duration (`duration_ms`) to match the exact duration of its synthesized audio file, preventing transitions before speech ends.
- **FastAPI Audio Serving**: Provide a secure API endpoint on FastAPI to serve the generated `.mp3` files.
- **Contiguous Layout Timing**: Re-calculate start times (`start_ms`) and overall video duration (`duration_seconds`) to keep the payload valid.
- **Smooth Subtitles**: Ensure subtitles are automatically synced to the adjusted scene duration.

---

## Proposed Architecture

### 1. Backend TTS Service (`server/app/resource/infra/tts.py`)
We will create a helper service `TtsService` in the backend to manage Edge-TTS execution and audio file duration extraction:
- **Synthesis**: Runs `edge-tts` command or uses the `edge-tts` Python library asynchronously. We'll use the high-quality Chinese voice `zh-CN-XiaoxiaoNeural` (default) or `zh-CN-YunxiNeural` based on configuration.
- **Storage**: Saves files to `server/workplace/video_audio/{resource_id}_scene_{scene_id}.mp3`.
- **Duration Extraction**: Uses the standard Python `mutagen` package to read the exact length of the MP3 file in milliseconds.

```python
import os
import edge_tts
from mutagen.mp3 import MP3
from app.config import WORKPLACE_DIR

class TtsService:
    @staticmethod
    async def synthesize(text: str, file_path: Path, voice: str = "zh-CN-XiaoxiaoNeural") -> float:
        """Synthesize text to MP3 and return its duration in seconds."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(file_path))
        
        # Extract duration
        audio = MP3(str(file_path))
        return audio.info.length
```

### 2. FastAPI Audio serving endpoint (`server/app/resource/api.py`)
Add a simple file response route to serve MP3 files:
```python
@router.get("/video/audio/{filename}")
async def get_video_audio(filename: str):
    """Serve generated video audio files."""
    from app.config import WORKPLACE_DIR
    from fastapi.responses import FileResponse
    
    file_path = WORKPLACE_DIR / "video_audio" / filename
    # Guard against directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
         return HttpResponse.error(code=400, message="Illegal filename")
         
    if not file_path.exists():
        return HttpResponse.error(code=404, message="Audio file not found")
        
    return FileResponse(path=str(file_path), media_type="audio/mpeg")
```

### 3. Pipeline Integration in `VideoAgent` (`server/app/resource/agents/video.py`)

#### Model Updates
Add `audio_src` field:
```python
class SceneDraft(BaseModel):
    ...
    audio_src: str | None = None

class VideoScene(BaseModel):
    ...
    audio_src: str | None = None
```

#### Graph Node Updates
1. **`_write_scene_node`**:
   - For each scene, after generating `SceneDraft` content, invoke `TtsService.synthesize` with `narration`.
   - Set `audio_src = f"/api/v1/ai/video/audio/{resource_id}_scene_{scene_id}.mp3"`.
   - Obtain `audio_duration_ms` (duration in seconds * 1000).
   - Set `duration_ms` of draft to `max(audio_duration_ms + 500, minimum_duration_ms)` (adding a 500ms safety buffer).

2. **`_payload_node` / `VideoPayloadBuilder`**:
   - Iterate through all scene drafts.
   - Accumulate and re-assign `start_ms` values contiguously:
     `scenes[i].start_ms = scenes[i-1].start_ms + scenes[i-1].duration_ms`.
   - Calculate the total duration in milliseconds: `total_ms = sum(s.duration_ms for s in scenes)`.
   - Calculate `duration_seconds = (total_ms + 999) // 1000` (ceiling division).
   - Distribute the remainder `diff_ms = duration_seconds * 1000 - total_ms` to the last scene's duration:
     `scenes[-1].duration_ms += diff_ms`.
   - This ensures the Pydantic check `total_duration_ms == duration_seconds * 1000` is perfectly satisfied.

---

## Verification Plan

### Automated Tests
- Create a unit test `server/tests/resource/test_video_tts.py` to:
  - Generate TTS for a sample text using the `TtsService`.
  - Assert that a valid MP3 file is created.
  - Assert that the duration is returned as a positive float.
- Run `uv run pytest server/tests/resource/test_video_tts.py` to verify.

### Manual Verification
1. Run uvicorn server on port 9999.
2. Request a video generation task.
3. Verify that the generated JSON has `audio_src` populated with the `/api/v1/ai/video/audio/...` path.
4. Verify that the audio files are downloadable and playable via the browser/GET endpoint.
5. Load the JSON into the Remotion project `src/video-render` and verify the video transitions exactly when the audio finishes speaking.
