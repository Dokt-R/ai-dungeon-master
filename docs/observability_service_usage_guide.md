# Observability Service Usage Guide

## Overview

The Observability Service (`packages/backend/components/observability_service.py`) provides comprehensive monitoring, tracing, and observability features for the AI Dungeon Master system using LangSmith integration.

### Purpose
- LangSmith tracing integration for AI operations
- Circuit breaker pattern for observability failures
- Health monitoring and status reporting
- Correlation ID tracking across requests
- Performance metrics and tracing decorators
- Automatic AI operation wrapping
- Custom trace tags for AI-specific operations

## Key Components

### Classes

#### `ObservabilityService`
Main service class providing observability functionality.

**Key Methods:**
- `initialize()` - Initialize LangSmith client and tracing
- `get_health_status()` - Get service health information
- `is_initialized()` - Check if service is initialized
- `trace_operation(operation_name, **tags)` - Context manager for tracing
- `trace_ai_operation(operation_name, **kwargs)` - Decorator for AI operations
- `create_trace_with_correlation(operation_name, **tags)` - Create correlated traces

#### `ObservabilityConfig`
Configuration dataclass for observability settings.

**Configuration Parameters:**
- `api_key`: LangSmith API key
- `project`: Project name (default: "ai-dungeon-master")
- `endpoint`: Custom LangSmith endpoint URL
- `tracing_enabled`: Enable/disable tracing (default: True)

#### `CircuitBreaker`
Circuit breaker implementation for observability resilience.

**States:**
- `CLOSED`: Normal operation
- `OPEN`: Circuit is open, failing fast
- `HALF_OPEN`: Testing service recovery

#### `ConfigurationValidator`
Validates observability configuration at startup.

### Tracing Context Managers

#### `trace_operation`
General-purpose operation tracing.

```python
with observability_service.trace_operation("database_query", table="monsters") as trace_id:
    result = database.query_monsters()
    print(f"Trace ID: {trace_id}")
```

#### `trace_llm_call`
LLM-specific call tracing.

```python
with observability_service.trace_llm_call("gpt-4", prompt="Generate story") as trace_id:
    response = await ai_client.generate_text("Generate story")
```

#### `trace_ai_workflow`
Complete AI workflow tracing.

```python
with observability_service.trace_ai_workflow("narrative_generation") as trace_id:
    story = await generate_dungeon_story()
```

### Tracing Decorators

#### `@trace_ai_operation`
Automatic tracing for AI operations.

```python
@observability_service.trace_ai_operation(
    operation_name="generate_monster",
    operation_type="ai_generation",
    include_args=True,
    include_result=False
)
async def generate_monster_stats(monster_name: str) -> dict:
    return await ai_client.generate_monster(monster_name)
```

#### `@trace_llm_call_decorator`
LLM call tracing decorator.

```python
@observability_service.trace_llm_call_decorator(
    model_name="gpt-4",
    include_prompt=True,
    include_response=False
)
async def generate_narrative(prompt: str) -> str:
    return await ai_client.generate_text(prompt)
```

#### `@trace_ai_workflow_decorator`
AI workflow tracing decorator.

```python
@observability_service.trace_ai_workflow_decorator(
    workflow_name="dungeon_generation",
    workflow_type="content_generation"
)
async def generate_dungeon() -> dict:
    return await dungeon_generator.generate()
```

## Dependencies

### External Dependencies
- `langsmith` package for tracing integration
- `urllib.parse` for URL validation
- `os` for environment variable access

### Internal Dependencies
- `packages.shared.logging_config` - Structured logging
- `packages.shared.correlation` - Correlation ID management

## Environment Variables

```bash
# Required
export LANGSMITH_API_KEY="ls__your_api_key_here"

# Optional
export LANGSMITH_PROJECT="ai-dungeon-master"
export LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
```

## Configuration

### Basic Configuration
```python
from packages.backend.components.observability_service import ObservabilityConfig

config = ObservabilityConfig(
    api_key="ls__your_api_key",
    project="ai-dungeon-master",
    endpoint="https://api.smith.langchain.com",
    tracing_enabled=True
)
```

### Environment-Based Configuration
```python
# Automatic configuration from environment
config = observability_service.load_config()
```

### Custom Configuration Validation
```python
# Manual configuration validation
validation_result = observability_service.validate_config_only()

if not validation_result.is_valid:
    for error in validation_result.errors:
        print(f"Configuration error: {error}")
else:
    print("Configuration is valid")
```

## Usage Examples

### Basic Initialization

```python
from packages.backend.components.observability_service import observability_service

# Initialize with environment configuration
success = await observability_service.initialize()
if success:
    print("Observability service initialized")
else:
    print("Failed to initialize observability service")
```

### Custom Initialization

```python
from packages.backend.components.observability_service import ObservabilityServiceFactory

# Create service with custom configuration
config = ObservabilityConfig(
    api_key="ls__custom_key",
    project="my-dungeon-master",
    tracing_enabled=True
)

service = ObservabilityServiceFactory.create_service(config)
```

### Health Monitoring

```python
# Get service health status
health = observability_service.get_health_status()

print(f"Status: {health['status']}")
print(f"Provider: {health['provider']}")
print(f"Project: {health['project']}")
print(f"Tracing Enabled: {health['tracing_enabled']}")
print(f"Circuit Breaker: {health['circuit_breaker']['state']}")

# Check circuit breaker state
if observability_service.is_circuit_breaker_open():
    print("Circuit breaker is open - observability temporarily disabled")
```

### Operation Tracing

```python
# Basic operation tracing
with observability_service.trace_operation("user_registration", user_id="12345") as trace_id:
    user = await create_user("john@example.com")
    print(f"User created with trace: {trace_id}")
```

### LLM Call Tracing

```python
# Trace LLM interactions
async def generate_monster_description(monster_name: str) -> str:
    prompt = f"Describe the {monster_name} from D&D 5.1 SRD"

    with observability_service.trace_llm_call("gpt-4", prompt) as trace_id:
        response = await ai_client.generate_text(prompt)

        # Add response data to trace
        observability_service.trace_llm_response(
            trace_id,
            response,
            "gpt-4"
        )

        return response
```

### AI Workflow Tracing

```python
# Trace complete AI workflows
async def generate_campaign_intro(campaign_name: str) -> dict:
    with observability_service.trace_ai_workflow(
        "campaign_intro_generation",
        campaign_name=campaign_name
    ) as trace_id:
        # Generate campaign intro
        intro = await ai_client.generate_text(f"Create intro for {campaign_name}")

        # Generate key locations
        locations = await ai_client.generate_text("Generate key locations")

        # Generate main quest
        quest = await ai_client.generate_text("Generate main quest")

        return {
            "intro": intro,
            "locations": locations,
            "quest": quest,
            "trace_id": trace_id
        }
```

### Using Tracing Decorators

```python
class DungeonMasterService:
    """Service with automatic tracing."""

    def __init__(self):
        self.observability = observability_service

    @observability_service.trace_ai_operation(
        operation_name="generate_monster",
        operation_type="content_generation",
        include_args=True,
        include_result=True
    )
    async def generate_monster(self, monster_type: str, challenge_rating: int) -> dict:
        """Generate a monster with automatic tracing."""
        prompt = f"Generate a {monster_type} with CR {challenge_rating}"
        response = await ai_client.generate_text(prompt)

        monster_data = self.parse_monster_response(response)
        return monster_data

    @observability_service.trace_llm_call_decorator(
        model_name="gpt-4",
        include_prompt=True,
        include_response=True
    )
    async def generate_spell_description(self, spell_name: str) -> str:
        """Generate spell description with LLM tracing."""
        prompt = f"Describe the {spell_name} spell from D&D 5.1 SRD"
        return await ai_client.generate_text(prompt)

    @observability_service.trace_ai_workflow_decorator(
        workflow_name="dungeon_generation",
        workflow_type="world_building"
    )
    async def generate_dungeon(self, dungeon_theme: str, difficulty: str) -> dict:
        """Generate complete dungeon with workflow tracing."""
        # Multiple AI calls for dungeon generation
        description = await ai_client.generate_text(f"Describe {dungeon_theme} dungeon")
        encounters = await ai_client.generate_text(f"Generate encounters for {difficulty} dungeon")
        traps = await ai_client.generate_text(f"Design traps for {dungeon_theme} dungeon")

        return {
            "description": description,
            "encounters": encounters,
            "traps": traps
        }
```

### Decision Point Tracing

```python
# Trace AI decision-making points
async def make_combat_decision(combat_state: dict) -> str:
    """Make combat decision with decision tracing."""
    trace_id = "combat_decision_123"

    options = ["Attack", "Defend", "Retreat", "Use Special Ability"]
    chosen_option = "Attack"  # AI decision logic here

    observability_service.trace_decision_point(
        trace_id=trace_id,
        decision_type="combat_tactics",
        options=options,
        chosen_option=chosen_option,
        reasoning="Enemy is vulnerable to direct attack"
    )

    return chosen_option
```

### Correlation ID Management

```python
# Automatic correlation ID handling
from packages.shared.correlation import get_correlation_id, set_correlation_id

async def handle_user_request(user_id: str, request: str):
    """Handle user request with correlation tracking."""
    # Create trace with correlation ID
    trace_id = observability_service.create_trace_with_correlation(
        "user_request",
        user_id=user_id,
        request_type="story_generation"
    )

    with observability_service.trace_operation("user_request", user_id=user_id) as trace_id:
        # Get current correlation ID
        correlation_id = get_correlation_id()
        print(f"Processing request with correlation ID: {correlation_id}")

        response = await process_request(request)

        return {"response": response, "correlation_id": correlation_id}
```

## Error Handling

### Circuit Breaker Pattern

```python
# Circuit breaker automatically handles failures
try:
    with observability_service.trace_operation("risky_operation") as trace_id:
        result = await perform_risky_operation()
except Exception as e:
    if "Circuit breaker is open" in str(e):
        logger.warning("Observability circuit breaker is open")
        # Continue without tracing
        result = await perform_risky_operation()
```

### Graceful Degradation

```python
# Continue operation even if observability fails
async def safe_trace_operation(operation_name: str, operation_func):
    """Execute operation with safe tracing."""
    if not observability_service.is_initialized():
        return await operation_func()  # No tracing

    if observability_service.is_circuit_breaker_open():
        return await operation_func()  # Circuit breaker open

    try:
        with observability_service.trace_operation(operation_name) as trace_id:
            return await operation_func()
    except Exception as e:
        logger.warning(f"Tracing failed for {operation_name}: {e}")
        return await operation_func()  # Continue without tracing
```

### Configuration Validation

```python
# Validate configuration before initialization
try:
    config = observability_service.load_config()
    validation = observability_service.validate_config_only()

    if not validation.is_valid:
        for error in validation.errors:
            logger.error(f"Configuration error: {error}")
        raise ConfigurationError("Invalid observability configuration")

    # Log warnings
    for warning in validation.warnings:
        logger.warning(f"Configuration warning: {warning}")

    # Log recommendations
    for recommendation in validation.recommendations:
        logger.info(f"Configuration recommendation: {recommendation}")

except Exception as e:
    logger.error(f"Observability configuration failed: {e}")
    # Continue without observability
    observability_service = None
```

## Integration Points

### With AI Client

```python
# packages/backend/components/ai_client.py
from packages.backend.components.observability_service import observability_service

class AIClient:
    """AI client with observability integration."""

    def __init__(self):
        self.observability = observability_service

    async def generate_text_with_tracing(self, prompt: str) -> str:
        """Generate text with automatic tracing."""
        with self.observability.trace_llm_call("gpt-4", prompt) as trace_id:
            response = await self._generate_text(prompt)

            # Add performance metrics
            self.observability._add_performance_metrics(trace_id, 0.5, "text_generation")

            return response

    @observability_service.trace_ai_operation(
        operation_name="ai_text_generation",
        operation_type="llm_call",
        include_args=True,
        include_result=False
    )
    async def _generate_text(self, prompt: str) -> str:
        """Internal text generation with automatic tracing."""
        return await self.provider.generate_text(prompt)
```

### With Backend Main

```python
# packages/backend/main.py
from packages.backend.components.observability_service import observability_service

async def initialize_services():
    """Initialize all backend services with observability."""

    # Initialize observability first
    if not await observability_service.initialize():
        logger.warning("Observability service failed to initialize")
        # Continue without observability

    # Initialize other services
    await initialize_ai_client()
    await initialize_memory_service()
    await initialize_api_endpoints()

    logger.info("All services initialized")
```

### With API Endpoints

```python
# packages/backend/api/dungeon_api.py
from packages.backend.components.observability_service import observability_service
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/generate-dungeon")
async def generate_dungeon(request: DungeonRequest):
    """Generate dungeon with tracing."""
    with observability_service.trace_ai_workflow("dungeon_generation") as trace_id:
        try:
            dungeon = await dungeon_generator.generate(request.theme, request.difficulty)

            # Add custom trace tags
            observability_service.add_custom_trace_tags(trace_id, {
                "theme": request.theme,
                "difficulty": request.difficulty,
                "dungeon_size": len(dungeon["rooms"])
            })

            return {"dungeon": dungeon, "trace_id": trace_id}

        except Exception as e:
            logger.error("Dungeon generation failed", error=str(e), trace_id=trace_id)
            raise HTTPException(status_code=500, detail="Generation failed")
```

### With Memory Service

```python
# packages/backend/components/memory_service.py
from packages.backend.components.observability_service import observability_service

class MemoryService:
    """Memory service with observability."""

    @observability_service.trace_ai_operation(
        operation_name="store_memory",
        operation_type="data_storage",
        include_args=False,
        include_result=True
    )
    async def store_memory(self, content: str, metadata: dict) -> str:
        """Store memory with tracing."""
        memory_id = await self._store(content, metadata)

        # Add performance data
        observability_service._add_result_metadata(
            "unknown",  # trace_id would be provided by decorator
            {"memory_id": memory_id, "content_length": len(content)},
            "memory_storage"
        )

        return memory_id
```

## Performance Considerations

### Circuit Breaker Tuning

```python
# Configure circuit breaker for high-traffic scenarios
from packages.backend.components.observability_service import CircuitBreakerConfig

circuit_breaker_config = CircuitBreakerConfig(
    failure_threshold=10,        # Allow more failures
    recovery_timeout=60.0,       # Shorter recovery time
    success_threshold=3,         # Require fewer successes
    expected_exception=(ObservabilityError, ConnectionError)
)

# Create service with custom circuit breaker
observability_service = ObservabilityService()
observability_service._circuit_breaker = CircuitBreaker(circuit_breaker_config)
```

### Sampling and Filtering

```python
# Implement sampling for high-volume operations
class SamplingObservabilityService(ObservabilityService):
    """Observability service with sampling."""

    def __init__(self, sample_rate: float = 0.1):
        super().__init__()
        self.sample_rate = sample_rate  # Sample 10% of operations

    def should_trace(self, operation_name: str) -> bool:
        """Determine if operation should be traced."""
        import random
        return random.random() < self.sample_rate
```

### Batch Operations

```python
# Batch trace operations for efficiency
async def batch_trace_operations(operations: List[dict]) -> List[str]:
    """Execute multiple operations with tracing."""
    trace_ids = []

    for operation in operations:
        with observability_service.trace_operation(
            operation["name"],
            **operation.get("tags", {})
        ) as trace_id:
            result = await execute_operation(operation)
            trace_ids.append(trace_id)

    return trace_ids
```

## Best Practices

### 1. Initialization

```python
# Always check initialization success
if not await observability_service.initialize():
    logger.warning("Observability initialization failed - continuing without tracing")
    # Application should continue to function
```

### 2. Error Handling

```python
# Never let observability failures crash the application
async def safe_observability_operation():
    """Execute operation with safe observability."""
    try:
        if observability_service.is_initialized():
            with observability_service.trace_operation("safe_operation") as trace_id:
                return await perform_operation()
        else:
            return await perform_operation()
    except Exception as e:
        logger.error(f"Observability operation failed: {e}")
        return await perform_operation()  # Continue without tracing
```

### 3. Resource Management

```python
# Properly manage resources
async def cleanup_observability():
    """Clean up observability resources."""
    if observability_service.is_initialized():
        # Close connections, flush traces, etc.
        observability_service.close()
```

### 4. Configuration Management

```python
# Validate configuration in different environments
def get_environment_config() -> ObservabilityConfig:
    """Get configuration appropriate for current environment."""
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        return ObservabilityConfig(
            api_key=os.getenv("LANGSMITH_API_KEY"),
            project="ai-dungeon-master-prod",
            tracing_enabled=True
        )
    elif env == "staging":
        return ObservabilityConfig(
            api_key=os.getenv("LANGSMITH_API_KEY"),
            project="ai-dungeon-master-staging",
            tracing_enabled=True
        )
    else:  # development
        return ObservabilityConfig(
            api_key="dev-key",
            project="ai-dungeon-master-dev",
            tracing_enabled=False  # Disable in development
        )
```

### 5. Monitoring and Alerting

```python
# Implement health checks
async def health_check_observability():
    """Check observability service health."""
    health = observability_service.get_health_status()

    if health["status"] != "healthy":
        # Send alert
        await send_alert("Observability service unhealthy", health)

    # Check circuit breaker
    if observability_service.is_circuit_breaker_open():
        await send_alert("Observability circuit breaker open", health["circuit_breaker"])

    return health
```

## Troubleshooting

### Common Issues

#### 1. Configuration Errors

```python
# Debug configuration issues
try:
    config = observability_service.load_config()
    validation = observability_service.validate_config_only()

    print("Configuration loaded successfully")
    print(f"API Key: {config.api_key[:10]}...")  # Don't log full key
    print(f"Project: {config.project}")
    print(f"Endpoint: {config.endpoint}")

    if not validation.is_valid:
        print("Configuration validation errors:")
        for error in validation.errors:
            print(f"  - {error}")

    if validation.warnings:
        print("Configuration warnings:")
        for warning in validation.warnings:
            print(f"  - {warning}")

except Exception as e:
    print(f"Configuration error: {e}")
```

#### 2. Circuit Breaker Issues

```python
# Handle circuit breaker states
def handle_circuit_breaker_state():
    """Handle different circuit breaker states."""
    state = observability_service.get_circuit_breaker_state()

    if state["state"] == "OPEN":
        print("Circuit breaker is OPEN")
        print(f"Last failure: {state['last_failure_time']}")
        print(f"Failure count: {state['failure_count']}")

        if state["can_attempt_reset"]:
            print("Can attempt reset")
            observability_service.reset_circuit_breaker()
            print("Circuit breaker reset")
        else:
            print("Cannot reset yet - wait for recovery timeout")

    elif state["state"] == "HALF_OPEN":
        print("Circuit breaker is HALF_OPEN - testing recovery")

    else:
        print("Circuit breaker is CLOSED - normal operation")
```

#### 3. Tracing Failures

```python
# Handle tracing failures gracefully
async def trace_with_fallback(operation_name: str, operation_func):
    """Execute operation with tracing fallback."""
    if not observability_service.is_initialized():
        logger.debug("Observability not initialized - executing without tracing")
        return await operation_func()

    try:
        with observability_service.trace_operation(operation_name) as trace_id:
            return await operation_func()
    except Exception as e:
        logger.warning(f"Tracing failed: {e} - executing without tracing")
        return await operation_func()
```

#### 4. Performance Issues

```python
# Monitor tracing performance
import time

async def monitor_tracing_performance():
    """Monitor tracing overhead."""
    start_time = time.time()

    # Execute traced operation
    with observability_service.trace_operation("performance_test") as trace_id:
        result = await perform_test_operation()

    tracing_time = time.time() - start_time

    # Log performance metrics
    logger.info(
        "tracing_performance",
        trace_id=trace_id,
        total_time=tracing_time,
        operation="performance_test"
    )

    if tracing_time > 1.0:  # More than 1 second
        logger.warning("Tracing overhead is high", tracing_time=tracing_time)
```

#### 5. Memory Issues

```python
# Handle memory constraints
class MemoryAwareObservabilityService(ObservabilityService):
    """Observability service with memory awareness."""

    def __init__(self, max_memory_mb: int = 100):
        super().__init__()
        self.max_memory_mb = max_memory_mb

    def should_skip_tracing(self, operation_name: str) -> bool:
        """Determine if tracing should be skipped based on memory."""
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb > self.max_memory_mb:
            logger.warning(f"Skipping tracing due to high memory usage: {memory_mb:.1f}MB")
            return True

        return False
```

## Security Considerations

### API Key Management

```python
# Never log API keys
logger.info("Observability configured")  # Don't include api_key

# Use environment variables
# Don't hardcode API keys in configuration files
```

### Input Validation

```python
# Validate trace inputs
def sanitize_trace_input(data: Any) -> Any:
    """Sanitize data before adding to traces."""
    if isinstance(data, dict):
        # Remove sensitive keys
        sensitive_keys = ["password", "token", "secret", "key"]
        return {k: v for k, v in data.items() if k.lower() not in sensitive_keys}
    return data
```

### Access Control

```python
# Implement access controls for observability data
class SecuredObservabilityService(ObservabilityService):
    """Observability service with access controls."""

    def __init__(self, allowed_projects: List[str]):
        super().__init__()
        self.allowed_projects = allowed_projects

    def validate_project_access(self, project: str) -> bool:
        """Validate access to project."""
        return project in self.allowed_projects

    async def initialize(self) -> bool:
        """Initialize with access validation."""
        if not self.validate_project_access(self._config.project):
            logger.error(f"Access denied to project: {self._config.project}")
            return False

        return await super().initialize()
```

This comprehensive guide covers all aspects of using the Observability Service effectively for monitoring and tracing the AI Dungeon Master system.