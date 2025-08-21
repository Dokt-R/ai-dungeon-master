from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from packages.backend.components.character_manager import CharacterManager
from packages.backend.main import app
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import NotFoundError, ValidationError
from packages.shared.models import Character
from packages.shared.routes import ROUTES


# Mock the CharacterManager dependency
@pytest.fixture
def mock_character_manager():
    return AsyncMock(spec=CharacterManager)


@pytest_asyncio.fixture
async def client(mock_character_manager: AsyncMock):
    app.dependency_overrides[CharacterManager] = lambda: mock_character_manager
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides = {}


class BaseTestData:
    player_id = "test_player"
    character_name = "test_char"
    character_url = "http://example.com"
    character_id = 1


@pytest.mark.asyncio
class TestCharacterAPI(BaseTestData):
    async def test_add_character(
        self, client: AsyncClient, mock_character_manager: AsyncMock
    ):
        # Arrange
        mock_character = Character(
            character_id=self.character_id,
            player_id=self.player_id,
            name=self.character_name,
            character_url=self.character_url,
        )
        mock_character_manager.add_character.return_value = mock_character

        # Act
        response = await client.post(ROUTES.character_add(),
            json={
                "player_id": self.player_id,
                "name": self.character_name,
                "character_url": self.character_url,
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "character_id" in data
        assert data["character_id"] == self.character_id
        mock_character_manager.add_character.assert_called_once_with(
            player_id=self.player_id,
            name=self.character_name,
            character_url=self.character_url,
        )

    async def test_add_character_not_found_player(
        self, client: AsyncClient, mock_character_manager: AsyncMock
    ):
        # Arrange
        error = ErrorCode.PLAYER_NOT_FOUND
        mock_character_manager.add_character.side_effect = NotFoundError(error)

        # Act
        response = await client.post(
            ROUTES.character_add(),
            json={
                "player_id": "nonexistent",
                "name": "Hero",
            },
        )

        # Assert
        assert response.status_code == 404
        assert error.message in response.text

    async def test_update_character(
        self, client: AsyncClient, mock_character_manager: AsyncMock
    ):
        # Arrange
        mock_character_manager.update_character.return_value = True

        # Act
        response = await client.post(
            ROUTES.character_update(),
            json={"character_id": self.character_id, "name": "NewName"},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_character_manager.update_character.assert_called_once_with(
            character_id=self.character_id, name="NewName", character_url=None
        )

    async def test_update_character_not_found(
        self, client: AsyncClient, mock_character_manager: AsyncMock
    ):
        # Arrange
        error = ErrorCode.CHARACTER_NOT_FOUND
        mock_character_manager.update_character.side_effect = NotFoundError(error)

        # Act
        response = await client.post(
            ROUTES.character_update(), json={"character_id": 99999, "name": "NewName"}
        )

        # Assert
        assert response.status_code == 404
        assert error.message in response.text

    async def test_update_character_duplicate_name(
        self, client: AsyncClient, mock_character_manager: AsyncMock
    ):
        # Arrange
        name = "ExistingName"
        error = ErrorCode.DUPLICATE_CHARACTER
        mock_character_manager.update_character.side_effect = ValidationError(
            error, name=name
        )

        # Act
        response = await client.post(
            ROUTES.character_update(),
            json={"character_id": self.character_id, "name": name},
        )

        # Assert
        assert response.status_code == error.status_code
        assert name in response.text

    async def test_remove_character(
        self, client: AsyncClient, mock_character_manager: AsyncMock
    ):
        # Arrange
        mock_character_manager.remove_character.return_value = True

        # Act
        response = await client.post(
            ROUTES.character_remove(), json={"character_id": self.character_id}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_character_manager.remove_character.assert_called_once_with(
            character_id=self.character_id
        )

    async def test_remove_character_not_found(
        self, client: AsyncClient, mock_character_manager: AsyncMock
    ):
        # Arrange
        error = ErrorCode.CHARACTER_NOT_FOUND
        mock_character_manager.remove_character.side_effect = NotFoundError(error)

        # Act
        response = await client.post(ROUTES.character_remove(), json={"character_id": 999})

        # Assert
        assert response.status_code == 404
        assert error.message in response.text

    async def test_list_characters(
        self, client: AsyncClient, mock_character_manager: AsyncMock
    ):
        # Arrange
        mock_characters = [
            Character(
                character_id=self.character_id,
                player_id=self.player_id,
                name=self.character_name,
            )
        ]
        mock_character_manager.get_characters_for_player.return_value = mock_characters

        # Act
        response = await client.post(
            ROUTES.character_list(), json={"player_id": self.player_id}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "characters" in data
        assert len(data["characters"]) == 1
        assert data["characters"][0]["name"] == self.character_name
        mock_character_manager.get_characters_for_player.assert_called_once_with(
            player_id=self.player_id
        )
