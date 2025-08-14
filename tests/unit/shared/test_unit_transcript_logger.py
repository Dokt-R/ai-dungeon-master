from unittest.mock import call, patch

import pytest

from packages.shared.transcript_logger import TranscriptLogger


@pytest.mark.asyncio
@patch("packages.shared.transcript_logger.os.makedirs")
@patch("packages.shared.transcript_logger.asyncio.to_thread")
async def test_log_message_writes_to_file(mock_to_thread, mock_makedirs):
    # Arrange
    logger = TranscriptLogger()
    campaign_id = "test_campaign"
    author = "Player1"
    message = "Hello, world!"

    # Act
    await logger.log_message(campaign_id, author, message)

    # Assert
    mock_makedirs.assert_called_once()
    # Check that rotate and append were called via to_thread
    assert mock_to_thread.call_count == 2
    # Check that _rotate_if_needed was called
    assert mock_to_thread.call_args_list[0].args[0] == logger._rotate_if_needed
    # Check that _append_line was called with a valid line
    append_call = mock_to_thread.call_args_list[1]
    assert append_call.args[0] == logger._append_line
    assert '"author": "Player1"' in append_call.args[2]
    assert '"message": "Hello, world!"' in append_call.args[2]


@pytest.mark.asyncio
@patch("packages.shared.transcript_logger.print")
async def test_log_message_invalid_campaign_id(mock_print):
    # Arrange
    logger = TranscriptLogger()
    # Act
    await logger.log_message("invalid/id", "author", "message")
    # Assert
    mock_print.assert_called_once_with(
        "[TranscriptLogger] Invalid campaign_id: 'invalid/id'"
    )


@patch("packages.shared.transcript_logger.os")
def test_rotate_if_needed(mock_os):
    # Arrange
    log_path = "/fake/dir/transcript.log"
    logger = TranscriptLogger()

    # Scenario 1: File doesn't exist, should do nothing
    mock_os.path.exists.return_value = False
    logger._rotate_if_needed(log_path)
    mock_os.rename.assert_not_called()

    # Scenario 2: File exists but is not large enough
    mock_os.path.exists.return_value = True
    mock_os.path.getsize.return_value = 100  # Less than MAX_LOG_SIZE_BYTES
    logger._rotate_if_needed(log_path)
    mock_os.rename.assert_not_called()

    # Scenario 3: File is large enough, should rotate
    mock_os.path.getsize.return_value = 999999999  # More than MAX_LOG_SIZE_BYTES
    # Simulate no old logs existing
    mock_os.path.exists.side_effect = [
        True,  # log_path
        False,  # log_path.3
        False,  # log_path.1
        False,  # log_path.2
    ]
    logger._rotate_if_needed(log_path)
    mock_os.rename.assert_called_once_with(log_path, f"{log_path}.1")

    # Scenario 4: Rotation with existing rotated logs
    mock_os.rename.reset_mock()
    mock_os.path.exists.side_effect = [
        True,  # log_path
        True,  # log_path.3 (oldest) -> should be removed
        True,  # log_path.2 -> should be moved to .3
        True,  # log_path.1 -> should be moved to .2
    ]
    logger._rotate_if_needed(log_path)
    mock_os.remove.assert_called_once_with(f"{log_path}.3")
    assert mock_os.rename.call_count == 3
    assert call(f"{log_path}.2", f"{log_path}.3") in mock_os.rename.call_args_list
    assert call(f"{log_path}.1", f"{log_path}.2") in mock_os.rename.call_args_list
    assert call(log_path, f"{log_path}.1") in mock_os.rename.call_args_list


@pytest.mark.parametrize(
    "campaign_id,expected",
    [
        ("valid_campaign", True),
        ("valid-campaign_123", True),
        ("a" * 100, True),
        ("", False),
        ("   ", False),
        (".", False),
        ("..", False),
        ("a" * 101, False),
        ("invalid/path", False),
        ("invalid\\path", False),
        ("invalid\0null", False),
        ("..invalid", False),
    ],
)
def test_is_valid_campaign_id(campaign_id, expected):
    assert TranscriptLogger._is_valid_campaign_id(campaign_id) == expected
