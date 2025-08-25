"""
Conversation Intelligence Engine for Multi-User Voice Interactions.

This module provides advanced conversation analysis including sentiment detection,
engagement tracking, conversation flow analysis, and highlight generation for
enhanced group dynamics and storytelling experiences.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
from pydantic import BaseModel, Field

from packages.backend.components.audio_utils import AudioUtils
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


class SentimentAnalysis(BaseModel):
    """Sentiment analysis result for voice segments."""

    segment_id: str = Field(..., description="Voice segment identifier")
    speaker_id: str = Field(..., description="Speaker identifier")
    sentiment_score: float = Field(
        ..., ge=-1.0, le=1.0, description="Sentiment score (-1 to 1)"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")
    emotion_labels: List[str] = Field(
        default_factory=list, description="Detected emotions"
    )
    intensity: float = Field(..., ge=0.0, le=1.0, description="Emotional intensity")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EngagementMetrics(BaseModel):
    """Engagement metrics for group conversations."""

    conversation_id: str = Field(..., description="Conversation identifier")
    speaker_engagement: Dict[str, float] = Field(
        default_factory=dict, description="Per-speaker engagement scores"
    )
    group_engagement_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall group engagement"
    )
    participation_balance: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Balance of participation"
    )
    interaction_frequency: float = Field(
        default=0.0, description="Interactions per minute"
    )
    dominant_speakers: List[str] = Field(
        default_factory=list, description="Most active speakers"
    )
    quiet_speakers: List[str] = Field(
        default_factory=list, description="Least active speakers"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationFlow(BaseModel):
    """Conversation flow and rhythm analysis."""

    conversation_id: str = Field(..., description="Conversation identifier")
    turn_taking_pattern: List[Dict[str, Any]] = Field(
        default_factory=list, description="Turn-taking events"
    )
    speaking_duration: Dict[str, float] = Field(
        default_factory=dict, description="Speaking time per speaker"
    )
    pause_duration: Dict[str, float] = Field(
        default_factory=dict, description="Pause time per speaker"
    )
    interruption_count: Dict[str, int] = Field(
        default_factory=dict, description="Interruptions per speaker"
    )
    rhythm_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Conversation rhythm quality"
    )
    flow_smoothness: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Flow smoothness score"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationHighlight(BaseModel):
    """Conversation highlight with context."""

    highlight_id: str = Field(..., description="Unique highlight identifier")
    conversation_id: str = Field(..., description="Conversation identifier")
    start_time: datetime = Field(..., description="Highlight start time")
    end_time: datetime = Field(..., description="Highlight end time")
    highlight_type: str = Field(..., description="Type of highlight")
    speakers_involved: List[str] = Field(
        default_factory=list, description="Speakers in highlight"
    )
    sentiment_score: float = Field(
        ..., ge=-1.0, le=1.0, description="Average sentiment"
    )
    engagement_score: float = Field(..., ge=0.0, le=1.0, description="Engagement level")
    significance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Highlight significance"
    )
    description: str = Field(..., description="Highlight description")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


@dataclass
class ConversationContext:
    """Context tracking for conversation analysis."""

    conversation_id: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    active_speakers: Dict[str, int] = field(
        default_factory=dict
    )  # speaker_id -> segment_count
    recent_segments: List[Dict[str, Any]] = field(default_factory=list)
    sentiment_history: Dict[str, List[float]] = field(
        default_factory=dict
    )  # speaker_id -> sentiment_scores
    engagement_history: List[float] = field(default_factory=list)
    last_turn_time: Dict[str, datetime] = field(default_factory=dict)
    interruption_events: List[Dict[str, Any]] = field(default_factory=list)
    pause_events: List[Dict[str, Any]] = field(default_factory=list)


class ConversationIntelligenceEngine:
    """
    Advanced conversation intelligence engine for multi-user voice interactions.

    Features:
    - Real-time sentiment analysis of voice interactions
    - Group engagement tracking and participation balance
    - Conversation flow and rhythm detection
    - Automatic highlight generation and summary creation
    - Turn-taking pattern recognition
    """

    def __init__(self, analysis_window_seconds: int = 300):
        self.audio_utils = AudioUtils()
        self.analysis_window = timedelta(seconds=analysis_window_seconds)
        self.conversation_contexts: Dict[str, ConversationContext] = {}
        self.logger = logger

        # Analysis parameters
        self.sentiment_threshold_high = 0.3
        self.sentiment_threshold_low = -0.3
        self.engagement_threshold = 0.7
        self.highlight_significance_threshold = 0.6

        self.logger.info(
            "ConversationIntelligenceEngine initialized",
            analysis_window_seconds=analysis_window_seconds,
        )

    async def analyze_voice_segment(
        self, conversation_id: str, segment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a voice segment for conversation intelligence.

        Args:
            conversation_id: Conversation identifier
            segment_data: Voice segment data with speaker_id, audio_data, etc.

        Returns:
            Analysis results including sentiment, engagement, and flow metrics
        """
        try:
            # Initialize conversation context if needed
            if conversation_id not in self.conversation_contexts:
                self.conversation_contexts[conversation_id] = ConversationContext(
                    conversation_id
                )

            context = self.conversation_contexts[conversation_id]

            # Perform comprehensive analysis
            sentiment = await self._analyze_sentiment(segment_data)
            engagement = await self._analyze_engagement(conversation_id, segment_data)
            flow_metrics = await self._analyze_conversation_flow(
                conversation_id, segment_data
            )

            # Update conversation context
            await self._update_conversation_context(
                conversation_id,
                segment_data,
                {
                    "sentiment": sentiment,
                    "engagement": engagement,
                    "flow": flow_metrics,
                },
            )

            # Generate highlights if significant events detected
            highlights = await self._detect_highlights(
                conversation_id,
                segment_data,
                {
                    "sentiment": sentiment,
                    "engagement": engagement,
                    "flow": flow_metrics,
                },
            )

            return {
                "conversation_id": conversation_id,
                "segment_id": segment_data.get("segment_id", "unknown"),
                "sentiment_analysis": sentiment,
                "engagement_metrics": engagement,
                "flow_analysis": flow_metrics,
                "highlights": highlights,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error("Voice segment analysis failed", error=str(e))
            return {}

    async def _analyze_sentiment(
        self, segment_data: Dict[str, Any]
    ) -> SentimentAnalysis:
        """Analyze sentiment from voice segment."""
        try:
            speaker_id = segment_data.get("speaker_id", "unknown")
            audio_data = segment_data.get("audio_data", np.array([]))

            # Extract audio features for sentiment analysis
            features = await self._extract_sentiment_features(audio_data)

            # Simplified sentiment analysis based on audio features
            # In practice, this would use ML models trained on voice sentiment
            sentiment_score = await self._calculate_sentiment_score(features)
            confidence = await self._calculate_sentiment_confidence(features)
            emotion_labels = await self._detect_emotions(features)
            intensity = await self._calculate_emotional_intensity(features)

            return SentimentAnalysis(
                segment_id=segment_data.get("segment_id", "unknown"),
                speaker_id=speaker_id,
                sentiment_score=sentiment_score,
                confidence=confidence,
                emotion_labels=emotion_labels,
                intensity=intensity,
            )

        except Exception as e:
            self.logger.warning("Sentiment analysis failed", error=str(e))
            return SentimentAnalysis(
                segment_id=segment_data.get("segment_id", "unknown"),
                speaker_id=segment_data.get("speaker_id", "unknown"),
                sentiment_score=0.0,
                confidence=0.0,
                intensity=0.0,
            )

    async def _extract_sentiment_features(
        self, audio_data: np.ndarray
    ) -> Dict[str, float]:
        """Extract audio features relevant to sentiment analysis."""
        try:
            # Pitch and fundamental frequency
            pitch = await self.audio_utils.calculate_pitch(audio_data)

            # Energy and RMS
            rms_energy = await self.audio_utils.calculate_rms_energy(audio_data)

            # Spectral centroid (brightness)
            spectral_centroid = await self._calculate_spectral_centroid(audio_data)

            # Zero crossing rate
            zcr = await self.audio_utils.calculate_zero_crossing_rate(audio_data)

            # Voice quality features
            jitter = await self._calculate_jitter(audio_data)
            shimmer = await self._calculate_shimmer(audio_data)

            return {
                "pitch": pitch,
                "rms_energy": rms_energy,
                "spectral_centroid": spectral_centroid,
                "zero_crossing_rate": zcr,
                "jitter": jitter,
                "shimmer": shimmer,
            }

        except Exception as e:
            self.logger.warning("Feature extraction failed", error=str(e))
            return {}

    async def _calculate_sentiment_score(self, features: Dict[str, float]) -> float:
        """Calculate sentiment score from audio features."""
        # Simplified sentiment model based on research findings
        score = 0.0

        # High pitch often indicates positive/enthusiastic sentiment
        if "pitch" in features and features["pitch"] > 200:  # Hz
            score += 0.3

        # High energy often indicates strong emotions
        if "rms_energy" in features and features["rms_energy"] > 0.1:
            score += 0.2

        # Bright spectral centroid can indicate positive emotions
        if "spectral_centroid" in features and features["spectral_centroid"] > 3000:
            score += 0.2

        # High zero crossing rate can indicate stress or excitement
        if "zero_crossing_rate" in features and features["zero_crossing_rate"] > 0.15:
            score += 0.1

        # Normalize to [-1, 1] range
        return max(-1.0, min(1.0, score))

    async def _calculate_sentiment_confidence(
        self, features: Dict[str, float]
    ) -> float:
        """Calculate confidence in sentiment analysis."""
        # Confidence based on feature completeness and consistency
        available_features = len([f for f in features.values() if f is not None])
        total_features = len(features)

        if total_features == 0:
            return 0.0

        return min(1.0, available_features / total_features * 0.8 + 0.2)

    async def _detect_emotions(self, features: Dict[str, float]) -> List[str]:
        """Detect emotions from audio features."""
        emotions = []

        try:
            # Simple rule-based emotion detection
            if features.get("pitch", 0) > 250:
                emotions.append("excited")

            if features.get("rms_energy", 0) > 0.15:
                emotions.append("enthusiastic")

            if features.get("jitter", 0) > 0.02:
                emotions.append("nervous")

            if features.get("shimmer", 0) > 0.05:
                emotions.append("emotional")

            # Ensure at least neutral emotion
            if not emotions:
                emotions.append("neutral")

        except Exception as e:
            self.logger.warning("Emotion detection failed", error=str(e))
            emotions = ["neutral"]

        return emotions

    async def _calculate_emotional_intensity(self, features: Dict[str, float]) -> float:
        """Calculate emotional intensity from features."""
        try:
            # Intensity based on energy and variation
            energy_intensity = min(1.0, features.get("rms_energy", 0) * 10)
            pitch_variation = min(1.0, abs(features.get("pitch", 200) - 200) / 200)

            return (energy_intensity + pitch_variation) / 2

        except Exception:
            return 0.5

    async def _calculate_spectral_centroid(self, audio_data: np.ndarray) -> float:
        """Calculate spectral centroid (brightness)."""
        try:
            spectrum = np.abs(np.fft.rfft(audio_data))
            frequencies = np.fft.rfftfreq(len(audio_data), 1 / 16000)

            if len(spectrum) == 0 or np.sum(spectrum) == 0:
                return 0.0

            return np.sum(frequencies * spectrum) / np.sum(spectrum)
        except:
            return 0.0

    async def _calculate_jitter(self, audio_data: np.ndarray) -> float:
        """Calculate jitter (pitch perturbation)."""
        # Simplified jitter calculation
        try:
            # This is a placeholder - real jitter calculation requires pitch tracking
            pitch_variation = np.std(audio_data) / np.mean(np.abs(audio_data))
            return min(1.0, pitch_variation)
        except:
            return 0.0

    async def _calculate_shimmer(self, audio_data: np.ndarray) -> float:
        """Calculate shimmer (amplitude perturbation)."""
        try:
            # Simplified shimmer calculation
            amplitude_variation = np.std(np.abs(audio_data)) / np.mean(
                np.abs(audio_data)
            )
            return min(1.0, amplitude_variation)
        except:
            return 0.0

    async def _analyze_engagement(
        self, conversation_id: str, segment_data: Dict[str, Any]
    ) -> EngagementMetrics:
        """Analyze group engagement and participation."""
        try:
            context = self.conversation_contexts.get(conversation_id)
            if not context:
                return EngagementMetrics(conversation_id=conversation_id)

            # Calculate per-speaker engagement
            speaker_engagement = {}
            total_segments = len(context.recent_segments)

            for speaker_id, segment_count in context.active_speakers.items():
                if total_segments > 0:
                    engagement = min(
                        1.0,
                        segment_count
                        / max(1, total_segments / len(context.active_speakers)),
                    )
                    speaker_engagement[speaker_id] = engagement

            # Calculate group engagement score
            if speaker_engagement:
                group_engagement = np.mean(list(speaker_engagement.values()))
            else:
                group_engagement = 0.0

            # Calculate participation balance
            if len(speaker_engagement) > 1:
                engagement_values = list(speaker_engagement.values())
                participation_balance = 1.0 - (
                    np.std(engagement_values) / np.mean(engagement_values)
                )
            else:
                participation_balance = 1.0

            # Calculate interaction frequency
            time_window = (datetime.utcnow() - context.start_time).total_seconds()
            if time_window > 0:
                interaction_frequency = len(context.recent_segments) / (
                    time_window / 60
                )  # per minute
            else:
                interaction_frequency = 0.0

            # Identify dominant and quiet speakers
            engagement_threshold = 0.3
            dominant_speakers = [
                speaker
                for speaker, score in speaker_engagement.items()
                if score > engagement_threshold
            ]
            quiet_speakers = [
                speaker
                for speaker, score in speaker_engagement.items()
                if score <= engagement_threshold
            ]

            return EngagementMetrics(
                conversation_id=conversation_id,
                speaker_engagement=speaker_engagement,
                group_engagement_score=group_engagement,
                participation_balance=participation_balance,
                interaction_frequency=interaction_frequency,
                dominant_speakers=dominant_speakers,
                quiet_speakers=quiet_speakers,
            )

        except Exception as e:
            self.logger.warning("Engagement analysis failed", error=str(e))
            return EngagementMetrics(conversation_id=conversation_id)

    async def _analyze_conversation_flow(
        self, conversation_id: str, segment_data: Dict[str, Any]
    ) -> ConversationFlow:
        """Analyze conversation flow and rhythm."""
        try:
            context = self.conversation_contexts.get(conversation_id)
            if not context:
                return ConversationFlow(conversation_id=conversation_id)

            # Calculate speaking durations
            speaking_duration = {}
            pause_duration = {}
            current_time = datetime.utcnow()

            for speaker_id, last_time in context.last_turn_time.items():
                if speaker_id in context.active_speakers:
                    # Calculate speaking time since last turn
                    speaking_time = (current_time - last_time).total_seconds()
                    speaking_duration[speaker_id] = speaking_time

                    # Estimate pause time (simplified)
                    if len(context.pause_events) > 0:
                        avg_pause = np.mean(
                            [p.get("duration", 0) for p in context.pause_events[-10:]]
                        )
                        pause_duration[speaker_id] = avg_pause
                    else:
                        pause_duration[speaker_id] = 0.0

            # Count interruptions
            interruption_count = {}
            for event in context.interruption_events[-50:]:  # Last 50 events
                speaker = event.get("speaker_id", "unknown")
                interruption_count[speaker] = interruption_count.get(speaker, 0) + 1

            # Calculate rhythm score
            if speaking_duration:
                speaking_times = list(speaking_duration.values())
                rhythm_score = 1.0 - (np.std(speaking_times) / np.mean(speaking_times))
            else:
                rhythm_score = 0.0

            # Calculate flow smoothness
            pause_times = [p.get("duration", 0) for p in context.pause_events[-20:]]
            if pause_times:
                flow_smoothness = 1.0 - min(1.0, np.std(pause_times) / 2.0)
            else:
                flow_smoothness = 1.0

            return ConversationFlow(
                conversation_id=conversation_id,
                speaking_duration=speaking_duration,
                pause_duration=pause_duration,
                interruption_count=interruption_count,
                rhythm_score=rhythm_score,
                flow_smoothness=flow_smoothness,
            )

        except Exception as e:
            self.logger.warning("Flow analysis failed", error=str(e))
            return ConversationFlow(conversation_id=conversation_id)

    async def _detect_highlights(
        self,
        conversation_id: str,
        segment_data: Dict[str, Any],
        analysis_results: Dict[str, Any],
    ) -> List[ConversationHighlight]:
        """Detect conversation highlights."""
        highlights = []

        try:
            sentiment = analysis_results.get("sentiment")
            engagement = analysis_results.get("engagement")

            if not sentiment or not engagement:
                return highlights

            # Check for significant sentiment changes
            if abs(sentiment.sentiment_score) > self.sentiment_threshold_high:
                highlight_type = (
                    "emotional_moment"
                    if sentiment.sentiment_score > 0
                    else "tense_moment"
                )
                highlights.append(
                    await self._create_highlight(
                        conversation_id,
                        segment_data,
                        highlight_type,
                        sentiment,
                        engagement,
                    )
                )

            # Check for high engagement moments
            if engagement.group_engagement_score > self.engagement_threshold:
                highlights.append(
                    await self._create_highlight(
                        conversation_id,
                        segment_data,
                        "high_engagement",
                        sentiment,
                        engagement,
                    )
                )

            # Check for conversation turning points
            if len(engagement.dominant_speakers) > 2:  # Multiple active speakers
                highlights.append(
                    await self._create_highlight(
                        conversation_id,
                        segment_data,
                        "lively_discussion",
                        sentiment,
                        engagement,
                    )
                )

        except Exception as e:
            self.logger.warning("Highlight detection failed", error=str(e))

        return highlights

    async def _create_highlight(
        self,
        conversation_id: str,
        segment_data: Dict[str, Any],
        highlight_type: str,
        sentiment: SentimentAnalysis,
        engagement: EngagementMetrics,
    ) -> ConversationHighlight:
        """Create a conversation highlight."""
        speaker_id = segment_data.get("speaker_id", "unknown")
        current_time = datetime.utcnow()

        # Calculate significance score
        significance = (
            abs(sentiment.sentiment_score) * 0.4
            + engagement.group_engagement_score * 0.4
            + sentiment.confidence * 0.2
        )

        # Generate description
        descriptions = {
            "emotional_moment": f"Emotional moment from {speaker_id} with sentiment {sentiment.sentiment_score:.2f}",
            "tense_moment": f"Intense moment from {speaker_id} with sentiment {sentiment.sentiment_score:.2f}",
            "high_engagement": f"High engagement moment with {len(engagement.dominant_speakers)} active speakers",
            "lively_discussion": "Lively group discussion with multiple participants",
        }

        description = descriptions.get(
            highlight_type, f"Conversation highlight: {highlight_type}"
        )

        return ConversationHighlight(
            highlight_id=f"{conversation_id}_{current_time.timestamp()}",
            conversation_id=conversation_id,
            start_time=current_time,
            end_time=current_time,  # Could be extended based on context
            highlight_type=highlight_type,
            speakers_involved=[speaker_id],
            sentiment_score=sentiment.sentiment_score,
            engagement_score=engagement.group_engagement_score,
            significance_score=significance,
            description=description,
        )

    async def _update_conversation_context(
        self,
        conversation_id: str,
        segment_data: Dict[str, Any],
        analysis_results: Dict[str, Any],
    ):
        """Update conversation context with new analysis results."""
        try:
            context = self.conversation_contexts[conversation_id]
            speaker_id = segment_data.get("speaker_id", "unknown")

            # Update active speakers
            context.active_speakers[speaker_id] = (
                context.active_speakers.get(speaker_id, 0) + 1
            )

            # Add to recent segments
            context.recent_segments.append(
                {
                    "speaker_id": speaker_id,
                    "timestamp": datetime.utcnow(),
                    "analysis": analysis_results,
                }
            )

            # Keep only recent segments within analysis window
            cutoff_time = datetime.utcnow() - self.analysis_window
            context.recent_segments = [
                s for s in context.recent_segments if s["timestamp"] > cutoff_time
            ]

            # Update sentiment history
            sentiment = analysis_results.get("sentiment")
            if sentiment:
                if speaker_id not in context.sentiment_history:
                    context.sentiment_history[speaker_id] = []
                context.sentiment_history[speaker_id].append(sentiment.sentiment_score)

                # Keep only recent history
                context.sentiment_history[speaker_id] = context.sentiment_history[
                    speaker_id
                ][-50:]

            # Update engagement history
            engagement = analysis_results.get("engagement")
            if engagement:
                context.engagement_history.append(engagement.group_engagement_score)
                context.engagement_history = context.engagement_history[-50:]

            # Update turn timing
            context.last_turn_time[speaker_id] = datetime.utcnow()

        except Exception as e:
            self.logger.warning("Context update failed", error=str(e))

    async def generate_conversation_summary(
        self, conversation_id: str
    ) -> Dict[str, Any]:
        """Generate a comprehensive conversation summary."""
        try:
            context = self.conversation_contexts.get(conversation_id)
            if not context:
                return {"error": "Conversation not found"}

            # Collect highlights
            highlights = []
            for segment in context.recent_segments:
                analysis = segment.get("analysis", {})
                highlights.extend(analysis.get("highlights", []))

            # Calculate overall metrics
            total_segments = len(context.recent_segments)
            avg_sentiment = {}
            for speaker_id, sentiments in context.sentiment_history.items():
                if sentiments:
                    avg_sentiment[speaker_id] = np.mean(sentiments)

            avg_engagement = (
                np.mean(context.engagement_history)
                if context.engagement_history
                else 0.0
            )

            # Generate summary
            summary = {
                "conversation_id": conversation_id,
                "duration_minutes": (
                    datetime.utcnow() - context.start_time
                ).total_seconds()
                / 60,
                "total_segments": total_segments,
                "active_speakers": len(context.active_speakers),
                "average_engagement": avg_engagement,
                "speaker_sentiment": avg_sentiment,
                "highlight_count": len(highlights),
                "top_highlights": sorted(
                    highlights, key=lambda x: x.significance_score, reverse=True
                )[:5],
                "generated_at": datetime.utcnow().isoformat(),
            }

            return summary

        except Exception as e:
            self.logger.error("Summary generation failed", error=str(e))
            return {"error": str(e)}

    async def cleanup_conversation(self, conversation_id: str):
        """Clean up conversation context."""
        if conversation_id in self.conversation_contexts:
            del self.conversation_contexts[conversation_id]
            self.logger.info("Cleaned up conversation context", conversation_id=conversation_id)

    async def get_conversation_stats(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation statistics."""
        if conversation_id not in self.conversation_contexts:
            return {}

        context = self.conversation_contexts[conversation_id]

        return {
            "conversation_id": conversation_id,
            "active_speakers": len(context.active_speakers),
            "total_segments": len(context.recent_segments),
            "sentiment_history_length": sum(
                len(h) for h in context.sentiment_history.values()
            ),
            "engagement_history_length": len(context.engagement_history),
            "interruption_count": len(context.interruption_events),
            "pause_count": len(context.pause_events),
            "duration_minutes": (datetime.utcnow() - context.start_time).total_seconds()
            / 60,
        }


# Global conversation intelligence engine instance
conversation_intelligence_engine = ConversationIntelligenceEngine()
