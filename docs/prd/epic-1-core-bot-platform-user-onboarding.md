# Epic 1: Core Bot Platform & User Onboarding

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
