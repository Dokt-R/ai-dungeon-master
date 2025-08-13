import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from packages.backend.main import app
from packages.backend.components.character_manager import CharacterManager
from packages.shared.models import Character
from packages.shared.error_handler import NotFoundError, ValidationError


# Mock the CharacterManager dependency
@pytest.fixture
def mock_character_manager():
    return MagicMock(spec=CharacterManager)


@pytest.fixture
def client(mock_character_manager: MagicMock):
    app.dependency_overrides[CharacterManager] = lambda: mock_character_manager
    with TestClient(app) as client:
        yield client
    app.dependency_overrides = {}


class BaseTestData:
    player_id = "test_player"
    character_name = "test_char"
    character_url = "http://example.com"
    character_id = 1


class TestCharacterAPI(BaseTestData):
    def test_add_character(self, client: TestClient, mock_character_manager: MagicMock):
        # Arrange
        mock_character = Character(
            character_id=self.character_id,
            player_id=self.player_id,
            name=self.character_name,
            character_url=self.character_url,
        )
        mock_character_manager.add_character.return_value = mock_character

        # Act
        response = client.post(
            "/characters/add",
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

    def test_add_character_not_found_player(
        self, client: TestClient, mock_character_manager: MagicMock
    ):
        # Arrange
        mock_character_manager.add_character.side_effect = NotFoundError(
            "Player does not exist"
        )

        # Act
        response = client.post(
            "/characters/add",
            json={
                "player_id": "nonexistent",
                "name": "Hero",
            },
        )

        # Assert
        assert response.status_code == 404
        assert "Player does not exist" in response.text

    def test_update_character(
        self, client: TestClient, mock_character_manager: MagicMock
    ):
        # Arrange
        mock_character_manager.update_character.return_value = True

        # Act
        response = client.post(
            "/characters/update",
            json={"character_id": self.character_id, "name": "NewName"},
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_character_manager.update_character.assert_called_once_with(
            character_id=self.character_id, name="NewName", character_url=None
        )

    def test_update_character_not_found(
        self, client: TestClient, mock_character_manager: MagicMock
    ):
        # Arrange
        mock_character_manager.update_character.side_effect = NotFoundError(
            "Character does not exist"
        )

        # Act
        response = client.post(
            "/characters/update", json={"character_id": 99999, "name": "NewName"}
        )

        # Assert
        assert response.status_code == 404
        assert "Character does not exist" in response.text

    def test_update_character_duplicate_name(
        self, client: TestClient, mock_character_manager: MagicMock
    ):
        # Arrange
        mock_character_manager.update_character.side_effect = ValidationError(
            "Name already exists"
        )

        # Act
        response = client.post(
            "/characters/update",
            json={"character_id": self.character_id, "name": "ExistingName"},
        )

        # Assert
        assert response.status_code == 400
        assert "Name already exists" in response.text

    def test_remove_character(
        self, client: TestClient, mock_character_manager: MagicMock
    ):
        # Arrange
        mock_character_manager.remove_character.return_value = True

        # Act
        response = client.post(
            "/characters/remove", json={"character_id": self.character_id}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_character_manager.remove_character.assert_called_once_with(
            character_id=self.character_id
        )

    def test_remove_character_not_found(
        self, client: TestClient, mock_character_manager: MagicMock
    ):
        # Arrange
        mock_character_manager.remove_character.return_value = False

        # Act
        response = client.post("/characters/remove", json={"character_id": 999})

        # Assert
        assert response.status_code == 404
        assert "Character not found" in response.text

    def test_list_characters(
        self, client: TestClient, mock_character_manager: MagicMock
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
        response = client.post("/characters/list", json={"player_id": self.player_id})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "characters" in data
        assert len(data["characters"]) == 1
        assert data["characters"][0]["name"] == self.character_name
        mock_character_manager.get_characters_for_player.assert_called_once_with(
            player_id=self.player_id
        )
