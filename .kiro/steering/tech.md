# Technology Stack & Development Guidelines

## Core Technologies

### Backend
- **Python 3.13**: Primary language for all backend logic (modern, robust ecosystem for AI and web services)
- **FastAPI 0.111.0**: Web framework for backend service (high performance, excellent for APIs, automatic documentation)
- **SQLModel/SQLAlchemy**: Database ORM with Pydantic integration
- **SQLite**: Database for structured data and SRD "Rules Library"
- **Pydantic v2**: Data validation and serialization (use `model_dump()` not deprecated `dict()`)

### AI Framework
- **LangGraph**: Manages stateful, cyclical AI logic as state machine/graph (provides explicit control over game loop)

### Bot Interface
- **discord.py 2.3.2**: Discord bot library (leading and most robust for Discord bots)
- **Cogs Pattern**: Organize bot commands into logical modules (AdminCog, CampaignCog, CharacterCog, UtilityCog)
- **Discord Tree Commands**: Use `@tree.command(name="{command}", description="{command_description}")` for server visibility

### HTTP & API
- **httpx**: Async HTTP client for API communication
- **Thin API Client Pattern**: Centralized HTTP handling in `packages/shared/api_client.py`

### Development Tools
- **pytest 8.2.2**: Testing framework with async support (standard for Python testing, rich plugin ecosystem)
- **ruff**: Linting and code formatting (enforced with PEP 8 compliance)
- **black**: Code formatting (enforced alongside ruff)
- **structlog**: Structured logging with traceable error handling

## Common Commands

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run backend service
uvicorn packages.backend.main:app --reload

# Run Discord bot
python packages/bot/main.py

# Run with Docker Compose (recommended)
docker compose up --build
```

### Testing
```bash
# Run all tests
pytest --maxfail=1 --disable-warnings -v

# Run specific test file
pytest tests/unit/test_api_client.py -v

# Run with coverage
pytest --cov=packages --cov-report=html
```

### Code Quality
```bash
# Format code
ruff format .

# Lint code
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

## Environment Configuration

### Required Environment Variables
- `DISCORD_BOT_TOKEN`: Discord bot token
- `FAST_API`: Backend API base URL (default: http://localhost:8000)

### Configuration Files
- `.env`: Environment variables (not committed)
- `pyproject.toml`: Project configuration and dependencies
- `pytest.ini`: Test configuration
- `docker-compose.yml`: Container orchestration

## Key Libraries & Versions

- `discord.py==2.3.2`
- `fastapi==0.111.0`
- `httpx==0.28.1`
- `pydantic==2.11.7`
- `sqlmodel==0.0.24`
- `pytest==8.2.2`
- `structlog>=24.1.0`
- `langgraph` (latest)

## Coding Standards & Key Strategies

### Code Quality
- **Black** for formatting and **Ruff** for linting (enforced)
- All code must adhere to **PEP 8** style guide
- **Type Hints**: All function signatures and variable declarations must include full, correct type hints
- **Naming Conventions**: 
  - snake_case for variables, functions, and modules
  - PascalCase for classes
  - ALL_CAPS for constants

### Architecture Patterns
- **Provider Pattern for AI**: AI model and TTS service as swappable components
- **Polyglot Persistence**: Best tool for each data job (SQLite, YAML, JSON, files)
- **Abstraction Layers**: All data access must go through MemoryService (no direct database calls)
- **Command Flow**: /command → Bot Gateway → API Call → Backend Service → SQLite Table

### Security & Data Handling
- **Secrets Management**: All secrets via environment variables
- **Input Validation**: All inputs validated by Pydantic models
- **Database Initialization**: Schema auto-created/updated on startup (no manual migrations needed)