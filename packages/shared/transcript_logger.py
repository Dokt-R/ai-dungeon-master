import asyncio
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

LOG_BASE_DIR = os.path.join("data", "saves")


class TranscriptLogger:
    """
    Asynchronous, robust logger for campaign transcripts.
    Writes structured JSONL entries to data/saves/[campaign_id]/transcript.log.
    """

    @staticmethod
    def _is_valid_campaign_id(campaign_id: str) -> bool:
        # Reject empty/whitespace, reserved names, path separators, control chars, unicode separators, only-dots, and too long
        if not campaign_id or campaign_id.strip() == "":
            return False
        if campaign_id in (".", ".."):
            return False
        if len(campaign_id) > 100:
            return False
        # Only dots (e.g., "...", "....") are not allowed
        if re.fullmatch(r"\.+", campaign_id):
            return False
        # Control chars (ASCII < 32)
        if any(ord(c) < 32 for c in campaign_id):
            return False
        # Unicode path separators
        if "\u2215" in campaign_id or "\u29f5" in campaign_id:
            return False
        # Path separators
        if "/" in campaign_id or "\\" in campaign_id or "\0" in campaign_id:
            return False
        # Only allow: alphanum, dash, underscore, space, dot, and unicode (emoji, CJK, etc.)
        # Forbid any character not in the allowed set
        if not re.fullmatch(r"[ \w\-.]+", campaign_id, re.UNICODE):
            return False
        # Forbid any occurrence of ".." anywhere in the campaign_id
        if ".." in campaign_id:
            return False
        return True

    def __init__(self):
        self._lock = asyncio.Lock()

    async def log_message(self, campaign_id: str, author: str, message: str) -> None:
        """
        Appends a structured log entry to the campaign's transcript log.
        Non-blocking: uses asyncio.to_thread for file I/O.
        """
        if not self._is_valid_campaign_id(campaign_id):
            print(f"[TranscriptLogger] Invalid campaign_id: {campaign_id!r}")
            return
        log_dir = os.path.join(LOG_BASE_DIR, campaign_id)
        log_path = os.path.join(log_dir, "transcript.log")
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "author": author,
            "message": message,
        }
        try:
            os.makedirs(log_dir, exist_ok=True)
            line = json.dumps(entry, ensure_ascii=False)
            # Use a lock to avoid race conditions in concurrent writes
            async with self._lock:
                await asyncio.to_thread(self._append_line, log_path, line)
        except Exception as e:
            # Optionally, integrate with shared error handler
            print(f"[TranscriptLogger] Error writing log: {e}")

    @staticmethod
    def _append_line(path: str, line: str) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
