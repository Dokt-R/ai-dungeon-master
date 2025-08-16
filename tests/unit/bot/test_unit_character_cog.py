from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from packages.bot.cogs.character_cog import CharacterCog


@pytest.mark.asyncio
async def test_character_add_command(mock_bot, mock_interaction):
    cog = CharacterCog(mock_bot)
    interaction = mock_interaction
    interaction.user.id = 42
    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 200
        mock_client.return_value.__aenter__.return_value.post.return_value.json = (
            AsyncMock(return_value={"character_id": 123})
        )
        await cog.add.callback(cog, interaction, name="Hero", character_url=None)
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "added successfully" in args[0].lower()
        assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_update_command():
    bot = MagicMock()
    cog = CharacterCog(bot)
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()
    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 200
        mock_client.return_value.__aenter__.return_value.post.return_value.json = (
            AsyncMock(return_value={"success": True})
        )
        await cog.update.callback(
            cog, interaction, character_id=1, name="NewName", character_url=None
        )
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "updated successfully" in args[0].lower()
        assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_remove_command():
    bot = MagicMock()
    cog = CharacterCog(bot)
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()
    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 200
        mock_client.return_value.__aenter__.return_value.post.return_value.json = (
            AsyncMock(return_value={"success": True})
        )
        await cog.remove.callback(cog, interaction, character_id=1)
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "removed successfully" in args[0].lower()
        assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_list_command():
    bot = MagicMock()
    cog = CharacterCog(bot)
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()
    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 200
        mock_client.return_value.__aenter__.return_value.post.return_value.json = (
            AsyncMock(
                return_value={
                    "characters": [
                        {"character_id": 1, "name": "Hero", "character_url": "url"}
                    ]
                }
            )
        )
        await cog.list.callback(cog, interaction)
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "your characters" in args[0].lower()
        assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_add_command_backend_error():
    bot = MagicMock()
    cog = CharacterCog(bot)
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()

    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json = AsyncMock(return_value={"message": "Failed to add character. Please try again later."})
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        await cog.add.callback(cog, interaction, name="Hero", character_url=None)
        interaction.response.send_message.assert_awaited_once_with(
            "Failed to add character. Please try again later.", ephemeral=True
        )


@pytest.mark.asyncio
async def test_character_update_command_no_fields():
    bot = MagicMock()
    cog = CharacterCog(bot)
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()
    await cog.update.callback(
        cog, interaction, character_id=1, name=None, character_url=None
    )
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "must provide at least one field" in args[0].lower()
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_remove_command_backend_error():
    bot = MagicMock()
    cog = CharacterCog(bot)
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
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        await cog.remove.callback(cog, interaction, character_id=999)
        interaction.response.send_message.assert_awaited_once_with(
            "Character not found", ephemeral=True
        )


@pytest.mark.asyncio
async def test_character_list_command_empty():
    bot = MagicMock()
    cog = CharacterCog(bot)
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()
    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 200
        mock_client.return_value.__aenter__.return_value.post.return_value.json = (
            AsyncMock(return_value={"characters": []})
        )
        await cog.list.callback(cog, interaction)
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "no characters" in args[0].lower()
        assert kwargs.get("ephemeral") is True
