import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.bot.cogs.character_cog import CharacterCog
from packages.shared.error_handler import ValidationError, NotFoundError


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

    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 400
        mock_client.return_value.__aenter__.return_value.post.return_value.json = (
            AsyncMock(return_value={"detail": "Invalid character data"})
        )
        await cog.add.callback(cog, interaction, name="Hero", character_url=None)
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "failed to add character" in args[0].lower()
        assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_update_command_validation_error(cog):
    """Test character update command when backend returns validation error."""
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()

    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 400
        mock_client.return_value.__aenter__.return_value.post.return_value.json = (
            AsyncMock(return_value={"detail": "Invalid character data"})
        )
        await cog.update.callback(
            cog, interaction, character_id=1, name="NewName", character_url=None
        )
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "failed to update character" in args[0].lower()
        assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_character_remove_command_not_found_error(cog):
    """Test character remove command when character is not found."""
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
async def test_character_list_command_validation_error(cog):
    """Test character list command when backend returns validation error."""
    interaction = AsyncMock()
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()

    with patch("packages.bot.cogs.character_cog.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 400
        mock_client.return_value.__aenter__.return_value.post.return_value.json = (
            AsyncMock(return_value={"detail": "Invalid request"})
        )
        await cog.list.callback(cog, interaction)
        interaction.response.send_message.assert_awaited_once()
        args, kwargs = interaction.response.send_message.call_args
        assert "failed to list characters" in args[0].lower()
        assert kwargs.get("ephemeral") is True


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
        assert "failed to add character" in args[0].lower()
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
        assert "failed to update character" in args[0].lower()
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
        assert "failed to remove character" in args[0].lower()
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
        assert "failed to list characters" in args[0].lower()
        assert kwargs.get("ephemeral") is True
