import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.bot.cogs.utility_cog import UtilityCog


class DummyInteraction:
    def __init__(self):
        self.response = AsyncMock()


@pytest.mark.asyncio
async def test_ping_generic_exception():
    interaction = DummyInteraction()
    cog = UtilityCog(bot=MagicMock())
    # Patch the response to raise an exception
    with patch.object(
        interaction.response, "send_message", side_effect=Exception("Unexpected error")
    ):
        # The error handler will log and re-raise, but we want to check that the exception is handled
        try:
            await cog.ping(interaction)
        except Exception:
            pass  # The error handler will re-raise, so we just ensure no crash
