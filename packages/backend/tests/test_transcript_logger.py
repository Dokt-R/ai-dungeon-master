import os
import json
import asyncio
import shutil
import tempfile
import pytest

from packages.shared.transcript_logger import TranscriptLogger


@pytest.mark.asyncio
async def test_log_message_creates_log_file_and_appends_entry():
    temp_dir = tempfile.mkdtemp()
    logger = TranscriptLogger()
    campaign_id = "test_campaign"
    author = "Player1"
    message = "Hello, world!"

    # Patch LOG_BASE_DIR to temp_dir for isolation
    orig_base = logger.__class__.__dict__["__init__"].__globals__["LOG_BASE_DIR"]
    logger.__class__.__dict__["__init__"].__globals__["LOG_BASE_DIR"] = temp_dir

    try:
        await logger.log_message(campaign_id, author, message)
        log_path = os.path.join(temp_dir, campaign_id, "transcript.log")
        assert os.path.exists(log_path), "Log file was not created"
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1, "Log file should have one entry"
        entry = json.loads(lines[0])
        assert entry["author"] == author
        assert entry["message"] == message
        assert "timestamp" in entry
    finally:
        # Restore LOG_BASE_DIR and clean up
        logger.__class__.__dict__["__init__"].__globals__["LOG_BASE_DIR"] = orig_base
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "campaign_id,should_create",
    [
        ("", False),  # empty
        ("   ", False),  # whitespace only
        (".", False),  # reserved
        ("..", False),  # reserved
        ("valid_campaign", True),  # valid
        ("valid-campaign_123", True),  # valid
        ("invalid/with/slash", False),
        ("invalid\\with\\backslash", False),
        ("invalid..dots", False),
        ("nullbyte\0inid", False),
        ("control\x1fchar", False),
        ("unicode\u2215separator", False),  # division slash
        ("unicode\u29f5separator", False),  # reversed solidus
        ("a" * 100, True),  # max valid length
        ("a" * 101, False),  # too long
    ],
)
async def test_log_message_campaign_id_edge_cases(tmp_path, campaign_id, should_create):
    logger = TranscriptLogger()
    # Patch LOG_BASE_DIR to tmp_path for isolation
    orig_base = logger.__class__.__dict__["__init__"].__globals__["LOG_BASE_DIR"]
    logger.__class__.__dict__["__init__"].__globals__["LOG_BASE_DIR"] = str(tmp_path)
    author = "EdgeTester"
    message = "Edge case test"
    try:
        await logger.log_message(campaign_id, author, message)
        log_path = os.path.join(tmp_path, campaign_id, "transcript.log")
        if should_create:
            assert os.path.exists(log_path), (
                f"Log file should be created for valid campaign_id: {repr(campaign_id)}"
            )
        else:
            assert not os.path.exists(log_path), (
                f"Log file should not be created for invalid campaign_id: {repr(campaign_id)}"
            )
    finally:
        logger.__class__.__dict__["__init__"].__globals__["LOG_BASE_DIR"] = orig_base


@pytest.mark.asyncio
async def test_log_message_handles_invalid_campaign_id():
    logger = TranscriptLogger()
    # Patch LOG_BASE_DIR to a temp dir
    temp_dir = tempfile.mkdtemp()
    orig_base = logger.__class__.__dict__["__init__"].__globals__["LOG_BASE_DIR"]
    logger.__class__.__dict__["__init__"].__globals__["LOG_BASE_DIR"] = temp_dir

    try:
        # Use an invalid campaign_id (e.g., with forbidden characters)
        campaign_id = "invalid/../id"
        author = "Player2"
        message = "Should fail gracefully"
        # Should not raise, but print error
        await logger.log_message(campaign_id, author, message)
        # No file should be created
        log_path = os.path.join(temp_dir, campaign_id, "transcript.log")
        assert not os.path.exists(log_path)
    finally:
        logger.__class__.__dict__["__init__"].__globals__["LOG_BASE_DIR"] = orig_base
        shutil.rmtree(temp_dir)
