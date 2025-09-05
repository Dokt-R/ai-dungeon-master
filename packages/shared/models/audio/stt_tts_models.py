"""
STT/TTS Service Models (for speech-to-text and text-to-speech services)
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import (
    BaseModel,
    Field as PydanticField,
)


class AudioTranscriptionRequest(BaseModel):
    """Request to transcribe audio to text."""

    audio_data: bytes = PydanticField(..., description="Raw audio data to transcribe")

    audio_format: Literal["wav", "mp3", "ogg", "flac", "webm"] = PydanticField(
        ..., description="Audio format of the input data"
    )

    sample_rate: int = PydanticField(
        ..., description="Sample rate in Hz", ge=8000, le=192000
    )

    channels: int = PydanticField(
        ..., description="Number of audio channels", ge=1, le=2
    )

    language: Optional[str] = PydanticField(
        "en-US",
        description="Language code for transcription",
        pattern=r"^[a-z]{2}-[A-Z]{2}$",
    )

    provider: Optional[str] = PydanticField(
        "auto", description="Preferred STT provider"
    )

    session_id: Optional[str] = PydanticField(
        None, description="Session identifier for tracking"
    )

    user_id: Optional[str] = PydanticField(None, description="User identifier")

    metadata: Optional[Dict[str, Any]] = PydanticField(
        None, description="Additional request metadata"
    )


class TranscriptionResult(BaseModel):
    """Result of speech-to-text transcription."""

    transcription_id: str = PydanticField(
        ..., description="Unique transcription identifier"
    )

    session_id: Optional[str] = PydanticField(
        None, description="Session identifier for tracking"
    )

    text: str = PydanticField(..., description="Transcribed text", min_length=1)

    confidence: float = PydanticField(
        ..., description="Confidence score (0.0 to 1.0)", ge=0.0, le=1.0
    )

    language: str = PydanticField(
        ...,
        description="Detected or specified language",
        pattern=r"^[a-z]{2}-[A-Z]{2}$",
    )

    duration: float = PydanticField(
        ..., description="Audio duration in seconds", ge=0.0
    )

    provider: str = PydanticField(..., description="STT provider used")

    word_timestamps: Optional[List[Dict[str, Any]]] = PydanticField(
        None, description="Word-level timestamps"
    )

    segments: Optional[List[Dict[str, Any]]] = PydanticField(
        None, description="Segment-level results"
    )

    processing_time: float = PydanticField(
        ..., description="Processing time in seconds", ge=0.0
    )

    error: Optional[str] = PydanticField(
        None, description="Error message if transcription failed"
    )


class TextToSpeechRequest(BaseModel):
    """Request to convert text to speech."""

    text: str = PydanticField(
        ..., description="Text to convert to speech", min_length=1, max_length=4000
    )

    voice: Optional[str] = PydanticField(
        "default", description="Voice identifier to use"
    )

    language: Optional[str] = PydanticField(
        "en-US",
        description="Language code for speech synthesis",
        pattern=r"^[a-z]{2}-[A-Z]{2}$",
    )

    speed: Optional[float] = PydanticField(
        1.0, description="Speech speed (0.5 to 2.0)", ge=0.5, le=2.0
    )

    pitch: Optional[float] = PydanticField(
        1.0, description="Voice pitch (0.5 to 2.0)", ge=0.5, le=2.0
    )

    volume: Optional[float] = PydanticField(
        1.0, description="Volume level (0.0 to 1.0)", ge=0.0, le=1.0
    )

    provider: Optional[str] = PydanticField(
        "auto", description="Preferred TTS provider"
    )

    output_format: Optional[Literal["wav", "mp3", "ogg", "flac"]] = PydanticField(
        "wav", description="Output audio format"
    )

    session_id: Optional[str] = PydanticField(
        None, description="Session identifier for tracking"
    )

    user_id: Optional[str] = PydanticField(None, description="User identifier")

    metadata: Optional[Dict[str, Any]] = PydanticField(
        None, description="Additional request metadata"
    )


class SpeechSynthesisResult(BaseModel):
    """Result of text-to-speech synthesis."""

    audio_data: bytes = PydanticField(..., description="Generated audio data")

    audio_format: str = PydanticField(..., description="Format of the generated audio")

    sample_rate: int = PydanticField(..., description="Sample rate in Hz")

    channels: int = PydanticField(..., description="Number of audio channels")

    duration: float = PydanticField(
        ..., description="Audio duration in seconds", ge=0.0
    )

    voice_used: str = PydanticField(..., description="Voice identifier used")

    provider: str = PydanticField(..., description="TTS provider used")

    processing_time: float = PydanticField(
        ..., description="Processing time in seconds", ge=0.0
    )

    file_size: int = PydanticField(
        ..., description="Size of generated audio in bytes", ge=0
    )

    error: Optional[str] = PydanticField(
        None, description="Error message if synthesis failed"
    )


class AudioProcessingConfig(BaseModel):
    """Configuration for audio processing operations."""

    chunk_size: int = PydanticField(
        1024, description="Audio chunk size for processing", ge=64, le=8192
    )

    overlap_size: int = PydanticField(
        256, description="Overlap size between chunks", ge=0, le=4096
    )

    silence_threshold: float = PydanticField(
        0.01, description="Threshold for silence detection (0.0 to 1.0)", ge=0.0, le=1.0
    )

    min_speech_duration: float = PydanticField(
        0.1, description="Minimum speech duration in seconds", ge=0.0, le=5.0
    )

    max_speech_duration: float = PydanticField(
        30.0, description="Maximum speech duration in seconds", ge=1.0, le=300.0
    )

    vad_mode: Literal["aggressive", "normal", "light"] = PydanticField(
        "normal", description="Voice activity detection sensitivity"
    )

    noise_reduction: bool = PydanticField(True, description="Enable noise reduction")

    normalize_audio: bool = PydanticField(
        True, description="Enable audio normalization"
    )


class ProviderHealthStatus(BaseModel):
    """Health status for STT/TTS providers."""

    provider_name: str = PydanticField(..., description="Name of the provider")

    service_type: Literal["stt", "tts"] = PydanticField(
        ..., description="Type of service"
    )

    status: Literal["healthy", "degraded", "unhealthy"] = PydanticField(
        ..., description="Current health status"
    )

    response_time: float = PydanticField(
        ..., description="Average response time in seconds", ge=0.0
    )

    success_rate: float = PydanticField(
        ..., description="Success rate (0.0 to 1.0)", ge=0.0, le=1.0
    )

    last_check: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Last health check timestamp"
    )

    consecutive_failures: int = PydanticField(
        0, description="Number of consecutive failures", ge=0
    )

    total_requests: int = PydanticField(0, description="Total requests made", ge=0)

    error_message: Optional[str] = PydanticField(
        None, description="Last error message", max_length=500
    )

    is_primary: bool = PydanticField(
        False, description="Whether this is the primary provider"
    )


class STTServiceStatus(BaseModel):
    """Overall status of the STT service."""

    is_available: bool = PydanticField(
        ..., description="Whether STT service is available"
    )

    active_streams: int = PydanticField(
        0, description="Number of active audio streams", ge=0
    )

    queued_requests: int = PydanticField(
        0, description="Number of queued transcription requests", ge=0
    )

    healthy_providers: int = PydanticField(
        0, description="Number of healthy providers", ge=0
    )

    total_providers: int = PydanticField(
        0, description="Total number of configured providers", ge=0
    )

    average_response_time: float = PydanticField(
        0.0, description="Average response time across all providers", ge=0.0
    )

    last_activity: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Last STT service activity"
    )

    service_uptime: float = PydanticField(
        0.0, description="Service uptime in seconds", ge=0.0
    )


class TTSServiceStatus(BaseModel):
    """Overall status of the TTS service."""

    is_available: bool = PydanticField(
        ..., description="Whether TTS service is available"
    )

    active_syntheses: int = PydanticField(
        0, description="Number of active speech syntheses", ge=0
    )

    queued_requests: int = PydanticField(
        0, description="Number of queued synthesis requests", ge=0
    )

    healthy_providers: int = PydanticField(
        0, description="Number of healthy providers", ge=0
    )

    total_providers: int = PydanticField(
        0, description="Total number of configured providers", ge=0
    )

    average_response_time: float = PydanticField(
        0.0, description="Average response time across all providers", ge=0.0
    )

    last_activity: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Last TTS service activity"
    )

    service_uptime: float = PydanticField(
        0.0, description="Service uptime in seconds", ge=0.0
    )
