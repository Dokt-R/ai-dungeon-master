"""
Observability service component for managing LangSmith integration.

This service provides centralized observability functionality including:
- LangSmith tracing initialization and configuration
- Environment variable validation
- Health check capabilities
- Error handling and fallback mechanisms
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Optional

from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ObservabilityConfig:
    """Configuration for observability settings."""

    api_key: str
    project: str = "ai-dungeon-master"
    endpoint: Optional[str] = None
    tracing_enabled: bool = True


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
    """

    _instance: Optional["ObservabilityService"] = None
    _is_initialized: bool = False

    def __new__(cls) -> "ObservabilityService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the observability service."""
        if not hasattr(self, "_config"):
            self._config: Optional[ObservabilityConfig] = None
            self._langsmith_client: Optional[Any] = None
            self._initialization_error: Optional[str] = None

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None
        cls._is_initialized = False

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
            if not api_key:
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

    def initialize(self) -> bool:
        """
        Initialize LangSmith tracing and observability.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._is_initialized:
            logger.debug("observability_already_initialized")
            return True

        try:
            # Load configuration
            self._config = self.load_config()

            # Initialize LangSmith client
            self._initialize_langsmith_client()

            self._is_initialized = True
            self._initialization_error = None

            logger.info(
                "observability_initialized",
                project=self._config.project,
                provider="langsmith",
            )

            return True

        except Exception as e:
            error_msg = f"Failed to initialize observability: {str(e)}"
            self._initialization_error = error_msg
            logger.error("observability_initialization_failed", error=str(e))
            return False

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
                "project": "unknown",
                "error": self._initialization_error or "not_initialized",
            }

        try:
            # Basic health check - verify client is accessible
            if self._langsmith_client is None:
                return {
                    "status": "unhealthy",
                    "provider": "langsmith",
                    "project": self._config.project if self._config else "unknown",
                    "error": "client_not_available",
                }

            # Additional health checks can be added here
            # For example, test API connectivity

            return {
                "status": "healthy",
                "provider": "langsmith",
                "project": self._config.project,
                "tracing_enabled": self._config.tracing_enabled,
            }

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
        Context manager for tracing operations.

        Args:
            operation_name: Name of the operation being traced
            **tags: Additional tags for the trace
        """
        if not self._is_initialized or not self._langsmith_client:
            logger.debug("tracing_disabled", operation=operation_name)
            yield
            return

        # This is a simplified tracing implementation
        # In a full implementation, you would use LangSmith's tracing decorators/contexts
        trace_id = f"{operation_name}_{os.urandom(8).hex()}"

        logger.info(
            "trace_started", operation=operation_name, trace_id=trace_id, **tags
        )

        try:
            yield trace_id
        except Exception as e:
            logger.error(
                "trace_error",
                operation=operation_name,
                trace_id=trace_id,
                error=str(e),
                **tags,
            )
            raise
        finally:
            logger.info(
                "trace_completed", operation=operation_name, trace_id=trace_id, **tags
            )

    def is_initialized(self) -> bool:
        """Check if the observability service is initialized."""
        return self._is_initialized

    def get_config(self) -> Optional[ObservabilityConfig]:
        """Get the current observability configuration."""
        return self._config


# Global service instance
observability_service = ObservabilityService()
