"""
Performance Models
Models for performance optimization and quality enhancement.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field as PydanticField


class VoiceLatencyMetrics(BaseModel):
    """Voice interaction latency tracking."""

    session_id: str = PydanticField(..., description="Voice session identifier")

    user_speech_start: datetime = PydanticField(
        ..., description="User speech start time"
    )

    transcription_complete: Optional[datetime] = PydanticField(
        None, description="STT completion time"
    )

    ai_processing_start: Optional[datetime] = PydanticField(
        None, description="AI processing start time"
    )

    ai_response_complete: Optional[datetime] = PydanticField(
        None, description="AI response completion time"
    )

    tts_generation_complete: Optional[datetime] = PydanticField(
        None, description="TTS completion time"
    )

    audio_playback_start: Optional[datetime] = PydanticField(
        None, description="Audio playback start time"
    )

    total_latency: Optional[float] = PydanticField(
        None, description="Total roundtrip latency in seconds"
    )

    stt_latency: Optional[float] = PydanticField(
        None, description="STT processing latency in seconds"
    )

    ai_latency: Optional[float] = PydanticField(
        None, description="AI processing latency in seconds"
    )

    tts_latency: Optional[float] = PydanticField(
        None, description="TTS generation latency in seconds"
    )

    audio_delivery_latency: Optional[float] = PydanticField(
        None, description="Audio delivery latency in seconds"
    )

    network_latency: Optional[float] = PydanticField(
        None, description="Network transmission latency in seconds"
    )

    processing_stage: str = PydanticField(
        default="speech_start", description="Current processing stage"
    )

    correlation_id: Optional[str] = PydanticField(
        None, description="Correlation ID for tracing"
    )

    metadata: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Additional latency metadata"
    )


class AudioQualityMetrics(BaseModel):
    """Audio quality assessment metrics."""

    session_id: str = PydanticField(..., description="Voice session identifier")

    transcription_accuracy: Optional[float] = PydanticField(
        None, ge=0.0, le=1.0, description="STT accuracy score"
    )

    voice_clarity: Optional[float] = PydanticField(
        None, ge=0.0, le=5.0, description="Voice synthesis clarity rating"
    )

    audio_artifacts: int = PydanticField(
        default=0, ge=0, description="Number of audio artifacts detected"
    )

    noise_level: Optional[float] = PydanticField(
        None, ge=0.0, le=1.0, description="Background noise level (0.0 to 1.0)"
    )

    signal_to_noise_ratio: Optional[float] = PydanticField(
        None, description="Signal-to-noise ratio in dB"
    )

    audio_bitrate: Optional[int] = PydanticField(
        None, description="Audio bitrate in bits per second"
    )

    sample_rate: Optional[int] = PydanticField(
        None, description="Audio sample rate in Hz"
    )

    audio_format: Optional[str] = PydanticField(None, description="Audio format used")

    user_feedback: Optional[str] = PydanticField(
        None, description="User feedback on quality"
    )

    quality_score: Optional[float] = PydanticField(
        None, ge=0.0, le=1.0, description="Overall quality score"
    )

    provider_performance: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Provider-specific performance metrics"
    )

    timestamp: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Metrics collection timestamp"
    )

    correlation_id: Optional[str] = PydanticField(
        None, description="Correlation ID for tracing"
    )


class VoiceSessionConfig(BaseModel):
    """Voice session configuration and limits."""

    max_concurrent_sessions: int = PydanticField(
        default=10, ge=1, le=100, description="Maximum concurrent voice sessions"
    )

    session_timeout: int = PydanticField(
        default=3600, ge=300, le=86400, description="Session timeout in seconds"
    )

    max_session_duration: int = PydanticField(
        default=7200,
        ge=600,
        le=43200,
        description="Maximum session duration in seconds",
    )

    audio_quality_threshold: float = PydanticField(
        default=0.8, ge=0.0, le=1.0, description="Minimum audio quality threshold"
    )

    privacy_mode_enabled: bool = PydanticField(
        default=True, description="Privacy mode enabled"
    )

    latency_threshold: float = PydanticField(
        default=4.0,
        ge=0.1,
        le=30.0,
        description="Maximum acceptable latency in seconds (NFR1)",
    )

    audio_retention_days: int = PydanticField(
        default=7, ge=0, le=365, description="Audio data retention period in days"
    )

    enable_performance_monitoring: bool = PydanticField(
        default=True, description="Enable detailed performance monitoring"
    )

    enable_quality_assessment: bool = PydanticField(
        default=True, description="Enable audio quality assessment"
    )


class PerformanceAlert(BaseModel):
    """Performance alert configuration and state."""

    alert_id: str = PydanticField(..., description="Unique alert identifier")

    alert_type: Literal["latency", "quality", "error_rate", "resource_usage"] = (
        PydanticField(..., description="Type of performance alert")
    )

    severity: Literal["low", "medium", "high", "critical"] = PydanticField(
        ..., description="Alert severity level"
    )

    threshold: float = PydanticField(..., description="Alert threshold value")

    current_value: float = PydanticField(..., description="Current measured value")

    session_id: Optional[str] = PydanticField(None, description="Associated session ID")

    message: str = PydanticField(..., description="Alert message")

    triggered_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When the alert was triggered"
    )

    resolved_at: Optional[datetime] = PydanticField(
        None, description="When the alert was resolved"
    )

    resolution_notes: Optional[str] = PydanticField(
        None, description="Notes about alert resolution"
    )


class PerformanceReport(BaseModel):
    """Performance report with aggregated metrics."""

    report_id: str = PydanticField(..., description="Unique report identifier")

    time_range_start: datetime = PydanticField(
        ..., description="Report time range start"
    )

    time_range_end: datetime = PydanticField(..., description="Report time range end")

    total_voice_sessions: int = PydanticField(
        default=0, description="Total number of voice sessions"
    )

    average_latency: Optional[float] = PydanticField(
        None, description="Average total latency in seconds"
    )

    p95_latency: Optional[float] = PydanticField(
        None, description="95th percentile latency in seconds"
    )

    p99_latency: Optional[float] = PydanticField(
        None, description="99th percentile latency in seconds"
    )

    sessions_meeting_latency_target: int = PydanticField(
        default=0, description="Sessions meeting latency target (< 4s)"
    )

    average_quality_score: Optional[float] = PydanticField(
        None, description="Average audio quality score"
    )

    stt_success_rate: Optional[float] = PydanticField(
        None, description="STT success rate"
    )

    tts_success_rate: Optional[float] = PydanticField(
        None, description="TTS success rate"
    )

    error_rate: Optional[float] = PydanticField(None, description="Overall error rate")

    provider_performance: Dict[str, Dict[str, Any]] = PydanticField(
        default_factory=dict, description="Provider-specific performance metrics"
    )

    alerts_generated: int = PydanticField(
        default=0, description="Number of alerts generated in period"
    )

    critical_issues: int = PydanticField(
        default=0, description="Number of critical issues identified"
    )

    recommendations: List[str] = PydanticField(
        default_factory=list, description="Performance improvement recommendations"
    )


class PrivacyComplianceRecord(BaseModel):
    """Privacy compliance tracking for voice data."""

    session_id: str = PydanticField(..., description="Voice session identifier")

    user_id: str = PydanticField(..., description="User identifier")

    data_collection_timestamp: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When audio data was collected"
    )

    data_retention_period_days: int = PydanticField(
        default=7, description="Data retention period in days"
    )

    data_deletion_date: datetime = PydanticField(
        ..., description="Scheduled data deletion date"
    )

    privacy_consent_obtained: bool = PydanticField(
        default=False, description="Whether user consent was obtained"
    )

    consent_timestamp: Optional[datetime] = PydanticField(
        None, description="When consent was obtained"
    )

    data_encrypted: bool = PydanticField(
        default=False, description="Whether data is encrypted"
    )

    encryption_method: Optional[str] = PydanticField(
        None, description="Encryption method used"
    )

    compliance_officer: str = PydanticField(
        default="system", description="Person responsible for compliance"
    )

    audit_trail: List[Dict[str, Any]] = PydanticField(
        default_factory=list, description="Audit trail of data access and processing"
    )
