from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from packages.bot.cogs.character_cog import CharacterCog


@pytest.fixture
def bot():
    return MagicMock()


@pytest.fixture
def cog(bot):
    return CharacterCog(bot)


@pytest.mark.asyncio
async def test_character_add_command_validation_error(cog):
    """Test character add command when backend returns validation error."""
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.response.send_message = AsyncMock()

    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json = AsyncMock(
            return_value={
                "error": {"message": "Failed to add character. Please try again later."}
            }
        )
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        mock_client.return_value.__aenter__.return_value.post.return_value = (
            mock_response
        )

        await cog.add.callback(cog, interaction, name="Hero", character_url=None)
        interaction.response.send_message.assert_awaited_once_with(
            "Failed to add character. Please try again later.", ephemeral=True
        )


@pytest.mark.asyncio
async def test_character_update_command_validation_error(cog):
    """Test character update command when backend returns validation error."""
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()
    interaction.followup.send = AsyncMock()

    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json = AsyncMock(
            return_value={
                "error": {
                    "message": "An unexpected error occurred. Please contact an administrator."
                }
            }
        )
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        mock_client.return_value.__aenter__.return_value.post.return_value = (
            mock_response
        )

        await cog.update.callback(
            cog, interaction, character_id=1, name="NewName", character_url=None
        )
        interaction.response.send_message.assert_awaited_once_with(
            "An unexpected error occurred. Please contact an administrator.",
            ephemeral=True,
        )


@pytest.mark.asyncio
async def test_character_remove_command_not_found_error(cog):
    """Test character remove command when character is not found."""
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()
    interaction.followup.send = AsyncMock()

    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json = AsyncMock(return_value={"detail": "Character not found"})
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_client.return_value.__aenter__.return_value.post.return_value = (
            mock_response
        )

        await cog.remove.callback(cog, interaction, character_id=999)
        interaction.response.send_message.assert_awaited_once_with(
            "Character not found", ephemeral=True
        )


@pytest.mark.asyncio
async def test_character_list_command_validation_error(cog):
    """Test character list command when backend returns validation error."""
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()

    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json = AsyncMock(
            return_value={
                "message": "Failed to list characters. Please try again later."
            }
        )
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        mock_client.return_value.__aenter__.return_value.post.return_value = (
            mock_response
        )

        await cog.list.callback(cog, interaction)
        interaction.response.send_message.assert_awaited_once_with(
            "Failed to list characters. Please try again later.", ephemeral=True
        )


@pytest.mark.asyncio
async def test_character_add_command_http_error(cog):
    """Test character add command when HTTP request fails."""
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()

    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = Exception(
            "Network error"
        )
        await cog.add.callback(cog, interaction, name="Hero", character_url=None)
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "an unexpected error occurred" in args[0].lower()
        assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_update_command_http_error(cog):
    """Test character update command when HTTP request fails."""
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()

    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = Exception(
            "Network error"
        )
        await cog.update.callback(
            cog, interaction, character_id=1, name="NewName", character_url=None
        )
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "an unexpected error occurred" in args[0].lower()
        assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_remove_command_http_error(cog):
    """Test character remove command when HTTP request fails."""
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()

    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = Exception(
            "Network error"
        )
        await cog.remove.callback(cog, interaction, character_id=1)
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "an unexpected error occurred" in args[0].lower()
        assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_list_command_http_error(cog):
    """Test character list command when HTTP request fails."""
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()

    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = Exception(
            "Network error"
        )
        await cog.list.callback(cog, interaction)
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "an unexpected error occurred" in args[0].lower()
        assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_add_command_internal_server_error(cog):
    """Test character add command when backend returns a 500 error."""
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()
    interaction.followup.send = AsyncMock()

    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json = AsyncMock(
            return_value={
                "error": {
                    "message": "An unexpected error occurred. Please contact an administrator."
                }
            }
        )
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )
        mock_client.return_value.__aenter__.return_value.post.return_value = (
            mock_response
        )

        await cog.add.callback(cog, interaction, name="Hero", character_url=None)
        interaction.response.send_message.assert_awaited_once_with(
            "An unexpected error occurred. Please contact an administrator.",
            ephemeral=True,
        )
