# Observability

To ensure long-term maintainability and assist in debugging the AI's behavior, the architecture includes comprehensive observability infrastructure with detailed tracing, monitoring, and logging capabilities.

## LLM Observability - LangSmith Integration

The system integrates with **LangSmith** to provide detailed, step-by-step traces of AI operations and decision-making processes. This is a foundational component for Epic 2 AI integration work.

### Core Components

#### ObservabilityService (`packages/backend/components/observability_service.py`)

A singleton service that manages LangSmith integration with the following capabilities:

- **Environment Configuration**: Secure handling of API keys and project settings
- **Client Initialization**: Lazy initialization with circuit breaker protection
- **Health Monitoring**: Comprehensive health checks and status reporting
- **Configuration Validation**: Startup-time validation with detailed error reporting
- **Error Handling**: Graceful degradation when LangSmith is unavailable

#### Key Features

**Tracing Decorators:**
- `@trace_ai_operation()` - Generic AI operation tracing with performance metrics
- `@trace_llm_call_decorator()` - LLM API call tracing with prompt/response tracking
- `@trace_ai_workflow_decorator()` - Complete AI workflow tracing with nested operations

**Context Managers:**
- `trace_operation()` - Basic operation tracing with custom metadata
- `trace_llm_call()` - LLM-specific tracing with model information
- `trace_ai_workflow()` - Workflow tracing with stage/step tracking

**Advanced Features:**
- **Circuit Breaker Pattern**: Automatic failure detection and recovery
- **Dependency Injection**: Factory patterns for improved testability
- **Correlation ID Integration**: Automatic trace correlation with request IDs
- **Custom Trace Tags**: AI-specific metadata and filtering capabilities
- **Performance Monitoring**: Execution time tracking and metrics collection

### Configuration

#### Getting a LangSmith API Key

To use the observability features, you'll need a LangSmith API key:

1. **Visit LangSmith**: Go to [https://smith.langchain.com/](https://smith.langchain.com/)
2. **Sign Up/Login**: Create an account or log in with your existing credentials
3. **Create API Key**: Navigate to Settings → API Keys → Create API Key
4. **Copy Key**: The API key will start with `ls__` or `lsv2_` prefix

**Note**: LangSmith offers a generous free tier suitable for development and small-scale production use. Your API key format may vary (e.g., `ls__`, `lsv2_`, etc.) - use the exact key provided by LangSmith.

#### Environment Variables

Configure the following environment variables for LangSmith integration:

```bash
# Required - Your LangSmith API key
LANGSMITH_API_KEY=your_langsmith_api_key_here  # Use exact key from LangSmith

# Optional with defaults
LANGSMITH_PROJECT=ai-dungeon-master
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_TRACING=true  # Set to "false" to disable tracing completely
```

**Important:** Tracing is **disabled by default** (`LANGSMITH_TRACING=false`) to allow the system to work without requiring immediate LangSmith API key setup. This enables development and deployment without observability overhead until you're ready to enable tracing. Set `LANGSMITH_TRACING=true` to enable LangSmith tracing. When disabled, all tracing calls will be no-ops, ensuring zero performance impact.

#### Validation

The system performs comprehensive validation of your configuration:
- API key format verification
- Project name validation (alphanumeric, hyphens, underscores only)
- Endpoint URL validation (must be valid HTTPS URL)
- Security best practice recommendations

If configuration is invalid, the system will provide detailed error messages and fail to start.

### Health Endpoints

The observability system provides comprehensive health monitoring:

- `GET /api/health/observability` - Observability service status
- `POST /api/health/observability/test-trace` - Test trace functionality
- `GET /api/health/general` - Overall system health including observability

### Integration Points

**Backend Integration (`packages/backend/main.py`):**
- Automatic initialization during FastAPI lifespan events
- Health router integration
- Correlation ID middleware integration

**Discord Bot Integration:**
- Health monitoring commands (`/health ai`, `/health observability`)
- Real-time status reporting

**API Client Integration (`packages/shared/api_client.py`):**
- Health check methods for all services
- Circuit breaker state reporting

### Testing Infrastructure

Comprehensive test coverage across multiple levels:

**Unit Tests (`tests/unit/backend/observability/`):**
- Configuration validation and loading
- Service initialization and singleton pattern
- Health status functionality
- Mocked LangSmith integration

**Integration Tests (`tests/integration/backend/`):**
- End-to-end tracing workflows
- LangSmith client creation and configuration
- Error handling and fallback scenarios
- Performance metrics collection

### Circuit Breaker Pattern

The observability service implements a circuit breaker to handle LangSmith API failures:

- **Failure Threshold**: 3 consecutive failures trigger circuit opening
- **Recovery Timeout**: 30 seconds (1 second in tests) before attempting recovery
- **Success Threshold**: 2 consecutive successes required to fully recover
- **Graceful Degradation**: Service continues with logging-only mode when circuit is open

### Custom Trace Tags

AI-specific trace tagging system for enhanced filtering and analysis:

**Standard Tags:**
- `ai_operation: true` - Identifies AI-related operations
- `operation_type` - Specific AI operation type (llm_call, ai_workflow, embedding)
- `ai_service: ai-dungeon-master` - Service identification

**LLM-Specific Tags:**
- `llm_model` - Model name (e.g., gpt-5-nano)
- `llm_provider` - Provider (e.g., openai, anthropic)
- `prompt_tokens`, `response_tokens` - Token usage tracking
- `temperature` - Model temperature setting

**Workflow Tags:**
- `workflow_stage` - Current workflow stage
- `workflow_step` - Specific step within workflow
- `data_processed` - Size of data being processed

### Performance Monitoring

Automatic performance metrics collection for all traced operations:

- **Execution Time**: Precise timing measurement using `perf_counter`
- **Operation Type**: Categorization for performance analysis
- **Result Metadata**: Automatic extraction of result information
- **Metrics API**: `get_performance_metrics()` for historical analysis

### Correlation ID Integration

All traces automatically include correlation IDs for request tracking:

- **Automatic Propagation**: Correlation IDs from HTTP requests included in traces
- **Logging Integration**: Consistent correlation ID usage across logs and traces
- **Trace Linking**: Ability to link traces to specific user requests

### Error Handling and Resilience

**Configuration Validation:**
- Startup-time validation with detailed error messages
- Security best practice recommendations
- Environment consistency checks

**Fallback Mechanisms:**
- Logging-only mode when LangSmith is unavailable
- Import error handling for missing dependencies
- Circuit breaker protection against API failures

**Monitoring and Alerting:**
- Health status endpoints for monitoring systems
- Structured logging with appropriate severity levels
- Performance metrics for anomaly detection

## Usage Examples

### Basic Operation Tracing

```python
from packages.backend.components.observability_service import observability_service

# Context manager approach
with observability_service.trace_operation("my_operation", operation_type="data_processing") as trace_id:
    # Your operation code here
    result = perform_data_processing()
    return result
```

### AI Operation Tracing

```python
@observability_service.trace_ai_operation(
    operation_name="process_user_query",
    operation_type="ai_operation",
    include_args=True,
    include_result=False
)
def process_user_query(query: str, context: dict):
    """Process a user query with AI assistance."""
    # AI processing logic here
    return ai_response
```

### LLM Call Tracing

```python
@observability_service.trace_llm_call_decorator(
    model_name="gpt-5-nano",
    include_prompt=True,
    include_response=True
)
def generate_story(prompt: str, max_tokens: int = 1000):
    """Generate a story using LLM."""
    # LLM API call logic here
    return story_text
```

### Workflow Tracing

```python
@observability_service.trace_ai_workflow_decorator(
    workflow_name="campaign_narrative_generation",
    workflow_type="story_creation"
)
def generate_campaign_narrative(campaign_data: dict):
    """Generate narrative content for a campaign."""
    # Multi-step workflow logic here
    return narrative_result
```

### Custom Trace Tags

```python
# Add custom tags to traces
tags = observability_service.create_ai_trace_tags(
    operation_type="llm_call",
    model_name="gpt-5-nano",
    user_id="user123",
    campaign_id="campaign456"
)

with observability_service.trace_operation("custom_traced_operation", **tags) as trace_id:
    # Operation with custom tags
    pass
```

### Health Check Integration

```python
# Check observability health
health_status = observability_service.get_health_status()
if health_status["status"] != "healthy":
    logger.warning("Observability service unhealthy", **health_status)
```

## Development Guidelines

### When to Use Tracing

**Use tracing for:**
- AI operations and LLM calls
- Complex business logic workflows
- External API interactions
- Performance-critical operations
- Error-prone code sections

**Avoid tracing for:**
- Simple getter/setter methods
- Pure utility functions
- High-frequency operations (unless performance monitoring is needed)

### Best Practices

**Tracing Overhead:**
- Be mindful of tracing overhead in performance-critical paths
- Use conditional tracing for high-frequency operations
- Consider circuit breaker state before adding heavy tracing

**Tag Usage:**
- Use standardized AI-specific tags for consistency
- Include relevant context (user_id, campaign_id, operation_type)
- Avoid excessive custom tags that may impact performance

**Error Handling:**
- Always handle ImportError for LangSmith gracefully
- Test with and without LangSmith available
- Use fallback logging when tracing is unavailable

**Testing:**
- Mock LangSmith client in unit tests
- Test both success and failure scenarios
- Verify trace data structure and content
- Test circuit breaker behavior

## Campaign Transcript Logs

In addition to LangSmith tracing, the system maintains detailed campaign transcripts for debugging and analysis.

## Campaign Transcript Log Format

Each campaign maintains a transcript log at `data/saves/[campaign_id]/transcript.log`. This file records every in-character player message and AI response as a single line of JSON (JSONL format), with the following structure:

```json
{
  "timestamp": "2025-07-31T20:00:00.000000+00:00",
  "author": "PlayerName or AI",
  "message": "The message content goes here."
}
```

- **timestamp**: ISO 8601 UTC timestamp of the message.
- **author**: The player name or "AI" for system-generated responses.
- **message**: The full message content.

### Log Rotation and Size Limits

To prevent unbounded log growth, each `transcript.log` file is automatically rotated when it exceeds 10 MB:
- The current `transcript.log` is renamed to `transcript.log.1`.
- Up to 3 rotated logs are kept (`transcript.log.1`, `transcript.log.2`, `transcript.log.3`).
- The oldest log is deleted when a new rotation occurs and the limit is reached.
- A new `transcript.log` is then started for subsequent entries.

This ensures that recent campaign history is always available, while preventing excessive disk usage for very large or long-running campaigns.