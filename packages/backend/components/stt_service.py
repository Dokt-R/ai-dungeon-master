"""
STT (Speech-to-Text) Service Component for AI Dungeon Master.

This module provides comprehensive speech-to-text functionality with provider abstraction,
supporting multiple STT services with automatic fallback and audio preprocessing.

Features:
- Provider-agnostic STT interface supporting multiple services
- Audio format conversion and preprocessing for optimal transcription
- Provider health monitoring and automatic failover
- Confidence scoring and transcription validation
- Audio stream processing and buffering
- Comprehensive error handling and logging
"""

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger
from packages.shared.models import (
    AudioTranscriptionRequest,
    ProviderHealthStatus,
    STTServiceStatus,
    TranscriptionResult,
)

logger = get_logger(__name__)


@dataclass
class AudioProcessingConfig:
    """Configuration for audio processing and preprocessing."""

    sample_rate: int = 16000  # Optimal for most STT services
    channels: int = 1  # Mono audio
    bit_depth: int = 16
    supported_formats: List[str] = field(
        default_factory=lambda: ["wav", "mp3", "ogg", "flac"]
    )
    max_duration: int = 300  # Maximum audio duration in seconds
    min_duration: float = 0.1  # Minimum audio duration in seconds
    normalize_audio: bool = True
    remove_silence: bool = True
    noise_reduction: bool = True
    compression_level: int = 5  # 0-9, higher = better quality but slower


@dataclass
class STTCacheEntry:
    """Cache entry for STT results."""

    cache_key: str
    transcription: str
    confidence: float
    language: str
    provider: str
    audio_hash: str
    created_at: datetime
    access_count: int = 0
    size_bytes: int = 0
    processing_time: float = 0.0


class STTCache:
    """Simple in-memory cache for STT results."""

    def __init__(self, max_size: int = 200, max_age_hours: int = 24):
        self.max_size = max_size
        self.max_age = timedelta(hours=max_age_hours)
        self._cache: Dict[str, STTCacheEntry] = {}
        self._access_order: List[str] = []

    def get(self, key: str) -> Optional[STTCacheEntry]:
        """Get cached transcription."""
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if datetime.utcnow() - entry.created_at > self.max_age:
            self._remove_entry(key)
            return None

        # Update access patterns
        entry.access_count += 1
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        return entry

    def put(
        self,
        key: str,
        transcription: str,
        confidence: float,
        language: str,
        provider: str,
        audio_data: bytes,
        processing_time: float,
    ) -> None:
        """Cache transcription result."""
        # Generate audio hash for cache key
        audio_hash = hashlib.md5(audio_data).hexdigest()

        entry = STTCacheEntry(
            cache_key=key,
            transcription=transcription,
            confidence=confidence,
            language=language,
            provider=provider,
            audio_hash=audio_hash,
            created_at=datetime.utcnow(),
            size_bytes=len(transcription.encode("utf-8")),
            processing_time=processing_time,
        )

        # Check cache size and evict if necessary
        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        self._cache[key] = entry
        self._access_order.append(key)

    def _remove_entry(self, key: str) -> None:
        """Remove an entry from cache."""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)

    def _evict_oldest(self) -> None:
        """Evict the least recently used entry."""
        if not self._access_order:
            return

        oldest_key = self._access_order.pop(0)
        if oldest_key in self._cache:
            del self._cache[oldest_key]

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._access_order.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_size = sum(entry.size_bytes for entry in self._cache.values())
        total_accesses = sum(entry.access_count for entry in self._cache.values())

        return {
            "entries": len(self._cache),
            "total_size_mb": total_size / (1024 * 1024),
            "total_accesses": total_accesses,
            "hit_rate": total_accesses / max(len(self._cache), 1),
        }


class STTProvider(ABC):
    """Abstract base class for STT providers."""

    def __init__(self, provider_name: str, config: Dict[str, Any]):
        self.provider_name = provider_name
        self.config = config
        self.logger = get_logger(f"{__name__}.{provider_name}Provider")
        self._health_status: ProviderHealthStatus = self._create_initial_health_status()
        self.audio_config = AudioProcessingConfig()

    @abstractmethod
    async def transcribe_audio(
        self,
        audio_data: bytes,
        audio_format: str,
        language: str = "en",
        session_id: str = None,
    ) -> TranscriptionResult:
        """Transcribe audio to text."""
        pass

    @abstractmethod
    async def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        pass

    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information and capabilities."""
        pass

    def _create_initial_health_status(self) -> ProviderHealthStatus:
        """Create initial health status for the provider."""
        return ProviderHealthStatus(
            provider_name=self.provider_name,
            service_type="stt",
            status="unknown",
            response_time=0.0,
            success_rate=0.0,
            last_check=datetime.utcnow(),
        )

    async def check_health(self) -> ProviderHealthStatus:
        """Check provider health and update status."""
        start_time = time.time()

        try:
            # Simple health check - try to get supported languages
            languages = await self.get_supported_languages()
            response_time = time.time() - start_time

            # Update health status
            self._health_status.status = "healthy"
            self._health_status.response_time = response_time
            self._health_status.last_check = datetime.utcnow()

            # Update success rate (simple moving average)
            self._health_status.success_rate = (
                self._health_status.success_rate * 0.9 + 1.0 * 0.1
            )

            self._health_status.consecutive_failures = 0
            self._health_status.error_message = None

        except Exception as e:
            response_time = time.time() - start_time

            self._health_status.status = "unhealthy"
            self._health_status.response_time = response_time
            self._health_status.last_check = datetime.utcnow()
            self._health_status.consecutive_failures += 1
            self._health_status.error_message = str(e)

            # Update success rate
            self._health_status.success_rate = (
                self._health_status.success_rate * 0.9  # Decay on failure
            )

        return self._health_status

    def get_health_status(self) -> ProviderHealthStatus:
        """Get current health status."""
        return self._health_status

    def preprocess_audio(
        self, audio_data: bytes, input_format: str
    ) -> Tuple[bytes, str]:
        """
        Preprocess audio data for optimal transcription.

        Args:
            audio_data: Raw audio data
            input_format: Input audio format

        Returns:
            Tuple of (processed_audio_data, output_format)
        """
        # In a real implementation, this would:
        # 1. Convert format if needed (using ffmpeg or similar)
        # 2. Normalize audio levels
        # 3. Remove silence
        # 4. Apply noise reduction
        # 5. Ensure correct sample rate and channels

        # For now, return as-is with WAV format
        return audio_data, "wav"


class OpenAISTTProvider(STTProvider):
    """OpenAI Whisper STT provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("openai", config)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "whisper-1")
        self.temperature = config.get("temperature", 0.0)

    async def transcribe_audio(
        self,
        audio_data: bytes,
        audio_format: str,
        language: str = "en",
        session_id: str = None,
    ) -> TranscriptionResult:
        """Transcribe audio using OpenAI Whisper."""
        start_time = time.time()

        try:
            # Preprocess audio
            processed_audio, output_format = self.preprocess_audio(
                audio_data, audio_format
            )

            # In a real implementation, this would call the OpenAI API
            # For now, return a mock result
            processing_time = time.time() - start_time

            # Mock transcription based on audio data hash
            audio_hash = hashlib.md5(processed_audio).hexdigest()
            mock_transcription = f"Mock transcription for audio {audio_hash[:8]}"

            return TranscriptionResult(
                transcription_id=f"trans_{audio_hash[:8]}",
                session_id=session_id or "default",
                text=mock_transcription,
                confidence=0.95,
                language=language,
                provider=self.provider_name,
                processing_time=processing_time,
            )

        except Exception as e:
            self.logger.error("OpenAI STT transcription failed", error=str(e))
            raise

    async def get_supported_languages(self) -> List[str]:
        """Get supported languages for OpenAI Whisper."""
        return [
            "en",
            "zh",
            "de",
            "es",
            "ru",
            "ko",
            "fr",
            "ja",
            "pt",
            "tr",
            "pl",
            "ca",
            "nl",
            "ar",
            "sv",
            "it",
            "id",
            "hi",
            "fi",
            "vi",
            "he",
            "uk",
            "el",
            "ms",
            "cs",
            "ro",
            "da",
            "hu",
            "ta",
            "no",
            "th",
            "ur",
            "hr",
            "bg",
            "lt",
            "la",
            "mi",
            "ml",
            "cy",
            "sk",
            "te",
            "fa",
            "lv",
            "bn",
            "sr",
            "az",
            "sl",
            "kn",
            "et",
            "mk",
            "br",
            "eu",
            "is",
            "hy",
            "ne",
            "mn",
            "bs",
            "kk",
            "sq",
            "sw",
            "gl",
            "mr",
            "pa",
            "si",
            "km",
            "sn",
            "yo",
            "so",
            "af",
            "oc",
            "ka",
            "be",
            "tg",
            "sd",
            "gu",
            "am",
            "yi",
            "lo",
            "uz",
            "fo",
            "ht",
            "ps",
            "tk",
            "nn",
            "mt",
            "sa",
            "lb",
            "my",
            "bo",
            "tl",
            "mg",
            "as",
            "tt",
            "haw",
            "ln",
            "ha",
            "ba",
            "jw",
            "su",
        ]

    def get_provider_info(self) -> Dict[str, Any]:
        """Get OpenAI STT provider information."""
        return {
            "name": "OpenAI Whisper",
            "provider": "openai",
            "model": self.model,
            "supported_formats": ["wav", "mp3", "ogg", "flac", "m4a", "mp4"],
            "supported_languages": self.get_supported_languages(),
            "max_file_size": "25MB",
            "quality": "high",
            "pricing": "per_minute",
            "features": [
                "language_detection",
                "speaker_detection",
                "punctuation",
                "timestamps",
            ],
        }


class GoogleSTTProvider(STTProvider):
    """Google Speech-to-Text provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("google", config)
        self.api_key = config.get("api_key", "")
        self.project_id = config.get("project_id", "")
        self.location = config.get("location", "global")
        self.recognition_config = config.get("recognition_config", {})

    async def transcribe_audio(
        self,
        audio_data: bytes,
        audio_format: str,
        language: str = "en",
        session_id: str = None,
    ) -> TranscriptionResult:
        """Transcribe audio using Google Speech-to-Text."""
        start_time = time.time()

        try:
            # Preprocess audio
            processed_audio, output_format = self.preprocess_audio(
                audio_data, audio_format
            )

            # In a real implementation, this would call the Google Cloud API
            # For now, return a mock result
            processing_time = time.time() - start_time

            # Mock transcription based on audio data hash
            audio_hash = hashlib.md5(processed_audio).hexdigest()
            mock_transcription = f"Google transcription for audio {audio_hash[:8]}"

            return TranscriptionResult(
                transcription_id=f"google_trans_{audio_hash[:8]}",
                session_id=session_id or "default",
                text=mock_transcription,
                confidence=0.92,
                language=language,
                provider=self.provider_name,
                processing_time=processing_time,
            )

        except Exception as e:
            self.logger.error("Google STT transcription failed", error=str(e))
            raise

    async def get_supported_languages(self) -> List[str]:
        """Get supported languages for Google Speech-to-Text."""
        return [
            "en",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "ru",
            "ja",
            "ko",
            "zh",
            "ar",
            "hi",
            "bn",
            "pa",
            "te",
            "mr",
            "ta",
            "ur",
            "gu",
            "kn",
            "ml",
            "or",
            "as",
            "mai",
            "bho",
            "aw",
            "bg",
            "hr",
            "cs",
            "da",
            "nl",
            "fi",
            "el",
            "hu",
            "id",
            "lv",
            "lt",
            "no",
            "pl",
            "ro",
            "sr",
            "sk",
            "sl",
            "sv",
            "th",
            "tr",
            "uk",
            "vi",
        ]

    def get_provider_info(self) -> Dict[str, Any]:
        """Get Google STT provider information."""
        return {
            "name": "Google Speech-to-Text",
            "provider": "google",
            "supported_formats": ["wav", "flac", "ogg", "mp3", "m4a", "webm"],
            "supported_languages": self.get_supported_languages(),
            "max_file_size": "10MB",
            "quality": "high",
            "pricing": "per_minute",
            "features": [
                "language_detection",
                "speaker_diarization",
                "punctuation",
                "timestamps",
                "word_confidence",
            ],
        }


class STTService:
    """
    Main STT service with provider abstraction and failover.

    Features:
    - Multiple provider support with automatic failover
    - Audio format conversion and preprocessing
    - Transcription caching and performance optimization
    - Health monitoring and provider management
    - Confidence scoring and transcription validation
    - Comprehensive error handling and logging
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = get_logger(f"{__name__}.STTService")

        # Provider management
        self.providers: Dict[str, STTProvider] = {}
        self.provider_order = ["openai", "google"]  # Priority order
        self.fallback_enabled = True

        # Audio processing
        self.audio_config = AudioProcessingConfig()

        # Caching
        self.cache = STTCache(
            max_size=self.config.get("cache_size", 200),
            max_age_hours=self.config.get("cache_age_hours", 24),
        )

        # Performance tracking
        self._operation_times: Dict[str, float] = {}
        self._transcription_count = 0
        self._cache_hits = 0

        # Initialize providers
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize STT providers from configuration."""
        provider_configs = self.config.get("providers", {})

        # OpenAI Whisper
        if "openai" in provider_configs:
            self.providers["openai"] = OpenAISTTProvider(provider_configs["openai"])

        # Google Speech-to-Text
        if "google" in provider_configs:
            self.providers["google"] = GoogleSTTProvider(provider_configs["google"])

    async def transcribe_audio(
        self, request: AudioTranscriptionRequest, correlation_id: str = None
    ) -> TranscriptionResult:
        """
        Transcribe audio from request with provider failover.

        Args:
            request: STT request containing audio data and parameters
            correlation_id: Correlation ID for tracing

        Returns:
            Transcription result
        """
        start_time = time.time()

        try:
            with observability_service.trace_operation(
                operation_name="stt_transcription",
                audio_size=len(request.audio_data),
                audio_format=request.audio_format,
                correlation_id=correlation_id,
            ) as trace_id:
                # Check cache first
                cache_key = self._generate_cache_key(request)
                cached_result = self.cache.get(cache_key)

                if cached_result:
                    self._cache_hits += 1
                    self.logger.debug(
                        "stt_cache_hit",
                        correlation_id=correlation_id,
                        cache_key=cache_key,
                    )

                    # Return cached result as TranscriptionResult
                    return TranscriptionResult(
                        transcription_id=f"cached_{cached_result.cache_key[:8]}",
                        session_id=request.session_id,
                        text=cached_result.transcription,
                        confidence=cached_result.confidence,
                        language=cached_result.language,
                        provider="cached",
                        processing_time=cached_result.processing_time,
                    )

                # Preprocess audio
                processed_audio, output_format = self._preprocess_audio(
                    request.audio_data, request.audio_format
                )

                # Try providers in order
                last_error = None
                for provider_name in self.provider_order:
                    if provider_name not in self.providers:
                        continue

                    provider = self.providers[provider_name]
                    provider_health = provider.get_health_status()

                    # Skip unhealthy providers
                    if provider_health.status == "unhealthy":
                        continue

                    try:
                        self.logger.debug(
                            "trying_stt_provider",
                            provider=provider_name,
                            audio_format=request.audio_format,
                            language=request.language,
                            correlation_id=correlation_id,
                        )

                        result = await provider.transcribe_audio(
                            audio_data=processed_audio,
                            audio_format=output_format,
                            language=request.language,
                            session_id=request.session_id,
                        )

                        # Update provider health on success
                        await provider.check_health()

                        # Cache the result
                        self.cache.put(
                            cache_key,
                            result.text,
                            result.confidence,
                            result.language,
                            result.provider,
                            processed_audio,
                            result.processing_time,
                        )

                        # Update metrics
                        self._transcription_count += 1
                        execution_time = time.time() - start_time
                        self._operation_times[correlation_id] = execution_time

                        self.logger.info(
                            "stt_transcription_successful",
                            provider=provider_name,
                            confidence=result.confidence,
                            language=result.language,
                            text_length=len(result.text),
                            processing_time=result.processing_time,
                            correlation_id=correlation_id,
                            trace_id=trace_id,
                        )

                        return result

                    except Exception as e:
                        last_error = e
                        self.logger.warning(
                            "stt_provider_failed",
                            provider=provider_name,
                            error=str(e),
                            correlation_id=correlation_id,
                        )

                        # Update provider health on failure
                        await provider.check_health()

                        # Continue to next provider if fallback is enabled
                        if not self.fallback_enabled:
                            break

                # All providers failed
                execution_time = time.time() - start_time
                error_msg = f"All STT providers failed. Last error: {str(last_error) if last_error else 'Unknown'}"

                self.logger.error(
                    "stt_transcription_failed_all_providers",
                    correlation_id=correlation_id,
                    execution_time=execution_time,
                    error=error_msg,
                )

                # Return error result
                return TranscriptionResult(
                    transcription_id=f"error_{hashlib.md5(request.audio_data).hexdigest()[:8]}",
                    session_id=request.session_id,
                    text="",
                    confidence=0.0,
                    language=request.language,
                    provider="error",
                    processing_time=execution_time,
                    error=error_msg,
                )

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(
                "stt_transcription_error",
                correlation_id=correlation_id,
                execution_time=execution_time,
                error=str(e),
            )

            return TranscriptionResult(
                transcription_id=f"error_{hashlib.md5(request.audio_data).hexdigest()[:8]}",
                session_id=request.session_id,
                text="",
                confidence=0.0,
                language=request.language,
                provider="error",
                processing_time=execution_time,
                error=str(e),
            )

    def _preprocess_audio(
        self, audio_data: bytes, input_format: str
    ) -> Tuple[bytes, str]:
        """
        Preprocess audio data for optimal transcription.

        Args:
            audio_data: Raw audio data
            input_format: Input audio format

        Returns:
            Tuple of (processed_audio_data, output_format)
        """
        # In a real implementation, this would:
        # 1. Convert unsupported formats to WAV
        # 2. Normalize audio levels
        # 3. Remove excessive silence
        # 4. Apply noise reduction if configured
        # 5. Ensure correct sample rate and channels

        # For now, return as-is with WAV format (assuming conversion)
        return audio_data, "wav"

    def _generate_cache_key(self, request: AudioTranscriptionRequest) -> str:
        """Generate cache key for STT request."""
        key_components = [
            hashlib.md5(request.audio_data).hexdigest(),
            request.audio_format,
            request.language,
            request.provider or "any",
            str(request.session_id),
        ]
        return hashlib.md5("|".join(key_components).encode("utf-8")).hexdigest()

    async def get_supported_languages(
        self, provider: Optional[str] = None
    ) -> List[str]:
        """Get all supported languages across providers."""
        all_languages = set()

        if provider and provider in self.providers:
            # Get languages from specific provider
            languages = await self.providers[provider].get_supported_languages()
            all_languages.update(languages)
        else:
            # Get languages from all providers
            for provider_instance in self.providers.values():
                try:
                    languages = await provider_instance.get_supported_languages()
                    all_languages.update(languages)
                except Exception as e:
                    self.logger.warning(
                        "failed_to_get_languages_from_provider",
                        provider=provider_instance.provider_name,
                        error=str(e),
                    )

        return sorted(list(all_languages))

    async def get_provider_health(self) -> Dict[str, ProviderHealthStatus]:
        """Get health status of all providers."""
        health_status = {}

        for name, provider in self.providers.items():
            try:
                health_status[name] = await provider.check_health()
            except Exception as e:
                self.logger.error(
                    "provider_health_check_failed", provider=name, error=str(e)
                )
                health_status[name] = provider.get_health_status()

        return health_status

    def get_service_status(self) -> STTServiceStatus:
        """Get overall STT service status."""
        provider_health = list(self.get_provider_health().values())
        healthy_providers = len([h for h in provider_health if h.status == "healthy"])

        cache_stats = self.cache.stats()

        return STTServiceStatus(
            is_available=healthy_providers > 0,
            active_transcriptions=0,  # Would track active operations
            queued_requests=0,  # Would track queued requests
            healthy_providers=healthy_providers,
            total_providers=len(self.providers),
            average_response_time=sum(h.response_time for h in provider_health)
            / max(len(provider_health), 1),
            last_activity=datetime.utcnow(),
            service_uptime=0.0,  # Would track actual uptime
        )

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of the STT service."""
        provider_health = self.get_provider_health()
        cache_stats = self.cache.stats()

        return {
            "status": "healthy"
            if any(h.status == "healthy" for h in provider_health.values())
            else "error",
            "providers": {
                name: health.__dict__ for name, health in provider_health.items()
            },
            "cache": cache_stats,
            "transcription_count": self._transcription_count,
            "cache_hit_rate": self._cache_hits / max(self._transcription_count, 1),
            "average_operation_time": sum(self._operation_times.values())
            / max(len(self._operation_times), 1),
            "audio_config": self.audio_config.__dict__,
            "config": {
                "provider_order": self.provider_order,
                "fallback_enabled": self.fallback_enabled,
                "cache_size": self.cache.max_size,
            },
        }

    def clear_cache(self) -> bool:
        """Clear the STT cache."""
        self.cache.clear()
        self.logger.info("stt_cache_cleared")
        return True

    async def warmup_providers(self) -> Dict[str, bool]:
        """Warm up all providers by checking their health."""
        results = {}

        for name, provider in self.providers.items():
            try:
                await provider.check_health()
                results[name] = True
                self.logger.info("provider_warmup_successful", provider=name)
            except Exception as e:
                results[name] = False
                self.logger.error("provider_warmup_failed", provider=name, error=str(e))

        return results


# Global STT service instance
stt_service = STTService()
