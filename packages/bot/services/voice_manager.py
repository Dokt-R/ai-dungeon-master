"""
Voice Manager Service for AI Dungeon Master.

This module provides comprehensive voice connection management for Discord voice channels,
including connection lifecycle, state tracking, permission handling, and error recovery.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from packages.shared.logging_config import get_logger
from packages.shared.models import (
    AudioStreamInfo,
    VoiceConnection,
    VoiceSession,
    VoiceStatusResponse,
)


@dataclass
class VoiceConnectionState:
    """Internal state tracking for voice connections."""

    connection_id: str
    guild_id: str
    channel_id: str
    status: str = "disconnected"
    connected_at: Optional[datetime] = None
    participants: Set[str] = field(default_factory=set)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    error_count: int = 0
    reconnect_attempts: int = 0
    max_reconnect_attempts: int = 3
    reconnect_delay: float = 5.0
    heartbeat_interval: float = 30.0
    connection_timeout: float = 300.0  # 5 minutes

    def should_reconnect(self) -> bool:
        """Check if connection should attempt to reconnect."""
        return (
            self.reconnect_attempts < self.max_reconnect_attempts
            and self.status in ["disconnected", "error"]
        )

    def can_timeout(self) -> bool:
        """Check if connection can timeout."""
        if not self.connected_at:
            return False
        return (
            datetime.utcnow() - self.connected_at
        ).total_seconds() > self.connection_timeout


class VoiceManagerService:
    """
    Core service for managing Discord voice connections.

    Features:
    - Voice connection lifecycle management
    - Permission validation and checking
    - State tracking and monitoring
    - Error recovery and reconnection
    - Audio stream management
    - Session tracking and analytics
    """

    def __init__(self):
        """Initialize the Voice Manager Service."""
        self.logger = get_logger(f"{__name__}.VoiceManagerService")

        # Connection tracking
        self._connections: Dict[str, VoiceConnectionState] = {}
        self._guild_connections: Dict[str, str] = {}  # guild_id -> connection_id

        # Session tracking
        self._sessions: Dict[str, VoiceSession] = {}

        # Audio stream tracking
        self._audio_streams: Dict[str, AudioStreamInfo] = {}

        # Background tasks
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self._timeout_tasks: Dict[str, asyncio.Task] = {}

        # Configuration
        self._max_connections_per_guild = 1
        self._default_reconnect_delay = 5.0
        self._max_reconnect_attempts = 3
        self._connection_timeout = 300.0  # 5 minutes
        self._heartbeat_interval = 30.0  # 30 seconds

        self.logger.info("VoiceManagerService initialized")

    def _generate_connection_id(self, guild_id: str, channel_id: str) -> str:
        """Generate a unique connection ID."""
        return f"voice_{guild_id}_{channel_id}_{int(datetime.utcnow().timestamp())}"

    def _generate_session_id(self, guild_id: str, channel_id: str) -> str:
        """Generate a unique session ID."""
        return f"session_{guild_id}_{channel_id}_{int(datetime.utcnow().timestamp())}"

    def _get_or_create_connection_state(
        self, guild_id: str, channel_id: str
    ) -> VoiceConnectionState:
        """Get or create connection state for a guild/channel."""
        connection_id = self._guild_connections.get(guild_id)

        if not connection_id:
            connection_id = self._generate_connection_id(guild_id, channel_id)
            self._guild_connections[guild_id] = connection_id
            self._connections[connection_id] = VoiceConnectionState(
                connection_id=connection_id, guild_id=guild_id, channel_id=channel_id
            )
            self.logger.info(
                "Created new connection state",
                connection_id=connection_id,
                guild_id=guild_id,
                channel_id=channel_id,
            )

        return self._connections[connection_id]

    def _cleanup_connection_state(self, connection_id: str) -> None:
        """Clean up connection state and associated resources."""
        if connection_id in self._connections:
            state = self._connections[connection_id]

            # Cancel background tasks
            if connection_id in self._heartbeat_tasks:
                self._heartbeat_tasks[connection_id].cancel()
                del self._heartbeat_tasks[connection_id]

            if connection_id in self._timeout_tasks:
                self._timeout_tasks[connection_id].cancel()
                del self._timeout_tasks[connection_id]

            # Remove from guild mapping
            if state.guild_id in self._guild_connections:
                del self._guild_connections[state.guild_id]

            # Remove connection state
            del self._connections[connection_id]

            self.logger.info("Cleaned up connection state", connection_id=connection_id)

    async def start_connection(
        self, guild_id: str, channel_id: str, user_id: str
    ) -> VoiceConnection:
        """
        Start a voice connection.

        Args:
            guild_id: Discord guild ID
            channel_id: Voice channel ID
            user_id: User initiating the connection

        Returns:
            VoiceConnection with connection details
        """
        try:
            # Check if guild already has active connection
            if guild_id in self._guild_connections:
                existing_connection_id = self._guild_connections[guild_id]
                existing_state = self._connections.get(existing_connection_id)
                if existing_state and existing_state.status == "connected":
                    raise ValueError(f"Guild {guild_id} already has active connection")

            # Create or get connection state
            state = self._get_or_create_connection_state(guild_id, channel_id)

            # Update state
            state.status = "connecting"
            state.connected_at = datetime.utcnow()
            state.last_activity = datetime.utcnow()
            state.participants.add(user_id)

            # Start heartbeat
            await self._start_heartbeat(state)

            # Create session
            session_id = self._generate_session_id(guild_id, channel_id)
            session = VoiceSession(
                session_id=session_id,
                guild_id=guild_id,
                channel_id=channel_id,
                status="active",
            )
            self._sessions[session_id] = session

            connection = VoiceConnection(
                connection_id=state.connection_id,
                channel_id=channel_id,
                guild_id=guild_id,
                status=state.status,
                participants=list(state.participants),
            )

            self.logger.info(
                "Voice connection started",
                connection_id=state.connection_id,
                guild_id=guild_id,
                channel_id=channel_id,
                user_id=user_id,
            )

            return connection

        except Exception as e:
            self.logger.error(
                "Failed to start voice connection",
                guild_id=guild_id,
                channel_id=channel_id,
                user_id=user_id,
                error=str(e),
            )
            raise

    async def complete_connection(
        self, connection_id: str, user_id: str
    ) -> VoiceConnection:
        """
        Mark a voice connection as fully established.

        Args:
            connection_id: The connection ID
            user_id: User completing the connection

        Returns:
            Updated VoiceConnection
        """
        if connection_id not in self._connections:
            raise ValueError(f"Connection {connection_id} not found")

        state = self._connections[connection_id]
        state.status = "connected"
        state.last_activity = datetime.utcnow()

        connection = VoiceConnection(
            connection_id=state.connection_id,
            channel_id=state.channel_id,
            guild_id=state.guild_id,
            status=state.status,
            participants=list(state.participants),
        )

        self.logger.info(
            "Voice connection completed", connection_id=connection_id, user_id=user_id
        )

        return connection

    async def disconnect_connection(
        self, connection_id: str, reason: str = "user_request", user_id: str = "system"
    ) -> None:
        """
        Disconnect a voice connection.

        Args:
            connection_id: The connection ID to disconnect
            reason: Reason for disconnection
            user_id: User requesting disconnection
        """
        if connection_id not in self._connections:
            self.logger.warning(
                "Attempted to disconnect non-existent connection",
                connection_id=connection_id,
                user_id=user_id,
            )
            return

        state = self._connections[connection_id]

        # Update session if exists
        session_id = self._generate_session_id(state.guild_id, state.channel_id)
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.ended_at = datetime.utcnow()
            session.status = "ended"

        # Update state
        state.status = "disconnected"
        state.disconnect_reason = reason
        state.last_activity = datetime.utcnow()

        # Clean up resources
        self._cleanup_connection_state(connection_id)

        self.logger.info(
            "Voice connection disconnected",
            connection_id=connection_id,
            guild_id=state.guild_id,
            channel_id=state.channel_id,
            reason=reason,
            user_id=user_id,
        )

    async def add_participant(self, connection_id: str, user_id: str) -> bool:
        """
        Add a participant to a voice connection.

        Args:
            connection_id: The connection ID
            user_id: User ID to add

        Returns:
            True if added successfully
        """
        if connection_id not in self._connections:
            return False

        state = self._connections[connection_id]
        state.participants.add(user_id)
        state.last_activity = datetime.utcnow()

        # Update session participant count
        session_id = self._generate_session_id(state.guild_id, state.channel_id)
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.total_participants = len(state.participants)
            session.max_concurrent_participants = max(
                session.max_concurrent_participants, len(state.participants)
            )

        self.logger.info(
            "Participant added to voice connection",
            connection_id=connection_id,
            user_id=user_id,
            total_participants=len(state.participants),
        )

        return True

    async def remove_participant(self, connection_id: str, user_id: str) -> bool:
        """
        Remove a participant from a voice connection.

        Args:
            connection_id: The connection ID
            user_id: User ID to remove

        Returns:
            True if removed successfully
        """
        if connection_id not in self._connections:
            return False

        state = self._connections[connection_id]
        if user_id in state.participants:
            state.participants.remove(user_id)
            state.last_activity = datetime.utcnow()

            self.logger.info(
                "Participant removed from voice connection",
                connection_id=connection_id,
                user_id=user_id,
                remaining_participants=len(state.participants),
            )

        return True

    def get_connection(self, connection_id: str) -> Optional[VoiceConnection]:
        """Get connection details by ID."""
        if connection_id not in self._connections:
            return None

        state = self._connections[connection_id]
        return VoiceConnection(
            connection_id=state.connection_id,
            channel_id=state.channel_id,
            guild_id=state.guild_id,
            status=state.status,
            participants=list(state.participants),
        )

    def get_guild_connection(self, guild_id: str) -> Optional[VoiceConnection]:
        """Get connection details for a guild."""
        if guild_id not in self._guild_connections:
            return None

        connection_id = self._guild_connections[guild_id]
        return self.get_connection(connection_id)

    def get_connection_status(self, guild_id: str) -> Optional[VoiceStatusResponse]:
        """Get voice connection status for a guild."""
        connection = self.get_guild_connection(guild_id)
        if not connection:
            return None

        # This would normally query Discord API for real-time info
        # For now, return cached information
        return VoiceStatusResponse(
            connected=connection.status == "connected",
            channel_id=connection.channel_id,
            guild_id=connection.guild_id,
            participant_count=len(connection.participants),
            participants=connection.participants,
            connected_at=connection.connected_at
            if connection.status == "connected"
            else None,
        )

    def list_active_connections(self) -> List[VoiceConnection]:
        """List all active voice connections."""
        active_connections = []
        for state in self._connections.values():
            if state.status == "connected":
                active_connections.append(
                    VoiceConnection(
                        connection_id=state.connection_id,
                        channel_id=state.channel_id,
                        guild_id=state.guild_id,
                        status=state.status,
                        participants=list(state.participants),
                    )
                )
        return active_connections

    async def _start_heartbeat(self, state: VoiceConnectionState) -> None:
        """Start heartbeat monitoring for a connection."""

        async def heartbeat():
            while state.status == "connected":
                try:
                    await asyncio.sleep(state.heartbeat_interval)
                    state.last_activity = datetime.utcnow()

                    # Check for timeout
                    if state.can_timeout():
                        await self.disconnect_connection(
                            state.connection_id, reason="timeout", user_id="system"
                        )
                        break

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(
                        "Heartbeat error",
                        connection_id=state.connection_id,
                        error=str(e),
                    )
                    state.error_count += 1

                    if state.error_count > 3:
                        await self.disconnect_connection(
                            state.connection_id,
                            reason="heartbeat_failed",
                            user_id="system",
                        )
                        break

        task = asyncio.create_task(heartbeat())
        self._heartbeat_tasks[state.connection_id] = task

    async def handle_connection_error(
        self, connection_id: str, error: str, user_id: str = "system"
    ) -> bool:
        """
        Handle a voice connection error.

        Args:
            connection_id: The connection with error
            error: Error description
            user_id: User who encountered the error

        Returns:
            True if error was handled successfully
        """
        if connection_id not in self._connections:
            return False

        state = self._connections[connection_id]
        state.error_count += 1
        state.error_message = error
        state.last_activity = datetime.utcnow()

        self.logger.warning(
            "Voice connection error",
            connection_id=connection_id,
            error=error,
            error_count=state.error_count,
            user_id=user_id,
        )

        # Update session with error
        session_id = self._generate_session_id(state.guild_id, state.channel_id)
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.connection_issues.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": error,
                    "user_id": user_id,
                }
            )

        # Attempt reconnection if appropriate
        if state.should_reconnect():
            await self._attempt_reconnection(state)
            return True

        # Disconnect if too many errors
        if state.error_count > 5:
            await self.disconnect_connection(
                connection_id, reason="too_many_errors", user_id="system"
            )
            return False
        else:
            return True

        return True

    async def _attempt_reconnection(self, state: VoiceConnectionState) -> None:
        """Attempt to reconnect a failed connection."""
        state.reconnect_attempts += 1
        state.status = "connecting"

        self.logger.info(
            "Attempting voice reconnection",
            connection_id=state.connection_id,
            attempt=state.reconnect_attempts,
            max_attempts=state.max_reconnect_attempts,
        )

        # Wait before attempting reconnection
        await asyncio.sleep(state.reconnect_delay)

        # In a real implementation, this would attempt to reconnect
        # For now, we'll just log the attempt
        self.logger.info(
            "Voice reconnection attempt completed",
            connection_id=state.connection_id,
            success=True,  # Assume success for MVP
        )

    def get_voice_statistics(self) -> Dict[str, Any]:
        """Get voice service statistics."""
        total_connections = len(self._connections)
        active_connections = len(
            [c for c in self._connections.values() if c.status == "connected"]
        )
        total_sessions = len(self._sessions)
        active_sessions = len(
            [s for s in self._sessions.values() if s.status == "active"]
        )

        return {
            "total_connections": total_connections,
            "active_connections": active_connections,
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "connections_by_status": {
                "connected": len(
                    [c for c in self._connections.values() if c.status == "connected"]
                ),
                "connecting": len(
                    [c for c in self._connections.values() if c.status == "connecting"]
                ),
                "disconnected": len(
                    [
                        c
                        for c in self._connections.values()
                        if c.status == "disconnected"
                    ]
                ),
                "error": len(
                    [c for c in self._connections.values() if c.status == "error"]
                ),
            },
            "service_uptime": datetime.utcnow().isoformat(),
        }

    def clear_memory(self) -> bool:
        """
        Clear all connection and session data.

        Returns:
            True if cleared successfully
        """
        try:
            # Cancel all background tasks
            for task in self._heartbeat_tasks.values():
                task.cancel()
            for task in self._timeout_tasks.values():
                task.cancel()

            # Clear all data structures
            self._connections.clear()
            self._guild_connections.clear()
            self._sessions.clear()
            self._audio_streams.clear()
            self._heartbeat_tasks.clear()
            self._timeout_tasks.clear()

            self.logger.info("Voice manager memory cleared")
            return True

        except Exception as e:
            self.logger.error("Failed to clear voice manager memory", error=str(e))
            return False


# Global voice manager instance
voice_manager_service = VoiceManagerService()
