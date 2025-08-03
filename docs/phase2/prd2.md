# PRD - Phase 2: Grand Vision

## Goals and Background Context

### Goals
* **To Achieve "Best-in-Class" Status:** To design and build a platform with such a high degree of quality, innovation, and user-centric design that it is recognized by the TTRPG community as a "fine piece of work" and the definitive leader in its space.
* **To Become an Indispensable Tool for DMs:** To build a "Creative Suite" so powerful and useful that it becomes the go-to tool for human Dungeon Masters, even for their real-world games.
* **To Foster a Thriving Community:** To build a deeply engaged and loyal user base across both player and creator segments by delivering powerful, community-requested features.
* **To Unlock True Campaign Freedom:** To empower users to play *their* way by building an advanced **Content Ingestion** system that allows them to integrate non-SRD and homebrew materials.
* **To Introduce a Premium Experience:** To introduce and validate a premium multimedia experience through the integration of high-quality voice and dynamic image generation.

### Background Context
The initial MVP was designed to prove the core viability of an AI-driven Dungeon Master. This next phase of development builds upon that success, aiming to solve the deeper, more complex challenges of group-based tabletop roleplaying. The focus will be on delivering a suite of advanced, community-requested features that provide unparalleled flexibility, immersion, and creative freedom, solidifying the project's position as the most powerful open-source tool in its class.

### Change Log

| Date       | Version | Description                               | Author      |
| :---       | :---    | :---                                      | :---        |
| 2025-08-02 | 1.0     | Initial draft based on Phase 2 Brief      | John, PM    |

## Requirements

### Functional Requirements
1.  **FR1 (Party System):** The system shall provide a full party management system, allowing a user to create a party, generate an invite name, and for other players to join using that name.
2.  **FR2 (Multi-Campaign System):** The system shall allow users to create, manage, and delete multiple distinct campaigns on the same server.
3.  **FR3 (Content Ingestion):** The system shall provide a secure, local-first mechanism for users to upload, parse, and use non-SRD or homebrew content in their private games.
4.  **FR4 (Premium TTS):** The system shall integrate with the ElevenLabs API to provide high-quality, premium voice narration.
5.  **FR5 (Image Generation):** The system shall integrate with an image generation API to create character avatars and narrative scenes on demand.
6.  **FR6 (Map & Location System):** The system shall support the uploading of custom maps and the tracking of the party's location, including a dynamic "Fog of War" feature.
7.  **FR7 (Persistent World):** The architecture must support a persistent world model, allowing the state of the world to be shared and affected by multiple independent parties.
8.  **FR8 (AI Auto-Play):** The system shall provide an optional mode for the AI to take control of a missing player's character, with that player's prior consent.
9.  **FR9 (Homebrew Creator):** The system shall provide a guided, template-based interface (`/homebrew create`) for users to create their own content, including AI-powered balance checks.
10. **FR10 (Human DM Assistant Mode):** The system shall provide a mode where the AI DM's narrative generation is disabled, but all other multimedia and organizational tools are available to a human DM.
11. **FR11 (Campaign Wiki):** The system shall auto-generate a locally hosted web interface to allow users to browse and edit their campaign's lore files.
12. **FR12 (AI Conversation Director):** The system shall provide an optional mode where the bot can analyze voice chat for off-topic drift and gently re-engage the party with narrative prompts.

### Non-Functional Requirements
1.  **NFR1 (Multimedia Latency):** The generation and delivery of new multimedia assets (voice and images) should not significantly disrupt the narrative flow of the game.
2.  **NFR2 (Content Isolation):** User-ingested custom content for one campaign must be strictly isolated and must not be accessible to or influence any other campaign.
3.  **NFR3 (Wiki Performance):** The localhost campaign wiki must be lightweight and responsive, with near-instantaneous loading and editing capabilities.
4.  **NFR4 (Analytics & Privacy):** The new feature usage analytics module must be fully anonymous and must not collect any personally identifiable information or specific campaign content.

## User Interface Design Goals

### Overall UX Vision
The UX vision for Phase 2 is to evolve the bot from a conversational partner into a comprehensive and intuitive **Creative & Command Center**. The interface must seamlessly blend immersive, narrative-driven gameplay with powerful, user-friendly tools for both players and creators. The technology should feel like an extension of the DM's imagination, empowering them without getting in the way.

### Key Interaction Paradigms
* **Conversational Gameplay:** The core voice-first and text-based interaction for in-character roleplaying will remain the primary paradigm for players.
* **Command-Driven Creation:** The new "Creative Suite" will be accessed via a clear, hierarchical command structure (e.g., `/homebrew create npc`), which will guide the user through the creation process with interactive prompts and templates.
* **Web-Based Wiki:** The auto-generated Campaign Wiki will be a separate, web-based interface, providing a rich, graphical environment for Browse and editing campaign lore.

### Core Screens and Views
* **New: The Campaign Wiki:** A responsive, locally hosted web page that displays all campaign lore (NPCs, locations, etc.) in a clean, searchable, and editable format.
* **New: Homebrew Creator Flow:** A series of interactive bot messages and modals that guide a user through the creation of a new asset, providing feedback and balance checks.
* **New: Content Ingestion View:** An interface (likely a series of commands) for a user to manage their custom content, including viewing a list of ingested sources and checking their status.
* **New: Party Management View:** A command (`/party view`) that displays a summary of the current party, including a list of player characters and their status.
* **New: Campaign Settings View:** A unified settings command (`/settings campaign`) that opens an interactive view where the host can toggle key features for their campaign (Premium TTS, Image Generation, AI Conversation Director, Human DM Assistant Mode).
* **New: Map & Token View:** An embed within Discord that displays the current location map, player tokens, and dynamic Fog of War.
* **Enhanced: Character Sheet View:** The existing multi-page character sheet will be enhanced to include any new data from the "Living World" (e.g., new traits, reputation with factions).

### Accessibility
We will continue to adhere to **WCAG 2.1 Level AA** standards, with a particular focus on ensuring the new Campaign Wiki interface is fully accessible.

### Branding
The visual identity will be extended from the Discord bot to the new Campaign Wiki, maintaining the "classic fantasy sourcebook" theme.

## Technical Assumptions

### Repository & Service Architecture
* **Repository Structure:** The project will continue to be housed in a single **Monorepo**.
* **Service Architecture:** The architecture will continue to be a **Modular Monolith**.

### Testing Requirements
* **Testing Strategy:** The project will continue to require, at a minimum, **Unit and Integration tests** using the **Pytest** framework.

### New Technical Assumptions for Phase 2
* **Primary AI Framework:** The backend will be architected around **LangGraph**.
* **Data Persistence:** The project will expand its **Polyglot Persistence** strategy, using SQLite for the "Rules Library," YAML files for the "Campaign Knowledge Base," and a new, lightweight, locally hosted web server for the "Campaign Wiki" interface.
* **Multimedia Integration:** The architecture must be designed to accommodate real-time, low-latency calls to external multimedia APIs (ElevenLabs for TTS, and an image generation provider).
* **Security:** The new Content Ingestion system must be designed with a "security-first" mindset.

## Epic List (Final Revised Order)

* **Epic 1: Immersive Multimedia Integration:** Integrate premium ElevenLabs voices, the AI Soundtrack Director, and the dynamic Image Generation system.
* **Epic 2: Foundational Quality of Life:** Implement the essential "gap-filling" features from the MVP, including the Turn Order Tracker, Action/Rule Helpers, Character Sheet Sync, and the full Whisper system.
* **Epic 3: The TTRPG Creative Suite:** Build the powerful "creator mode" (`/homebrew create`) with AI-powered balance checks and creative suggestions, as well as the "Human DM Assistant" mode.
* **Epic 4: Advanced Content Ingestion:** Build the secure, local-first system for users to ingest and use custom, non-SRD content.
* **Epic 5: The Auto-Generated Campaign Wiki:** Develop the locally hosted web interface that automatically generates a browsable and editable wiki from the campaign's data files.
* **Epic 6: Advanced Party & Campaign Management:** Implement the full Party & Invite System and the Multi-Campaign Management tools.
* **Epic 7: Advanced Gameplay & World Systems:** Build the Map & Location system with Dynamic Fog of War, the AI Notetaker, and AI-powered summaries.
* **Epic 8: The Living World Engine:** Implement the most ambitious features, including the "Persistent World" architecture, the Dynamic World Engine for NPCs, AI Companions, and AI Auto-Play for missing players.

## Epic 1: Immersive Multimedia Integration

**Expanded Goal:** The goal of this epic is to introduce a rich, multi-sensory layer to the gameplay experience. By the end of this epic, the bot will be able to deliver emotionally resonant voice narration using a premium TTS service and generate beautiful, context-aware images for key scenes and characters. This epic is designed to deliver the "wow" factor and a premium feel, attracting new users and delighting our existing community.

---
### Story 1.1: Campaign Settings Framework
**As a** campaign host, **I want** a unified and interactive settings command, **so that** I can easily manage and toggle all the new features for my campaign from one place.
#### Acceptance Criteria
1.  A user can successfully run the `/settings campaign` command.
2.  The bot responds with an interactive view for managing campaign settings.
3.  The view is designed to be easily expandable with new toggles and options in future stories.
4.  The system can successfully save and retrieve a setting chosen by the user in this view.

---
### Story 1.2: Premium TTS Integration
**As a** player, **I want** to hear the Dungeon Master's narration in a high-quality, expressive voice, **so that** I can be more deeply immersed in the story.
#### Acceptance Criteria
1. The system integrates with the ElevenLabs API for Text-to-Speech generation.
2. A new option is successfully added to the `/settings campaign` view to enable or disable "Premium Voice Narration."
3. When enabled, the `NotificationService` sends the AI's narrative text to the ElevenLabs API and plays the resulting audio in the correct voice channel.
4. The integration gracefully handles potential API errors from ElevenLabs.

---
### Story 1.3: Implement Advanced & Context-Aware Image Generation
**As a** Dungeon Master or Player, **I want** a powerful and context-aware system for generating images, **so that** I can create beautiful, stylistically consistent visuals for my campaign with minimal effort.
#### Tasks / Subtasks
- [ ] **Task 1:** Implement the foundational `/imagine` command with a subcommand structure (`/imagine <type> [prompt]`).
- [ ] **Task 2:** Build the `/imagine character` subcommand, including the backend logic to fetch a player's character sheet data and use it to construct a detailed descriptive prompt.
- [ ] **Task 3:** Build the generic subcommands: `/imagine npc [description]`, `/imagine location [description]`, and `/imagine scene [description]`.
- [ ] **Task 4:** Create a "Prompt Enhancer" module in the backend. This module will automatically inject keywords and phrases from our project's "Style Guide" (e.g., "classic fantasy ink drawing style, mysterious, epic") into the user's prompt before sending it to the Image Generation API.
- [ ] **Task 5:** Add a new "Image Generation Settings" section to the `/settings campaign` view with toggles for automatic image generation (for new locations, important NPCs, and epic moments).
- [ ] **Task 6:** Implement the backend logic that listens for in-game events and triggers automatic image generation based on the campaign's settings.
#### Acceptance Criteria
1. The new `/imagine` command is created and supports the subcommands: `character`, `npc`, `location`, and `scene`.
2. When a player uses `/imagine character`, the system automatically generates a detailed prompt based on their linked character sheet data and our style guide, then creates and displays the avatar image.
3. When a user provides a prompt for an NPC, location, or scene, the backend's "Prompt Enhancer" successfully augments the prompt with style guide keywords to ensure a consistent artistic style in the generated image.
4. The `/settings campaign` view contains a dedicated, functional section for managing all automatic image generation toggles.
5. When an automatic generation setting is enabled, the system successfully generates and displays a relevant image at the appropriate narrative moment (e.g., upon discovering a new location).
6. The system includes robust error handling for the Image Generation API across all subcommands and automatic triggers.

## Epic 2: Foundational Quality of Life

**Expanded Goal:** The goal of this epic is to perfect the core gameplay loop by implementing essential "quality of life" features that players expect. This includes providing clear in-combat information, easy access to rules, a seamless way to keep character sheets updated, and robust tools for private communication. This epic focuses on the small details that create a smooth, frictionless, and professional-feeling user experience.

---
### Story 2.1: Implement Turn Order Tracker
**As a** player in combat, **I want** a simple command to see the initiative order, **so that** I always know whose turn it is and who is coming up next.
#### Acceptance Criteria
1. A new command, `/turn-order`, is created.
2. When used during an active combat encounter, the bot displays a clean, ordered list of all combatants (players and monsters) and their initiative scores.
3. If used outside of combat, the bot responds with a helpful message like, "No combat is currently in progress."

---
### Story 2.2: Implement Player Helper Commands
**As a** new player, **I want** simple commands to remind me of my options and the game's rules, **so that** I can participate confidently without slowing down the game.
#### Acceptance Criteria
1. A new command, `/action-list`, is created that displays a list of common actions a player can take on their turn (e.g., Attack, Cast a Spell, Dodge, Help).
2. A new command, `/rule [topic]`, is implemented that allows a player to query the SRD Rules Library (e.g., `/rule grappling`).
3. The bot successfully retrieves and displays the relevant rule from the SQLite database.
4. If a rule is not found, the bot provides a user-friendly "not found" message.

---
### Story 2.3: Implement Character Sheet Sync
**As a** player using a Digital Sheet, **I want** a way to tell the bot to re-sync my character sheet, **so that** its data reflects my latest level-ups and equipment changes.
#### Acceptance Criteria
1. A new command, `/sheet refresh`, is created.
2. When a player uses this command, the backend service re-fetches the data from their linked character sheet URL.
3. The bot's internal representation of the character's stats and abilities is successfully updated with the new data.
4. The bot sends a confirmation message to the player upon successful synchronization.

---
### Story 2.4: Implement Whisper System
**As a** player, **I want** the ability to send private messages to other players and the DM, **so that** I can perform secret actions and engage in private conversations.
#### Acceptance Criteria
1. A new command, `/whisper @player [message]`, is implemented. The bot deletes the user's command and then sends the message as a direct message to the tagged player.
2. The system is updated to allow the AI DM to send a private message to a single player when the narrative requires it (e.g., for a secret Insight check).
3. The `transcript.log` is updated to correctly log whispers, noting who sent them and who received them, but keeping the content visible in the log for the DM's reference.

---
## Epic 3: The TTRPG Creative Suite

**Expanded Goal:** The goal of this epic is to build a powerful, AI-assisted toolkit that streamlines the creative process for Dungeon Masters. By the end of this epic, a user will be able to create high-quality, balanced homebrew content using a **guided, best-practice-driven interface**, and a human DM will be able to use the bot's full suite of multimedia and organizational tools as a powerful assistant for their own games. This epic is designed to attract and retain our new core user: the Human DM as a Power User.

---
### Story 3.1: Implement Guided Homebrew Creator Framework
**As a** Dungeon Master, **I want** a simple, guided command that walks me through creating custom content using a best-practice framework, **so that** I can easily and confidently expand the world for my players.
#### Acceptance Criteria
1. A new, hierarchical command, `/homebrew create <asset_type>`, is created, supporting `npc`, `item`, and `monster`.
2. When a user runs the command, the bot initiates an interactive, step-by-step creation flow that provides tips and follows a proven process (e.g., for a monster, it will ask for a core concept, then stats, then actions, then lore).
3. The system provides a clear template for the user to fill in for each step.
4. Upon completion, the new homebrew asset is correctly saved to the appropriate YAML file in the campaign's "Knowledge Base".

---
### Story 3.2: Implement AI-Powered Balance Checker
**As a** Dungeon Master, **I want** to receive automated feedback on the balance of my custom monsters, **so that** I can be confident they will provide a fair and interesting challenge for my players.
#### Acceptance Criteria
1. After a user completes the creation of a new `monster` asset, the system automatically sends the monster's stats to a specialized AI agent for analysis.
2. The AI agent compares the monster's stats (HP, AC, damage output, etc.) against the D&D 5.1 SRD guidelines for its Challenge Rating.
3. The bot provides the user with clear, actionable feedback (e.g., "This monster's HP is a bit low for a CR 5 creature. Consider increasing it.").
4. The user has the option to accept the AI's suggestions or save the monster as-is.

---
### Story 3.3: Implement "Human DM Assistant" Mode
**As a** human Dungeon Master, **I want** to be able to use the bot's powerful tools without the AI taking over the narrative, **so that** I can enhance my own games.
#### Acceptance Criteria
1. A new "Human DM Assistant Mode" toggle is successfully added to the `/settings campaign` view.
2. When this mode is enabled, the AI DM's core narrative generation is disabled.
3. All other features, especially the multimedia and quality-of-life commands, remain fully functional for the human DM to use (`/imagine`, `/turn-order`, the AI Soundtrack Director, the AI Notetaker).
4. The bot provides a clear confirmation message when this mode is enabled or disabled.

---
## Epic 4: Advanced Content & DM Assistance Toolkit

**Expanded Goal:** The goal of this epic is to build a comprehensive toolkit that empowers Dungeon Masters with a suite of powerful content management and creation tools. This goes beyond simple file uploads, offering guided best practices, integration with popular community platforms, and AI-powered random generation to assist DMs in every stage of their creative process.

---
### Story 4.1: Implement Content Creation Guide
**As a** new Dungeon Master, **I want** to be able to get best-practice tips and templates for creating homebrew content, **so that** I can learn how to build high-quality assets for my game.
#### Acceptance Criteria
1. A new command, `/ingest guide`, is implemented.
2. When a user runs the command, the bot responds with an interactive view allowing the user to select a content type (e.g., NPC, Item, Monster).
3. Upon selection, the bot provides a helpful guide with best-practice tips and a clear template for that asset type.

---
### Story 4.2: Ingest from Popular Homebrew URLs
**As a** Dungeon Master who uses community tools, **I want** to be able to ingest content directly from a URL from popular platforms, **so that** I can easily bring my existing homebrew into the platform.
#### Acceptance Criteria
1. A new command, `/ingest from-url [url]`, is created.
2. The initial version supports, at a minimum, D&D Beyond (for monsters/spells) and Tetra-Cube (for statblocks).
3. The system successfully fetches the content from the URL, parses it, and structures it into a usable game asset.
4. The newly ingested asset is added to the campaign's "Knowledge Base" and is ready for use.

---
### Story 4.3: AI-Powered Random Generation
**As a** Dungeon Master in need of quick inspiration, **I want** to be able to randomly generate an asset based on a topic, **so that** I can get a starting point that I can then refine.
#### Acceptance Criteria
1. A new command, `/ingest random [topic]`, is implemented. The `[topic]` refers to a source document or list for generation (e.g., `srd_monsters`, `common_magic_items`).
2. The bot uses the specified topic to randomly generate a complete asset (e.g., an NPC with a name, trait, and flaw).
3. The bot presents the generated asset to the user with options to **[Approve]**, **[Edit]**, **[Regenerate]**, or **[Cancel]**.
4. If the user chooses to "Edit," the bot initiates a guided flow to modify the asset.
5. Once approved, the new asset is saved to the campaign's "Knowledge Base".

---
### Story 4.4: Support for Custom Random Lists
**As a** Dungeon Master with my own ideas, **I want** to be able to provide my own custom lists for the random generator, **so that** the generated content fits the unique flavor of my world.
#### Acceptance Criteria
1. A new command, `/ingest add-list [name]`, is created that allows a user to upload a simple text file containing a list of items (e.g., a list of fantasy names).
2. The user can then use this custom list with the random generator, e.g., `/ingest random [my_custom_list_name]`.
3. The system successfully uses the user-provided list to generate random content.

---
### Story 4.5: Ingest from File Upload & AI Parsing
**As a** Dungeon Master, **I want** the AI to intelligently read my uploaded content and structure it into usable game assets, **so that** I don't have to manually re-type everything.
#### Acceptance Criteria
1. The `/ingest upload` command is implemented, allowing a user to attach a supported file type.
2. The uploaded file is processed, and its text is passed to a specialized AI agent for parsing and structuring.
3. The structured data for each new asset is saved to a temporary location pending user review.
4. The user is notified that their file is ready for review.

---
### Story 4.6: Implement Unified Content Review Workflow
**As a** Dungeon Master, **I want** a single, consistent way to review and approve all new content, **so that** I have final control over what gets added to my campaign.
#### Acceptance Criteria
1. A new command, `/ingest review [source]`, is implemented. The `[source]` can be a file from Story 4.5 or a generation session from Story 4.3.
2. The bot displays all the structured assets from the source in a clear, easy-to-read format.
3. The user has the ability to approve or reject each individual asset.
4. Approved assets are formally saved to the campaign's "Knowledge Base".

---
## Epic 5: The Auto-Generated Campaign Wiki

**Expanded Goal:** The goal of this epic is to dramatically improve the user experience of world management by creating a locally hosted web interface that acts as a campaign wiki. By the end of this epic, a user will be able to launch a simple, local web server that reads their campaign's data files and presents the information in a beautiful, browsable, and editable format for both the DM and the players.

---
### Story 5.1: Implement Lightweight Web Server Framework
**As a** developer, **I want** to set up a lightweight, local-only web server within the backend service, **so that** we have a foundation to build the campaign wiki upon.
#### Acceptance Criteria
1. A lightweight Python web framework (like Flask or a sub-application within our existing FastAPI) is integrated into the project.
2. A new command, `/wiki start`, is created that successfully launches the local web server.
3. When launched, the bot provides the user with a local URL (e.g., `http://localhost:8080`) to access the wiki.
4. The server can successfully serve a basic "Hello World" HTML page at the provided URL.

---
### Story 5.2: Develop Wiki Read & Display Functionality
**As a** Dungeon Master, **I want** to be able to view all my campaign's lore in a clean, organized, and easy-to-read web interface, **so that** I can quickly reference information during my games.
#### Acceptance Criteria
1. The web interface is styled to match our "classic fantasy sourcebook" theme.
2. The wiki homepage displays a list of all campaigns.
3. Clicking on a campaign leads to a dashboard with links to different lore categories (NPCs, Locations, Items, etc.).
4. The system successfully reads the data from the campaign's YAML files and displays the content for each category in a clear, well-formatted way.
5. The wiki is searchable, allowing a user to quickly find any entry (e.g., a specific NPC).

---
### Story 5.3: Implement In-Wiki Editing for DMs
**As a** Dungeon Master, **I want** to be able to edit my campaign's lore directly from the web interface, **so that** I don't have to manually edit YAML files.
#### Acceptance Criteria
1. Each entry in the wiki (e.g., an NPC's page) has a clear "Edit" button that is **only visible to the DM**.
2. Clicking "Edit" turns the content fields into an editable form.
3. When the DM saves their changes, the backend service successfully and safely updates the corresponding YAML file with the new information.
4. The system includes validation to prevent malformed data from being saved.
5. The web interface immediately reflects the saved changes.

---
### Story 5.4: Implement Player View with Permissions
**As a** player, **I want** to be able to access a read-only version of the campaign wiki, **so that** I can reference the lore and information my character would know.
#### Acceptance Criteria
1. A new command, `/wiki share`, is created that provides a URL to the wiki that can be accessed by other players in the campaign.
2. The wiki has a permissions system. Fields or entries in the YAML files marked as "secret" or "DM-only" **are not displayed** to users who are not the DM.
3. The "Edit" buttons are not visible to players.
4. Players can browse and search all public lore for the campaign.

## Epic 6: Advanced Party & Campaign Management

**Expanded Goal:** The goal of this epic is to build the foundational systems for true multi-player and multi-campaign support. By the end of this epic, a server owner will be able to host multiple, distinct campaigns, and players will be able to seamlessly form parties and join the correct game session. This epic is critical for supporting our core group-play use case.

---
### Story 6.1: Implement Party Creation & Invite System
**As a** campaign host, **I want** to be able to create a new party for my campaign and receive a simple, memorable name to share with my players, **so that** they can easily join my game.
#### Acceptance Criteria
1. A new command, `/party create`, is implemented.
2. When a host uses this command within an active campaign, the system generates a new, unique party record.
3. The bot responds with a simple, memorable invite name (e.g., "blue-dragon-7") that is associated with the new party.
4. The bot provides clear instructions to the host on how players can use the invite name with the `/party join` command.

---
### Story 6.2: Implement Party Join Workflow
**As a** player, **I want** to be able to join a specific party using an invite name, **so that** I can participate in the campaign with my friends.
#### Acceptance Criteria
1. A new command, `/party join [invite-name]`, is implemented.
2. When a player uses the command with a valid invite name, they are added to the corresponding party roster.
3. The system then initiates the character link flow (asking for their character sheet URL or confirming they are using a physical sheet).
4. The host of the party receives a notification that a new player has joined.
5. The system handles errors gracefully, such as for an invalid invite name or a full party.

---
### Story 6.3: Implement Multi-Campaign Management
**As a** server owner, **I want** to be able to run multiple, separate campaigns on my server, **so that** I can host games for different groups of friends.
#### Acceptance Criteria
1. The system is updated to support multiple, distinct campaign records on a single server.
2. The `/campaign new "[name]"` command functions as expected, creating a new, isolated campaign.
3. A new command, `/campaign switch "[name]"`, is implemented that allows a server admin to set the "active" campaign for the server.
4. The `/campaign delete "[name]"` command is fully implemented, allowing an admin to permanently delete a campaign and all its associated data after a confirmation step.
5. All gameplay commands (`/turn-order`, `/roll`, etc.) correctly operate on the currently "active" campaign.

## Epic 7: Advanced Gameplay & World Systems

**Expanded Goal:** The goal of this epic is to build the core systems that will make the game world feel like a real, persistent place. By the end of this epic, a campaign will have AI-generated summaries to help players stay engaged, a navigable map with dynamic fog of war, and an AI-powered notetaker to track the adventure. This epic is designed to create a deeply immersive and user-friendly gameplay experience.

---
### Story 7.1: Implement AI-Powered Summaries
**As a** player, **I want** to be able to get a quick summary of what has happened, **so that** I can easily catch up after a break or a missed session.
#### Acceptance Criteria
1. A new command, `/catch-me-up`, is implemented.
2. When a player uses this command, the system sends the `transcript.log` for the relevant session(s) to the AI provider.
3. The AI successfully generates a concise, narrative summary of the key events.
4. The bot sends the summary to the player as a direct message.
5. An "End of Session" summary is automatically generated and posted by the bot when a host uses the `/campaign end` command.

---
### Story 7.2: Implement Map & Location System
**As a** player, **I want** to be able to see a map of the area my party is exploring, **so that** I can better understand the world and make strategic decisions.
#### Acceptance Criteria
1. A new command, `/map`, is created that displays an image of the current area map in a Discord embed.
2. The system is updated to allow a campaign host to upload a map image for a specific location.
3. The system can track the party's current coordinates on the active map.
4. The map display includes tokens representing the current position of the party members.

---
### Story 7.3: Implement Dynamic Fog of War
**As a** player, **I want** the map to be gradually revealed as we explore, **so that** I can experience a sense of discovery and surprise.
#### Acceptance Criteria
1. The map system is enhanced to support a "Fog of War" overlay that hides unexplored areas.
2. As the AI DM describes the party moving to a new area, the backend service updates the map to reveal that area, removing the fog.
3. The image displayed by the `/map` command correctly shows the currently revealed portions of the map.
4. The host has a setting in `/settings campaign` to enable or disable Dynamic Fog of War.

---
### Story 7.4: Implement AI Notetaker & Journal
**As a** player, **I want** an automated system to keep track of important information, **so that** I can focus on roleplaying without worrying about forgetting key details.
#### Acceptance Criteria
1. A new command, `/journal [topic]`, is created.
2. A specialized AI agent ("the Notetaker") is implemented that processes the campaign's `transcript.log` in the background.
3. The Notetaker agent successfully identifies and saves key entities (like NPC names, location names, and important quests) to the `party_state.yaml` file.
4. When a player uses `/journal [topic]`, the bot searches the saved notes and displays the relevant entries.

## Epic 8: The Living World Engine

**Expanded Goal:** The goal of this epic is to implement the most ambitious and technically complex features of the platform, transforming it from a reactive DM into a proactive, living world. By the end of this epic, the game world will feel truly alive, with NPCs and factions pursuing their own goals, and the bot will be able to intelligently manage the party, even when players are absent.

---
### Story 8.1: Implement AI Companions & Party Members
**As a** player in a small group, **I want** the ability for the AI to create and control a dedicated NPC party member, **so that** our party feels more complete and we have an in-character source of guidance.
#### Acceptance Criteria
1. A new command, `/party add-companion`, is created that allows the host to add an AI-controlled member to the party.
2. The AI Companion has its own character sheet, participates in combat, and can be interacted with by the players.
3. The AI Companion's roleplaying is handled by a specialized AI agent or sub-process to give it a distinct personality.
4. The host can use a `/party remove-companion` command to remove the AI member from the party.

---
### Story 8.2: Implement AI Auto-Play for Missing Players
**As a** player, **I want** the option to have the AI take control of my character when I miss a session, **so that** the game can continue without me and my character doesn't fall behind.
#### Acceptance Criteria
1. A new `[Enable Auto-Play]` option is added to the `/party view` for each player. This can only be toggled by the player themselves.
2. When a session starts and a player with Auto-Play enabled is not present, the AI DM takes control of their character.
3. The AI's actions for the character are guided by their known personality traits, skills, and backstory from their character sheet.
4. When the human player returns for the next session, they can use the `/catch-me-up` command to get a summary of what their character did while they were away.

---
### Story 8.3: Implement Dynamic World Engine
**As a** player, **I want** the world to feel alive and dynamic, where events happen in the background, **so that** my choices feel more meaningful and the world feels more immersive.
#### Acceptance Criteria
1. A new "Dynamic World" setting is added to the `/settings campaign` view.
2. When enabled, the backend service runs a periodic check on key NPCs and factions that have been given specific "background goals" (e.g., "The Evil Cult wants to summon a demon").
3. The system updates the state of the world based on the progress of these goals (e.g., "The curse has spread to the next village").
4. The AI DM's narrative generation is updated to reflect these background changes, making the players aware of the evolving world state.

---
### Story 8.4: Implement Persistent World Architecture
**As a** player, **I want** my party's actions to have a lasting impact on the game world, **so that** we feel like we are part of a larger, shared story.
#### Acceptance Criteria
1. The backend data architecture is updated to support a persistent world that can be shared by multiple, independent parties.
2. A party's significant actions (e.g., defeating a major villain, liberating a town) are saved as permanent "world events" in the campaign's lore files.
3. When a *different* party enters an area affected by a world event, the AI DM's narration correctly reflects the changes made by the previous party.
4. The system is designed to handle potential conflicts or overlapping actions between different parties in the same world.