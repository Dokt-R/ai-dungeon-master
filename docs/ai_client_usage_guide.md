# AI Client Usage Guide

## Overview

The AI Client (`packages/backend/components/ai_client.py`) is a provider-agnostic interface for integrating multiple AI services (OpenAI, Anthropic, etc.) with built-in resilience features including circuit breaker patterns, retry logic, and comprehensive error handling.

### Purpose
- Unified interface for multiple AI providers
- Automatic failover and resilience
- Secure credential management
- LangSmith tracing integration
- Production-ready error handling

## Key Components

### Classes

#### `AIClient`
Singleton service class providing the main AI client functionality.

**Key Methods:**
- `initialize(config=None)` - Initialize with configuration
- `generate_text(prompt, max_tokens=None, temperature=None, **kwargs)` - Generate text
- `generate_chat(messages, max_tokens=None, temperature=None, **kwargs)` - Generate chat responses
- `get_health_status()` - Get service health status

#### `AIClientConfig`
Configuration dataclass for AI client settings.

**Configuration Parameters:**
- `provider`: AI provider (OPENAI, ANTHROPIC)
- `api_key`: API key for authentication
- `base_url`: Custom API endpoint URL
- `model`: AI model name (default: "gpt-4")
- `timeout`: Request timeout in seconds (default: 30.0)
- `max_retries`: Maximum retry attempts (default: 3)
- `retry_delay`: Initial delay between retries (default: 1.0)
- `circuit_breaker_threshold`: Circuit breaker trigger threshold (default: 5)
- `circuit_breaker_timeout`: Circuit breaker recovery timeout (default: 300.0)

#### `AICircuitBreaker`
Implements circuit breaker pattern for resilience.

**States:**
- `CLOSED`: Normal operation
- `OPEN`: Circuit is open, failing fast
- `HALF_OPEN`: Testing service recovery

#### `AIProviderInterface`
Abstract base class for AI provider implementations.

#### `OpenAIProvider`
OpenAI-specific implementation of the AI provider interface.

### Exception Classes
- `AIClientError`: Base exception for AI client errors
- `ConfigurationError`: Configuration validation errors
- `ConnectionError`: Connection and API errors
- `RateLimitError`: Rate limiting errors
- `AuthenticationError`: Authentication failures

## Dependencies

### External Dependencies
- `openai` package for OpenAI API integration
- `langsmith` package for tracing (optional)

### Internal Dependencies
- `packages.backend.components.observability_service` - Tracing integration
- `packages.shared.logging_config` - Structured logging

## Environment Variables

```bash
# Required
export AI_PROVIDER_API_KEY="your_api_key_here"

# Optional
export AI_PROVIDER="openai"                    # openai or anthropic
export AI_PROVIDER_BASE_URL="https://api.openai.com/v1"
export AI_PROVIDER_MODEL="gpt-4"
export AI_PROVIDER_TIMEOUT="30.0"
export AI_PROVIDER_MAX_RETRIES="3"
export AI_PROVIDER_RETRY_DELAY="1.0"
export AI_CIRCUIT_BREAKER_THRESHOLD="5"
export AI_CIRCUIT_BREAKER_TIMEOUT="300.0"
export AI_CONNECTION_POOL_SIZE="10"
```

## Error Handling

### Circuit Breaker Pattern
The AI client implements a circuit breaker to prevent cascade failures:

```python
# Circuit breaker automatically handles failures
try:
    response = await ai_client.generate_text("Hello, world!")
except ConnectionError as e:
    if "Circuit breaker is open" in str(e):
        # Service temporarily unavailable
        logger.warning("AI service temporarily unavailable")
```

### Retry Logic
Automatic retry with exponential backoff for transient failures:

```python
# Automatic retries for rate limits and temporary failures
response = await ai_client.generate_text(
    prompt="Generate story content",
    max_tokens=1000,
    temperature=0.7
)
```

### Error Types
```python
from packages.backend.components.ai_client import (
    AIClientError, ConfigurationError, ConnectionError,
    RateLimitError, AuthenticationError
)

try:
    await ai_client.generate_text("test")
except ConfigurationError:
    # Invalid configuration
    pass
except AuthenticationError:
    # API key invalid
    pass
except RateLimitError:
    # Rate limit exceeded
    pass
except ConnectionError:
    # Network/API issues
    pass
except AIClientError:
    # General AI client errors
    pass
```

## Usage Examples

### Basic Text Generation

```python
from packages.backend.components.ai_client import ai_client

# Initialize with environment variables
success = await ai_client.initialize()
if success:
    # Generate text
    response = await ai_client.generate_text(
        prompt="Create a dungeon description",
        max_tokens=500,
        temperature=0.8
    )
    print(f"Generated: {response}")
```

### Chat Completion

```python
from packages.backend.components.ai_client import ai_client

# Initialize client
await ai_client.initialize()

# Generate chat response
messages = [
    {"role": "system", "content": "You are a dungeon master."},
    {"role": "user", "content": "What's in this room?"}
]

response = await ai_client.generate_chat(
    messages=messages,
    max_tokens=300,
    temperature=0.7
)
print(f"DM Response: {response}")
```

### Custom Configuration

```python
from packages.backend.components.ai_client import AIClientConfig, AIProvider

# Custom configuration
config = AIClientConfig(
    provider=AIProvider.OPENAI,
    api_key="your-api-key",
    model="gpt-4-turbo",
    timeout=60.0,
    max_retries=5,
    circuit_breaker_threshold=10
)

# Initialize with custom config
success = await ai_client.initialize(config)
```

### Health Monitoring

```python
from packages.backend.components.ai_client import ai_client

# Get health status
health = ai_client.get_health_status()
print(f"Status: {health['status']}")
print(f"Provider: {health['provider']}")
print(f"Model: {health['model']}")
print(f"Circuit Breaker: {health['circuit_breaker_state']}")
```

### Integration with Observability

```python
from packages.backend.components.ai_client import ai_client
from packages.backend.components.observability_service import observability_service

# Initialize both services
await ai_client.initialize()
await observability_service.initialize()

# Traced AI operation
with observability_service.trace_operation("story_generation") as trace_id:
    response = await ai_client.generate_text(
        prompt="Generate a fantasy story",
        max_tokens=1000
    )
    print(f"Trace ID: {trace_id}")
    print(f"Generated: {response}")
```

### Error Recovery

```python
from packages.backend.components.ai_client import ai_client, AIClientError

async def generate_with_fallback(prompt: str) -> str:
    """Generate text with fallback handling."""
    try:
        return await ai_client.generate_text(prompt)
    except AIClientError as e:
        logger.error(f"AI generation failed: {e}")

        # Check if circuit breaker is open
        if "Circuit breaker is open" in str(e):
            # Use cached or default response
            return "Service temporarily unavailable. Please try again later."

        # For other errors, re-raise
        raise
```

### Testing with Mock Provider

```python
from packages.backend.components.ai_client import AIClient, AIProviderInterface

class MockProvider(AIProviderInterface):
    """Mock provider for testing."""

    def __init__(self, config):
        super().__init__(config)

    async def initialize(self):
        pass

    async def generate_text(self, prompt, **kwargs):
        return f"Mock response to: {prompt}"

    async def generate_chat(self, messages, **kwargs):
        return "Mock chat response"

    async def close(self):
        pass

# Use mock provider for testing
mock_config = AIClientConfig(
    provider=AIProvider.OPENAI,  # Any provider type
    api_key="mock-key"
)

client = AIClient()
# Manually inject mock provider
client._provider = MockProvider(mock_config)
client._is_initialized = True

response = await client.generate_text("test prompt")
assert response == "Mock response to: test prompt"
```

## Integration Points

### With Backend Main
```python
# packages/backend/main.py
from packages.backend.components.ai_client import ai_client

async def initialize_services():
    """Initialize all backend services."""
    # Initialize AI client
    if not await ai_client.initialize():
        logger.error("Failed to initialize AI client")
        return False

    logger.info("AI client initialized successfully")
    return True
```

### With API Endpoints
```python
# packages/backend/api/ai_api.py
from packages.backend.components.ai_client import ai_client
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/generate")
async def generate_text(request: GenerateTextRequest):
    """Generate text using AI client."""
    try:
        response = await ai_client.generate_text(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        return {"generated_text": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### With Dungeon Master Agent
```python
# packages/backend/agents/dm_graph.py
from packages.backend.components.ai_client import ai_client

class DungeonMasterAgent:
    """AI-powered dungeon master."""

    def __init__(self):
        self.ai_client = ai_client

    async def generate_narrative(self, prompt: str) -> str:
        """Generate narrative content."""
        system_prompt = """You are an expert dungeon master..."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        return await self.ai_client.generate_chat(
            messages=messages,
            max_tokens=1000,
            temperature=0.8
        )
```

## Best Practices

### 1. Initialization
```python
# Always check initialization success
if not await ai_client.initialize():
    logger.error("AI client failed to initialize")
    # Handle initialization failure
```

### 2. Error Handling
```python
# Always wrap AI calls in try-catch
try:
    response = await ai_client.generate_text(prompt)
except RateLimitError:
    # Implement backoff strategy
    await asyncio.sleep(60)
    response = await ai_client.generate_text(prompt)
except ConnectionError as e:
    if "Circuit breaker" in str(e):
        # Use fallback response
        response = get_fallback_response()
```

### 3. Resource Management
```python
# Always close resources
try:
    await ai_client.initialize()
    # Use AI client
finally:
    await ai_client.close()
```

### 4. Configuration Validation
```python
# Validate configuration before use
from packages.backend.components.ai_client import AIClientConfig

try:
    config = AIClientConfig.from_env()
    # Configuration is valid
except ConfigurationError as e:
    logger.error(f"Invalid configuration: {e}")
    # Handle configuration error
```

### 5. Monitoring and Observability
```python
# Use health checks in monitoring
health = ai_client.get_health_status()
if health["status"] != "healthy":
    logger.warning(f"AI client unhealthy: {health['error']}")

# Include circuit breaker status in metrics
if health["circuit_breaker_state"] == "OPEN":
    logger.warning("AI service circuit breaker is open")
```

## Performance Considerations

### Circuit Breaker Tuning
```python
# Adjust circuit breaker for high-traffic scenarios
config = AIClientConfig(
    circuit_breaker_threshold=10,    # Allow more failures
    circuit_breaker_timeout=600,     # Longer recovery time
    max_retries=5,                   # More retry attempts
    retry_delay=2.0                  # Longer initial delay
)
```

### Connection Pooling
```python
# Configure connection pool for high throughput
config = AIClientConfig(
    connection_pool_size=20,         # More concurrent connections
    timeout=120.0                    # Longer timeout for complex requests
)
```

### Batch Processing
```python
# Process multiple requests efficiently
async def batch_generate(prompts: List[str]) -> List[str]:
    """Generate multiple texts concurrently."""
    tasks = [
        ai_client.generate_text(prompt, max_tokens=500)
        for prompt in prompts
    ]
    return await asyncio.gather(*tasks)
```

## Troubleshooting

### Common Issues

#### 1. Configuration Errors
```python
# Check environment variables
import os
required_vars = ["AI_PROVIDER_API_KEY"]
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    logger.error(f"Missing environment variables: {missing}")
```

#### 2. Circuit Breaker Issues
```python
# Check circuit breaker state
health = ai_client.get_health_status()
if health["circuit_breaker_state"] == "OPEN":
    # Reset manually if needed
    ai_client.reset_instance()
    await ai_client.initialize()
```

#### 3. Rate Limiting
```python
# Implement rate limit handling
from packages.backend.components.ai_client import RateLimitError

async def generate_with_rate_limit_handling(prompt: str) -> str:
    """Handle rate limits gracefully."""
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            return await ai_client.generate_text(prompt)
        except RateLimitError:
            wait_time = (2 ** attempt) * 60  # Exponential backoff
            logger.warning(f"Rate limited, waiting {wait_time}s")
            await asyncio.sleep(wait_time)

    raise Exception("Max attempts exceeded")
```

#### 4. Network Issues
```python
# Implement retry with network error handling
async def generate_with_retry(prompt: str) -> str:
    """Retry on network issues."""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            return await ai_client.generate_text(prompt)
        except ConnectionError as e:
            if attempt == max_attempts - 1:
                raise
            logger.warning(f"Network error, retrying ({attempt + 1}/{max_attempts})")
            await asyncio.sleep(2 ** attempt)
```

## Security Considerations

### API Key Management
```python
# Never log API keys
logger.info("AI client initialized")  # Don't include api_key in logs

# Use environment variables for secrets
# Don't hardcode API keys in code
```

### Input Validation
```python
# Validate prompts before sending to AI
def validate_prompt(prompt: str) -> bool:
    """Validate AI prompt."""
    if not prompt or len(prompt) > 10000:
        return False
    # Add more validation as needed
    return True

if validate_prompt(user_prompt):
    response = await ai_client.generate_text(user_prompt)
```

### Output Sanitization
```python
# Sanitize AI responses before use
import re

def sanitize_response(response: str) -> str:
    """Sanitize AI response."""
    # Remove potentially harmful content
    # Add your sanitization logic here
    return response.strip()
```

This comprehensive guide covers all aspects of using the AI Client effectively in the AI Dungeon Master system.