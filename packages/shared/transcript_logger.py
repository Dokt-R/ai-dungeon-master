import os
import json
import asyncio
from datetime import datetime
from typing import Any

LOG_BASE_DIR = os.path.join("data", "saves")

class TranscriptLogger:
    """
    Asynchronous, robust logger for campaign transcripts.
    Writes structured JSONL entries to data/saves/[campaign_id]/transcript.log.
    """

    def __init__(self):
        self._lock = asyncio.Lock()

    async def log_message(self, campaign_id: str, author: str, message: str) -> None:
        """
        Appends a structured log entry to the campaign's transcript log.
        Non-blocking: uses asyncio.to_thread for file I/O.
        """
        log_dir = os.path.join(LOG_BASE_DIR, campaign_id)
        log_path = os.path.join(log_dir, "transcript.log")
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "author": author,
            "message": message
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