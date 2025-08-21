# Project Structure & Organization

## Monorepo Layout

The project follows a monorepo structure with clear separation of concerns:

```
/ai-dungeon-master/
├── packages/                 # Main application code
│   ├── bot/                 # Discord bot (Gateway)
│   ├── backend/             # FastAPI backend service (AI Brain)
│   ├── shared/              # Shared models and utilities
│   └── __init__.py
├── tests/                   # Test suites
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   ├── e2e/               # End-to-end tests
│   └── utils/             # Test utilities and mocks
├── docs/                   # Documentation
├── examples/               # Usage examples
└── data/                   # Data storage (campaigns, saves)
```

## Package Organization

### packages/bot/
Discord bot interface using the Cogs pattern:
- `main.py`: Bot entry point and cog loading
- `cogs/`: Command modules
  - `admin_cog.py`: Server administration commands
  - `campaign_cog.py`: Campaign management commands
  - `character_cog.py`: Character management commands
  - `utility_cog.py`: General utility commands

### packages/backend/
FastAPI backend service:
- `main.py`: FastAPI application entry point
- `api/`: API endpoint definitions (routers)
- `components/`: Core logic components (AIOrchestrator, ServerSettingsManager, etc.)
- `core/`: Core logic (e.g., security)
- `agents/`: AI agent personas & LangGraph graphs
  - `dm_graph.py`: Main DM state machine
- `tools/`: Deterministic rule functions
  - `dice_tools.py`: Dice rolling utilities

### packages/shared/
Common code shared between bot and backend:
- `models.py`: Pydantic/SQLModel data models
- `api_client.py`: Thin API client for bot-backend communication
- `errors.py`: Custom exception classes
- `db.py`: Database utilities
- `transcript_logger.py`: Campaign logging utilities

## Data Organization

### Official Campaign Data Structure
```
data/
├── campaigns/
│   └── [campaign_name]/           # Single, persistent world setting
│       ├── lore/                  # Core, static knowledge for this world
│       │   ├── npcs.yaml
│       │   └── locations.yaml
│       └── parties/               # All parties playing in this world
│           └── [party_name]/      # Dynamic save data for specific party
│               ├── chronicle.yaml
│               ├── party_state.yaml
│               └── player_characters.yaml
└── srd_database.sqlite            # SRD "Rules Library"
```

## Testing Structure

### Test Organization (Test-After-Development for MVP)
- **Unit Tests** (`tests/unit/`): Test components in isolation with mocked dependencies
  - Subdirectory structure mirrors `packages/` directory
  - Framework: **Pytest** for all unit testing
- **Integration Tests** (`tests/integration/`): Verify interactions between internal components
  - May use in-memory dependencies or dedicated test SQLite instance
- **E2E Tests** (`tests/e2e/`): Simulate full user workflows from Discord to backend
  - Use tools that interact with live/near-live environment
- **Test Utilities** (`tests/utils/`): Test utilities, factories, and mocks
  - `factories.py` and `factories_db.py` for consistent test data
  - `mock_api_client.py` for testing without backend

### Test Naming Conventions
- Test files: `test_[component_name].py`
- Test classes: `Test[ComponentName]`
- Test methods: `test_[specific_behavior]`

### CI Integration
- All tests run automatically via CI pipeline (GitHub Actions) on every PR
- High test coverage required for all new code before merge

## Key Architectural Patterns

### Cogs Pattern (Bot)
Commands organized into logical modules that can be loaded/unloaded dynamically.

### Thin API Client Pattern
Centralized HTTP communication through `packages/shared/api_client.py` eliminates boilerplate and provides consistent error handling.

### Modular Monolith
Single deployable application with clear internal service boundaries, allowing future microservice extraction if needed.

### Polyglot Persistence Strategy
- **SQLite**: Structured relational data and SRD "Rules Library" (monster stats, spells)
- **YAML**: Human-readable campaign data (lore, chronicles, party state)
- **JSON**: Temporary session state
- **Log files**: Campaign transcripts

### LangGraph State Machine
- Core application built as state machine/graph using **LangGraph**
- Provides explicit, deterministic control over game loop
- Essential for rule-heavy, stateful D&D application

## Import Conventions

### Local Imports
```python
# Use absolute imports for packages
from packages.shared.models import Campaign
from packages.shared.api_client import ApiClient

# Known first-party modules (configured in pyproject.toml)
known-first-party = ["packages"]
```

### Dependency Management
- All dependencies in `requirements.txt`
- Project metadata in `pyproject.toml`
- Development dependencies included in requirements