import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.bot.cogs.character_cog import CharacterCog


@pytest.mark.asyncio
async def test_character_add_command():
    bot = MagicMock()
    cog = CharacterCog(bot)
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()
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
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 400
        mock_client.return_value.__aenter__.return_value.post.return_value.json = (
            AsyncMock(return_value={"detail": "Character already exists"})
        )
        await cog.add.callback(cog, interaction, name="Hero", character_url=None)
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "failed to add character" in args[0].lower()
        assert kwargs.get("ephemeral") is True


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
    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 404
        mock_client.return_value.__aenter__.return_value.post.return_value.json = (
            AsyncMock(return_value={"detail": "Character not found"})
        )
        await cog.remove.callback(cog, interaction, character_id=999)
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "failed to remove character" in args[0].lower()
        assert kwargs.get("ephemeral") is True


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
