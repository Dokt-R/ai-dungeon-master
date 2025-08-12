Of course. Here is the complete and finalized `fullstack-architecture-phase2.md` document, which incorporates all of our decisions, refinements, and the full, ambitious scope of your project's grand vision.

You can copy the content from the code block below and save it as `fullstack-architecture-phase2.md` in your `docs/phase2/` folder.

````markdown
# AI D&D DM Fullstack Architecture Document - Phase 2

## Introduction

This document outlines the architectural evolution of the AI D&D DM platform for Phase 2. It builds directly upon the foundational architecture established in the MVP, extending the system to support a vast new suite of features including a full TTRPG Creative Suite, immersive multimedia, and advanced, dynamic gameplay systems. This document will serve as the single source of truth for all new technical implementation.

### Architectural Approach
The core architectural principle for this phase is **extensibility**. We will build upon the existing Modular Monolith, adding new components and services in a way that is clean, scalable, and maintains the separation of concerns we established in the initial design. The foundational tech stack (Python, FastAPI, LangGraph, Docker) remains the same. The architecture will be a **LangGraph-only** system, leveraging its state machine capabilities for both the complex game loop and simpler creative tasks to ensure a unified and consistent development model.

### Change Log

| Date       | Version | Description                                    | Author             |
| :---       | :---    | :---                                           | :---               |
| 2025-08-08 | 1.0     | Initial draft for Phase 2 Architecture         | Winston, Architect |

---
## High Level Architecture

### Technical Summary
Building upon the successful MVP, the Phase 2 architecture extends the platform into a comprehensive TTRPG ecosystem. The system will continue to be a cloud-hosted, service-oriented application with a Python backend and a Discord bot interface. The backend will be architected around **LangGraph** to manage the complex, stateful game loop and AI interactions. A new, locally hosted **web service** will be introduced to power the "Auto-Generated Campaign Wiki." This expanded architecture is designed to support a rich multimedia experience, a powerful creative suite, and a dynamic, persistent game world.

### Architectural Overview
* **Architectural Style:** We will continue to build upon the **Modular Monolith**. This maintains a single, deployable backend application, but we will add the new, lightweight web service for the wiki as a distinct component within our `docker-compose` environment.
* **Repository Structure:** The **Monorepo** will be maintained to house the backend, the bot, the new web-wiki frontend code, and all shared libraries.
* **Platform:** The application remains a **Cloud-Hosted Service**, designed for portability and easy self-hosting via Docker.

### High Level Project Diagram
This revised diagram illustrates the new components and interactions for Phase 2, including the Campaign Wiki.

```mermaid
graph TD
    subgraph User
        A[Player / DM] -- Interacts via --> B[Discord Client];
        A -- Interacts via --> H[Web Browser];
    end

    subgraph Internet
        B -- via Discord API --> C[discord.py Bot Gateway];
        C -- API Calls --> D[AI DM Backend Service];
        D -- API Calls --> E[AI Provider APIs <br/> (LLM, TTS, Images)];
        D -- Read/Write --> F[Data Stores <br/> (SQLite, YAML, JSON)];
        D -- Serves data to --> G[Campaign Wiki Web Service];
        G -- Serves HTML/JS to --> H;
    end

    subgraph "Our Application (Cloud-Hosted)"
        C;
        D;
        F;
        G;
    end
````

### Architectural and Design Patterns

  * **Modular Monolith:** Provides a balance of simplicity with a clear path for future scaling.
  * **State Machine (LangGraph):** The core application logic will be built as a state machine or graph, giving us explicit control over the game loop.
  * **Polyglot Persistence:** We will use the best tool for each data job (SQLite for rules, YAML for lore, LangGraph state for live encounters).
  * **Containerization (Docker):** The application will be fully containerized to ensure portability and simplify self-hosting.
  * **Provider Pattern for AI:** All external AI services (LLM, TTS, Image Gen) will be treated as "swappable" components.
  * **Client-Server for Wiki:** The Campaign Wiki will operate on a classic client-server model, with a lightweight Python backend serving a simple frontend to the user's browser.

-----

## Tech Stack

This table outlines the specific technologies chosen for the project's Phase 2 development.

| Category | Technology | Version | Purpose | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Language** | Python | 3.11 | Primary language for all backend logic. | Prioritizes stability and broad library compatibility over the newest features. |
| **Backend Framework**| FastAPI | Latest | Provides the structure for our backend service. | High performance, excellent for building APIs, and has automatic documentation. |
| **AI Framework** | LangGraph | Latest | Manages the stateful, cyclical AI logic. | Provides explicit, stateful control over the game loop, essential for a rule-heavy game. |
| **Bot Interface** | discord.py | Latest | Connects our application to the Discord API. | The leading and most robust library for creating Discord bots in Python. |
| **Web Wiki Framework** | **Flask** | **Latest** | **Serves the local Campaign Wiki.** | **A minimal, lightweight framework perfect for a simple, local-only web interface that can be easily integrated.** |
| **Data Persistence** | Polyglot | N/A | Flexible data storage. | Uses the best tool for each job: SQLite for rules, and YAML/JSON for campaign files. |
| **Premium TTS API** | **ElevenLabs** | **v1** | **Provides high-quality voice narration.** | **The market leader in expressive, emotionally resonant AI voices, perfect for a premium experience.** |
| **Image Gen API** | **Midjourney / Stable Diffusion**| **N/A**| **Generates character & scene images.** | **To be determined based on a final analysis of API ease-of-use, cost, and stylistic consistency.** |
| **Containerization** | Docker / Docker Compose | Latest | Packages the application for portability. | Simplifies local self-hosting and ensures consistent deployment environments. |
| **Testing Framework**| Pytest | Latest | For all unit and integration tests. | The standard for Python testing; powerful, flexible, and has a rich plugin ecosystem. |

-----

## Data Models

This section defines the core Pydantic and SQLModel classes for Phase 2, building directly upon the existing structures in `packages/shared/models.py`.

### **Updated & New `SQLModel` Classes for Phase 2**

*(These represent the new tables and the extensions to existing tables required for our new features. This code would be added to your `models.py` file.)*

```python
from sqlmodel import Field, SQLModel
from typing import List, Optional

# --- Updates to existing tables via new models ---

class Campaign(SQLModel, table=True):
    campaign_id: str = Field(primary_key=True)
    server_id: str = Field(foreign_key="serverconfig.server_id")
    name: str
    
    # New settings fields for Phase 2 features
    is_persistent_world: bool = False
    premium_tts_enabled: bool = False
    image_gen_enabled: bool = False
    human_dm_mode_enabled: bool = False
    ai_conversation_director_enabled: bool = False
    dynamic_world_engine_enabled: bool = False

class PlayerCharacter(SQLModel, table=True):
    character_id: str = Field(primary_key=True)
    player_discord_id: str
    party_id: Optional[str] = Field(default=None, foreign_key="parties.party_id")
    name: str
    character_sheet_url: Optional[str] = None
    preferred_output_mode: str = "text"
    ai_autoplay_enabled: bool = False


# --- New table for Phase 2 ---

class Party(SQLModel, table=True):
    """Represents a group of players within a single campaign."""
    party_id: str = Field(primary_key=True)
    campaign_id: str = Field(foreign_key="campaigns.campaign_id")
    name: str
    invite_name: str = Field(unique=True)
    is_recruiting: bool = False
```

-----

## API Specification

This specification defines the expanded REST API for the AI DM Backend Service for Phase 2, building directly upon the existing endpoints in `packages/backend/main.py`.

```yaml
openapi: 3.0.1
info:
  title: AI DM Backend API - Phase 2
  version: 2.0.0
  description: Expanded API for managing advanced features like the Creative Suite, party system, and multimedia.

servers:
  - url: /api/v1 # Continuing with the v1 endpoint for consistency

paths:
  # --- Existing Endpoints (from your main.py) ---
  /health:
    get:
      summary: Health Check
  /config/{server_id}:
    put:
      summary: Create or Update Server Configuration
    get:
      summary: Get Server Configuration

  # --- New Endpoints for Phase 2 ---
  /campaigns/{campaign_id}/settings:
    put:
      summary: Update Campaign-Specific Settings
  /parties:
    post:
      summary: Create a new party
  /parties/{party_id}/join:
    post:
      summary: Join an existing party
  /homebrew/create:
    post:
      summary: Create a new homebrew asset
  /ingest/from-url:
    post:
      summary: Ingest content from a URL
  /wiki/data/{campaign_id}:
    get:
      summary: Get All Data for Campaign Wiki
    put:
      summary: Update Lore from Wiki
```

-----

## Components

The backend service is broken down into the following logical components:

### **Existing Components (Enhanced for Phase 2)**

  * **`AIOrchestrator`:** Remains the central "brain" of the application. It will be significantly upgraded to manage the **LangGraph execution flow**.
  * **`CampaignMemoryService`:** Its responsibilities will be greatly expanded to manage the full **four-tiered persistence strategy**.
  * **`RulesEngine`:** Continues to provide deterministic results for D\&D 5.1 SRD rules.
  * **`NotificationService`:** Will be upgraded to handle multimedia, integrating with the **ElevenLabs API** and the **Image Generation API**.

### **New Components for Phase 2**

  * **`PartyManager`:** A new component dedicated to handling all the logic for the advanced party system.
  * **`HomebrewManager`:** A new component that will contain all the logic for the "Creative Suite".
  * **`IngestionService`:** A dedicated, secure service for handling all content ingestion tasks.
  * **`WikiWebService`:** A new, lightweight **Flask** application that will run as a separate component to serve the Campaign Wiki.

-----

## External APIs

The application depends on the following external services:

1.  **AI Language Model Provider (e.g., OpenAI):** Powers the core narrative and reasoning.
2.  **Premium TTS Provider (ElevenLabs):** Provides high-quality, emotionally resonant Text-to-Speech.
3.  **Image Generation Provider (To Be Determined):** Provides the service to generate images for character avatars and scenes.
4.  **Discord API:** The foundational platform for the bot interface.

-----

## Core Workflows

The components will interact in clear sequences to handle user actions, as illustrated in the AI-Assisted Homebrew Creation Workflow. The primary risks in these workflows are latency from external APIs and the potential for low-quality AI responses, which are mitigated by robust error handling and a strong separation between deterministic rules and creative narration.

-----

## Database Schema

The `SQLModel` classes defined in the "Data Models" section will be used to automatically generate and manage our SQLite database tables. This includes the new `Parties` table and the expanded `Campaigns` and `PlayerCharacters` tables.

-----

## Source Tree

The project will use a monorepo structure that adds a new top-level package for the web-based wiki frontend and expands the backend to include our new components and AI-specific folders.

```plaintext
/ai-dm-project/
├── packages/
│   ├── bot/
│   ├── backend/
│   │   ├── components/
│   │   │   ├── party_manager.py
│   │   │   ├── homebrew_manager.py
│   │   │   └── ingestion_service.py
│   │   ├── agents/
│   │   ├── tools/
│   │   └── services/
│   │       └── wiki_web_service.py
│   ├── shared/
│   └── wiki_frontend/
│       ├── static/
│       └── templates/
├── data/
└── docs/
    └── phase2/
```

-----

## Infrastructure and Deployment

The project is designed for easy self-hosting using **Docker Compose**. To make the self-hosting process accessible to non-technical users, we will implement a two-stage strategy:

  * **Phase 2 (One-Click Start Script):** We will create simple script files (`start.bat` and `start.sh`) that a user can double-click to build and run the entire application, avoiding the command line.
  * **Post-Phase 2 (One-Click Installer):** A future epic will be dedicated to creating a traditional installer application (`.exe` or `.dmg`) that fully automates the setup process.

-----

## Key Strategies

  * **Error Handling:** We will define new custom exception types for our new external dependencies (e.g., `ElevenLabsAPIError`).
  * **Coding Standards:** We will continue to enforce **Black** for formatting and **Ruff** for linting.
  * **Test Strategy:** Our strategy will expand to cover all new features, including simple **End-to-End (E2E) tests** for critical flows like the "Homebrew Creator."
  * **Security:** The new **Content Ingestion Service** must be designed to process user-uploaded files in a sandboxed, isolated environment.

-----

## Future Architectural Evolution

This section documents advanced concepts for the project's long-term vision.

### **Potential Use Cases for an MCP-Enabled Platform**

The **Model Context Protocol (MCP)**, enabled by libraries like `fastapi-mcp`, offers a clear path to transforming our backend service into an open platform, allowing other AI agents to interact with our "Creative Suite."

### **Advanced LangGraph Tool Examples**

Beyond simple dice rollers, we will build sophisticated and reliable game mechanics as tools, such as an **"Encounter Balancer" Tool**, an **"Intelligent Loot Generator" Tool**, and a **"Narrative Pacing" Tool**.

```
```