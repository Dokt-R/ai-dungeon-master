"""
Unit tests for Voice Manager Service.

Tests cover:
- Voice connection lifecycle management
- Participant tracking and management
- Error handling and recovery mechanisms
- Session tracking and statistics
- Service initialization and configuration
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from packages.bot.services.voice_manager import (
    VoiceConnectionState,
    VoiceManagerService,
)
from packages.shared.models import (
    VoiceConnection,
    VoiceSession,
)


class TestVoiceManagerServiceInitialization:
    """Test VoiceManagerService initialization."""

    def test_service_initialization(self):
        """Test service initializes with correct default values."""
        service = VoiceManagerService()

        assert service._connections == {}
        assert service._guild_connections == {}
        assert service._sessions == {}
        assert service._audio_streams == {}
        assert service._max_connections_per_guild == 1
        assert service._default_reconnect_delay == 5.0
        assert service._max_reconnect_attempts == 3
        assert service._connection_timeout == 300.0

    def test_generate_connection_id(self):
        """Test connection ID generation."""
        service = VoiceManagerService()

        with patch("packages.bot.services.voice_manager.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value.timestamp.return_value = 1234567890.0

            connection_id = service._generate_connection_id("123", "456")

            assert "voice_123_456_1234567890" in connection_id

    def test_generate_session_id(self):
        """Test session ID generation."""
        service = VoiceManagerService()

        with patch("packages.bot.services.voice_manager.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value.timestamp.return_value = 1234567890.0

            session_id = service._generate_session_id("123", "456")

            assert "session_123_456_1234567890" in session_id


class TestVoiceConnectionLifecycle:
    """Test voice connection lifecycle management."""

    @pytest.mark.asyncio
    async def test_start_connection_success(self):
        """Test successful voice connection start."""
        service = VoiceManagerService()

        with patch.object(service, "_start_heartbeat"):
            connection = await service.start_connection(
                guild_id="123", channel_id="456", user_id="789"
            )

        assert isinstance(connection, VoiceConnection)
        assert connection.guild_id == "123"
        assert connection.channel_id == "456"
        assert connection.status == "connecting"
        assert len(connection.participants) == 1
        assert "789" in connection.participants

        # Verify connection is tracked
        assert "123" in service._guild_connections
        assert connection.connection_id in service._connections

    @pytest.mark.asyncio
    async def test_start_connection_guild_already_connected(self):
        """Test starting connection when guild already has active connection."""
        service = VoiceManagerService()

        # Create existing connection
        existing_state = VoiceConnectionState(
            connection_id="existing_conn",
            guild_id="123",
            channel_id="456",
            status="connected",
        )
        service._connections["existing_conn"] = existing_state
        service._guild_connections["123"] = "existing_conn"

        with pytest.raises(ValueError, match="already has active connection"):
            await service.start_connection("123", "789", "999")

    @pytest.mark.asyncio
    async def test_complete_connection_success(self):
        """Test successful connection completion."""
        service = VoiceManagerService()

        # Create connection state
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="connecting",
        )
        service._connections["test_conn"] = state

        connection = await service.complete_connection(
            connection_id="test_conn", user_id="789"
        )

        assert connection.status == "connected"
        assert service._connections["test_conn"].status == "connected"

    @pytest.mark.asyncio
    async def test_disconnect_connection_success(self):
        """Test successful connection disconnection."""
        service = VoiceManagerService()

        # Create connection state
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="connected",
        )
        service._connections["test_conn"] = state
        service._guild_connections["123"] = "test_conn"

        await service.disconnect_connection(
            connection_id="test_conn", reason="user_request", user_id="789"
        )

        assert "test_conn" not in service._connections
        assert "123" not in service._guild_connections

    @pytest.mark.asyncio
    async def test_disconnect_connection_not_found(self):
        """Test disconnecting non-existent connection."""
        service = VoiceManagerService()

        await service.disconnect_connection(
            connection_id="nonexistent", reason="test", user_id="789"
        )

        # Should not raise exception


class TestParticipantManagement:
    """Test voice participant management."""

    @pytest.mark.asyncio
    async def test_add_participant_success(self):
        """Test successfully adding a participant."""
        service = VoiceManagerService()

        # Create connection state
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="connected",
        )
        service._connections["test_conn"] = state

        result = await service.add_participant("test_conn", "789")

        assert result is True
        assert "789" in state.participants

    @pytest.mark.asyncio
    async def test_add_participant_connection_not_found(self):
        """Test adding participant to non-existent connection."""
        service = VoiceManagerService()

        result = await service.add_participant("nonexistent", "789")

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_participant_success(self):
        """Test successfully removing a participant."""
        service = VoiceManagerService()

        # Create connection state with participant
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="connected",
        )
        state.participants.add("789")
        service._connections["test_conn"] = state

        result = await service.remove_participant("test_conn", "789")

        assert result is True
        assert "789" not in state.participants

    @pytest.mark.asyncio
    async def test_remove_participant_not_found(self):
        """Test removing participant from non-existent connection."""
        service = VoiceManagerService()

        result = await service.remove_participant("nonexistent", "789")

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_participant_not_in_channel(self):
        """Test removing participant not in the channel."""
        service = VoiceManagerService()

        # Create connection state without the participant
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="connected",
        )
        service._connections["test_conn"] = state

        result = await service.remove_participant("test_conn", "789")

        assert result is True  # Should succeed even if participant wasn't there


class TestConnectionQueries:
    """Test voice connection query methods."""

    def test_get_connection_exists(self):
        """Test getting existing connection."""
        service = VoiceManagerService()

        # Create connection state
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="connected",
        )
        service._connections["test_conn"] = state

        connection = service.get_connection("test_conn")

        assert connection is not None
        assert connection.connection_id == "test_conn"
        assert connection.guild_id == "123"
        assert connection.channel_id == "456"
        assert connection.status == "connected"

    def test_get_connection_not_exists(self):
        """Test getting non-existent connection."""
        service = VoiceManagerService()

        connection = service.get_connection("nonexistent")

        assert connection is None

    def test_get_guild_connection_exists(self):
        """Test getting guild connection."""
        service = VoiceManagerService()

        # Create connection state
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="error",  # Error status allows reconnection
        )
        service._connections["test_conn"] = state
        service._guild_connections["123"] = "test_conn"

        connection = service.get_guild_connection("123")

        assert connection is not None
        assert connection.guild_id == "123"

    def test_get_guild_connection_not_exists(self):
        """Test getting guild connection when none exists."""
        service = VoiceManagerService()

        connection = service.get_guild_connection("123")

        assert connection is None

    def test_list_active_connections(self):
        """Test listing all active connections."""
        service = VoiceManagerService()

        # Create multiple connection states
        states = [
            VoiceConnectionState(
                connection_id="conn_1",
                guild_id="123",
                channel_id="456",
                status="connected",
            ),
            VoiceConnectionState(
                connection_id="conn_2",
                guild_id="789",
                channel_id="012",
                status="connecting",  # Not active
            ),
            VoiceConnectionState(
                connection_id="conn_3",
                guild_id="345",
                channel_id="678",
                status="disconnected",  # Not active
            ),
        ]

        for state in states:
            service._connections[state.connection_id] = state

        active_connections = service.list_active_connections()

        assert len(active_connections) == 1
        assert active_connections[0].connection_id == "conn_1"
        assert active_connections[0].status == "connected"


class TestErrorHandling:
    """Test error handling and recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_handle_connection_error_first_attempt(self):
        """Test handling connection error on first attempt."""
        service = VoiceManagerService()

        # Create connection state
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="error",  # Error status allows reconnection
        )
        service._connections["test_conn"] = state

        with patch.object(service, "_attempt_reconnection") as mock_reconnect:
            result = await service.handle_connection_error(
                connection_id="test_conn", error="Connection timeout", user_id="789"
            )

        assert result is True
        assert state.error_count == 1
        assert state.error_message == "Connection timeout"
        # The reconnection is attempted for the first few errors
        mock_reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_connection_error_multiple_attempts(self):
        """Test handling connection error after multiple attempts."""
        service = VoiceManagerService()

        # Create connection state with high error count
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="connected",
        )
        state.error_count = 5  # At limit - will trigger disconnect
        service._connections["test_conn"] = state

        with patch.object(service, "disconnect_connection") as mock_disconnect:
            result = await service.handle_connection_error(
                connection_id="test_conn", error="Connection timeout", user_id="789"
            )

        assert result is False
        mock_disconnect.assert_called_once_with("test_conn", reason="too_many_errors", user_id="system")

    @pytest.mark.asyncio
    async def test_handle_connection_error_connection_not_found(self):
        """Test handling error for non-existent connection."""
        service = VoiceManagerService()

        result = await service.handle_connection_error(
            connection_id="nonexistent", error="Test error", user_id="789"
        )

        assert result is False


class TestReconnectionLogic:
    """Test reconnection logic and state management."""

    def test_connection_state_should_reconnect_true(self):
        """Test reconnection eligibility when conditions are met."""
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="disconnected",
        )
        state.reconnect_attempts = 1  # Under limit

        assert state.should_reconnect() is True

    def test_connection_state_should_reconnect_false_max_attempts(self):
        """Test reconnection ineligibility when max attempts reached."""
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="disconnected",
        )
        state.reconnect_attempts = 3  # At limit

        assert state.should_reconnect() is False

    def test_connection_state_should_reconnect_false_wrong_status(self):
        """Test reconnection ineligibility when status is not appropriate."""
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="connected",  # Wrong status
        )
        state.reconnect_attempts = 1

        assert state.should_reconnect() is False

    def test_connection_state_can_timeout_true(self):
        """Test timeout eligibility when conditions are met."""
        past_time = datetime.utcnow() - timedelta(minutes=10)
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="connected",
        )
        state.connected_at = past_time

        assert state.can_timeout() is True

    def test_connection_state_can_timeout_false_no_connection_time(self):
        """Test timeout ineligibility when no connection time is set."""
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="connected",
        )
        # connected_at is None by default

        assert state.can_timeout() is False

    def test_connection_state_can_timeout_false_recent_connection(self):
        """Test timeout ineligibility when connection is recent."""
        recent_time = datetime.utcnow() - timedelta(minutes=1)
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="connected",
        )
        state.connected_at = recent_time

        assert state.can_timeout() is False


class TestVoiceStatistics:
    """Test voice service statistics and monitoring."""

    def test_get_voice_statistics_empty(self):
        """Test getting statistics with no connections."""
        service = VoiceManagerService()

        stats = service.get_voice_statistics()

        assert stats["total_connections"] == 0
        assert stats["active_connections"] == 0
        assert stats["total_sessions"] == 0
        assert stats["active_sessions"] == 0
        assert "connections_by_status" in stats
        assert "service_uptime" in stats

    def test_get_voice_statistics_with_data(self):
        """Test getting statistics with connections and sessions."""
        service = VoiceManagerService()

        # Create connection states
        states = [
            VoiceConnectionState(
                connection_id="conn_1",
                guild_id="123",
                channel_id="456",
                status="connected",
            ),
            VoiceConnectionState(
                connection_id="conn_2",
                guild_id="789",
                channel_id="012",
                status="connecting",
            ),
        ]

        for state in states:
            service._connections[state.connection_id] = state

        # Create sessions
        sessions = [
            VoiceSession(
                session_id="session_1",
                guild_id="123",
                channel_id="456",
                status="active",
            ),
            VoiceSession(
                session_id="session_2", guild_id="789", channel_id="012", status="ended"
            ),
        ]

        for session in sessions:
            service._sessions[session.session_id] = session

        stats = service.get_voice_statistics()

        assert stats["total_connections"] == 2
        assert stats["active_connections"] == 1
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 1
        assert stats["connections_by_status"]["connected"] == 1
        assert stats["connections_by_status"]["connecting"] == 1


class TestServiceCleanup:
    """Test service cleanup and resource management."""

    @pytest.mark.asyncio
    async def test_clear_memory_clears_all_data(self):
        """Test that clear_memory removes all connection data."""
        service = VoiceManagerService()

        # Add test data
        state = VoiceConnectionState(
            connection_id="test_conn",
            guild_id="123",
            channel_id="456",
            status="connected",
        )
        service._connections["test_conn"] = state
        service._guild_connections["123"] = "test_conn"

        session = VoiceSession(
            session_id="test_session", guild_id="123", channel_id="456", status="active"
        )
        service._sessions["test_session"] = session

        # Clear memory
        result = service.clear_memory()

        assert result is True
        assert len(service._connections) == 0
        assert len(service._guild_connections) == 0
        assert len(service._sessions) == 0
        assert len(service._audio_streams) == 0


class TestIndexOperations:
    """Test search index operations."""

    def test_initialize_indexes(self):
        """Test that indexes are properly initialized."""
        service = VoiceManagerService()

        # Indexes should be initialized in __init__
        assert hasattr(service, "_connections")
        assert hasattr(service, "_guild_connections")
        assert hasattr(service, "_sessions")
        assert hasattr(service, "_audio_streams")
        assert hasattr(service, "_heartbeat_tasks")
        assert hasattr(service, "_timeout_tasks")

        # Verify index structures exist
        assert isinstance(service._connections, dict)
        assert isinstance(service._guild_connections, dict)
        assert isinstance(service._sessions, dict)
        assert isinstance(service._audio_streams, dict)
        assert isinstance(service._heartbeat_tasks, dict)
        assert isinstance(service._timeout_tasks, dict)
