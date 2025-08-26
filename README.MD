# AI Dungeon Master – Monorepo

## Bot Invite Instructions
1. Go to the Discord Developer Portal.
2. Navigate to your application and select the "OAuth2" tab.
3. Under "Scopes", select the `bot` checkbox.
4. Under "Bot Permissions", select the following permissions:
   - View Channels
   - Send Messages
   - Send Messages in Threads
   - Embed Links
   - Read Message History
   - Use Slash Commands
   - (Optional, for advanced features: Manage Messages, Embed Links, Attach Files, etc.)
5. In the "Bot" section of the Developer Portal, under "Privileged Gateway Intents", enable the **Message Content Intent**. This is required for the bot to respond to commands in servers.
6. Click Reset Token if necessary and note the token somewhere for now.
7. Copy the generated OAuth2 URL and use it to invite the bot to your server.

---

## Project Structure

```
/ai-dungeon-master/
├── README.MD
├── pyproject.toml
├── packages/
│   ├── bot/         # Discord bot (Gateway)
│   │   ├── main.py
│   │   └── cogs/
│   ├── backend/     # FastAPI backend service (AI Brain)
│   │   ├── main.py
│   │   ├── api/
│   │   ├── components/
│   └── shared/      # Shared Pydantic models
```

---
# Installation

### Environment Setup

- Create a `.env` file in `packages/bot/` with:
  ```
  DISCORD_BOT_TOKEN=your_bot_token_here
  ```
  Replace `DISCORD_BOT_TOKEN` with your bot's token.

### Quick Start (Docker Compose)

The recommended way to run the project is with Docker Compose. This will start both the backend API and the Discord bot with a single command.

1. **Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/).**

2. **Clone the repository and navigate to the project root:**
   ```sh
   git clone https://github.com/your-org/ai-dungeon-master.git
   cd ai-dungeon-master
   ```

3. **Build and run the stack:**
   ```sh
   # May need sudo rights
   docker compose up --build
   ```
   - The backend API will be available at [http://localhost:8000](http://localhost:8000).
   - The Discord bot will start and connect to Discord using the provided token.

4. **Test the Bot:**
   - Use the `/ping` command in any channel where the bot is present to test its functionality.

#### You can also find the process to manually run services [here](#manual-setup-advanced)

---

# Server Key Onboarding Command Flow

### Commands
- `/help`: Lists all available commands and references advanced help.
- `/getting-started`: Step-by-step onboarding guide for new users and server owners.
- `/cost`: API usage cost info and transparency, with a link to full documentation.
- `/server-setup`: Explains the shared API key model and how to submit a key. Only users with "Administrator" or "Manage Server" permissions can run this command.
- `/server-setkey [API_KEY]`: Allows an admin to submit the server's shared API key. Only users with "Administrator" or "Manage Server" permissions can run this command. The key is securely sent to the backend and never shown to other users.
- `/ping`: Check if the bot is alive.
- `/campaign`: Manage campaigns with subcommands like `new`, `join`, `delete`, and `info`.

> All commands return ephemeral messages by default to avoid channel clutter.
> For advanced help, see [Command Reference](docs/commands.md).


### How It Works

- The bot does **not** store API keys locally. When `/server-setkey` is used, the bot makes a secure API call to the backend service, which handles encryption and storage.
- All key submission and confirmation messages are sent as ephemeral responses, ensuring only the submitting admin can view them.
- Only users with the required permissions can submit or update the server API key.
- All secrets are managed via environment variables and never hardcoded.

---

## Storage and Retrieval Process

- The backend service uses a database to store server API keys and configuration.
- Data is stored in a structured format, managed by SQLAlchemy and SQLModel. The schema is defined in `packages/shared/models.py`.
- The backend exposes RESTful endpoints (see `docs/architecture/api-specification.md`) for the bot and other clients to interact with server settings.
- For more details on the database schema and how to interact with it, refer to `packages/shared/models.py` and `packages/shared/db.py`.

---

## Security Considerations

- API keys are encrypted at rest by the backend using Fernet symmetric encryption.
- Keys are never exposed in logs or non-ephemeral messages.
- All secrets are managed via environment variables.

---

## Development & Testing

- All code is organized as a modular monolith, with clear separation between bot, backend, and shared models.
- Unit and integration tests are located in `packages/bot/tests/` and `packages/backend/tests/`.
- Run all tests with:
  ```bash
  pytest --maxfail=1 --disable-warnings -v
  ```

---

**Note:**
If the bot does not respond to commands in servers, ensure that the "Message Content Intent" is enabled in the Discord Developer Portal for your bot, and that the bot has the required permissions in your server.

---

## Contributing

We welcome contributions from the community! Whether you're fixing bugs, adding features, improving documentation, or suggesting ideas, your help is appreciated.

### Getting Started
- Read our [Contributing Guide](CONTRIBUTING.md) for detailed instructions
- Check the [Issues](https://github.com/your-org/ai-dungeon-master/issues) for good first issues
- Join our community discussions on GitHub Discussions

### Development Workflow
1. Fork the repository and create a feature branch
2. Make your changes with tests
3. Ensure all tests pass: `pytest --maxfail=1 --disable-warnings -v`
4. Submit a pull request with a clear description

### Areas for Contribution
- **Bot Features**: New Discord commands and interactions
- **Backend Services**: API endpoints and business logic
- **Documentation**: Architecture docs, user guides, and tutorials
- **Testing**: Unit tests, integration tests, and test coverage
- **Performance**: Optimization and monitoring improvements

For questions or help, see our [Contributing Guide](CONTRIBUTING.md) or open a discussion.

---

# Manual Setup (Advanced)

If you prefer to run the services manually (not recommended for most users):

#### 1. Install Dependencies

- From the root folder install the prerequisites using `requirements.txt`
  ```bash
  pip install -r requirements.txt
  ```

#### 2. Start the Backend Service

- The backend is a FastAPI app. Start it with:
  ```bash
  uvicorn packages.backend.main:app --reload
  ```
  By default, it runs on `http://localhost:8000`.

- If you do not have **uvicorn** installed, install it with:
  ```bash
  pip install uvicorn[standard]
  ```

#### 3. Start the Bot

- In a separate terminal, run:
  ```bash
  python packages/bot/main.py
  ```

### 4. Test the Bot

- Use the `/ping` command in any channel where the bot is present to test its functionality.

# Observability

## LangSmith AI Tracing (Optional)

The system includes comprehensive AI operation tracing via LangSmith for detailed observability of AI decision-making processes. This feature is **disabled by default** to allow immediate development without API key setup.

### Enabling AI Tracing

To enable LangSmith tracing for AI operations:

1. **Get a LangSmith API Key**:
   - Visit [https://smith.langchain.com/](https://smith.langchain.com/)
   - Create an account or log in with existing credentials
   - Navigate to Settings → API Keys → Create API Key
   - Copy the key (typically starts with `ls__` or `lsv2_`)

2. **Configure Environment Variables**:
   ```bash
   # Add to your environment or .env file
   LANGSMITH_API_KEY=your_langsmith_api_key_here  # Use exact key from LangSmith
   LANGSMITH_TRACING=true  # Enable tracing
   LANGSMITH_PROJECT=ai-dungeon-master  # Optional: project name
   ```

3. **Restart the Services**:
   ```bash
   docker compose down && docker compose up --build
   ```

### What Gets Traced

When enabled, the system automatically traces:
- **LLM API calls** with model information, prompts, and responses
- **AI workflows** with decision points and reasoning
- **Performance metrics** including execution time and token usage
- **Custom trace tags** for AI-specific operations
- **Correlation IDs** linking traces to user requests

### Health Monitoring

Check tracing status via Discord commands:
- `/health observability` - Check LangSmith connection status
- `/health ai` - Check AI services with tracing integration
- `/health general` - Overall system health including observability

### Benefits

- **Step-by-step AI decision tracing** for debugging complex interactions
- **Performance monitoring** for AI operations and LLM calls
- **Cost optimization** insights through token usage tracking
- **Quality assurance** for AI-generated content and responses

**Note**: LangSmith offers a generous free tier suitable for development and small-scale production use.

## Campaign Transcript Logging

- Every campaign has a persistent transcript log saved at `data/saves/[campaign_id]/transcript.log`.
- All in-character player messages and AI responses are recorded in this file.
- Log files are automatically rotated when they exceed 10 MB, with up to 3 rotated logs retained.
- For details on log file format and rotation policy, see `docs/architecture/observability.md`.


### Developer Notes: Campaign Transcript Logging

- Logging is implemented via an async, thread-safe utility: [`packages/shared/transcript_logger.py`](packages/shared/transcript_logger.py:1).
- All log entries are structured as JSONL with `timestamp`, `author`, and `message` fields.
- Campaign IDs are validated for filesystem safety; invalid IDs are rejected and not logged.
- The logging system is fully covered by unit and integration tests (see [`packages/backend/tests/test_transcript_logger.py`](packages/backend/tests/test_transcript_logger.py:1) and [`packages/backend/tests/test_message_processor.py`](packages/backend/tests/test_message_processor.py:1)).
- For the full development story, see [`docs/stories/1.6.story.md`](docs/stories/1.6.story.md:1).
- For log format and rotation policy, see [`docs/architecture/observability.md`](docs/architecture/observability.md:1).