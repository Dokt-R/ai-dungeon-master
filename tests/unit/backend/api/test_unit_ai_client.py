"""
Unit tests for the AI client component.

Tests cover:
- AI client configuration loading and validation
- Provider-agnostic interface with multiple implementations
- OpenAI provider implementation
- Circuit breaker functionality
- Retry logic and exponential backoff
- Error handling and graceful degradation
- Integration with LangSmith tracing
"""

import asyncio
import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from packages.backend.components.ai_client import (
    AICircuitBreaker,
    AIClient,
    AIClientConfig,
    AIProvider,
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    OpenAIProvider,
    RateLimitError,
    ai_client,
)


@pytest.fixture
def reset_ai_client():
    """Reset the AI client singleton before and after each test."""
    AIClient.reset_instance()
    yield
    AIClient.reset_instance()


class TestAIClientConfig:
    """Test the AIClientConfig dataclass."""

    def test_config_creation_with_all_params(self):
        """Test creating config with all parameters."""
        config = AIClientConfig(
            provider=AIProvider.OPENAI,
            api_key="test-key",
            base_url="https://api.example.com",
            model="gpt-5-nano-turbo",
            timeout=60.0,
            max_retries=5,
            retry_delay=2.0,
            circuit_breaker_threshold=10,
        )

        assert config.provider == AIProvider.OPENAI
        assert config.api_key == "test-key"
        assert config.base_url == "https://api.example.com"
        assert config.model == "gpt-5-nano-turbo"
        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.circuit_breaker_threshold == 10

    def test_config_creation_with_defaults(self):
        """Test creating config with default values."""
        config = AIClientConfig(api_key="test-key")

        assert config.provider == AIProvider.OPENAI
        assert config.api_key == "test-key"
        assert config.base_url is None
        assert config.model == "gpt-5-nano"
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.circuit_breaker_threshold == 5

    def test_config_validation_missing_api_key(self):
        """Test configuration validation with missing API key."""
        with pytest.raises(ConfigurationError, match="API key is required"):
            AIClientConfig(api_key="")

    def test_config_validation_invalid_timeout(self):
        """Test configuration validation with invalid timeout."""
        with pytest.raises(ConfigurationError, match="Timeout must be positive"):
            AIClientConfig(api_key="test-key", timeout=-1)

    def test_config_validation_invalid_max_retries(self):
        """Test configuration validation with invalid max retries."""
        with pytest.raises(ConfigurationError, match="Max retries cannot be negative"):
            AIClientConfig(api_key="test-key", max_retries=-1)

    def test_config_validation_invalid_circuit_breaker_threshold(self):
        """Test configuration validation with invalid circuit breaker threshold."""
        with pytest.raises(
            ConfigurationError, match="Circuit breaker threshold must be at least 1"
        ):
            AIClientConfig(api_key="test-key", circuit_breaker_threshold=0)

    @patch.dict(
        os.environ,
        {
            "AI_PROVIDER_API_KEY": "env-test-key",
            "AI_PROVIDER_BASE_URL": "https://api.example.com",
            "AI_PROVIDER_MODEL": "gpt-5-nano-turbo",
            "AI_PROVIDER_TIMEOUT": "45.0",
            "AI_PROVIDER_MAX_RETRIES": "5",
        },
    )
    def test_from_env_success(self):
        """Test successful configuration loading from environment variables."""
        config = AIClientConfig.from_env()

        assert config.api_key == "env-test-key"
        assert config.base_url == "https://api.example.com"
        assert config.model == "gpt-5-nano-turbo"
        assert config.timeout == 45.0
        assert config.max_retries == 5

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_missing_api_key(self):
        """Test configuration loading with missing API key environment variable."""
        with pytest.raises(
            ConfigurationError,
            match="AI_PROVIDER_API_KEY environment variable is required",
        ):
            AIClientConfig.from_env()

    @patch.dict(
        os.environ,
        {"AI_PROVIDER_API_KEY": "test-key", "AI_PROVIDER": "invalid_provider"},
    )
    def test_from_env_invalid_provider(self):
        """Test configuration loading with invalid provider."""
        with pytest.raises(
            ConfigurationError, match="Unsupported AI provider: invalid_provider"
        ):
            AIClientConfig.from_env()


class TestAICircuitBreaker:
    """Test the AICircuitBreaker class."""

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker initial state."""
        cb = AICircuitBreaker(threshold=3, timeout=60)

        assert cb.threshold == 3
        assert cb.timeout == 60
        assert cb.state.state == "CLOSED"
        assert cb.state.failure_count == 0
        assert cb.state.last_failure_time == 0

    def test_can_execute_closed_state(self):
        """Test can_execute when circuit breaker is closed."""
        cb = AICircuitBreaker()

        assert cb.can_execute() is True

    def test_can_execute_open_state_within_timeout(self):
        """Test can_execute when circuit breaker is open and within timeout."""
        cb = AICircuitBreaker(timeout=60)
        cb.state.state = "OPEN"
        cb.state.last_failure_time = 1000  # Recent failure

        # Mock current time to be within timeout
        with patch("time.time", return_value=1010):  # 10 seconds later
            assert cb.can_execute() is False

    def test_can_execute_open_state_after_timeout(self):
        """Test can_execute when circuit breaker is open and timeout has passed."""
        cb = AICircuitBreaker(timeout=60)
        cb.state.state = "OPEN"
        cb.state.last_failure_time = 1000  # Recent failure

        # Mock current time to be after timeout
        with patch("time.time", return_value=1070):  # 70 seconds later
            assert cb.can_execute() is True
            assert cb.state.state == "HALF_OPEN"

    def test_record_success_closed_state(self):
        """Test recording success in closed state."""
        cb = AICircuitBreaker()
        cb.state.failure_count = 2

        cb.record_success()

        assert cb.state.failure_count == 0
        assert cb.state.state == "CLOSED"

    def test_record_success_half_open_state(self):
        """Test recording success in half-open state."""
        cb = AICircuitBreaker()
        cb.state.state = "HALF_OPEN"
        cb.state.failure_count = 2

        cb.record_success()

        assert cb.state.failure_count == 0
        assert cb.state.state == "CLOSED"

    def test_record_failure_threshold_not_reached(self):
        """Test recording failure when threshold not reached."""
        cb = AICircuitBreaker(threshold=3)
        cb.state.failure_count = 1

        cb.record_failure()

        assert cb.state.failure_count == 2
        assert cb.state.state == "CLOSED"

    def test_record_failure_threshold_reached(self):
        """Test recording failure when threshold reached."""
        cb = AICircuitBreaker(threshold=3)
        cb.state.failure_count = 2

        with patch("time.time", return_value=1000):
            cb.record_failure()

        assert cb.state.failure_count == 3
        assert cb.state.state == "OPEN"
        assert cb.state.last_failure_time == 1000


class TestOpenAIProvider:
    """Test the OpenAIProvider implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = AIClientConfig(api_key="test-key")

    @patch("packages.backend.components.ai_client.AsyncOpenAI")
    def test_initialize_success(self, mock_openai_class):
        """Test successful OpenAI provider initialization."""
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        provider = OpenAIProvider(self.config)
        asyncio.run(provider.initialize())

        assert provider.client is not None
        mock_openai_class.assert_called_once_with(
            api_key="test-key", base_url=None, timeout=30.0, max_retries=0
        )
        mock_client.models.list.assert_called_once()

    @patch("packages.backend.components.ai_client.AsyncOpenAI")
    def test_initialize_with_base_url(self, mock_openai_class):
        """Test OpenAI provider initialization with custom base URL."""
        config = AIClientConfig(api_key="test-key", base_url="https://custom.api.com")
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        provider = OpenAIProvider(config)
        asyncio.run(provider.initialize())

        mock_openai_class.assert_called_once_with(
            api_key="test-key",
            base_url="https://custom.api.com",
            timeout=30.0,
            max_retries=0,
        )

    def test_initialize_without_openai_package(self):
        """Test OpenAI provider initialization when package is not installed."""
        with patch(
            "packages.backend.components.ai_client.AsyncOpenAI", side_effect=ImportError
        ):
            provider = OpenAIProvider(self.config)

            with pytest.raises(
                ConfigurationError, match="OpenAI package is not installed"
            ):
                asyncio.run(provider.initialize())

    @patch("packages.backend.components.ai_client.AsyncOpenAI")
    def test_initialize_connection_error(self, mock_openai_class):
        """Test OpenAI provider initialization with connection error."""
        mock_client = AsyncMock()
        mock_client.models.list.side_effect = Exception("Connection failed")
        mock_openai_class.return_value = mock_client

        provider = OpenAIProvider(self.config)

        with pytest.raises(ConnectionError, match="Failed to initialize OpenAI client"):
            asyncio.run(provider.initialize())

    @patch("packages.backend.components.ai_client.AsyncOpenAI")
    def test_generate_text_success(self, mock_openai_class):
        """Test successful text generation with OpenAI provider."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Generated text"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        provider = OpenAIProvider(self.config)
        provider.client = mock_client

        result = asyncio.run(provider.generate_text("Test prompt"))

        assert result == "Generated text"
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": "Test prompt"}],
            max_tokens=None,
            temperature=1,
        )

    @patch("packages.backend.components.ai_client.AsyncOpenAI")
    def test_generate_text_with_options(self, mock_openai_class):
        """Test text generation with custom options."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Generated text"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        config = AIClientConfig(api_key="test-key", model="gpt-5-nano-turbo")
        provider = OpenAIProvider(config)
        provider.client = mock_client

        result = asyncio.run(
            provider.generate_text("Test prompt", max_tokens=100, temperature=1)
        )

        assert result == "Generated text"
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-5-nano-turbo",
            messages=[{"role": "user", "content": "Test prompt"}],
            max_tokens=100,
            temperature=1,
        )

    @patch("packages.backend.components.ai_client.AsyncOpenAI")
    def test_generate_text_authentication_error(self, mock_openai_class):
        """Test text generation with authentication error."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = Exception("Invalid API key")
        mock_openai_class.return_value = mock_client

        provider = OpenAIProvider(self.config)
        provider.client = mock_client

        with pytest.raises(AuthenticationError, match="OpenAI authentication failed"):
            asyncio.run(provider.generate_text("Test prompt"))

    @patch("packages.backend.components.ai_client.AsyncOpenAI")
    def test_generate_text_rate_limit_error(self, mock_openai_class):
        """Test text generation with rate limit error."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = Exception(
            "Rate limit exceeded"
        )
        mock_openai_class.return_value = mock_client

        provider = OpenAIProvider(self.config)
        provider.client = mock_client

        with pytest.raises(RateLimitError, match="OpenAI rate limit exceeded"):
            asyncio.run(provider.generate_text("Test prompt"))

    @patch("packages.backend.components.ai_client.AsyncOpenAI")
    def test_generate_text_connection_error(self, mock_openai_class):
        """Test text generation with connection error."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = Exception("Network timeout")
        mock_openai_class.return_value = mock_client

        provider = OpenAIProvider(self.config)
        provider.client = mock_client

        with pytest.raises(ConnectionError, match="OpenAI API error"):
            asyncio.run(provider.generate_text("Test prompt"))

    @patch("packages.backend.components.ai_client.AsyncOpenAI")
    def test_generate_chat_success(self, mock_openai_class):
        """Test successful chat generation with OpenAI provider."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Chat response"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]

        provider = OpenAIProvider(self.config)
        provider.client = mock_client

        result = asyncio.run(provider.generate_chat(messages))

        assert result == "Chat response"
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-5-nano", messages=messages, max_tokens=None, temperature=1
        )


class TestAIClient:
    """Test the main AIClient class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = AIClientConfig(api_key="test-key")

    def test_singleton_pattern(self, reset_ai_client):
        """Test that AIClient follows singleton pattern."""
        client1 = AIClient()
        client2 = AIClient()

        assert client1 is client2

    def test_initialization_not_initialized(self, reset_ai_client):
        """Test AI client state when not initialized."""
        client = AIClient()

        assert not client.is_initialized()
        assert client.get_config() is None
        assert client._initialization_error is None

    @patch("packages.backend.components.ai_client.OpenAIProvider")
    def test_initialize_success(self, mock_provider_class, reset_ai_client):
        """Test successful AI client initialization."""
        mock_provider = AsyncMock()
        mock_provider_class.return_value = mock_provider

        client = AIClient()
        result = asyncio.run(client.initialize(self.config))

        assert result is True
        assert client.is_initialized()
        assert client._config is not None
        assert client._provider is not None
        assert client._initialization_error is None
        assert client._circuit_breaker is not None

        mock_provider_class.assert_called_once_with(self.config)
        mock_provider.initialize.assert_called_once()

    @patch("packages.backend.components.ai_client.OpenAIProvider")
    def test_initialize_provider_error(self, mock_provider_class, reset_ai_client):
        """Test AI client initialization with provider error."""
        mock_provider = AsyncMock()
        mock_provider.initialize.side_effect = Exception("Provider init failed")
        mock_provider_class.return_value = mock_provider

        client = AIClient()
        result = asyncio.run(client.initialize(self.config))

        assert result is False
        assert not client.is_initialized()
        assert client._initialization_error is not None

    def test_initialize_twice(self, reset_ai_client):
        """Test initializing AI client twice."""
        client = AIClient()

        # First initialization will fail due to missing provider mock
        result1 = asyncio.run(client.initialize(self.config))
        assert result1 is False

        # Second initialization should also fail
        result2 = asyncio.run(client.initialize(self.config))
        assert result2 is False

    @patch("packages.backend.components.ai_client.OpenAIProvider")
    def test_generate_text_success(self, mock_provider_class, reset_ai_client):
        """Test successful text generation through AI client."""
        # Setup mocks
        mock_provider = AsyncMock()
        mock_provider.generate_text.return_value = "Generated text"
        mock_provider_class.return_value = mock_provider

        client = AIClient()
        asyncio.run(client.initialize(self.config))

        with patch.object(client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = "Generated text"

            result = asyncio.run(client.generate_text("Test prompt"))

            assert result == "Generated text"
            mock_execute.assert_called_once_with(
                "generate_text", prompt="Test prompt", max_tokens=None, temperature=None
            )

    @patch("packages.backend.components.ai_client.OpenAIProvider")
    def test_generate_text_not_initialized(self, mock_provider_class, reset_ai_client):
        """Test text generation when AI client is not initialized."""
        client = AIClient()

        with pytest.raises(ConnectionError, match="AI client not initialized"):
            asyncio.run(client.generate_text("Test prompt"))

    @patch("packages.backend.components.ai_client.OpenAIProvider")
    def test_generate_chat_success(self, mock_provider_class, reset_ai_client):
        """Test successful chat generation through AI client."""
        mock_provider = AsyncMock()
        mock_provider.generate_chat.return_value = "Chat response"
        mock_provider_class.return_value = mock_provider

        client = AIClient()
        asyncio.run(client.initialize(self.config))

        with patch.object(client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = "Chat response"

            messages = [{"role": "user", "content": "Hello"}]
            result = asyncio.run(client.generate_chat(messages))

            assert result == "Chat response"
            mock_execute.assert_called_once_with(
                "generate_chat", messages=messages, max_tokens=None, temperature=None
            )

    @patch("packages.backend.components.ai_client.OpenAIProvider")
    def test_get_health_status_not_initialized(
        self, mock_provider_class, reset_ai_client
    ):
        """Test health status when AI client is not initialized."""
        client = AIClient()

        status = client.get_health_status()

        expected_status = {
            "status": "unhealthy",
            "provider": "unknown",
            "model": "unknown",
            "error": "not_initialized",
        }

        assert status == expected_status

    @patch("packages.backend.components.ai_client.OpenAIProvider")
    def test_get_health_status_initialized(self, mock_provider_class, reset_ai_client):
        """Test health status when AI client is initialized."""
        mock_provider = AsyncMock()
        mock_provider_class.return_value = mock_provider

        client = AIClient()
        asyncio.run(client.initialize(self.config))

        status = client.get_health_status()

        assert status["status"] == "healthy"
        assert status["provider"] == "openai"
        assert status["model"] == "gpt-5-nano"
        assert status["circuit_breaker_state"] == "CLOSED"
        assert status["timeout"] == 30.0
        assert status["max_retries"] == 3

    @patch("packages.backend.components.ai_client.OpenAIProvider")
    def test_execute_with_retry_success(self, mock_provider_class, reset_ai_client):
        """Test successful execution with retry logic."""
        mock_provider = AsyncMock()
        mock_provider.generate_text.return_value = "Success"
        mock_provider_class.return_value = mock_provider

        client = AIClient()
        asyncio.run(client.initialize(self.config))

        result = asyncio.run(client._execute_with_retry("generate_text", prompt="Test"))

        assert result == "Success"

    @patch("packages.backend.components.ai_client.OpenAIProvider")
    def test_execute_with_retry_circuit_breaker_open(
        self, mock_provider_class, reset_ai_client
    ):
        """Test execution when circuit breaker is open."""
        mock_provider = AsyncMock()
        mock_provider_class.return_value = mock_provider

        client = AIClient()
        asyncio.run(client.initialize(self.config))

        # Open the circuit breaker
        client._circuit_breaker.state.state = "OPEN"
        client._circuit_breaker.state.last_failure_time = 1000

        with patch("time.time", return_value=1010):  # Within timeout
            with pytest.raises(ConnectionError, match="Circuit breaker is open"):
                asyncio.run(client._execute_with_retry("generate_text", prompt="Test"))

    @patch("packages.backend.components.ai_client.OpenAIProvider")
    def test_execute_with_retry_authentication_error(
        self, mock_provider_class, reset_ai_client
    ):
        """Test execution with authentication error (no retry)."""
        mock_provider = AsyncMock()
        mock_provider.generate_text.side_effect = AuthenticationError("Auth failed")
        mock_provider_class.return_value = mock_provider

        client = AIClient()
        asyncio.run(client.initialize(self.config))

        with pytest.raises(AuthenticationError, match="Auth failed"):
            asyncio.run(client._execute_with_retry("generate_text", prompt="Test"))

    @patch("packages.backend.components.ai_client.OpenAIProvider")
    def test_execute_with_retry_with_retries(
        self, mock_provider_class, reset_ai_client
    ):
        """Test execution with retries on recoverable errors."""
        mock_provider = AsyncMock()
        # Fail twice, then succeed
        mock_provider.generate_text.side_effect = [
            ConnectionError("Network error"),
            ConnectionError("Network error"),
            "Success",
        ]
        mock_provider_class.return_value = mock_provider

        client = AIClient()
        asyncio.run(client.initialize(self.config))

        with patch("asyncio.sleep") as mock_sleep:
            result = asyncio.run(
                client._execute_with_retry("generate_text", prompt="Test")
            )

            assert result == "Success"
            assert mock_provider.generate_text.call_count == 3
            assert mock_sleep.call_count == 2  # Two retry delays


class TestGlobalAIClientInstance:
    """Test the global AI client instance."""

    def setup_method(self):
        """Reset the singleton instance before each test."""
        AIClient.reset_instance()

    def teardown_method(self):
        """Reset the singleton instance after each test."""
        AIClient.reset_instance()

    def test_global_instance_exists(self):
        """Test that the global instance exists and is correct type."""
        assert isinstance(ai_client, AIClient)

    def test_global_instance_singleton(self):
        """Test that the global instance follows singleton pattern."""
        from packages.backend.components.ai_client import ai_client as global_client

        client1 = AIClient()
        client2 = AIClient()

        assert global_client is client1
        assert global_client is client2
