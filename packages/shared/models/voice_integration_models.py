"""
Voice Integration Models
Models for Discord voice channel management and integration.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field as PydanticField


class VoiceChannelInfo(BaseModel):
    """Information about a Discord voice channel."""

    channel_id: str = PydanticField(
        ..., description="Discord voice channel ID", pattern=r"^[0-9]+$"
    )

    guild_id: str = PydanticField(
        ..., description="Discord guild ID", pattern=r"^[0-9]+$"
    )

    channel_name: str = PydanticField(
        ..., description="Voice channel name", min_length=1, max_length=100
    )

    user_limit: Optional[int] = PydanticField(
        None, description="User limit for channel", ge=0, le=99
    )

    bitrate: int = PydanticField(..., description="Channel bitrate", ge=8000, le=512000)

    region: str = PydanticField(..., description="Voice region")

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When this info was retrieved"
    )


class VoiceConnection(BaseModel):
    """Represents an active voice connection."""

    connection_id: str = PydanticField(
        ...,
        description="Unique connection identifier",
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=128,
    )

    channel_id: str = PydanticField(
        ..., description="Connected voice channel ID", pattern=r"^[0-9]+$"
    )

    guild_id: str = PydanticField(
        ..., description="Discord guild ID", pattern=r"^[0-9]+$"
    )

    status: Literal["connecting", "connected", "disconnected", "error"] = PydanticField(
        ..., description="Connection status"
    )

    connected_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Connection start time"
    )

    participants: List[str] = PydanticField(
        default_factory=list, description="User IDs in voice"
    )

    last_activity: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Last voice activity"
    )

    error_message: Optional[str] = PydanticField(
        None, description="Last error message", max_length=500
    )

    disconnect_reason: Optional[str] = PydanticField(
        None, description="Reason for disconnection", max_length=200
    )

    connection_quality: Optional[Dict[str, Any]] = PydanticField(
        None, description="Connection quality metrics"
    )


class VoicePermission(BaseModel):
    """Voice channel permissions for users and bot."""

    user_id: str = PydanticField(..., description="User or bot ID", pattern=r"^[0-9]+$")

    can_connect: bool = PydanticField(..., description="Can connect to voice channel")

    can_speak: bool = PydanticField(..., description="Can speak in voice channel")

    can_mute_members: bool = PydanticField(..., description="Can mute other members")

    can_deafen_members: bool = PydanticField(
        ..., description="Can deafen other members"
    )

    can_move_members: bool = PydanticField(
        ..., description="Can move members between channels"
    )

    can_use_voice_activity: bool = PydanticField(
        ..., description="Can use voice activity detection"
    )

    can_priority_speaker: bool = PydanticField(
        ..., description="Can be priority speaker"
    )

    checked_at: datetime = PydanticField(
        default_factory=datetime.utcnow,
        description="When permissions were last checked",
    )


class AudioStreamInfo(BaseModel):
    """Information about an audio stream."""

    stream_id: str = PydanticField(
        ...,
        description="Unique stream identifier",
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=128,
    )

    user_id: str = PydanticField(
        ..., description="User ID of the stream source", pattern=r"^[0-9]+$"
    )

    channel_id: str = PydanticField(
        ..., description="Voice channel ID", pattern=r"^[0-9]+$"
    )

    session_id: str = PydanticField(..., description="Voice session identifier")

    format: str = PydanticField(..., description="Audio format (e.g., 's16le', 'opus')")

    sample_rate: int = PydanticField(
        ..., description="Sample rate in Hz", ge=8000, le=192000
    )

    channels: int = PydanticField(
        ..., description="Number of audio channels", ge=1, le=2
    )

    bitrate: int = PydanticField(
        ..., description="Audio bitrate in bits per second", ge=8000, le=512000
    )

    started_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When the stream started"
    )

    last_activity: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Last audio activity"
    )

    is_speaking: bool = PydanticField(
        ..., description="Whether user is currently speaking"
    )

    volume_level: float = PydanticField(
        ..., description="Current volume level (0.0 to 1.0)", ge=0.0, le=1.0
    )

    silence_threshold: float = PydanticField(
        ..., description="Silence detection threshold", ge=0.0, le=1.0
    )

    is_active: bool = PydanticField(
        True, description="Whether stream is currently active"
    )

    buffer_size: int = PydanticField(
        0, description="Current buffer size in bytes", ge=0
    )

    processed_chunks: int = PydanticField(
        0, description="Number of chunks processed", ge=0
    )

    total_transcriptions: int = PydanticField(
        0, description="Total transcriptions generated", ge=0
    )

    average_confidence: float = PydanticField(
        0.0, description="Average transcription confidence", ge=0.0, le=1.0
    )


class VoiceSession(BaseModel):
    """Represents a complete voice session."""

    session_id: str = PydanticField(
        ...,
        description="Unique session identifier",
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=128,
    )

    guild_id: str = PydanticField(
        ..., description="Discord guild ID", pattern=r"^[0-9]+$"
    )

    channel_id: str = PydanticField(
        ..., description="Voice channel ID", pattern=r"^[0-9]+$"
    )

    started_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Session start time"
    )

    ended_at: Optional[datetime] = PydanticField(None, description="Session end time")

    total_participants: int = PydanticField(
        0, description="Total unique participants", ge=0
    )

    max_concurrent_participants: int = PydanticField(
        0, description="Maximum concurrent participants", ge=0
    )

    total_audio_time: float = PydanticField(
        0.0, description="Total audio time in seconds", ge=0.0
    )

    connection_issues: List[Dict[str, Any]] = PydanticField(
        default_factory=list, description="Connection issues encountered"
    )

    audio_quality_metrics: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Audio quality metrics"
    )

    status: Literal["active", "ended", "error"] = PydanticField(
        ..., description="Session status"
    )


class VoiceJoinRequest(BaseModel):
    """Request to join a voice channel."""

    channel_id: str = PydanticField(
        ..., description="Voice channel ID to join", pattern=r"^[0-9]+$"
    )

    user_id: str = PydanticField(
        ..., description="User requesting to join", pattern=r"^[0-9]+$"
    )

    force: bool = PydanticField(
        False, description="Force join even if already connected"
    )

    self_deaf: bool = PydanticField(False, description="Join deafened")

    self_mute: bool = PydanticField(False, description="Join muted")


class VoiceLeaveRequest(BaseModel):
    """Request to leave voice channel."""

    user_id: str = PydanticField(
        ..., description="User requesting to leave", pattern=r"^[0-9]+$"
    )

    reason: Optional[str] = PydanticField(
        None, description="Reason for leaving", max_length=200
    )


class VoiceStatusResponse(BaseModel):
    """Response containing voice connection status."""

    connected: bool = PydanticField(
        ..., description="Whether bot is connected to voice"
    )

    channel_id: Optional[str] = PydanticField(
        None, description="Current voice channel ID"
    )

    channel_name: Optional[str] = PydanticField(
        None, description="Current voice channel name"
    )

    guild_id: Optional[str] = PydanticField(None, description="Current guild ID")

    participant_count: int = PydanticField(
        0, description="Number of participants", ge=0
    )

    participants: List[str] = PydanticField(
        default_factory=list, description="List of participant user IDs"
    )

    connection_quality: Optional[Dict[str, Any]] = PydanticField(
        None, description="Connection quality information"
    )

    connected_at: Optional[datetime] = PydanticField(
        None, description="When connection was established"
    )


class VoiceChannelResponse(BaseModel):
    """Response containing voice channel information."""

    channel_id: str = PydanticField(..., description="Voice channel ID")

    channel_name: str = PydanticField(..., description="Voice channel name")

    user_limit: Optional[int] = PydanticField(None, description="User limit")

    bitrate: int = PydanticField(..., description="Channel bitrate")

    region: str = PydanticField(..., description="Voice region")

    member_count: int = PydanticField(0, description="Current member count", ge=0)

    bot_can_join: bool = PydanticField(
        ..., description="Whether bot has permission to join"
    )

    bot_permissions: Optional[Dict[str, bool]] = PydanticField(
        None, description="Bot's permissions in the channel"
    )


class VoiceCommandResponse(BaseModel):
    """Generic response for voice commands."""

    success: bool = PydanticField(..., description="Whether the command was successful")

    message: str = PydanticField(
        ..., description="Response message", min_length=1, max_length=500
    )

    data: Optional[Dict[str, Any]] = PydanticField(
        None, description="Additional response data"
    )

    error_code: Optional[str] = PydanticField(
        None, description="Error code if not successful", max_length=100
    )


class MemoryQueryRequest(BaseModel):
    """Request to query memory data."""

    query_type: Literal["events", "facts", "context"] = PydanticField(
        ..., description="Type of memory to query"
    )

    filters: Optional[Dict[str, Any]] = PydanticField(None, description="Query filters")

    limit: Optional[int] = PydanticField(
        100, ge=1, le=1000, description="Maximum results to return"
    )

    include_metadata: Optional[bool] = PydanticField(
        True, description="Whether to include metadata in results"
    )