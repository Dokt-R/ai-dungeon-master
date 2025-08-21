"""
Unit tests for CharacterCog using the mock API client.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
import discord

from packages.bot.cogs.character_cog import CharacterCog
from packages.shared.exceptions import NotFoundError, ValidationError
from tests.utils.mock_api_client import MockApiClient


@pytest.mark.asyncio
class TestCharacterCog:
    """Test suite for CharacterCog."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock Discord bot."""
        bot = AsyncMock()
        return bot

    @pytest.fixture
    def mock_interaction(self):
        """Create a mock Discord interaction."""
        interaction = AsyncMock(spec=discord.Interaction)
        interaction.user.id = 12345
        interaction.response.send_message = AsyncMock()
        return interaction

    @pytest_asyncio.fixture
    async def character_cog_with_mock_client(self, mock_bot):
        """Create a CharacterCog with a mock API client."""
        cog = CharacterCog(mock_bot)
        # Replace the real API client with our mock
        cog.api_client = MockApiClient()
        return cog

    async def test_add_character_success(self, character_cog_with_mock_client, mock_interaction):
        """Test successful character addition."""
        cog = character_cog_with_mock_client
        
        # Set up mock response
        cog.api_client.set_response_override('add_character', {
            'character_id': 123,
            'name': 'Test Character',
            'player_id': '12345'
        })
        
        await cog._handle_character_add(mock_interaction, "Test Character", None)
        
        # Verify the interaction response
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "Test Character" in call_args[0][0]
        assert "123" in call_args[0][0]
        
        # Verify API client was called correctly
        assert len(cog.api_client.call_history) == 1
        assert cog.api_client.call_history[0]['method'] == 'add_character'

    async def test_add_character_duplicate_error(self, character_cog_with_mock_client, mock_interaction):
        """Test character addition with duplicate name error."""
        cog = character_cog_with_mock_client
        
        # Set up mock to raise validation error
        cog.api_client.set_exception_override(
            'add_character', 
            ValidationError("DUPLICATE_CHARACTER", name="Test Character")
        )
        
        with pytest.raises(ValidationError):
            await cog._handle_character_add(mock_interaction, "Test Character", None)

    async def test_update_character_success(self, character_cog_with_mock_client, mock_interaction):
        """Test successful character update."""
        cog = character_cog_with_mock_client
        
        # Set up mock response
        cog.api_client.set_response_override('update_character', {
            'character_id': 123,
            'name': 'Updated Character',
            'player_id': '12345'
        })
        
        await cog._handle_update(mock_interaction, 123, "Updated Character", None)
        
        # Verify the interaction response
        mock_interaction.response.send_message.assert_called_once_with(
            "Character updated successfully.",
            ephemeral=True
        )
        
        # Verify API client was called correctly
        assert len(cog.api_client.call_history) == 1
        assert cog.api_client.call_history[0]['method'] == 'update_character'

    async def test_update_character_no_fields_error(self, character_cog_with_mock_client, mock_interaction):
        """Test character update with no fields provided."""
        cog = character_cog_with_mock_client
        
        with pytest.raises(ValidationError) as exc_info:
            await cog._handle_update(mock_interaction, 123, None, None)
        
        assert "CHARACTER_EMPTY_FIELDS" in str(exc_info.value.error_code)

    async def test_update_character_not_found(self, character_cog_with_mock_client, mock_interaction):
        """Test character update with character not found."""
        cog = character_cog_with_mock_client
        
        # Set up mock to raise not found error
        cog.api_client.set_exception_override(
            'update_character',
            NotFoundError("CHARACTER_NOT_FOUND")
        )
        
        with pytest.raises(NotFoundError):
            await cog._handle_update(mock_interaction, 999, "New Name", None)

    async def test_remove_character_success(self, character_cog_with_mock_client, mock_interaction):
        """Test successful character removal."""
        cog = character_cog_with_mock_client
        
        # Set up mock response
        cog.api_client.set_response_override('remove_character', {
            'message': 'Character removed successfully'
        })
        
        await cog._handle_character_remove(mock_interaction, 123)
        
        # Verify the interaction response
        mock_interaction.response.send_message.assert_called_once_with(
            "Character removed successfully.",
            ephemeral=True
        )
        
        # Verify API client was called correctly
        assert len(cog.api_client.call_history) == 1
        assert cog.api_client.call_history[0]['method'] == 'remove_character'

    async def test_remove_character_not_found(self, character_cog_with_mock_client, mock_interaction):
        """Test character removal with character not found."""
        cog = character_cog_with_mock_client
        
        # Set up mock to raise not found error
        cog.api_client.set_exception_override(
            'remove_character',
            NotFoundError("CHARACTER_NOT_FOUND")
        )
        
        with pytest.raises(NotFoundError):
            await cog._handle_character_remove(mock_interaction, 999)

    async def test_list_characters_success(self, character_cog_with_mock_client, mock_interaction):
        """Test successful character listing."""
        cog = character_cog_with_mock_client
        
        # Set up mock response with characters
        cog.api_client.set_response_override('list_characters', {
            'characters': [
                {'character_id': 1, 'name': 'Character 1', 'character_url': 'http://example.com'},
                {'character_id': 2, 'name': 'Character 2', 'character_url': None}
            ]
        })
        
        # Call the underlying method directly (bypassing Discord decorators)
        await cog.list.callback(cog, mock_interaction)
        
        # Verify the interaction response
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        message = call_args[0][0]
        
        assert "Your Characters:" in message
        assert "Character 1" in message
        assert "Character 2" in message
        assert "http://example.com" in message
        assert "N/A" in message

    async def test_list_characters_empty(self, character_cog_with_mock_client, mock_interaction):
        """Test character listing with no characters."""
        cog = character_cog_with_mock_client
        
        # Set up mock response with empty characters list
        cog.api_client.set_response_override('list_characters', {
            'characters': []
        })
        
        # Call the underlying method directly (bypassing Discord decorators)
        await cog.list.callback(cog, mock_interaction)
        
        # Verify the interaction response
        mock_interaction.response.send_message.assert_called_once_with(
            "You have no characters.",
            ephemeral=True
        )

    async def test_cog_unload_closes_client(self, character_cog_with_mock_client):
        """Test that cog unload properly closes the API client."""
        cog = character_cog_with_mock_client
        
        # Mock the close method to track if it's called
        cog.api_client.close = AsyncMock()
        
        await cog.cog_unload()
        
        # Verify close was called
        cog.api_client.close.assert_called_once()

    async def test_api_client_call_tracking(self, character_cog_with_mock_client, mock_interaction):
        """Test that the mock API client properly tracks calls."""
        cog = character_cog_with_mock_client
        
        # Make several API calls
        await cog._handle_character_add(mock_interaction, "Test 1", None)
        await cog._handle_character_add(mock_interaction, "Test 2", "http://example.com")
        
        # Verify call history
        assert len(cog.api_client.call_history) == 2
        
        first_call = cog.api_client.call_history[0]
        assert first_call['method'] == 'add_character'
        assert first_call['args'][0].name == "Test 1"
        assert first_call['args'][0].character_url is None
        
        second_call = cog.api_client.call_history[1]
        assert second_call['method'] == 'add_character'
        assert second_call['args'][0].name == "Test 2"
        assert second_call['args'][0].character_url == "http://example.com"