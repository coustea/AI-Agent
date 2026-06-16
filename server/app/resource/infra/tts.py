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
