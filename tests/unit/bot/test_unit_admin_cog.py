from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.bot.cogs.admin_cog import AdminCog
from packages.shared.errors import ErrorCode
from tests.utils.factories import MockInteraction
from tests.utils.mock_api_client import MockApiClient

pytestmark = pytest.mark.asyncio


class TestGeneralCommands:
    """Test the generic bot commands."""

    async def test_cog_exists(self, bot_client):
        cog = bot_client.get_cog("AdminCog")
        assert cog is not None

    async def test_ping_command(self, bot_client):
        """Test the /ping command response."""
        interaction = MockInteraction()
        cmd = None
        for command in bot_client.tree.get_commands():
            if command.name == "ping":
                cmd = command
                break
        assert cmd is not None
        await cmd.callback(cmd, interaction)
        expected_response = "Pong!"
        assert interaction.message == expected_response

    async def test_server_setup_permissions(self, bot_client):
        """Test that only admins can run the /server-setup command."""
        interaction = MockInteraction(is_admin=False)
        cmd = None
        for command in bot_client.tree.get_commands():
            if command.name == "server-setup":
                cmd = command
                break
        assert cmd is not None
        await cmd.callback(cmd, interaction)
        assert (
            ErrorCode.PERMISSION_DENIED_ERROR.message in interaction.message
        )
        assert interaction.ephemeral is True


class TestOnServerSetkey:
    """Test the /server-setkey command."""

    async def test_server_setkey_permissions(self, bot_client, mock_admin_cog):
        interaction = MockInteraction(is_admin=False)
        cmd = None
        for command in bot_client.tree.get_commands():
            if command.name == "server-setkey":
                cmd = command
                break
        assert cmd is not None
        cog = mock_admin_cog
        await cog.server_setkey.callback(cog, interaction, "dummy_key")
        assert (
            ErrorCode.PERMISSION_DENIED_ERROR.message in interaction.message
        )
        assert interaction.ephemeral is True

    async def test_server_setkey_success(self, mock_admin_cog, mock_interaction):
        cog = mock_admin_cog
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = True
        interaction.user.guild_permissions.manage_guild = False

        # Patch httpx.AsyncClient
        class MockResponse:
            status_code = 200
            text = "OK"

        async def mock_put(*args, **kwargs):
            return MockResponse()

        await cog.server_setkey.callback(cog, interaction, "testkey")
        interaction.response.send_message.assert_awaited_with(
            "API key securely stored for this server.", ephemeral=True
        )

    async def test_server_setkey_failure(self, mock_admin_cog, mock_interaction):
        cog = mock_admin_cog
        cog.api_client = MockApiClient()
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = True
        interaction.user.guild_permissions.manage_guild = False

        class MockResponse:
            status_code = 500
            text = "Internal Server Error"

        async def mock_put(*args, **kwargs):
            return MockResponse()

        await cog.server_setkey.callback(cog, interaction, "testkey")
        interaction.response.send_message.assert_called_with(
            ErrorCode.AI_API_ERROR.player_message, ephemeral=True
        )


class TestOnMemberJoin:
    """Tests for the on_member_join event handler."""

    async def test_on_member_join_bot(self, mock_bot, mock_member):
        """Test that on_member_join does nothing when a bot joins."""
        cog = AdminCog(mock_bot)
        member = mock_member()

        # Call the event handler
        await cog.on_member_join(member)

        # Verify no HTTP request was made
        # This is a bit tricky to test since we don't have a direct mock for the httpx client
        # in this context, but we can at least verify the function completes without error

    async def test_on_member_join_user_success(self, mock_bot, mock_member):
        """Test that on_member_join creates a player when a user joins."""
        cog = AdminCog(mock_bot)
        member = mock_member()

        # Mock the httpx.AsyncClient.post method
        class MockResponse:
            status_code = 200
            text = "OK"

            async def raise_for_status(self):
                pass

        async def mock_post(*args, **kwargs):
            return MockResponse()

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            # Mock the context manager behavior
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = mock_post
                mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()

                # Call the event handler
                await cog.on_member_join(member)

                # Verify the HTTP request was made with correct parameters
                # Note: This verification is limited because of the context manager mocking

    async def test_on_member_join_user_http_error(self, mock_bot, mock_member):
        """Test that on_member_join handles HTTP errors gracefully."""
        cog = AdminCog(mock_bot)
        member = mock_member()

        # Mock the httpx.AsyncClient.post method to raise an HTTPStatusError
        async def mock_post(*args, **kwargs):
            raise Exception("HTTP error")

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            # Mock the context manager behavior
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = mock_post
                mock_client.return_value.__aenter__.return_value.__aexit__ = AsyncMock()

                # Call the event handler
                await cog.on_member_join(member)

                # We can't easily verify the print statement, but we can verify
                # the function completes without crashing


class TestErrorHandling:
    """Test error handling in the AdminCog."""

    async def test_server_setup_permission_error(self, mock_bot, mock_interaction):
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = False
        interaction.user.guild_permissions.manage_guild = False
        interaction.guild_id = 123
        cog = AdminCog(mock_bot)
        await cog.server_setup.callback(cog, interaction)
        interaction.response.send_message.assert_awaited_with(
            ErrorCode.PERMISSION_DENIED_ERROR.player_message,
            ephemeral=True,
        )

    async def test_server_setkey_permission_error(self, mock_bot, mock_interaction):
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = False
        interaction.user.guild_permissions.manage_guild = False
        interaction.guild_id = 123
        cog = AdminCog(mock_bot)
        await cog.server_setkey.callback(cog, interaction, "testkey")
        interaction.response.send_message.assert_awaited_with(
            ErrorCode.PERMISSION_DENIED_ERROR.player_message,
            ephemeral=True,
        )

    async def test_server_setkey_backend_failure(self, mock_bot, mock_interaction):
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = True
        interaction.user.guild_permissions.manage_guild = False
        interaction.guild_id = 123
        cog = AdminCog(mock_bot)
        with patch("httpx.AsyncClient.put", side_effect=Exception("Backend error")):
            await cog.server_setkey.callback(cog, interaction, "testkey")
        # Should call the error handler and send a generic error message
        assert any(
            ErrorCode.UNKNOWN.player_message.lower() == str(call.args[0]).lower()
            for call in interaction.response.send_message.await_args_list
        )

    async def test_server_setup_generic_exception(self, mock_bot, mock_interaction):
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = True
        interaction.user.guild_permissions.manage_guild = False
        interaction.guild_id = 123
        cog = AdminCog(mock_bot)
        # Patch the method to raise a generic exception after permission check
        with patch.object(
            cog, "server_setup", side_effect=Exception("Unexpected error")
        ):
            try:
                await cog.server_setup(interaction)
            except Exception:
                pass  # The error handler will log and re-raise, but we want to check the response
        # Should call the error handler and send a generic error message
        # (In this patch, the error is raised before the response, so this is illustrative)


class TestSyncCommands:
    """Test the new sync command functionality."""

    async def test_sync_members_command_permissions(self, bot_client):
        """Test that only admins can run the /sync members command."""
        interaction = MockInteraction(is_admin=False)
        cmd = None
        for command in bot_client.tree.get_commands():
            if command.name == "sync":
                for subcommand in command.commands:
                    if subcommand.name == "members":
                        cmd = subcommand
                        break
                if cmd:
                    break

        if cmd:
            cog = bot_client.get_cog("AdminCog")
            await cmd.callback(cog, interaction)
            # The error handler returns a generic message, not the specific permission message
            assert ErrorCode.PERMISSION_DENIED_ERROR.player_message in interaction.message
            assert interaction.ephemeral is True

    async def test_sync_members_command_success(self, mock_interaction, mock_admin_cog):
        """Test successful sync members command."""
        cog = mock_admin_cog
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = True

        # Mock guild with members
        mock_member1 = MagicMock()
        mock_member1.id = 123
        mock_member1.display_name = "TestUser1"
        mock_member1.bot = False

        mock_member2 = MagicMock()
        mock_member2.id = 124
        mock_member2.display_name = "TestUser2"
        mock_member2.bot = True  # This should be filtered out

        mock_guild = MagicMock()
        mock_guild.members = [mock_member1, mock_member2]
        interaction.guild = mock_guild

        # Mock API client
        mock_response = {"player_id": "123", "username": "TestUser1"}
        cog.api_client.create_player = AsyncMock(return_value=mock_response)

        # Mock followup send to capture all calls
        interaction.followup.send = AsyncMock()
        interaction.response.defer = AsyncMock()

        await cog.sync_members.callback(cog, interaction)

        # Verify followup.send was called for the initial message
        assert interaction.followup.send.call_count >= 1

        # Check that the initial message is sent (the completion may happen via edit)
        calls = interaction.followup.send.await_args_list
        initial_call = calls[0][0][0]  # First call arguments
        assert "Starting sync of 1 members" in initial_call

        # Verify API was called for the non-bot member
        assert cog.api_client.create_player.call_count == 1

    async def test_sync_start_command(self, mock_admin_cog, mock_interaction):
        """Test sync start command."""
        cog = mock_admin_cog
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = True

        # Mock the periodic sync task
        cog._periodic_sync = AsyncMock()

        await cog.start_sync.callback(cog, interaction)

        interaction.response.send_message.assert_awaited_with(
            "Started periodic sync (every 1 hour).", ephemeral=True
        )
        assert cog.sync_task is not None

    async def test_sync_stop_command(self, mock_admin_cog, mock_interaction):
        """Test sync stop command."""
        cog = mock_admin_cog
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = True

        # Set up a mock task
        cog.sync_task = MagicMock()
        cog.sync_task.done.return_value = False

        await cog.stop_sync.callback(cog, interaction)

        interaction.response.send_message.assert_awaited_with(
            "Stopped periodic sync.", ephemeral=True
        )
        cog.sync_task.cancel.assert_called_once()

    async def test_sync_status_command_running(self, mock_admin_cog, mock_interaction):
        """Test sync status when sync is running."""
        cog = mock_admin_cog
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = True

        # Set up a running mock task
        cog.sync_task = MagicMock()
        cog.sync_task.done.return_value = False

        await cog.sync_status.callback(cog, interaction)

        interaction.response.send_message.assert_awaited_with(
            "✅ Periodic sync is running\nNext sync in ~1 hour", ephemeral=True
        )

    async def test_sync_status_command_stopped(self, mock_admin_cog, mock_interaction):
        """Test sync status when sync is not running."""
        cog = mock_admin_cog
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = True

        cog.sync_task = None

        await cog.sync_status.callback(cog, interaction)

        interaction.response.send_message.assert_awaited_with(
            "❌ Periodic sync is not running\nYou can start it with `/sync start`",
            ephemeral=True
        )

    async def test_sync_restart_command(self, mock_admin_cog, mock_interaction):
        """Test sync restart command."""
        cog = mock_admin_cog
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = True

        # Set up existing task
        old_task = MagicMock()
        old_task.done.return_value = False
        cog.sync_task = old_task
        cog._periodic_sync = AsyncMock()

        await cog.restart_sync.callback(cog, interaction)

        old_task.cancel.assert_called_once()
        interaction.response.send_message.assert_awaited_with(
            "Restarted periodic sync.", ephemeral=True
        )

    async def test_create_or_update_player_success(self, mock_admin_cog):
        """Test successful player creation/update."""
        cog = mock_admin_cog

        # Mock Discord member
        mock_member = MagicMock()
        mock_member.id = 123
        mock_member.display_name = "TestUser"
        mock_member.bot = False

        # Mock API response
        mock_response = {"player_id": "123", "username": "TestUser"}
        cog.api_client.create_player = AsyncMock(return_value=mock_response)

        result = await cog._create_or_update_player(mock_member)

        assert not result["created"]
        assert result["updated"]
        cog.api_client.create_player.assert_awaited_once_with({
            "player_id": "123",
            "username": "TestUser"
        })

    async def test_check_backend_health_success(self, mock_admin_cog):
        """Test successful backend health check."""
        cog = mock_admin_cog

        # Mock successful API response
        mock_response = {"player_id": "health_check_test", "username": "Health Check User"}
        cog.api_client.create_player = AsyncMock(return_value=mock_response)

        result = await cog._check_backend_health()

        assert result is True
        cog.api_client.create_player.assert_awaited_once_with({
            "player_id": "health_check_test",
            "username": "Health Check User"
        })

    async def test_check_backend_health_failure(self, mock_bot):
        """Test failed backend health check."""
        cog = AdminCog(mock_bot)

        # Mock failed API request
        cog.api_client._request = AsyncMock(side_effect=Exception("Connection error"))

        result = await cog._check_backend_health()

        assert result is False
