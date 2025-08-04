# Components

The backend service is broken down into the following logical components:

* **`ServerSettingsManager`:** Manages the configuration for each Discord server.
* **`CampaignManager`:** Handles logic for creating, starting, and ending campaigns.
* **`PlayerManager`:** Handles all player participation logic, campaign membership, and character associations.
  - **Responsibilities:**
    - Manages player joining, leaving, and ending campaigns, enforcing that a player can only be joined to one campaign per server at a time.
    - Associates players with characters (existing or new) when joining campaigns.
    - Maintains and updates the player's last active campaign.
    - Provides player status summaries, including campaign participation and character list.
  - **Key Flows:**
    - **Join Campaign:** Validates campaign existence, ensures player is not already joined, associates character, updates last active campaign, and inserts/updates the CampaignPlayers table.
    - **Leave Campaign:** Removes player from campaign, optionally clears last active campaign if leaving the last one.
    - **End Campaign:** Sets player status to 'cmd' (command state) for a campaign, without removing the player.
    - **Get Player Status:** Aggregates player info, campaign participation, and all associated characters.
  - **Database Interactions:**
    - Reads/writes to `Players`, `Campaigns`, `CampaignPlayers`, and `Characters` tables.
    - Enforces uniqueness and referential integrity for player-campaign-character relationships.
  - **API/Data Flows:**
    - Exposed via `/players` API endpoints (see REST API spec).
    - Used by Discord bot and other backend services for player state management.

* **`CharacterManager`:** Manages character creation, updates, removal, and retrieval for players.
  - **Responsibilities:**
    - Handles creation of new characters, ensuring uniqueness of character names per player.
    - Updates character data (name, D&D Beyond URL), enforcing uniqueness constraints.
    - Removes characters and cleans up references in campaign participation.
    - Retrieves all characters for a given player.
  - **Key Flows:**
    - **Add Character:** Validates player existence, inserts new character, enforces name uniqueness.
    - **Update Character:** Updates name and/or D&D Beyond URL, checks for uniqueness.
    - **Remove Character:** Deletes character and sets character_id to NULL in CampaignPlayers for affected rows.
    - **List Characters:** Returns all characters for a player.
  - **Database Interactions:**
    - Reads/writes to `Characters`, `Players`, and `CampaignPlayers` tables.
    - Maintains referential integrity and uniqueness constraints.
  - **API/Data Flows:**
    - Exposed via `/characters` API endpoints (see REST API spec).
    - Used by PlayerManager and external clients for character management.

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