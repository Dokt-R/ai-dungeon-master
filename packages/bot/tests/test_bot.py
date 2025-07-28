import pytest
from bot import bot


@pytest.fixture
def client():
    """Fixture to create a test client for the bot."""
    return bot  # Replace with actual bot initialization if needed


def test_bot_startup(client):
    """Test that the bot starts up without errors."""
    assert client is not None  # Ensure the bot client is initialized


@pytest.mark.asyncio
async def test_ping_command(client):
    """Test the /ping command response."""

    class MockInteraction:
        def __init__(self):
            self.response = self

        async def send_message(self, message):
            self.message = message

    interaction = MockInteraction()
    await client.tree.get_command("ping").callback(interaction)
    expected_response = "Pong!"
    assert (
        interaction.message == expected_response
    )  # Check if the response is as expected
    # Ensure the response is correct
