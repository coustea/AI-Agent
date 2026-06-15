"""
Bridge service state management.
Defines message types for avatar WebSocket communication.
"""


class MessageType:
    """Message type constants."""
    # Client → Server
    AUDIO_CHUNK = "audio_chunk"
    AUDIO_END = "audio_end"
    TEXT_INPUT = "text_input"
    STOP_SPEAKING = "stop_speaking"
    CLEAR_HISTORY = "clear_history"

    # Server → Client
    HISTORY_CLEARED = "history_cleared"
