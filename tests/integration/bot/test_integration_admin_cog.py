import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.bot.cogs.admin_cog import AdminCog
from tests.utils.factories import make_discord_interaction, make_discord_member

pytestmark = pytest.mark.asyncio


@pytest.mark.skip(reason="needs fixing and takes too long")
class TestSyncIntegration:
    """Integration tests for sync functionality."""

    async def test_sync_members_integration(self, mock_bot):
        """Test that sync_members properly integrates with API client."""
        cog = AdminCog(mock_bot)

        # Create mock interaction
        interaction = make_discord_interaction(is_admin=True)

        # Mock guild with members
        mock_member1 = make_discord_member(
            user_id=123, display_name="TestUser1", bot=False
        )
        mock_member2 = make_discord_member(
            user_id=124, display_name="TestUser2", bot=False
        )
        mock_guild = MagicMock()
        mock_guild.members = [mock_member1, mock_member2]
        mock_guild.chunk = AsyncMock()
        interaction.guild = mock_guild

        # Mock successful API responses
        mock_api_response = {"player_id": "123", "username": "TestUser1"}
        cog.api_client.create_player = AsyncMock(return_value=mock_api_response)

        # Mock the followup methods
        interaction.followup.send = AsyncMock()
        interaction.response.defer = AsyncMock()

        await cog.sync_members_(cog, interaction)

        # Verify API was called for each non-bot member
        assert cog.api_client.create_player.call_count == 2
        interaction.followup.send.assert_awaited()

        # Check that the initial progress message was sent
        calls = interaction.followup.send.await_args_list
        initial_call = calls[0][0][0]
        assert "Starting sync of 2 members" in initial_call

    async def test_periodic_sync_integration(self, mock_bot):
        """Test periodic sync integration with backend."""
        cog = AdminCog(mock_bot)

        # Mock bot guilds
        mock_guild = MagicMock()
        mock_guild.id = 123456
        mock_guild.name = "Test Guild"
        mock_guild.members = [
            make_discord_member(user_id=123, display_name="User1", bot=False),
            make_discord_member(user_id=124, display_name="User2", bot=False),
        ]
        mock_guild.chunk = AsyncMock()
        mock_bot.guilds = [mock_guild]

        # Mock API client
        mock_api_response = {"player_id": "123", "username": "User1"}
        cog.api_client.create_player = AsyncMock(return_value=mock_api_response)

        # Override the sync interval to be very short for testing
        cog.sync_interval = 0.1

        # Run periodic sync for a short time
        task = asyncio.create_task(cog._periodic_sync())

        # Wait for the task to start
        await asyncio.sleep(0.2)

        # Verify the task is running
        assert not task.done()

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify the task completed after cancellation
        assert task.done()

    async def test_member_join_integration(self, mock_bot):
        """Test member join event integration."""
        cog = AdminCog(mock_bot)
        member = make_discord_member(user_id=123, display_name="NewUser", bot=False)

        # Mock API response
        mock_api_response = {"player_id": "123", "username": "NewUser"}
        cog.api_client.create_player = AsyncMock(return_value=mock_api_response)

        await cog.on_member_join(member)

        # Verify API was called with correct data
        cog.api_client.create_player.assert_awaited_once_with(
            {"player_id": "123", "username": "NewUser"}
        )

    async def test_member_update_integration(self, mock_bot):
        """Test member update event integration when display name changes."""
        cog = AdminCog(mock_bot)
        before_member = make_discord_member(
            user_id=123, display_name="OldName", bot=False
        )
        after_member = make_discord_member(
            user_id=123, display_name="NewName", bot=False
        )

        # Mock API response
        mock_api_response = {"player_id": "123", "username": "NewName"}
        cog.api_client.create_player = AsyncMock(return_value=mock_api_response)

        await cog.on_member_update(before_member, after_member)

        # Verify API was called with new display name
        cog.api_client.create_player.assert_awaited_once_with(
            {"player_id": "123", "username": "NewName"}
        )

    async def test_member_update_no_change(self, mock_bot):
        """Test member update event when display name doesn't change."""
        cog = AdminCog(mock_bot)
        before_member = make_discord_member(
            user_id=123, display_name="SameName", bot=False
        )
        after_member = make_discord_member(
            user_id=123, display_name="SameName", bot=False
        )

        # Mock API client to ensure it's not called
        cog.api_client.create_player = AsyncMock()

        await cog.on_member_update(before_member, after_member)

        # Verify API was not called since display name didn't change
        cog.api_client.create_player.assert_not_awaited()

    async def test_backend_health_check_integration(self, mock_bot):
        """Test backend health check integration."""
        cog = AdminCog(mock_bot)

        # Test successful health check
        mock_response = {
            "player_id": "health_check_test",
            "username": "Health Check User",
        }
        cog.api_client.create_player = AsyncMock(return_value=mock_response)

        result = await cog._check_backend_health()
        assert result is True

        # Test failed health check
        cog.api_client.create_player = AsyncMock(
            side_effect=Exception("Connection error")
        )

        result = await cog._check_backend_health()
        assert result is False

    async def test_sync_error_handling(self, mock_bot):
        """Test error handling during sync operations."""
        cog = AdminCog(mock_bot)
        interaction = make_discord_interaction(is_admin=True)

        # Mock guild with problematic members
        mock_member = make_discord_member(
            user_id=123, display_name="TestUser", bot=False
        )
        mock_guild = MagicMock()
        mock_guild.members = [mock_member]
        mock_guild.chunk = AsyncMock()
        interaction.guild = mock_guild

        # Mock API to raise an exception
        cog.api_client.create_player = AsyncMock(side_effect=Exception("API Error"))

        interaction.followup.send = AsyncMock()
        interaction.response.defer = AsyncMock()

        await cog.sync_members_(cog, interaction)

        # Verify error was handled and reported
        calls = interaction.followup.send.await_args_list
        initial_call = calls[0][0][0]
        assert "Starting sync of 1 members" in initial_call

    async def test_bot_member_filtering(self, mock_bot):
        """Test that bot members are properly filtered out."""
        cog = AdminCog(mock_bot)
        interaction = make_discord_interaction(is_admin=True)

        # Mock guild with mix of bot and human members
        human_member = make_discord_member(
            user_id=123, display_name="HumanUser", bot=False
        )
        bot_member = make_discord_member(user_id=124, display_name="BotUser", bot=True)
        mock_guild = MagicMock()
        mock_guild.members = [human_member, bot_member]
        mock_guild.chunk = AsyncMock()
        interaction.guild = mock_guild

        # Mock successful API response
        mock_api_response = {"player_id": "123", "username": "HumanUser"}
        cog.api_client.create_player = AsyncMock(return_value=mock_api_response)

        interaction.followup.send = AsyncMock()
        interaction.response.defer = AsyncMock()

        await cog.sync_members_(cog, interaction)

        # Verify only human member was processed
        assert cog.api_client.create_player.call_count == 1
        call_args = cog.api_client.create_player.call_args[0][0]
        assert call_args["player_id"] == "123"
        assert call_args["username"] == "HumanUser"
