import os
import tempfile
import asyncio
import pytest
from packages.backend.components.message_processor import MessageProcessor


@pytest.mark.asyncio
async def test_process_player_message_logs_to_transcript(monkeypatch):
    # Setup: use a temporary directory for log output
    with tempfile.TemporaryDirectory() as temp_dir:
        # Patch LOG_BASE_DIR in transcript_logger
        from packages.shared import transcript_logger

        monkeypatch.setattr(transcript_logger, "LOG_BASE_DIR", temp_dir)

        processor = MessageProcessor()
        campaign_id = "test_campaign"
        author = "Player1"
        message = "This is an in-character action."

        await processor.process_player_message(campaign_id, author, message)

        log_path = os.path.join(temp_dir, campaign_id, "transcript.log")
        assert os.path.exists(log_path), "Transcript log file was not created"

        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            import json

            entry = json.loads(lines[0])
            assert entry["author"] == author
            assert entry["message"] == message
            assert "timestamp" in entry


@pytest.mark.asyncio
async def test_log_ai_response_logs_to_transcript(monkeypatch):
    # Setup: use a temporary directory for log output
    with tempfile.TemporaryDirectory() as temp_dir:
        # Patch LOG_BASE_DIR in transcript_logger
        from packages.shared import transcript_logger

        monkeypatch.setattr(transcript_logger, "LOG_BASE_DIR", temp_dir)

        processor = MessageProcessor()
        campaign_id = "test_campaign_ai"
        ai_message = "The dragon roars and takes flight."

        await processor.log_ai_response(campaign_id, ai_message)

        log_path = os.path.join(temp_dir, campaign_id, "transcript.log")
        assert os.path.exists(log_path), (
            "Transcript log file was not created for AI response"
        )

        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            import json

            entry = json.loads(lines[0])
            assert entry["author"] == "AI"
            assert entry["message"] == ai_message
            assert "timestamp" in entry


@pytest.mark.asyncio
async def test_log_ai_response_handles_logging_error(monkeypatch):
    # Patch log_message to raise an exception
    class DummyLogger:
        async def log_message(self, *a, **kw):
            raise RuntimeError("Simulated error")

    processor = MessageProcessor()
    processor.transcript_logger = DummyLogger()

    # Should not raise, but print error
    await processor.log_ai_response("cid", "AI says something")


@pytest.mark.asyncio
async def test_campaign_log_integration_multiple_player_and_ai_messages(monkeypatch):
    import json

    # Setup: use a temporary directory for log output
    with tempfile.TemporaryDirectory() as temp_dir:
        # Patch LOG_BASE_DIR in transcript_logger
        from packages.shared import transcript_logger

        monkeypatch.setattr(transcript_logger, "LOG_BASE_DIR", temp_dir)

        processor = MessageProcessor()
        campaign_id = "integration_campaign"
        player_msgs = [
            ("Player1", "Player1 enters the dungeon."),
            ("Player2", "Player2 lights a torch."),
        ]
        ai_msgs = [
            "The dungeon is dark and cold.",
            "A faint growl echoes from the shadows.",
        ]

        # Interleave player and AI messages
        await processor.process_player_message(
            campaign_id, player_msgs[0][0], player_msgs[0][1]
        )
        await processor.log_ai_response(campaign_id, ai_msgs[0])
        await processor.process_player_message(
            campaign_id, player_msgs[1][0], player_msgs[1][1]
        )
        await processor.log_ai_response(campaign_id, ai_msgs[1])

        log_path = os.path.join(temp_dir, campaign_id, "transcript.log")
        assert os.path.exists(log_path), "Transcript log file was not created"

        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 4, f"Expected 4 log entries, got {len(lines)}"
            entries = [json.loads(line) for line in lines]

        # Check order and structure
        assert entries[0]["author"] == "Player1"
        assert entries[0]["message"] == player_msgs[0][1]
        assert "timestamp" in entries[0]

        assert entries[1]["author"] == "AI"
        assert entries[1]["message"] == ai_msgs[0]
        assert "timestamp" in entries[1]

        assert entries[2]["author"] == "Player2"
        assert entries[2]["message"] == player_msgs[1][1]
        assert "timestamp" in entries[2]

        assert entries[3]["author"] == "AI"
        assert entries[3]["message"] == ai_msgs[1]
        assert "timestamp" in entries[3]


@pytest.mark.asyncio
async def test_process_player_message_handles_logging_error(monkeypatch):
    # Patch transcript_logger.log_message to raise an exception
    class DummyLogger:
        async def log_message(self, *a, **kw):
            raise RuntimeError("Simulated error")

    processor = MessageProcessor()
    processor.transcript_logger = DummyLogger()

    # Should not raise, but print error
    await processor.process_player_message("cid", "Player1", "Player says something")
