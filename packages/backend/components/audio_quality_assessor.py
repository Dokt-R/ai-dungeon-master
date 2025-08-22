"""
Audio Quality Assessor Component for AI Dungeon Master.

This module provides comprehensive audio quality assessment and monitoring
to ensure high-quality voice interactions and meet user expectations.

Features:
- Audio quality assessment and validation
- User feedback collection and analysis
- Quality improvement recommendations
- Provider performance comparison
- Quality standards enforcement
- Real-time quality monitoring
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

from packages.shared.models import (
    AudioQualityMetrics, AudioStreamInfo, VoiceLatencyMetrics,
    PerformanceReport
)
from packages.backend.components.observability_service import observability_service
from packages.backend.components.audio_processor import audio_processor
from packages.backend.components.tts_service import tts_service
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


class QualityStandard(Enum):
    """Audio quality standards."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNUSABLE = "unusable"


@dataclass
class QualityThreshold:
    """Quality assessment thresholds."""

    excellent_threshold: float = 0.9
    good_threshold: float = 0.8
    acceptable_threshold: float = 0.7
    poor_threshold: float = 0.5

    # Specific metric thresholds
    min_transcription_accuracy: float = 0.85
    min_voice_clarity: float = 0.8
    max_artifacts_ratio: float = 0.1
    max_noise_level: float = 0.15
    min_signal_to_noise_ratio: float = 15.0  # dB


@dataclass
class UserFeedback:
    """User feedback on audio quality."""

    session_id: str
    user_id: str
    rating: float  # 1.0 to 5.0
    categories: List[str]  # e.g., ["clarity", "speed", "naturalness"]
    comments: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityRecommendation:
    """Quality improvement recommendation."""

    recommendation_id: str
    category: str
    severity: str
    description: str
    action_required: str
    estimated_improvement: float
    implementation_complexity: str
    created_at: datetime = field(default_factory=datetime.utcnow)


class AudioQualityAssessor:
    """
    Audio quality assessment and monitoring service.

    Features:
    - Comprehensive quality assessment
    - User feedback analysis
    - Quality improvement recommendations
    - Provider performance comparison
    - Standards enforcement
    - Real-time monitoring
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = get_logger(f"{__name__}.AudioQualityAssessor")

        # Quality standards and thresholds
        self.thresholds = QualityThreshold()
        self.quality_standards = self._define_quality_standards()

        # Assessment results storage
        self.quality_assessments: Dict[str, List[AudioQualityMetrics]] = {}
        self.user_feedback: List[UserFeedback] = []
        self.recommendations: List[QualityRecommendation] = []

        # Provider performance tracking
        self.provider_performance: Dict[str, Dict[str, Any]] = {}

        # Assessment configuration
        self.enable_real_time_assessment = True
        self.feedback_collection_enabled = True
        self.automatic_recommendations = True

        # Assessment intervals
        self.assessment_interval = 300  # 5 minutes
        self.reporting_interval = 3600  # 1 hour

        # Start background assessment
        self._assessment_task: Optional[asyncio.Task] = None

    def _define_quality_standards(self) -> Dict[str, Dict[str, Any]]:
        """Define quality standards for different use cases."""
        return {
            "voice_interaction": {
                "description": "Real-time voice interaction quality",
                "min_accuracy": 0.85,
                "min_clarity": 0.8,
                "max_noise": 0.1,
                "min_snr": 20.0,
                "max_artifacts": 0.05
            },
            "narration": {
                "description": "Story narration quality",
                "min_accuracy": 0.9,
                "min_clarity": 0.85,
                "max_noise": 0.08,
                "min_snr": 25.0,
                "max_artifacts": 0.03
            },
            "background_audio": {
                "description": "Background audio quality",
                "min_accuracy": 0.75,
                "min_clarity": 0.7,
                "max_noise": 0.2,
                "min_snr": 15.0,
                "max_artifacts": 0.15
            }
        }

    async def start_assessment(self) -> None:
        """Start the quality assessment service."""
        if self._assessment_task is None:
            self._assessment_task = asyncio.create_task(self._assessment_loop())
            self.logger.info("audio_quality_assessment_started")

    async def stop_assessment(self) -> None:
        """Stop the quality assessment service."""
        if self._assessment_task:
            self._assessment_task.cancel()
            try:
                await self._assessment_task
            except asyncio.CancelledError:
                pass
            self._assessment_task = None
            self.logger.info("audio_quality_assessment_stopped")

    async def _assessment_loop(self) -> None:
        """Main assessment loop."""
        while self.enable_real_time_assessment:
            try:
                await asyncio.sleep(self.assessment_interval)

                # Generate periodic quality report
                await self._generate_quality_report()

                # Update recommendations
                if self.automatic_recommendations:
                    await self._update_recommendations()

            except Exception as e:
                self.logger.error("assessment_loop_error", error=str(e))

    async def assess_audio_quality(
        self,
        session_id: str,
        audio_data: bytes,
        audio_format: str,
        sample_rate: int,
        channels: int,
        context: Dict[str, Any] = None
    ) -> AudioQualityMetrics:
        """
        Assess the quality of audio data.

        Args:
            session_id: Voice session identifier
            audio_data: Audio data to assess
            audio_format: Audio format
            sample_rate: Sample rate
            channels: Number of channels
            context: Assessment context

        Returns:
            AudioQualityMetrics with assessment results
        """
        start_time = time.time()

        try:
            with observability_service.trace_operation(
                operation_name="audio_quality_assessment",
                session_id=session_id,
                audio_format=audio_format
            ) as trace_id:

                # Basic audio properties
                audio_info = self._analyze_audio_properties(audio_data, sample_rate, channels)

                # Technical quality metrics
                technical_metrics = self._calculate_technical_metrics(audio_data, sample_rate)

                # Content-based assessment
                content_metrics = await self._assess_content_quality(audio_data, audio_format, context)

                # Overall quality score
                overall_score = self._calculate_overall_score(
                    audio_info, technical_metrics, content_metrics
                )

                # Determine quality standard
                quality_standard = self._determine_quality_standard(overall_score)

                # Create assessment result
                assessment = AudioQualityMetrics(
                    session_id=session_id,
                    transcription_accuracy=content_metrics.get('accuracy'),
                    voice_clarity=content_metrics.get('clarity'),
                    audio_artifacts=technical_metrics.get('artifacts_ratio', 0),
                    noise_level=technical_metrics.get('noise_level', 0),
                    signal_to_noise_ratio=technical_metrics.get('snr'),
                    audio_bitrate=self._estimate_bitrate(audio_data, sample_rate, channels),
                    sample_rate=sample_rate,
                    audio_format=audio_format,
                    quality_score=overall_score
                )

                # Store assessment
                if session_id not in self.quality_assessments:
                    self.quality_assessments[session_id] = []
                self.quality_assessments[session_id].append(assessment)

                processing_time = time.time() - start_time

                self.logger.info(
                    "audio_quality_assessed",
                    session_id=session_id,
                    quality_score=overall_score,
                    quality_standard=quality_standard.value,
                    processing_time=processing_time,
                    trace_id=trace_id
                )

                return assessment

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(
                "audio_quality_assessment_failed",
                session_id=session_id,
                processing_time=processing_time,
                error=str(e)
            )

            # Return minimal assessment on error
            return AudioQualityMetrics(
                session_id=session_id,
                quality_score=0.0
            )

    def _analyze_audio_properties(
        self,
        audio_data: bytes,
        sample_rate: int,
        channels: int
    ) -> Dict[str, Any]:
        """Analyze basic audio properties."""
        try:
            # Convert to numpy array for analysis
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            audio_array = audio_array / 32768.0  # Normalize to [-1, 1]

            # Calculate RMS and peak levels
            rms_level = np.sqrt(np.mean(audio_array ** 2))
            peak_level = np.max(np.abs(audio_array))

            # Calculate duration
            duration = len(audio_array) / sample_rate

            # Estimate dynamic range
            if rms_level > 0:
                dynamic_range = 20 * np.log10(peak_level / rms_level)
            else:
                dynamic_range = 0.0

            return {
                'rms_level': rms_level,
                'peak_level': peak_level,
                'duration': duration,
                'dynamic_range': dynamic_range,
                'channels': channels,
                'sample_rate': sample_rate
            }

        except Exception as e:
            self.logger.warning("audio_properties_analysis_failed", error=str(e))
            return {}

    def _calculate_technical_metrics(self, audio_data: bytes, sample_rate: int) -> Dict[str, Any]:
        """Calculate technical audio quality metrics."""
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            audio_array = audio_array / 32768.0

            # Signal-to-noise ratio estimation
            signal_power = np.var(audio_array)
            noise_power = np.var(audio_array - np.convolve(audio_array, [1/5]*5, mode='same'))

            if noise_power > 0:
                snr = 10 * np.log10(signal_power / noise_power)
            else:
                snr = 60.0  # High SNR if no noise detected

            # Noise level estimation
            noise_level = np.sqrt(noise_power)

            # Artifact detection (simple clipping detection)
            clipped_samples = np.sum(np.abs(audio_array) >= 0.99)
            artifacts_ratio = clipped_samples / len(audio_array)

            # Zero crossing rate (voice activity indicator)
            zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_array)))) / 2
            zero_crossing_rate = zero_crossings / len(audio_array)

            return {
                'snr': snr,
                'noise_level': noise_level,
                'artifacts_ratio': artifacts_ratio,
                'zero_crossing_rate': zero_crossing_rate
            }

        except Exception as e:
            self.logger.warning("technical_metrics_calculation_failed", error=str(e))
            return {}

    async def _assess_content_quality(
        self,
        audio_data: bytes,
        audio_format: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Assess content-based quality (placeholder for advanced analysis)."""
        try:
            # In a real implementation, this would use:
            # - Machine learning models for clarity assessment
            # - Speech analysis for naturalness scoring
            # - Transcription accuracy comparison
            # - Voice quality models

            # For now, return mock assessments based on technical metrics
            technical_metrics = self._calculate_technical_metrics(audio_data, 16000)

            # Estimate clarity based on SNR and noise
            snr = technical_metrics.get('snr', 20.0)
            noise_level = technical_metrics.get('noise_level', 0.1)
            artifacts = technical_metrics.get('artifacts_ratio', 0.05)

            # Simple clarity estimation
            clarity = max(0.0, min(1.0, (snr / 40.0) * (1.0 - noise_level) * (1.0 - artifacts)))

            # Transcription accuracy would come from actual STT comparison
            # For now, use clarity as proxy
            accuracy = clarity * 0.9  # Slightly lower as proxy

            return {
                'clarity': clarity,
                'accuracy': accuracy,
                'content_assessed': True
            }

        except Exception as e:
            self.logger.warning("content_quality_assessment_failed", error=str(e))
            return {}

    def _calculate_overall_score(
        self,
        audio_info: Dict[str, Any],
        technical_metrics: Dict[str, Any],
        content_metrics: Dict[str, Any]
    ) -> float:
        """Calculate overall quality score."""
        try:
            scores = []

            # Technical quality score (40% weight)
            snr = technical_metrics.get('snr', 20.0)
            noise_level = technical_metrics.get('noise_level', 0.1)
            artifacts = technical_metrics.get('artifacts_ratio', 0.05)

            technical_score = (
                min(1.0, snr / 40.0) * 0.5 +  # SNR contribution
                (1.0 - noise_level) * 0.3 +     # Noise contribution
                (1.0 - artifacts) * 0.2         # Artifacts contribution
            )
            scores.append(('technical', technical_score, 0.4))

            # Content quality score (35% weight)
            clarity = content_metrics.get('clarity', 0.8)
            accuracy = content_metrics.get('accuracy', clarity * 0.9)

            content_score = (clarity + accuracy) / 2.0
            scores.append(('content', content_score, 0.35))

            # Audio properties score (25% weight)
            rms_level = audio_info.get('rms_level', 0.5)
            peak_level = audio_info.get('peak_level', 0.8)
            dynamic_range = audio_info.get('dynamic_range', 20.0)

            properties_score = (
                min(1.0, rms_level * 2.0) * 0.4 +      # RMS level
                min(1.0, peak_level * 1.2) * 0.3 +     # Peak level
                min(1.0, dynamic_range / 30.0) * 0.3   # Dynamic range
            )
            scores.append(('properties', properties_score, 0.25))

            # Calculate weighted average
            overall_score = sum(score * weight for _, score, weight in scores)

            return max(0.0, min(1.0, overall_score))

        except Exception as e:
            self.logger.error("overall_score_calculation_failed", error=str(e))
            return 0.5  # Neutral score on error

    def _determine_quality_standard(self, score: float) -> QualityStandard:
        """Determine quality standard based on score."""
        thresholds = self.thresholds

        if score >= thresholds.excellent_threshold:
            return QualityStandard.EXCELLENT
        elif score >= thresholds.good_threshold:
            return QualityStandard.GOOD
        elif score >= thresholds.acceptable_threshold:
            return QualityStandard.ACCEPTABLE
        elif score >= thresholds.poor_threshold:
            return QualityStandard.POOR
        else:
            return QualityStandard.UNUSABLE

    def _estimate_bitrate(self, audio_data: bytes, sample_rate: int, channels: int) -> int:
        """Estimate audio bitrate."""
        duration = len(audio_data) / (sample_rate * channels * 2)  # 16-bit samples
        if duration > 0:
            return int((len(audio_data) * 8) / duration)  # bits per second
        return 0

    def collect_user_feedback(
        self,
        session_id: str,
        user_id: str,
        rating: float,
        categories: List[str],
        comments: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Collect user feedback on audio quality.

        Args:
            session_id: Voice session identifier
            user_id: User identifier
            rating: Quality rating (1.0 to 5.0)
            categories: Feedback categories
            comments: Optional comments
            metadata: Additional metadata
        """
        try:
            feedback = UserFeedback(
                session_id=session_id,
                user_id=user_id,
                rating=rating,
                categories=categories,
                comments=comments,
                metadata=metadata or {}
            )

            self.user_feedback.append(feedback)

            # Log feedback for analysis
            self.logger.info(
                "user_feedback_collected",
                session_id=session_id,
                user_id=user_id,
                rating=rating,
                categories=categories,
                has_comments=comments is not None
            )

            # Check if immediate action is needed
            if rating <= 2.0:  # Very poor feedback
                self._handle_poor_feedback(feedback)

        except Exception as e:
            self.logger.error("user_feedback_collection_failed", error=str(e))

    async def generate_quality_report(
        self,
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """Generate comprehensive quality report."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)

            # Filter recent assessments
            recent_assessments = []
            for assessments in self.quality_assessments.values():
                recent = [a for a in assessments if a.timestamp >= cutoff_time]
                recent_assessments.extend(recent)

            # Filter recent feedback
            recent_feedback = [f for f in self.user_feedback if f.timestamp >= cutoff_time]

            # Calculate statistics
            if recent_assessments:
                avg_quality_score = np.mean([a.quality_score for a in recent_assessments if a.quality_score])
                avg_clarity = np.mean([a.voice_clarity for a in recent_assessments if a.voice_clarity])
                avg_accuracy = np.mean([a.transcription_accuracy for a in recent_assessments if a.transcription_accuracy])
                avg_noise = np.mean([a.noise_level for a in recent_assessments if a.noise_level])
                avg_artifacts = np.mean([a.audio_artifacts for a in recent_assessments if a.audio_artifacts])
            else:
                avg_quality_score = avg_clarity = avg_accuracy = avg_noise = avg_artifacts = 0.0

            if recent_feedback:
                avg_user_rating = np.mean([f.rating for f in recent_feedback])
                feedback_count = len(recent_feedback)
            else:
                avg_user_rating = 0.0
                feedback_count = 0

            # Generate recommendations
            recommendations = await self._generate_quality_recommendations(
                recent_assessments, recent_feedback
            )

            report = {
                "report_period_hours": time_range_hours,
                "assessment_count": len(recent_assessments),
                "feedback_count": feedback_count,
                "average_quality_score": avg_quality_score,
                "average_clarity": avg_clarity,
                "average_accuracy": avg_accuracy,
                "average_noise_level": avg_noise,
                "average_artifacts_ratio": avg_artifacts,
                "average_user_rating": avg_user_rating,
                "recommendations": [r.__dict__ for r in recommendations],
                "generated_at": datetime.utcnow().isoformat()
            }

            self.logger.info(
                "quality_report_generated",
                assessments=len(recent_assessments),
                feedback=feedback_count,
                avg_score=avg_quality_score,
                avg_rating=avg_user_rating
            )

            return report

        except Exception as e:
            self.logger.error("quality_report_generation_failed", error=str(e))
            return {}

    async def _generate_quality_recommendations(
        self,
        assessments: List[AudioQualityMetrics],
        feedback: List[UserFeedback]
    ) -> List[QualityRecommendation]:
        """Generate quality improvement recommendations."""
        recommendations = []

        try:
            if not assessments:
                return recommendations

            # Analyze quality issues
            avg_score = np.mean([a.quality_score for a in assessments if a.quality_score])

            if avg_score < self.thresholds.good_threshold:
                recommendations.append(QualityRecommendation(
                    recommendation_id=f"rec_{int(time.time())}_quality_improvement",
                    category="overall_quality",
                    severity="high" if avg_score < self.thresholds.poor_threshold else "medium",
                    description=".2f",
                    action_required="Implement audio enhancement pipeline and quality monitoring",
                    estimated_improvement=0.2,
                    implementation_complexity="medium"
                ))

            # Check noise levels
            high_noise_sessions = [a for a in assessments if a.noise_level and a.noise_level > 0.2]
            if len(high_noise_sessions) > len(assessments) * 0.3:  # More than 30%
                recommendations.append(QualityRecommendation(
                    recommendation_id=f"rec_{int(time.time())}_noise_reduction",
                    category="noise_reduction",
                    severity="medium",
                    description=f"High noise detected in {len(high_noise_sessions)} sessions",
                    action_required="Implement noise reduction algorithms and echo cancellation",
                    estimated_improvement=0.15,
                    implementation_complexity="high"
                ))

            # Check user feedback
            if feedback:
                low_ratings = [f for f in feedback if f.rating <= 3.0]
                if len(low_ratings) > len(feedback) * 0.4:  # More than 40% low ratings
                    recommendations.append(QualityRecommendation(
                        recommendation_id=f"rec_{int(time.time())}_user_feedback",
                        category="user_experience",
                        severity="high",
                        description=f"{len(low_ratings)} users reported poor quality",
                        action_required="Address user feedback and implement quality monitoring",
                        estimated_improvement=0.25,
                        implementation_complexity="medium"
                    ))

        except Exception as e:
            self.logger.error("recommendation_generation_failed", error=str(e))

        return recommendations

    def _handle_poor_feedback(self, feedback: UserFeedback) -> None:
        """Handle poor user feedback."""
        try:
            self.logger.warning(
                "poor_user_feedback_received",
                session_id=feedback.session_id,
                user_id=feedback.user_id,
                rating=feedback.rating,
                categories=feedback.categories,
                comments=feedback.comments
            )

            # In a real implementation, this could trigger:
            # - Immediate quality assessment
            # - Alert notifications
            # - Session monitoring
            # - Provider switching

        except Exception as e:
            self.logger.error("poor_feedback_handling_failed", error=str(e))

    async def _generate_quality_report(self) -> None:
        """Generate periodic quality report."""
        try:
            report = await self.generate_quality_report()

            # Log key metrics
            self.logger.info(
                "periodic_quality_metrics",
                avg_quality_score=report.get("average_quality_score", 0),
                avg_user_rating=report.get("average_user_rating", 0),
                assessment_count=report.get("assessment_count", 0),
                feedback_count=report.get("feedback_count", 0)
            )

        except Exception as e:
            self.logger.error("periodic_quality_report_failed", error=str(e))

    async def _update_recommendations(self) -> None:
        """Update quality recommendations."""
        try:
            # Get recent data
            recent_assessments = []
            for assessments in self.quality_assessments.values():
                recent = [a for a in assessments if a.timestamp >= datetime.utcnow() - timedelta(hours=1)]
                recent_assessments.extend(recent)

            recent_feedback = [f for f in self.user_feedback if f.timestamp >= datetime.utcnow() - timedelta(hours=1)]

            # Generate new recommendations
            new_recommendations = await self._generate_quality_recommendations(
                recent_assessments, recent_feedback
            )

            # Update recommendations (keep recent ones)
            self.recommendations = new_recommendations

        except Exception as e:
            self.logger.error("recommendation_update_failed", error=str(e))

    def get_quality_assessments(self, session_id: Optional[str] = None) -> List[AudioQualityMetrics]:
        """Get quality assessments for a session or all sessions."""
        if session_id:
            return self.quality_assessments.get(session_id, [])
        else:
            all_assessments = []
            for assessments in self.quality_assessments.values():
                all_assessments.extend(assessments)
            return all_assessments

    def get_user_feedback(self, session_id: Optional[str] = None) -> List[UserFeedback]:
        """Get user feedback for a session or all sessions."""
        if session_id:
            return [f for f in self.user_feedback if f.session_id == session_id]
        return self.user_feedback.copy()

    def get_recommendations(self) -> List[QualityRecommendation]:
        """Get current quality recommendations."""
        return self.recommendations.copy()

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the quality assessor."""
        recent_assessments = []
        for assessments in self.quality_assessments.values():
            recent = [a for a in assessments if a.timestamp >= datetime.utcnow() - timedelta(minutes=30)]
            recent_assessments.extend(recent)

        avg_quality = 0.0
        if recent_assessments:
            valid_scores = [a.quality_score for a in recent_assessments if a.quality_score is not None]
            if valid_scores:
                avg_quality = np.mean(valid_scores)

        return {
            "status": "healthy",
            "total_assessments": sum(len(assessments) for assessments in self.quality_assessments.values()),
            "recent_assessments_30min": len(recent_assessments),
            "total_feedback": len(self.user_feedback),
            "recent_feedback_30min": len([f for f in self.user_feedback if f.timestamp >= datetime.utcnow() - timedelta(minutes=30)]),
            "average_quality_score": avg_quality,
            "recommendations_count": len(self.recommendations),
            "real_time_assessment_enabled": self.enable_real_time_assessment,
            "feedback_collection_enabled": self.feedback_collection_enabled
        }


# Global audio quality assessor instance
audio_quality_assessor = AudioQualityAssessor()