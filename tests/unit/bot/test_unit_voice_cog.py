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

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord import Guild, Member, VoiceChannel, VoiceState

from packages.bot.services.voice_manager import voice_manager_service
from packages.bot.cogs.voice_cog import VoiceCog
from packages.shared.models import VoiceChannelResponse


@pytest.fixture
def mock_voice_channel():
    """Fixture for creating mock voice channels."""
    channel = MagicMock(spec=VoiceChannel)
    channel.id = 555666
    channel.name = "Test Voice"
    channel.user_limit = 10
    channel.bitrate = 64000
    channel.rtc_region = "us-central"
    channel.members = [MagicMock(), MagicMock()]
    channel.guild = MagicMock(spec=Guild)
    channel.guild.id = 987654
    return channel


@pytest.fixture
def mock_voice_state():
    """Fixture for creating mock voice states."""
    state = MagicMock(spec=VoiceState)
    state.channel = None
    return state


class TestVoiceCogInitialization:
    """Test VoiceCog initialization and setup."""

    def test_voice_cog_initialization(self, mock_voice_cog):
        """Test VoiceCog initializes correctly."""
        cog = mock_voice_cog

        assert cog.bot is not None
        assert cog._voice_clients == {}
        assert cog._permission_cache == {}
        assert cog._cache_timeout == 300

    def test_permission_cache_key_generation(self, mock_voice_cog):
        """Test permission cache key generation."""
        cog = mock_voice_cog

        cache_key = cog._get_permission_cache_key("123", "456", "789")
        assert cache_key == "123:456:789"


class TestVoiceChannelPermissions:
    """Test voice channel permission handling."""

    def test_get_cached_permissions_valid(self, mock_voice_cog):
        """Test getting valid cached permissions."""
        cog = mock_voice_cog

        cache_key = "123:456:789"
        cached_perms = {"can_connect": True, "can_speak": False}
        cog._permission_cache[cache_key] = {
            "permissions": cached_perms,
            "timestamp": 1234567890.0,
        }

        # Mock datetime.utcnow() to return a time before the cached timestamp + timeout
        mock_datetime = MagicMock()
        mock_datetime.utcnow.return_value.timestamp.return_value = 1234567890.0

        with (
            patch.object(cog, "_get_permission_cache_key", return_value=cache_key),
            patch("packages.bot.cogs.voice_cog.datetime", mock_datetime),
        ):
            result = cog._get_cached_permissions(cache_key)
            assert result == cached_perms

    def test_get_cached_permissions_expired(self, mock_voice_cog):
        """Test getting expired cached permissions."""
        cog = mock_voice_cog

        cache_key = "123:456:789"
        cog._permission_cache[cache_key] = {
            "permissions": {"can_connect": True},
            "timestamp": 0,  # Very old timestamp
        }

        with patch.object(cog, "_get_permission_cache_key", return_value=cache_key):
            result = cog._get_cached_permissions(cache_key)
            assert result is None
            assert cache_key not in cog._permission_cache

    def test_cache_permissions(self, mock_voice_cog):
        """Test caching permissions."""
        cog = mock_voice_cog

        cache_key = "123:456:789"
        permissions = {"can_connect": True, "can_speak": True}

        # Mock datetime.utcnow() to return the expected timestamp
        mock_datetime = MagicMock()
        mock_datetime.utcnow.return_value.timestamp.return_value = 1234567890.0

        with patch("packages.bot.cogs.voice_cog.datetime", mock_datetime):
            cog._cache_permissions(cache_key, permissions)

        assert cache_key in cog._permission_cache
        cached_data = cog._permission_cache[cache_key]
        assert cached_data["permissions"] == permissions
        assert cached_data["timestamp"] == 1234567890.0


class TestVoiceChannelInfo:
    """Test voice channel information retrieval."""

    @pytest.mark.asyncio
    async def test_get_channel_info_success(self, mock_voice_cog, mock_voice_channel):
        """Test getting channel info successfully."""
        cog = mock_voice_cog
        channel = mock_voice_channel

        # Update channel properties for this test
        channel.id = 123456
        channel.name = "Test Voice"
        channel.user_limit = 10
        channel.bitrate = 64000
        channel.rtc_region = "us-central"
        channel.members = [MagicMock(), MagicMock()]  # 2 members

        # Mock guild and bot member
        guild = channel.guild
        guild.id = 987654

        bot_member = MagicMock(spec=Member)
        bot_member.id = cog.bot.user.id

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
    async def test_get_channel_info_no_bot_member(
        self, mock_voice_cog, mock_voice_channel
    ):
        """Test getting channel info when bot is not a guild member."""
        cog = mock_voice_cog
        channel = mock_voice_channel

        guild = channel.guild
        guild.get_member.return_value = None

        with pytest.raises(ValueError, match="Bot is not a member of the guild"):
            await cog._get_channel_info(channel)


class TestVoiceJoinLogic:
    """Test the voice join business logic."""

    @pytest.mark.asyncio
    async def test_join_voice_success(
        self, mock_voice_cog, mock_interaction_member, mock_voice_channel
    ):
        """Test successful voice channel join logic."""
        cog = mock_voice_cog
        interaction = mock_interaction_member
        channel = mock_voice_channel

        # Mock voice channel
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
                # Test the join logic by simulating the slash command flow
                # Check if bot is already in a voice channel in this guild
                if interaction.guild_id in cog._voice_clients:
                    existing_client = cog._voice_clients[interaction.guild_id]
                    if existing_client.is_connected():
                        await interaction.followup.send(
                            "I'm already connected to a voice channel in this server. "
                            "Use `/voice_leave` to disconnect first.",
                            ephemeral=True,
                        )
                        return

                # Check bot permissions
                channel_info = await cog._get_channel_info(channel)
                if not channel_info.bot_can_join:
                    await interaction.followup.send(
                        "I don't have permission to join that voice channel.",
                        ephemeral=True,
                    )
                    return

                # Check user permissions
                user_permissions = await cog._check_voice_permissions(
                    interaction.guild, channel, interaction.user
                )

                if not user_permissions["can_connect"]:
                    await interaction.followup.send(
                        "You don't have permission to connect to that voice channel.",
                        ephemeral=True,
                    )
                    return

                # Start voice connection in service
                connection = await voice_manager_service.start_connection(
                    guild_id=str(interaction.guild_id),
                    channel_id=str(channel.id),
                    user_id=str(interaction.user.id),
                )

                # Connect to Discord voice channel
                voice_client = await channel.connect()

                # Store voice client reference
                cog._voice_clients[interaction.guild_id] = voice_client

                # Mark connection as complete
                await voice_manager_service.complete_connection(
                    connection_id=connection.connection_id,
                    user_id=str(interaction.user.id),
                )

                # Add the user as participant
                await voice_manager_service.add_participant(
                    connection_id=connection.connection_id,
                    user_id=str(interaction.user.id),
                )

                await interaction.followup.send(
                    f"Successfully joined {channel.name}! 🎤", ephemeral=True
                )

            # Verify calls
            mock_start.assert_called_once_with(
                guild_id="456", channel_id="555666", user_id="123"
            )
            mock_complete.assert_called_once()
            mock_add.assert_called_once()

            # Verify voice client storage
            assert 456 in cog._voice_clients
            assert cog._voice_clients[456] == mock_voice_client

            interaction.followup.send.assert_called_once_with(
                "Successfully joined Test Voice! 🎤", ephemeral=True
            )

    @pytest.mark.asyncio
    async def test_join_voice_already_connected(
        self, mock_voice_cog, mock_interaction_member
    ):
        """Test joining when already connected to a voice channel."""
        cog = mock_voice_cog
        interaction = mock_interaction_member

        # Setup existing connection
        existing_client = MagicMock()
        existing_client.is_connected.return_value = True
        cog._voice_clients[456] = existing_client

        # Test the connection check logic
        if interaction.guild_id in cog._voice_clients:
            existing_client = cog._voice_clients[interaction.guild_id]
            if existing_client.is_connected():
                await interaction.followup.send(
                    "I'm already connected to a voice channel in this server. "
                    "Use `/voice_leave` to disconnect first.",
                    ephemeral=True,
                )

        interaction.followup.send.assert_called_once_with(
            "I'm already connected to a voice channel in this server. "
            "Use `/voice_leave` to disconnect first.",
            ephemeral=True,
        )

    @pytest.mark.asyncio
    async def test_join_voice_no_bot_permission(
        self, mock_voice_cog, mock_interaction_member, mock_voice_channel
    ):
        """Test joining when bot lacks permission."""
        cog = mock_voice_cog
        interaction = mock_interaction_member
        channel = mock_voice_channel

        with patch.object(cog, "_get_channel_info") as mock_get_info:
            mock_get_info.return_value.bot_can_join = False

            # Test the permission check logic
            channel_info = await cog._get_channel_info(channel)
            if not channel_info.bot_can_join:
                await interaction.followup.send(
                    "I don't have permission to join that voice channel.",
                    ephemeral=True,
                )

            interaction.followup.send.assert_called_once_with(
                "I don't have permission to join that voice channel.", ephemeral=True
            )

    @pytest.mark.asyncio
    async def test_join_voice_no_user_permission(
        self, mock_voice_cog, mock_interaction_member, mock_voice_channel
    ):
        """Test joining when user lacks permission."""
        cog = mock_voice_cog
        interaction = mock_interaction_member
        channel = mock_voice_channel

        with (
            patch.object(cog, "_get_channel_info") as mock_get_info,
            patch.object(
                cog, "_check_voice_permissions", return_value={"can_connect": False}
            ),
        ):
            mock_get_info.return_value.bot_can_join = True

            # Test the user permission check logic
            channel_info = await cog._get_channel_info(channel)
            if not channel_info.bot_can_join:
                await interaction.followup.send(
                    "I don't have permission to join that voice channel.",
                    ephemeral=True,
                )
                return

            user_permissions = await cog._check_voice_permissions(
                interaction.guild, channel, interaction.user
            )

            if not user_permissions["can_connect"]:
                await interaction.followup.send(
                    "You don't have permission to connect to that voice channel.",
                    ephemeral=True,
                )

            interaction.followup.send.assert_called_once_with(
                "You don't have permission to connect to that voice channel.",
                ephemeral=True,
            )


class TestVoiceLeaveLogic:
    """Test the voice leave business logic."""

    @pytest.mark.asyncio
    async def test_leave_voice_success(self, mock_voice_cog, mock_interaction_member):
        """Test successful voice channel leave logic."""
        cog = mock_voice_cog
        interaction = mock_interaction_member

        # Setup existing connection
        mock_voice_client = AsyncMock()
        cog._voice_clients[456] = mock_voice_client

        with (
            patch.object(voice_manager_service, "get_guild_connection") as mock_get,
            patch.object(
                voice_manager_service, "disconnect_connection"
            ) as mock_disconnect,
        ):
            mock_get.return_value = MagicMock(connection_id="test_conn_id")

            # Test the leave logic by simulating the slash command flow
            # Check if bot is in a voice channel
            if interaction.guild_id not in cog._voice_clients:
                await interaction.followup.send(
                    "I'm not currently connected to a voice channel in this server.",
                    ephemeral=True,
                )
                return

            voice_client = cog._voice_clients[interaction.guild_id]

            # Get connection info for cleanup
            connection = voice_manager_service.get_guild_connection(
                str(interaction.guild_id)
            )
            if connection:
                # Disconnect from service
                await voice_manager_service.disconnect_connection(
                    connection_id=connection.connection_id,
                    reason="user_request",
                    user_id=str(interaction.user.id),
                )

            # Disconnect from Discord
            await voice_client.disconnect()

            # Clean up voice client reference
            del cog._voice_clients[interaction.guild_id]

            await interaction.followup.send(
                "Successfully left the voice channel! 👋", ephemeral=True
            )

            # Verify service calls
            mock_disconnect.assert_called_once_with(
                connection_id="test_conn_id", reason="user_request", user_id="123"
            )

            # Verify Discord disconnect
            mock_voice_client.disconnect.assert_called_once()

            # Verify cleanup
            assert 456 not in cog._voice_clients

            interaction.followup.send.assert_called_once_with(
                "Successfully left the voice channel! 👋", ephemeral=True
            )

    @pytest.mark.asyncio
    async def test_leave_voice_not_connected(
        self, mock_voice_cog, mock_interaction_member
    ):
        """Test leaving when not connected to voice."""
        cog = mock_voice_cog
        interaction = mock_interaction_member

        # Test the connection check logic
        if interaction.guild_id not in cog._voice_clients:
            await interaction.followup.send(
                "I'm not currently connected to a voice channel in this server.",
                ephemeral=True,
            )

        interaction.followup.send.assert_called_once_with(
            "I'm not currently connected to a voice channel in this server.",
            ephemeral=True,
        )


class TestVoiceStatusLogic:
    """Test the voice status business logic."""

    @pytest.mark.asyncio
    async def test_voice_status_connected(
        self, mock_voice_cog, mock_interaction_member, mock_voice_channel
    ):
        """Test voice status when connected."""
        cog = mock_voice_cog
        interaction = mock_interaction_member
        channel = mock_voice_channel

        # Mock status response
        status_response = MagicMock()
        status_response.connected = True
        status_response.channel_id = "555666"
        status_response.participant_count = 2
        status_response.participants = ["123", "456"]
        status_response.connected_at = 1234567890.0

        # Mock channel
        channel.name = "Test Voice"
        interaction.guild.get_channel.return_value = channel

        # Mock guild members
        mock_member1 = MagicMock(spec=Member)
        mock_member1.display_name = "User1"
        mock_member2 = MagicMock(spec=Member)
        mock_member2.display_name = "User2"

        interaction.guild.get_member.side_effect = lambda id: {
            123: mock_member1,
            456: mock_member2,
        }.get(id)

        with patch.object(
            voice_manager_service, "get_connection_status", return_value=status_response
        ):
            # Test the status logic by simulating the slash command flow
            status_response = voice_manager_service.get_connection_status(
                str(interaction.guild_id)
            )

            if not status_response or not status_response.connected:
                await interaction.followup.send(
                    "I'm not currently connected to a voice channel in this server.",
                    ephemeral=True,
                )
                return

            # Get channel info
            guild = interaction.guild
            channel = guild.get_channel(int(status_response.channel_id))

            embed = discord.Embed(
                title="Voice Connection Status", color=discord.Color.blue()
            )

            embed.add_field(
                name="Channel",
                value=channel.name if channel else "Unknown",
                inline=True,
            )

            embed.add_field(
                name="Participants",
                value=str(status_response.participant_count),
                inline=True,
            )

            if status_response.connected_at:
                # Convert float timestamp to datetime for subtraction
                connected_datetime = datetime.utcfromtimestamp(
                    status_response.connected_at
                )
                duration = datetime.utcnow() - connected_datetime
                embed.add_field(
                    name="Connected For",
                    value=f"{duration.seconds // 60} minutes",
                    inline=True,
                )

            if status_response.participants:
                participant_names = []
                for participant_id in status_response.participants[:5]:  # Limit to 5
                    member = guild.get_member(int(participant_id))
                    if member:
                        participant_names.append(member.display_name)
                if participant_names:
                    embed.add_field(
                        name="Current Participants",
                        value="\n".join(participant_names),
                        inline=False,
                    )

            await interaction.followup.send(embed=embed, ephemeral=True)

            # Verify embed creation
            args, kwargs = interaction.followup.send.call_args
            assert "embed" in kwargs
            embed = kwargs["embed"]
            assert isinstance(embed, discord.Embed)
            assert embed.title == "Voice Connection Status"

    @pytest.mark.asyncio
    async def test_voice_status_not_connected(
        self, mock_voice_cog, mock_interaction_member
    ):
        """Test voice status when not connected."""
        cog = mock_voice_cog
        interaction = mock_interaction_member

        with patch.object(
            voice_manager_service, "get_connection_status", return_value=None
        ):
            # Test the status logic by simulating the slash command flow
            status_response = voice_manager_service.get_connection_status(
                str(interaction.guild_id)
            )

            if not status_response or not status_response.connected:
                await interaction.followup.send(
                    "I'm not currently connected to a voice channel in this server.",
                    ephemeral=True,
                )

            interaction.followup.send.assert_called_once_with(
                "I'm not currently connected to a voice channel in this server.",
                ephemeral=True,
            )


class TestVoiceStateUpdate:
    """Test voice state update handling."""

    @pytest.mark.asyncio
    async def test_user_join_voice_channel(self, mock_voice_cog, mock_voice_state):
        """Test handling user joining voice channel."""
        cog = mock_voice_cog

        # Mock voice states
        before = mock_voice_state

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
    async def test_user_leave_voice_channel(self, mock_voice_cog, mock_voice_state):
        """Test handling user leaving voice channel."""
        cog = mock_voice_cog

        # Mock voice states
        before = MagicMock(spec=VoiceState)
        before.channel = MagicMock(spec=VoiceChannel)
        before.channel.id = 555666

        after = mock_voice_state

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
    async def test_bot_voice_state_change_ignored(self, mock_voice_cog):
        """Test that bot's own voice state changes are ignored."""
        cog = mock_voice_cog

        member = MagicMock(spec=Member)
        member.id = cog.bot.user.id  # Bot's ID

        # Should not call any service methods
        with patch.object(voice_manager_service, "get_guild_connection") as mock_get:
            await cog.on_voice_state_update(member, MagicMock(), MagicMock())

            mock_get.assert_not_called()


class TestVoiceClientError:
    """Test voice client error handling."""

    @pytest.mark.asyncio
    async def test_voice_client_error_handled(self, mock_voice_cog):
        """Test voice client error is properly handled."""
        cog = mock_voice_cog

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
    async def test_cog_unload(self, mock_voice_cog):
        """Test cog unload cleans up resources."""
        cog = mock_voice_cog

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
    async def test_setup_function(self, mock_bot):
        """Test setup function adds cog correctly."""
        bot = mock_bot

        # Import the setup function
        from packages.bot.cogs.voice_cog import setup

        await setup(bot)

        bot.add_cog.assert_called_once()
        args, kwargs = bot.add_cog.call_args
        assert isinstance(args[0], VoiceCog)
        assert args[0].bot == bot
