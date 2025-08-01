# Unified Project Structure

This document outlines the official folder and file structure for the AI DM monorepo. It is designed to be clean, scalable, and to clearly separate the concerns of the Discord bot, the backend service, and all project data.

## Monorepo Structure

```plaintext
/ai-dm-project/
├── .gitignore
├── README.md
├── docker-compose.yml       # For easy local self-hosting
├── pyproject.toml           # Root project configuration for Python tooling
├── packages/                # Main directory for our Python code
│   ├── bot/                 # The discord.py bot application (Gateway)
│   │   ├── __init__.py
│   │   ├── main.py          # Bot entrypoint, loads cogs
│   │   └── cogs/            # Directory for command modules (Cogs)
│   │       ├── __init__.py
│   │       ├── admin_cog.py # Handles /server-setup, etc.
│   │       └── campaign_cog.py # Handles /campaign new, etc.
│   │
│   ├── backend/             # The FastAPI backend service (AI Brain)
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application entrypoint
│   │   ├── api/             # API endpoint definitions (routers)
│   │   ├── components/      # Core logic components (AIOrchestrator, etc.)
│   │   └── core/            # Core logic, e.g., security
│   │   └── agents/          # For defining our AI agent personas & LangGraph graphs
│   │       ├── __init__.py
│   │       └── dm_graph.py
│   │   └── tools/          # For our deterministic rule functions (e.g., dice rolls)
│   │       ├── __init__.py
│   │       └── dice_tools.py
│   │
│   └── shared/              # Shared code used by both bot and backend
│       ├── __init__.py
│       └── models.py        # Our Pydantic data models
│
├── data/                    # For persistent, non-code data
│   ├── campaigns/
│   │   └── [campaign_name]/       # A single, persistent world setting
│   │       ├── lore/            # The core, static knowledge for this world
│   │       │   ├── npcs.yaml
│   │       │   └── locations.yaml
│   │       │
│   │       └── parties/           # Folder for all parties playing in this world
│   │           └── [party_name]/  # The dynamic save data for a specific party
│   │               ├── chronicle.yaml
│   │               ├── party_state.yaml
│   │               └── player_characters.yaml
│   │
│   └── srd_database.sqlite      # The SRD "Rules Library"
│
└── docs/                    # All planning documents
    ├── prd.md
    ├── ui-ux-specification.md
    └── fullstack-architecture.md