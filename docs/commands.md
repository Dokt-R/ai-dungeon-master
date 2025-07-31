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

## Advanced Usage

- All commands return ephemeral messages by default to avoid channel clutter.
- For campaign management, use `/campaign new`, `/campaign continue`, and `/campaign end` (if available).
- For character management, use `/sheet` to view your character sheet.

For the latest updates and detailed guides, see the [README](../README.MD) or project documentation.