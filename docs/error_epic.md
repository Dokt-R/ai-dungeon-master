# Epic: Error Handling Overhaul

**User Story:** As a developer, I want a robust, consistent, and secure error handling mechanism so that I can build reliable features faster, diagnose issues more effectively, and provide a better user experience.

**Business Value:**
*   **Increased Reliability:** Reduces unexpected crashes and improves application stability.
*   **Faster Development:** Provides clear patterns for handling errors, speeding up feature implementation.
*   **Improved Security:** Prevents sensitive information from being leaked in error messages.
*   **Better User Experience:** Delivers clear, user-friendly error messages instead of technical jargon.
*   **Enhanced Maintainability:** Centralized and well-documented error handling makes the codebase easier to manage and debug.

---

## Acceptance Criteria

- [ ] Logging configuration is removed from the shared `error_handler.py` module and handled by the application's entry point.
- [ ] The generic `handle_error` function is removed, and its logic is moved into context-specific handlers.
- [ ] FastAPI error handling uses application-level `@app.exception_handler` instead of a manual decorator.
- [ ] Custom exception classes (`ValidationError`, `NotFoundError`, etc.) are enhanced to include error codes and structured details.
- [ ] A specific `AIAPIError` is created to gracefully handle failures from external AI service calls.
- [ ] The `discord_error_handler` decorator is refactored to be simpler, safer, and less repetitive.
- [ ] All unhandled exceptions result in a generic, sanitized, user-facing message, while detailed technical information is logged securely.
- [ ] Pydantic validation errors (`pydantic.ValidationError`) are handled globally within the FastAPI exception handlers.
- [ ] Comprehensive type hints are added to the `error_handler` module and related components to improve code clarity and maintainability.
- [ ] Comprehensive tests are in place for all major error handling paths, including decorators and exception handlers.
- [ ] Documentation is updated to reflect the new error handling architecture, with clear examples.

---

## Actionable Plan & User Stories

### Phase 1: Foundational Refactoring

This phase focuses on correcting the core architectural issues to establish a solid foundation.

*   **Story 1.1: Decouple Logging Configuration**
    *   **User Story:** As a developer, I want the logging configuration to be managed by the application entry point, not a shared module, so that I can have predictable and environment-specific logging behavior without side effects.
    *   **Acceptance Criteria:**
        1.  The `logging.basicConfig()` call is completely removed from `packages/shared/error_handler.py`.
        2.  The `error_handler.py` module retrieves its logger using `logging.getLogger(__name__)`.
        3.  The FastAPI application (`packages/backend/main.py`) initializes the logging configuration for the backend service.
        4.  The Discord bot application (`packages/bot/main.py`) initializes the logging configuration for the bot service.
        5.  Existing logging functionality continues to work as expected in both the backend and the bot.
    *   **Technical Tasks:**
        *   [ ] **Refactor `error_handler.py`:** Remove `logging.basicConfig()`, add `logger = logging.getLogger(__name__)`, and update logging calls.
        *   [ ] **Update `packages/backend/main.py`:** Add a `logging.basicConfig()` call at application startup.
        *   [ ] **Update `packages/bot/main.py`:** Add a `logging.basicConfig()` call at application startup.
        *   [ ] **Validation:** Manually trigger errors in both the API and the bot to confirm logs are generated correctly.

*   **Story 1.2: Implement Idiomatic FastAPI Exception Handlers**
    *   **User Story:** As a developer, I want to use FastAPI's native application-level exception handlers instead of a manual decorator, so that error handling is applied consistently and automatically to all endpoints.
    *   **Acceptance Criteria:**
        1.  The `@fastapi_error_handler` decorator is completely removed from `packages/shared/error_handler.py`.
        2.  Application-level handlers for `ValidationError`, `NotFoundError`, `pydantic.ValidationError`, and the base `Exception` are registered in `packages/backend/main.py`.
        3.  The handler for `Exception` logs the full error with a stack trace and returns a generic, sanitized HTTP 500 response.
        4.  The handlers for custom exceptions return appropriate HTTP status codes (400, 404) and structured error messages.
        5.  All API endpoints now have error handling applied automatically without needing a decorator.
    *   **Technical Tasks:**
        *   [ ] **Refactor `error_handler.py`:** Delete the `fastapi_error_handler` function.
        *   [ ] **Update `packages/backend/main.py`:** Import custom exceptions and `pydantic.ValidationError`. Implement and register `@app.exception_handler` for each required exception type.
        *   [ ] **Code Cleanup:** Remove all usages of the `@fastapi_error_handler` decorator from API endpoint files.
        *   [ ] **Validation:** Test API endpoints by triggering validation errors, not found errors, and unexpected exceptions to verify the handlers work correctly.

*   **Story 1.3: Refactor Core Exception Logic**
    *   **User Story:** As a developer, I want to enhance our custom exceptions to carry structured data and eliminate the generic `handle_error` function, so that our error handling logic is more specific, powerful, and easier to maintain.
    *   **Acceptance Criteria:**
        1.  The `handle_error` function is completely removed from `packages/shared/error_handler.py`.
        2.  `CustomException`, `ValidationError`, and `NotFoundError` are updated to accept optional `error_code` and `details` arguments in their `__init__` methods.
        3.  A new `AIAPIError(CustomException)` is created to represent failures from external AI services.
        4.  The logic previously in `handle_error` is now fully contained within the FastAPI exception handlers and the Discord decorator.
    *   **Technical Tasks:**
        *   [ ] **Refactor `error_handler.py`:** Delete the `handle_error` function. Modify the `__init__` methods of `CustomException`, `ValidationError`, and `NotFoundError`. Add the new `AIAPIError` class.
        *   [ ] **Update Consumers:** Refactor the FastAPI handlers and Discord decorator to no longer call `handle_error` and instead use the exception's properties directly.
        *   [ ] **Validation:** Run tests and manually verify that errors are still handled correctly after removing the central function.

### Phase 2: Discord and Security Enhancements

This phase improves the Discord bot's error handling and implements critical security measures.

*   **Story 2.1: Simplify Discord Error Handler**
    *   **User Story:** As a developer, I want to refactor the `discord_error_handler` to be cleaner and safer, so that it's easier to debug and maintain, and it no longer hides critical logging failures.
    *   **Acceptance Criteria:**
        1.  The `discord_error_handler` now has a single `except` block for `(ValidationError, NotFoundError)`.
        2.  The nested `try...except Exception: pass` blocks around logging calls are removed.
        3.  The final `except Exception as e:` block correctly logs the full exception with a stack trace using `logger.error(..., exc_info=True)`.
        4.  The decorator continues to send appropriate user-facing messages for both custom and unexpected errors.
    *   **Technical Tasks:**
        *   [ ] **Refactor `discord_error_handler`:** Restructure the `try...except` blocks as per the acceptance criteria. Update the logging call to include `exc_info=True` for generic exceptions.
        *   [ ] **Validation:** Manually trigger a `ValidationError`, a `NotFoundError`, and an unexpected `Exception` in a Discord command to verify that the correct message is sent to the user and the correct information is logged.

*   **Story 2.2: Secure Error Message Handling**
    *   **User Story:** As a user, I want to receive helpful error messages without seeing sensitive backend information, so that my data and the system's integrity are protected.
    *   **Acceptance Criteria:**
        1.  No raw exception messages from unexpected errors are ever returned in an API response or sent in a Discord message.
        2.  The generic exception handlers for both FastAPI and Discord provide a fixed, sanitized message (e.g., "An unexpected error occurred.").
        3.  Error messages for custom, known exceptions (`ValidationError`, `NotFoundError`, `AIAPIError`) are confirmed to be safe for display.
    *   **Technical Tasks:**
        *   [ ] **Audit Handlers:** Review the implementation of the FastAPI and Discord exception handlers to confirm they meet the acceptance criteria.
        *   [ ] **Code Review:** Search the codebase for any other instances of `str(e)` being passed to a user-facing output and refactor them to use safe, custom messages.
        *   [ ] **Validation:** Trigger an unexpected error (e.g., `TypeError`) and confirm the user sees the generic, sanitized message.

*   **Story 2.3: Enhance `_safe_send_message`**
    *   **User Story:** As a developer, I want visibility into the behavior of `_safe_send_message`, so that I can debug situations where Discord error messages might be failing to send.
    *   **Acceptance Criteria:**
        1.  A warning is logged when `interaction.response.send_message` fails and the function falls back to `interaction.followup.send`.
        2.  An error is logged if both `send_message` and `followup.send` fail, just before the `RuntimeError` is raised.
    *   **Technical Tasks:**
        *   [ ] **Refactor `_safe_send_message`:** Add `logger.warning(...)` and `logger.error(...)` calls in the appropriate `except` blocks within the function.
        *   [ ] **Validation:** This is difficult to test automatically. A code review will be the primary means of validation.

### Phase 3: Advanced Features and Quality Assurance

This phase focuses on production-readiness, including advanced observability, testing, and documentation.

*   **Story 3.1: Implement Structured & Correlated Logging**
    *   **User Story:** As a developer, I want our logs to be structured (e.g., JSON) and contain a correlation ID, so that I can easily trace a request's entire lifecycle through different services and debug complex issues more effectively.
    *   **Acceptance Criteria:**
        1.  A structured logging library (like `structlog`) is integrated and configured in both `packages/backend/main.py` and `packages/bot/main.py`.
        2.  A FastAPI middleware is implemented that generates a unique correlation ID for each incoming request.
        3.  The correlation ID is automatically included in all log messages generated during the processing of that request.
    *   **Technical Tasks:**
        *   [ ] **Add Dependency:** Add `structlog` to the project's requirements.
        *   [ ] **Configure Logging:** Replace the `logging.basicConfig` with `structlog` configuration in both main entry points.
        *   [ ] **Create Middleware:** Write a FastAPI middleware to generate and store a correlation ID.
        *   [ ] **Validation:** Make an API request and inspect the console logs to confirm they are in JSON format and all logs for that request share the same correlation ID.

*   **Story 3.2: Improve Test Coverage**
    *   **User Story:** As a developer, I want comprehensive tests for our error handling logic, so that I can refactor it with confidence and ensure it remains reliable.
    *   **Acceptance Criteria:**
        1.  Unit tests exist for the FastAPI exception handlers, verifying correct status codes and response content for each handled exception.
        2.  Integration tests for the `discord_error_handler` simulate commands raising `ValidationError`, `NotFoundError`, and `Exception`, and assert the bot's response is correct.
        3.  Tests are added to cover the `AIAPIError` flow in both FastAPI and Discord contexts.
    *   **Technical Tasks:**
        *   [ ] **Create `tests/integration/backend/test_error_handler.py`:** Add tests using `TestClient` to make requests that trigger the exception handlers.
        *   [ ] **Create `tests/unit/bot/test_error_handling_cogs.py`:** Add tests that mock Discord interactions and check the responses from commands decorated with the error handler.
        *   [ ] **Validation:** Run the full test suite and ensure all new tests pass and code coverage for the error handling module has increased.

*   **Story 3.3: Update Documentation**
    *   **User Story:** As a new developer joining the team, I want clear documentation on the error handling system, so that I can understand how to use it correctly and consistently.
    *   **Acceptance Criteria:**
        1.  The docstrings in `error_handler.py` are updated to reflect the new exception classes and decorator behavior.
        2.  The main `architecture.md` or a new `error-handling.md` document outlines the overall strategy (e.g., "raise custom exceptions, let handlers deal with them").
        3.  The documentation includes examples of how and when to raise `ValidationError`, `NotFoundError`, and `AIAPIError`.
    *   **Technical Tasks:**
        *   [ ] **Update Docstrings:** Edit the docstrings in `packages/shared/error_handler.py`.
        *   [ ] **Update Architecture Docs:** Modify the relevant markdown files in the `/docs` folder to describe the new patterns.
        *   [ ] **Validation:** A peer review of the documentation for clarity and completeness.
*   **Story 3.4: Improve Code Quality**
    *   **User Story:** As a developer, I want comprehensive type hints in the error handling module, so that I can benefit from static analysis and better IDE support, reducing potential bugs.
    *   **Acceptance Criteria:**
        1.  All functions, methods, and arguments in `packages/shared/error_handler.py` have complete and correct type hints.
        2.  The code passes a static type check using a tool like `mypy` without errors.
    *   **Technical Tasks:**
        *   [ ] **Add Type Hints:** Edit the function and method signatures in `packages/shared/error_handler.py` to include type hints.
        *   [ ] **Validation:** Run a static type checker (e.g., `mypy packages/shared/error_handler.py`) and ensure it passes.

---

## Out of Scope for this Epic

*   Implementing a full circuit-breaker pattern for all external services (can be a future epic).
*   Adding localization (internationalization) support for error messages.
*   Implementing rate limiting on error-reporting endpoints (unless it becomes a security concern).