# Contributing to AI Dungeon Master Backend

Thank you for your interest in contributing! This guide covers development, testing, and documentation practices for the PlayerManager, CharacterManager, and related backend features.

## Overview

The backend manages players, characters, and campaign participation using:
- `PlayerManager` and `CharacterManager` for business logic
- FastAPI endpoints in `player_api.py` and `character_api.py`
- SQLite database initialized via `server_settings_manager.py`
- Comprehensive validation and error handling via `error_handler.py`

## Development Setup

1. **Clone the repository** and install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

2. **Database Initialization**  
   The SQLite database (`server_settings.db`) is auto-initialized by `server_settings_manager.py`. No manual migration is needed for development.

3. **Running the Backend**
   ```sh
   uvicorn packages.backend.main:app --reload
   ```

## Testing

- **Unit Tests:**  
  Located in `packages/backend/tests/test_player_manager.py`, `test_character_manager.py`, etc.
- **Integration Tests:**  
  Located in `test_backend_managers.py`, `test_character_api.py`, `test_player_api.py`.

Run all tests with:
```sh
pytest packages/backend/tests/
```
To verify DB persistence and endpoint logic:
```sh
pytest packages/backend/tests/test_backend_managers.py
```

## Coding Standards

- Use Google-style docstrings for all public classes and methods.
- Validate all API inputs using Pydantic models with strict field constraints.
- Route all errors through the shared error handler for consistent responses.

## Documentation

- Update docstrings and endpoint documentation when making changes.
- If you change data models, business logic, or API endpoints, update:
  - `docs/architecture/components.md`
  - `docs/architecture/data-models.md`
  - `docs/architecture/rest-api-spec.md`

## Contribution Workflow

1. Fork and branch from `main`.
2. Make your changes with clear, atomic commits.
3. Add or update tests as needed.
4. Ensure all tests pass and documentation is up to date.
5. Open a pull request with a clear description of your changes.

---

For questions, see the architecture docs or contact the maintainers.