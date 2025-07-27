# AI D&D DM Product Requirements Document (PRD)

## Goals and Background Context

### Goals
* To launch a functional, open-source AI-DM engine as an MVP within **3 months** to build a community and gather feedback.
* To establish a platform that can support a future marketplace for original, premium campaign modules.
* To validate the "Bring Your Own Key" model as a sustainable way to manage operational costs for advanced users.
* To create an engaging and immersive D&D experience that supports long, multi-hour sessions and encourages players to return to their campaigns.
* To deliver an AI capable of "Guided Improvisation," balancing player freedom with narrative progression to create a truly authentic TTRPG experience.

### Background Context
The popularity of Dungeons & Dragons is at an all-time high, but the "Dungeon Master bottleneck"—the scarcity of skilled and available DMs—prevents many aspiring players from participating. Existing digital solutions like video games lack the true freedom of a TTRPG, while virtual tabletops still require a human DM.

This project aims to solve that problem by creating a sophisticated AI-DM. The initial MVP will be a Discord bot leveraging the D&D 5.1 SRD ruleset. It will address the primary user adoption risks of cost and complexity through a carefully designed strategy involving transparent cost estimates and simplified pricing metrics, ensuring a smooth onboarding experience for all user types.

### Change Log

| Date | Version | Description | Author |
| :--- | :--- | :--- | :--- |
| 2025-07-25 | 1.0 | Initial PRD draft based on Project Brief v1.1 | John, PM |

## Requirements

### Functional Requirements
1.  **FR1**: The system shall support both text-based and voice-based interaction for all core gameplay loops.
2.  **FR2**: The AI DM engine must adjudicate gameplay using the Dungeons & Dragons 5.1 SRD ruleset.
3.  **FR3**: The system must have a core memory system capable of recalling key NPCs, locations, and plot events within a single campaign.
4.  **FR4**: The platform must provide a user interface for server owners to securely input and manage a server-wide API key for the BYOK model.
5.  **FR5**: The MVP of the platform must be delivered as an installable Discord bot.
6.  **FR7**: The AI DM must support a foundational system for narrative control, allowing for different DMing styles (e.g., a "Dynamic World" that creates urgency vs. a "Sandbox" that waits for player initiative).
7.  **FR8**: The bot must provide a clear, comprehensive "Getting Started" guide and a `/cost` command that links to transparent cost-average data to help users understand the BYOK model before they commit.

### Non-Functional Requirements
1.  **NFR1**: Voice-based interactions should have a target roundtrip latency of under 4 seconds.
2.  **NFR2**: The system must securely handle all user-provided API keys.
3.  **NFR3**: The architecture must support future post-MVP capabilities for processing and storing user-uploaded copyrighted content on the user's local machine.
4.  **NFR4**: The configuration process for a "Hobbyist" user with their own API key should be completable in under 15 minutes.

## User Interface Design Goals

### Overall UX Vision
The core UX vision is to create an accessible and deeply immersive D&D experience by minimizing traditional UI complexity. The interface should feel like a natural conversation with a skilled Dungeon Master. The user should feel empowered and unconstrained, with the technology fading into the background to let the story shine.

### Key Interaction Paradigms
The MVP will support two primary, seamlessly integrated interaction paradigms within the Discord platform:
* **Voice-First Interaction:** Users should be able to speak their actions and decisions naturally. The AI will respond with a generated voice narrative.
* **Text-Based Interaction:** A complete and robust text interface for users who prefer to type, for playing in quiet environments, or for reviewing logs.

### Core Screens and Views
Within the context of a Discord bot, "screens" are the primary bot responses and interaction points:
* **Game/Session Management:** Commands and responses for starting a new campaign, loading a saved one, and ending a session.
* **Main Gameplay View:** The primary channel view where the AI's narrative descriptions, generated images, and player actions are displayed.
* **Character Sheet View:** A response to a `/sheet` command, showing a concise, easy-to-read summary of the player's character sheet.
* **Getting Started & Cost Info:** The output of the `/help` and `/cost` commands, providing clear onboarding instructions and transparent cost information.

### Accessibility: WCAG AA
To align with the project's core goal of making D&D more accessible, the interface will adhere to Web Content Accessibility Guidelines (WCAG) 2.1 Level AA standards where applicable, ensuring text contrast, clear language, and usability for players with disabilities.

### Branding
*(To Be Defined)* - The visual identity, personality, and branding for the AI DM have not yet been defined.

### Target Device and Platforms: Cross-Platform
The MVP will be a Discord bot, which is inherently cross-platform and available on Desktop (Windows, Mac, Linux) and Mobile (iOS, Android).

## Technical Assumptions

### Repository Structure: Monorepo
The project will be housed in a single monorepo.
* **Rationale**: For a solo developer, a monorepo simplifies dependency management, streamlines the build process, and makes it easier to share code and types between the AI backend and any future front-end applications (like the PC App).

### Service Architecture
The architecture will be **service-oriented**, as specified in the brief. For the MVP, this will likely be implemented as a **Modular Monolith**.
* **Rationale**: This approach allows for clear separation of concerns and logical service boundaries from day one, while avoiding the operational complexity of deploying multiple microservices for the MVP. It provides a clear path to scale out to true microservices post-MVP if needed.

### Testing Requirements
The project will require, at a minimum, **Unit and Integration tests**.
* **Rationale**: This ensures that individual components work as expected (Unit tests) and that they connect and interact correctly (Integration tests), providing a solid foundation of quality for the MVP.

### Additional Technical Assumptions and Requests
* **Primary Backend Language**: The backend will be developed in **Python**.
* **AI Framework**: We will explore agentic frameworks like **CrewAI** to manage the AI DM's logic.
* **Data Persistence**: The project will adopt a **flexible persistence strategy**, using the most appropriate storage solution for each type of data. The Architect will determine the best tool for each use case, which may include options like pre-built memory systems within AI frameworks, file-based storage (YAML, JSON), or a traditional database (SQL or NoSQL).
* **Security**: The system must be designed for the secure handling of user-provided API keys.

## Epic List

**Epic 1: Core Bot Platform & User Onboarding**
* **Goal:** Establish the installable Discord bot, implement the complete user onboarding flow with the "Bring Your Own Key" (BYOK) model, and create the foundational command interaction framework.

**Epic 2: The AI Dungeon Master Engine**
* **Goal:** Integrate the core AI, memory system, and D&D 5.1 SRD ruleset to bring the Dungeon Master to life, enabling full campaign gameplay through both text and voice interaction.

## Epic 1: Core Bot Platform & User Onboarding

**Expanded Goal:** This epic lays the complete foundation for the AI DM application. When this epic is complete, a **server owner** will be able to discover the project, install the bot on their Discord server, and successfully configure a **shared, server-wide API key** through a clear, guided process. This epic focuses on creating a stable, secure, and user-friendly "scaffold" that is ready to have the core AI engine integrated in the next epic.

---
### Story 1.1: Project Setup & Repository Initialization
**As a** solo developer, **I want** a properly initialized monorepo with a basic Python backend structure, **so that** I have a clean, organized foundation to start building the application.
#### Acceptance Criteria
1. A new Git repository is created.
2. The repository is structured as a monorepo.
3. A Python project for the backend service is initialized with standard dependency management.
4. A basic `README.md` file is created with the project's name and a brief description.

---
### Story 1.2: Basic Discord Bot Integration
**As a** server owner, **I want** to be able to invite the AI DM bot to my server and see it come online, **so that** I can confirm the basic integration is working.
#### Acceptance Criteria
1. The Discord bot application is created in the Discord developer portal.
2. The bot can be successfully invited to a Discord server using a standard OAuth2 URL.
3. The bot appears with an "online" status in the server's member list.
4. The bot responds to a simple `/ping` command with "pong" in the channel where it was invoked.

---
### Story 1.3: Secure Server API Key Storage
**As a** system, **I want** to securely store and retrieve a single, server-wide API key, **so that** all interactions on a given server are powered by the key provided by the server owner.
#### Acceptance Criteria
1. A storage mechanism is created for **server-to-API-key** mapping.
2. API keys are encrypted at rest in the storage mechanism.
3. The backend has a secure method to write a new key for a specific Discord **server ID**.
4. The backend has a secure method to retrieve a decrypted key associated with a specific Discord **server ID**.

---
### Story 1.4: Server Key Onboarding Command Flow
**As a** server owner, **I want** simple commands to set up a shared API key for my server, **so that** all members can participate in campaigns using my key.
#### Acceptance Criteria
1. The bot responds to a `/server-setup` command with a message explaining the shared API key model and how to submit a key.
2. The `/server-setup` and `/server-setkey` commands can only be successfully run by users with "Administrator" or "Manage Server" permissions.
3. The bot has a command (e.g., `/server-setkey [API_KEY]`) that accepts the owner's key.
4. When a key is submitted, the bot securely saves it for the entire server using the functionality from Story 1.3.
5. The bot provides a confirmation message upon successful key submission and an error for failures.
6. The owner's submitted key is not visible to other users in the channel.

---
### Story 1.5: User Guidance & Cost Transparency Commands
**As a** new user, **I want** simple commands to get help and understand potential costs, **so that** I can use the bot confidently.
#### Acceptance Criteria
1. The bot responds to a `/help` command with a list of available commands, clarifying that `/server-setup` and `/server-setkey` are for server owners/admins.
2. The bot responds to a `/cost` command with a message explaining the BYOK model and linking to the transparent cost-average data.

## Epic 2: The AI Dungeon Master Engine

**Expanded Goal:** This epic breathes life into the core platform, integrating the AI language models to transform the bot from a simple command-handler into a living Dungeon Master. By the end of this epic, the bot will be able to run a basic D&D 5.1 SRD-compliant game, remember key events, and interact with players through both text and voice, delivering the core product promise.

---
### Story 2.1: Basic AI Narrative Generation
**As a** player, **I want** to send a prompt to the bot and receive a narrative response from the AI, **so that** I can begin to interact with the game world.
#### Acceptance Criteria
1. The bot uses the server's configured API key to send a user's text prompt to the specified AI service.
2. The AI's text-based narrative response is successfully received from the service.
3. The narrative response is displayed clearly in the Discord channel.
4. The system gracefully handles and reports any errors during the AI API call.

---
### Story 2.2: D&D 5.1 SRD Ruleset Integration
**As a** player, **I want** the AI DM to be aware of the D&D 5.1 SRD rules, **so that** its rulings and descriptions are accurate and fair.
#### Acceptance Criteria
1. The AI's system prompt or context is primed with the D&D 5.1 SRD ruleset (e.g., via RAG or context priming).
2. The AI can correctly answer a direct question about a specific SRD rule (e.g., "How much damage does a longsword do?").
3. The AI's narrative descriptions correctly reference SRD mechanics (e.g., correctly describing a spell's effect or a monster's abilities).

> **Note for the Architect:** The user has suggested that instead of relying purely on text-based context priming, we should explore implementing specific, deterministic rules as callable **agent tools or server-side functions**. This hybrid approach could greatly improve accuracy and reduce long-term API costs. Please evaluate this during the architecture design phase.

---
### Story 2.3: Core Memory System Implementation
**As a** player, **I want** the AI DM to remember what has happened in our campaign, **so that** the story is coherent and my actions have lasting impact.
#### Acceptance Criteria
1. The system can create, read, update, and delete key events or facts for an active campaign (e.g., "Player met NPC Gundren," "The party cleared the goblin cave").
2. The AI's context for generating a new response includes relevant memories from the current campaign.
3. The AI can demonstrate recall by referencing a past event in its narrative when prompted or appropriate.
4. The campaign memory persists between bot restarts.

---
### Story 2.4: Voice Interaction Integration
**As a** player, **I want** to be able to speak to the AI DM and hear it speak back, **so that** I can have an immersive, hands-free gameplay experience.
#### Acceptance Criteria
1. The bot can join a Discord voice channel.
2. The bot can listen to and accurately transcribe a player's spoken words into a text prompt.
3. The AI's text response is successfully converted to speech audio.
4. The generated audio is played back to the user in the voice channel.
5. The average roundtrip latency (from end of user speech to beginning of bot speech) for a standard interaction meets the `NFR1` target of under 4 seconds.