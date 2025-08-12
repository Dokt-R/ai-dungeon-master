# Project Test Strategy

This document outlines the comprehensive test strategy for the AI DM project, as defined in the main architecture document. All new code must adhere to these standards.

## 1. Testing Philosophy
* [cite_start]**Approach:** The project will follow a test-after-development approach for the MVP, focusing on ensuring the reliability of our components and their interactions. [cite: 809]
* [cite_start]**Coverage Goals:** A high level of test coverage will be required for all new code before it can be merged. [cite: 809]
* [cite_start]**Test Pyramid:** The focus will be on a strong base of unit tests, supported by a layer of integration tests. [cite: 809]

## 2. Test Directory Structure

All tests are located in the root `tests/` directory, which is organized as follows:

*   `tests/unit/`: For unit tests, which test components in isolation with mocked dependencies. The subdirectory structure mirrors the `packages/` directory (e.g., `tests/unit/backend/` for backend unit tests).
*   `tests/integration/`: For integration tests, which verify the interactions between internal components (e.g., managers and the database).
*   `tests/e2e/`: For end-to-end tests, which simulate user workflows from the Discord bot to the backend API.
*   `tests/utils/`: Contains test utilities, such as factories for creating test data.

## 3. Test Types

### Unit Tests
* **Framework:** We will use **Pytest** for all unit testing.
* **Scope:** Each individual component and its functions will be tested in isolation. All external dependencies, such as the Discord API, AI provider APIs, and other components, must be mocked.
* **Location:** `tests/unit/`

### Integration Tests
* **Scope:** We will write tests to verify that our internal components (e.g., `AIOrchestrator` and `CampaignMemory Service`) interact with each other as expected according to the defined API contracts.
* **Test Infrastructure:** Integration tests may use in-memory versions of dependencies or a dedicated test instance of the SQLite database, configured in `tests/conftest.py`.
* **Location:** `tests/integration/`

### End-to-End (E2E) Tests
* **Scope:** E2E tests will simulate full user workflows, from a user issuing a command in Discord to the backend processing the request and returning a response.
* **Framework:** These tests will use tools that can interact with a live or near-live environment, including a test Discord bot and a running backend instance.
* **Location:** `tests/e2e/`

## 4. Test Utilities
* **Factories:** To ensure consistent and reusable test data, we will use factories. These will be defined in `tests/utils/factories.py` and `tests/utils/factories_db.py`.

## 5. Continuous Testing
* **CI Integration:** All tests (unit, integration, and E2E) will be run automatically via a CI pipeline (e.g., GitHub Actions) on every pull request to the main branch.