"""
TTS (Text-to-Speech) Service Component for AI Dungeon Master.

This module provides comprehensive text-to-speech functionality with provider abstraction,
supporting multiple TTS services with automatic fallback and voice consistency.

Features:
- Provider-agnostic TTS interface supporting multiple services
- Voice selection and audio format configuration
- Provider health monitoring and automatic failover
- Audio caching and performance optimization
- Voice consistency across provider switches
- Comprehensive error handling and logging
"""

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger
from packages.shared.models import (
    ProviderHealthStatus,
    SpeechSynthesisResult,
    TextToSpeechRequest,
    TTSServiceStatus,
)

logger = get_logger(__name__)


@dataclass
class VoiceInfo:
    """Information about a TTS voice."""

    voice_id: str
    name: str
    language: str
    gender: str
    age: Optional[str] = None
    accent: Optional[str] = None
    provider: str = ""
    quality: str = "standard"  # standard, high, premium
    sample_rate: int = 22050
    supported_formats: List[str] = field(default_factory=lambda: ["wav", "mp3"])
    description: str = ""


@dataclass
class TTSCacheEntry:
    """Cache entry for TTS results."""

    cache_key: str
    audio_data: bytes
    format: str
    voice_id: str
    text_hash: str
    created_at: datetime
    access_count: int = 0
    size_bytes: int = 0


class TTSCache:
    """Simple in-memory cache for TTS results."""

    def __init__(self, max_size: int = 100, max_age_hours: int = 24):
        self.max_size = max_size
        self.max_age = timedelta(hours=max_age_hours)
        self._cache: Dict[str, TTSCacheEntry] = {}
        self._access_order: List[str] = []

    def get(self, key: str) -> Optional[bytes]:
        """Get cached audio data."""
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

        return entry.audio_data

    def put(
        self, key: str, audio_data: bytes, voice_id: str, text: str, format: str
    ) -> None:
        """Cache audio data."""
        # Generate text hash for cache key
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()

        entry = TTSCacheEntry(
            cache_key=key,
            audio_data=audio_data,
            format=format,
            voice_id=voice_id,
            text_hash=text_hash,
            created_at=datetime.utcnow(),
            size_bytes=len(audio_data),
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


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    def __init__(self, provider_name: str, config: Dict[str, Any]):
        self.provider_name = provider_name
        self.config = config
        self.logger = get_logger(f"{__name__}.{provider_name}Provider")
        self._health_status: ProviderHealthStatus = self._create_initial_health_status()

    @abstractmethod
    async def synthesize_speech(
        self,
        text: str,
        voice_id: str,
        language: str = "en-US",
        speed: float = 1.0,
        pitch: float = 1.0,
        volume: float = 1.0,
        output_format: str = "wav",
    ) -> SpeechSynthesisResult:
        """Synthesize speech from text."""
        pass

    @abstractmethod
    async def get_available_voices(
        self, language: Optional[str] = None
    ) -> List[VoiceInfo]:
        """Get list of available voices."""
        pass

    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information and capabilities."""
        pass

    def _create_initial_health_status(self) -> ProviderHealthStatus:
        """Create initial health status for the provider."""
        return ProviderHealthStatus(
            provider_name=self.provider_name,
            service_type="tts",
            status="unknown",
            response_time=0.0,
            success_rate=0.0,
            last_check=datetime.utcnow(),
        )

    async def check_health(self) -> ProviderHealthStatus:
        """Check provider health and update status."""
        start_time = time.time()

        try:
            # Simple health check - try to get voices
            voices = await self.get_available_voices()
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


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("openai", config)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "tts-1")
        self.default_voice = config.get("default_voice", "alloy")

    async def synthesize_speech(
        self,
        text: str,
        voice_id: str,
        language: str = "en-US",
        speed: float = 1.0,
        pitch: float = 1.0,
        volume: float = 1.0,
        output_format: str = "wav",
    ) -> SpeechSynthesisResult:
        """Synthesize speech using OpenAI TTS."""
        start_time = time.time()

        try:
            # In a real implementation, this would call the OpenAI API
            # For now, return a mock result
            processing_time = time.time() - start_time

            # Mock audio data (would be real audio from OpenAI)
            mock_audio_data = b"mock_openai_audio_data_" + text.encode("utf-8")[:50]

            return SpeechSynthesisResult(
                audio_data=mock_audio_data,
                audio_format=output_format,
                sample_rate=22050,
                channels=1,
                duration=len(text) * 0.1,  # Rough estimate
                voice_used=voice_id,
                provider=self.provider_name,
                processing_time=processing_time,
                file_size=len(mock_audio_data),
            )

        except Exception as e:
            self.logger.error("OpenAI TTS synthesis failed", error=str(e))
            raise

    async def get_available_voices(
        self, language: Optional[str] = None
    ) -> List[VoiceInfo]:
        """Get available OpenAI voices."""
        voices = [
            VoiceInfo(
                voice_id="alloy",
                name="Alloy",
                language="en-US",
                gender="neutral",
                provider="openai",
                quality="high",
                description="Clear and confident voice",
            ),
            VoiceInfo(
                voice_id="echo",
                name="Echo",
                language="en-US",
                gender="male",
                provider="openai",
                quality="high",
                description="Warm and friendly male voice",
            ),
            VoiceInfo(
                voice_id="fable",
                name="Fable",
                language="en-US",
                gender="female",
                provider="openai",
                quality="high",
                description="Expressive female voice",
            ),
            VoiceInfo(
                voice_id="onyx",
                name="Onyx",
                language="en-US",
                gender="male",
                provider="openai",
                quality="high",
                description="Deep and authoritative male voice",
            ),
            VoiceInfo(
                voice_id="nova",
                name="Nova",
                language="en-US",
                gender="female",
                provider="openai",
                quality="high",
                description="Bright and energetic female voice",
            ),
            VoiceInfo(
                voice_id="shimmer",
                name="Shimmer",
                language="en-US",
                gender="female",
                provider="openai",
                quality="high",
                description="Gentle and soft female voice",
            ),
        ]

        if language:
            voices = [v for v in voices if v.language == language]

        return voices

    def get_provider_info(self) -> Dict[str, Any]:
        """Get OpenAI TTS provider information."""
        return {
            "name": "OpenAI TTS",
            "provider": "openai",
            "model": self.model,
            "supported_formats": ["mp3", "opus", "aac", "flac"],
            "supported_languages": [
                "en-US",
                "en-GB",
                "es-ES",
                "fr-FR",
                "de-DE",
                "it-IT",
            ],
            "voice_count": 6,
            "quality": "high",
            "pricing": "per_character",
        }


class ElevenLabsTTSProvider(TTSProvider):
    """ElevenLabs TTS provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("elevenlabs", config)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.elevenlabs.io/v1")
        self.model = config.get("model", "eleven_monolingual_v1")
        self.default_voice = config.get("default_voice", "21m00Tcm4TlvDq8ikWAM")

    async def synthesize_speech(
        self,
        text: str,
        voice_id: str,
        language: str = "en-US",
        speed: float = 1.0,
        pitch: float = 1.0,
        volume: float = 1.0,
        output_format: str = "wav",
    ) -> SpeechSynthesisResult:
        """Synthesize speech using ElevenLabs."""
        start_time = time.time()

        try:
            # In a real implementation, this would call the ElevenLabs API
            processing_time = time.time() - start_time

            # Mock audio data (would be real audio from ElevenLabs)
            mock_audio_data = b"mock_elevenlabs_audio_data_" + text.encode("utf-8")[:50]

            return SpeechSynthesisResult(
                audio_data=mock_audio_data,
                audio_format=output_format,
                sample_rate=22050,
                channels=1,
                duration=len(text) * 0.08,  # Rough estimate
                voice_used=voice_id,
                provider=self.provider_name,
                processing_time=processing_time,
                file_size=len(mock_audio_data),
            )

        except Exception as e:
            self.logger.error("ElevenLabs TTS synthesis failed", error=str(e))
            raise

    async def get_available_voices(
        self, language: Optional[str] = None
    ) -> List[VoiceInfo]:
        """Get available ElevenLabs voices."""
        voices = [
            VoiceInfo(
                voice_id="21m00Tcm4TlvDq8ikWAM",
                name="Rachel",
                language="en-US",
                gender="female",
                age="young",
                provider="elevenlabs",
                quality="premium",
                description="Calm and professional female voice",
            ),
            VoiceInfo(
                voice_id="29vD33N1CtxCmqQRPOHJ",
                name="Drew",
                language="en-US",
                gender="male",
                age="middle-aged",
                provider="elevenlabs",
                quality="premium",
                description="Deep and resonant male voice",
            ),
            VoiceInfo(
                voice_id="2EiwWnXFnvU5JabPnv8n",
                name="Clyde",
                language="en-US",
                gender="male",
                age="middle-aged",
                provider="elevenlabs",
                quality="premium",
                description="Warm and friendly male voice",
            ),
            VoiceInfo(
                voice_id="EXAVITQu4vr4xnSDxMaL",
                name="Paul",
                language="en-US",
                gender="male",
                age="middle-aged",
                provider="elevenlabs",
                quality="premium",
                description="Confident and clear male voice",
            ),
            VoiceInfo(
                voice_id="ErXwobaYiN019PkySvjV",
                name="Antoni",
                language="en-US",
                gender="male",
                age="young",
                provider="elevenlabs",
                quality="premium",
                description="Energetic and youthful male voice",
            ),
            VoiceInfo(
                voice_id="VR6AewLTigWG4xSOukaG",
                name="Arnold",
                language="en-US",
                gender="male",
                age="middle-aged",
                provider="elevenlabs",
                quality="premium",
                description="Authoritative and strong male voice",
            ),
            VoiceInfo(
                voice_id="pNInz6obpgDQGcFmaJgB",
                name="Domi",
                language="en-US",
                gender="female",
                age="young",
                provider="elevenlabs",
                quality="premium",
                description="Sweet and approachable female voice",
            ),
            VoiceInfo(
                voice_id="yoZ06aMxZJJ28mfd3POQ",
                name="Fin",
                language="en-US",
                gender="male",
                age="young",
                provider="elevenlabs",
                quality="premium",
                description="Playful and fun male voice",
            ),
        ]

        if language:
            voices = [v for v in voices if v.language == language]

        return voices

    def get_provider_info(self) -> Dict[str, Any]:
        """Get ElevenLabs provider information."""
        return {
            "name": "ElevenLabs",
            "provider": "elevenlabs",
            "model": self.model,
            "supported_formats": ["mp3", "wav", "flac", "ogg"],
            "supported_languages": [
                "en-US",
                "es-ES",
                "fr-FR",
                "de-DE",
                "it-IT",
                "pt-BR",
                "pl-PL",
            ],
            "voice_count": 8,
            "quality": "premium",
            "pricing": "per_character",
        }


class TTSService:
    """
    Main TTS service with provider abstraction and failover.

    Features:
    - Multiple provider support with automatic failover
    - Voice consistency and mapping across providers
    - Audio caching and performance optimization
    - Health monitoring and provider management
    - Comprehensive error handling and logging
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = get_logger(f"{__name__}.TTSService")

        # Provider management
        self.providers: Dict[str, TTSProvider] = {}
        self.provider_order = ["elevenlabs", "openai"]  # Priority order
        self.fallback_enabled = True

        # Caching
        self.cache = TTSCache(
            max_size=self.config.get("cache_size", 100),
            max_age_hours=self.config.get("cache_age_hours", 24),
        )

        # Voice mapping for consistency across providers
        self.voice_mappings: Dict[str, Dict[str, str]] = {}

        # Performance tracking
        self._operation_times: Dict[str, float] = {}
        self._synthesis_count = 0
        self._cache_hits = 0

        # Initialize providers
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize TTS providers from configuration."""
        provider_configs = self.config.get("providers", {})

        # OpenAI TTS
        if "openai" in provider_configs:
            self.providers["openai"] = OpenAITTSProvider(provider_configs["openai"])

        # ElevenLabs TTS
        if "elevenlabs" in provider_configs:
            self.providers["elevenlabs"] = ElevenLabsTTSProvider(
                provider_configs["elevenlabs"]
            )

        # Set up voice mappings for consistency
        self._setup_voice_mappings()

    def _setup_voice_mappings(self) -> None:
        """Set up voice mappings for consistency across providers."""
        # Map common voice characteristics to provider-specific voice IDs
        self.voice_mappings = {
            "female_young": {
                "elevenlabs": "pNInz6obpgDQGcFmaJgB",  # Domi
                "openai": "nova",  # Nova
            },
            "female_mature": {
                "elevenlabs": "21m00Tcm4TlvDq8ikWAM",  # Rachel
                "openai": "shimmer",  # Shimmer
            },
            "male_young": {
                "elevenlabs": "ErXwobaYiN019PkySvjV",  # Antoni
                "openai": "echo",  # Echo
            },
            "male_mature": {
                "elevenlabs": "29vD33N1CtxCmqQRPOHJ",  # Drew
                "openai": "onyx",  # Onyx
            },
            "neutral": {
                "elevenlabs": "21m00Tcm4TlvDq8ikWAM",  # Rachel (neutral)
                "openai": "alloy",  # Alloy
            },
        }

    async def synthesize_speech(
        self, request: TextToSpeechRequest, correlation_id: str = None
    ) -> SpeechSynthesisResult:
        """
        Synthesize speech from text with provider failover.

        Args:
            request: TTS request containing text and voice parameters
            correlation_id: Correlation ID for tracing

        Returns:
            Speech synthesis result
        """
        start_time = time.time()

        try:
            with observability_service.trace_operation(
                operation_name="tts_synthesis",
                text_length=len(request.text),
                correlation_id=correlation_id,
            ) as trace_id:
                # Check cache first
                cache_key = self._generate_cache_key(request)
                cached_result = self.cache.get(cache_key)

                if cached_result:
                    self._cache_hits += 1
                    self.logger.debug(
                        "tts_cache_hit",
                        correlation_id=correlation_id,
                        cache_key=cache_key,
                    )

                    # Return cached result (would need to reconstruct SpeechSynthesisResult)
                    return SpeechSynthesisResult(
                        audio_data=cached_result,
                        audio_format=request.output_format or "wav",
                        sample_rate=22050,
                        channels=1,
                        duration=len(request.text) * 0.1,
                        voice_used=request.voice or "default",
                        provider="cached",
                        processing_time=0.001,
                        file_size=len(cached_result),
                    )

                # Map voice ID to provider-specific voice
                mapped_voice = self._map_voice_id(request.voice or "default")

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
                            "trying_tts_provider",
                            provider=provider_name,
                            voice=request.voice,
                            mapped_voice=mapped_voice.get(provider_name),
                            correlation_id=correlation_id,
                        )

                        # Use mapped voice for this provider
                        provider_voice = mapped_voice.get(
                            provider_name, request.voice or "default"
                        )

                        result = await provider.synthesize_speech(
                            text=request.text,
                            voice_id=provider_voice,
                            language=request.language or "en-US",
                            speed=request.speed or 1.0,
                            pitch=request.pitch or 1.0,
                            volume=request.volume or 1.0,
                            output_format=request.output_format or "wav",
                        )

                        # Update provider health on success
                        await provider.check_health()

                        # Cache the result
                        self.cache.put(
                            cache_key,
                            result.audio_data,
                            result.voice_used,
                            request.text,
                            result.audio_format,
                        )

                        # Update metrics
                        self._synthesis_count += 1
                        execution_time = time.time() - start_time
                        self._operation_times[correlation_id] = execution_time

                        self.logger.info(
                            "tts_synthesis_successful",
                            provider=provider_name,
                            voice=result.voice_used,
                            duration=result.duration,
                            processing_time=result.processing_time,
                            correlation_id=correlation_id,
                            trace_id=trace_id,
                        )

                        return result

                    except Exception as e:
                        last_error = e
                        self.logger.warning(
                            "tts_provider_failed",
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
                error_msg = f"All TTS providers failed. Last error: {str(last_error) if last_error else 'Unknown'}"

                self.logger.error(
                    "tts_synthesis_failed_all_providers",
                    correlation_id=correlation_id,
                    execution_time=execution_time,
                    error=error_msg,
                )

                # Return error result
                return SpeechSynthesisResult(
                    audio_data=b"",
                    audio_format=request.output_format or "wav",
                    sample_rate=22050,
                    channels=1,
                    duration=0.0,
                    voice_used=request.voice or "default",
                    provider="error",
                    processing_time=execution_time,
                    file_size=0,
                    error=error_msg,
                )

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(
                "tts_synthesis_error",
                correlation_id=correlation_id,
                execution_time=execution_time,
                error=str(e),
            )

            return SpeechSynthesisResult(
                audio_data=b"",
                audio_format=request.output_format or "wav",
                sample_rate=22050,
                channels=1,
                duration=0.0,
                voice_used=request.voice or "default",
                provider="error",
                processing_time=execution_time,
                file_size=0,
                error=str(e),
            )

    def _generate_cache_key(self, request: TextToSpeechRequest) -> str:
        """Generate cache key for TTS request."""
        key_components = [
            request.text,
            request.voice or "default",
            request.language or "en-US",
            str(request.speed or 1.0),
            str(request.pitch or 1.0),
            str(request.volume or 1.0),
            request.output_format or "wav",
        ]
        return hashlib.md5("|".join(key_components).encode("utf-8")).hexdigest()

    def _map_voice_id(self, voice_id: str) -> Dict[str, str]:
        """Map a generic voice ID to provider-specific voice IDs."""
        # If voice_id is already a specific provider voice, return as-is
        if ":" in voice_id:
            provider, specific_voice = voice_id.split(":", 1)
            return {provider: specific_voice}

        # Map generic voice characteristics to provider voices
        if voice_id in self.voice_mappings:
            return self.voice_mappings[voice_id].copy()

        # Default mapping
        return {
            "elevenlabs": "21m00Tcm4TlvDq8ikWAM",  # Rachel
            "openai": "alloy",  # Alloy
        }

    async def get_available_voices(
        self, provider: Optional[str] = None
    ) -> List[VoiceInfo]:
        """Get all available voices across providers."""
        all_voices = []

        if provider and provider in self.providers:
            # Get voices from specific provider
            voices = await self.providers[provider].get_available_voices()
            all_voices.extend(voices)
        else:
            # Get voices from all providers
            for provider_instance in self.providers.values():
                try:
                    voices = await provider_instance.get_available_voices()
                    all_voices.extend(voices)
                except Exception as e:
                    self.logger.warning(
                        "failed_to_get_voices_from_provider",
                        provider=provider_instance.provider_name,
                        error=str(e),
                    )

        return all_voices

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

    def get_service_status(self) -> TTSServiceStatus:
        """Get overall TTS service status."""
        provider_health = list(self.get_provider_health().values())
        healthy_providers = len([h for h in provider_health if h.status == "healthy"])

        cache_stats = self.cache.stats()

        return TTSServiceStatus(
            is_available=healthy_providers > 0,
            active_syntheses=0,  # Would track active operations
            queued_requests=0,  # Would track queued requests
            healthy_providers=healthy_providers,
            total_providers=len(self.providers),
            average_response_time=sum(h.response_time for h in provider_health)
            / max(len(provider_health), 1),
            last_activity=datetime.utcnow(),
            service_uptime=0.0,  # Would track actual uptime
        )

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of the TTS service."""
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
            "synthesis_count": self._synthesis_count,
            "cache_hit_rate": self._cache_hits / max(self._synthesis_count, 1),
            "average_operation_time": sum(self._operation_times.values())
            / max(len(self._operation_times), 1),
            "config": {
                "provider_order": self.provider_order,
                "fallback_enabled": self.fallback_enabled,
                "cache_size": self.cache.max_size,
            },
        }

    def clear_cache(self) -> bool:
        """Clear the TTS cache."""
        self.cache.clear()
        self.logger.info("tts_cache_cleared")
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


# Global TTS service instance
tts_service = TTSService()
