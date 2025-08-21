# Error Handling Strategy

## Overview

Our error handling strategy is designed to be robust, consistent, and secure. It follows these principles:
- **Fail Fast**: Errors are raised as soon as they are detected
- **Custom Exceptions**: We use custom exception types to provide context
- **Centralized Handling**: Errors are handled in dedicated handlers rather than scattered throughout the code
- **User-Safe Messages**: Users never see technical error details
- **Developer-Friendly Logging**: Full technical details are logged for debugging

## Exception Types

### CustomException
Base class for all custom exceptions. Should not be raised directly.

### ValidationError
Raised when input validation fails. Results in HTTP 400 or user-friendly Discord message.

### NotFoundError
Raised when a requested resource is not found. Results in HTTP 404 or user-friendly Discord message.

### AIAPIError
Raised when an external AI API call fails. Results in appropriate HTTP status or user-friendly Discord message.

### PermissionDeniedError
Raised when a user lacks the required permissions to perform an action. Results in HTTP 403 or user-friendly Discord message.

## Handling Strategy

### FastAPI
Uses application-level exception handlers registered with `@app.exception_handler`.

### Discord
Uses the `@discord_error_handler` decorator on command methods. This decorator:
- Automatically catches custom exceptions and sends user-friendly messages
- Logs detailed error information for developers
- Handles fallback scenarios when message sending fails
- Supports correlation IDs for request tracing

## Error Codes

The system uses standardized error codes defined in `packages/shared/errors.py`. This file contains:

- **ErrorCode enum**: All available error codes
- **ERRORS dictionary**: System-facing error definitions with HTTP status codes
- **PLAYER_ERRORS dictionary**: User-friendly error messages
- **ErrorDef/PlayerErrorDef dataclasses**: Structured error information

Example error codes include:
- `NO_MEMBERS_FOUND`: No non-bot members found in server
- `MEMBER_FETCH_ERROR`: Failed to fetch server members
- `PERMISSION_DENIED_ERROR`: User lacks required permissions

## Centralized Implementation

All Discord commands across all cogs now use the `@discord_error_handler` decorator:
- `AdminCog`: Server management commands
- `CampaignCog`: Campaign management commands
- `CharacterCog`: Character management commands
- `UtilityCog`: General utility commands

This ensures consistent error handling across the entire Discord bot.

## Logging Integration

The error handling system integrates with the structured logging configuration in `packages/shared/logging_config.py`. Errors are logged with:

- **Correlation IDs**: For request tracing across services
- **Structured Context**: Error type, message, error code, and additional details
- **Stack Traces**: Full exception information for debugging
- **User-Safe Messages**: Separate user-facing messages that hide technical details

The logging system supports both development console output and production JSON format for observability platforms.

## Contributing New Exceptions

When adding new error scenarios, follow these steps to maintain consistency:

### Step 1: Define Error Codes
Add new error codes to the `ErrorCode` enum in `packages/shared/errors.py`:

```python
class ErrorCode(str, Enum):
    # ... existing codes ...

    # Add your new error codes here
    NEW_ERROR_SCENARIO = "NEW_ERROR_SCENARIO"
    ANOTHER_ERROR_CASE = "ANOTHER_ERROR_CASE"
```

### Step 2: Add System-Facing Error Definitions
Add entries to the `ERRORS` dictionary with appropriate HTTP status codes:

```python
ERRORS: Dict[str, ErrorDef] = {
    # ... existing definitions ...

    # Add system-facing error definitions
    ErrorCode.NEW_ERROR_SCENARIO: ErrorDef(
        ErrorCode.NEW_ERROR_SCENARIO,
        "System description of what went wrong",
        HTTPStatus.BAD_REQUEST,  # Choose appropriate HTTP status
    ),
    ErrorCode.ANOTHER_ERROR_CASE: ErrorDef(
        ErrorCode.ANOTHER_ERROR_CASE,
        "Another system error description",
        HTTPStatus.NOT_FOUND,
    ),
}
```

### Step 3: Add Player-Facing Error Messages
Add user-friendly messages to the `PLAYER_ERRORS` dictionary:

```python
PLAYER_ERRORS: Dict[str, PlayerErrorDef] = {
    # ... existing definitions ...

    # Add user-friendly error messages
    ErrorCode.NEW_ERROR_SCENARIO: PlayerErrorDef(
        ErrorCode.NEW_ERROR_SCENARIO,
        "A user-friendly message explaining what went wrong and how to fix it."
    ),
    ErrorCode.ANOTHER_ERROR_CASE: PlayerErrorDef(
        ErrorCode.ANOTHER_ERROR_CASE,
        "Another helpful message for users."
    ),
}
```

### Step 4: Use the Error Codes in Your Code
Now you can use the new error codes in your exception handling:

```python
from packages.shared.exceptions import ValidationError
from packages.shared.errors import ErrorCode

# Example usage in your code
if some_condition:
    raise ValidationError(
        ErrorCode.NEW_ERROR_SCENARIO,
        details={"context": "additional error context"}
    )
```

### Step 5: Test Your Changes
Add tests to ensure your new exceptions work correctly:
- Test that the exception is raised with the correct error code
- Test that the error handler processes it correctly
- Test that users receive the appropriate error message

This approach ensures all errors have both system-facing and user-facing messages, proper HTTP status codes, and consistent handling across the application.

## Best Practices

1. Always raise the most specific exception type possible
2. Provide clear, user-friendly messages in exceptions
3. Include error codes for programmatic handling
4. Add details when helpful for debugging
5. Never expose technical details to users

## Examples

### Raising ValidationError

```python
from packages.shared.exceptions import ValidationError
from packages.shared.errors import ErrorCode

# Example 1: Invalid character name
raise ValidationError(
    error_code=ErrorCode.CHARACTER_NOT_FOUND,
    name="invalid_name"
)

# Example 2: Missing required field
raise ValidationError(
    error_code=ErrorCode.VALIDATION_ERROR,
    field="level"
)
```

### Raising NotFoundError

```python
from packages.shared.exceptions import NotFoundError
from packages.shared.errors import ErrorCode

# Example 1: Character not found
raise NotFoundError(
    error_code=ErrorCode.CHARACTER_NOT_FOUND,
    name="missing_character"
)

# Example 2: Campaign not found
raise NotFoundError(
    error_code=ErrorCode.CAMPAIGN_NOT_FOUND,
    campaign="nonexistent_campaign"
)
```

### Raising AIAPIError

```python
from packages.shared.exceptions import AIAPIError
from packages.shared.errors import ErrorCode

# Example 1: OpenAI API failure
try:
    response = openai.ChatCompletion.create(...)
except Exception as e:
    raise AIAPIError(
        error_code=ErrorCode.AI_API_ERROR,
        service="OpenAI",
        error=str(e)
    ) from e

# Example 2: Generic API failure
try:
    result = some_external_api_call()
except Exception as e:
    raise AIAPIError(
        error_code=ErrorCode.AI_API_ERROR,
        service="external_api",
        error=str(e)
    ) from e