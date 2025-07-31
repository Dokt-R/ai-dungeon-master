# Components

The backend service is broken down into the following logical components:

* **`ServerSettingsManager`:** Manages the configuration for each Discord server.
* **`CampaignManager`:** Handles logic for creating, starting, and ending campaigns.
* **`PlayerManager`:** Manages players joining a campaign and their associated character data.
* **`AIOrchestrator`:** The central component that manages the **LangGraph execution flow**. It passes the current game state through the graph's nodes to process player actions and generate responses.
* **`CampaignMemoryService`:** Manages the **four-tiered persistence strategy**. It is responsible for loading the 'Campaign Knowledge Base' into the graph state, appending events to the 'Campaign Chronicle', and providing access to the SQLite 'Rules Library'.
* **`RulesEngine`:** Contains the deterministic functions for D&D 5.1 SRD rules by querying the SQLite database.
## Shared Error Handling Utility for Discord Commands

A centralized error handling utility is provided in [`packages/shared/error_handler.py`](../../packages/shared/error_handler.py) to standardize error logging and user-facing error messages in Discord command methods.

### Usage

- Import the `discord_error_handler` decorator:
  ```python
  from packages.shared.error_handler import discord_error_handler
  ```

- Apply the decorator to any Discord command method:
  ```python
  @discord.app_commands.command(name="example", description="Example command")
  @discord_error_handler()
  async def example_command(self, interaction: discord.Interaction):
      # Command logic here
      ...
  ```

- The decorator will:
  - Catch `ValidationError` and `NotFoundError`, log them, and send the error message to the user.
  - Catch all other exceptions, log them, and send a generic fallback message.
  - Ensure the Discord interaction is always responded to, avoiding "interaction failed" errors.

### Best Practices

- Remove manual try/except/handle_error/send_message blocks from command methods.
- Use the decorator for all Discord command methods to ensure consistent error handling.
- For custom fallback messages, pass the `fallback_message` argument to the decorator.

See [`packages/shared/error_handler.py`](../../packages/shared/error_handler.py) for implementation details.