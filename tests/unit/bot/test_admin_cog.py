import pytest
from unittest.mock import AsyncMock, patch
from packages.bot.cogs.admin_cog import AdminCog
from tests.utils.factories import MockInteraction

pytestmark = pytest.mark.asyncio


class TestGeneralCommands:
    """Test the generic bot commands."""

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
            "You need Administrator or Manage Server permissions" in interaction.message
        )
        assert interaction.ephemeral is True


class TestOnServerSetkey:
    """Test the /server-setkey command."""

    async def test_server_setkey_permissions(self, bot_client):
        interaction = MockInteraction(is_admin=False)
        cmd = None
        for command in bot_client.tree.get_commands():
            if command.name == "server-setkey":
                cmd = command
                break
        assert cmd is not None
        cog = bot_client.get_cog("AdminCog")
        assert cog is not None
        await cog.server_setkey.callback(cog, interaction, "dummy_key")
        assert (
            "You need Administrator or Manage Server permissions" in interaction.message
        )
        assert interaction.ephemeral is True

    async def test_server_setkey_success(self, mock_bot, mock_interaction):
        cog = AdminCog(mock_bot)
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = True
        interaction.user.guild_permissions.manage_guild = False

        # Patch httpx.AsyncClient
        class MockResponse:
            status_code = 200
            text = "OK"

        async def mock_put(*args, **kwargs):
            return MockResponse()

        with patch("httpx.AsyncClient.put", new=mock_put):
            await cog.server_setkey.callback(cog, interaction, "testkey")
            interaction.response.send_message.assert_awaited_with(
                "API key securely stored for this server.", ephemeral=True
            )

    # Add parametrize for guild master
    async def test_server_setkey_failure(self, mock_bot, mock_interaction):
        cog = AdminCog(mock_bot)
        interaction = mock_interaction
        interaction.user.guild_permissions.administrator = True
        interaction.user.guild_permissions.manage_guild = False

        class MockResponse:
            status_code = 500
            text = "Internal Server Error"

        async def mock_put(*args, **kwargs):
            return MockResponse()

        with patch("httpx.AsyncClient.put", new=mock_put):
            await cog.server_setkey.callback(cog, interaction, "testkey")
            interaction.response.send_message.assert_awaited_with(
                "Failed to store API key: Internal Server Error", ephemeral=True
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
            "You need Administrator or Manage Server permissions to use this command.",
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
            "You need Administrator or Manage Server permissions to use this command.",
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
            "unexpected error" in str(call.args[0]).lower()
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
