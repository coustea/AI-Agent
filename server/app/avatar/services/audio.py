"""Audio processing module.

Manages audio buffer and coordinates with ASR service.
"""

from app.avatar.services.asr import IatClient
from app.infra.logging import get_logger

logger = get_logger(__name__)


class AudioHandler:
    """Audio handler for buffering and speech recognition."""

    SAMPLE_RATE = 16000
    CHUNK_SIZE = 1280
    MIN_AUDIO_LENGTH = 1600

    def __init__(self):
        self.iat_client = IatClient()
        self.audio_buffer = bytearray()

    def clear(self):
        """Clear the audio buffer."""
        self.audio_buffer.clear()

    def is_valid(self) -> bool:
        """Check if audio buffer has enough data to be valid."""
        return len(self.audio_buffer) >= self.MIN_AUDIO_LENGTH

    def get_duration(self) -> float:
        """Get audio duration in seconds."""
        sample_count = len(self.audio_buffer) // 2
        return sample_count / self.SAMPLE_RATE
