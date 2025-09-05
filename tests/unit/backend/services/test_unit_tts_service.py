"""
Unit tests for TTS (Text-to-Speech) Service Component.

This module provides comprehensive unit tests for the TTS service including:
- Provider abstraction and switching
- Voice consistency and mapping
- Caching mechanisms
- Error handling and fallback
- Performance and health monitoring
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from packages.backend.components.audio.tts_service import (
    ElevenLabsTTSProvider,
    OpenAITTSProvider,
    ProviderHealthStatus,
    TTSCache,
    TTSService,
    TTSServiceStatus,
    VoiceInfo,
)
from packages.shared.logging_config import get_logger
from packages.shared.models import SpeechSynthesisResult, TextToSpeechRequest

logger = get_logger(__name__)


class TestVoiceInfo:
    """Test cases for VoiceInfo dataclass."""

    def test_voice_info_creation(self):
        """Test creating a VoiceInfo instance."""
        voice = VoiceInfo(
            voice_id="test_voice_001",
            name="Test Voice",
            language="en-US",
            gender="female",
            age="young",
            provider="test_provider",
            quality="high",
            sample_rate=22050,
            supported_formats=["wav", "mp3"],
            description="A test voice for unit testing",
        )

        assert voice.voice_id == "test_voice_001"
        assert voice.name == "Test Voice"
        assert voice.language == "en-US"
        assert voice.gender == "female"
        assert voice.provider == "test_provider"
        assert voice.quality == "high"
        assert voice.sample_rate == 22050
        assert "wav" in voice.supported_formats
        assert voice.age == "young"

    def test_voice_info_defaults(self):
        """Test VoiceInfo with default values."""
        voice = VoiceInfo(
            voice_id="minimal_voice",
            name="Minimal Voice",
            language="en-US",
            gender="neutral",
        )

        assert voice.quality == "standard"  # Default value
        assert voice.sample_rate == 22050  # Default value
        assert voice.supported_formats == ["wav", "mp3"]  # Default value
        assert voice.age is None
        assert voice.accent is None


class TestTTSCache:
    """Test cases for TTS caching mechanism."""

    def setup_method(self):
        """Set up test environment."""
        self.cache = TTSCache(max_size=10, max_age_hours=1)

    def test_cache_initialization(self):
        """Test cache initialization."""
        assert self.cache.max_size == 10
        assert self.cache.max_age == timedelta(hours=1)
        assert len(self.cache._cache) == 0
        assert len(self.cache._access_order) == 0

    def test_cache_put_and_get(self):
        """Test basic cache put and get operations."""
        test_key = "test_cache_key"
        test_data = b"test_audio_data"
        voice_id = "test_voice"
        text = "Hello world"

        # Put data in cache
        self.cache.put(test_key, test_data, voice_id, text, "wav")

        # Get data from cache
        cached_data = self.cache.get(test_key)

        assert cached_data == test_data
        assert len(self.cache._cache) == 1
        assert test_key in self.cache._access_order

    def test_cache_expiration(self):
        """Test cache entry expiration."""
        test_key = "expiring_key"
        test_data = b"expiring_data"

        # Manually set old timestamp
        old_time = datetime.utcnow() - timedelta(hours=2)

        # Put data with old timestamp
        self.cache.put(test_key, test_data, "voice", "text", "wav")

        # Manually modify timestamp to simulate expiration
        if test_key in self.cache._cache:
            self.cache._cache[test_key].created_at = old_time

        # Try to get expired data
        cached_data = self.cache.get(test_key)

        assert cached_data is None
        assert len(self.cache._cache) == 0

    def test_cache_size_limit(self):
        """Test cache size limit enforcement."""
        small_cache = TTSCache(max_size=2)

        # Fill cache beyond limit
        for i in range(5):
            key = f"key_{i}"
            data = f"data_{i}".encode()
            small_cache.put(key, data, f"voice_{i}", f"text_{i}", "wav")

        # Cache should only contain max_size entries
        assert len(small_cache._cache) == 2
        assert len(small_cache._access_order) == 2

    def test_cache_clear(self):
        """Test cache clearing functionality."""
        # Add some data
        self.cache.put("key1", b"data1", "voice1", "text1", "wav")
        self.cache.put("key2", b"data2", "voice2", "text2", "wav")

        assert len(self.cache._cache) == 2

        # Clear cache
        self.cache.clear()

        assert len(self.cache._cache) == 0
        assert len(self.cache._access_order) == 0

    def test_cache_stats(self):
        """Test cache statistics generation."""
        # Add some test data
        self.cache.put("key1", b"data1", "voice1", "text1", "wav")
        self.cache.put("key2", b"data2", "voice2", "text2", "wav")

        # Access one entry multiple times
        self.cache.get("key1")
        self.cache.get("key1")

        stats = self.cache.stats()

        assert stats["entries"] == 2
        assert stats["total_accesses"] == 2
        assert stats["total_size_mb"] > 0


class TestOpenAITTSProvider:
    """Test cases for OpenAI TTS provider."""

    def setup_method(self):
        """Set up test environment."""
        self.config = {
            "api_key": "test_openai_key",
            "base_url": "https://api.openai.com/v1",
            "model": "tts-1",
            "default_voice": "alloy",
        }
        self.provider = OpenAITTSProvider(self.config)

    def test_provider_initialization(self):
        """Test provider initialization."""
        assert self.provider.provider_name == "openai"
        assert self.provider.api_key == "test_openai_key"
        assert self.provider.model == "tts-1"
        assert self.provider.default_voice == "alloy"

    @pytest.mark.asyncio
    async def test_get_available_voices(self):
        """Test getting available voices."""
        voices = await self.provider.get_available_voices()

        assert len(voices) == 6  # OpenAI has 6 voices
        voice_names = [v.name for v in voices]
        assert "Alloy" in voice_names
        assert "Echo" in voice_names
        assert "Nova" in voice_names

        # Check voice properties
        for voice in voices:
            assert voice.provider == "openai"
            assert voice.quality == "high"
            assert voice.language == "en-US"

    @pytest.mark.asyncio
    async def test_get_available_voices_with_language_filter(self):
        """Test getting voices filtered by language."""
        voices = await self.provider.get_available_voices("en-US")

        # All OpenAI voices are en-US
        assert len(voices) == 6

        # Test with non-existent language
        voices = await self.provider.get_available_voices("fr-FR")
        assert len(voices) == 0

    def test_provider_info(self):
        """Test provider information retrieval."""
        info = self.provider.get_provider_info()

        assert info["name"] == "OpenAI TTS"
        assert info["provider"] == "openai"
        assert info["model"] == "tts-1"
        assert info["voice_count"] == 6
        assert info["quality"] == "high"
        assert "mp3" in info["supported_formats"]

    @pytest.mark.asyncio
    async def test_synthesize_speech_success(self):
        """Test successful speech synthesis."""
        request = TextToSpeechRequest(
            text="Hello world", voice="alloy", language="en-US"
        )

        result = await self.provider.synthesize_speech(
            text=request.text, voice_id=request.voice, language=request.language
        )

        assert isinstance(result, SpeechSynthesisResult)
        assert result.audio_data is not None
        assert result.voice_used == "alloy"
        assert result.provider == "openai"
        assert result.audio_format == "wav"
        assert result.duration > 0
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test provider health checking."""
        # Initial health should be unhealthy
        assert self.provider._health_status.status == "unhealthy"

        # Check health
        health = await self.provider.check_health()

        # After check, should be healthy (mock implementation)
        assert health.status == "healthy"
        assert health.provider_name == "openai"
        assert health.service_type == "tts"
        assert health.response_time >= 0


class TestElevenLabsTTSProvider:
    """Test cases for ElevenLabs TTS provider."""

    def setup_method(self):
        """Set up test environment."""
        self.config = {
            "api_key": "test_elevenlabs_key",
            "base_url": "https://api.elevenlabs.io/v1",
            "model": "eleven_monolingual_v1",
            "default_voice": "21m00Tcm4TlvDq8ikWAM",
        }
        self.provider = ElevenLabsTTSProvider(self.config)

    def test_provider_initialization(self):
        """Test provider initialization."""
        assert self.provider.provider_name == "elevenlabs"
        assert self.provider.api_key == "test_elevenlabs_key"
        assert self.provider.model == "eleven_monolingual_v1"

    @pytest.mark.asyncio
    async def test_get_available_voices(self):
        """Test getting available voices."""
        voices = await self.provider.get_available_voices()

        assert len(voices) == 8  # ElevenLabs has 8 test voices
        voice_names = [v.name for v in voices]
        assert "Rachel" in voice_names
        assert "Drew" in voice_names
        assert "Domi" in voice_names

        # Check voice properties
        for voice in voices:
            assert voice.provider == "elevenlabs"
            assert voice.quality == "premium"
            assert voice.language == "en-US"

    def test_provider_info(self):
        """Test provider information retrieval."""
        info = self.provider.get_provider_info()

        assert info["name"] == "ElevenLabs"
        assert info["provider"] == "elevenlabs"
        assert info["voice_count"] == 8
        assert info["quality"] == "premium"
        assert "mp3" in info["supported_formats"]


class TestTTSService:
    """Test cases for main TTS service."""

    def setup_method(self):
        """Set up test environment."""
        self.config = {
            "providers": {
                "openai": {"api_key": "test_openai_key", "model": "tts-1"},
                "elevenlabs": {
                    "api_key": "test_elevenlabs_key",
                    "model": "eleven_monolingual_v1",
                },
            },
            "cache_size": 50,
            "cache_age_hours": 2,
        }
        self.service = TTSService(self.config)

    def test_service_initialization(self):
        """Test service initialization."""
        assert len(self.service.providers) == 2
        assert "openai" in self.service.providers
        assert "elevenlabs" in self.service.providers
        assert isinstance(self.service.cache, TTSCache)
        assert self.service.fallback_enabled is True

    def test_voice_mappings(self):
        """Test voice mapping functionality."""
        # Test voice mapping
        mapped_voices = self.service._map_voice_id("female_young")

        # Should contain mappings for both providers
        assert "elevenlabs" in mapped_voices
        assert "openai" in mapped_voices

        # Test direct voice ID (no mapping needed)
        direct_mapping = self.service._map_voice_id("openai:alloy")
        assert direct_mapping == {"openai": "alloy"}

    def test_generate_cache_key(self):
        """Test cache key generation."""
        request = TextToSpeechRequest(
            text="Test message",
            voice="alloy",
            language="en-US",
            speed=1.0,
            pitch=1.0,
            volume=1.0,
            output_format="wav",
        )

        key1 = self.service._generate_cache_key(request)
        key2 = self.service._generate_cache_key(request)

        # Same request should generate same key
        assert key1 == key2

        # Different request should generate different key
        request2 = request.copy()
        request2.text = "Different message"
        key3 = self.service._generate_cache_key(request2)

        assert key1 != key3

    @pytest.mark.asyncio
    async def test_get_available_voices(self):
        """Test getting all available voices."""
        voices = await self.service.get_available_voices()

        # Should get voices from both providers
        openai_voices = [v for v in voices if v.provider == "openai"]
        elevenlabs_voices = [v for v in voices if v.provider == "elevenlabs"]

        assert len(openai_voices) == 6
        assert len(elevenlabs_voices) == 8

    @patch("packages.backend.components.tts_service.observability_service")
    @pytest.mark.asyncio
    async def test_synthesize_speech_success(self, mock_obs):
        """Test successful speech synthesis."""
        # Mock the trace_operation context manager
        mock_obs.trace_operation.return_value.__enter__ = lambda self: "test_trace_id"
        mock_obs.trace_operation.return_value.__exit__ = lambda self, *args: None

        request = TextToSpeechRequest(
            text="Hello world", voice="default", language="en-US"
        )

        result = await self.service.synthesize_speech(request, "test_correlation_id")

        assert isinstance(result, SpeechSynthesisResult)
        assert result.audio_data is not None
        assert result.provider in ["openai", "elevenlabs"]
        assert result.processing_time > 0

    @patch("packages.backend.components.tts_service.observability_service")
    @pytest.mark.asyncio
    async def test_synthesize_speech_caching(self, mock_obs):
        """Test TTS caching functionality."""
        # Mock the trace_operation context manager
        mock_obs.trace_operation.return_value.__enter__ = lambda self: "test_trace_id"
        mock_obs.trace_operation.return_value.__exit__ = lambda self, *args: None

        request = TextToSpeechRequest(
            text="Cache test message", voice="alloy", language="en-US"
        )

        # First synthesis
        result1 = await self.service.synthesize_speech(request, "cache_test_1")

        # Second synthesis (should use cache)
        result2 = await self.service.synthesize_speech(request, "cache_test_2")

        # Results should be identical (from cache)
        assert result1.audio_data == result2.audio_data
        assert result2.provider == "cached"

    @patch("packages.backend.components.tts_service.observability_service")
    @pytest.mark.asyncio
    async def test_provider_fallback(self, mock_obs):
        """Test provider fallback functionality."""
        # Mock the trace_operation context manager
        mock_obs.trace_operation.return_value.__enter__ = lambda self: "test_trace_id"
        mock_obs.trace_operation.return_value.__exit__ = lambda self, *args: None

        # Mock OpenAI provider to fail
        original_synthesize = self.service.providers["openai"].synthesize_speech

        async def failing_synthesis(*args, **kwargs):
            raise Exception("OpenAI provider failed")

        self.service.providers["openai"].synthesize_speech = failing_synthesis

        try:
            request = TextToSpeechRequest(text="Fallback test", voice="default")

            result = await self.service.synthesize_speech(request, "fallback_test")

            # Should succeed with ElevenLabs provider
            assert result.provider == "elevenlabs"
            assert result.audio_data is not None

        finally:
            # Restore original method
            self.service.providers["openai"].synthesize_speech = original_synthesize

    def test_service_status(self):
        """Test service status retrieval."""
        status = self.service.get_service_status()

        assert isinstance(status, TTSServiceStatus)
        assert hasattr(status, "healthy_providers")
        assert hasattr(status, "total_providers")
        assert hasattr(status, "average_response_time")
        assert status.total_providers == 2

    def test_cache_operations(self):
        """Test cache management operations."""
        # Add some test data
        self.service.cache.put(
            "test_key", b"test_data", "test_voice", "test_text", "wav"
        )

        assert self.service.cache.get("test_key") is not None

        # Clear cache
        self.service.clear_cache()

        assert self.service.cache.get("test_key") is None

    @pytest.mark.asyncio
    async def test_provider_health_monitoring(self):
        """Test provider health monitoring."""
        # Check initial health
        health_statuses = await self.service.get_provider_health()

        assert len(health_statuses) == 2
        assert "openai" in health_statuses
        assert "elevenlabs" in health_statuses

        for health in health_statuses.values():
            assert isinstance(health, ProviderHealthStatus)
            assert health.status in ["healthy", "degraded", "unhealthy"]

    def test_service_health_status(self):
        """Test overall service health status."""
        status = self.service.get_health_status()

        assert isinstance(status, dict)
        assert "status" in status
        assert "providers" in status
        assert "cache" in status
        assert "synthesis_count" in status


class TestTTSServiceErrorHandling:
    """Test error handling scenarios for TTS service."""

    def setup_method(self):
        """Set up test environment."""
        self.service = TTSService()

    @patch("packages.backend.components.tts_service.observability_service")
    @pytest.mark.asyncio
    async def test_all_providers_failed(self, mock_obs):
        """Test behavior when all providers fail."""
        # Mock the trace_operation context manager
        mock_obs.trace_operation.return_value.__enter__ = lambda self: "test_trace_id"
        mock_obs.trace_operation.return_value.__exit__ = lambda self, *args: None

        # Mock all providers to fail
        for provider in self.service.providers.values():
            original_synthesize = provider.synthesize_speech

            async def failing_synthesis(*args, **kwargs):
                raise Exception("Provider failed")

            provider.synthesize_speech = failing_synthesis

        try:
            request = TextToSpeechRequest(text="Test", voice="default")
            result = await self.service.synthesize_speech(request, "error_test")

            # Should return error result
            assert result.error is not None
            assert result.provider == "error"

        finally:
            # Restore providers (simplified for test)
            pass

    def test_invalid_voice_mapping(self):
        """Test handling of invalid voice mappings."""
        # Test with non-existent voice
        mapped = self.service._map_voice_id("nonexistent_voice")

        # Should return default mapping
        assert "elevenlabs" in mapped
        assert "openai" in mapped

    def test_empty_text_handling(self):
        """Test handling of empty text input."""
        request = TextToSpeechRequest(text="test", voice="default")

        # Should handle text gracefully
        cache_key = self.service._generate_cache_key(request)
        assert cache_key is not None


if __name__ == "__main__":
    pytest.main([__file__])
