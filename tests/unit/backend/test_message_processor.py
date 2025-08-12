import pytest
from unittest.mock import AsyncMock, patch
from packages.backend.components.message_processor import MessageProcessor
from packages.shared.transcript_logger import TranscriptLogger


@pytest.fixture
def mock_transcript_logger():
    # We patch the class in the module where it's used
    with patch(
        "packages.backend.components.message_processor.TranscriptLogger",
        spec=TranscriptLogger,
    ) as mock_logger_class:
        # Configure the instance that will be created
        mock_instance = mock_logger_class.return_value
        mock_instance.log_message = AsyncMock()
        yield mock_instance


@pytest.mark.asyncio
async def test_process_player_message_logs_to_transcript(mock_transcript_logger):
    # Arrange
    processor = MessageProcessor()
    campaign_id = "test_campaign"
    author = "Player1"
    message = "This is an in-character action."

    # Act
    await processor.process_player_message(campaign_id, author, message)

    # Assert
    mock_transcript_logger.log_message.assert_awaited_once_with(
        campaign_id, author, message
    )


@pytest.mark.asyncio
async def test_log_ai_response_logs_to_transcript(mock_transcript_logger):
    # Arrange
    processor = MessageProcessor()
    campaign_id = "test_campaign_ai"
    ai_message = "The dragon roars and takes flight."

    # Act
    await processor.log_ai_response(campaign_id, ai_message)

    # Assert
    mock_transcript_logger.log_message.assert_awaited_once_with(
        campaign_id, "AI", ai_message
    )


@pytest.mark.asyncio
async def test_process_player_message_handles_logging_error(
    mock_transcript_logger, capsys
):
    # Arrange
    processor = MessageProcessor()
    mock_transcript_logger.log_message.side_effect = RuntimeError("Simulated error")

    # Act
    await processor.process_player_message("cid", "Player1", "Player says something")

    # Assert
    captured = capsys.readouterr()
    assert "Error logging message: Simulated error" in captured.out
    mock_transcript_logger.log_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_log_ai_response_handles_logging_error(mock_transcript_logger, capsys):
    # Arrange
    processor = MessageProcessor()
    mock_transcript_logger.log_message.side_effect = RuntimeError("Simulated error")

    # Act
    await processor.log_ai_response("cid", "AI says something")

    # Assert
    captured = capsys.readouterr()
    assert "Error logging AI response: Simulated error" in captured.out
    mock_transcript_logger.log_message.assert_awaited_once()