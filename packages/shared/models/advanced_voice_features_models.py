"""
Advanced Voice Features Models
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    Field as PydanticField,
)


class SpeakerProfile(BaseModel):
    """Voice profile for speaker identification."""

    profile_id: str = PydanticField(
        ..., description="Unique speaker profile identifier"
    )

    user_id: str = PydanticField(..., description="Associated user ID")

    voice_print: bytes = PydanticField(..., description="Voice biometric data")

    voice_characteristics: Dict[str, float] = PydanticField(
        default_factory=dict,
        description="Voice characteristics (pitch, tone, speed, etc.)",
        examples={
            "average_pitch": 120.5,
            "pitch_variance": 15.2,
            "speaking_rate": 150.0,
            "tone_stability": 0.85,
        },
    )

    sample_audio_clips: List[bytes] = PydanticField(
        default_factory=list, description="Sample audio clips for voice training"
    )

    confidence_threshold: float = PydanticField(
        default=0.8, ge=0.0, le=1.0, description="Identification confidence threshold"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When profile was created"
    )

    last_updated: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When profile was last updated"
    )

    total_training_samples: int = PydanticField(
        default=0, description="Number of training samples"
    )

    identification_accuracy: float = PydanticField(
        default=0.0, ge=0.0, le=1.0, description="Speaker identification accuracy"
    )

    last_identification: Optional[datetime] = PydanticField(
        None, description="When speaker was last identified"
    )


class VoiceActivitySegment(BaseModel):
    """Voice activity detection segment."""

    segment_id: str = PydanticField(..., description="Unique segment identifier")

    session_id: str = PydanticField(..., description="Voice session identifier")

    speaker_id: Optional[str] = PydanticField(None, description="Identified speaker ID")

    start_time: datetime = PydanticField(..., description="Segment start time")

    end_time: datetime = PydanticField(..., description="Segment end time")

    confidence: float = PydanticField(
        ..., ge=0.0, le=1.0, description="VAD confidence score"
    )

    energy_level: float = PydanticField(..., description="Audio energy level")

    noise_level: float = PydanticField(..., description="Background noise level")

    overlap_detected: bool = PydanticField(
        default=False, description="Whether speaker overlap was detected"
    )

    speaker_confidence: Optional[float] = PydanticField(
        None, ge=0.0, le=1.0, description="Speaker identification confidence"
    )

    audio_features: Dict[str, float] = PydanticField(
        default_factory=dict,
        description="Extracted audio features",
        examples={
            "mfcc_mean": 0.5,
            "spectral_centroid": 2500.0,
            "zero_crossing_rate": 0.15,
        },
    )

    duration: float = PydanticField(..., description="Segment duration in seconds")


class MultiUserConversation(BaseModel):
    """Multi-user conversation context."""

    conversation_id: str = PydanticField(
        ..., description="Unique conversation identifier"
    )

    session_id: str = PydanticField(..., description="Voice session identifier")

    active_speakers: List[str] = PydanticField(
        default_factory=list, description="Currently active speaker IDs"
    )

    speaker_segments: List[VoiceActivitySegment] = PydanticField(
        default_factory=list, description="Voice activity segments"
    )

    conversation_flow: List[Dict[str, Any]] = PydanticField(
        default_factory=list,
        description="Conversation flow and turn-taking events",
        examples=[
            {
                "speaker_id": "user_123",
                "start_time": "2025-08-22T21:35:20Z",
                "end_time": "2025-08-22T21:35:25Z",
                "text": "I want to attack the goblin",
                "sentiment": 0.2,
            }
        ],
    )

    turn_taking_events: List[Dict[str, Any]] = PydanticField(
        default_factory=list, description="Turn-taking events and transitions"
    )

    engagement_metrics: Dict[str, float] = PydanticField(
        default_factory=dict,
        description="Group engagement metrics",
        examples={
            "average_participation": 0.75,
            "turn_taking_efficiency": 0.85,
            "conversation_balance": 0.70,
            "engagement_trend": 0.05,
        },
    )

    started_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When conversation started"
    )

    last_activity: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When last activity occurred"
    )

    total_speakers: int = PydanticField(
        default=0, description="Total number of speakers"
    )

    total_turns: int = PydanticField(
        default=0, description="Total number of conversation turns"
    )

    average_turn_duration: float = PydanticField(
        default=0.0, description="Average turn duration in seconds"
    )

    dominant_speaker: Optional[str] = PydanticField(
        None, description="Most active speaker ID"
    )


class AudioMixConfiguration(BaseModel):
    """Audio mixing configuration for multi-user scenarios."""

    mix_id: str = PydanticField(..., description="Unique mix configuration identifier")

    session_id: str = PydanticField(..., description="Voice session identifier")

    input_streams: List[str] = PydanticField(..., description="Input audio stream IDs")

    output_stream: str = PydanticField(..., description="Output mixed stream ID")

    volume_levels: Dict[str, float] = PydanticField(
        default_factory=dict, description="Per-stream volume levels (0.0 to 1.0)"
    )

    spatial_positions: Dict[str, Dict[str, float]] = PydanticField(
        default_factory=dict,
        description="3D spatial positions for each stream",
        examples={
            "user_123": {
                "x": 1.0,
                "y": 0.0,
                "z": 0.0,
                "azimuth": 30.0,
                "elevation": 0.0,
            }
        },
    )

    priority_speakers: List[str] = PydanticField(
        default_factory=list, description="Priority speaker order for ducking"
    )

    ducking_enabled: bool = PydanticField(
        default=True, description="Enable audio ducking for priority speakers"
    )

    ducking_threshold: float = PydanticField(
        default=0.7, ge=0.0, le=1.0, description="Ducking trigger threshold"
    )

    ducking_amount: float = PydanticField(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="How much to duck other streams (0.0 = no ducking, 1.0 = mute)",
    )

    room_simulation: bool = PydanticField(
        default=False, description="Enable room acoustics simulation"
    )

    room_size: str = PydanticField(
        default="medium",
        description="Room size for acoustics simulation",
        examples=["small", "medium", "large", "hall"],
    )

    reverb_enabled: bool = PydanticField(
        default=True, description="Enable reverb effects"
    )

    reverb_decay: float = PydanticField(
        default=0.5, ge=0.0, le=1.0, description="Reverb decay time"
    )


class ConversationIntelligenceData(BaseModel):
    """Conversation intelligence and analysis data."""

    conversation_id: str = PydanticField(..., description="Conversation identifier")

    session_id: str = PydanticField(..., description="Voice session identifier")

    sentiment_analysis: Dict[str, float] = PydanticField(
        default_factory=dict,
        description="Sentiment analysis results",
        examples={
            "overall_sentiment": 0.3,
            "positive_ratio": 0.4,
            "negative_ratio": 0.2,
            "neutral_ratio": 0.4,
        },
    )

    engagement_scores: Dict[str, float] = PydanticField(
        default_factory=dict,
        description="Engagement scores by speaker",
        examples={"user_123": 0.75, "user_456": 0.85, "user_789": 0.60},
    )

    topic_detection: List[Dict[str, Any]] = PydanticField(
        default_factory=list,
        description="Detected conversation topics",
        examples=[
            {
                "topic": "combat_strategy",
                "confidence": 0.8,
                "start_time": "2025-08-22T21:35:20Z",
                "end_time": "2025-08-22T21:35:35Z",
            }
        ],
    )

    rhythm_analysis: Dict[str, Any] = PydanticField(
        default_factory=dict,
        description="Conversation rhythm and pacing analysis",
        examples={
            "average_pause_duration": 1.2,
            "turn_taking_speed": 0.8,
            "interruption_rate": 0.15,
            "conversation_tempo": "moderate",
        },
    )

    highlight_moments: List[Dict[str, Any]] = PydanticField(
        default_factory=list,
        description="Identified conversation highlights",
        examples=[
            {
                "type": "exciting_moment",
                "timestamp": "2025-08-22T21:35:30Z",
                "description": "Player successfully lands critical hit",
                "intensity": 0.9,
            }
        ],
    )

    summary: str = PydanticField(
        default="", description="Generated conversation summary"
    )

    key_insights: List[str] = PydanticField(
        default_factory=list, description="Key insights from conversation analysis"
    )

    generated_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When analysis was generated"
    )
