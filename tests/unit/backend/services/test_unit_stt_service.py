"""
Unit tests for STT (Speech-to-Text) Service Component.

This module provides comprehensive unit tests for the STT service including:
- Provider abstraction and switching
- Audio preprocessing and format conversion
- Caching mechanisms for transcriptions
- Error handling and fallback
- Performance and health monitoring
"""

from datetime import datetime, timedelta

import pytest

from packages.backend.components.audio.stt_service import (
    AudioProcessingConfig,
    GoogleSTTProvider,
    OpenAISTTProvider,
    ProviderHealthStatus,
    STTCache,
    STTService,
)
from packages.shared.logging_config import get_logger
from packages.shared.models import AudioTranscriptionRequest, TranscriptionResult

logger = get_logger(__name__)


class TestAudioProcessingConfig:
    """Test cases for AudioProcessingConfig dataclass."""

    def test_audio_config_creation(self):
        """Test creating an AudioProcessingConfig instance."""
        config = AudioProcessingConfig(
            sample_rate=22050,
            channels=1,
            bit_depth=16,
            supported_formats=["wav", "mp3", "flac"],
            max_duration=120,
            min_duration=0.5,
            normalize_audio=True,
            remove_silence=True,
            noise_reduction=False,
            compression_level=3,
        )

        assert config.sample_rate == 22050
        assert config.channels == 1
        assert config.bit_depth == 16
        assert "wav" in config.supported_formats
        assert "mp3" in config.supported_formats
        assert config.max_duration == 120
        assert config.min_duration == 0.5
        assert config.normalize_audio is True
        assert config.remove_silence is True
        assert config.noise_reduction is False
        assert config.compression_level == 3

    def test_audio_config_defaults(self):
        """Test AudioProcessingConfig with default values."""
        config = AudioProcessingConfig()

        assert config.sample_rate == 16000  # Default value
        assert config.channels == 1  # Default value
        assert config.bit_depth == 16  # Default value
        assert "wav" in config.supported_formats  # Default value
        assert "mp3" in config.supported_formats
        assert config.max_duration == 300  # Default value
        assert config.min_duration == 0.1  # Default value
        assert config.normalize_audio is True  # Default value
        assert config.remove_silence is True  # Default value
        assert config.noise_reduction is True  # Default value
        assert config.compression_level == 5  # Default value


class TestSTTCache:
    """Test cases for STT caching mechanism."""

    def setup_method(self):
        """Set up test environment."""
        self.cache = STTCache(max_size=10, max_age_hours=1)

    def test_cache_initialization(self):
        """Test cache initialization."""
        assert self.cache.max_size == 10
        assert self.cache.max_age == timedelta(hours=1)
        assert len(self.cache._cache) == 0
        assert len(self.cache._access_order) == 0

    def test_cache_put_and_get(self):
        """Test basic cache put and get operations."""
        test_key = "test_cache_key"
        transcription = "Hello world transcription"
        confidence = 0.95
        language = "en"
        provider = "openai"
        audio_data = b"test_audio_data"
        processing_time = 0.5

        # Put data in cache
        self.cache.put(
            test_key,
            transcription,
            confidence,
            language,
            provider,
            audio_data,
            processing_time,
        )

        # Get data from cache
        cached_entry = self.cache.get(test_key)

        assert cached_entry is not None
        assert cached_entry.transcription == transcription
        assert cached_entry.confidence == confidence
        assert cached_entry.language == language
        assert cached_entry.provider == provider
        assert cached_entry.processing_time == processing_time
        assert len(self.cache._cache) == 1
        assert test_key in self.cache._access_order

    def test_cache_expiration(self):
        """Test cache entry expiration."""
        test_key = "expiring_key"
        transcription = "Expiring transcription"

        # Manually set old timestamp
        old_time = datetime.utcnow() - timedelta(hours=2)

        # Put data with old timestamp
        self.cache.put(test_key, transcription, 0.9, "en", "openai", b"audio", 0.5)

        # Manually modify timestamp to simulate expiration
        if test_key in self.cache._cache:
            self.cache._cache[test_key].created_at = old_time

        # Try to get expired data
        cached_entry = self.cache.get(test_key)

        assert cached_entry is None
        assert len(self.cache._cache) == 0

    def test_cache_size_limit(self):
        """Test cache size limit enforcement."""
        small_cache = STTCache(max_size=2)

        # Fill cache beyond limit
        for i in range(5):
            key = f"key_{i}"
            transcription = f"Transcription {i}"
            audio_data = f"audio_{i}".encode()
            small_cache.put(key, transcription, 0.9, "en", "openai", audio_data, 0.5)

        # Cache should only contain max_size entries
        assert len(small_cache._cache) == 2
        assert len(small_cache._access_order) == 2

    def test_cache_clear(self):
        """Test cache clearing functionality."""
        # Add some data
        self.cache.put("key1", "transcription1", 0.9, "en", "openai", b"audio1", 0.5)
        self.cache.put("key2", "transcription2", 0.9, "en", "openai", b"audio2", 0.5)

        assert len(self.cache._cache) == 2

        # Clear cache
        self.cache.clear()

        assert len(self.cache._cache) == 0
        assert len(self.cache._access_order) == 0

    def test_cache_stats(self):
        """Test cache statistics generation."""
        # Add some test data
        self.cache.put("key1", "transcription1", 0.9, "en", "openai", b"audio1", 0.5)
        self.cache.put("key2", "transcription2", 0.9, "en", "openai", b"audio2", 0.5)

        # Access one entry multiple times
        self.cache.get("key1")
        self.cache.get("key1")

        stats = self.cache.stats()

        assert stats["entries"] == 2
        assert stats["total_accesses"] == 2
        assert stats["total_size_mb"] > 0


class TestOpenAISTTProvider:
    """Test cases for OpenAI STT provider."""

    def setup_method(self):
        """Set up test environment."""
        self.config = {
            "api_key": "test_openai_key",
            "base_url": "https://api.openai.com/v1",
            "model": "whisper-1",
            "temperature": 0.0,
        }
        self.provider = OpenAISTTProvider(self.config)

    def test_provider_initialization(self):
        """Test provider initialization."""
        assert self.provider.provider_name == "openai"
        assert self.provider.api_key == "test_openai_key"
        assert self.provider.model == "whisper-1"
        assert self.provider.temperature == 0.0

    @pytest.mark.asyncio
    async def test_get_supported_languages(self):
        """Test getting supported languages."""
        languages = await self.provider.get_supported_languages()

        assert len(languages) > 50  # OpenAI Whisper supports many languages
        assert "en" in languages
        assert "es" in languages
        assert "fr" in languages
        assert "de" in languages

    @pytest.mark.asyncio
    async def test_get_supported_languages_count(self):
        """Test that we get a reasonable number of supported languages."""
        languages = await self.provider.get_supported_languages()

        # OpenAI Whisper supports around 99 languages
        assert 90 <= len(languages) <= 110

    def test_provider_info(self):
        """Test provider information retrieval."""
        info = self.provider.get_provider_info()

        assert info["name"] == "OpenAI Whisper"
        assert info["provider"] == "openai"
        assert info["model"] == "whisper-1"
        assert "wav" in info["supported_formats"]
        assert "mp3" in info["supported_formats"]
        assert "flac" in info["supported_formats"]
        assert "language_detection" in info["features"]

    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self):
        """Test successful audio transcription."""
        audio_data = b"test_audio_data"
        audio_format = "wav"
        language = "en-US"
        session_id = "test_session"

        result = await self.provider.transcribe_audio(
            audio_data=audio_data,
            audio_format=audio_format,
            language=language,
            session_id=session_id,
        )

        assert isinstance(result, TranscriptionResult)
        assert result.transcription_id is not None
        assert result.session_id == session_id
        assert result.text is not None
        assert result.confidence > 0
        assert result.language == language
        assert result.provider == "openai"
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
        assert health.service_type == "stt"
        assert health.response_time >= 0

    def test_audio_preprocessing(self):
        """Test audio preprocessing functionality."""
        audio_data = b"original_audio_data"
        input_format = "mp3"

        processed_audio, output_format = self.provider.preprocess_audio(
            audio_data, input_format
        )

        # In mock implementation, should return same data with WAV format
        assert processed_audio == audio_data
        assert output_format == "wav"


class TestGoogleSTTProvider:
    """Test cases for Google STT provider."""

    def setup_method(self):
        """Set up test environment."""
        self.config = {
            "api_key": "test_google_key",
            "project_id": "test_project",
            "location": "global",
            "recognition_config": {},
        }
        self.provider = GoogleSTTProvider(self.config)

    def test_provider_initialization(self):
        """Test provider initialization."""
        assert self.provider.provider_name == "google"
        assert self.provider.api_key == "test_google_key"
        assert self.provider.project_id == "test_project"
        assert self.provider.location == "global"

    @pytest.mark.asyncio
    async def test_get_supported_languages(self):
        """Test getting supported languages."""
        languages = await self.provider.get_supported_languages()

        assert len(languages) > 40  # Google STT supports many languages
        assert "en" in languages
        assert "es" in languages
        assert "fr" in languages
        assert "de" in languages

    def test_provider_info(self):
        """Test provider information retrieval."""
        info = self.provider.get_provider_info()

        assert info["name"] == "Google Speech-to-Text"
        assert info["provider"] == "google"
        assert "wav" in info["supported_formats"]
        assert "flac" in info["supported_formats"]
        assert "word_confidence" in info["features"]

    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self):
        """Test successful audio transcription."""
        audio_data = b"test_audio_data"
        audio_format = "flac"
        language = "en-US"
        session_id = "test_session"

        result = await self.provider.transcribe_audio(
            audio_data=audio_data,
            audio_format=audio_format,
            language=language,
            session_id=session_id,
        )

        assert isinstance(result, TranscriptionResult)
        assert result.transcription_id is not None
        assert result.session_id == session_id
        assert result.text is not None
        assert result.confidence > 0
        assert result.language == language
        assert result.provider == "google"
        assert result.processing_time > 0


class TestSTTService:
    """Test cases for main STT service."""

    def setup_method(self):
        """Set up test environment."""
        self.config = {
            "providers": {
                "openai": {"api_key": "test_openai_key", "model": "whisper-1"},
                "google": {
                    "api_key": "test_google_key",
                    "project_id": "test_project",
                },
            },
            "cache_size": 50,
            "cache_age_hours": 2,
        }
        self.service = STTService(self.config)

    def test_service_initialization(self):
        """Test service initialization."""
        assert len(self.service.providers) == 2
        assert "openai" in self.service.providers
        assert "google" in self.service.providers
        assert isinstance(self.service.cache, STTCache)
        assert self.service.fallback_enabled is True
        assert isinstance(self.service.audio_config, AudioProcessingConfig)

    def test_generate_cache_key(self):
        """Test cache key generation."""
        request = AudioTranscriptionRequest(
            audio_data=b"test_audio_data",
            audio_format="wav",
            language="en-US",
            provider="openai",
            session_id="test_session",
            sample_rate=16000,
            channels=1,
        )

        key1 = self.service._generate_cache_key(request)
        key2 = self.service._generate_cache_key(request)

        # Same request should generate same key
        assert key1 == key2

        # Different request should generate different key
        request2 = request.copy()
        request2.language = "es-ES"
        key3 = self.service._generate_cache_key(request2)

        assert key1 != key3

    @pytest.mark.asyncio
    async def test_get_supported_languages(self):
        """Test getting all supported languages."""
        languages = await self.service.get_supported_languages()

        # Should get languages from both providers
        assert len(languages) > 50  # Combined languages from both providers
        assert "en" in languages
        assert "es" in languages

    @pytest.mark.asyncio
    async def test_get_supported_languages_specific_provider(self):
        """Test getting languages from specific provider."""
        languages = await self.service.get_supported_languages("openai")

        # Should only get OpenAI languages
        assert len(languages) > 50
        assert "en" in languages

    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self):
        """Test successful audio transcription."""
        request = AudioTranscriptionRequest(
            audio_data=b"test_audio_data",
            audio_format="wav",
            language="en-US",
            session_id="test_session",
            sample_rate=16000,
            channels=1,
        )

        result = await self.service.transcribe_audio(request, "test_correlation_id")

        assert isinstance(result, TranscriptionResult)
        assert result.transcription_id is not None
        assert result.session_id == "test_session"
        assert result.text is not None
        assert result.confidence > 0
        assert result.provider in ["openai", "google"]
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_transcribe_audio_caching(self):
        """Test STT caching functionality."""
        request = AudioTranscriptionRequest(
            audio_data=b"cache_test_audio_data",
            audio_format="wav",
            language="en-US",
            session_id="cache_test",
            sample_rate=16000,
            channels=1,
        )

        # First transcription
        result1 = await self.service.transcribe_audio(request, "cache_test_1")

        # Second transcription (should use cache)
        result2 = await self.service.transcribe_audio(request, "cache_test_2")

        # Results should be identical (from cache)
        assert result1.text == result2.text
        assert result1.confidence == result2.confidence
        assert result2.provider == "cached"

    @pytest.mark.asyncio
    async def test_provider_fallback(self):
        """Test provider fallback functionality."""
        # Mock OpenAI provider to fail
        original_transcribe = self.service.providers["openai"].transcribe_audio

        async def failing_transcription(*args, **kwargs):
            raise Exception("OpenAI provider failed")

        self.service.providers["openai"].transcribe_audio = failing_transcription

        try:
            request = AudioTranscriptionRequest(
                audio_data=b"fallback_test_audio",
                audio_format="wav",
                language="en-US",
                sample_rate=16000,
                channels=1,
            )

            result = await self.service.transcribe_audio(request, "fallback_test")

            # Should succeed with Google provider
            assert result.provider == "google"
            assert result.text is not None

        finally:
            # Restore original method
            self.service.providers["openai"].transcribe_audio = original_transcribe

    def test_audio_preprocessing(self):
        """Test audio preprocessing in service."""
        audio_data = b"original_audio_data"
        input_format = "mp3"

        processed_audio, output_format = self.service._preprocess_audio(
            audio_data, input_format
        )

        # In mock implementation, should return same data with WAV format
        assert processed_audio == audio_data
        assert output_format == "wav"

    @pytest.mark.asyncio
    async def test_service_status(self):
        """Test service status retrieval."""
        status = await self.service.get_service_status()

        # Should have the expected structure
        assert hasattr(status, "is_available")
        assert hasattr(status, "healthy_providers")
        assert hasattr(status, "total_providers")
        assert hasattr(status, "average_response_time")

    def test_cache_operations(self):
        """Test cache management operations."""
        # Add some test data
        self.service.cache.put(
            "test_key", "test_transcription", 0.9, "en", "openai", b"test_audio", 0.5
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
        assert "google" in health_statuses

        for health in health_statuses.values():
            assert isinstance(health, ProviderHealthStatus)
            assert health.status in ["healthy", "degraded", "unhealthy"]

    @pytest.mark.asyncio
    async def test_service_health_status(self):
        """Test overall service health status."""
        status = await self.service.get_health_status()

        assert isinstance(status, dict)
        assert "status" in status
        assert "providers" in status
        assert "cache" in status
        assert "transcription_count" in status
        assert "audio_config" in status


class TestSTTServiceErrorHandling:
    """Test error handling scenarios for STT service."""

    def setup_method(self):
        """Set up test environment."""
        self.service = STTService()

    @pytest.mark.asyncio
    async def test_all_providers_failed(self):
        """Test behavior when all providers fail."""
        # Mock all providers to fail
        for provider in self.service.providers.values():
            original_transcribe = provider.transcribe_audio

            async def failing_transcription(*args, **kwargs):
                raise Exception("Provider failed")

            provider.transcribe_audio = failing_transcription

        try:
            request = AudioTranscriptionRequest(
                audio_data=b"test_audio",
                audio_format="wav",
                language="en-US",
                sample_rate=16000,
                channels=1,
            )
            result = await self.service.transcribe_audio(request, "error_test")

            # Should return error result
            assert result.provider == "error"
            assert result.text == "Transcription failed"
            assert result.confidence == 0.0
            assert result.error is not None

        finally:
            # Restore providers (simplified for test)
            pass

    def test_invalid_audio_format_handling(self):
        """Test handling of invalid audio formats."""
        # Test with empty audio data
        request = AudioTranscriptionRequest(
            audio_data=b"",
            audio_format="wav",
            language="en-US",
            sample_rate=16000,
            channels=1,
        )

        cache_key = self.service._generate_cache_key(request)
        assert cache_key is not None

    def test_large_audio_data_handling(self):
        """Test handling of large audio data."""
        # Create large audio data
        large_audio = b"x" * (1024 * 1024)  # 1MB of data

        request = AudioTranscriptionRequest(
            audio_data=large_audio,
            audio_format="wav",
            language="en-US",
            sample_rate=16000,
            channels=1,
        )

        cache_key = self.service._generate_cache_key(request)
        assert cache_key is not None


if __name__ == "__main__":
    pytest.main([__file__])
