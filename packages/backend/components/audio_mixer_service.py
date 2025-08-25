"""
Audio Mixer Service for Multi-User Voice Conversations.

This module provides advanced audio mixing capabilities with spatial audio positioning,
volume control, audio ducking, and real-time mixing for immersive multi-user experiences.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

from packages.backend.components.audio_utils import AudioUtils
from packages.shared.logging_config import get_logger
from packages.shared.models import AudioMixConfiguration

logger = get_logger(__name__)


class SpatialPosition(BaseModel):
    """3D spatial position for audio sources."""

    x: float = Field(default=0.0, description="X coordinate (-1.0 to 1.0)")
    y: float = Field(default=0.0, description="Y coordinate (-1.0 to 1.0)")
    z: float = Field(default=0.0, description="Z coordinate (-1.0 to 1.0)")
    distance: float = Field(
        default=1.0, description="Distance from listener (0.0 to 10.0)"
    )


class AudioSource(BaseModel):
    """Audio source configuration for mixing."""

    source_id: str = Field(..., description="Unique audio source identifier")
    user_id: str = Field(..., description="Associated user ID")
    volume: float = Field(default=1.0, ge=0.0, le=2.0, description="Volume level")
    muted: bool = Field(default=False, description="Mute status")
    position: SpatialPosition = Field(default_factory=SpatialPosition)
    priority: int = Field(
        default=0, ge=0, le=10, description="Priority level for ducking"
    )
    is_active: bool = Field(default=True, description="Source active status")


@dataclass
class MixingState:
    """State tracking for audio mixing session."""

    session_id: str
    active_sources: Dict[str, AudioSource] = field(default_factory=dict)
    master_volume: float = 1.0
    ducking_enabled: bool = True
    ducking_threshold: float = 0.7
    spatial_enabled: bool = True
    focus_mode: bool = False
    focus_speaker: Optional[str] = None
    last_mix_time: datetime = field(default_factory=datetime.utcnow)


class HRTFProcessor:
    """Head-Related Transfer Function processor for 3D audio positioning."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.hrtf_cache: Dict[str, np.ndarray] = {}

    async def apply_hrtf(
        self, audio: np.ndarray, position: SpatialPosition
    ) -> np.ndarray:
        """
        Apply HRTF filtering for 3D positioning.

        Args:
            audio: Input audio signal
            position: 3D position of the source

        Returns:
            Spatially positioned audio signal
        """
        # Generate HRTF cache key
        cache_key = ".2f"

        if cache_key in self.hrtf_cache:
            hrtf_filter = self.hrtf_cache[cache_key]
        else:
            # Generate simplified HRTF filter (in practice, use actual HRTF database)
            hrtf_filter = await self._generate_hrtf_filter(position)
            self.hrtf_cache[cache_key] = hrtf_filter

        # Apply HRTF filtering
        return await self._convolve_hrtf(audio, hrtf_filter)

    async def _generate_hrtf_filter(self, position: SpatialPosition) -> np.ndarray:
        """Generate HRTF filter for given position."""
        # Simplified HRTF generation (interaural time difference + level difference)
        filter_length = 512

        # Calculate interaural time difference (ITD)
        azimuth = np.arctan2(position.y, position.x)
        distance = np.sqrt(position.x**2 + position.y**2 + position.z**2)
        itd_samples = int((azimuth / np.pi) * 10)  # Simplified ITD calculation

        # Create delay filter
        filter_left = np.zeros(filter_length)
        filter_right = np.zeros(filter_length)

        # Basic delay-based spatialization
        delay_left = max(0, itd_samples)
        delay_right = max(0, -itd_samples)

        # Apply distance attenuation
        attenuation = 1.0 / (1.0 + distance)

        # Simple head shadowing effect
        if azimuth > 0:  # Right side
            attenuation *= 1.0 - min(azimuth / np.pi, 0.3)
        else:  # Left side
            attenuation *= 1.0 + max(azimuth / np.pi, -0.3)

        filter_left[delay_left] = attenuation
        filter_right[delay_right] = attenuation

        return np.array([filter_left, filter_right])

    async def _convolve_hrtf(
        self, audio: np.ndarray, hrtf_filter: np.ndarray
    ) -> np.ndarray:
        """Apply HRTF convolution to audio signal."""
        # Simplified convolution (in practice, use FFT-based convolution)
        left_filter, right_filter = hrtf_filter

        # Ensure audio is mono for processing
        if audio.ndim > 1:
            audio_mono = np.mean(audio, axis=1)
        else:
            audio_mono = audio

        # Apply convolution
        try:
            left_channel = np.convolve(audio_mono, left_filter, mode="same")
            right_channel = np.convolve(audio_mono, right_filter, mode="same")

            return np.column_stack([left_channel, right_channel])
        except Exception as e:
            logger.warning("HRTF convolution failed: %s", e)
            # Return stereo version of original audio
            return np.column_stack([audio_mono, audio_mono])


class AudioMixerService:
    """
    Advanced Audio Mixer Service for multi-user voice conversations.

    Features:
    - Multi-user audio mixing with volume control
    - 3D spatial audio positioning with HRTF
    - Audio ducking for priority speakers
    - Real-time mixing with low latency
    - Focus management for game events
    """

    def __init__(self, sample_rate: int = 16000, buffer_size: int = 1024):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.audio_utils = AudioUtils()
        self.hrtf_processor = HRTFProcessor(sample_rate)
        self.mixing_states: Dict[str, MixingState] = {}
        self.source_buffers: Dict[str, List[np.ndarray]] = {}
        self.logger = logger

        self.logger.info(
            "AudioMixerService initialized with sample_rate=%d, buffer_size=%d",
            sample_rate,
            buffer_size,
        )

    async def create_mix_session(
        self, session_id: str, configuration: Optional[AudioMixConfiguration] = None
    ) -> str:
        """
        Create a new audio mixing session.

        Args:
            session_id: Unique session identifier
            configuration: Optional mixing configuration

        Returns:
            Session ID
        """
        try:
            # Create mixing state
            mixing_state = MixingState(session_id=session_id)

            if configuration:
                mixing_state.master_volume = configuration.volume_levels.get(
                    "master", 1.0
                )
                mixing_state.ducking_enabled = configuration.ducking_enabled
                mixing_state.ducking_threshold = configuration.ducking_threshold

            self.mixing_states[session_id] = mixing_state
            self.source_buffers[session_id] = []

            self.logger.info("Created audio mixing session: %s", session_id)
            return session_id

        except Exception as e:
            self.logger.error("Failed to create mix session %s: %s", session_id, e)
            raise

    async def add_audio_source(self, session_id: str, source: AudioSource) -> bool:
        """
        Add an audio source to the mixing session.

        Args:
            session_id: Mixing session identifier
            source: Audio source configuration

        Returns:
            Success status
        """
        try:
            if session_id not in self.mixing_states:
                raise ValueError(f"Session {session_id} not found")

            mixing_state = self.mixing_states[session_id]
            mixing_state.active_sources[source.source_id] = source

            self.logger.info(
                "Added audio source %s to session %s", source.source_id, session_id
            )
            return True

        except Exception as e:
            self.logger.error("Failed to add audio source %s: %s", source.source_id, e)
            return False

    async def mix_audio_streams(
        self, session_id: str, audio_streams: Dict[str, np.ndarray]
    ) -> np.ndarray:
        """
        Mix multiple audio streams with spatial processing and ducking.

        Args:
            session_id: Mixing session identifier
            audio_streams: Dictionary of source_id -> audio_data

        Returns:
            Mixed audio stream
        """
        try:
            if session_id not in self.mixing_states:
                raise ValueError(f"Session {session_id} not found")

            mixing_state = self.mixing_states[session_id]

            if not audio_streams:
                return np.zeros((self.buffer_size, 2))  # Return silent stereo audio

            # Process each audio stream
            processed_streams = []
            for source_id, audio_data in audio_streams.items():
                if source_id in mixing_state.active_sources:
                    source = mixing_state.active_sources[source_id]
                    processed_audio = await self._process_audio_source(
                        source, audio_data, mixing_state
                    )
                    processed_streams.append(processed_audio)

            if not processed_streams:
                return np.zeros((self.buffer_size, 2))

            # Mix all processed streams
            mixed_audio = await self._mix_streams(processed_streams)

            # Apply master volume
            mixed_audio *= mixing_state.master_volume

            # Store in buffer for potential replay/monitoring
            self.source_buffers[session_id].append(mixed_audio.copy())

            # Keep buffer size manageable
            if len(self.source_buffers[session_id]) > 50:  # Keep last 50 mixes
                self.source_buffers[session_id] = self.source_buffers[session_id][-50:]

            mixing_state.last_mix_time = datetime.utcnow()
            return mixed_audio

        except Exception as e:
            self.logger.error("Audio mixing failed for session %s: %s", session_id, e)
            return np.zeros((self.buffer_size, 2))

    async def _process_audio_source(
        self, source: AudioSource, audio_data: np.ndarray, mixing_state: MixingState
    ) -> np.ndarray:
        """Process a single audio source with volume, spatial, and ducking effects."""
        try:
            # Start with original audio
            processed_audio = audio_data.copy()

            # Apply volume control
            if source.volume != 1.0:
                processed_audio *= source.volume

            # Apply muting
            if source.muted:
                processed_audio *= 0.0

            # Apply spatial audio positioning
            if mixing_state.spatial_enabled and source.position.distance > 0:
                processed_audio = await self.hrtf_processor.apply_hrtf(
                    processed_audio, source.position
                )

            # Apply ducking if needed
            if mixing_state.ducking_enabled and mixing_state.focus_mode:
                processed_audio = await self._apply_ducking(
                    processed_audio, source, mixing_state
                )

            return processed_audio

        except Exception as e:
            self.logger.warning("Audio source processing failed: %s", e)
            return audio_data

    async def _apply_ducking(
        self, audio: np.ndarray, source: AudioSource, mixing_state: MixingState
    ) -> np.ndarray:
        """Apply audio ducking based on priority and focus."""
        try:
            # Calculate ducking factor based on priority
            if (
                mixing_state.focus_speaker
                and source.source_id != mixing_state.focus_speaker
            ):
                focus_source = mixing_state.active_sources.get(
                    mixing_state.focus_speaker
                )
                if focus_source:
                    priority_diff = focus_source.priority - source.priority
                    ducking_factor = max(0.1, 1.0 - (priority_diff * 0.1))
                    audio *= ducking_factor

            # Apply threshold-based ducking
            rms_level = np.sqrt(np.mean(audio**2))
            if rms_level > mixing_state.ducking_threshold:
                # Reduce volume of lower priority sources
                if source.priority < 5:  # Lower priority threshold
                    ducking_factor = mixing_state.ducking_threshold / rms_level
                    audio *= ducking_factor

            return audio

        except Exception as e:
            self.logger.warning("Ducking application failed: %s", e)
            return audio

    async def _mix_streams(self, streams: List[np.ndarray]) -> np.ndarray:
        """Mix multiple audio streams with proper normalization."""
        try:
            if not streams:
                return np.zeros((self.buffer_size, 2))

            # Convert all streams to same format
            max_length = max(len(stream) for stream in streams)

            # Pad shorter streams with zeros
            padded_streams = []
            for stream in streams:
                if len(stream) < max_length:
                    padding = np.zeros(
                        (
                            max_length - len(stream),
                            stream.shape[1] if stream.ndim > 1 else 1,
                        )
                    )
                    padded_stream = (
                        np.vstack([stream, padding])
                        if stream.ndim > 1
                        else np.concatenate([stream, padding])
                    )
                else:
                    padded_stream = stream
                padded_streams.append(padded_stream)

            # Mix streams
            mixed = np.sum(padded_streams, axis=0)

            # Normalize to prevent clipping
            max_amplitude = np.max(np.abs(mixed))
            if max_amplitude > 0.95:  # Leave some headroom
                mixed = mixed * (0.95 / max_amplitude)

            return mixed

        except Exception as e:
            self.logger.error("Stream mixing failed: %s", e)
            return np.zeros((self.buffer_size, 2))

    async def set_focus_mode(
        self, session_id: str, focus_speaker: Optional[str] = None, enable: bool = True
    ) -> bool:
        """
        Enable or disable focus mode for priority speaker.

        Args:
            session_id: Mixing session identifier
            focus_speaker: Speaker to focus on (None for disable)
            enable: Enable or disable focus mode

        Returns:
            Success status
        """
        try:
            if session_id not in self.mixing_states:
                return False

            mixing_state = self.mixing_states[session_id]
            mixing_state.focus_mode = enable
            mixing_state.focus_speaker = focus_speaker if enable else None

            self.logger.info(
                "Focus mode %s for session %s, speaker: %s",
                "enabled" if enable else "disabled",
                session_id,
                focus_speaker,
            )
            return True

        except Exception as e:
            self.logger.error("Focus mode change failed: %s", e)
            return False

    async def update_source_position(
        self, session_id: str, source_id: str, position: SpatialPosition
    ) -> bool:
        """
        Update spatial position of an audio source.

        Args:
            session_id: Mixing session identifier
            source_id: Audio source identifier
            position: New spatial position

        Returns:
            Success status
        """
        try:
            if session_id not in self.mixing_states:
                return False

            mixing_state = self.mixing_states[session_id]
            if source_id not in mixing_state.active_sources:
                return False

            mixing_state.active_sources[source_id].position = position

            # Clear HRTF cache for this position
            cache_key = ".2f"
            if cache_key in self.hrtf_processor.hrtf_cache:
                del self.hrtf_processor.hrtf_cache[cache_key]

            self.logger.info(
                "Updated position for source %s in session %s", source_id, session_id
            )
            return True

        except Exception as e:
            self.logger.error("Position update failed: %s", e)
            return False

    async def get_mixing_state(self, session_id: str) -> Optional[MixingState]:
        """Get current mixing state for a session."""
        return self.mixing_states.get(session_id)

    async def get_audio_buffer(
        self, session_id: str, num_frames: int = 10
    ) -> List[np.ndarray]:
        """Get recent audio buffer for monitoring/debugging."""
        if session_id not in self.source_buffers:
            return []

        return self.source_buffers[session_id][-num_frames:]

    async def cleanup_session(self, session_id: str):
        """Clean up resources for a mixing session."""
        try:
            if session_id in self.mixing_states:
                del self.mixing_states[session_id]
            if session_id in self.source_buffers:
                del self.source_buffers[session_id]

            self.logger.info("Cleaned up mixing session: %s", session_id)

        except Exception as e:
            self.logger.error("Session cleanup failed: %s", e)

    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a mixing session."""
        if session_id not in self.mixing_states:
            return {}

        mixing_state = self.mixing_states[session_id]

        return {
            "session_id": session_id,
            "active_sources": len(mixing_state.active_sources),
            "master_volume": mixing_state.master_volume,
            "ducking_enabled": mixing_state.ducking_enabled,
            "spatial_enabled": mixing_state.spatial_enabled,
            "focus_mode": mixing_state.focus_mode,
            "focus_speaker": mixing_state.focus_speaker,
            "last_mix_time": mixing_state.last_mix_time.isoformat(),
            "buffer_frames": len(self.source_buffers.get(session_id, [])),
        }


# Global AudioMixerService instance
audio_mixer_service = AudioMixerService()
