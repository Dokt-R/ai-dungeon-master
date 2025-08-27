"""
AI Client Component for provider-agnostic AI service integration.

This module provides a unified interface for multiple AI providers (OpenAI, Anthropic, etc.)
with built-in error handling, retry logic, connection pooling, and observability integration.

Key Features:
- Provider-agnostic interface with swappable implementations
- Comprehensive error handling and retry mechanisms
- Circuit breaker pattern for resilience
- Integration with LangSmith tracing
- Secure credential management
- Connection pooling and session management
"""

import asyncio
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

# Import OpenAI with fallback for testing
try:
    from openai import AsyncOpenAI
except ImportError:
    # Handle case where openai package is not installed
    AsyncOpenAI = None
    logger.warning(
        "openai_package_not_available",
        message="OpenAI package is not installed. OpenAI provider will not be available.",
    )


class AIProvider(Enum):
    """Supported AI providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    # Add more providers as needed


class AIClientError(Exception):
    """Base exception for AI client errors."""

    pass


class ConfigurationError(AIClientError):
    """Raised when AI client configuration is invalid or missing."""

    pass


class ConnectionError(AIClientError):
    """Raised when connection to AI provider fails."""

    pass


class RateLimitError(AIClientError):
    """Raised when rate limit is exceeded."""

    pass


class AuthenticationError(AIClientError):
    """Raised when authentication fails."""

    pass


@dataclass
class AIClientConfig:
    """
    Configuration for AI client settings.

    All sensitive information is loaded from environment variables to ensure security.
    """

    provider: AIProvider = AIProvider.OPENAI
    api_key: str = ""
    base_url: Optional[str] = None
    model: str = "gpt-5-nano-2025-08-07"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    max_retry_delay: float = 60.0
    backoff_multiplier: float = 2.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 300.0  # 5 minutes
    connection_pool_size: int = 10

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.api_key:
            raise ConfigurationError("API key is required")

        if self.timeout <= 0:
            raise ConfigurationError("Timeout must be positive")

        if self.max_retries < 0:
            raise ConfigurationError("Max retries cannot be negative")

        if self.circuit_breaker_threshold < 1:
            raise ConfigurationError("Circuit breaker threshold must be at least 1")

    @classmethod
    def from_env(cls) -> "AIClientConfig":
        """
        Create configuration from environment variables.

        Returns:
            AIClientConfig: Validated configuration object

        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        try:
            # Load required API key
            api_key = os.getenv("AI_PROVIDER_API_KEY")
            if not api_key:
                raise ConfigurationError(
                    "AI_PROVIDER_API_KEY environment variable is required"
                )

            # Load optional configuration with defaults
            provider_str = os.getenv("AI_PROVIDER", "openai")
            try:
                provider = AIProvider(provider_str.lower())
            except ValueError:
                raise ConfigurationError(f"Unsupported AI provider: {provider_str}")

            config = cls(
                provider=provider,
                api_key=api_key.strip(),
                base_url=os.getenv("AI_PROVIDER_BASE_URL"),
                model=os.getenv("AI_PROVIDER_MODEL", "gpt-4"),
                timeout=float(os.getenv("AI_PROVIDER_TIMEOUT", "30.0")),
                max_retries=int(os.getenv("AI_PROVIDER_MAX_RETRIES", "3")),
                retry_delay=float(os.getenv("AI_PROVIDER_RETRY_DELAY", "1.0")),
                max_retry_delay=float(os.getenv("AI_PROVIDER_MAX_RETRY_DELAY", "60.0")),
                backoff_multiplier=float(
                    os.getenv("AI_PROVIDER_BACKOFF_MULTIPLIER", "2.0")
                ),
                circuit_breaker_threshold=int(
                    os.getenv("AI_CIRCUIT_BREAKER_THRESHOLD", "5")
                ),
                circuit_breaker_timeout=float(
                    os.getenv("AI_CIRCUIT_BREAKER_TIMEOUT", "300.0")
                ),
                connection_pool_size=int(os.getenv("AI_CONNECTION_POOL_SIZE", "10")),
            )

            logger.info(
                "ai_client_config_loaded",
                provider=config.provider.value,
                model=config.model,
                has_base_url=bool(config.base_url),
                timeout=config.timeout,
                max_retries=config.max_retries,
            )

            return config

        except Exception as e:
            error_msg = f"Failed to load AI client configuration: {str(e)}"
            logger.error("ai_client_config_load_failed", error=str(e))
            raise ConfigurationError(error_msg) from e


@dataclass
class CircuitBreakerState:
    """State tracking for circuit breaker pattern."""

    failure_count: int = 0
    last_failure_time: float = 0.0
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN


class AICircuitBreaker:
    """
    Circuit breaker implementation for AI provider resilience.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is open, requests fail immediately
    - HALF_OPEN: Testing if service has recovered
    """

    def __init__(self, threshold: int = 5, timeout: float = 300.0):
        self.threshold = threshold
        self.timeout = timeout
        self.state = CircuitBreakerState()

    def can_execute(self) -> bool:
        """Check if request can be executed based on circuit breaker state."""
        current_time = time.time()

        if self.state.state == "CLOSED":
            return True
        elif self.state.state == "OPEN":
            if current_time - self.state.last_failure_time >= self.timeout:
                # Transition to half-open
                self.state.state = "HALF_OPEN"
                logger.info("circuit_breaker_half_open")
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self) -> None:
        """Record successful operation."""
        if self.state.state == "HALF_OPEN":
            # Service has recovered, close the circuit
            self.state.state = "CLOSED"
            self.state.failure_count = 0
            logger.info("circuit_breaker_closed")
        elif self.state.state == "CLOSED":
            # Reset failure count on success
            self.state.failure_count = 0

    def record_failure(self) -> None:
        """Record failed operation."""
        self.state.failure_count += 1
        self.state.last_failure_time = time.time()

        if self.state.failure_count >= self.threshold:
            self.state.state = "OPEN"
            logger.warning(
                "circuit_breaker_opened",
                failure_count=self.state.failure_count,
                threshold=self.threshold,
            )


class AIProviderInterface(ABC):
    """
    Abstract base class for AI provider implementations.

    All AI providers must implement this interface to ensure compatibility
    with the provider-agnostic client.
    """

    def __init__(self, config: AIClientConfig):
        self.config = config
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the AI provider client."""
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate text using the AI provider.

        Args:
            prompt: Input prompt for text generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific parameters

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate chat response using the AI provider.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific parameters

        Returns:
            Generated chat response
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connections and cleanup resources."""
        pass


class OpenAIProvider(AIProviderInterface):
    """OpenAI-specific implementation of AI provider interface."""

    def __init__(self, config: AIClientConfig):
        super().__init__(config)
        self.client: Optional[Any] = None

    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        try:
            if AsyncOpenAI is None:
                raise ImportError("OpenAI package is not installed")

            self.client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                max_retries=0,  # We handle retries ourselves
            )

            # Test the connection
            await self.client.models.list()
            self.logger.info("openai_client_initialized")

        except ImportError as e:
            raise ConfigurationError(
                "OpenAI package is not installed. Install with: pip install openai"
            ) from e
        except Exception as e:
            raise ConnectionError(
                f"Failed to initialize OpenAI client: {str(e)}"
            ) from e

    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text using OpenAI."""
        if not self.client:
            raise ConnectionError("OpenAI client not initialized")

        try:
            # Prepare parameters for OpenAI API call
            openai_params = {
                "model": self.config.model,
                "messages": [{"role": "user", "content": prompt}],
            }
            
            # Only include temperature if specified and not None
            if temperature is not None:
                openai_params["temperature"] = temperature
            
            # Only include max_tokens if it's not None
            if max_tokens is not None:
                openai_params["max_tokens"] = max_tokens
                
            # Include any additional kwargs
            openai_params.update(kwargs)

            response = await self.client.chat.completions.create(**openai_params)

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error("openai_text_generation_failed", error=str(e))
            raise self._map_openai_error(e)

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        """Generate chat response using OpenAI."""
        if not self.client:
            raise ConnectionError("OpenAI client not initialized")

        try:
            # Prepare parameters for OpenAI API call
            openai_params = {
                "model": self.config.model,
                "messages": messages,
            }
            
            # Only include temperature if specified and not None
            if temperature is not None:
                openai_params["temperature"] = temperature
            
            # Only include max_tokens if it's not None
            if max_tokens is not None:
                openai_params["max_tokens"] = max_tokens
                
            # Include any additional kwargs
            openai_params.update(kwargs)

            response = await self.client.chat.completions.create(**openai_params)

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error("openai_chat_generation_failed", error=str(e))
            raise self._map_openai_error(e)

    def _map_openai_error(self, error: Exception) -> AIClientError:
        """Map OpenAI-specific errors to AI client errors."""
        error_str = str(error).lower()

        if "authentication" in error_str or "api key" in error_str:
            return AuthenticationError(f"OpenAI authentication failed: {str(error)}")
        elif "rate limit" in error_str:
            return RateLimitError(f"OpenAI rate limit exceeded: {str(error)}")
        else:
            return ConnectionError(f"OpenAI API error: {str(error)}")

    async def close(self) -> None:
        """Close OpenAI client connections."""
        if self.client:
            await self.client.close()
            self.client = None
            self.logger.info("openai_client_closed")


class AIClient:
    """
    Main AI client with provider-agnostic interface and resilience features.

    Features:
    - Provider abstraction for easy switching
    - Circuit breaker pattern for resilience
    - Retry logic with exponential backoff
    - Comprehensive error handling
    - LangSmith tracing integration
    """

    _instance: Optional["AIClient"] = None
    _is_initialized: bool = False

    def __new__(cls) -> "AIClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the AI client."""
        if not hasattr(self, "_config"):
            self._config: Optional[AIClientConfig] = None
            self._provider: Optional[AIProviderInterface] = None
            self._circuit_breaker: Optional[AICircuitBreaker] = None
            self._initialization_error: Optional[str] = None

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        if cls._instance:
            # Handle the case where there's no running event loop (e.g., in tests)
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(cls._instance.close())
            except RuntimeError:
                # No running event loop, close synchronously if possible
                logger.debug("no_event_loop_for_async_close")
        cls._instance = None
        cls._is_initialized = False

        # Also reset the global instance for testing
        global ai_client
        ai_client = AIClient()

    async def initialize(self, config: Optional[AIClientConfig] = None) -> bool:
        """
        Initialize the AI client with configuration.

        Args:
            config: Optional configuration, will load from env if not provided

        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._is_initialized:
            logger.debug("ai_client_already_initialized")
            return True

        try:
            # Load configuration
            self._config = config or AIClientConfig.from_env()

            # Initialize circuit breaker
            self._circuit_breaker = AICircuitBreaker(
                threshold=self._config.circuit_breaker_threshold,
                timeout=self._config.circuit_breaker_timeout,
            )

            # Initialize provider
            await self._initialize_provider()

            self._is_initialized = True
            self._initialization_error = None

            logger.info(
                "ai_client_initialized",
                provider=self._config.provider.value,
                model=self._config.model,
            )

            return True

        except Exception as e:
            error_msg = f"Failed to initialize AI client: {str(e)}"
            self._initialization_error = error_msg
            logger.error("ai_client_initialization_failed", error=str(e))
            return False

    async def _initialize_provider(self) -> None:
        """Initialize the AI provider based on configuration."""
        if self._config.provider == AIProvider.OPENAI:
            self._provider = OpenAIProvider(self._config)
        elif self._config.provider == AIProvider.ANTHROPIC:
            # TODO: Implement Anthropic provider
            raise ConfigurationError("Anthropic provider not yet implemented")
        else:
            raise ConfigurationError(f"Unsupported provider: {self._config.provider}")

        await self._provider.initialize()

    async def generate_text(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate text with retry logic and error handling.

        Args:
            prompt: Input prompt for text generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text response

        Raises:
            AIClientError: If generation fails after retries
        """
        if not self._is_initialized or not self._provider:
            raise ConnectionError("AI client not initialized")

        return await self._execute_with_retry(
            "generate_text",
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate chat response with retry logic and error handling.

        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated chat response

        Raises:
            AIClientError: If generation fails after retries
        """
        if not self._is_initialized or not self._provider:
            raise ConnectionError("AI client not initialized")

        return await self._execute_with_retry(
            "generate_chat",
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

    async def _execute_with_retry(self, method_name: str, **kwargs: Any) -> str:
        """
        Execute AI provider method with retry logic and circuit breaker.

        Args:
            method_name: Name of the method to execute
            **kwargs: Arguments for the method

        Returns:
            Method result

        Raises:
            AIClientError: If execution fails
        """
        if not self._circuit_breaker or not self._circuit_breaker.can_execute():
            raise ConnectionError(
                "Circuit breaker is open, AI service temporarily unavailable"
            )

        method = getattr(self._provider, method_name)
        delay = self._config.retry_delay

        for attempt in range(self._config.max_retries + 1):
            try:
                with observability_service.trace_operation(
                    operation_name=f"ai_{method_name}",
                    provider=self._config.provider.value,
                    model=self._config.model,
                    attempt=attempt + 1,
                    max_attempts=self._config.max_retries + 1,
                ) as trace_id:
                    logger.info(
                        "ai_request_started",
                        method=method_name,
                        trace_id=trace_id,
                        attempt=attempt + 1,
                    )

                    result = await method(**kwargs)

                    # Record success and return
                    if self._circuit_breaker:
                        self._circuit_breaker.record_success()

                    logger.info(
                        "ai_request_success",
                        method=method_name,
                        trace_id=trace_id,
                        attempt=attempt + 1,
                    )

                    return result

            except AuthenticationError:
                # Don't retry authentication errors
                logger.error(
                    "ai_authentication_error", method=method_name, attempt=attempt + 1
                )
                if self._circuit_breaker:
                    self._circuit_breaker.record_failure()
                raise

            except RateLimitError:
                # Special handling for rate limits
                if attempt == self._config.max_retries:
                    logger.error(
                        "ai_rate_limit_exceeded",
                        method=method_name,
                        attempt=attempt + 1,
                    )
                    if self._circuit_breaker:
                        self._circuit_breaker.record_failure()
                    raise

                # Exponential backoff for rate limits
                wait_time = min(delay * (2**attempt), self._config.max_retry_delay)
                logger.warning(
                    "ai_rate_limit_waiting",
                    method=method_name,
                    attempt=attempt + 1,
                    wait_time=wait_time,
                )
                await asyncio.sleep(wait_time)

            except Exception as e:
                if attempt == self._config.max_retries:
                    logger.error(
                        "ai_request_failed_final",
                        method=method_name,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    if self._circuit_breaker:
                        self._circuit_breaker.record_failure()
                    raise AIClientError(
                        f"AI request failed after {self._config.max_retries + 1} attempts: {str(e)}"
                    ) from e

                logger.warning(
                    "ai_request_failed_retry",
                    method=method_name,
                    attempt=attempt + 1,
                    error=str(e),
                    delay=delay,
                )

                await asyncio.sleep(delay)
                delay = min(
                    delay * self._config.backoff_multiplier,
                    self._config.max_retry_delay,
                )

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the AI client.

        Returns:
            Dict containing health status information
        """
        if not self._is_initialized:
            return {
                "status": "unhealthy",
                "provider": "unknown",
                "model": "unknown",
                "error": self._initialization_error or "not_initialized",
            }

        try:
            circuit_breaker_status = "unknown"
            if self._circuit_breaker:
                circuit_breaker_status = self._circuit_breaker.state.state

            return {
                "status": "healthy",
                "provider": self._config.provider.value if self._config else "unknown",
                "model": self._config.model if self._config else "unknown",
                "circuit_breaker_state": circuit_breaker_status,
                "timeout": self._config.timeout if self._config else "unknown",
                "max_retries": self._config.max_retries if self._config else "unknown",
            }

        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "provider": self._config.provider.value if self._config else "unknown",
                "model": self._config.model if self._config else "unknown",
                "error": f"health_check_failed: {str(e)}",
            }

    async def close(self) -> None:
        """Close all connections and cleanup resources."""
        if self._provider:
            await self._provider.close()
            self._provider = None

        self._is_initialized = False
        logger.info("ai_client_closed")

    def is_initialized(self) -> bool:
        """Check if the AI client is initialized."""
        return self._is_initialized

    def get_config(self) -> Optional[AIClientConfig]:
        """Get the current AI client configuration."""
        return self._config


# Global service instance
ai_client = AIClient()
