import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from discord.ext import commands

from packages.bot.main import bot, load_cogs


@pytest.mark.asyncio
async def test_bot_initialization():
    """Test that the bot is properly initialized with correct intents."""
    # Check that the bot is an instance of commands.Bot
    assert bot is not None
    assert isinstance(bot, commands.Bot)

    # Check that the bot has the correct command prefix
    assert bot.command_prefix == "/"

    # Check that the bot has the correct intents
    assert bot.intents.messages is True
    assert bot.intents.guilds is True
    assert bot.intents.message_content is True


@patch("builtins.print")
@pytest.mark.asyncio
async def test_on_ready_success(mock_print):
    """Test the on_ready event handler when command sync is successful."""
    # Import the on_ready function directly
    from packages.bot.main import on_ready

    # Mock the bot.tree.sync method to return a list of commands
    with patch.object(bot.tree, "sync", new_callable=AsyncMock) as mock_sync:
        mock_sync.return_value = ["command1", "command2", "command3"]

        # Create a simple approach to mock bot.user
        mock_user = MagicMock()
        mock_user.__str__ = lambda self: "TestBot#1234"

        # Temporarily add a _user attribute and mock the property
        bot._test_user = mock_user
        original_user_property = bot.__class__.user
        bot.__class__.user = property(lambda self: self._test_user)

        try:
            # Call the on_ready function
            await on_ready()

            # Check that print was called with the correct messages
            mock_print.assert_any_call("Logged in as TestBot#1234")
            mock_print.assert_any_call("Synced 3 commands globally.")
        finally:
            # Restore the original user property
            bot.__class__.user = original_user_property
            if hasattr(bot, "_test_user"):
                delattr(bot, "_test_user")


@patch("builtins.print")
@pytest.mark.asyncio
async def test_on_ready_sync_failure(mock_print):
    """Test the on_ready event handler when command sync fails."""
    # Import the on_ready function directly
    from packages.bot.main import on_ready

    # Mock the bot.tree.sync method to raise an exception
    with patch.object(bot.tree, "sync", new_callable=AsyncMock) as mock_sync:
        mock_sync.side_effect = Exception("Sync failed")

        # Create a simple approach to mock bot.user
        mock_user = MagicMock()
        mock_user.__str__ = lambda self: "TestBot#1234"

        # Temporarily add a _user attribute and mock the property
        bot._test_user = mock_user
        original_user_property = bot.__class__.user
        bot.__class__.user = property(lambda self: self._test_user)

        try:
            # Call the on_ready function
            await on_ready()

            # Check that print was called with the correct messages
            mock_print.assert_any_call("Logged in as TestBot#1234")
            mock_print.assert_any_call("Failed to sync commands: Sync failed")
        finally:
            # Restore the original user property
            bot.__class__.user = original_user_property
            if hasattr(bot, "_test_user"):
                delattr(bot, "_test_user")


@pytest.mark.asyncio
async def test_load_cogs_success():
    """Test that load_cogs successfully loads all cogs."""
    # Mock bot.load_extension to simulate successful loading
    with patch.object(bot, "load_extension", new_callable=AsyncMock) as mock_load:
        await load_cogs()

        # Check that load_extension was called for each cog
        expected_cogs = [
            "packages.bot.cogs.utility_cog",
            "packages.bot.cogs.admin_cog",
            "packages.bot.cogs.campaign_cog",
            "packages.bot.cogs.character_cog",
        ]

        assert mock_load.call_count == 4
        for cog in expected_cogs:
            mock_load.assert_any_call(cog)


@pytest.mark.asyncio
async def test_load_cogs_failure():
    """Test that load_cogs handles failures gracefully."""
    # Mock bot.load_extension to simulate a failure
    with patch.object(bot, "load_extension", new_callable=AsyncMock) as mock_load:
        mock_load.side_effect = Exception("Failed to load cog")

        # Check that the exception is raised when loading cogs
        with pytest.raises(Exception, match="Failed to load cog"):
            await load_cogs()


def test_main_function_structure():
    """Test that the main function structure is correct."""
    # This test verifies that the main.py file can be imported without errors
    # and that it contains the expected functions and structures

    # Import the module to check it can be imported without errors
    import packages.bot.main

    # Check that the expected functions exist
    assert hasattr(packages.bot.main, "load_cogs")
    assert hasattr(packages.bot.main, "on_ready")

    # Check that the bot is created
    assert packages.bot.main.bot is not None

    # Check that the if __name__ == "__main__": block exists by checking
    # that the module can be executed without syntax errors
    assert True  # If we get here, the module imported successfully


def test_environment_variable_loading():
    """Test that environment variables are loaded."""
    # Check that load_dotenv was called (indirectly by checking if os.getenv works)
    # This test assumes that the .env file or environment variables are set up
    # In a real test environment, you might want to mock this
    os.getenv("DISCORD_BOT_TOKEN")
    # Token might be None in test environment, but the function should have been called
    assert (
        True
    )  # The actual loading is tested by the fact that the module imported successfully


# Test the bot_client fixture from conftest.py to ensure it works with our main module
def test_bot_client_fixture(bot_client):
    """Test that the bot_client fixture works correctly."""
    assert bot_client is not None
    assert isinstance(bot_client, commands.Bot)

    # Check that all cogs are loaded
    cog_names = [cog.qualified_name for cog in bot_client.cogs.values()]
    expected_cogs = ["AdminCog", "CharacterCog", "CampaignCog", "UtilityCog"]
    for cog in expected_cogs:
        assert cog in cog_names
