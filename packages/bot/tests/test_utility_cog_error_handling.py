import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.bot.cogs.utility_cog import UtilityCog


class DummyInteraction:
    def __init__(self):
        self.response = AsyncMock()
        self.followup = AsyncMock()
        self.response.is_done = MagicMock(return_value=False)


@pytest.mark.asyncio
async def test_ping_generic_exception():
    interaction = DummyInteraction()
    cog = UtilityCog(bot=MagicMock())
    # Patch send_message to raise, and followup.send to succeed
    with patch.object(
        interaction.response, "send_message", side_effect=Exception("Unexpected error")
    ), patch.object(
        interaction, "followup"
    ) as mock_followup:
        # Simulate response.is_done returning False, so fallback is attempted
        interaction.response.is_done.return_value = False
        await cog.ping.callback(cog, interaction)
        # After send_message fails, followup.send should be called with fallback message
        mock_followup.send.assert_called_with(
            "An unexpected error occurred. Please contact an administrator.", ephemeral=True
        )
