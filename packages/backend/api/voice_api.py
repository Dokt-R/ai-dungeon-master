"""
Voice API endpoints for controlling advanced voice features.

This module provides API endpoints to enable, disable, and configure
advanced voice features including speaker identification, VAD, audio mixing,
and conversation intelligence.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from packages.backend.components.advanced_vad_processor import (
    advanced_vad_processor,
)
from packages.backend.components.audio_mixer_service import (
    AudioSource,
    SpatialPosition,
    audio_mixer_service,
)
from packages.backend.components.conversation_intelligence import (
    conversation_intelligence_engine,
)
from packages.backend.components.multi_user_conversation_manager import (
    multi_user_conversation_manager,
)
from packages.backend.components.speaker_identification_service import (
    speaker_identification_service,
)
from packages.shared.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


class VoiceFeatureStatus(BaseModel):
    """Status of a voice feature."""

    enabled: bool = Field(description="Whether the feature is enabled")
    status: str = Field(description="Current status of the feature")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional status details"
    )


class VoiceConfiguration(BaseModel):
    """Voice system configuration."""

    speaker_identification: bool = Field(
        default=False, description="Enable speaker identification"
    )
    advanced_vad: bool = Field(default=False, description="Enable advanced VAD")
    audio_mixing: bool = Field(default=False, description="Enable audio mixing")
    conversation_intelligence: bool = Field(
        default=False, description="Enable conversation intelligence"
    )
    multi_user_conversation: bool = Field(
        default=False, description="Enable multi-user conversations"
    )


class AudioSourceConfig(BaseModel):
    """Configuration for an audio source."""

    source_id: str = Field(..., description="Unique source identifier")
    user_id: str = Field(..., description="User identifier")
    volume: float = Field(default=1.0, ge=0.0, le=2.0, description="Volume level")
    muted: bool = Field(default=False, description="Mute status")
    position: Optional[SpatialPosition] = Field(
        default=None, description="3D spatial position"
    )
    priority: int = Field(default=0, ge=0, le=10, description="Priority level")


class SessionConfig(BaseModel):
    """Voice session configuration."""

    session_id: str = Field(..., description="Session identifier")
    sources: Optional[Dict[str, AudioSourceConfig]] = Field(
        default=None, description="Audio sources"
    )
    focus_mode: bool = Field(default=False, description="Enable focus mode")
    focus_speaker: Optional[str] = Field(
        default=None, description="Speaker to focus on"
    )


@router.get("/voice/status", response_model=Dict[str, VoiceFeatureStatus])
async def get_voice_status():
    """Get the status of all voice features."""
    try:
        status = {}

        # Speaker identification status
        try:
            speaker_status = (
                "active" if speaker_identification_service else "not_initialized"
            )
            status["speaker_identification"] = VoiceFeatureStatus(
                enabled=speaker_identification_service is not None,
                status=speaker_status,
            )
        except Exception as e:
            status["speaker_identification"] = VoiceFeatureStatus(
                enabled=False, status="error", details={"error": str(e)}
            )

        # Advanced VAD status
        try:
            vad_status = "active" if advanced_vad_processor else "not_initialized"
            status["advanced_vad"] = VoiceFeatureStatus(
                enabled=advanced_vad_processor is not None, status=vad_status
            )
        except Exception as e:
            status["advanced_vad"] = VoiceFeatureStatus(
                enabled=False, status="error", details={"error": str(e)}
            )

        # Audio mixing status
        try:
            mixing_status = "active" if audio_mixer_service else "not_initialized"
            status["audio_mixing"] = VoiceFeatureStatus(
                enabled=audio_mixer_service is not None, status=mixing_status
            )
        except Exception as e:
            status["audio_mixing"] = VoiceFeatureStatus(
                enabled=False, status="error", details={"error": str(e)}
            )

        # Conversation intelligence status
        try:
            ci_status = (
                "active" if conversation_intelligence_engine else "not_initialized"
            )
            status["conversation_intelligence"] = VoiceFeatureStatus(
                enabled=conversation_intelligence_engine is not None, status=ci_status
            )
        except Exception as e:
            status["conversation_intelligence"] = VoiceFeatureStatus(
                enabled=False, status="error", details={"error": str(e)}
            )

        # Multi-user conversation status
        try:
            muc_status = (
                "active" if multi_user_conversation_manager else "not_initialized"
            )
            status["multi_user_conversation"] = VoiceFeatureStatus(
                enabled=multi_user_conversation_manager is not None, status=muc_status
            )
        except Exception as e:
            status["multi_user_conversation"] = VoiceFeatureStatus(
                enabled=False, status="error", details={"error": str(e)}
            )

        return status

    except Exception as e:
        logger.error("Failed to get voice status: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to get voice status: {str(e)}"
        )


@router.post("/voice/session/{session_id}/create")
async def create_voice_session(session_id: str, config: Optional[SessionConfig] = None):
    """Create a new voice session with specified configuration."""
    try:
        # Create audio mixer session
        if audio_mixer_service:
            mixer_session_id = await audio_mixer_service.create_mix_session(session_id)
            if mixer_session_id != session_id:
                raise HTTPException(
                    status_code=500, detail="Failed to create mixer session"
                )

        # Create conversation if requested
        if config and config.sources and multi_user_conversation_manager:
            source_user_ids = [source.user_id for source in config.sources.values()]
            conversation = await multi_user_conversation_manager.create_conversation(
                session_id, source_user_ids
            )

            # Add sources to mixer if specified
            if config.sources and audio_mixer_service:
                for source_config in config.sources.values():
                    source = AudioSource(
                        source_id=source_config.source_id,
                        user_id=source_config.user_id,
                        volume=source_config.volume,
                        muted=source_config.muted,
                        position=source_config.position or SpatialPosition(),
                        priority=source_config.priority,
                    )
                    success = await audio_mixer_service.add_audio_source(
                        session_id, source
                    )
                    if not success:
                        logger.warning(
                            "Failed to add audio source: %s", source_config.source_id
                        )

            # Enable focus mode if requested
            if config.focus_mode and config.focus_speaker and audio_mixer_service:
                success = await audio_mixer_service.set_focus_mode(
                    session_id, config.focus_speaker, enable=True
                )
                if not success:
                    logger.warning(
                        "Failed to enable focus mode for session: %s", session_id
                    )

        logger.info("Created voice session: %s", session_id)
        return {"session_id": session_id, "status": "created"}

    except Exception as e:
        logger.error("Failed to create voice session %s: %s", session_id, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to create voice session: {str(e)}"
        )


@router.post("/voice/session/{session_id}/source")
async def add_audio_source(session_id: str, source_config: AudioSourceConfig):
    """Add an audio source to a voice session."""
    try:
        if not audio_mixer_service:
            raise HTTPException(
                status_code=400, detail="Audio mixing service not available"
            )

        source = AudioSource(
            source_id=source_config.source_id,
            user_id=source_config.user_id,
            volume=source_config.volume,
            muted=source_config.muted,
            position=source_config.position or SpatialPosition(),
            priority=source_config.priority,
        )

        success = await audio_mixer_service.add_audio_source(session_id, source)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add audio source")

        logger.info(
            "Added audio source %s to session %s", source_config.source_id, session_id
        )
        return {"status": "source_added", "source_id": source_config.source_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add audio source: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to add audio source: {str(e)}"
        )


@router.put("/voice/session/{session_id}/source/{source_id}/position")
async def update_source_position(
    session_id: str, source_id: str, position: SpatialPosition
):
    """Update the spatial position of an audio source."""
    try:
        if not audio_mixer_service:
            raise HTTPException(
                status_code=400, detail="Audio mixing service not available"
            )

        success = await audio_mixer_service.update_source_position(
            session_id, source_id, position
        )
        if not success:
            raise HTTPException(status_code=404, detail="Audio source not found")

        logger.info(
            "Updated position for source %s in session %s", source_id, session_id
        )
        return {"status": "position_updated"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update source position: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to update source position: {str(e)}"
        )


@router.put("/voice/session/{session_id}/focus")
async def set_focus_mode(
    session_id: str, focus_speaker: Optional[str] = None, enable: bool = True
):
    """Enable or disable focus mode for a session."""
    try:
        if not audio_mixer_service:
            raise HTTPException(
                status_code=400, detail="Audio mixing service not available"
            )

        success = await audio_mixer_service.set_focus_mode(
            session_id, focus_speaker, enable
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set focus mode")

        mode = "enabled" if enable else "disabled"
        logger.info("Focus mode %s for session %s", mode, session_id)
        return {"status": f"focus_mode_{mode}", "focus_speaker": focus_speaker}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to set focus mode: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to set focus mode: {str(e)}"
        )


@router.get("/voice/session/{session_id}/stats")
async def get_session_stats(session_id: str):
    """Get statistics for a voice session."""
    try:
        stats = {}

        # Audio mixer stats
        if audio_mixer_service:
            mixer_state = await audio_mixer_service.get_mixing_state(session_id)
            if mixer_state:
                stats["audio_mixing"] = {
                    "active_sources": len(mixer_state.active_sources),
                    "master_volume": mixer_state.master_volume,
                    "focus_mode": mixer_state.focus_mode,
                    "focus_speaker": mixer_state.focus_speaker,
                }

        # Conversation intelligence stats
        if conversation_intelligence_engine:
            ci_stats = await conversation_intelligence_engine.get_conversation_stats(
                session_id
            )
            if ci_stats:
                stats["conversation_intelligence"] = ci_stats

        if not stats:
            raise HTTPException(
                status_code=404, detail="Session not found or no services available"
            )

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get session stats: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to get session stats: {str(e)}"
        )


@router.delete("/voice/session/{session_id}")
async def cleanup_voice_session(session_id: str):
    """Clean up a voice session and all associated resources."""
    try:
        cleanup_status = {}

        # Clean up audio mixer
        if audio_mixer_service:
            await audio_mixer_service.cleanup_session(session_id)
            cleanup_status["audio_mixing"] = "cleaned"

        # Clean up conversation
        if multi_user_conversation_manager:
            await multi_user_conversation_manager.end_conversation(session_id)
            cleanup_status["multi_user_conversation"] = "cleaned"

        # Clean up conversation intelligence
        if conversation_intelligence_engine:
            await conversation_intelligence_engine.cleanup_conversation(session_id)
            cleanup_status["conversation_intelligence"] = "cleaned"

        logger.info("Cleaned up voice session: %s", session_id)
        return {
            "session_id": session_id,
            "status": "cleaned",
            "services": cleanup_status,
        }

    except Exception as e:
        logger.error("Failed to cleanup voice session: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to cleanup voice session: {str(e)}"
        )


@router.get("/voice/conversation/{conversation_id}/summary")
async def get_conversation_summary(conversation_id: str):
    """Get a summary of conversation intelligence analysis."""
    try:
        if not conversation_intelligence_engine:
            raise HTTPException(
                status_code=400, detail="Conversation intelligence not available"
            )

        summary = await conversation_intelligence_engine.generate_conversation_summary(
            conversation_id
        )

        if "error" in summary:
            raise HTTPException(status_code=404, detail=summary["error"])

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get conversation summary: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to get conversation summary: {str(e)}"
        )


@router.get("/voice/health")
async def get_voice_system_health():
    """Get the health status of all voice system components."""
    try:
        health_status = {}

        # Check each service
        services = {
            "speaker_identification": speaker_identification_service,
            "advanced_vad": advanced_vad_processor,
            "audio_mixing": audio_mixer_service,
            "conversation_intelligence": conversation_intelligence_engine,
            "multi_user_conversation": multi_user_conversation_manager,
        }

        for service_name, service in services.items():
            if service is not None:
                health_status[service_name] = {"status": "healthy", "available": True}
            else:
                health_status[service_name] = {
                    "status": "not_available",
                    "available": False,
                }

        return {
            "overall_status": "healthy"
            if any(s["available"] for s in health_status.values())
            else "no_services",
            "services": health_status,
        }

    except Exception as e:
        logger.error("Failed to get voice system health: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to get voice system health: {str(e)}"
        )
