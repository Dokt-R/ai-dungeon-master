# Components

The backend service is broken down into the following logical components:

* **`ServerSettingsManager`:** Manages the configuration for each Discord server.
* **`CampaignManager`:** Handles logic for creating, starting, and ending campaigns.
* **`PlayerManager`:** Manages players joining a campaign and their associated character data.
* **`AIOrchestrator`:** The central component that manages the **LangGraph execution flow**. It passes the current game state through the graph's nodes to process player actions and generate responses.
* **`CampaignMemoryService`:** Manages the **four-tiered persistence strategy**. It is responsible for loading the 'Campaign Knowledge Base' into the graph state, appending events to the 'Campaign Chronicle', and providing access to the SQLite 'Rules Library'.
* **`RulesEngine`:** Contains the deterministic functions for D&D 5.1 SRD rules by querying the SQLite database.