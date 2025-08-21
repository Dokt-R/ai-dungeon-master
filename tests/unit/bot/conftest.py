from unittest.mock import MagicMock, patch

import pytest

from packages.bot.cogs.admin_cog import AdminCog
from packages.bot.cogs.campaign_cog import CampaignCog
from packages.bot.cogs.character_cog import CharacterCog
from packages.bot.cogs.utility_cog import UtilityCog
from tests.utils.mock_api_client import MockApiClient


@pytest.fixture
def mock_character_cog(mock_bot):
    """Pre-built CharacterCog with mocked API client - avoids expensive httpx.AsyncClient creation"""
    # Mock the ApiClient class before CharacterCog creation
    with patch('packages.bot.cogs.character_cog.ApiClient') as mock_api_class:
        # Make ApiClient.__init__ return a lightweight mock
        mock_api_instance = MagicMock()
        mock_api_class.return_value = mock_api_instance
        
        # Now create CharacterCog without the expensive httpx client
        cog = CharacterCog(mock_bot)
        
        # Replace with your actual MockApiClient
        cog.api_client = MockApiClient()
        
        return cog