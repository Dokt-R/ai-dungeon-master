# Components

The backend service is broken down into the following logical components:

* **`ServerSettingsManager`:** Manages the configuration for each Discord server.
* **`CampaignManager`:** Handles logic for creating, starting, and ending campaigns.
* **`PlayerManager`:** Manages players joining a campaign and their characters.
* **`AIOrchestrator`:** The core component that interacts with the CrewAI framework.
* **`MemoryService`:** Manages all tiers of the campaign and session memory.
* **`RulesEngine`:** Provides deterministic results for D\\\&D 5.1 SRD rules by querying the SQLite database.
* **`NotificationService`:** Sends responses to players in their preferred format (text or voice).

