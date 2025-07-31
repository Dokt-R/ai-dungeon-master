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
- Data is stored in a structured format, following the defined database schema located in `packages/backend/database_schema_extension.sql`.
- The backend exposes RESTful endpoints (see `docs/architecture/api-specification.md`) for the bot and other clients to interact with server settings.
- For more details on the database schema and how to interact with it, refer to the `database_schema_extension.sql` file.

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