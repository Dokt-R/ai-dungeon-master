"""
Unit tests for Voice Cog.

Tests cover:
- Voice channel joining and leaving commands
- Voice state tracking and monitoring
- Permission validation and caching
- Error handling and recovery scenarios
- Voice connection management
- Discord interaction handling
"""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord import Guild, Member, VoiceChannel, VoiceState
from discord.ext import commands

from packages.bot.cogs.voice_cog import VoiceCog
from packages.bot.services.voice_manager import voice_manager_service
from packages.shared.models import VoiceChannelResponse


class TestVoiceCogInitialization:
    """Test VoiceCog initialization and setup."""

    def test_voice_cog_initialization(self):
        """Test VoiceCog initializes correctly."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        assert cog.bot == bot
        assert cog._voice_clients == {}
        assert cog._permission_cache == {}
        assert cog._cache_timeout == 300

    def test_permission_cache_key_generation(self):
        """Test permission cache key generation."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        cache_key = cog._get_permission_cache_key("123", "456", "789")
        assert cache_key == "123:456:789"


class TestVoiceChannelPermissions:
    """Test voice channel permission handling."""

    def test_get_cached_permissions_valid(self):
        """Test getting valid cached permissions."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        cache_key = "123:456:789"
        cached_perms = {"can_connect": True, "can_speak": False}
        cog._permission_cache[cache_key] = {
            "permissions": cached_perms,
            "timestamp": 1234567890.0,
        }

        with patch.object(cog, "_get_permission_cache_key", return_value=cache_key):
            result = cog._get_cached_permissions(cache_key)
            assert result == cached_perms

    def test_get_cached_permissions_expired(self):
        """Test getting expired cached permissions."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        cache_key = "123:456:789"
        cog._permission_cache[cache_key] = {
            "permissions": {"can_connect": True},
            "timestamp": 0,  # Very old timestamp
        }

        with patch.object(cog, "_get_permission_cache_key", return_value=cache_key):
            result = cog._get_cached_permissions(cache_key)
            assert result is None
            assert cache_key not in cog._permission_cache

    def test_cache_permissions(self):
        """Test caching permissions."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        cache_key = "123:456:789"
        permissions = {"can_connect": True, "can_speak": True}

        with patch("time.time", return_value=1234567890.0):
            cog._cache_permissions(cache_key, permissions)

        assert cache_key in cog._permission_cache
        cached_data = cog._permission_cache[cache_key]
        assert cached_data["permissions"] == permissions
        assert cached_data["timestamp"] == 1234567890.0


class TestVoiceChannelInfo:
    """Test voice channel information retrieval."""

    @pytest.mark.asyncio
    async def test_get_channel_info_success(self):
        """Test getting channel info successfully."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        # Mock voice channel
        channel = MagicMock(spec=VoiceChannel)
        channel.id = 123456
        channel.name = "Test Voice"
        channel.user_limit = 10
        channel.bitrate = 64000
        channel.rtc_region = "us-central"
        channel.members = [MagicMock(), MagicMock()]  # 2 members

        # Mock guild and bot member
        guild = MagicMock(spec=Guild)
        guild.id = 987654
        channel.guild = guild

        bot_member = MagicMock(spec=Member)
        bot_member.id = bot.user.id

        # Mock permissions
        permissions = MagicMock()
        permissions.connect = True
        permissions.speak = True
        permissions.mute_members = False
        permissions.deafen_members = False
        permissions.move_members = False
        permissions.use_voice_activation = True
        permissions.priority_speaker = False

        channel.permissions_for.return_value = permissions

        with (
            patch.object(guild, "get_member", return_value=bot_member),
            patch.object(
                cog,
                "_check_voice_permissions",
                return_value={
                    "can_connect": True,
                    "can_speak": True,
                    "can_mute_members": False,
                    "can_deafen_members": False,
                    "can_move_members": False,
                    "can_use_voice_activity": True,
                    "can_priority_speaker": False,
                },
            ),
        ):
            result = await cog._get_channel_info(channel)

        assert isinstance(result, VoiceChannelResponse)
        assert result.channel_id == "123456"
        assert result.channel_name == "Test Voice"
        assert result.user_limit == 10
        assert result.bitrate == 64000
        assert result.region == "us-central"
        assert result.member_count == 2
        assert result.bot_can_join is True

    @pytest.mark.asyncio
    async def test_get_channel_info_no_bot_member(self):
        """Test getting channel info when bot is not a guild member."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        channel = MagicMock(spec=VoiceChannel)
        guild = MagicMock(spec=Guild)
        channel.guild = guild

        guild.get_member.return_value = None

        with pytest.raises(ValueError, match="Bot is not a member of the guild"):
            await cog._get_channel_info(channel)


class TestVoiceJoinCommand:
    """Test the /voice_join slash command."""

    @pytest.mark.asyncio
    async def test_voice_join_success(self):
        """Test successful voice channel join."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        # Mock interaction
        interaction = AsyncMock()
        interaction.guild_id = 987654
        interaction.user.id = 123456
        interaction.user = MagicMock()
        interaction.guild = MagicMock(spec=Guild)

        # Mock voice channel
        channel = MagicMock(spec=VoiceChannel)
        channel.id = 555666
        channel.name = "Test Voice"

        # Mock permissions
        user_perms = {
            "can_connect": True,
            "can_speak": True,
            "can_mute_members": False,
            "can_deafen_members": False,
            "can_move_members": False,
            "can_use_voice_activity": True,
            "can_priority_speaker": False,
        }

        with (
            patch.object(cog, "_get_channel_info") as mock_get_info,
            patch.object(cog, "_check_voice_permissions", return_value=user_perms),
            patch.object(voice_manager_service, "start_connection") as mock_start,
            patch.object(voice_manager_service, "complete_connection") as mock_complete,
            patch.object(voice_manager_service, "add_participant") as mock_add,
        ):
            # Setup mocks
            mock_get_info.return_value.bot_can_join = True
            mock_start.return_value = MagicMock(connection_id="test_conn_id")
            mock_complete.return_value = MagicMock()

            # Mock Discord voice connection
            mock_voice_client = AsyncMock()
            with patch.object(channel, "connect", return_value=mock_voice_client):
                await cog.voice_join(interaction, channel)

            # Verify calls
            interaction.response.defer.assert_called_once_with(ephemeral=True)
            mock_start.assert_called_once_with(
                guild_id="987654", channel_id="555666", user_id="123456"
            )
            mock_complete.assert_called_once()
            mock_add.assert_called_once()

            # Verify voice client storage
            assert 987654 in cog._voice_clients
            assert cog._voice_clients[987654] == mock_voice_client

            interaction.followup.send.assert_called_once_with(
                "Successfully joined Test Voice! 🎤", ephemeral=True
            )

    @pytest.mark.asyncio
    async def test_voice_join_already_connected(self):
        """Test joining when already connected to a voice channel."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        # Setup existing connection
        existing_client = MagicMock()
        existing_client.is_connected.return_value = True
        cog._voice_clients[987654] = existing_client

        # Mock interaction
        interaction = AsyncMock()
        interaction.guild_id = 987654

        await cog.voice_join(interaction, MagicMock())

        interaction.followup.send.assert_called_once_with(
            "I'm already connected to a voice channel in this server. "
            "Use `/voice_leave` to disconnect first.",
            ephemeral=True,
        )

    @pytest.mark.asyncio
    async def test_voice_join_no_permission(self):
        """Test joining when bot lacks permission."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        interaction = AsyncMock()
        interaction.guild_id = 987654
        interaction.user.id = 123456

        channel = MagicMock(spec=VoiceChannel)

        with patch.object(cog, "_get_channel_info") as mock_get_info:
            mock_get_info.return_value.bot_can_join = False

            await cog.voice_join(interaction, channel)

            interaction.followup.send.assert_called_once_with(
                "I don't have permission to join that voice channel.", ephemeral=True
            )

    @pytest.mark.asyncio
    async def test_voice_join_user_no_permission(self):
        """Test joining when user lacks permission."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        interaction = AsyncMock()
        interaction.guild_id = 987654
        interaction.user.id = 123456

        channel = MagicMock(spec=VoiceChannel)

        with (
            patch.object(cog, "_get_channel_info") as mock_get_info,
            patch.object(
                cog, "_check_voice_permissions", return_value={"can_connect": False}
            ),
        ):
            mock_get_info.return_value.bot_can_join = True

            await cog.voice_join(interaction, channel)

            interaction.followup.send.assert_called_once_with(
                "You don't have permission to connect to that voice channel.",
                ephemeral=True,
            )


class TestVoiceLeaveCommand:
    """Test the /voice_leave slash command."""

    @pytest.mark.asyncio
    async def test_voice_leave_success(self):
        """Test successful voice channel leave."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        # Setup existing connection
        mock_voice_client = AsyncMock()
        cog._voice_clients[987654] = mock_voice_client

        # Mock interaction
        interaction = AsyncMock()
        interaction.guild_id = 987654
        interaction.user.id = 123456

        with (
            patch.object(voice_manager_service, "get_guild_connection") as mock_get,
            patch.object(
                voice_manager_service, "disconnect_connection"
            ) as mock_disconnect,
        ):
            mock_get.return_value = MagicMock(connection_id="test_conn_id")

            await cog.voice_leave(interaction, MagicMock())

            # Verify service calls
            mock_disconnect.assert_called_once_with(
                connection_id="test_conn_id", reason="user_request", user_id="123456"
            )

            # Verify Discord disconnect
            mock_voice_client.disconnect.assert_called_once()

            # Verify cleanup
            assert 987654 not in cog._voice_clients

            interaction.followup.send.assert_called_once_with(
                "Successfully left the voice channel! 👋", ephemeral=True
            )

    @pytest.mark.asyncio
    async def test_voice_leave_not_connected(self):
        """Test leaving when not connected to voice."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        interaction = AsyncMock()
        interaction.guild_id = 987654

        await cog.voice_leave(interaction, MagicMock())

        interaction.followup.send.assert_called_once_with(
            "I'm not currently connected to a voice channel in this server.",
            ephemeral=True,
        )


class TestVoiceStatusCommand:
    """Test the /voice_status slash command."""

    @pytest.mark.asyncio
    async def test_voice_status_connected(self):
        """Test voice status when connected."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        interaction = AsyncMock()
        interaction.guild_id = 987654
        interaction.guild = MagicMock(spec=Guild)

        # Mock status response
        status_response = MagicMock()
        status_response.connected = True
        status_response.channel_id = "555666"
        status_response.participant_count = 2
        status_response.participants = ["123", "456"]
        status_response.connected_at = 1234567890.0

        # Mock channel
        channel = MagicMock(spec=VoiceChannel)
        channel.name = "Test Voice"
        interaction.guild.get_channel.return_value = channel

        with patch.object(
            voice_manager_service, "get_connection_status", return_value=status_response
        ):
            await cog.voice_status(interaction)

            # Verify embed creation
            args, kwargs = interaction.followup.send.call_args
            assert "embed" in kwargs
            embed = kwargs["embed"]
            assert isinstance(embed, discord.Embed)
            assert embed.title == "Voice Connection Status"

    @pytest.mark.asyncio
    async def test_voice_status_not_connected(self):
        """Test voice status when not connected."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        interaction = AsyncMock()
        interaction.guild_id = 987654

        with patch.object(
            voice_manager_service, "get_connection_status", return_value=None
        ):
            await cog.voice_status(interaction)

            interaction.followup.send.assert_called_once_with(
                "I'm not currently connected to a voice channel in this server.",
                ephemeral=True,
            )


class TestVoiceStateUpdate:
    """Test voice state update handling."""

    @pytest.mark.asyncio
    async def test_user_join_voice_channel(self):
        """Test handling user joining voice channel."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        # Mock voice states
        before = MagicMock(spec=VoiceState)
        before.channel = None

        after = MagicMock(spec=VoiceState)
        after.channel = MagicMock(spec=VoiceChannel)
        after.channel.id = 555666

        member = MagicMock(spec=Member)
        member.guild.id = 987654
        member.id = 123456

        # Mock connection
        connection = MagicMock()
        connection.channel_id = "555666"

        with (
            patch.object(
                voice_manager_service, "get_guild_connection", return_value=connection
            ),
            patch.object(voice_manager_service, "add_participant") as mock_add,
        ):
            await cog.on_voice_state_update(member, before, after)

            mock_add.assert_called_once_with(
                connection_id=connection.connection_id, user_id="123456"
            )

    @pytest.mark.asyncio
    async def test_user_leave_voice_channel(self):
        """Test handling user leaving voice channel."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        # Mock voice states
        before = MagicMock(spec=VoiceState)
        before.channel = MagicMock(spec=VoiceChannel)
        before.channel.id = 555666

        after = MagicMock(spec=VoiceState)
        after.channel = None

        member = MagicMock(spec=Member)
        member.guild.id = 987654
        member.id = 123456

        # Mock connection
        connection = MagicMock()
        connection.channel_id = "555666"

        with (
            patch.object(
                voice_manager_service, "get_guild_connection", return_value=connection
            ),
            patch.object(voice_manager_service, "remove_participant") as mock_remove,
        ):
            await cog.on_voice_state_update(member, before, after)

            mock_remove.assert_called_once_with(
                connection_id=connection.connection_id, user_id="123456"
            )

    @pytest.mark.asyncio
    async def test_bot_voice_state_change_ignored(self):
        """Test that bot's own voice state changes are ignored."""
        bot = MagicMock(spec=commands.Bot)
        bot.user.id = 987654
        cog = VoiceCog(bot)

        member = MagicMock(spec=Member)
        member.id = 987654  # Bot's ID

        # Should not call any service methods
        with patch.object(voice_manager_service, "get_guild_connection") as mock_get:
            await cog.on_voice_state_update(member, MagicMock(), MagicMock())

            mock_get.assert_not_called()


class TestVoiceClientError:
    """Test voice client error handling."""

    @pytest.mark.asyncio
    async def test_voice_client_error_handled(self):
        """Test voice client error is properly handled."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        # Mock voice client and error
        voice_client = MagicMock()
        voice_client.guild.id = 987654

        error = Exception("Connection failed")

        # Mock connection
        connection = MagicMock()
        connection.connection_id = "test_conn_id"

        with (
            patch.object(
                voice_manager_service, "get_guild_connection", return_value=connection
            ),
            patch.object(
                voice_manager_service, "handle_connection_error"
            ) as mock_handle,
        ):
            await cog.on_voice_client_error(voice_client, error)

            mock_handle.assert_called_once_with(
                connection_id="test_conn_id",
                error="Connection failed",
                user_id="discord_voice_client",
            )


class TestCogLifecycle:
    """Test cog lifecycle methods."""

    @pytest.mark.asyncio
    async def test_cog_unload(self):
        """Test cog unload cleans up resources."""
        bot = MagicMock(spec=commands.Bot)
        cog = VoiceCog(bot)

        # Setup voice clients
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        cog._voice_clients = {123: mock_client1, 456: mock_client2}

        # Mock connections
        with (
            patch.object(voice_manager_service, "get_guild_connection") as mock_get,
            patch.object(
                voice_manager_service, "disconnect_connection"
            ) as mock_disconnect,
        ):
            mock_get.side_effect = [
                MagicMock(connection_id="conn_123"),
                MagicMock(connection_id="conn_456"),
            ]

            await cog.cog_unload()

            # Verify disconnect calls
            assert mock_disconnect.call_count == 2

            # Verify voice client disconnects
            mock_client1.disconnect.assert_called_once()
            mock_client2.disconnect.assert_called_once()

            # Verify cleanup
            assert cog._voice_clients == {}


class TestSetupFunction:
    """Test the setup function for the cog."""

    @pytest.mark.asyncio
    async def test_setup_function(self):
        """Test setup function adds cog correctly."""
        bot = MagicMock(spec=commands.Bot)

        # Import the setup function
        from packages.bot.cogs.voice_cog import setup

        await setup(bot)

        bot.add_cog.assert_called_once()
        args, kwargs = bot.add_cog.call_args
        assert isinstance(args[0], VoiceCog)
        assert args[0].bot == bot
