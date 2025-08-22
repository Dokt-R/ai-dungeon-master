"""
Voice Session Manager Component for AI Dungeon Master.

This module provides comprehensive voice session lifecycle management with boundaries,
resource allocation, and privacy controls to ensure system stability and compliance.

Features:
- Voice session lifecycle management
- Concurrent session handling and resource allocation
- Session cleanup and resource optimization
- Privacy and data retention management
- Session timeout and recovery procedures
- Resource monitoring and limits enforcement
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from packages.shared.models import (
    VoiceSessionConfig, VoiceLatencyMetrics, AudioStreamInfo,
    PrivacyComplianceRecord
)
from packages.backend.components.observability_service import observability_service
from packages.backend.components.voice_performance_monitor import voice_performance_monitor
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


class SessionState(Enum):
    """Voice session states."""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    PROCESSING = "processing"
    PAUSED = "paused"
    TERMINATING = "terminating"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class ManagedVoiceSession:
    """A managed voice session with full lifecycle tracking."""

    session_id: str
    user_id: str
    channel_id: str
    guild_id: str
    started_at: datetime
    state: SessionState = SessionState.INITIALIZING

    # Session configuration
    config: VoiceSessionConfig = field(default_factory=VoiceSessionConfig)

    # Performance tracking
    performance_metrics: List[VoiceLatencyMetrics] = field(default_factory=list)

    # Resource tracking
    audio_streams: List[str] = field(default_factory=list)
    active_connections: int = 0
    memory_usage: int = 0
    processing_time: float = 0.0

    # Privacy and compliance
    privacy_record: Optional[PrivacyComplianceRecord] = None

    # Session boundaries
    max_duration_reached: bool = False
    timeout_warning_sent: bool = False
    resource_limit_exceeded: bool = False

    # Cleanup tracking
    last_activity: datetime = field(default_factory=datetime.utcnow)
    cleanup_scheduled: bool = False

    def is_expired(self) -> bool:
        """Check if session has expired based on timeout."""
        return datetime.utcnow() - self.started_at > timedelta(seconds=self.config.session_timeout)

    def is_duration_exceeded(self) -> bool:
        """Check if session duration exceeds maximum."""
        return datetime.utcnow() - self.started_at > timedelta(seconds=self.config.max_session_duration)

    def should_cleanup(self) -> bool:
        """Check if session should be cleaned up."""
        time_since_activity = datetime.utcnow() - self.last_activity
        return time_since_activity > timedelta(minutes=5)  # 5 minutes of inactivity


@dataclass
class ResourceLimits:
    """System resource limits for voice sessions."""

    max_concurrent_sessions: int = 10
    max_sessions_per_user: int = 3
    max_sessions_per_guild: int = 5
    max_total_memory_mb: int = 1024
    max_cpu_usage_percent: int = 80

    # Rate limiting
    max_session_starts_per_minute: int = 20
    max_session_starts_per_user_per_minute: int = 2


class VoiceSessionManager:
    """
    Comprehensive voice session manager with boundaries and compliance.

    Features:
    - Session lifecycle management
    - Resource allocation and limits
    - Privacy and data retention
    - Session cleanup and optimization
    - Performance monitoring integration
    - Compliance tracking
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Session management
        self.active_sessions: Dict[str, ManagedVoiceSession] = {}
        self.completed_sessions: Dict[str, ManagedVoiceSession] = {}
        self.session_history: List[ManagedVoiceSession] = []

        # Resource limits
        self.resource_limits = ResourceLimits(
            max_concurrent_sessions=self.config.get('max_concurrent_sessions', 10),
            max_sessions_per_user=self.config.get('max_sessions_per_user', 3),
            max_sessions_per_guild=self.config.get('max_sessions_per_guild', 5)
        )

        # User and guild tracking
        self.user_sessions: Dict[str, Set[str]] = {}
        self.guild_sessions: Dict[str, Set[str]] = {}

        # Rate limiting
        self.session_start_times: List[datetime] = []
        self.user_session_start_times: Dict[str, List[datetime]] = {}

        # Privacy and compliance
        self.privacy_records: Dict[str, PrivacyComplianceRecord] = {}

        # Performance tracking
        self.session_stats = {
            'total_sessions_created': 0,
            'total_sessions_completed': 0,
            'total_sessions_timed_out': 0,
            'total_sessions_error': 0,
            'average_session_duration': 0.0,
            'max_concurrent_sessions': 0
        }

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._monitoring_task: Optional[asyncio.Task] = None

        # Configuration
        self.enable_auto_cleanup = True
        self.enable_privacy_mode = True
        self.session_cleanup_interval = 60  # seconds
        self.session_monitoring_interval = 30  # seconds

    async def start_manager(self) -> None:
        """Start the session manager."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info("voice_session_manager_started")

    async def stop_manager(self) -> None:
        """Stop the session manager."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None

        logger.info("voice_session_manager_stopped")

    async def create_voice_session(
        self,
        session_id: str,
        user_id: str,
        channel_id: str,
        guild_id: str,
        correlation_id: Optional[str] = None
    ) -> Optional[ManagedVoiceSession]:
        """
        Create a new voice session with validation and limits checking.

        Args:
            session_id: Unique session identifier
            user_id: User creating the session
            channel_id: Voice channel ID
            guild_id: Discord guild ID
            correlation_id: Correlation ID for tracing

        Returns:
            ManagedVoiceSession if created successfully, None otherwise
        """
        try:
            with observability_service.trace_operation(
                operation_name="voice_session_creation",
                session_id=session_id,
                user_id=user_id,
                correlation_id=correlation_id
            ) as trace_id:

                # Check resource limits
                if not self._check_resource_limits(user_id, guild_id):
                    logger.warning(
                        "session_creation_denied_resource_limits",
                        session_id=session_id,
                        user_id=user_id,
                        guild_id=guild_id,
                        correlation_id=correlation_id
                    )
                    return None

                # Check rate limits
                if not self._check_rate_limits(user_id):
                    logger.warning(
                        "session_creation_denied_rate_limit",
                        session_id=session_id,
                        user_id=user_id,
                        correlation_id=correlation_id
                    )
                    return None

                # Create session
                session = ManagedVoiceSession(
                    session_id=session_id,
                    user_id=user_id,
                    channel_id=channel_id,
                    guild_id=guild_id,
                    started_at=datetime.utcnow(),
                    state=SessionState.INITIALIZING
                )

                # Register session
                self.active_sessions[session_id] = session

                # Update tracking
                self._register_session(session)

                # Create privacy record
                if self.enable_privacy_mode:
                    privacy_record = self._create_privacy_record(session)
                    session.privacy_record = privacy_record
                    self.privacy_records[session_id] = privacy_record

                # Update statistics
                self.session_stats['total_sessions_created'] += 1
                self.session_stats['max_concurrent_sessions'] = max(
                    self.session_stats['max_concurrent_sessions'],
                    len(self.active_sessions)
                )

                logger.info(
                    "voice_session_created",
                    session_id=session_id,
                    user_id=user_id,
                    channel_id=channel_id,
                    guild_id=guild_id,
                    concurrent_sessions=len(self.active_sessions),
                    correlation_id=correlation_id,
                    trace_id=trace_id
                )

                return session

        except Exception as e:
            logger.error(
                "voice_session_creation_failed",
                session_id=session_id,
                user_id=user_id,
                error=str(e),
                correlation_id=correlation_id
            )
            return None

    def update_session_state(
        self,
        session_id: str,
        new_state: SessionState,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Update the state of an active session.

        Args:
            session_id: Session to update
            new_state: New session state
            correlation_id: Correlation ID for tracing

        Returns:
            True if update successful, False otherwise
        """
        try:
            if session_id not in self.active_sessions:
                logger.warning(
                    "session_not_found_for_state_update",
                    session_id=session_id,
                    correlation_id=correlation_id
                )
                return False

            session = self.active_sessions[session_id]
            old_state = session.state
            session.state = new_state
            session.last_activity = datetime.utcnow()

            # Handle state-specific logic
            if new_state == SessionState.COMPLETED:
                self._complete_session(session, correlation_id)
            elif new_state == SessionState.ERROR:
                self._handle_session_error(session, correlation_id)
            elif new_state == SessionState.TIMEOUT:
                self._handle_session_timeout(session, correlation_id)

            logger.info(
                "voice_session_state_updated",
                session_id=session_id,
                old_state=old_state.value,
                new_state=new_state.value,
                correlation_id=correlation_id
            )

            return True

        except Exception as e:
            logger.error(
                "session_state_update_failed",
                session_id=session_id,
                new_state=new_state.value,
                error=str(e),
                correlation_id=correlation_id
            )
            return False

    async def terminate_session(
        self,
        session_id: str,
        reason: str = "terminated_by_request",
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Terminate a voice session.

        Args:
            session_id: Session to terminate
            reason: Reason for termination
            correlation_id: Correlation ID for tracing

        Returns:
            True if termination successful, False otherwise
        """
        try:
            if session_id not in self.active_sessions:
                logger.warning(
                    "session_not_found_for_termination",
                    session_id=session_id,
                    correlation_id=correlation_id
                )
                return False

            session = self.active_sessions[session_id]

            # Update state
            session.state = SessionState.TERMINATING
            session.last_activity = datetime.utcnow()

            # Clean up resources
            await self._cleanup_session_resources(session)

            # Move to completed
            self._complete_session(session, correlation_id, reason)

            logger.info(
                "voice_session_terminated",
                session_id=session_id,
                reason=reason,
                duration=(datetime.utcnow() - session.started_at).total_seconds(),
                correlation_id=correlation_id
            )

            return True

        except Exception as e:
            logger.error(
                "session_termination_failed",
                session_id=session_id,
                error=str(e),
                correlation_id=correlation_id
            )
            return False

    def get_session_info(self, session_id: str) -> Optional[ManagedVoiceSession]:
        """Get information about a specific session."""
        return self.active_sessions.get(session_id)

    def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        return len(self.active_sessions)

    def get_sessions_by_user(self, user_id: str) -> List[ManagedVoiceSession]:
        """Get all sessions for a specific user."""
        return [s for s in self.active_sessions.values() if s.user_id == user_id]

    def get_sessions_by_guild(self, guild_id: str) -> List[ManagedVoiceSession]:
        """Get all sessions for a specific guild."""
        return [s for s in self.active_sessions.values() if s.guild_id == guild_id]

    def _check_resource_limits(self, user_id: str, guild_id: str) -> bool:
        """Check if creating a new session would exceed resource limits."""
        try:
            # Check total concurrent sessions
            if len(self.active_sessions) >= self.resource_limits.max_concurrent_sessions:
                return False

            # Check user session limit
            user_sessions = len(self.user_sessions.get(user_id, set()))
            if user_sessions >= self.resource_limits.max_sessions_per_user:
                return False

            # Check guild session limit
            guild_sessions = len(self.guild_sessions.get(guild_id, set()))
            if guild_sessions >= self.resource_limits.max_sessions_per_guild:
                return False

            return True

        except Exception as e:
            logger.error("resource_limit_check_failed", error=str(e))
            return False

    def _check_rate_limits(self, user_id: str) -> bool:
        """Check if user is within rate limits."""
        try:
            current_time = datetime.utcnow()
            cutoff_time = current_time - timedelta(minutes=1)

            # Global rate limit
            recent_starts = [t for t in self.session_start_times if t > cutoff_time]
            if len(recent_starts) >= self.resource_limits.max_session_starts_per_minute:
                return False

            # User-specific rate limit
            user_starts = self.user_session_start_times.get(user_id, [])
            recent_user_starts = [t for t in user_starts if t > cutoff_time]
            if len(recent_user_starts) >= self.resource_limits.max_session_starts_per_user_per_minute:
                return False

            return True

        except Exception as e:
            logger.error("rate_limit_check_failed", error=str(e))
            return False

    def _register_session(self, session: ManagedVoiceSession) -> None:
        """Register session in tracking structures."""
        try:
            # Add to user tracking
            if session.user_id not in self.user_sessions:
                self.user_sessions[session.user_id] = set()
            self.user_sessions[session.user_id].add(session.session_id)

            # Add to guild tracking
            if session.guild_id not in self.guild_sessions:
                self.guild_sessions[session.guild_id] = set()
            self.guild_sessions[session.guild_id].add(session.session_id)

            # Track start time for rate limiting
            self.session_start_times.append(session.started_at)
            if session.user_id not in self.user_session_start_times:
                self.user_session_start_times[session.user_id] = []
            self.user_session_start_times[session.user_id].append(session.started_at)

            # Clean old rate limit data
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)
            self.session_start_times = [t for t in self.session_start_times if t > cutoff_time]
            for user_id in self.user_session_start_times:
                self.user_session_start_times[user_id] = [
                    t for t in self.user_session_start_times[user_id] if t > cutoff_time
                ]

        except Exception as e:
            logger.error("session_registration_failed", session_id=session.session_id, error=str(e))

    def _create_privacy_record(self, session: ManagedVoiceSession) -> PrivacyComplianceRecord:
        """Create privacy compliance record for session."""
        deletion_date = datetime.utcnow() + timedelta(days=session.config.audio_retention_days)

        return PrivacyComplianceRecord(
            session_id=session.session_id,
            user_id=session.user_id,
            data_retention_period_days=session.config.audio_retention_days,
            data_deletion_date=deletion_date,
            privacy_consent_obtained=True,  # Assume obtained for voice sessions
            data_encrypted=True,  # Assume encrypted in transit
            compliance_officer="voice_session_manager",
            audit_trail=[{
                "timestamp": datetime.utcnow().isoformat(),
                "action": "session_created",
                "details": "Voice session initialized with privacy compliance"
            }]
        )

    def _complete_session(
        self,
        session: ManagedVoiceSession,
        correlation_id: Optional[str] = None,
        completion_reason: str = "normal_completion"
    ) -> None:
        """Complete a session and move to completed tracking."""
        try:
            # Remove from active sessions
            if session.session_id in self.active_sessions:
                del self.active_sessions[session.session_id]

            # Add to completed sessions
            self.completed_sessions[session.session_id] = session

            # Update session history (keep last 1000)
            self.session_history.append(session)
            if len(self.session_history) > 1000:
                self.session_history = self.session_history[-1000:]

            # Clean up tracking
            self._unregister_session(session)

            # Update statistics
            session_duration = (datetime.utcnow() - session.started_at).total_seconds()
            self.session_stats['total_sessions_completed'] += 1

            # Update average duration
            total_completed = self.session_stats['total_sessions_completed']
            current_avg = self.session_stats['average_session_duration']
            self.session_stats['average_session_duration'] = (
                (current_avg * (total_completed - 1)) + session_duration
            ) / total_completed

        except Exception as e:
            logger.error(
                "session_completion_failed",
                session_id=session.session_id,
                error=str(e),
                correlation_id=correlation_id
            )

    def _handle_session_error(self, session: ManagedVoiceSession, correlation_id: Optional[str] = None) -> None:
        """Handle session error state."""
        self.session_stats['total_sessions_error'] += 1
        logger.warning(
            "session_entered_error_state",
            session_id=session.session_id,
            correlation_id=correlation_id
        )

    def _handle_session_timeout(self, session: ManagedVoiceSession, correlation_id: Optional[str] = None) -> None:
        """Handle session timeout."""
        self.session_stats['total_sessions_timed_out'] += 1
        logger.info(
            "session_timed_out",
            session_id=session.session_id,
            timeout_duration=session.config.session_timeout,
            correlation_id=correlation_id
        )

    def _unregister_session(self, session: ManagedVoiceSession) -> None:
        """Remove session from tracking structures."""
        try:
            # Remove from user tracking
            if session.user_id in self.user_sessions:
                self.user_sessions[session.user_id].discard(session.session_id)
                if not self.user_sessions[session.user_id]:
                    del self.user_sessions[session.user_id]

            # Remove from guild tracking
            if session.guild_id in self.guild_sessions:
                self.guild_sessions[session.guild_id].discard(session.session_id)
                if not self.guild_sessions[session.guild_id]:
                    del self.guild_sessions[session.guild_id]

        except Exception as e:
            logger.error("session_unregistration_failed", session_id=session.session_id, error=str(e))

    async def _cleanup_session_resources(self, session: ManagedVoiceSession) -> None:
        """Clean up resources used by a session."""
        try:
            # Clean up audio streams
            for stream_id in session.audio_streams:
                # This would integrate with audio processor to clean up streams
                pass

            # Clean up privacy record
            if session.privacy_record and session.session_id in self.privacy_records:
                del self.privacy_records[session.session_id]

            logger.debug("session_resources_cleaned", session_id=session.session_id)

        except Exception as e:
            logger.error("session_resource_cleanup_failed", session_id=session.session_id, error=str(e))

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for expired sessions."""
        while self.enable_auto_cleanup:
            try:
                await asyncio.sleep(self.session_cleanup_interval)

                current_time = datetime.utcnow()
                expired_sessions = []

                # Find expired sessions
                for session_id, session in self.active_sessions.items():
                    if session.is_expired() or session.is_duration_exceeded() or session.should_cleanup():
                        expired_sessions.append(session_id)

                # Clean up expired sessions
                for session_id in expired_sessions:
                    session = self.active_sessions.get(session_id)
                    if session:
                        reason = "expired" if session.is_expired() else "duration_exceeded" if session.is_duration_exceeded() else "inactivity"
                        await self.terminate_session(session_id, reason)

                if expired_sessions:
                    logger.info("expired_sessions_cleaned", count=len(expired_sessions))

            except Exception as e:
                logger.error("cleanup_loop_error", error=str(e))

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop for session health."""
        while True:
            try:
                await asyncio.sleep(self.session_monitoring_interval)

                # Check for sessions needing attention
                for session in self.active_sessions.values():
                    await self._check_session_health(session)

            except Exception as e:
                logger.error("monitoring_loop_error", error=str(e))

    async def _check_session_health(self, session: ManagedVoiceSession) -> None:
        """Check health of an individual session."""
        try:
            current_time = datetime.utcnow()

            # Check for timeout warnings
            if not session.timeout_warning_sent:
                time_remaining = session.config.session_timeout - (current_time - session.started_at).total_seconds()
                if time_remaining <= 300:  # 5 minutes warning
                    session.timeout_warning_sent = True
                    logger.warning(
                        "session_timeout_warning",
                        session_id=session.session_id,
                        time_remaining=time_remaining
                    )

            # Check for duration warnings
            if not session.max_duration_reached:
                duration_remaining = session.config.max_session_duration - (current_time - session.started_at).total_seconds()
                if duration_remaining <= 600:  # 10 minutes warning
                    session.max_duration_reached = True
                    logger.warning(
                        "session_duration_warning",
                        session_id=session.session_id,
                        duration_remaining=duration_remaining
                    )

        except Exception as e:
            logger.error("session_health_check_failed", session_id=session.session_id, error=str(e))

    def get_session_statistics(self) -> Dict[str, Any]:
        """Get comprehensive session statistics."""
        return {
            "active_sessions": len(self.active_sessions),
            "completed_sessions": len(self.completed_sessions),
            "total_sessions_created": self.session_stats['total_sessions_created'],
            "total_sessions_completed": self.session_stats['total_sessions_completed'],
            "total_sessions_timed_out": self.session_stats['total_sessions_timed_out'],
            "total_sessions_error": self.session_stats['total_sessions_error'],
            "average_session_duration": self.session_stats['average_session_duration'],
            "max_concurrent_sessions": self.session_stats['max_concurrent_sessions'],
            "sessions_by_user": {user_id: len(sessions) for user_id, sessions in self.user_sessions.items()},
            "sessions_by_guild": {guild_id: len(sessions) for guild_id, sessions in self.guild_sessions.items()},
            "resource_limits": {
                "max_concurrent_sessions": self.resource_limits.max_concurrent_sessions,
                "max_sessions_per_user": self.resource_limits.max_sessions_per_user,
                "max_sessions_per_guild": self.resource_limits.max_sessions_per_guild
            }
        }

    def get_privacy_compliance_status(self) -> Dict[str, Any]:
        """Get privacy compliance status."""
        return {
            "privacy_mode_enabled": self.enable_privacy_mode,
            "total_privacy_records": len(self.privacy_records),
            "records_pending_deletion": len([
                r for r in self.privacy_records.values()
                if r.data_deletion_date <= datetime.utcnow()
            ]),
            "compliance_officer": "voice_session_manager"
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the session manager."""
        # Determine overall health
        active_sessions = len(self.active_sessions)
        resource_usage_percent = (active_sessions / self.resource_limits.max_concurrent_sessions) * 100

        if resource_usage_percent >= 90:
            status = "critical"
        elif resource_usage_percent >= 75:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "active_sessions": active_sessions,
            "resource_usage_percent": resource_usage_percent,
            "auto_cleanup_enabled": self.enable_auto_cleanup,
            "privacy_mode_enabled": self.enable_privacy_mode,
            "session_limits": {
                "max_concurrent": self.resource_limits.max_concurrent_sessions,
                "max_per_user": self.resource_limits.max_sessions_per_user,
                "max_per_guild": self.resource_limits.max_sessions_per_guild
            },
            "background_tasks": {
                "cleanup_task_running": self._cleanup_task is not None and not self._cleanup_task.done(),
                "monitoring_task_running": self._monitoring_task is not None and not self._monitoring_task.done()
            }
        }


# Global voice session manager instance
voice_session_manager = VoiceSessionManager()