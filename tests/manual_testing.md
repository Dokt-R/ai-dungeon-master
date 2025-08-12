# Manual Testing Plan for Error Handling and Logging

This document provides a comprehensive list of manual test cases to rigorously trigger and validate error conditions within the application, with a specific focus on the decoupled logging configuration and general error handling.

## Test Case Categories

### 1. Decoupled Logging Configuration Tests

#### TC-LOG-001: Verify Backend Service Logging Configuration
- **Description**: Validate that the backend service correctly initializes its own logging configuration.
- **Steps**:
  1. Start the backend service (`packages/backend/main.py`)
  2. Trigger any API endpoint that generates a log message
- **Expected Behavior**:
  - Log messages should appear in the console with the configured format
  - Log messages should show the correct module names (e.g., `packages.backend.api.campaign_api`)
  - Log level should be set according to the configuration
- **Actual Results**:

#### TC-LOG-002: Verify Discord Bot Logging Configuration
- **Description**: Validate that the Discord bot correctly initializes its own logging configuration.
- **Steps**:
  1. Start the Discord bot service (`packages/bot/main.py`)
  2. Trigger any bot command that generates a log message
- **Expected Behavior**:
  - Log messages should appear in the console with the configured format
  - Log messages should show the correct module names (e.g., `packages.bot.cogs.campaign_cog`)
  - Log level should be set according to the configuration
- **Actual Results**:

#### TC-LOG-003: Verify Shared Module Logger Usage
- **Description**: Confirm that the shared error handler module uses its own logger instance.
- **Steps**:
  1. Trigger an error condition in a component that uses the shared error handler
  2. Check the log output
- **Expected Behavior**:
  - Log messages from the error handler should show `packages.shared.error_handler` as the module name
  - Log messages should be properly formatted according to the application's logging configuration
- **Actual Results**:

#### TC-LOG-004: Verify No Conflicting Logging Configurations
- **Description**: Ensure that removing the centralized logging configuration doesn't cause conflicts.
- **Steps**:
  1. Start both the backend service and Discord bot
  2. Trigger various operations in both services that generate logs
- **Expected Behavior**:
  - Both services should produce logs without interfering with each other
  - Log formats should be consistent within each service
  - No warnings or errors related to logging configuration should appear
- **Actual Results**:

### 2. API Error Handling Tests

#### TC-API-001: Validation Error Handling
- **Description**: Test handling of validation errors in API endpoints.
- **Steps**:
  1. Make an API request with invalid data that should trigger a validation error
  2. Observe the HTTP response and log output
- **Expected Behavior**:
  - HTTP 400 Bad Request response should be returned
  - Response body should contain a structured error message
  - A warning or error should be logged with details about the validation failure
- **Actual Results**:

#### TC-API-002: Not Found Error Handling
- **Description**: Test handling of not found errors in API endpoints.
- **Steps**:
  1. Make an API request to a non-existent endpoint or for a non-existent resource
  2. Observe the HTTP response and log output
- **Expected Behavior**:
  - HTTP 404 Not Found response should be returned
  - Response body should contain a structured error message
  - An error should be logged with details about the missing resource
- **Actual Results**:

#### TC-API-003: Generic Exception Handling
- **Description**: Test handling of unexpected exceptions in API endpoints.
- **Steps**:
  1. Force an unexpected exception in an API endpoint (e.g., by mocking a database connection failure)
  2. Observe the HTTP response and log output
- **Expected Behavior**:
  - HTTP 500 Internal Server Error response should be returned
  - Response body should contain a generic, sanitized error message
  - A critical error should be logged with the full exception details and stack trace
- **Actual Results**:

#### TC-API-004: Pydantic Validation Error Handling
- **Description**: Test handling of Pydantic validation errors.
- **Steps**:
  1. Make an API request with data that fails Pydantic validation
  2. Observe the HTTP response and log output
- **Expected Behavior**:
  - HTTP 422 Unprocessable Entity response should be returned
  - Response body should contain a structured error message with validation details
  - An error should be logged with information about the validation failure
- **Actual Results**:

#### TC-API-005: Rate Limiting Simulation (429 Error)
- **Description**: Test handling of rate limiting scenarios.
- **Steps**:
  1. Configure a mock or simulate a scenario where an external API returns a 429 status
  2. Make a request that would trigger this condition
  3. Observe the HTTP response and log output
- **Expected Behavior**:
  - Appropriate HTTP response should be returned to the client (may be 429 or translated to another error)
  - A warning should be logged with details about the rate limiting
  - The system should gracefully handle the condition without crashing
- **Actual Results**:

### 3. Discord Bot Error Handling Tests

#### TC-BOT-001: Validation Error in Command
- **Description**: Test handling of validation errors in Discord commands.
- **Steps**:
  1. Execute a Discord command with invalid parameters that should trigger a ValidationError
  2. Observe the bot's response and log output
- **Expected Behavior**:
  - Bot should send an ephemeral message to the user with a clear error description
  - A warning should be logged with details about the validation failure
- **Actual Results**:

#### TC-BOT-002: Not Found Error in Command
- **Description**: Test handling of not found errors in Discord commands.
- **Steps**:
  1. Execute a Discord command for a resource that doesn't exist
  2. Observe the bot's response and log output
- **Expected Behavior**:
  - Bot should send an ephemeral message to the user with a clear error description
  - An error should be logged with details about the missing resource
- **Actual Results**:

#### TC-BOT-003: Generic Exception in Command
- **Description**: Test handling of unexpected exceptions in Discord commands.
- **Steps**:
  1. Force an unexpected exception in a Discord command (e.g., by mocking a database connection failure)
  2. Observe the bot's response and log output
- **Expected Behavior**:
  - Bot should send an ephemeral message to the user with a generic, sanitized error message
  - A critical error should be logged with the full exception details and stack trace
- **Actual Results**:

#### TC-BOT-004: AI API Error Handling
- **Description**: Test handling of AI API call failures.
- **Steps**:
  1. Configure a mock or simulate a failure in an AI API call (e.g., timeout, service unavailable)
  2. Execute a command that would trigger this AI call
  3. Observe the bot's response and log output
- **Expected Behavior**:
  - Bot should send an ephemeral message to the user with a user-friendly error message
  - An error should be logged with technical details about the AI API failure
- **Actual Results**:

#### TC-BOT-005: Safe Send Message Failure
- **Description**: Test the fallback mechanism in `_safe_send_message`.
- **Steps**:
  1. Force a failure in `interaction.response.send_message` (e.g., by mocking it to raise an exception)
  2. Execute a command that triggers an error
  3. Observe the bot's response and log output
- **Expected Behavior**:
  - Bot should attempt to use `interaction.followup.send` as a fallback
  - A warning should be logged when the primary send method fails
  - If both methods fail, a critical error should be logged
- **Actual Results**:

### 4. Resource Exhaustion and System Failure Tests

#### TC-SYS-001: Disk Space Exhaustion During Logging
- **Description**: Test system behavior when disk space is full and logs cannot be written.
- **Steps**:
  1. Fill up the disk space where logs would be written (in a test environment)
  2. Trigger operations that generate log messages
  3. Observe system behavior
- **Expected Behavior**:
  - The application should not crash
  - A critical error should be logged about the logging failure (to stderr or alternative location)
  - The application should continue to function, albeit with reduced logging
- **Actual Results**:

#### TC-SYS-002: Memory Exhaustion
- **Description**: Test system behavior under memory pressure.
- **Steps**:
  1. Use a tool to consume most available memory
  2. Trigger operations in the application
  3. Observe system behavior
- **Expected Behavior**:
  - The application should handle memory errors gracefully
  - OutOfMemory errors should be caught and logged appropriately
  - The application should attempt to free resources if possible
- **Actual Results**:

#### TC-SYS-003: Database Connection Failure
- **Description**: Test handling of database connection failures.
- **Steps**:
  1. Stop the database service or block database connections
  2. Trigger operations that require database access
  3. Observe system behavior
- **Expected Behavior**:
  - Appropriate error responses should be returned to users (500 for API, error message for Discord)
  - Critical errors should be logged with details about the database connection failure
  - The application should not crash and should be able to recover when the database is available again
- **Actual Results**:

### 5. Security-Related Error Tests

#### TC-SEC-001: Sensitive Information Leakage Prevention
- **Description**: Verify that sensitive information is not leaked in error messages.
- **Steps**:
  1. Trigger an unexpected exception that might contain sensitive data in its message
  2. Observe the error messages sent to users (API response, Discord message)
  3. Check the detailed logs
- **Expected Behavior**:
  - User-facing error messages should be generic and not contain sensitive information
  - Detailed logs should contain the full error information for developers
- **Actual Results**:

#### TC-SEC-002: Malformed Input Handling
- **Description**: Test handling of deliberately malformed or malicious input.
- **Steps**:
  1. Send deliberately malformed requests to API endpoints
  2. Send unusual parameters to Discord commands
  3. Observe system behavior
- **Expected Behavior**:
  - All malformed input should be handled gracefully without crashing the application
  - Appropriate validation errors should be returned
  - Suspicious activity should be logged for security monitoring
- **Actual Results**:

### 6. Logging Misconfiguration Tests

#### TC-LOG-005: Invalid Log Level Configuration
- **Description**: Test behavior when an invalid log level is configured.
- **Steps**:
  1. Configure an invalid log level in the logging configuration
  2. Start the application
  3. Observe system behavior
- **Expected Behavior**:
  - The application should either fail to start with a clear error message or default to a standard log level
  - Error about invalid configuration should be logged
- **Actual Results**:

#### TC-LOG-006: Unwritable Log File Directory
- **Description**: Test behavior when the log file directory is not writable.
- **Steps**:
  1. Configure logging to write to a file in a directory without write permissions
  2. Start the application
  3. Observe system behavior
- **Expected Behavior**:
  - The application should handle the logging failure gracefully
  - Error about inability to write logs should be logged to stderr
  - The application should continue to function
- **Actual Results**:

### 7. Integration and End-to-End Tests

#### TC-INT-001: Cross-Component Error Propagation
- **Description**: Test how errors propagate between different components of the system.
- **Steps**:
  1. Trigger an error in a low-level component (e.g., database access)
  2. Observe how the error is handled and reported through the layers (component -> API/bot -> user)
- **Expected Behavior**:
  - Errors should be properly caught and wrapped with appropriate context at each layer
  - Final user-facing message should be clear and user-appropriate
  - Technical details should be preserved in the logs for debugging
- **Actual Results**:

#### TC-INT-002: Concurrent Error Conditions
- **Description**: Test system behavior when multiple errors occur simultaneously.
- **Steps**:
  1. Create a scenario where multiple components experience errors at the same time
  2. Observe system behavior
- **Expected Behavior**:
  - The system should handle each error independently
  - Logging should clearly distinguish between different errors
  - The application should remain stable and not crash
- **Actual Results**: