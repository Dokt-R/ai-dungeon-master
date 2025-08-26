# Contributing to AI Dungeon Master

Thank you for your interest in contributing! This guide covers development, testing, and documentation practices for the entire AI Dungeon Master monorepo, including bot, backend, and shared components.

## Project Overview

This is a modular monolith with three main packages:
- **Bot Package** (`packages/bot/`): Discord bot gateway handling user interactions and commands
- **Backend Package** (`packages/backend/`): FastAPI service managing AI brain, database operations, and business logic
- **Shared Package** (`packages/shared/`): Common Pydantic models, utilities, and database schemas

Key components include:
- Discord bot with slash commands for campaign management
- FastAPI backend with player/character managers and AI integration
- SQLite databases for settings and game data
- Comprehensive validation, error handling, and observability features

## Development Setup

### Prerequisites
- Python 3.8+
- Docker and Docker Compose (for containerized development)
- Discord bot token (for bot development)

### Environment Setup

1. **Clone the repository** and install dependencies:
   ```sh
   git clone https://github.com/your-org/ai-dungeon-master.git
   cd ai-dungeon-master
   pip install -r requirements.txt
   ```

2. **Bot Configuration**
   - Create `.env` file in `packages/bot/` with your Discord bot token:
     ```
     DISCORD_BOT_TOKEN=your_bot_token_here
     ```

3. **Database Initialization**
   - SQLite databases are automatically created when services start
   - No manual setup or migration needed for development

### Running the Services

#### Option 1: Docker Compose (Recommended)
```sh
docker compose up --build
```
- Backend API: http://localhost:8000
- Bot connects to Discord automatically

#### Option 2: Manual Setup
```sh
# Terminal 1: Backend
uvicorn packages.backend.main:app --reload

# Terminal 2: Bot
python packages.bot.main.py
```

## Testing

### Test Structure
- **Backend Tests** (`packages/backend/tests/`): Unit and integration tests for API endpoints, managers, and components
- **Bot Tests** (`packages/bot/tests/`): Discord interaction and command tests
- **Shared Tests** (`packages/shared/tests/`): Model validation and utility tests

### Running Tests

Run all tests:
```sh
pytest --maxfail=1 --disable-warnings -v
```

Run specific test suites:
```sh
# Backend tests only
pytest packages/backend/tests/

# Bot tests only
pytest packages/bot/tests/

# Shared tests only
pytest packages/shared/tests/

# Integration tests
pytest packages/backend/tests/test_backend_managers.py
```

### Test Coverage
- All new features require corresponding unit tests
- Integration tests for database operations and API endpoints
- Use pytest fixtures for test data setup
- Mock external dependencies (Discord API, AI services)

## Coding Standards

- Use Google-style docstrings for all public classes and methods.
- Validate all API inputs using Pydantic models with strict field constraints.
- Route all errors through the shared error handler for consistent responses.
- When adding new exceptions, follow the guide in `docs/architecture/error-handling.md` under "Contributing New Exceptions" to ensure proper error code definitions and user-facing messages.

## Documentation

### Code Documentation
- Use Google-style docstrings for all public classes and methods
- Include type hints for function parameters and return values
- Document complex business logic with clear explanations

### Architecture Documentation
When making changes, update relevant docs:
- **Components**: `docs/architecture/components.md`
- **Data Models**: `docs/architecture/data-models.md`
- **API Specs**: `docs/architecture/rest-api-spec.md`
- **Database Schema**: `docs/architecture/database-schema.md`
- **Error Handling**: `docs/architecture/error-handling.md`
- **Security**: `docs/architecture/security.md`

### Story Documentation
- Update story files in `docs/stories/` when implementing features
- Include implementation details, decisions, and testing results
- Reference relevant architecture docs

### README and Contributing
- Keep README.md up to date with setup instructions
- Update this CONTRIBUTING.md for any process changes

## Contribution Workflow

### Getting Started
1. **Fork and Clone**: Fork the repository and clone to your local machine
2. **Create Branch**: Branch from `main` with descriptive name (e.g., `feature/add-campaign-commands`)
3. **Set up Environment**: Follow the development setup instructions above

### Making Changes
1. **Atomic Commits**: Make small, focused commits with clear messages
2. **Add Tests**: Write tests for new functionality and update existing ones
3. **Update Documentation**: Keep docs in sync with code changes
4. **Code Standards**: Follow the coding standards outlined below

### Pull Request Process
1. **Test Thoroughly**: Ensure all tests pass locally
2. **Update Branch**: Rebase on latest `main` if needed
3. **PR Description**: Write clear description including:
   - What changes were made
   - Why they were needed
   - How to test the changes
   - Any breaking changes or migration notes
4. **Code Review**: Address review feedback and make necessary changes
5. **Merge**: PR will be merged by maintainers after approval

## Coding Standards

### General
- **Type Hints**: Use type hints for all function parameters and return values
- **Error Handling**: Use custom exceptions and route through shared error handler
- **Logging**: Use structured logging with appropriate levels
- **Security**: Never commit secrets or sensitive data

### Observability Best Practices
- **AI Operation Tracing**: Use `@observability_service.trace_ai_operation()` for AI-related functions
- **LLM Call Tracing**: Use `@observability_service.trace_llm_call_decorator()` for LLM API calls
- **Workflow Tracing**: Use `@observability_service.trace_ai_workflow_decorator()` for complex workflows
- **Context Managers**: Use `trace_operation()`, `trace_llm_call()`, `trace_ai_workflow()` for dynamic tracing
- **Custom Tags**: Add relevant AI-specific tags for better trace filtering and analysis
- **Health Monitoring**: Implement health checks for new services and update existing ones
- **Correlation IDs**: Ensure correlation ID propagation in all async operations and traces
- **Performance Monitoring**: Add performance metrics for operations that could impact user experience
- **Documentation**: See `docs/architecture/observability.md` for comprehensive observability guidelines and examples

### Package-Specific
- **Backend**: Validate all API inputs with Pydantic models
- **Bot**: Handle Discord rate limits and implement proper error responses
- **Shared**: Keep models lightweight and focused on data representation

### Code Style
- **Formatting**: Use black for Python code formatting
- **Imports**: Organize imports (standard library, third-party, local)
- **Naming**: Use descriptive names following Python conventions
- **Comments**: Comment complex logic, not obvious code

## Getting Help

- **Architecture Docs**: `docs/architecture/` for system design and patterns
- **Story Documentation**: `docs/stories/` for feature implementation details
- **Issues**: Open GitHub issues for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas

---

For questions, see the architecture docs or contact the maintainers.