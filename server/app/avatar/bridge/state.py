"""Bridge 服务状态管理 — 定义数字人 WebSocket 通信的消息类型常量。"""


# 定义数字人 WebSocket 通信的消息类型常量（客户端与服务端双向）
class MessageType:
    """WebSocket 消息类型常量。"""
    # ── 客户端 → 服务端 ──
    AUDIO_CHUNK = "audio_chunk"      # 音频数据块（base64 编码的 PCM）
    AUDIO_END = "audio_end"          # 音频输入结束标记
    TEXT_INPUT = "text_input"        # 文本输入（替代语音的文本模式）
    STOP_SPEAKING = "stop_speaking"  # 停止数字人播报
    CLEAR_HISTORY = "clear_history"  # 清除当前会话历史

    # ── 服务端 → 客户端 ──
    HISTORY_CLEARED = "history_cleared"  # 历史清除完成通知
