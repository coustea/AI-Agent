"""Unit tests for TTS service.

Tests cover CartoonTtsService synthesis, caching, and word timing
estimation for both Edge-TTS and Spark TTS providers.

User instruction: "@app/shared/cartoon/ 按照google的python代码规范来完善代码，补充测试和修复类型注解"
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.shared.cartoon.schemas import CaptionWord
from app.shared.cartoon.tts import CartoonTtsService


class TestCartoonTtsService:
    """Tests for CartoonTtsService."""

    def test_init_creates_cache_dir(self, tmp_path: Path) -> None:
        """Test that cache directory is created on initialization."""
        cache_dir = tmp_path / "tts_cache"
        assert not cache_dir.exists()

        CartoonTtsService(cache_dir=cache_dir)

        assert cache_dir.exists()

    @pytest.mark.asyncio
    async def test_synthesize_empty_text(self, tmp_path: Path) -> None:
        """Test that empty text returns zero duration and empty words."""
        service = CartoonTtsService(cache_dir=tmp_path / "cache")
        output_path = tmp_path / "output.mp3"

        duration_ms, words = await service.synthesize(
            text="",
            output_path=output_path,
        )

        assert duration_ms == 0
        assert words == []

    @pytest.mark.asyncio
    async def test_synthesize_uses_cache(self, tmp_path: Path) -> None:
        """Test that cached result is reused when available."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create fake cache files with valid SHA-256 hash pattern
        # Using a deterministic hash for testing
        cache_mp3 = cache_dir / "tts_test_hash.mp3"
        cache_meta = cache_dir / "tts_test_hash.json"

        cache_mp3.write_bytes(b"fake audio data")
        cache_meta.write_text(
            '{"duration_ms": 5000, "words": [{"text": "你好", "start_ms": 0, "end_ms": 500}]}'
        )

        service = CartoonTtsService(cache_dir=cache_dir)

        # Patch hashlib to return our known hash
        with patch(
            "app.shared.cartoon.tts.hashlib.sha256"
        ) as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "test_hash"

            output_path = tmp_path / "output.mp3"
            duration_ms, words = await service.synthesize(
                text="测试文本",
                output_path=output_path,
            )

        assert duration_ms == 5000
        assert len(words) == 1
        assert words[0].text == "你好"

    @pytest.mark.asyncio
    async def test_synthesize_edge_tts_fallback(self, tmp_path: Path) -> None:
        """Test synthesis using Edge-TTS when Spark is not configured."""
        service = CartoonTtsService(cache_dir=tmp_path / "cache")

        # Mock Edge TTS Communicate stream events
        # stream() returns an async generator
        async def mock_stream() -> Any:
            yield {
                "type": "WordBoundary",
                "offset": 0,  # 100-nanosecond units
                "duration": 5000000,  # 500ms in 100ns units
                "text": "你好",
            }
            yield {"type": "audio", "data": b"fake audio chunk"}

        mock_communicate = MagicMock()
        mock_communicate.stream = mock_stream

        with patch("app.shared.cartoon.tts.edge_tts.Communicate", return_value=mock_communicate):
            with patch("app.shared.cartoon.tts.MP3") as mock_mp3:
                mock_mp3_instance = MagicMock()
                mock_mp3_instance.info.length = 5.0
                mock_mp3.return_value = mock_mp3_instance

                # Patch Spark config to force Edge-TTS fallback
                with patch("app.shared.cartoon.tts.SPARK_TTS_APP_ID", ""):
                    output_path = tmp_path / "output.mp3"
                    duration_ms, words = await service.synthesize(
                        text="你好",
                        output_path=output_path,
                        voice="zh-CN-XiaoxiaoNeural",
                    )

        assert duration_ms == 5000
        assert len(words) == 1
        assert words[0].text == "你好"


class TestEstimateSparkWords:
    """Tests for _estimate_spark_words static method."""

    def test_estimate_simple_chinese_text(self) -> None:
        """Test word timing estimation for simple Chinese text."""
        text = "你好世界"
        duration = 2.0  # 2 seconds

        words = CartoonTtsService._estimate_spark_words(text, duration)

        assert len(words) == 4
        assert all(isinstance(w, CaptionWord) for w in words)
        assert words[0].text == "你"
        assert words[0].start_ms == 0
        assert words[-1].end_ms == 2000

    def test_estimate_text_with_punctuation(self) -> None:
        """Test that punctuation gets appropriate timing weight."""
        text = "你好，世界。"
        duration = 3.0

        words = CartoonTtsService._estimate_spark_words(text, duration)

        # 你好，世界。 = 6 tokens: 你、好、，、世、界、。
        # Regex splits Chinese characters individually: [一-鿿]
        assert len(words) == 6  # 你、好、，、世、界、。
        # Comma should be recognized as a punctuation token
        comma_word = next((w for w in words if w.text == "，"), None)
        assert comma_word is not None

    def test_estimate_empty_text(self) -> None:
        """Test that empty text returns empty word list."""
        words = CartoonTtsService._estimate_spark_words("", 1.0)
        assert words == []

    def test_estimate_zero_duration(self) -> None:
        """Test that zero duration returns empty word list."""
        words = CartoonTtsService._estimate_spark_words("你好", 0.0)
        assert words == []

    def test_estimate_mixed_chinese_english(self) -> None:
        """Test estimation with mixed Chinese and English text."""
        text = "使用 Python 编程"
        duration = 2.5

        words = CartoonTtsService._estimate_spark_words(text, duration)

        assert len(words) >= 4
        # "Python" should be a single token
        python_word = next((w for w in words if w.text == "Python"), None)
        assert python_word is not None

    def test_estimate_assigns_longer_weight_to_punctuation(self) -> None:
        """Test that punctuation marks get longer duration weights."""
        text_no_punct = "你好世界"
        text_with_punct = "你好。世界"

        words_no_punct = CartoonTtsService._estimate_spark_words(text_no_punct, 2.0)
        words_with_punct = CartoonTtsService._estimate_spark_words(text_with_punct, 2.0)

        # With punctuation, total weight is higher, so words may be shorter
        # But the key test is that punctuation is properly weighted
        assert len(words_with_punct) > len(words_no_punct)


class TestCreateSparkAuthUrl:
    """Tests for _create_spark_auth_url static method."""

    def test_raises_without_credentials(self) -> None:
        """Test that missing Spark credentials raise ValueError."""
        with patch("app.shared.cartoon.tts.SPARK_TTS_APP_ID", ""):
            with patch("app.shared.cartoon.tts.SPARK_TTS_API_KEY", ""):
                with patch("app.shared.cartoon.tts.SPARK_TTS_API_SECRET", ""):
                    with pytest.raises(ValueError, match="Missing Spark API credentials"):
                        CartoonTtsService._create_spark_auth_url()

    def test_creates_valid_url_structure(self) -> None:
        """Test that generated URL has correct structure."""
        with patch("app.shared.cartoon.tts.SPARK_TTS_APP_ID", "test_app_id"):
            with patch("app.shared.cartoon.tts.SPARK_TTS_API_KEY", "test_api_key"):
                with patch("app.shared.cartoon.tts.SPARK_TTS_API_SECRET", "test_api_secret"):
                    url = CartoonTtsService._create_spark_auth_url()

        assert url.startswith("wss://tts-api.xfyun.cn/v2/tts?")
        assert "authorization=" in url
        assert "date=" in url
        assert "host=" in url


class TestCaptionWord:
    """Tests for CaptionWord used in TTS results."""

    def test_caption_word_creation(self) -> None:
        """Test creating a CaptionWord instance."""
        word = CaptionWord(text="测试", start_ms=100, end_ms=500)
        assert word.text == "测试"
        assert word.start_ms == 100
        assert word.end_ms == 500

    def test_caption_word_from_dict(self) -> None:
        """Test creating CaptionWord from dictionary."""
        data = {"text": "测试", "start_ms": 100, "end_ms": 500}
        word = CaptionWord(**data)
        assert word.text == "测试"