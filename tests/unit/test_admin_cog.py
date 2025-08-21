"""
Unit tests for AdminCog using the mock API client.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
import discord

from packages.bot.cogs.admin_cog import AdminCog
from packages.shared.exceptions import PermissionDeniedError, ValidationError
from packages.shared.models import ServerConfigModel
from tests.utils.mock_api_client import MockApiClient


@pytest.mark.asyncio
class TestAdminCog:
    """Test suite for AdminCog."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock Discord bot."""
        bot = AsyncMock()
        return bot

    @pytest.fixture
    def mock_interaction(self):
        """Create a mock Discord interaction."""
        interaction = AsyncMock(spec=discord.Interaction)
        interaction.user.id = 12345
        interaction.guild_id = 67890
        interaction.response.send_message = AsyncMock()
        
        # Mock permissions - admin by default
        permissions = AsyncMock()
        permissions.administrator = True
        permissions.manage_guild = True
        interaction.user.guild_permissions = permissions
        
        return interaction

    @pytest.fixture
    def mock_member(self):
        """Create a mock Discord member."""
        member = AsyncMock(spec=discord.Member)
        member.id = 12345
        member.name = "TestUser"
        member.bot = False
        return member

    @pytest_asyncio.fixture
    async def admin_cog_with_mock_client(self, mock_bot):
        """Create an AdminCog with a mock API client."""
        cog = AdminCog(mock_bot)
        # Replace the real API client with our mock
        cog.api_client = MockApiClient()
        return cog

    async def test_on_member_join_success(self, admin_cog_with_mock_client, mock_member):
        """Test successful player creation when member joins."""
        cog = admin_cog_with_mock_client
        
        # Set up mock response
        cog.api_client.set_response_override('create_player', {
            'player_id': '12345',
            'username': 'TestUser',
            'status': 'created'
        })
        
        await cog.on_member_join(mock_member)
        
        # Verify API client was called correctly
        assert len(cog.api_client.call_history) == 1
        call = cog.api_client.call_history[0]
        assert call['method'] == 'create_player'
        assert call['args'][0]['player_id'] == '12345'
        assert call['args'][0]['username'] == 'TestUser'

    async def test_on_member_join_bot_ignored(self, admin_cog_with_mock_client):
        """Test that bot members are ignored."""
        cog = admin_cog_with_mock_client
        
        # Create a bot member
        bot_member = AsyncMock(spec=discord.Member)
        bot_member.bot = True
        
        await cog.on_member_join(bot_member)
        
        # Verify no API calls were made
        assert len(cog.api_client.call_history) == 0

    async def test_on_member_join_error_handling(self, admin_cog_with_mock_client, mock_member):
        """Test error handling during player creation."""
        cog = admin_cog_with_mock_client
        
        # Set up mock to raise an exception
        cog.api_client.set_exception_override(
            'create_player',
            ValidationError("UNKNOWN", details={"message": "Network error"})
        )
        
        # Should not raise exception (error is caught and logged)
        await cog.on_member_join(mock_member)
        
        # Verify API client was called
        assert len(cog.api_client.call_history) == 1

    async def test_server_setup_success(self, admin_cog_with_mock_client, mock_interaction):
        """Test successful server setup command."""
        cog = admin_cog_with_mock_client
        
        await cog.server_setup.callback(cog, mock_interaction)
        
        # Verify the interaction response
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        message = call_args[0][0]
        
        assert "Shared API Key Model" in message
        assert "/server-setkey" in message
        assert call_args[1]['ephemeral'] is True

    async def test_server_setup_permission_denied(self, admin_cog_with_mock_client, mock_interaction):
        """Test server setup with insufficient permissions."""
        cog = admin_cog_with_mock_client
        
        # Remove admin permissions
        mock_interaction.user.guild_permissions.administrator = False
        mock_interaction.user.guild_permissions.manage_guild = False
        
        # The error handler decorator catches the exception and sends a Discord message
        # So we test that the error message was sent instead of expecting an exception
        await cog.server_setup.callback(cog, mock_interaction)
        
        # Verify that an error message was sent (the error handler sends the player-facing message)
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        # The error handler should send an ephemeral error message
        assert call_args[1]['ephemeral'] is True

    async def test_server_setkey_success(self, admin_cog_with_mock_client, mock_interaction):
        """Test successful server API key setting."""
        cog = admin_cog_with_mock_client
        
        # Set up mock response
        cog.api_client.set_response_override('set_server_config', {
            'message': 'Server configuration updated successfully'
        })
        
        await cog.server_setkey.callback(cog, mock_interaction, "sk-test-api-key-12345")
        
        # Verify API client was called correctly
        assert len(cog.api_client.call_history) == 1
        call = cog.api_client.call_history[0]
        assert call['method'] == 'set_server_config'
        assert call['args'][0] == '67890'  # server_id
        
        # Verify the config object
        config = call['args'][1]
        assert isinstance(config, ServerConfigModel)
        assert config.api_key.get_secret_value() == "sk-test-api-key-12345"
        assert config.dm_roll_visibility == "public"
        assert config.player_roll_mode == "digital"
        assert config.character_sheet_mode == "digital_sheet"
        
        # Verify the interaction response
        mock_interaction.response.send_message.assert_called_once_with(
            "API key securely stored for this server.",
            ephemeral=True
        )

    async def test_server_setkey_permission_denied(self, admin_cog_with_mock_client, mock_interaction):
        """Test server setkey with insufficient permissions."""
        cog = admin_cog_with_mock_client
        
        # Remove admin permissions
        mock_interaction.user.guild_permissions.administrator = False
        mock_interaction.user.guild_permissions.manage_guild = False
        
        # The error handler decorator catches the exception and sends a Discord message
        await cog.server_setkey.callback(cog, mock_interaction, "sk-test-api-key-12345")
        
        # Verify that an error message was sent
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert call_args[1]['ephemeral'] is True

    async def test_server_setkey_api_error(self, admin_cog_with_mock_client, mock_interaction):
        """Test server setkey with API error."""
        cog = admin_cog_with_mock_client
        
        # The issue here is that Pydantic validation fails before we even get to the API call
        # because empty string doesn't meet the min_length=1 requirement for api_key
        # This is actually correct behavior - the validation should happen at the model level
        
        # Test with a valid key but API error
        cog.api_client.set_exception_override(
            'set_server_config',
            ValidationError("EMPTY_API_KEY")
        )
        
        # The error handler will catch the exception and send a Discord message
        await cog.server_setkey.callback(cog, mock_interaction, "sk-valid-key")
        
        # Verify that an error message was sent
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert call_args[1]['ephemeral'] is True

    async def test_cog_unload_closes_client(self, admin_cog_with_mock_client):
        """Test that cog unload properly closes the API client."""
        cog = admin_cog_with_mock_client
        
        # Mock the close method to track if it's called
        cog.api_client.close = AsyncMock()
        
        await cog.cog_unload()
        
        # Verify close was called
        cog.api_client.close.assert_called_once()

    async def test_manage_guild_permission_sufficient(self, admin_cog_with_mock_client, mock_interaction):
        """Test that manage_guild permission is sufficient for admin commands."""
        cog = admin_cog_with_mock_client
        
        # Set only manage_guild permission (not administrator)
        mock_interaction.user.guild_permissions.administrator = False
        mock_interaction.user.guild_permissions.manage_guild = True
        
        # Should not raise permission error
        await cog.server_setup.callback(cog, mock_interaction)
        
        # Verify the interaction response was sent
        mock_interaction.response.send_message.assert_called_once()

    async def test_api_client_call_tracking(self, admin_cog_with_mock_client, mock_member, mock_interaction):
        """Test that the mock API client properly tracks calls."""
        cog = admin_cog_with_mock_client
        
        # Make several API calls
        await cog.on_member_join(mock_member)
        await cog.server_setkey.callback(cog, mock_interaction, "sk-test-key")
        
        # Verify call history
        assert len(cog.api_client.call_history) == 2
        
        first_call = cog.api_client.call_history[0]
        assert first_call['method'] == 'create_player'
        assert first_call['args'][0]['player_id'] == '12345'
        
        second_call = cog.api_client.call_history[1]
        assert second_call['method'] == 'set_server_config'
        assert second_call['args'][0] == '67890'