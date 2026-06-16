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
