# Thin API Client Implementation

This document describes the implementation of the thin API client for the AI Dungeon Master project, following the design principles outlined in the [API Client Implementation Guide](api_client.md).

## Overview

The thin API client provides a lightweight abstraction layer that:
- Centralizes HTTP communication with the backend API
- Handles error parsing and response validation
- Provides connection pooling for performance
- Enables consistent error handling across all cogs
- Supports async context management for resource cleanup

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Discord Cog   │───▶│   API Client    │───▶│  Backend API    │
│                 │    │                 │    │                 │
│ - CharacterCog  │    │ - add_character │    │ POST /characters│
│ - CampaignCog   │    │ - list_chars    │    │ GET /campaigns  │
│ - AdminCog      │    │ - create_camp   │    │ PUT /config     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Key Components

### 1. ApiClient Class (`packages/shared/api_client.py`)

The main client class that handles all HTTP communication:

```python
class ApiClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
    
    async def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Centralized error handling and response parsing"""
        # Maps HTTP status codes to custom exceptions
        
    # Character operations
    async def add_character(self, req: AddCharacterRequest) -> Dict[str, Any]:
    async def update_character(self, req: UpdateCharacterRequest) -> Dict[str, Any]:
    async def remove_character(self, req: RemoveCharacterRequest) -> Dict[str, Any]:
    async def list_characters(self, req: ListCharactersRequest) -> Dict[str, Any]:
    
    # Campaign operations
    async def create_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
    async def join_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
    async def end_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
    
    # Server configuration
    async def set_server_config(self, server_id: str, config: ServerConfigModel) -> Dict[str, Any]:
```

### 2. Centralized Error Handling

The `_handle_response` method maps backend errors to custom exceptions:

```python
async def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
    if response.status_code == 200:
        return response.json()
    
    error_info = response.json().get('error', {})
    error_code = error_info.get('code', 'UNKNOWN_ERROR')
    
    if response.status_code == 400:
        raise ValidationError(error_code, details=error_info.get('details', {}))
    elif response.status_code == 404:
        raise NotFoundError(error_code, details=error_info.get('details', {}))
    # ... other mappings
```

### 3. Connection Pooling

The client uses httpx with connection pooling for better performance:

```python
self.client = httpx.AsyncClient(
    base_url=self.base_url,
    timeout=self.timeout,
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
)
```

### 4. Async Context Manager Support

The client supports async context managers for automatic resource cleanup:

```python
async with ApiClient(base_url="http://localhost:8000") as client:
    result = await client.add_character(request)
    # Client is automatically closed when exiting the context
```

## Integration with Cogs

### Before (Direct HTTP calls)

```python
async def add_character(self, interaction, name: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{self.api_base_url}/characters/add",
                json={"player_id": str(interaction.user.id), "name": name}
            )
            response.raise_for_status()
            data = response.json()
            # Handle success
        except httpx.HTTPStatusError as e:
            # Manual error handling
            if e.response.status_code == 400:
                raise ValidationError("Invalid input")
            # ... more error handling
```

### After (Using Thin API Client)

```python
class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_client = ApiClient(base_url=os.getenv("FAST_API", "http://localhost:8000"))
    
    async def add_character(self, interaction, name: str):
        req = AddCharacterRequest(
            player_id=str(interaction.user.id),
            name=name,
            character_url=None
        )
        
        # All error handling is centralized in the API client
        data = await self.api_client.add_character(req)
        # Handle success - errors are automatically mapped to custom exceptions
    
    async def cog_unload(self):
        """Clean up resources when cog is unloaded"""
        await self.api_client.close()
```

## Benefits Achieved

### 1. Reduced Boilerplate
- Eliminated repetitive HTTP client setup in each cog method
- Removed duplicate error handling code
- Simplified request/response handling

### 2. Centralized Error Handling
- All API errors are consistently mapped to custom exceptions
- Error messages are standardized across the application
- Both internal and user-facing error messages are supported

### 3. Improved Testability
- Mock API client (`tests/utils/mock_api_client.py`) enables comprehensive testing
- Cogs can be tested without running the backend server
- Error scenarios can be easily simulated

### 4. Better Performance
- Connection pooling reduces overhead for multiple requests
- Keep-alive connections improve response times
- Configurable timeouts prevent hanging requests

### 5. Resource Management
- Async context manager ensures proper cleanup
- Connection pools are properly closed
- Memory leaks are prevented

## Testing Strategy

### 1. Unit Tests for API Client

```python
# tests/test_api_client.py
async def test_add_character_success(api_client, mock_response):
    with patch.object(api_client.client, 'post', return_value=mock_response):
        req = AddCharacterRequest(player_id="123", name="Test")
        result = await api_client.add_character(req)
        assert result["character_id"] == 123
```

### 2. Mock Client for Cog Testing

```python
# tests/test_character_cog.py
async def test_add_character_success(character_cog_with_mock_client, mock_interaction):
    cog = character_cog_with_mock_client
    cog.api_client.set_response_override('add_character', {'character_id': 123})
    
    await cog._handle_character_add(mock_interaction, "Test Character")
    
    # Verify interaction response and API client calls
    assert len(cog.api_client.call_history) == 1
```

### 3. Integration Tests

Integration tests can be run against a real backend server by removing the `@pytest.mark.skip` decorator from integration test methods.

## Error Schema Validation

The backend API must return errors in the following structured format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input provided",
    "details": {
      "field": "name",
      "reason": "Name cannot be empty"
    }
  }
}
```

This ensures consistent error handling across all endpoints.

## API Versioning Support

The client uses versioned URLs (`/api/v1/...`) to support future API versions:

```python
url = "/api/v1/characters/add"  # Version is explicit in the URL
```

Future versions can be supported by:
1. Adding version parameter to the client constructor
2. Using version-specific URL prefixes
3. Implementing version-specific error handling if needed

## Security Considerations

1. **Input Validation**: All requests use Pydantic models for validation
2. **Error Message Sanitization**: Error details don't leak sensitive information
3. **Connection Security**: HTTPS is supported for production deployments
4. **Timeout Configuration**: Prevents hanging requests and resource exhaustion

## Performance Optimizations

1. **Connection Pooling**: Reuses HTTP connections for better performance
2. **Keep-Alive**: Maintains persistent connections when possible
3. **Configurable Timeouts**: Prevents resource exhaustion
4. **Async Operations**: Non-blocking I/O for better concurrency

## Migration Checklist

- [x] Refactor ApiClient to use direct endpoint paths
- [x] Integrate ApiClient into CharacterCog
- [x] Integrate ApiClient into CampaignCog
- [x] Centralize error handling in ApiClient
- [x] Implement connection pooling
- [x] Add API versioning support
- [x] Create comprehensive unit tests
- [x] Create mock client for testing
- [x] Add async context manager support
- [x] Document usage patterns and examples
- [ ] Integrate ApiClient into remaining cogs (AdminCog, UtilityCog)
- [ ] Run integration tests against live backend
- [ ] Update deployment documentation
- [ ] Conduct performance testing

## Usage Examples

See `examples/api_client_usage.py` for comprehensive usage examples including:
- Character CRUD operations
- Campaign management
- Server configuration
- Error handling patterns
- Resource management

## Troubleshooting

### Common Issues

1. **Connection Errors**: Check that the backend API is running and accessible
2. **Timeout Errors**: Increase timeout value or check backend performance
3. **Validation Errors**: Ensure request models match API expectations
4. **Resource Leaks**: Always use async context managers or call `close()` manually

### Debug Mode

Enable debug logging to see HTTP requests and responses:

```python
import logging
logging.getLogger("httpx").setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Retry Logic**: Add automatic retry for transient failures
2. **Circuit Breaker**: Implement circuit breaker pattern for resilience
3. **Metrics**: Add request/response metrics and monitoring
4. **Caching**: Implement response caching for read-heavy operations
5. **Rate Limiting**: Add client-side rate limiting to prevent API abuse

## Conclusion

The thin API client implementation successfully achieves the goals outlined in the design document:

- **Reduced complexity** in cogs by eliminating HTTP boilerplate
- **Centralized error handling** with consistent exception mapping
- **Improved testability** through mock client support
- **Better performance** via connection pooling
- **Resource safety** through proper cleanup mechanisms

The implementation follows best practices for async Python development and provides a solid foundation for future API client enhancements.