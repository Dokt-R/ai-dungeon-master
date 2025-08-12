import pytest
from unittest.mock import MagicMock, create_autospec, patch
from pydantic import SecretStr
from sqlmodel import Session
from cryptography.fernet import Fernet

from packages.backend.components.server_manager import ServerSettingsManager
from packages.shared.models import Server


@pytest.fixture
def mock_session():
    return create_autospec(Session)


@pytest.fixture
def server_manager(mock_session: MagicMock):
    # Patch the _load_encryption_key to avoid dealing with environment variables
    with patch.object(
        ServerSettingsManager,
        "_load_encryption_key",
        return_value=Fernet.generate_key(),
    ) as mock_load_key:
        manager = ServerSettingsManager(session=mock_session)
        # Keep the key accessible for tests
        manager.mock_key = mock_load_key.return_value
        yield manager


def test_store_and_retrieve_api_key(
    server_manager: ServerSettingsManager, mock_session: MagicMock
):
    # Arrange
    server_id = "test_server"
    api_key = "test_api_key"
    config = Server(
        server_id=server_id,
        api_key=SecretStr(api_key),
        dm_roll_visibility="public",
        player_roll_mode="auto",
        character_sheet_mode="digital_sheet",
    )
    mock_session.get.return_value = None  # Simulate no existing config

    # Act
    server_manager.store_server_config(config)

    # Assert that the config was added and committed
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

    # Now, test retrieval
    # We need to get the encrypted value that would have been stored
    fernet = Fernet(server_manager.mock_key)
    encrypted_key = fernet.encrypt(api_key.encode()).decode()
    mock_session.get.return_value = Server(server_id=server_id, api_key=encrypted_key)

    retrieved_key = server_manager.retrieve_api_key(server_id)
    assert retrieved_key == api_key


def test_store_empty_api_key(server_manager: ServerSettingsManager):
    # Arrange
    config = Server(
        server_id="test_server",
        api_key=SecretStr(""),  # Empty API key
    )

    # Act & Assert
    with pytest.raises(ValueError, match="API key must not be empty."):
        server_manager.store_server_config(config)


def test_retrieve_nonexistent_api_key(
    server_manager: ServerSettingsManager, mock_session: MagicMock
):
    # Arrange
    mock_session.get.return_value = None

    # Act
    retrieved_key = server_manager.retrieve_api_key("nonexistent_server")

    # Assert
    assert retrieved_key is None


def test_get_full_server_config(
    server_manager: ServerSettingsManager, mock_session: MagicMock
):
    # Arrange
    server_id = "test_server_full_config"
    api_key = "test_full_api_key"
    fernet = Fernet(server_manager.mock_key)
    encrypted_key = fernet.encrypt(api_key.encode()).decode()

    mock_db_config = Server(
        server_id=server_id,
        api_key=encrypted_key,
        dm_roll_visibility="hidden",
        player_roll_mode="physical",
        character_sheet_mode="physical_sheet",
    )
    mock_session.get.return_value = mock_db_config

    # Act
    retrieved_config = server_manager.get_server_config(server_id)

    # Assert
    assert retrieved_config is not None
    assert retrieved_config.server_id == server_id
    assert retrieved_config.api_key.get_secret_value() == api_key
    assert retrieved_config.dm_roll_visibility == "hidden"
