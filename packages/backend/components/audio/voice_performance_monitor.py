"""
Voice Performance Monitor Component for AI Dungeon Master.

This module provides comprehensive latency monitoring and performance tracking for voice interactions,
ensuring the system meets the 4-second NFR1 latency target.

Features:
- Real-time latency tracking for voice interactions
- Performance metrics collection and analysis
- Early warning system for latency issues
- Performance dashboards and reporting
- Optimization recommendations
- Alert generation and management
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger
from packages.shared.models import (
    PerformanceAlert,
    PerformanceReport,
    VoiceLatencyMetrics,
)

logger = get_logger(__name__)


@dataclass
class LatencyThreshold:
    """Latency threshold configuration."""

    warning_threshold: float = 2.0  # seconds
    critical_threshold: float = 3.5  # seconds
    target_threshold: float = 4.0  # NFR1 target
    max_threshold: float = 6.0  # maximum acceptable

    def get_severity(self, latency: float) -> str:
        """Get severity level for given latency."""
        if latency >= self.max_threshold:
            return "critical"
        elif latency >= self.critical_threshold:
            return "high"
        elif latency >= self.warning_threshold:
            return "medium"
        else:
            return "low"


@dataclass
class PerformanceMetricsBuffer:
    """Circular buffer for performance metrics."""

    max_size: int = 1000
    _buffer: deque = field(default_factory=lambda: deque(maxlen=1000))

    def add_metric(self, metric: VoiceLatencyMetrics) -> None:
        """Add a metric to the buffer."""
        self._buffer.append(metric)

    def get_recent_metrics(self, seconds: int = 300) -> List[VoiceLatencyMetrics]:
        """Get metrics from the last N seconds."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=seconds)
        return [m for m in self._buffer if m.user_speech_start >= cutoff_time]

    def get_all_metrics(self) -> List[VoiceLatencyMetrics]:
        """Get all metrics in buffer."""
        return list(self._buffer)

    def clear(self) -> None:
        """Clear the metrics buffer."""
        self._buffer.clear()


class VoicePerformanceMonitor:
    """
    Monitor and track voice interaction performance.

    Features:
    - Real-time latency tracking and monitoring
    - Performance metrics collection and analysis
    - Early warning system for latency issues
    - Performance optimization recommendations
    - Alert generation and management
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = get_logger(f"{__name__}.VoicePerformanceMonitor")

        # Latency thresholds
        self.thresholds = LatencyThreshold(
            warning_threshold=self.config.get("warning_threshold", 2.0),
            critical_threshold=self.config.get("critical_threshold", 3.5),
            target_threshold=self.config.get("target_threshold", 4.0),
            max_threshold=self.config.get("max_threshold", 6.0),
        )

        # Metrics storage
        self.metrics_buffer = PerformanceMetricsBuffer(
            max_size=self.config.get("metrics_buffer_size", 1000)
        )

        # Active sessions tracking
        self.active_sessions: Dict[str, VoiceLatencyMetrics] = {}

        # Alert tracking
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.alert_history: List[PerformanceAlert] = []

        # Performance statistics
        self.performance_stats = {
            "total_sessions": 0,
            "sessions_meeting_target": 0,
            "average_latency": 0.0,
            "p95_latency": 0.0,
            "p99_latency": 0.0,
            "alerts_generated": 0,
            "critical_alerts": 0,
        }

        # Monitoring configuration
        self.monitoring_enabled = True
        self.alerting_enabled = True
        self.reporting_interval = self.config.get(
            "reporting_interval", 300
        )  # 5 minutes

        # Start background monitoring
        self._monitoring_task: Optional[asyncio.Task] = None

    async def start_monitoring(self) -> None:
        """Start the performance monitoring system."""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.logger.info("voice_performance_monitoring_started")

    async def stop_monitoring(self) -> None:
        """Stop the performance monitoring system."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            self.logger.info("voice_performance_monitoring_stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for periodic tasks."""
        while self.monitoring_enabled:
            try:
                await asyncio.sleep(self.reporting_interval)
                await self._generate_periodic_report()
                await self._cleanup_expired_alerts()
            except Exception as e:
                self.logger.error("monitoring_loop_error", error=str(e))

    def start_voice_interaction(
        self, session_id: str, correlation_id: Optional[str] = None
    ) -> VoiceLatencyMetrics:
        """
        Start tracking a voice interaction.

        Args:
            session_id: Voice session identifier
            correlation_id: Correlation ID for tracing

        Returns:
            VoiceLatencyMetrics instance for tracking
        """
        start_time = datetime.utcnow()

        metrics = VoiceLatencyMetrics(
            session_id=session_id,
            user_speech_start=start_time,
            correlation_id=correlation_id,
            metadata={
                "monitoring_start": start_time.isoformat(),
                "monitoring_enabled": self.monitoring_enabled,
            },
        )

        self.active_sessions[session_id] = metrics
        self.performance_stats["total_sessions"] += 1

        with observability_service.trace_operation(
            operation_name="voice_interaction_started",
            session_id=session_id,
            correlation_id=correlation_id,
        ) as trace_id:
            self.logger.info(
                "voice_interaction_started",
                session_id=session_id,
                correlation_id=correlation_id,
                trace_id=trace_id,
                start_time=start_time.isoformat(),
            )

        return metrics

    def update_latency_stage(
        self, session_id: str, stage: str, correlation_id: Optional[str] = None
    ) -> Optional[VoiceLatencyMetrics]:
        """
        Update the current processing stage for latency tracking.

        Args:
            session_id: Voice session identifier
            stage: Processing stage name
            correlation_id: Correlation ID for tracing

        Returns:
            Updated metrics or None if session not found
        """
        if session_id not in self.active_sessions:
            self.logger.warning(
                "session_not_found_for_stage_update",
                session_id=session_id,
                stage=stage,
                correlation_id=correlation_id,
            )
            return None

        metrics = self.active_sessions[session_id]
        current_time = datetime.utcnow()

        # Update stage-specific timestamps
        stage_mapping = {
            "stt_complete": "transcription_complete",
            "ai_processing_start": "ai_processing_start",
            "ai_response_complete": "ai_response_complete",
            "tts_complete": "tts_generation_complete",
            "audio_playback_start": "audio_playback_start",
        }

        if stage in stage_mapping:
            setattr(metrics, stage_mapping[stage], current_time)

        metrics.processing_stage = stage

        # Calculate stage-specific latencies
        self._calculate_stage_latencies(metrics)

        # Check for latency alerts
        if self.alerting_enabled:
            self._check_latency_alerts(metrics, correlation_id)

        with observability_service.trace_operation(
            operation_name="voice_interaction_stage_updated",
            session_id=session_id,
            stage=stage,
            correlation_id=correlation_id,
        ) as trace_id:
            self.logger.debug(
                "voice_interaction_stage_updated",
                session_id=session_id,
                stage=stage,
                correlation_id=correlation_id,
                trace_id=trace_id,
                current_time=current_time.isoformat(),
            )

        return metrics

    def complete_voice_interaction(
        self, session_id: str, correlation_id: Optional[str] = None
    ) -> Optional[VoiceLatencyMetrics]:
        """
        Complete tracking of a voice interaction.

        Args:
            session_id: Voice session identifier
            correlation_id: Correlation ID for tracing

        Returns:
            Completed metrics or None if session not found
        """
        if session_id not in self.active_sessions:
            self.logger.warning(
                "session_not_found_for_completion",
                session_id=session_id,
                correlation_id=correlation_id,
            )
            return None

        metrics = self.active_sessions.pop(session_id)
        current_time = datetime.utcnow()

        # Set final timestamps
        metrics.audio_playback_start = current_time
        metrics.processing_stage = "completed"

        # Calculate final latencies
        self._calculate_final_latencies(metrics)

        # Store in buffer for analysis
        self.metrics_buffer.add_metric(metrics)

        # Update performance statistics
        self._update_performance_stats(metrics)

        # Check final latency against targets
        if metrics.total_latency is not None:
            if metrics.total_latency <= self.thresholds.target_threshold:
                self.performance_stats["sessions_meeting_target"] += 1

        with observability_service.trace_operation(
            operation_name="voice_interaction_completed",
            session_id=session_id,
            total_latency=metrics.total_latency,
            correlation_id=correlation_id,
        ) as trace_id:
            self.logger.info(
                "voice_interaction_completed",
                session_id=session_id,
                correlation_id=correlation_id,
                trace_id=trace_id,
                total_latency=metrics.total_latency,
                stt_latency=metrics.stt_latency,
                ai_latency=metrics.ai_latency,
                tts_latency=metrics.tts_latency,
                meets_target=metrics.total_latency <= self.thresholds.target_threshold
                if metrics.total_latency
                else None,
            )

        return metrics

    def _calculate_stage_latencies(self, metrics: VoiceLatencyMetrics) -> None:
        """Calculate stage-specific latencies."""
        start_time = metrics.user_speech_start

        if metrics.transcription_complete:
            metrics.stt_latency = (
                metrics.transcription_complete - start_time
            ).total_seconds()

        if metrics.ai_response_complete and metrics.ai_processing_start:
            metrics.ai_latency = (
                metrics.ai_response_complete - metrics.ai_processing_start
            ).total_seconds()

        if metrics.tts_generation_complete and metrics.ai_response_complete:
            metrics.tts_latency = (
                metrics.tts_generation_complete - metrics.ai_response_complete
            ).total_seconds()

        if metrics.audio_playback_start and metrics.tts_generation_complete:
            metrics.audio_delivery_latency = (
                metrics.audio_playback_start - metrics.tts_generation_complete
            ).total_seconds()

    def _calculate_final_latencies(self, metrics: VoiceLatencyMetrics) -> None:
        """Calculate final total latency."""
        if metrics.audio_playback_start:
            metrics.total_latency = (
                metrics.audio_playback_start - metrics.user_speech_start
            ).total_seconds()

            # Estimate network latency (rough approximation)
            if metrics.stt_latency and metrics.tts_latency and metrics.ai_latency:
                processing_latency = (
                    metrics.stt_latency + metrics.ai_latency + metrics.tts_latency
                )
                metrics.network_latency = max(
                    0, metrics.total_latency - processing_latency
                )

    def _check_latency_alerts(
        self, metrics: VoiceLatencyMetrics, correlation_id: Optional[str] = None
    ) -> None:
        """Check for latency threshold violations and generate alerts."""
        if not metrics.total_latency:
            return

        severity = self.thresholds.get_severity(metrics.total_latency)

        if severity in ["medium", "high", "critical"]:
            alert = PerformanceAlert(
                alert_id=f"latency_{metrics.session_id}_{int(time.time())}",
                alert_type="latency",
                severity=severity,
                threshold=self.thresholds.target_threshold,
                current_value=metrics.total_latency,
                session_id=metrics.session_id,
                message=self._generate_latency_alert_message(metrics, severity),
            )

            self.active_alerts[alert.alert_id] = alert
            self.alert_history.append(alert)
            self.performance_stats["alerts_generated"] += 1

            if severity == "critical":
                self.performance_stats["critical_alerts"] += 1

            self.logger.warning(
                "latency_alert_generated",
                alert_id=alert.alert_id,
                session_id=metrics.session_id,
                severity=severity,
                total_latency=metrics.total_latency,
                threshold=self.thresholds.target_threshold,
                correlation_id=correlation_id,
            )

    def _generate_latency_alert_message(
        self, metrics: VoiceLatencyMetrics, severity: str
    ) -> str:
        """Generate alert message for latency violations."""
        latency = metrics.total_latency or 0
        target = self.thresholds.target_threshold

        messages = {"medium": ".2f", "high": ".2f", "critical": ".2f"}

        return messages.get(
            severity, f"High latency detected: {latency:.2f}s (target: {target}s)"
        )

    def _update_performance_stats(self, metrics: VoiceLatencyMetrics) -> None:
        """Update rolling performance statistics."""
        if not metrics.total_latency:
            return

        # Update average latency (simple moving average)
        total_sessions = self.performance_stats["total_sessions"]
        current_avg = self.performance_stats["average_latency"]

        self.performance_stats["average_latency"] = (
            (current_avg * (total_sessions - 1)) + metrics.total_latency
        ) / total_sessions

        # Update percentile tracking (simplified)
        recent_metrics = self.metrics_buffer.get_recent_metrics(3600)  # Last hour
        if recent_metrics:
            latencies = [m.total_latency for m in recent_metrics if m.total_latency]
            if latencies:
                latencies.sort()
                self.performance_stats["p95_latency"] = latencies[
                    int(len(latencies) * 0.95)
                ]
                self.performance_stats["p99_latency"] = latencies[
                    int(len(latencies) * 0.99)
                ]

    async def generate_performance_report(
        self, time_range_seconds: int = 3600
    ) -> PerformanceReport:
        """Generate a performance report for the specified time range."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(seconds=time_range_seconds)

        # Get metrics for time range
        recent_metrics = [
            m
            for m in self.metrics_buffer.get_all_metrics()
            if start_time <= m.user_speech_start <= end_time
        ]

        # Calculate metrics
        total_sessions = len(recent_metrics)
        completed_sessions = [m for m in recent_metrics if m.total_latency is not None]

        if completed_sessions:
            latencies = [m.total_latency for m in completed_sessions]
            average_latency = sum(latencies) / len(latencies)
            latencies.sort()

            p95_latency = latencies[int(len(latencies) * 0.95)] if latencies else None
            p99_latency = latencies[int(len(latencies) * 0.99)] if latencies else None

            sessions_meeting_target = len(
                [
                    m
                    for m in completed_sessions
                    if m.total_latency <= self.thresholds.target_threshold
                ]
            )
        else:
            average_latency = p95_latency = p99_latency = None
            sessions_meeting_target = 0

        # Generate recommendations
        recommendations = self._generate_performance_recommendations(
            recent_metrics, average_latency or 0
        )

        report = PerformanceReport(
            report_id=f"perf_report_{int(time.time())}",
            time_range_start=start_time,
            time_range_end=end_time,
            total_voice_sessions=total_sessions,
            average_latency=average_latency,
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            sessions_meeting_latency_target=sessions_meeting_target,
            recommendations=recommendations,
        )

        self.logger.info(
            "performance_report_generated",
            report_id=report.report_id,
            time_range_seconds=time_range_seconds,
            total_sessions=total_sessions,
            average_latency=average_latency,
            sessions_meeting_target=sessions_meeting_target,
        )

        return report

    def _generate_performance_recommendations(
        self, metrics: List[VoiceLatencyMetrics], average_latency: float
    ) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []

        if average_latency > self.thresholds.target_threshold:
            recommendations.append(".2f")

        if average_latency > self.thresholds.critical_threshold:
            recommendations.append("Consider implementing audio streaming optimization")
            recommendations.append("Review AI processing pipeline for bottlenecks")
            recommendations.append("Optimize TTS provider selection and caching")

        # Check stage-specific latencies
        stage_latencies = defaultdict(list)
        for metric in metrics:
            if metric.stt_latency:
                stage_latencies["stt"].append(metric.stt_latency)
            if metric.ai_latency:
                stage_latencies["ai"].append(metric.ai_latency)
            if metric.tts_latency:
                stage_latencies["tts"].append(metric.tts_latency)

        # Find bottleneck stages
        for stage, latencies in stage_latencies.items():
            if latencies:
                avg_stage_latency = sum(latencies) / len(latencies)
                if avg_stage_latency > 1.5:  # Stage taking more than 1.5 seconds
                    recommendations.append(
                        f"Optimize {stage.upper()} processing (avg: {avg_stage_latency:.2f}s)"
                    )

        if len(recommendations) == 0:
            recommendations.append("Performance is within acceptable ranges")

        return recommendations[:5]  # Limit to 5 recommendations

    async def _generate_periodic_report(self) -> None:
        """Generate periodic performance report."""
        try:
            report = await self.generate_performance_report(self.reporting_interval)

            # Log performance summary
            self.logger.info(
                "periodic_performance_summary",
                total_sessions=report.total_voice_sessions,
                average_latency=report.average_latency,
                p95_latency=report.p95_latency,
                sessions_meeting_target=report.sessions_meeting_latency_target,
                recommendations_count=len(report.recommendations),
            )

            # Log warnings for concerning metrics
            if (
                report.average_latency
                and report.average_latency > self.thresholds.warning_threshold
            ):
                self.logger.warning(
                    "high_average_latency_detected",
                    average_latency=report.average_latency,
                    threshold=self.thresholds.warning_threshold,
                )

        except Exception as e:
            self.logger.error("periodic_report_generation_failed", error=str(e))

    async def _cleanup_expired_alerts(self) -> None:
        """Clean up expired alerts."""
        try:
            current_time = datetime.utcnow()
            expired_alerts = []

            for alert_id, alert in self.active_alerts.items():
                # Auto-resolve alerts older than 1 hour
                if current_time - alert.triggered_at > timedelta(hours=1):
                    alert.resolved_at = current_time
                    alert.resolution_notes = "Auto-resolved after 1 hour"
                    expired_alerts.append(alert_id)

            # Remove expired alerts
            for alert_id in expired_alerts:
                del self.active_alerts[alert_id]

            if expired_alerts:
                self.logger.info("expired_alerts_cleaned_up", count=len(expired_alerts))

        except Exception as e:
            self.logger.error("alert_cleanup_failed", error=str(e))

    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get currently active alerts."""
        return list(self.active_alerts.values())

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        return self.performance_stats.copy()

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the performance monitor."""
        recent_metrics = self.metrics_buffer.get_recent_metrics(300)  # Last 5 minutes
        recent_alerts = [
            a
            for a in self.active_alerts.values()
            if datetime.utcnow() - a.triggered_at < timedelta(minutes=5)
        ]

        # Determine health status
        if len(recent_alerts) > 5:
            status = "critical"
        elif len(recent_alerts) > 2:
            status = "degraded"
        elif len(recent_metrics) == 0:
            status = "unknown"
        else:
            status = "healthy"

        return {
            "status": status,
            "active_alerts": len(self.active_alerts),
            "recent_alerts_5min": len(recent_alerts),
            "metrics_buffer_size": len(self.metrics_buffer._buffer),
            "active_sessions": len(self.active_sessions),
            "performance_stats": self.get_performance_stats(),
            "monitoring_enabled": self.monitoring_enabled,
            "alerting_enabled": self.alerting_enabled,
        }

    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        self.metrics_buffer.clear()
        self.active_sessions.clear()
        self.active_alerts.clear()
        self.performance_stats = {
            "total_sessions": 0,
            "sessions_meeting_target": 0,
            "average_latency": 0.0,
            "p95_latency": 0.0,
            "p99_latency": 0.0,
            "alerts_generated": 0,
            "critical_alerts": 0,
        }
        self.logger.info("performance_metrics_reset")


# Global voice performance monitor instance
voice_performance_monitor = VoicePerformanceMonitor()
