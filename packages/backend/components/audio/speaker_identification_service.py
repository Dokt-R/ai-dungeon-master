"""
Speaker Identification Service Component for AI Dungeon Master.

This module provides comprehensive speaker identification and diarization capabilities
for multi-user voice conversations, enabling accurate speaker attribution and voice
biometric matching.

Features:
- Voice biometric processing and matching
- Speaker profile management and updates
- Real-time speaker identification with confidence scoring
- Voice print generation and storage
- Speaker diarization for conversation attribution
- Multi-speaker conversation support
"""

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger
from packages.shared.models import (
    MultiUserConversation,
    SpeakerProfile,
    VoiceActivitySegment,
)

logger = get_logger(__name__)


@dataclass
class SpeakerMatch:
    """Result of speaker identification matching."""

    speaker_id: str
    confidence: float
    profile_id: str
    match_score: float
    audio_features: Dict[str, float]
    comparison_details: Dict[str, Any]


@dataclass
class VoiceBiometricData:
    """Voice biometric features for identification."""

    fundamental_frequency: float  # F0 in Hz
    pitch_range: float  # Pitch variation
    speaking_rate: float  # Syllables per second
    formant_frequencies: List[float]  # F1, F2, F3 in Hz
    spectral_centroid: float  # Spectral centroid
    mfcc_features: List[float]  # MFCC coefficients
    voice_quality: float  # Voice quality measure
    articulation_rate: float  # Clear speech rate
    extracted_at: datetime = field(default_factory=datetime.utcnow)


class SpeakerIdentificationService:
    """
    Speaker identification and diarization service.

    Features:
    - Voice biometric processing and matching
    - Speaker profile management and updates
    - Real-time speaker identification
    - Voice print generation and storage
    - Speaker diarization for conversation attribution
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Speaker profiles
        self.speaker_profiles: Dict[str, SpeakerProfile] = {}
        self.user_profiles: Dict[str, List[str]] = {}  # user_id -> profile_ids

        # Active conversations
        self.active_conversations: Dict[str, MultiUserConversation] = {}

        # Performance tracking
        self.identification_stats = {
            "total_identifications": 0,
            "successful_identifications": 0,
            "identification_accuracy": 0.0,
            "average_confidence": 0.0,
            "average_processing_time": 0.0,
            "false_positives": 0,
            "false_negatives": 0,
        }

        # Configuration
        self.enable_real_time_identification = True
        self.enable_profile_updates = True
        self.min_confidence_threshold = 0.8
        self.max_profiles_per_user = 5
        self.profile_retention_days = 365
        self.biometric_update_threshold = 0.9

        logger.info("speaker_identification_service_initialized")

    async def create_speaker_profile(
        self,
        user_id: str,
        audio_samples: List[bytes],
        profile_name: str = "default",
        correlation_id: Optional[str] = None,
    ) -> Optional[SpeakerProfile]:
        """
        Create a new speaker profile from audio samples.

        Args:
            user_id: User identifier
            audio_samples: List of audio sample bytes
            profile_name: Name for the profile
            correlation_id: Correlation ID for tracing

        Returns:
            Created speaker profile or None if creation fails
        """
        try:
            with observability_service.trace_operation(
                operation_name="create_speaker_profile",
                user_id=user_id,
                sample_count=len(audio_samples),
                correlation_id=correlation_id,
            ) as trace_id:
                # Generate unique profile ID
                profile_id = f"profile_{user_id}_{int(time.time() * 1000)}"

                # Extract voice characteristics from samples
                voice_characteristics = await self._extract_voice_characteristics(
                    audio_samples
                )

                # Generate voice print (simplified representation)
                voice_print = await self._generate_voice_print(
                    audio_samples, voice_characteristics
                )

                # Create profile
                profile = SpeakerProfile(
                    profile_id=profile_id,
                    user_id=user_id,
                    voice_print=voice_print,
                    voice_characteristics=voice_characteristics,
                    sample_audio_clips=audio_samples[:5],  # Keep up to 5 samples
                    confidence_threshold=self.min_confidence_threshold,
                    total_training_samples=len(audio_samples),
                )

                # Store profile
                self.speaker_profiles[profile_id] = profile

                # Update user profile mapping
                if user_id not in self.user_profiles:
                    self.user_profiles[user_id] = []
                self.user_profiles[user_id].append(profile_id)

                # Clean up old profiles if needed
                await self._cleanup_old_profiles(user_id)

                logger.info(
                    "speaker_profile_created",
                    profile_id=profile_id,
                    user_id=user_id,
                    sample_count=len(audio_samples),
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                )

                return profile

        except Exception as e:
            logger.error(
                "speaker_profile_creation_failed",
                user_id=user_id,
                error=str(e),
                correlation_id=correlation_id,
            )
            return None

    async def identify_speaker(
        self,
        audio_segment: bytes,
        session_id: str,
        candidate_user_ids: List[str],
        correlation_id: Optional[str] = None,
    ) -> Optional[SpeakerMatch]:
        """
        Identify speaker from audio segment.

        Args:
            audio_segment: Audio data to analyze
            session_id: Voice session identifier
            candidate_user_ids: List of candidate user IDs to match against
            correlation_id: Correlation ID for tracing

        Returns:
            Speaker match result or None if no match found
        """
        start_time = time.time()

        try:
            with observability_service.trace_operation(
                operation_name="speaker_identification",
                session_id=session_id,
                candidate_count=len(candidate_user_ids),
                correlation_id=correlation_id,
            ) as trace_id:
                # Extract voice characteristics from audio segment
                voice_characteristics = await self._extract_voice_characteristics(
                    [audio_segment]
                )

                # Get candidate profiles
                candidate_profiles = []
                for user_id in candidate_user_ids:
                    if user_id in self.user_profiles:
                        for profile_id in self.user_profiles[user_id]:
                            if profile_id in self.speaker_profiles:
                                candidate_profiles.append(
                                    self.speaker_profiles[profile_id]
                                )

                if not candidate_profiles:
                    return None

                # Match against candidate profiles
                matches = []
                for profile in candidate_profiles:
                    (
                        match_score,
                        comparison_details,
                    ) = await self._compare_voice_characteristics(
                        voice_characteristics, profile.voice_characteristics
                    )

                    confidence = self._calculate_identification_confidence(
                        match_score, profile
                    )

                    if confidence >= self.min_confidence_threshold:
                        matches.append(
                            SpeakerMatch(
                                speaker_id=profile.user_id,
                                confidence=confidence,
                                profile_id=profile.profile_id,
                                match_score=match_score,
                                audio_features=voice_characteristics,
                                comparison_details=comparison_details,
                            )
                        )

                if not matches:
                    return None

                # Return best match
                best_match = max(matches, key=lambda m: m.confidence)

                # Update profile if confidence is high
                if (
                    self.enable_profile_updates
                    and best_match.confidence >= self.biometric_update_threshold
                ):
                    await self._update_speaker_profile(
                        best_match.profile_id, audio_segment, voice_characteristics
                    )

                # Update statistics
                self._update_identification_stats(
                    True, best_match.confidence, time.time() - start_time
                )

                # Update profile last identification
                profile = self.speaker_profiles[best_match.profile_id]
                profile.last_identification = datetime.utcnow()
                profile.identification_accuracy = (
                    profile.identification_accuracy * 0.9 + best_match.confidence * 0.1
                )

                logger.info(
                    "speaker_identified",
                    speaker_id=best_match.speaker_id,
                    profile_id=best_match.profile_id,
                    confidence=best_match.confidence,
                    session_id=session_id,
                    processing_time=time.time() - start_time,
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                )

                return best_match

        except Exception as e:
            processing_time = time.time() - start_time
            self._update_identification_stats(False, 0.0, processing_time)

            logger.error(
                "speaker_identification_failed",
                session_id=session_id,
                processing_time=processing_time,
                error=str(e),
                correlation_id=correlation_id,
            )
            return None

    async def perform_speaker_diarization(
        self,
        audio_stream: bytes,
        session_id: str,
        known_speakers: List[str],
        correlation_id: Optional[str] = None,
    ) -> List[VoiceActivitySegment]:
        """
        Perform speaker diarization on audio stream.

        Args:
            audio_stream: Audio data to analyze
            session_id: Voice session identifier
            known_speakers: List of known speaker user IDs
            correlation_id: Correlation ID for tracing

        Returns:
            List of voice activity segments with speaker attribution
        """
        try:
            with observability_service.trace_operation(
                operation_name="speaker_diarization",
                session_id=session_id,
                known_speakers=len(known_speakers),
                correlation_id=correlation_id,
            ) as trace_id:
                # In a real implementation, this would:
                # 1. Split audio into segments based on voice activity
                # 2. Extract features from each segment
                # 3. Identify speakers for each segment
                # 4. Handle speaker changes and overlaps

                # Simplified implementation
                segments = []

                # Simulate segmentation (would use VAD in real implementation)
                segment_duration = 2.0  # 2-second segments
                audio_duration = len(audio_stream) / (16000 * 2)  # Rough estimation

                current_time = datetime.utcnow()

                for i in range(0, int(audio_duration), int(segment_duration)):
                    segment_id = f"segment_{session_id}_{i}"

                    # Try to identify speaker for this segment
                    segment_data = audio_stream[
                        i * 32000 : (i + 2) * 32000
                    ]  # 2 seconds at 16kHz
                    if segment_data:
                        speaker_match = await self.identify_speaker(
                            segment_data, session_id, known_speakers, correlation_id
                        )

                        segment = VoiceActivitySegment(
                            segment_id=segment_id,
                            session_id=session_id,
                            speaker_id=speaker_match.speaker_id
                            if speaker_match
                            else None,
                            start_time=current_time + timedelta(seconds=i),
                            end_time=current_time
                            + timedelta(seconds=i + segment_duration),
                            confidence=speaker_match.confidence
                            if speaker_match
                            else 0.0,
                            energy_level=0.5,  # Would calculate from audio
                            noise_level=0.1,  # Would estimate from audio
                            speaker_confidence=speaker_match.confidence
                            if speaker_match
                            else None,
                            duration=segment_duration,
                        )

                        segments.append(segment)

                logger.info(
                    "speaker_diarization_completed",
                    session_id=session_id,
                    segments=len(segments),
                    identified_segments=len([s for s in segments if s.speaker_id]),
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                )

                return segments

        except Exception as e:
            logger.error(
                "speaker_diarization_failed",
                session_id=session_id,
                error=str(e),
                correlation_id=correlation_id,
            )
            return []

    async def _extract_voice_characteristics(
        self, audio_samples: List[bytes]
    ) -> Dict[str, float]:
        """Extract voice characteristics from audio samples."""
        try:
            # In a real implementation, this would use signal processing libraries
            # to extract actual voice characteristics

            # Simplified mock implementation
            characteristics = {}

            if audio_samples:
                # Use hash of audio data to generate consistent "characteristics"
                sample_hash = hashlib.md5(audio_samples[0]).hexdigest()

                # Generate pseudo-random but consistent characteristics
                hash_int = int(sample_hash[:8], 16)

                characteristics = {
                    "fundamental_frequency": 85 + (hash_int % 80),  # 85-165 Hz
                    "pitch_range": 10 + (hash_int % 20),  # 10-30 Hz variation
                    "speaking_rate": 120 + (hash_int % 80),  # 120-200 syllables/min
                    "spectral_centroid": 2000 + (hash_int % 2000),  # 2000-4000 Hz
                    "voice_quality": 0.6 + ((hash_int % 40) / 100),  # 0.6-1.0
                    "articulation_rate": 4.0
                    + ((hash_int % 20) / 10),  # 4.0-6.0 syllables/sec
                }

            return characteristics

        except Exception as e:
            logger.warning("voice_characteristics_extraction_failed", error=str(e))
            return {}

    async def _generate_voice_print(
        self, audio_samples: List[bytes], characteristics: Dict[str, float]
    ) -> bytes:
        """Generate voice print from audio samples and characteristics."""
        try:
            # In a real implementation, this would create a compact biometric representation
            # For now, create a hash-based representation

            combined_data = b""
            for sample in audio_samples[:3]:  # Use first 3 samples
                combined_data += sample[:1024]  # Use first 1KB of each

            # Add characteristics to the mix
            char_string = str(sorted(characteristics.items())).encode("utf-8")
            combined_data += char_string

            # Generate voice print hash
            voice_print = hashlib.sha256(combined_data).digest()

            return voice_print

        except Exception as e:
            logger.error("voice_print_generation_failed", error=str(e))
            return b"default_voice_print"

    async def _compare_voice_characteristics(
        self,
        sample_characteristics: Dict[str, float],
        profile_characteristics: Dict[str, float],
    ) -> Tuple[float, Dict[str, Any]]:
        """Compare voice characteristics between sample and profile."""
        try:
            if not profile_characteristics:
                return 0.0, {"error": "No profile characteristics"}

            # Calculate similarity for each characteristic
            similarities = {}
            details = {}

            for key in profile_characteristics.keys():
                if key in sample_characteristics:
                    sample_value = sample_characteristics[key]
                    profile_value = profile_characteristics[key]

                    if profile_value != 0:
                        # Calculate relative difference
                        diff = abs(sample_value - profile_value) / profile_value
                        similarity = max(0.0, 1.0 - diff)
                    else:
                        similarity = 1.0 if sample_value == 0 else 0.0

                    similarities[key] = similarity
                    details[key] = {
                        "sample": sample_value,
                        "profile": profile_value,
                        "similarity": similarity,
                    }

            # Calculate overall match score (weighted average)
            weights = {
                "fundamental_frequency": 0.25,
                "pitch_range": 0.15,
                "speaking_rate": 0.20,
                "spectral_centroid": 0.15,
                "voice_quality": 0.15,
                "articulation_rate": 0.10,
            }

            overall_score = 0.0
            total_weight = 0.0

            for key, weight in weights.items():
                if key in similarities:
                    overall_score += similarities[key] * weight
                    total_weight += weight

            if total_weight > 0:
                overall_score /= total_weight

            return overall_score, {
                "individual_similarities": similarities,
                "details": details,
                "overall_score": overall_score,
            }

        except Exception as e:
            logger.error("voice_characteristics_comparison_failed", error=str(e))
            return 0.0, {"error": str(e)}

    def _calculate_identification_confidence(
        self, match_score: float, profile: SpeakerProfile
    ) -> float:
        """Calculate identification confidence based on match score and profile history."""
        try:
            # Base confidence from match score
            base_confidence = match_score

            # Adjust based on profile accuracy history
            accuracy_boost = profile.identification_accuracy * 0.1

            # Adjust based on training samples
            training_boost = min(profile.total_training_samples / 100.0, 0.1)

            # Adjust based on recency of last identification
            recency_boost = 0.0
            if profile.last_identification:
                days_since_last = (datetime.utcnow() - profile.last_identification).days
                recency_boost = max(0.0, 0.05 * (30 - days_since_last) / 30)

            confidence = (
                base_confidence + accuracy_boost + training_boost + recency_boost
            )
            return min(confidence, 1.0)

        except Exception as e:
            logger.warning("confidence_calculation_failed", error=str(e))
            return match_score

    async def _update_speaker_profile(
        self, profile_id: str, audio_sample: bytes, characteristics: Dict[str, float]
    ) -> None:
        """Update speaker profile with new sample."""
        try:
            if profile_id not in self.speaker_profiles:
                return

            profile = self.speaker_profiles[profile_id]

            # Update voice characteristics (weighted average)
            for key, new_value in characteristics.items():
                if key in profile.voice_characteristics:
                    current_value = profile.voice_characteristics[key]
                    # Weighted average favoring recent samples
                    updated_value = (current_value * 0.7) + (new_value * 0.3)
                    profile.voice_characteristics[key] = updated_value

            # Add new sample to clips (keep only recent ones)
            profile.sample_audio_clips.append(audio_sample)
            if len(profile.sample_audio_clips) > 5:
                profile.sample_audio_clips = profile.sample_audio_clips[-5:]

            profile.total_training_samples += 1
            profile.last_updated = datetime.utcnow()

            logger.debug("speaker_profile_updated", profile_id=profile_id)

        except Exception as e:
            logger.error(
                "speaker_profile_update_failed", profile_id=profile_id, error=str(e)
            )

    async def _cleanup_old_profiles(self, user_id: str) -> None:
        """Clean up old speaker profiles for user."""
        try:
            if user_id not in self.user_profiles:
                return

            profile_ids = self.user_profiles[user_id]

            # Sort by last updated (most recent first)
            profiles = []
            for profile_id in profile_ids:
                if profile_id in self.speaker_profiles:
                    profiles.append(self.speaker_profiles[profile_id])

            profiles.sort(key=lambda p: p.last_updated, reverse=True)

            # Keep only the most recent profiles
            profiles_to_keep = profiles[: self.max_profiles_per_user]
            profiles_to_remove = profiles[self.max_profiles_per_user :]

            # Remove old profiles
            for profile in profiles_to_remove:
                if profile.profile_id in self.speaker_profiles:
                    del self.speaker_profiles[profile.profile_id]
                if profile.profile_id in profile_ids:
                    profile_ids.remove(profile.profile_id)

            if profiles_to_remove:
                logger.info(
                    "old_speaker_profiles_cleaned",
                    user_id=user_id,
                    removed_count=len(profiles_to_remove),
                )

        except Exception as e:
            logger.error("profile_cleanup_failed", user_id=user_id, error=str(e))

    def _update_identification_stats(
        self, success: bool, confidence: float, processing_time: float
    ) -> None:
        """Update identification statistics."""
        self.identification_stats["total_identifications"] += 1

        if success:
            self.identification_stats["successful_identifications"] += 1

        # Update rolling averages
        total = self.identification_stats["total_identifications"]
        current_avg_confidence = self.identification_stats["average_confidence"]
        current_avg_time = self.identification_stats["average_processing_time"]

        if success:
            self.identification_stats["average_confidence"] = (
                (current_avg_confidence * (total - 1)) + confidence
            ) / total

        self.identification_stats["average_processing_time"] = (
            (current_avg_time * (total - 1)) + processing_time
        ) / total

        # Update accuracy
        successful = self.identification_stats["successful_identifications"]
        if total > 0:
            self.identification_stats["identification_accuracy"] = successful / total

    def get_speaker_profile(self, profile_id: str) -> Optional[SpeakerProfile]:
        """Get speaker profile by ID."""
        return self.speaker_profiles.get(profile_id)

    def get_user_profiles(self, user_id: str) -> List[SpeakerProfile]:
        """Get all speaker profiles for a user."""
        if user_id not in self.user_profiles:
            return []

        profiles = []
        for profile_id in self.user_profiles[user_id]:
            if profile_id in self.speaker_profiles:
                profiles.append(self.speaker_profiles[profile_id])

        return profiles

    def delete_speaker_profile(self, profile_id: str) -> bool:
        """Delete a speaker profile."""
        try:
            if profile_id in self.speaker_profiles:
                profile = self.speaker_profiles[profile_id]
                del self.speaker_profiles[profile_id]

                # Remove from user mapping
                if profile.user_id in self.user_profiles:
                    if profile_id in self.user_profiles[profile.user_id]:
                        self.user_profiles[profile.user_id].remove(profile_id)

                logger.info("speaker_profile_deleted", profile_id=profile_id)
                return True

        except Exception as e:
            logger.error(
                "speaker_profile_deletion_failed", profile_id=profile_id, error=str(e)
            )

        return False

    def get_identification_stats(self) -> Dict[str, Any]:
        """Get identification statistics."""
        return self.identification_stats.copy()

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the speaker identification service."""
        accuracy = self.identification_stats["identification_accuracy"]
        avg_confidence = self.identification_stats["average_confidence"]
        avg_processing_time = self.identification_stats["average_processing_time"]

        # Determine health status
        if accuracy >= 0.9 and avg_confidence >= 0.8:
            status = "healthy"
        elif accuracy >= 0.7 or avg_confidence >= 0.6:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "total_profiles": len(self.speaker_profiles),
            "total_users": len(self.user_profiles),
            "identification_accuracy": accuracy,
            "average_confidence": avg_confidence,
            "average_processing_time": avg_processing_time,
            "real_time_identification_enabled": self.enable_real_time_identification,
            "profile_updates_enabled": self.enable_profile_updates,
        }


# Global speaker identification service instance
speaker_identification_service = SpeakerIdentificationService()
