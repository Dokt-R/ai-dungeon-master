# Observability

To ensure long-term maintainability and assist in debugging the AI's behavior, the architecture will include:

* **LLM Observability:** Integration with a tracing platform (e.g., LangSmith, LangFuse) to provide detailed, step-by-step traces of the AI's "thought process." This is a foundational task for Epic 2.
* **Campaign Transcript:** A `transcript.log` will be maintained for each campaign, providing a complete, raw record of all player and AI messages for debugging and future summarization features.
## Campaign Transcript Log Format

Each campaign maintains a transcript log at `data/saves/[campaign_id]/transcript.log`. This file records every in-character player message and AI response as a single line of JSON (JSONL format), with the following structure:

```json
{
  "timestamp": "2025-07-31T20:00:00.000000+00:00",
  "author": "PlayerName or AI",
  "message": "The message content goes here."
}
```

- **timestamp**: ISO 8601 UTC timestamp of the message.
- **author**: The player name or "AI" for system-generated responses.
- **message**: The full message content.

### Log Rotation and Size Limits

To prevent unbounded log growth, each `transcript.log` file is automatically rotated when it exceeds 10 MB:
- The current `transcript.log` is renamed to `transcript.log.1`.
- Up to 3 rotated logs are kept (`transcript.log.1`, `transcript.log.2`, `transcript.log.3`).
- The oldest log is deleted when a new rotation occurs and the limit is reached.
- A new `transcript.log` is then started for subsequent entries.

This ensures that recent campaign history is always available, while preventing excessive disk usage for very large or long-running campaigns.