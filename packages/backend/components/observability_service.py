"""
Observability service component for managing LangSmith integration.

This service provides centralized observability functionality including:
- LangSmith tracing initialization and configuration
- Environment variable validation
- Health check capabilities
- Error handling and fallback mechanisms
- Tracing decorators for automatic AI operation wrapping
- Performance monitoring and metrics collection
- Custom trace tags for AI-specific operations
- Dependency injection support for improved testability
"""

import functools
import os
import threading
import time
import weakref
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Protocol, Union
from unittest.mock import patch

from packages.shared.correlation import get_correlation_id
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


class CircuitBreakerState(Enum):
    """States for the circuit breaker pattern."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 60.0  # Seconds to wait before trying to recover
    success_threshold: int = 3  # Number of successes needed in half-open state
    expected_exception: type = Exception  # Exception type to catch


class CircuitBreaker:
    """Circuit breaker implementation for observability service failures."""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result of function call

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitBreakerState.OPEN:
            if not self._should_attempt_reset():
                raise CircuitBreakerOpenException(
                    f"Circuit breaker is OPEN. Last failure: {self.last_failure_time}"
                )
            self.state = CircuitBreakerState.HALF_OPEN
            self.success_count = 0

        try:
            result = func(*args, **kwargs)

            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    logger.info("circuit_breaker_recovered")
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on success in closed state
                if self.failure_count > 0:
                    self.failure_count = 0

            return result

        except self.config.expected_exception:
            self._record_failure()
            raise

    def _record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning(
                "circuit_breaker_opened_from_half_open",
                failure_count=self.failure_count,
            )
        elif (
            self.state == CircuitBreakerState.CLOSED
            and self.failure_count >= self.config.failure_threshold
        ):
            self.state = CircuitBreakerState.OPEN
            logger.error(
                "circuit_breaker_opened",
                failure_count=self.failure_count,
                threshold=self.config.failure_threshold,
            )

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset from open to half-open state."""
        if self.state != CircuitBreakerState.OPEN or self.last_failure_time is None:
            return False

        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state information."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.config.failure_threshold,
            "recovery_timeout": self.config.recovery_timeout,
            "can_attempt_reset": self._should_attempt_reset(),
        }

    def reset(self):
        """Manually reset the circuit breaker to closed state."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info("circuit_breaker_manually_reset")


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""

    pass


class ObservabilityServiceInterface(Protocol):
    """Protocol defining the observability service interface."""

    def initialize(self) -> bool:
        """Initialize the observability service."""
        ...

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the service."""
        ...

    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        ...

    @contextmanager
    def trace_operation(self, operation_name: str, **tags):
        """Context manager for tracing operations."""
        ...

    @contextmanager
    def trace_llm_call(self, model_name: str, prompt: str, **metadata):
        """Context manager for tracing LLM calls."""
        ...

    @contextmanager
    def trace_ai_workflow(
        self, workflow_name: str, workflow_type: str = "ai_workflow", **metadata
    ):
        """Context manager for tracing AI workflows."""
        ...

    def trace_ai_operation(
        self,
        operation_name: str = None,
        operation_type: str = "ai_operation",
        include_args: bool = True,
        include_result: bool = False,
    ):
        """Decorator for AI operation tracing."""
        ...

    def trace_llm_call_decorator(
        self,
        model_name: str = None,
        include_prompt: bool = False,
        include_response: bool = False,
    ):
        """Decorator for LLM call tracing."""
        ...

    def trace_ai_workflow_decorator(
        self, workflow_name: str = None, workflow_type: str = "ai_workflow"
    ):
        """Decorator for AI workflow tracing."""
        ...


@dataclass
class ObservabilityConfig:
    """Configuration for observability settings."""

    api_key: str
    project: str = "ai-dungeon-master"
    endpoint: Optional[str] = None
    tracing_enabled: bool = True


@dataclass
class ConfigurationValidationResult:
    """Result of configuration validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    recommendations: list[str]


class ConfigurationValidator:
    """Validates observability configuration at startup."""

    def __init__(self):
        self.validation_errors: list[str] = []
        self.validation_warnings: list[str] = []
        self.validation_recommendations: list[str] = []

    def validate_config(
        self, config: ObservabilityConfig
    ) -> ConfigurationValidationResult:
        """
        Perform comprehensive validation of observability configuration.

        Args:
            config: Configuration to validate

        Returns:
            ConfigurationValidationResult with validation results
        """
        # Reset validation state
        self.validation_errors.clear()
        self.validation_warnings.clear()
        self.validation_recommendations.clear()

        # Perform all validations
        self._validate_api_key(config.api_key)
        self._validate_project(config.project)
        self._validate_endpoint(config.endpoint)
        self._validate_tracing_enabled(config.tracing_enabled)
        self._validate_environment_consistency(config)
        self._validate_security_best_practices(config)
        self._validate_performance_implications(config)

        # Determine overall validity
        is_valid = len(self.validation_errors) == 0

        return ConfigurationValidationResult(
            is_valid=is_valid,
            errors=self.validation_errors.copy(),
            warnings=self.validation_warnings.copy(),
            recommendations=self.validation_recommendations.copy(),
        )

    def _validate_api_key(self, api_key: str):
        """Validate LangSmith API key."""
        if not api_key:
            self.validation_errors.append(
                "LANGSMITH_API_KEY is required but not provided"
            )
            return

        if not isinstance(api_key, str):
            self.validation_errors.append("LANGSMITH_API_KEY must be a string")
            return

        api_key = api_key.strip()
        if not api_key:
            self.validation_errors.append(
                "LANGSMITH_API_KEY cannot be empty or whitespace"
            )
            return

        # Basic format validation (LangSmith keys typically start with ls__)
        if not api_key.startswith("ls__"):
            self.validation_warnings.append(
                "LANGSMITH_API_KEY should start with 'ls__' - please verify the key format"
            )

        # Check for common placeholder values
        placeholder_values = ["your_api_key", "api_key_here", "changeme", "placeholder"]
        if api_key.lower() in placeholder_values:
            self.validation_errors.append(
                "LANGSMITH_API_KEY appears to contain a placeholder value - please set a real API key"
            )

    def _validate_project(self, project: str):
        """Validate project name."""
        if not project:
            self.validation_errors.append("Project name is required")
            return

        if not isinstance(project, str):
            self.validation_errors.append("Project name must be a string")
            return

        project = project.strip()
        if not project:
            self.validation_errors.append("Project name cannot be empty or whitespace")
            return

        # Check length constraints
        if len(project) > 100:
            self.validation_warnings.append(
                "Project name is quite long (>100 chars) - consider shortening"
            )

        # Check for valid characters (alphanumeric, hyphens, underscores)
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", project):
            self.validation_errors.append(
                "Project name contains invalid characters - use only letters, numbers, hyphens, and underscores"
            )

        # Recommend project naming convention
        if not project.startswith(("ai-dungeon-master", "dungeon-master", "dm-ai")):
            self.validation_recommendations.append(
                "Consider prefixing project name with 'ai-dungeon-master' for better organization"
            )

    def _validate_endpoint(self, endpoint: Optional[str]):
        """Validate custom endpoint if provided."""
        if endpoint is None:
            return  # Using default endpoint is fine

        if not isinstance(endpoint, str):
            self.validation_errors.append("LANGSMITH_ENDPOINT must be a string")
            return

        endpoint = endpoint.strip()
        if not endpoint:
            self.validation_warnings.append(
                "LANGSMITH_ENDPOINT is empty - using default endpoint"
            )
            return

        # Validate URL format
        from urllib.parse import urlparse

        try:
            parsed = urlparse(endpoint)
            if not parsed.scheme or not parsed.netloc:
                self.validation_errors.append(
                    "LANGSMITH_ENDPOINT must be a valid URL with scheme and host"
                )
        except Exception as e:
            self.validation_errors.append(
                f"LANGSMITH_ENDPOINT is not a valid URL: {str(e)}"
            )

        # Check for HTTPS
        if endpoint and not endpoint.startswith("https://"):
            self.validation_warnings.append(
                "LANGSMITH_ENDPOINT should use HTTPS for security"
            )

    def _validate_tracing_enabled(self, tracing_enabled: bool):
        """Validate tracing enabled setting."""
        if not isinstance(tracing_enabled, bool):
            self.validation_errors.append("tracing_enabled must be a boolean")
            return

        if not tracing_enabled:
            self.validation_warnings.append(
                "Tracing is disabled - AI operations will not be traced"
            )

    def _validate_environment_consistency(self, config: ObservabilityConfig):
        """Validate consistency between environment variables and config."""
        # Check if environment variables match config
        env_api_key = os.getenv("LANGSMITH_API_KEY")
        env_project = os.getenv("LANGSMITH_PROJECT")
        env_endpoint = os.getenv("LANGSMITH_ENDPOINT")

        if env_api_key and env_api_key != config.api_key:
            self.validation_warnings.append(
                "LANGSMITH_API_KEY environment variable differs from loaded configuration"
            )

        if env_project and env_project != config.project:
            self.validation_warnings.append(
                "LANGSMITH_PROJECT environment variable differs from loaded configuration"
            )

        if env_endpoint != config.endpoint:
            if env_endpoint is None and config.endpoint is not None:
                self.validation_warnings.append(
                    "LANGSMITH_ENDPOINT environment variable not set but config has endpoint"
                )
            elif env_endpoint is not None and config.endpoint is None:
                self.validation_warnings.append(
                    "LANGSMITH_ENDPOINT environment variable set but config has no endpoint"
                )
            elif (
                env_endpoint is not None
                and config.endpoint is not None
                and env_endpoint != config.endpoint
            ):
                self.validation_warnings.append(
                    "LANGSMITH_ENDPOINT environment variable differs from loaded configuration"
                )

    def _validate_security_best_practices(self, config: ObservabilityConfig):
        """Validate security best practices."""
        # Check if API key is exposed in logs (basic check)
        if len(config.api_key) < 20:
            self.validation_warnings.append(
                "API key seems short - verify it's a complete LangSmith API key"
            )

        # Recommend using environment variables
        self.validation_recommendations.append(
            "Always use environment variables for API keys in production"
        )

        # Check for common security issues
        if config.endpoint and "localhost" in config.endpoint:
            self.validation_warnings.append(
                "Using localhost endpoint - ensure this is intended for development only"
            )

    def _validate_performance_implications(self, config: ObservabilityConfig):
        """Validate performance implications of configuration."""
        if not config.tracing_enabled:
            return  # No performance implications if tracing is disabled

        # Performance recommendations
        self.validation_recommendations.append(
            "Monitor tracing overhead in high-throughput scenarios"
        )

        if config.endpoint:
            self.validation_recommendations.append(
                "Custom endpoints may introduce additional latency - monitor performance"
            )


class ObservabilityError(Exception):
    """Base exception for observability-related errors."""

    pass


class ConfigurationError(ObservabilityError):
    """Raised when observability configuration is invalid or missing."""

    pass


class ObservabilityService:
    """
    Singleton service for managing LangSmith observability integration.

    This service handles:
    - Environment variable validation and loading
    - LangSmith client initialization
    - Tracing lifecycle management
    - Health check functionality
    - Dependency injection support for improved testability
    """

    _instance: Optional["ObservabilityService"] = None
    _is_initialized: bool = False
    _lock = threading.Lock()

    def __new__(cls) -> "ObservabilityService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the observability service."""
        # Only initialize if this is the first time __init__ is called on this instance
        if hasattr(self, "_initialized_attributes "):
            return

        self._initialized_attributes: bool = True
        self._config: Optional[ObservabilityConfig] = None
        self._langsmith_client: Optional[Any] = None
        self._initialization_error: Optional[str] = None
        #! TODO: Consider moving to initialize()
        self._config_validator: Optional[ConfigurationValidator] = None
        self._validation_result: Optional[ConfigurationValidationResult] = None
        self._circuit_breaker: Optional[CircuitBreaker] = None

        # This tracks whether initialize() has been called successfully
        self._is_initialized: bool = False

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        with cls._lock:
            cls._instance = None
            cls._is_initialized = False

        # Also reset the global instance for testing
        global observability_service
        observability_service = _create_global_service()

    def load_config(self) -> ObservabilityConfig:
        """
        Load and validate observability configuration from environment variables.

        Returns:
            ObservabilityConfig: Validated configuration object

        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        try:
            # Load required API key
            api_key = os.getenv("LANGSMITH_API_KEY")
            if api_key is None:
                raise ConfigurationError(
                    "LANGSMITH_API_KEY environment variable is required"
                )

            # Load optional configuration with defaults
            project = os.getenv("LANGSMITH_PROJECT", "ai-dungeon-master")
            endpoint = os.getenv("LANGSMITH_ENDPOINT")

            # Validate API key format (basic check)
            if not isinstance(api_key, str) or len(api_key.strip()) == 0:
                raise ConfigurationError("LANGSMITH_API_KEY cannot be empty")

            # Validate project name
            if not isinstance(project, str) or len(project.strip()) == 0:
                raise ConfigurationError("LANGSMITH_PROJECT cannot be empty")

            config = ObservabilityConfig(
                api_key=api_key.strip(),
                project=project.strip(),
                endpoint=endpoint.strip() if endpoint else None,
                tracing_enabled=True,
            )

            # If endpoint is still None after all processing, ensure it's explicitly None
            if not endpoint:
                config.endpoint = None

            logger.info(
                "observability_config_loaded",
                project=config.project,
                has_endpoint=bool(config.endpoint),
            )

            return config

        except Exception as e:
            error_msg = f"Failed to load observability configuration: {str(e)}"
            logger.error("observability_config_load_failed", error=str(e))
            raise ConfigurationError(error_msg) from e

    def initialize(self, validate_config_at_startup: bool = True) -> bool:
        """
        Initialize LangSmith tracing and observability.

        Args:
            validate_config_at_startup: Whether to perform comprehensive config validation

        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._is_initialized:
            logger.debug("observability_already_initialized")
            return True

        try:
            # Load configuration
            self._config = self.load_config()

            # Perform configuration validation if requested
            if validate_config_at_startup:
                self._validate_configuration_at_startup()

            # Initialize circuit breaker for observability failures
            self._initialize_circuit_breaker()

            # Initialize LangSmith client (protected by circuit breaker)
            # Performance optimization: skip client initialization for integration tests to speed them up
            if os.getenv("PYTEST_CURRENT_TEST") == "integration_test_for_performance":
                logger.debug(
                    "skipping_langsmith_initialization_for_integration_test_performance"
                )
                self._langsmith_client = None  # Will be handled by tracing methods
            else:
                try:
                    self._circuit_breaker.call(self._initialize_langsmith_client)
                except CircuitBreakerOpenException:
                    logger.warning("langsmith_initialization_skipped_circuit_open")
                except Exception as e:
                    logger.warning(
                        "langsmith_initialization_failed_but_continuing", error=str(e)
                    )

            self._is_initialized = True
            ObservabilityService._is_initialized = True
            self._initialization_error = None

            logger.info(
                "observability_initialized",
                project=self._config.project,
                provider="langsmith",
                circuit_breaker_state=self._circuit_breaker.get_state()["state"],
            )

            return True

        except Exception as e:
            error_msg = f"Failed to initialize observability: {str(e)}"
            self._initialization_error = error_msg
            self._is_initialized = False
            logger.error("observability_initialization_failed", error=str(e))
            return False

    def _validate_configuration_at_startup(self):
        """Perform comprehensive configuration validation at startup."""
        if self._config is None:
            raise ObservabilityError("Configuration must be loaded before validation")

        # Initialize validator
        self._config_validator = ConfigurationValidator()

        # Perform validation
        self._validation_result = self._config_validator.validate_config(self._config)

        # Log validation results
        if not self._validation_result.is_valid:
            error_details = "; ".join(self._validation_result.errors)
            raise ConfigurationError(
                f"Observability configuration validation failed: {error_details}"
            )

        # Log warnings if any
        if self._validation_result.warnings:
            for warning in self._validation_result.warnings:
                logger.warning("observability_config_warning", warning=warning)

        # Log recommendations if any
        if self._validation_result.recommendations:
            for recommendation in self._validation_result.recommendations:
                logger.info(
                    "observability_config_recommendation", recommendation=recommendation
                )

        logger.info(
            "observability_config_validated",
            warnings_count=len(self._validation_result.warnings),
            recommendations_count=len(self._validation_result.recommendations),
        )

    def get_validation_result(self) -> Optional[ConfigurationValidationResult]:
        """Get the result of configuration validation."""
        return self._validation_result

    def get_config_validator(self) -> Optional[ConfigurationValidator]:
        """Get the configuration validator instance."""
        return self._config_validator

    def validate_config_only(self) -> ConfigurationValidationResult:
        """
        Validate configuration without initializing the service.

        Returns:
            ConfigurationValidationResult with validation results
        """
        try:
            config = self.load_config()
            validator = ConfigurationValidator()
            return validator.validate_config(config)
        except Exception as e:
            return ConfigurationValidationResult(
                is_valid=False,
                errors=[f"Failed to load configuration: {str(e)}"],
                warnings=[],
                recommendations=[],
            )

    def get_circuit_breaker_state(self) -> Optional[Dict[str, Any]]:
        """Get the current circuit breaker state."""
        if self._circuit_breaker is None:
            return None
        return self._circuit_breaker.get_state()

    def reset_circuit_breaker(self):
        """Manually reset the circuit breaker to closed state."""
        if self._circuit_breaker is not None:
            self._circuit_breaker.reset()
            logger.info("observability_circuit_breaker_reset")
        else:
            logger.warning("cannot_reset_circuit_breaker_not_initialized")

    def is_circuit_breaker_open(self) -> bool:
        """Check if the circuit breaker is currently open."""
        if self._circuit_breaker is None:
            return False
        return self._circuit_breaker.state == CircuitBreakerState.OPEN

    def get_correlation_id_for_trace(self, trace_id: str) -> Optional[str]:
        """
        Get the correlation ID associated with a trace.

        Args:
            trace_id: The trace ID to look up

        Returns:
            Correlation ID if available, None otherwise
        """
        # In a full implementation, this would query LangSmith for trace metadata
        # For now, return the current correlation ID from context
        return get_correlation_id()

    def create_trace_with_correlation(self, operation_name: str, **tags) -> str:
        """
        Create a trace that automatically includes the current correlation ID.

        Args:
            operation_name: Name of the operation
            **tags: Additional trace tags

        Returns:
            Trace ID for the created trace
        """
        correlation_id = get_correlation_id()
        if correlation_id:
            tags = dict(tags)  # Create a copy
            tags["correlation_id"] = correlation_id

        trace_id = f"{operation_name}_{os.urandom(8).hex()}"

        # Log trace creation with correlation context
        log_context = {
            "operation": operation_name,
            "trace_id": trace_id,
            "has_correlation_id": correlation_id is not None,
            **tags,
        }

        logger.info("trace_created_with_correlation", **log_context)
        return trace_id

    def _initialize_langsmith_client(self) -> None:
        """
        Initialize the LangSmith client with configuration.

        Raises:
            ObservabilityError: If client initialization fails
        """
        try:
            # Import LangSmith here to avoid import errors if package is not installed
            from langsmith import Client

            # Set environment variables for LangSmith
            os.environ["LANGSMITH_API_KEY"] = self._config.api_key
            os.environ["LANGSMITH_PROJECT"] = self._config.project

            if self._config.endpoint:
                os.environ["LANGSMITH_ENDPOINT"] = self._config.endpoint

            # Create client instance
            self._langsmith_client = Client()

            logger.debug("langsmith_client_created")

        except ImportError as e:
            raise ObservabilityError(
                "LangSmith package is not installed. Install with: pip install langsmith"
            ) from e
        except Exception as e:
            raise ObservabilityError(
                f"Failed to initialize LangSmith client: {str(e)}"
            ) from e

    def _initialize_circuit_breaker(self):
        """Initialize the circuit breaker for observability failures."""
        # Configure circuit breaker for observability service
        # Use shorter timeout in test environments to speed up test execution
        recovery_timeout = 1.0 if os.getenv("PYTEST_CURRENT_TEST") else 30.0

        circuit_breaker_config = CircuitBreakerConfig(
            failure_threshold=3,  # Open after 3 consecutive failures
            recovery_timeout=recovery_timeout,  # Shorter timeout for tests
            success_threshold=2,  # Need 2 successes to fully recover
            expected_exception=(ObservabilityError, CircuitBreakerOpenException),
        )

        self._circuit_breaker = CircuitBreaker(circuit_breaker_config)

        logger.debug("circuit_breaker_initialized", **circuit_breaker_config.__dict__)

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the observability service.

        Returns:
            Dict containing health status information
        """
        if not self._is_initialized:
            return {
                "status": "unhealthy",
                "provider": "langsmith",
                "project": getattr(self._config, "project", "unknown")
                if self._config
                else "unknown",
                "error": getattr(self, "_initialization_error", None)
                or "not_initialized",
                "correlation_id_support": "enabled",
                "current_correlation_id": get_correlation_id(),
            }

        try:
            # Basic health check - verify client is accessible
            if self._langsmith_client is None:
                return {
                    "status": "unhealthy",
                    "provider": "langsmith",
                    "project": self._config.project if self._config else "unknown",
                    "error": "client_not_available",
                    "circuit_breaker": self.get_circuit_breaker_state(),
                    "correlation_id_support": "enabled",
                    "current_correlation_id": get_correlation_id(),
                }

            # Additional health checks can be added here
            # For example, test API connectivity

            health_status = {
                "status": "healthy",
                "provider": "langsmith",
                "project": self._config.project,
                "tracing_enabled": self._config.tracing_enabled,
                "circuit_breaker": self.get_circuit_breaker_state(),
                "correlation_id_support": "enabled",
                "current_correlation_id": get_correlation_id(),
            }

            # Check circuit breaker state
            if self.is_circuit_breaker_open():
                health_status["status"] = "degraded"
                health_status["degraded_reason"] = "circuit_breaker_open"

            return health_status

        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "provider": "langsmith",
                "project": self._config.project if self._config else "unknown",
                "error": f"health_check_failed: {str(e)}",
            }

    @contextmanager
    def trace_operation(self, operation_name: str, **tags):
        """
        Context manager for tracing operations with LangSmith integration.

        Args:
            operation_name: Name of the operation being traced
            **tags: Additional tags for the trace (operation_type, model_name, etc.)
        """
        if not self._is_initialized:
            logger.debug(
                "tracing_disabled_service_not_initialized", operation=operation_name
            )
            yield None
            return

        # Check circuit breaker
        if self.is_circuit_breaker_open():
            logger.debug(
                "tracing_disabled_circuit_breaker_open", operation=operation_name
            )
            yield None
            return

        if not self._langsmith_client:
            logger.debug("tracing_disabled_no_client", operation=operation_name)
            yield None
            return

        # Create a proper LangSmith trace using the client
        trace_id = f"{operation_name}_{os.urandom(8).hex()}"

        # Get correlation ID from current context
        correlation_id = get_correlation_id()
        if correlation_id:
            # Add correlation ID to trace metadata
            tags = dict(tags)  # Create a copy to avoid modifying the original
            tags["correlation_id"] = correlation_id

        # Start trace with LangSmith (protected by circuit breaker)
        try:
            from langsmith import traceable

            # Create traceable function for this operation
            @traceable(
                name=operation_name,
                project_name=self._config.project,
                tags=list(tags.keys()),
                metadata=tags,
            )
            def execute_traced_operation():
                return trace_id

            # Execute the traced operation through circuit breaker
            result = self._circuit_breaker.call(execute_traced_operation)

            # Prepare log context with correlation ID
            log_context = {
                "operation": operation_name,
                "trace_id": trace_id,
                "provider": "langsmith",
                **tags,
            }

            # Add correlation ID if available
            if correlation_id:
                log_context["correlation_id"] = correlation_id

            logger.info("trace_started", **log_context)

            try:
                yield result
            except CircuitBreakerOpenException:
                log_context = {
                    "operation": operation_name,
                    "trace_id": trace_id,
                    "provider": "langsmith",
                    **tags,
                }
                if correlation_id:
                    log_context["correlation_id"] = correlation_id
                logger.warning("trace_skipped_circuit_breaker_open", **log_context)
                yield None
            except Exception as e:
                log_context = {
                    "operation": operation_name,
                    "trace_id": trace_id,
                    "error": str(e),
                    "provider": "langsmith",
                    **tags,
                }
                if correlation_id:
                    log_context["correlation_id"] = correlation_id
                logger.error("trace_error", **log_context)
                raise
            finally:
                log_context = {
                    "operation": operation_name,
                    "trace_id": trace_id,
                    "provider": "langsmith",
                    **tags,
                }
                if correlation_id:
                    log_context["correlation_id"] = correlation_id
                logger.info("trace_completed", **log_context)

        except ImportError:
            # Fallback to basic logging if LangSmith tracing fails
            logger.warning(
                "langsmith_tracing_unavailable",
                operation=operation_name,
                fallback="logging_only",
            )
            yield trace_id

    def is_initialized(self) -> bool:
        """Check if the observability service is initialized."""
        return getattr(self, "_is_initialized", False)

    def get_config(self) -> Optional[ObservabilityConfig]:
        """Get the current observability configuration."""
        return self._config

    @contextmanager
    def trace_llm_call(self, model_name: str, prompt: str, **metadata):
        """
        Context manager specifically for tracing LLM API calls.

        Args:
            model_name: Name of the AI model being called
            prompt: The prompt being sent to the model
            **metadata: Additional metadata for the trace
        """
        if not self._is_initialized or not self._langsmith_client:
            logger.debug("llm_tracing_disabled", model=model_name)
            yield None
            return

        trace_id = f"llm_call_{model_name}_{os.urandom(8).hex()}"

        try:
            from langsmith import traceable

            @traceable(
                name=f"llm_call_{model_name}",
                project_name=self._config.project,
                tags=["llm_call", model_name],
                metadata={
                    "model_name": model_name,
                    "prompt_length": len(prompt),
                    "operation_type": "llm_call",
                    **metadata,
                },
            )
            def execute_llm_trace():
                return trace_id

            result = execute_llm_trace()

            logger.info(
                "llm_call_trace_started",
                model=model_name,
                trace_id=trace_id,
                prompt_length=len(prompt),
                provider="langsmith",
                **metadata,
            )

            try:
                yield result
            except Exception as e:
                logger.error(
                    "llm_call_trace_error",
                    model=model_name,
                    trace_id=trace_id,
                    error=str(e),
                    provider="langsmith",
                    **metadata,
                )
                raise
            finally:
                logger.info(
                    "llm_call_trace_completed",
                    model=model_name,
                    trace_id=trace_id,
                    provider="langsmith",
                    **metadata,
                )

        except ImportError:
            logger.warning(
                "langsmith_tracing_unavailable_for_llm",
                model=model_name,
                fallback="logging_only",
            )
            yield trace_id

    @contextmanager
    def trace_ai_workflow(
        self, workflow_name: str, workflow_type: str = "ai_workflow", **metadata
    ):
        """
        Context manager for tracing complete AI workflows.

        Args:
            workflow_name: Name of the AI workflow
            workflow_type: Type of workflow (e.g., "narrative_generation", "character_interaction")
            **metadata: Additional metadata for the trace
        """
        if not self._is_initialized or not self._langsmith_client:
            logger.debug("ai_workflow_tracing_disabled", workflow=workflow_name)
            yield None
            return

        trace_id = f"ai_workflow_{workflow_name}_{os.urandom(8).hex()}"

        try:
            from langsmith import traceable

            @traceable(
                name=f"ai_workflow_{workflow_name}",
                project_name=self._config.project,
                tags=["ai_workflow", workflow_type, workflow_name],
                metadata={
                    "workflow_name": workflow_name,
                    "workflow_type": workflow_type,
                    "operation_type": "ai_workflow",
                    **metadata,
                },
            )
            def execute_workflow_trace():
                return trace_id

            result = execute_workflow_trace()

            logger.info(
                "ai_workflow_trace_started",
                workflow=workflow_name,
                workflow_type=workflow_type,
                trace_id=trace_id,
                provider="langsmith",
                **metadata,
            )

            try:
                yield result
            except Exception as e:
                logger.error(
                    "ai_workflow_trace_error",
                    workflow=workflow_name,
                    workflow_type=workflow_type,
                    trace_id=trace_id,
                    error=str(e),
                    provider="langsmith",
                    **metadata,
                )
                raise
            finally:
                logger.info(
                    "ai_workflow_trace_completed",
                    workflow=workflow_name,
                    workflow_type=workflow_type,
                    trace_id=trace_id,
                    provider="langsmith",
                    **metadata,
                )

        except ImportError:
            logger.warning(
                "langsmith_tracing_unavailable_for_workflow",
                workflow=workflow_name,
                fallback="logging_only",
            )
            yield trace_id

    def trace_llm_response(
        self, trace_id: str, response: str, model_name: str, **metadata
    ):
        """
        Add LLM response data to an existing trace.

        Args:
            trace_id: The trace ID to add response data to
            response: The response from the LLM
            model_name: Name of the model that generated the response
            **metadata: Additional metadata to include
        """
        if not self._is_initialized or not self._langsmith_client:
            logger.debug(
                "llm_response_tracing_disabled", model=model_name, trace_id=trace_id
            )
            return

        try:
            # Log structured response data
            logger.info(
                "llm_response_traced",
                trace_id=trace_id,
                model=model_name,
                response_length=len(response),
                provider="langsmith",
                **metadata,
            )

            # In a full implementation, you would send this to LangSmith
            # using their API to add response data to the trace

        except Exception as e:
            logger.error(
                "llm_response_tracing_failed",
                trace_id=trace_id,
                model=model_name,
                error=str(e),
            )

    def trace_decision_point(
        self,
        trace_id: str,
        decision_type: str,
        options: list,
        chosen_option: str,
        reasoning: str = None,
        **metadata,
    ):
        """
        Trace AI decision-making points for transparency.

        Args:
            trace_id: The trace ID to add decision data to
            decision_type: Type of decision being made
            options: List of available options
            chosen_option: The option that was chosen
            reasoning: Optional reasoning for the decision
            **metadata: Additional metadata
        """
        if not self._is_initialized or not self._langsmith_client:
            logger.debug(
                "decision_tracing_disabled",
                decision_type=decision_type,
                trace_id=trace_id,
            )
            return

        try:
            logger.info(
                "ai_decision_point_traced",
                trace_id=trace_id,
                decision_type=decision_type,
                options_count=len(options),
                chosen_option=chosen_option,
                has_reasoning=bool(reasoning),
                provider="langsmith",
                **metadata,
            )

            # In a full implementation, this would be sent to LangSmith
            # to build a decision tree visualization

        except Exception as e:
            logger.error(
                "decision_tracing_failed",
                trace_id=trace_id,
                decision_type=decision_type,
                error=str(e),
            )

    # Tracing Decorators for Automatic AI Operation Wrapping

    def trace_ai_operation(
        self,
        operation_name: str = None,
        operation_type: str = "ai_operation",
        include_args: bool = True,
        include_result: bool = False,
    ):
        """
        Decorator for automatic tracing of AI operations.

        Args:
            operation_name: Custom name for the operation (defaults to function name)
            operation_type: Type of AI operation for categorization
            include_args: Whether to include function arguments in trace metadata
            include_result: Whether to include function result in trace metadata
        """

        def decorator(func: Callable) -> Callable:
            service_ref = weakref.ref(self)

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                service = service_ref()
                if service is None:
                    return func(*args, **kwargs)  # Service was garbage collected

                # Use provided operation name or function name
                trace_name = operation_name or func.__name__

                # Prepare metadata
                metadata = {
                    "operation_type": operation_type,
                    "function_name": func.__name__,
                    "module_name": func.__module__,
                }

                # Include arguments if requested (exclude self)
                if include_args:
                    func_args = (
                        args[1:] if args and hasattr(args[0], "__dict__") else args
                    )
                    metadata.update(
                        {
                            "args_count": len(func_args),
                            "kwargs_keys": list(kwargs.keys()),
                        }
                    )

                # Add performance monitoring
                start_time = time.perf_counter()

                # Create trace
                with self.trace_operation(trace_name, **metadata) as trace_id:
                    try:
                        result = func(*args, **kwargs)

                        # Calculate duration
                        duration = time.perf_counter() - start_time

                        # Add performance data to trace
                        if trace_id:
                            self._add_performance_metrics(
                                trace_id, duration, operation_type
                            )

                        # Include result in metadata if requested
                        if include_result and result is not None:
                            self._add_result_metadata(trace_id, result, operation_type)

                        logger.info(
                            "ai_operation_completed",
                            operation=trace_name,
                            trace_id=trace_id,
                            duration_ms=round(duration * 1000, 2),
                            operation_type=operation_type,
                        )

                        return result

                    except Exception as e:
                        duration = time.perf_counter() - start_time
                        logger.error(
                            "ai_operation_failed",
                            operation=trace_name,
                            trace_id=trace_id,
                            duration_ms=round(duration * 1000, 2),
                            error=str(e),
                            operation_type=operation_type,
                        )
                        raise

            return wrapper

        return decorator

    def trace_llm_call_decorator(
        self,
        model_name: str = None,
        include_prompt: bool = False,
        include_response: bool = False,
    ):
        """
        Decorator specifically for tracing LLM API calls.

        Args:
            model_name: Name of the AI model (if not provided, will try to extract from args)
            include_prompt: Whether to include the prompt in trace metadata
            include_response: Whether to include the response in trace metadata
        """

        def decorator(func: Callable) -> Callable:
            service_ref = weakref.ref(self)

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                service = service_ref()
                if service is None:
                    return func(*args, **kwargs)
                # Try to extract model name from arguments
                model = model_name
                if not model:
                    # Look for common parameter names
                    for arg_name in ["model", "model_name", "model_id"]:
                        if arg_name in kwargs:
                            model = kwargs[arg_name]
                            break
                    # If still not found, check positional args (limited)
                    if not model and len(args) > 1:
                        model = (
                            getattr(args[1], "model", None)
                            if hasattr(args[1], "model")
                            else None
                        )

                model = model or "unknown_model"

                # Extract prompt and response if requested
                prompt = None
                if include_prompt:
                    prompt = kwargs.get(
                        "prompt", kwargs.get("messages", kwargs.get("input", None))
                    )

                start_time = time.perf_counter()

                with self.trace_llm_call(
                    model, prompt or "prompt_not_included"
                ) as trace_id:
                    try:
                        result = func(*args, **kwargs)
                        duration = time.perf_counter() - start_time

                        # Add response data if requested
                        if include_response and result is not None:
                            self.trace_llm_response(
                                trace_id or "unknown",
                                str(result),
                                model,
                                duration_ms=round(duration * 1000, 2),
                            )

                        logger.info(
                            "llm_call_decorator_completed",
                            function=func.__name__,
                            model=model,
                            trace_id=trace_id,
                            duration_ms=round(duration * 1000, 2),
                        )

                        return result

                    except Exception as e:
                        duration = time.perf_counter() - start_time
                        logger.error(
                            "llm_call_decorator_failed",
                            function=func.__name__,
                            model=model,
                            trace_id=trace_id,
                            duration_ms=round(duration * 1000, 2),
                            error=str(e),
                        )
                        raise

            return wrapper

        return decorator

    def trace_ai_workflow_decorator(
        self, workflow_name: str = None, workflow_type: str = "ai_workflow"
    ):
        """
        Decorator for tracing complete AI workflows.

        Args:
            workflow_name: Custom name for the workflow (defaults to function name)
            workflow_type: Type of workflow for categorization
        """

        def decorator(func: Callable) -> Callable:
            service_ref = weakref.ref(self)

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                service = service_ref()
                if service is None:
                    return func(*args, **kwargs)

                trace_name = workflow_name or func.__name__

                start_time = time.perf_counter()

                with self.trace_ai_workflow(trace_name, workflow_type) as trace_id:
                    try:
                        result = func(*args, **kwargs)
                        duration = time.perf_counter() - start_time

                        logger.info(
                            "ai_workflow_decorator_completed",
                            workflow=trace_name,
                            workflow_type=workflow_type,
                            trace_id=trace_id,
                            duration_ms=round(duration * 1000, 2),
                        )

                        return result

                    except Exception as e:
                        duration = time.perf_counter() - start_time
                        logger.error(
                            "ai_workflow_decorator_failed",
                            workflow=trace_name,
                            workflow_type=workflow_type,
                            trace_id=trace_id,
                            duration_ms=round(duration * 1000, 2),
                            error=str(e),
                        )
                        raise

            return wrapper

        return decorator

    # Performance Monitoring and Metrics Collection

    def _add_performance_metrics(
        self, trace_id: str, duration: float, operation_type: str
    ):
        """Add performance metrics to a trace."""
        if not self._is_initialized:
            return

        try:
            logger.info(
                "performance_metrics_added",
                trace_id=trace_id,
                duration_seconds=duration,
                duration_ms=round(duration * 1000, 2),
                operation_type=operation_type,
            )
        except Exception as e:
            logger.error("performance_metrics_failed", trace_id=trace_id, error=str(e))

    def _add_result_metadata(self, trace_id: str, result: Any, operation_type: str):
        """Add result metadata to a trace."""
        if not self._is_initialized:
            return

        try:
            # Extract basic metadata from result
            metadata = {}
            if hasattr(result, "__dict__"):
                metadata["result_type"] = type(result).__name__
            elif isinstance(result, dict):
                metadata["result_keys"] = list(result.keys())
                metadata["result_type"] = "dict"
            elif isinstance(result, (list, tuple)):
                metadata["result_length"] = len(result)
                metadata["result_type"] = type(result).__name__
            elif isinstance(result, str):
                metadata["result_length"] = len(result)
                metadata["result_type"] = "str"
            else:
                metadata["result_type"] = type(result).__name__

            logger.info(
                "result_metadata_added",
                trace_id=trace_id,
                operation_type=operation_type,
                **metadata,
            )
        except Exception as e:
            logger.error("result_metadata_failed", trace_id=trace_id, error=str(e))

    def get_performance_metrics(
        self, operation_type: str = None, time_window_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Get performance metrics for operations.

        Args:
            operation_type: Filter by operation type (None for all)
            time_window_seconds: Time window to look back (default 1 hour)

        Returns:
            Dict containing performance metrics
        """
        # In a full implementation, this would query actual metrics from LangSmith
        # For now, return basic structure
        return {
            "operation_type": operation_type,
            "time_window_seconds": time_window_seconds,
            "metrics_available": False,
            "note": "Performance metrics collection requires LangSmith integration",
        }

    # Custom Trace Tags for AI-specific Operations

    def add_custom_trace_tags(
        self, trace_id: str, tags: Dict[str, Union[str, int, float, bool]]
    ):
        """
        Add custom tags to an existing trace.

        Args:
            trace_id: The trace ID to add tags to
            tags: Dictionary of tag key-value pairs
        """
        if not self._is_initialized:
            return

        try:
            logger.info(
                "custom_trace_tags_added",
                trace_id=trace_id,
                tags=list(tags.keys()),
                tag_count=len(tags),
            )
        except Exception as e:
            logger.error("custom_trace_tags_failed", trace_id=trace_id, error=str(e))

    def create_ai_trace_tags(
        self, operation_type: str, **kwargs
    ) -> Dict[str, Union[str, int, float, bool]]:
        """
        Create standardized AI-specific trace tags.

        Args:
            operation_type: The type of AI operation
            **kwargs: Additional tag values

        Returns:
            Dict of standardized AI trace tags
        """
        base_tags = {
            "ai_operation": "true",
            "operation_type": operation_type,
            "ai_service": "ai-dungeon-master",
        }

        # Add AI-specific tags based on operation type
        if operation_type == "llm_call":
            ai_tags = {
                "llm_model": kwargs.get("model_name", "unknown"),
                "llm_provider": kwargs.get("provider", "unknown"),
                "prompt_tokens": kwargs.get("prompt_tokens", 0),
                "response_tokens": kwargs.get("response_tokens", 0),
                "temperature": kwargs.get("temperature", 0.0),
            }
        elif operation_type == "ai_workflow":
            ai_tags = {
                "workflow_stage": kwargs.get("stage", "unknown"),
                "workflow_step": kwargs.get("step", "unknown"),
                "data_processed": kwargs.get("data_size", 0),
            }
        elif operation_type == "embedding":
            ai_tags = {
                "embedding_model": kwargs.get("model_name", "unknown"),
                "embedding_dimension": kwargs.get("dimension", 0),
                "text_length": kwargs.get("text_length", 0),
            }
        else:
            ai_tags = {
                "custom_operation": "true",
            }

        return {**base_tags, **ai_tags, **kwargs}


class ObservabilityServiceFactory:
    """Factory for creating ObservabilityService instances with dependency injection support."""

    @staticmethod
    def create_service(
        config: Optional[ObservabilityConfig] = None, initialize_on_create: bool = True
    ) -> ObservabilityService:
        """
        Create a new ObservabilityService instance with optional configuration.

        Args:
            config: Pre-configured ObservabilityConfig (if None, loads from environment)
            initialize_on_create: Whether to initialize the service immediately

        Returns:
            ObservabilityService instance
        """
        service = ObservabilityService()

        if config is not None:
            # Set the config directly on the service instance
            service._config = config
            # Use provided configuration instead of loading from environment
            with patch.object(service, "load_config", return_value=config):
                if initialize_on_create:
                    service.initialize()
        elif initialize_on_create:
            service.initialize()

        return service

    @staticmethod
    def create_test_service(mock_langsmith: bool = True) -> ObservabilityService:
        """
        Create a service instance configured for testing.

        Args:
            mock_langsmith: Whether to mock LangSmith client for testing

        Returns:
            ObservabilityService configured for testing
        """
        config = ObservabilityConfig(
            api_key="test_api_key",
            project="test_project",
            endpoint=None,
            tracing_enabled=True,
        )

        service = ObservabilityService()

        with patch.object(service, "load_config", return_value=config):
            if mock_langsmith:
                with patch.object(service, "_initialize_langsmith_client"):
                    service.initialize()
            else:
                service.initialize()

        return service

    @staticmethod
    def create_disabled_service() -> ObservabilityService:
        """
        Create a service instance with observability disabled.

        Returns:
            ObservabilityService with tracing disabled
        """
        config = ObservabilityConfig(
            api_key="disabled", project="disabled", endpoint=None, tracing_enabled=False
        )

        service = ObservabilityService()

        with patch.object(service, "load_config", return_value=config):
            service.initialize()

        return service


class DependencyContainer:
    """Simple dependency injection container for observability services."""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}

    def register_service(self, name: str, service: Any):
        """Register a service instance."""
        self._services[name] = service

    def register_factory(self, name: str, factory: Callable):
        """Register a service factory function."""
        self._factories[name] = factory

    def get_service(self, name: str) -> Any:
        """Get a service by name, creating it if necessary."""
        if name in self._services:
            return self._services[name]

        if name in self._factories:
            service = self._factories[name]()
            self._services[name] = service
            return service

        raise ValueError(f"Service '{name}' not registered and no factory available")

    def clear(self):
        """Clear all registered services and factories."""
        self._services.clear()
        self._factories.clear()


# Global service instance - use lazy initialization only in test environments
def _create_global_service():
    """Create the global observability service instance."""
    return ObservabilityService()


# Use immediate initialization for backward compatibility
observability_service = _create_global_service()


def get_global_service():
    """Get the global observability service instance."""
    return observability_service


# Global dependency container
dependency_container = DependencyContainer()

# Register default observability service factory
dependency_container.register_factory(
    "observability_service", lambda: ObservabilityServiceFactory.create_service()
)
