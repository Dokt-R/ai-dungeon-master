from unittest.mock import MagicMock, patch

import pytest

from packages.bot.cogs.utility_cog import UtilityCog
from packages.shared.errors import ErrorCode
from tests.utils.factories import MockInteraction

pytestmark = pytest.mark.asyncio


async def test_getting_started_generic_exception():
    """Test getting_started command when a generic exception occurs."""
    interaction = MockInteraction()
    cog = UtilityCog(bot=MagicMock())

    with patch.object(
        interaction.response, "send_message", side_effect=Exception("Unexpected error")
    ):
        await cog.getting_started.callback(cog, interaction)
        # After send_message fails, followup.send should be called with fallback message
        interaction.followup.send.assert_awaited_with(
            ErrorCode.UNKNOWN.player_message,
            ephemeral=True,
        )


async def test_cost_generic_exception():
    """Test cost command when a generic exception occurs."""
    interaction = MockInteraction()
    cog = UtilityCog(bot=MagicMock())

    with patch.object(
        interaction.response, "send_message", side_effect=Exception("Unexpected error")
    ):
        await cog.cost.callback(cog, interaction)
        # After send_message fails, followup.send should be called with fallback message
        interaction.followup.send.assert_awaited_with(
            ErrorCode.UNKNOWN.player_message,
            ephemeral=True,
        )


async def test_help_generic_exception():
    """Test help command when a generic exception occurs."""
    interaction = MockInteraction()
    cog = UtilityCog(bot=MagicMock())

    with patch.object(
        interaction.response, "send_message", side_effect=Exception("Unexpected error")
    ):
        await cog.help.callback(cog, interaction, None)
        # After send_message fails, followup.send should be called with fallback message
        interaction.followup.send.assert_awaited_with(
            ErrorCode.UNKNOWN.player_message,
            ephemeral=True,
        )


async def test_help_with_topic_generic_exception():
    """Test help command with topic when a generic exception occurs."""
    interaction = MockInteraction()
    cog = UtilityCog(bot=MagicMock())

    with patch.object(
        interaction.response, "send_message", side_effect=Exception("Unexpected error")
    ):
        await cog.help.callback(cog, interaction, "campaign")
        # After send_message fails, followup.send should be called with fallback message
        interaction.followup.send.assert_awaited_with(
            ErrorCode.UNKNOWN.player_message,
            ephemeral=True,
        )
