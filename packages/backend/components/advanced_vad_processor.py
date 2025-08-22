"""
Advanced Voice Activity Detection (VAD) Processor.

This module provides enhanced voice activity detection with noise filtering,
multi-speaker overlap detection, adaptive thresholds, and confidence scoring
for improved accuracy in group conversation scenarios.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

from packages.backend.components.audio_utils import AudioUtils
from packages.shared.logging_config import get_logger
from packages.shared.models import VoiceActivitySegment

logger = get_logger(__name__)


class VADConfiguration(BaseModel):
    """Configuration for advanced VAD processing."""

    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    frame_length_ms: int = Field(default=30, description="Frame length in milliseconds")
    hop_length_ms: int = Field(default=10, description="Hop length in milliseconds")
    energy_threshold_db: float = Field(
        default=-20.0, description="Energy threshold in dB"
    )
    spectral_flatness_threshold: float = Field(
        default=0.3, description="Spectral flatness threshold"
    )
    min_speech_duration_ms: int = Field(
        default=100, description="Minimum speech duration"
    )
    max_silence_duration_ms: int = Field(
        default=500, description="Maximum silence duration"
    )
    overlap_detection_threshold: float = Field(
        default=0.6, description="Overlap detection threshold"
    )
    noise_adaptation_rate: float = Field(
        default=0.01, description="Noise adaptation rate"
    )
    confidence_threshold: float = Field(
        default=0.8, description="VAD confidence threshold"
    )
    adaptive_threshold_enabled: bool = Field(
        default=True, description="Enable adaptive thresholds"
    )


@dataclass
class VADState:
    """State tracking for VAD processing."""

    is_active: bool = False
    current_speaker: Optional[str] = None
    confidence_score: float = 0.0
    energy_level: float = 0.0
    noise_level: float = 0.0
    overlap_detected: bool = False
    adaptive_threshold: float = -20.0
    last_update: datetime = field(default_factory=datetime.utcnow)


class AdvancedVADProcessor:
    """
    Advanced Voice Activity Detection processor with multi-speaker support.

    Features:
    - Noise filtering and adaptive thresholds
    - Multi-speaker overlap detection
    - Confidence scoring and validation
    - Real-time processing with low latency
    """

    def __init__(self, config: Optional[VADConfiguration] = None):
        self.config = config or VADConfiguration()
        self.audio_utils = AudioUtils()
        self.vad_states: Dict[str, VADState] = {}
        self.noise_profiles: Dict[str, np.ndarray] = {}
        self.logger = logger

        # Initialize VAD parameters
        self.frame_length_samples = int(
            self.config.sample_rate * self.config.frame_length_ms / 1000
        )
        self.hop_length_samples = int(
            self.config.sample_rate * self.config.hop_length_ms / 1000
        )

        self.logger.info(
            "AdvancedVADProcessor initialized with config: %s", self.config.dict()
        )

    async def process_audio_frame(
        self, session_id: str, audio_data: bytes, speaker_id: Optional[str] = None
    ) -> List[VoiceActivitySegment]:
        """
        Process an audio frame for voice activity detection.

        Args:
            session_id: Voice session identifier
            audio_data: Raw audio data
            speaker_id: Optional speaker identifier

        Returns:
            List of voice activity segments detected
        """
        try:
            # Convert audio data to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.float32)

            # Initialize VAD state if not exists
            if session_id not in self.vad_states:
                self.vad_states[session_id] = VADState()

            # Apply noise filtering
            filtered_audio = await self._apply_noise_filtering(audio_array, session_id)

            # Detect voice activity
            vad_result = await self._detect_voice_activity(
                filtered_audio, session_id, speaker_id
            )

            # Generate voice activity segments
            segments = await self._generate_segments(session_id, vad_result, speaker_id)

            return segments

        except Exception as e:
            self.logger.error(
                "Error processing audio frame for session %s: %s", session_id, e
            )
            return []

    async def _apply_noise_filtering(
        self, audio_array: np.ndarray, session_id: str
    ) -> np.ndarray:
        """Apply noise filtering to audio data."""
        try:
            # Estimate noise profile if not available
            if session_id not in self.noise_profiles:
                self.noise_profiles[session_id] = await self._estimate_noise_profile(
                    audio_array
                )

            # Apply spectral subtraction for noise reduction
            filtered_audio = await self._spectral_subtraction(
                audio_array, self.noise_profiles[session_id]
            )

            # Update noise profile adaptively
            await self._update_noise_profile(audio_array, session_id)

            return filtered_audio

        except Exception as e:
            self.logger.warning(
                "Noise filtering failed for session %s: %s", session_id, e
            )
            return audio_array

    async def _estimate_noise_profile(self, audio_array: np.ndarray) -> np.ndarray:
        """Estimate noise profile from audio data."""
        # Simple noise estimation using low-energy frames
        frame_energy = await self.audio_utils.calculate_frame_energy(
            audio_array, self.frame_length_samples, self.hop_length_samples
        )

        # Find frames with low energy (potential noise)
        low_energy_threshold = np.percentile(frame_energy, 20)  # Bottom 20% as noise
        noise_frames = audio_array[frame_energy <= low_energy_threshold]

        if len(noise_frames) > 0:
            # Compute average spectrum of noise frames
            noise_spectrum = np.mean(np.abs(np.fft.rfft(noise_frames, axis=1)), axis=0)
            return noise_spectrum

        # Fallback: use first few frames as noise estimate
        return np.abs(np.fft.rfft(audio_array[: self.frame_length_samples]))

    async def _spectral_subtraction(
        self, audio_array: np.ndarray, noise_profile: np.ndarray
    ) -> np.ndarray:
        """Apply spectral subtraction for noise reduction."""
        # Compute STFT
        stft = np.fft.rfft(audio_array)

        # Apply spectral subtraction
        alpha = 2.0  # Over-subtraction factor
        enhanced_spectrum = np.maximum(np.abs(stft) - alpha * noise_profile, 0)

        # Restore phase
        enhanced_stft = enhanced_spectrum * np.exp(1j * np.angle(stft))

        # Inverse STFT
        enhanced_audio = np.fft.irfft(enhanced_stft)
        return enhanced_audio

    async def _update_noise_profile(self, audio_array: np.ndarray, session_id: str):
        """Update noise profile adaptively."""
        if not self.config.adaptive_threshold_enabled:
            return

        # Compute current noise estimate
        current_noise = await self._estimate_noise_profile(audio_array)

        # Adaptive update
        alpha = self.config.noise_adaptation_rate
        self.noise_profiles[session_id] = (1 - alpha) * self.noise_profiles[
            session_id
        ] + alpha * current_noise

    async def _detect_voice_activity(
        self, audio_array: np.ndarray, session_id: str, speaker_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Detect voice activity with multi-speaker support."""
        vad_state = self.vad_states[session_id]

        # Calculate audio features
        features = await self._extract_audio_features(audio_array)

        # Multi-speaker VAD decision
        vad_decision = await self._multi_speaker_vad_decision(
            features, session_id, speaker_id
        )

        # Update VAD state
        vad_state.is_active = vad_decision["is_active"]
        vad_state.confidence_score = vad_decision["confidence"]
        vad_state.energy_level = features["energy"]
        vad_state.noise_level = features["noise_level"]
        vad_state.overlap_detected = vad_decision["overlap_detected"]
        vad_state.last_update = datetime.utcnow()

        if speaker_id:
            vad_state.current_speaker = speaker_id

        # Update adaptive threshold
        if self.config.adaptive_threshold_enabled:
            await self._update_adaptive_threshold(session_id, features)

        return vad_decision

    async def _extract_audio_features(
        self, audio_array: np.ndarray
    ) -> Dict[str, float]:
        """Extract audio features for VAD decision."""
        # Frame energy
        energy = await self.audio_utils.calculate_rms_energy(audio_array)

        # Spectral flatness (measure of noise-like vs speech-like)
        spectral_flatness = await self._calculate_spectral_flatness(audio_array)

        # Zero-crossing rate
        zero_crossing_rate = await self.audio_utils.calculate_zero_crossing_rate(
            audio_array
        )

        # Noise level estimation
        noise_level = await self._estimate_noise_level(audio_array)

        return {
            "energy": energy,
            "spectral_flatness": spectral_flatness,
            "zero_crossing_rate": zero_crossing_rate,
            "noise_level": noise_level,
        }

    async def _calculate_spectral_flatness(self, audio_array: np.ndarray) -> float:
        """Calculate spectral flatness measure."""
        spectrum = np.abs(np.fft.rfft(audio_array))

        # Avoid log(0) by adding small epsilon
        epsilon = 1e-10
        spectrum = np.maximum(spectrum, epsilon)

        # Geometric mean / arithmetic mean
        geometric_mean = np.exp(np.mean(np.log(spectrum)))
        arithmetic_mean = np.mean(spectrum)

        if arithmetic_mean > 0:
            return geometric_mean / arithmetic_mean
        return 0.0

    async def _estimate_noise_level(self, audio_array: np.ndarray) -> float:
        """Estimate background noise level."""
        # Simple noise estimation using low-frequency components
        spectrum = np.abs(np.fft.rfft(audio_array))
        low_freq_spectrum = spectrum[: len(spectrum) // 4]  # Low frequency components

        return np.mean(low_freq_spectrum) if len(low_freq_spectrum) > 0 else 0.0

    async def _multi_speaker_vad_decision(
        self,
        features: Dict[str, float],
        session_id: str,
        speaker_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Make VAD decision for multi-speaker scenarios."""
        energy_db = 20 * np.log10(max(features["energy"], 1e-10))

        # Get adaptive threshold
        vad_state = self.vad_states[session_id]
        threshold = vad_state.adaptive_threshold

        # Basic energy-based VAD
        is_active_energy = energy_db > threshold

        # Spectral flatness check (low flatness indicates speech-like signal)
        is_active_spectral = (
            features["spectral_flatness"] < self.config.spectral_flatness_threshold
        )

        # Combine decisions
        is_active = is_active_energy and is_active_spectral

        # Calculate confidence score
        confidence = await self._calculate_vad_confidence(
            features, energy_db, threshold
        )

        # Detect speaker overlap
        overlap_detected = await self._detect_speaker_overlap(session_id, features)

        return {
            "is_active": is_active,
            "confidence": confidence,
            "overlap_detected": overlap_detected,
            "energy_db": energy_db,
            "threshold": threshold,
        }

    async def _calculate_vad_confidence(
        self, features: Dict[str, float], energy_db: float, threshold: float
    ) -> float:
        """Calculate confidence score for VAD decision."""
        # Energy confidence
        energy_margin = energy_db - threshold
        energy_confidence = min(1.0, max(0.0, energy_margin / 20.0))  # Normalize to 0-1

        # Spectral flatness confidence
        spectral_confidence = 1.0 - features["spectral_flatness"]

        # Combined confidence with weights
        confidence = 0.6 * energy_confidence + 0.4 * spectral_confidence

        return confidence

    async def _detect_speaker_overlap(
        self, session_id: str, features: Dict[str, float]
    ) -> bool:
        """Detect if multiple speakers are talking simultaneously."""
        # Check if energy is significantly higher than typical single speaker
        # This is a simplified approach - in practice, you'd use more sophisticated methods
        overlap_threshold = self.config.overlap_detection_threshold

        # Look for high energy with mixed frequency characteristics
        high_energy = features["energy"] > np.percentile([0.1, 0.2, 0.3], 80)
        mixed_frequencies = features["zero_crossing_rate"] > 0.15

        return high_energy and mixed_frequencies

    async def _update_adaptive_threshold(
        self, session_id: str, features: Dict[str, float]
    ):
        """Update adaptive threshold based on environmental conditions."""
        vad_state = self.vad_states[session_id]

        # Simple adaptive threshold update
        current_noise = features["noise_level"]
        noise_db = 20 * np.log10(max(current_noise, 1e-10))

        # Smooth threshold adaptation
        alpha = 0.05  # Adaptation rate
        vad_state.adaptive_threshold = (
            1 - alpha
        ) * vad_state.adaptive_threshold + alpha * (noise_db + 10)

    async def _generate_segments(
        self,
        session_id: str,
        vad_result: Dict[str, Any],
        speaker_id: Optional[str] = None,
    ) -> List[VoiceActivitySegment]:
        """Generate voice activity segments from VAD results."""
        vad_state = self.vad_states[session_id]

        segments = []

        # Create segment if voice activity detected
        if (
            vad_result["is_active"]
            and vad_result["confidence"] >= self.config.confidence_threshold
        ):
            segment = VoiceActivitySegment(
                segment_id=f"{session_id}_{datetime.utcnow().timestamp()}",
                session_id=session_id,
                speaker_id=speaker_id,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),  # Will be updated when activity ends
                confidence=vad_result["confidence"],
                energy_level=vad_result["energy_db"],
                noise_level=20 * np.log10(max(vad_state.noise_level, 1e-10)),
                overlap_detected=vad_result["overlap_detected"],
            )
            segments.append(segment)

        return segments

    async def get_vad_state(self, session_id: str) -> Optional[VADState]:
        """Get current VAD state for a session."""
        return self.vad_states.get(session_id)

    async def reset_session(self, session_id: str):
        """Reset VAD state for a session."""
        if session_id in self.vad_states:
            del self.vad_states[session_id]
        if session_id in self.noise_profiles:
            del self.noise_profiles[session_id]

        self.logger.info("Reset VAD session: %s", session_id)

    async def cleanup_inactive_sessions(self, max_age_seconds: int = 300):
        """Clean up inactive VAD sessions."""
        current_time = datetime.utcnow()

        inactive_sessions = [
            session_id
            for session_id, state in self.vad_states.items()
            if (current_time - state.last_update).total_seconds() > max_age_seconds
        ]

        for session_id in inactive_sessions:
            await self.reset_session(session_id)

        if inactive_sessions:
            self.logger.info(
                "Cleaned up %d inactive VAD sessions", len(inactive_sessions)
            )
