# AI Dungeon Master Bot – Command Reference

This document lists all available bot commands, their descriptions, and advanced usage notes.

## Core Commands

- **/help**  
  Lists all available commands and references this advanced help.
  
- **/getting-started**  
  Step-by-step onboarding guide for new users and server owners.

- **/cost**  
  API usage cost info and transparency, with a link to full documentation. See the full cost breakdown and real-world examples (here)[https://example.com/docs/costs.md]

- **/server-setup**  
  Explains the shared API key model and how to submit a key. Only users with "Administrator" or "Manage Server" permissions can run this command.

- **/server-setkey [API_KEY]**
  Allows an admin to submit the server's shared API key. Only users with "Administrator" or "Manage Server" permissions can run this command. The key is securely sent to the backend and never shown to other users.

- **/ping**
  Check if the bot is alive.

## Sync Commands (Admin Only)

These commands manage automatic synchronization of Discord server members to the database as players. **These commands are only visible and available to users with "Administrator" or "Manage Server" permissions.**

- **/sync members**
  Sync all current server members to the database as players. Shows progress and reports how many members were created/updated.

- **/sync start**
  Start automatic periodic member sync that runs every hour to check for new members and username changes.

- **/sync stop**
  Stop the periodic member sync task.

- **/sync status**
  Check if the periodic sync is currently running and when the next sync is scheduled.

- **/sync restart**
  Restart the periodic member sync task.

## Advanced Usage

- All commands return ephemeral messages by default to avoid channel clutter.
- For campaign management, use the `/campaign` command with its subcommands:
  - `new`: Create a new campaign.
  - `join`: Join an existing campaign.
  - `continue`: Continue your last active campaign.
  - `end`: End your current campaign session.
  - `delete`: Delete a campaign (owner or admin only).
  - `info`: Get information about a campaign.
- For player synchronization, use the `/sync` command with its subcommands:
  - `members`: Sync current server members to database.
  - `start`: Start periodic member sync.
  - `stop`: Stop periodic member sync.
  - `status`: Check sync status.
  - `restart`: Restart periodic sync.
- For character management, use `/sheet` to view your character sheet.

For the latest updates and detailed guides, see the [README](../README.MD) or project documentation.