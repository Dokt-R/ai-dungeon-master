import pytest
from unittest.mock import MagicMock, create_autospec
from sqlmodel import Session
from packages.backend.components.character_manager import CharacterManager
from packages.shared.models import Character, Player
from packages.shared.error_handler import ValidationError, NotFoundError


@pytest.fixture
def mock_session():
    return create_autospec(Session)


@pytest.fixture
def character_manager(mock_session: MagicMock):
    return CharacterManager(session=mock_session)


class TestAddCharacter:
    def test_add_character_normal(
        self, character_manager: CharacterManager, mock_session: MagicMock
    ):
        # Arrange
        player_id = "user-id-1"
        character_name = "Hero"
        character_url = "http://dndbeyond.com/hero"
        mock_session.get.return_value = Player(player_id=player_id)
        mock_session.exec.return_value.first.return_value = None

        # Act
        character = character_manager.add_character(
            player_id, character_name, character_url
        )

        # Assert
        assert character.name == character_name
        assert character.character_url == character_url
        mock_session.get.assert_called_once_with(Player, player_id)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    def test_add_character_missing_player(
        self, character_manager: CharacterManager, mock_session: MagicMock
    ):
        # Arrange
        mock_session.get.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            character_manager.add_character("user-id-2", "Hero")

    def test_add_character_duplicate_name(
        self, character_manager: CharacterManager, mock_session: MagicMock
    ):
        # Arrange
        player_id = "user-id-1"
        character_name = "Hero"
        mock_session.get.return_value = Player(player_id=player_id)
        mock_session.exec.return_value.first.return_value = Character(
            name=character_name, player_id=player_id
        )

        # Act & Assert
        with pytest.raises(ValidationError):
            character_manager.add_character(player_id, character_name)


class TestUpdateCharacter:
    def test_update_character_normal(
        self, character_manager: CharacterManager, mock_session: MagicMock
    ):
        # Arrange
        character_id = 1
        new_name = "Hero2"
        new_url = "url2"
        mock_character = Character(
            character_id=character_id, name="Hero", player_id="user-id-1"
        )
        mock_session.get.return_value = mock_character
        # for duplicate check
        mock_session.exec.return_value.first.return_value = None

        # Act
        result = character_manager.update_character(
            character_id, name=new_name, character_url=new_url
        )

        # Assert
        assert result.name == new_name
        assert result.character_url == new_url
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    def test_update_character_no_fields(self, character_manager: CharacterManager):
        # Act & Assert
        with pytest.raises(ValidationError):
            character_manager.update_character(1)

    def test_update_character_not_found(
        self, character_manager: CharacterManager, mock_session: MagicMock
    ):
        # Arrange
        mock_session.get.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            character_manager.update_character(9999, name="NewName")

    def test_update_character_duplicate_name(
        self, character_manager: CharacterManager, mock_session: MagicMock
    ):
        # Arrange
        character_id = 2
        existing_name = "Hero"
        mock_character = Character(
            character_id=character_id, name="Hero2", player_id="user-id-1"
        )
        mock_session.get.return_value = mock_character
        mock_session.exec.return_value.first.return_value = Character(
            name=existing_name, player_id="user-id-1"
        )

        # Act & Assert
        with pytest.raises(ValidationError):
            character_manager.update_character(character_id, name=existing_name)


class TestRemoveCharacter:
    def test_remove_character_normal(
        self, character_manager: CharacterManager, mock_session: MagicMock
    ):
        # Arrange
        character_id = 1
        mock_character = Character(character_id=character_id)
        mock_session.get.return_value = mock_character

        # Act
        result = character_manager.remove_character(character_id)

        # Assert
        assert result is True
        mock_session.delete.assert_called_once_with(mock_character)
        mock_session.commit.assert_called_once()

    def test_remove_character_not_found(
        self, character_manager: CharacterManager, mock_session: MagicMock
    ):
        # Arrange
        mock_session.get.return_value = None

        # Act
        result = character_manager.remove_character(9999)

        # Assert
        assert result is False


class TestGetCharactersForPlayer:
    def test_get_characters_for_player_normal(
        self, character_manager: CharacterManager, mock_session: MagicMock
    ):
        # Arrange
        player_id = "user-id-1"
        mock_chars = [
            Character(name="Hero", player_id=player_id),
            Character(name="Hero2", player_id=player_id),
        ]
        mock_session.exec.return_value.all.return_value = mock_chars

        # Act
        chars = character_manager.get_characters_for_player(player_id)

        # Assert
        assert len(chars) == 2
        names = {c.name for c in chars}
        assert "Hero" in names and "Hero2" in names

    def test_get_characters_for_player_no_characters(
        self, character_manager: CharacterManager, mock_session: MagicMock
    ):
        # Arrange
        player_id = "user-id-1"
        mock_session.exec.return_value.all.return_value = []

        # Act
        chars = character_manager.get_characters_for_player(player_id)

        # Assert
        assert chars == []
