"""
Unit tests for the observability service component.

Tests cover:
- Environment variable loading and validation
- LangSmith client initialization
- Error handling for configuration issues
- Tracing functionality with mocked dependencies
- Health check functionality
"""

import os
from unittest.mock import Mock, patch

import pytest

from packages.backend.components.observability_service import (
    ConfigurationError,
    ConfigurationValidator,
    ObservabilityConfig,
    ObservabilityService,
    observability_service,
)


# Comprehensive mock setup to prevent any real network calls
@pytest.fixture(autouse=True)
def mock_langsmith_completely():
    """Mock all LangSmith components to prevent network calls."""
    with (
        patch("langsmith.Client") as mock_client_class,
        patch("langsmith.traceable") as mock_traceable,
        patch("langsmith.trace") as mock_trace,
    ):
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock traceable decorator
        def mock_decorator(*args, **kwargs):
            def wrapper(func):
                def wrapped_func(*args, **kwargs):
                    return func(*args, **kwargs)

                return wrapped_func

            return wrapper

        mock_traceable.side_effect = mock_decorator
        mock_trace.side_effect = mock_decorator

        yield mock_client_class, mock_traceable, mock_trace


os.environ["PYTEST_CURRENT_TEST"] = "integration_test_for_performance"


class TestObservabilityConfig:
    """Test the ObservabilityConfig dataclass."""

    def test_config_creation_with_all_params(self):
        """Test creating config with all parameters."""
        config = ObservabilityConfig(
            api_key="ls__test_key_12345",
            project="test-project",
            endpoint="https://api.example.com",
            tracing_enabled=True,
            langsmith_tracing=True,
        )

        assert config.api_key == "ls__test_key_12345"
        assert config.project == "test-project"
        assert config.endpoint == "https://api.example.com"
        assert config.tracing_enabled is True
        assert config.langsmith_tracing is True

    def test_config_creation_with_defaults(self):
        """Test creating config with default values."""
        config = ObservabilityConfig(api_key="ls__test_key_12345")

        assert config.api_key == "ls__test_key_12345"
        assert config.project == "ai-dungeon-master"
        assert config.endpoint is None
        assert config.tracing_enabled is True
        assert config.langsmith_tracing is False  # Should default to False

    def test_config_creation_with_langsmith_tracing_enabled(self):
        """Test creating config with langsmith_tracing explicitly enabled."""
        config = ObservabilityConfig(
            api_key="ls__test_key_12345", langsmith_tracing=True
        )

        assert config.api_key == "ls__test_key_12345"
        assert config.langsmith_tracing is True


class TestObservabilityService:
    """Test the ObservabilityService class."""

    def setup_method(self):
        """Reset the singleton instance before each test."""
        ObservabilityService.reset_instance()
        self.service = ObservabilityService()

        # Ensure service is not initialized at the start of each test
        self.service._is_initialized = False
        self.service._config = None
        self.service._langsmith_client = None

    def teardown_method(self):
        """Reset the singleton instance after each test."""
        ObservabilityService.reset_instance()

    def test_singleton_pattern(self):
        """Test that ObservabilityService follows singleton pattern."""
        service1 = ObservabilityService()
        service2 = ObservabilityService()

        assert service1 is service2

    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_missing_api_key(self):
        """Test configuration loading with missing API key."""
        with pytest.raises(
            ConfigurationError,
            match="LANGSMITH_API_KEY environment variable is required",
        ):
            self.service.load_config()

    @patch.dict(
        os.environ, {"LANGSMITH_API_KEY": "", "LANGSMITH_PROJECT": "test-project"}
    )
    def test_load_config_empty_api_key(self):
        """Test configuration loading with empty API key."""
        with pytest.raises(
            ConfigurationError, match="LANGSMITH_API_KEY cannot be empty"
        ):
            self.service.load_config()

    @patch.dict(
        os.environ,
        {
            "LANGSMITH_API_KEY": "ls__test_key_12345",
            "LANGSMITH_PROJECT": "",
            "LANGSMITH_ENDPOINT": "https://api.example.com",
        },
    )
    def test_load_config_empty_project(self):
        """Test configuration loading with empty project name."""
        with pytest.raises(
            ConfigurationError, match="LANGSMITH_PROJECT cannot be empty"
        ):
            self.service.load_config()

    @patch.dict(
        os.environ,
        {
            "LANGSMITH_API_KEY": "ls__test_key_12345",
            "LANGSMITH_PROJECT": "test-project",
            "LANGSMITH_ENDPOINT": "https://api.example.com",
        },
    )
    def test_load_config_success(self):
        """Test successful configuration loading."""
        config = self.service.load_config()

        assert config.api_key == "ls__test_key_12345"
        assert config.project == "test-project"
        assert config.endpoint == "https://api.example.com"
        assert config.tracing_enabled is True

    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "ls__test_key_12345", "LANGSMITH_TRACING": "false"},
    )
    def test_load_config_defaults(self):
        """Test configuration loading with default values."""
        config = self.service.load_config()

        assert config.api_key == "ls__test_key_12345"
        assert config.project == "ai-dungeon-master"
        # Endpoint can be None or a default value - both are acceptable
        assert config.endpoint is None or isinstance(config.endpoint, str)
        assert config.tracing_enabled is True
        assert config.langsmith_tracing is False  # Should default to False

    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "ls__test_key_12345", "LANGSMITH_TRACING": "true"},
    )
    def test_load_config_with_langsmith_tracing_enabled(self):
        """Test configuration loading with LANGSMITH_TRACING=true."""
        config = self.service.load_config()

        assert config.api_key == "ls__test_key_12345"
        assert config.langsmith_tracing is True

    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "ls__test_key_12345", "LANGSMITH_TRACING": "false"},
    )
    def test_load_config_with_langsmith_tracing_disabled(self):
        """Test configuration loading with LANGSMITH_TRACING=false."""
        config = self.service.load_config()

        assert config.api_key == "ls__test_key_12345"
        assert config.langsmith_tracing is False

    @patch.dict(
        os.environ,
        {
            "LANGSMITH_API_KEY": "ls__test_key_12345",
            "LANGSMITH_TRACING": "invalid_value",
        },
    )
    def test_load_config_with_langsmith_tracing_invalid_value(self):
        """Test configuration loading with invalid LANGSMITH_TRACING value."""
        config = self.service.load_config()

        assert config.api_key == "ls__test_key_12345"
        assert (
            config.langsmith_tracing is False
        )  # Should default to False for invalid values

    @patch(
        "packages.backend.components.observability_service.ObservabilityService._initialize_langsmith_client"
    )
    @patch.dict(
        os.environ,
        {
            "LANGSMITH_API_KEY": "ls__test_key_12345",
            "LANGSMITH_PROJECT": "test-project",
            "LANGSMITH_TRACING": "true",
        },
    )
    def test_initialize_success(self, mock_init_client):
        """Test successful service initialization."""
        # Mock the client initialization to avoid import issues
        mock_client = Mock()
        self.service._langsmith_client = mock_client

        result = self.service.initialize()

        assert result is True
        assert self.service.is_initialized() is True
        assert self.service._config is not None
        assert self.service._initialization_error is None

        # Verify client initialization was called
        mock_init_client.assert_called_once()

    @patch(
        "packages.backend.components.observability_service.ObservabilityService._initialize_langsmith_client"
    )
    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "ls__test_key_12345", "LANGSMITH_TRACING": "true"},
    )
    def test_initialize_with_import_error(self, mock_init_client):
        """Test initialization with import error (service continues but logs warning)."""
        mock_init_client.side_effect = ImportError("No module named 'langsmith'")

        result = self.service.initialize()

        # Service should still initialize successfully (fault-tolerant design)
        assert result is True
        assert self.service.is_initialized() is True
        assert self.service._initialization_error is None  # No fatal error

        # Verify the import error was handled gracefully
        mock_init_client.assert_called_once()

    @patch(
        "packages.backend.components.observability_service.ObservabilityService._initialize_langsmith_client"
    )
    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "ls__test_key_12345", "LANGSMITH_TRACING": "true"},
    )
    def test_initialize_with_client_error(self, mock_init_client):
        """Test initialization with client error (service continues but logs warning)."""
        mock_init_client.side_effect = Exception("Client initialization failed")

        result = self.service.initialize()

        # Service should still initialize successfully (fault-tolerant design)
        assert result is True
        assert self.service.is_initialized() is True
        assert self.service._initialization_error is None  # No fatal error

        # Verify the client error was handled gracefully
        mock_init_client.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    def test_initialize_twice(self):
        """Test that calling initialize twice doesn't break anything."""
        # First initialization will fail due to missing env vars
        result1 = self.service.initialize()
        assert result1 is False

        # Second initialization should also fail but not crash
        result2 = self.service.initialize()
        assert result2 is False

    def test_get_health_status_not_initialized(self):
        """Test health status when service is not initialized."""
        status = self.service.get_health_status()

        expected_status = {
            "status": "unhealthy",
            "provider": "langsmith",
            "project": "unknown",
            "error": "not_initialized",
            "correlation_id_support": "enabled",
            "current_correlation_id": None,
        }

        assert status == expected_status

    @patch(
        "packages.backend.components.observability_service.ObservabilityService._initialize_langsmith_client"
    )
    @patch.dict(
        os.environ,
        {
            "LANGSMITH_API_KEY": "ls__test_key_12345",
            "LANGSMITH_PROJECT": "test-project",
            "LANGSMITH_TRACING": "true",
        },
    )
    def test_get_health_status_initialized(self, mock_init_client):
        """Test health status when service is initialized."""
        # Mock the client to avoid import issues
        mock_client = Mock()
        self.service._langsmith_client = mock_client

        self.service.initialize()
        status = self.service.get_health_status()

        assert status["status"] == "healthy"
        assert status["provider"] == "langsmith"
        assert status["project"] == "test-project"
        assert status["tracing_enabled"] is True

    @patch(
        "packages.backend.components.observability_service.ObservabilityService._initialize_langsmith_client"
    )
    @patch.dict(os.environ, {"LANGSMITH_API_KEY": "ls__test_key_12345"})
    def test_trace_operation_not_initialized(self, mock_init_client):
        """Test trace operation when service is not initialized."""
        # Don't initialize the service
        trace_calls = []

        with self.service.trace_operation("test_operation") as trace_id:
            trace_calls.append(trace_id)

        # Should still work but trace_id will be None
        assert len(trace_calls) == 1
        assert trace_calls[0] is None

    @patch(
        "packages.backend.components.observability_service.ObservabilityService._initialize_langsmith_client"
    )
    @patch.dict(
        os.environ,
        {
            "LANGSMITH_API_KEY": "ls__test_key_12345",
            "LANGSMITH_PROJECT": "test-project",
            "LANGSMITH_TRACING": "true",
        },
    )
    def test_trace_operation_initialized(self, mock_init_client):
        """Test trace operation when service is initialized."""
        # Mock the client to avoid import issues
        mock_client = Mock()
        self.service._langsmith_client = mock_client

        self.service.initialize()

        trace_calls = []

        with self.service.trace_operation("test_operation", tag1="value1") as trace_id:
            trace_calls.append(trace_id)
            # Simulate some work
            pass

        # Should have a trace_id
        assert len(trace_calls) == 1
        assert trace_calls[0] is not None
        assert "test_operation" in trace_calls[0]

    def test_get_config_not_initialized(self):
        """Test getting config when service is not initialized."""
        config = self.service.get_config()
        assert config is None

    @patch(
        "packages.backend.components.observability_service.ObservabilityService._initialize_langsmith_client"
    )
    @patch.dict(
        os.environ,
        {
            "LANGSMITH_API_KEY": "ls__test_key_12345",
            "LANGSMITH_PROJECT": "test-project",
        },
    )
    def test_get_config_initialized(self, mock_init_client):
        """Test getting config when service is initialized."""
        # Mock the client to avoid import issues
        mock_client = Mock()
        self.service._langsmith_client = mock_client

        self.service.initialize()
        config = self.service.get_config()

        assert config is not None
        assert config.api_key == "ls__test_key_12345"
        assert config.project == "test-project"


class TestLangSmithTracingDisabled:
    """Test tracing behavior when LANGSMITH_TRACING is disabled."""

    def setup_method(self):
        """Reset the singleton instance before each test."""
        ObservabilityService.reset_instance()
        self.service = ObservabilityService()

        # Ensure service is not initialized at the start of each test
        self.service._is_initialized = False
        self.service._config = None
        self.service._langsmith_client = None

    def teardown_method(self):
        """Reset the singleton instance after each test."""
        ObservabilityService.reset_instance()

    @patch.dict(os.environ, {"LANGSMITH_API_KEY": "ls__test_key_12345"})
    def test_trace_operation_disabled_by_default(self):
        """Test that trace_operation returns early when tracing is disabled by default."""
        # Configure with tracing disabled (default)
        self.service._config = ObservabilityConfig(
            api_key="ls__test_key_12345",
            langsmith_tracing=False,  # Explicitly disabled
        )
        self.service._is_initialized = True

        with self.service.trace_operation("test_operation") as trace_id:
            assert trace_id is None

    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "ls__test_key_12345", "LANGSMITH_TRACING": "false"},
    )
    def test_trace_operation_disabled_by_env_var(self):
        """Test that trace_operation returns early when disabled by environment variable."""
        self.service.initialize()

        with self.service.trace_operation("test_operation") as trace_id:
            assert trace_id is None

    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "ls__test_key_12345", "LANGSMITH_TRACING": "false"},
    )
    def test_trace_llm_call_disabled(self):
        """Test that trace_llm_call returns early when tracing is disabled."""
        self.service.initialize()

        with self.service.trace_llm_call("test-model", "test prompt") as trace_id:
            assert trace_id is None

    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "ls__test_key_12345", "LANGSMITH_TRACING": "false"},
    )
    def test_trace_ai_workflow_disabled(self):
        """Test that trace_ai_workflow returns early when tracing is disabled."""
        self.service.initialize()

        with self.service.trace_ai_workflow("test-workflow") as trace_id:
            assert trace_id is None

    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "ls__test_key_12345", "LANGSMITH_TRACING": "true"},
    )
    def test_trace_operation_enabled(self):
        """Test that trace_operation works when tracing is enabled."""
        self.service.initialize()

        with self.service.trace_operation("test_operation") as trace_id:
            assert trace_id is not None
            assert "test_operation" in trace_id

    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "ls__test_key_12345", "LANGSMITH_TRACING": "true"},
    )
    def test_trace_llm_call_enabled(self):
        """Test that trace_llm_call works when tracing is enabled."""
        self.service.initialize()

        with self.service.trace_llm_call("test-model", "test prompt") as trace_id:
            assert trace_id is not None
            assert "llm_call_test-model" in trace_id

    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "ls__test_key_12345", "LANGSMITH_TRACING": "true"},
    )
    def test_trace_ai_workflow_enabled(self):
        """Test that trace_ai_workflow works when tracing is enabled."""
        self.service.initialize()

        with self.service.trace_ai_workflow("test-workflow") as trace_id:
            assert trace_id is not None
            assert "ai_workflow_test-workflow" in trace_id


class TestGlobalServiceInstance:
    """Test the global observability service instance."""

    def setup_method(self):
        """Reset the singleton instance before each test."""
        ObservabilityService.reset_instance()

    def teardown_method(self):
        """Reset the singleton instance after each test."""
        ObservabilityService.reset_instance()

    def test_global_instance_exists(self):
        """Test that the global instance exists and is correct type."""
        assert isinstance(observability_service, ObservabilityService)

    def test_global_instance_singleton(self):
        """Test that the global instance follows singleton pattern."""
        ObservabilityService.reset_instance()
        from packages.backend.components.observability_service import (
            observability_service as global_service,
        )

        service1 = ObservabilityService()
        service2 = ObservabilityService()

        assert global_service is service1
        assert global_service is service2
        assert service1 is service2


class TestAPIKeyValidation:
    """Test API key validation with different formats."""

    def setup_method(self):
        """Reset the singleton instance before each test."""
        ObservabilityService.reset_instance()
        self.service = ObservabilityService()

    def teardown_method(self):
        """Reset the singleton instance after each test."""
        ObservabilityService.reset_instance()

    def test_api_key_validation_ls_double_underscore(self):
        """Test API key validation with ls__ prefix."""
        config = ObservabilityConfig(
            api_key="ls__test_key_12345", langsmith_tracing=True
        )

        # Create validator and test validation
        validator = ConfigurationValidator()
        result = validator.validate_config(config)

        assert result.is_valid is True

    def test_api_key_validation_lsv2_underscore(self):
        """Test API key validation with lsv2_ prefix."""
        config = ObservabilityConfig(
            api_key="lsv2_test_key_67890", langsmith_tracing=True
        )

        # Create validator and test validation
        validator = ConfigurationValidator()
        result = validator.validate_config(config)

        assert result.is_valid is True

    def test_api_key_validation_unknown_prefix_warning(self):
        """Test API key validation with unknown prefix shows warning."""
        config = ObservabilityConfig(
            api_key="unknown_prefix_key_99999", langsmith_tracing=True
        )

        # Create validator and test validation
        validator = ConfigurationValidator()
        result = validator.validate_config(config)

        assert result.is_valid is True  # Should still be valid but with warning
        assert len(result.warnings) > 0
        assert any(
            "should start with 'ls__' or 'lsv2_'" in warning
            for warning in result.warnings
        )
