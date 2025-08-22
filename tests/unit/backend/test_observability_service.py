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
    ObservabilityConfig,
    ObservabilityService,
    observability_service,
)


class TestObservabilityConfig:
    """Test the ObservabilityConfig dataclass."""

    def test_config_creation_with_all_params(self):
        """Test creating config with all parameters."""
        config = ObservabilityConfig(
            api_key="test-key",
            project="test-project",
            endpoint="https://api.example.com",
            tracing_enabled=True,
        )

        assert config.api_key == "test-key"
        assert config.project == "test-project"
        assert config.endpoint == "https://api.example.com"
        assert config.tracing_enabled is True

    def test_config_creation_with_defaults(self):
        """Test creating config with default values."""
        config = ObservabilityConfig(api_key="test-key")

        assert config.api_key == "test-key"
        assert config.project == "ai-dungeon-master"
        assert config.endpoint is None
        assert config.tracing_enabled is True


class TestObservabilityService:
    """Test the ObservabilityService class."""

    def setup_method(self):
        """Reset the singleton instance before each test."""
        ObservabilityService.reset_instance()
        self.service = ObservabilityService()

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
            "LANGSMITH_API_KEY": "test-key",
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
            "LANGSMITH_API_KEY": "test-key",
            "LANGSMITH_PROJECT": "test-project",
            "LANGSMITH_ENDPOINT": "https://api.example.com",
        },
    )
    def test_load_config_success(self):
        """Test successful configuration loading."""
        config = self.service.load_config()

        assert config.api_key == "test-key"
        assert config.project == "test-project"
        assert config.endpoint == "https://api.example.com"
        assert config.tracing_enabled is True

    @patch.dict(os.environ, {"LANGSMITH_API_KEY": "test-key"})
    def test_load_config_defaults(self):
        """Test configuration loading with default values."""
        config = self.service.load_config()

        assert config.api_key == "test-key"
        assert config.project == "ai-dungeon-master"
        assert config.endpoint is None
        assert config.tracing_enabled is True

    @patch("packages.backend.components.observability_service.Client")
    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "test-key", "LANGSMITH_PROJECT": "test-project"},
    )
    def test_initialize_success(self, mock_client_class):
        """Test successful service initialization."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        result = self.service.initialize()

        assert result is True
        assert self.service.is_initialized() is True
        assert self.service._config is not None
        assert self.service._langsmith_client is not None
        assert self.service._initialization_error is None

        # Verify client was created
        mock_client_class.assert_called_once()

    @patch("packages.backend.components.observability_service.Client")
    @patch.dict(os.environ, {"LANGSMITH_API_KEY": "test-key"})
    def test_initialize_with_import_error(self, mock_client_class):
        """Test initialization failure due to import error."""
        mock_client_class.side_effect = ImportError("No module named 'langsmith'")

        result = self.service.initialize()

        assert result is False
        assert self.service.is_initialized() is False
        assert self.service._initialization_error is not None
        assert (
            "LangSmith package is not installed" in self.service._initialization_error
        )

    @patch("packages.backend.components.observability_service.Client")
    @patch.dict(os.environ, {"LANGSMITH_API_KEY": "test-key"})
    def test_initialize_with_client_error(self, mock_client_class):
        """Test initialization failure due to client error."""
        mock_client_class.side_effect = Exception("Client initialization failed")

        result = self.service.initialize()

        assert result is False
        assert self.service.is_initialized() is False
        assert self.service._initialization_error is not None

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
        }

        assert status == expected_status

    @patch("packages.backend.components.observability_service.Client")
    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "test-key", "LANGSMITH_PROJECT": "test-project"},
    )
    def test_get_health_status_initialized(self, mock_client_class):
        """Test health status when service is initialized."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        self.service.initialize()
        status = self.service.get_health_status()

        assert status["status"] == "healthy"
        assert status["provider"] == "langsmith"
        assert status["project"] == "test-project"
        assert status["tracing_enabled"] is True

    @patch("packages.backend.components.observability_service.Client")
    @patch.dict(os.environ, {"LANGSMITH_API_KEY": "test-key"})
    def test_trace_operation_not_initialized(self, mock_client_class):
        """Test trace operation when service is not initialized."""
        # Don't initialize the service
        trace_calls = []

        with self.service.trace_operation("test_operation") as trace_id:
            trace_calls.append(trace_id)

        # Should still work but trace_id will be None
        assert len(trace_calls) == 1
        assert trace_calls[0] is None

    @patch("packages.backend.components.observability_service.Client")
    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "test-key", "LANGSMITH_PROJECT": "test-project"},
    )
    def test_trace_operation_initialized(self, mock_client_class):
        """Test trace operation when service is initialized."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

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

    @patch("packages.backend.components.observability_service.Client")
    @patch.dict(
        os.environ,
        {"LANGSMITH_API_KEY": "test-key", "LANGSMITH_PROJECT": "test-project"},
    )
    def test_get_config_initialized(self, mock_client_class):
        """Test getting config when service is initialized."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        self.service.initialize()
        config = self.service.get_config()

        assert config is not None
        assert config.api_key == "test-key"
        assert config.project == "test-project"


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
        from packages.backend.components.observability_service import (
            observability_service as global_service,
        )

        service1 = ObservabilityService()
        service2 = ObservabilityService()

        assert global_service is service1
        assert global_service is service2
