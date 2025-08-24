"""
Unit tests for enhanced observability features.

This module tests the new observability features including:
- Configuration validation at startup
- Circuit breaker pattern for observability failures
- Correlation ID integration with logging infrastructure
- Dependency injection support for improved testability
"""

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from packages.backend.components.observability_service import (
    ObservabilityService,
    ObservabilityConfig,
    ConfigurationValidator,
    ConfigurationValidationResult,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    CircuitBreakerOpenException,
    ObservabilityServiceFactory,
    DependencyContainer,
)

os.environ['PYTEST_CURRENT_TEST'] = 'integration_test_for_performance'

class TestConfigurationValidation:
    """Test configuration validation features."""

    def test_configuration_validator_creation(self):
        """Test creating a configuration validator."""
        validator = ConfigurationValidator()
        assert validator is not None
        assert validator.validation_errors == []
        assert validator.validation_warnings == []
        assert validator.validation_recommendations == []

    def test_validate_valid_config(self):
        """Test validation of a valid configuration."""
        validator = ConfigurationValidator()
        config = ObservabilityConfig(
            api_key="ls__test_key_123",
            project="ai-dungeon-master",
            endpoint="https://api.langsmith.com",
            tracing_enabled=True
        )

        result = validator.validate_config(config)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'recommendations')

    def test_validate_invalid_api_key(self):
        """Test validation with invalid API key."""
        validator = ConfigurationValidator()

        # Test empty API key
        config = ObservabilityConfig(
            api_key="",
            project="test_project",
            endpoint=None,
            tracing_enabled=True
        )

        result = validator.validate_config(config)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("LANGSMITH_API_KEY" in error for error in result.errors)

    def test_validate_api_key_format(self):
        """Test API key format validation."""
        validator = ConfigurationValidator()

        # Test non-ls__ prefixed key
        config = ObservabilityConfig(
            api_key="invalid_key_format",
            project="test_project",
            endpoint=None,
            tracing_enabled=True
        )

        result = validator.validate_config(config)

        assert result.is_valid is True  # Should be valid but with warnings
        assert len(result.warnings) > 0
        assert any("ls__" in warning for warning in result.warnings)

    def test_validate_project_name(self):
        """Test project name validation."""
        validator = ConfigurationValidator()

        # Test empty project name
        config = ObservabilityConfig(
            api_key="ls__test_key",
            project="",
            endpoint=None,
            tracing_enabled=True
        )

        result = validator.validate_config(config)

        assert result.is_valid is False
        assert any("Project name" in error for error in result.errors)

    def test_validate_endpoint_url(self):
        """Test endpoint URL validation."""
        validator = ConfigurationValidator()

        # Test invalid URL
        config = ObservabilityConfig(
            api_key="ls__test_key",
            project="test_project",
            endpoint="not-a-valid-url",
            tracing_enabled=True
        )

        result = validator.validate_config(config)

        assert result.is_valid is False
        assert any("URL" in error for error in result.errors)

    def test_validate_environment_consistency(self):
        """Test environment variable consistency validation."""
        validator = ConfigurationValidator()

        with patch.dict(os.environ, {
            "LANGSMITH_API_KEY": "different_key",
            "LANGSMITH_PROJECT": "different_project"
        }):
            config = ObservabilityConfig(
                api_key="ls__test_key",
                project="test_project",
                endpoint=None,
                tracing_enabled=True
            )

            result = validator.validate_config(config)

            assert result.is_valid is True
            assert len(result.warnings) > 0
            assert any("differs from loaded configuration" in warning for warning in result.warnings)

    def test_security_best_practices(self):
        """Test security best practices validation."""
        validator = ConfigurationValidator()

        # Test localhost endpoint
        config = ObservabilityConfig(
            api_key="ls__test_key",
            project="test_project",
            endpoint="http://localhost:8080",
            tracing_enabled=True
        )

        result = validator.validate_config(config)

        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("localhost" in warning.lower() for warning in result.warnings)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_creation(self):
        """Test creating a circuit breaker."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config)

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.last_failure_time is None

    def test_circuit_breaker_success(self):
        """Test circuit breaker with successful operations."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config)

        def successful_operation():
            return "success"

        result = cb.call(successful_operation)
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_failure_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker(config)

        def failing_operation():
            raise ValueError("Test failure")

        # First failure
        with pytest.raises(ValueError):
            cb.call(failing_operation)
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 1

        # Second failure - should open circuit
        with pytest.raises(ValueError):
            cb.call(failing_operation)
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 2

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,  # Very short timeout for testing
            success_threshold=1   # Need only 1 success to fully recover
        )
        cb = CircuitBreaker(config)

        def failing_operation():
            raise ValueError("Test failure")

        def successful_operation():
            return "success"

        # Cause circuit to open
        with pytest.raises(ValueError):
            cb.call(failing_operation)
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)

        # Should transition to half-open and succeed
        result = cb.call(successful_operation)
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_half_open_failure(self):
        """Test circuit breaker returns to open on half-open failure."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=2
        )
        cb = CircuitBreaker(config)

        def failing_operation():
            raise ValueError("Test failure")

        def successful_operation():
            return "success"

        # Cause circuit to open
        with pytest.raises(ValueError):
            cb.call(failing_operation)
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)

        # Fail in half-open state
        with pytest.raises(ValueError):
            cb.call(failing_operation)
        assert cb.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_state_info(self):
        """Test circuit breaker state information."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config)

        state_info = cb.get_state()

        assert "state" in state_info
        assert "failure_count" in state_info
        assert "success_count" in state_info
        assert "last_failure_time" in state_info
        assert state_info["state"] == "closed"
        assert state_info["failure_count"] == 0

    def test_circuit_breaker_reset(self):
        """Test manual circuit breaker reset."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config)

        def failing_operation():
            raise ValueError("Test failure")

        # Cause failures and open circuit
        for _ in range(5):
            with pytest.raises(ValueError):
                cb.call(failing_operation)

        assert cb.state == CircuitBreakerState.OPEN

        # Reset circuit
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.last_failure_time is None


class TestDependencyInjection:
    """Test dependency injection features."""

    def test_observability_service_factory_creation(self):
        """Test creating services through factory."""
        config = ObservabilityConfig(
            api_key="ls__test_key",
            project="test_project",
            endpoint=None,
            tracing_enabled=True
        )

        with patch('packages.backend.components.observability_service.ObservabilityService.load_config') as mock_load:
            mock_load.return_value = config

            # Test service creation
            service = ObservabilityServiceFactory.create_service(config, initialize_on_create=False)
            assert service is not None
            assert service._config == config

    def test_test_service_factory(self):
        """Test creating test service through factory."""
        with patch('packages.backend.components.observability_service.ObservabilityService._initialize_langsmith_client'):
            service = ObservabilityServiceFactory.create_test_service(mock_langsmith=False)
            assert service is not None
            assert service._config.api_key == "test_api_key"
            assert service._config.project == "test_project"

    def test_disabled_service_factory(self):
        """Test creating disabled service through factory."""
        service = ObservabilityServiceFactory.create_disabled_service()
        assert service is not None
        assert service._config.api_key == "disabled"
        assert service._config.tracing_enabled is False

    def test_dependency_container(self):
        """Test dependency container functionality."""
        container = DependencyContainer()

        # Test registering services
        config = ObservabilityConfig(
            api_key="ls__test_key",
            project="test_project",
            endpoint=None,
            tracing_enabled=True
        )

        container.register_service("test_config", config)
        container.register_factory("test_service", lambda: "test_service_instance")

        # Test retrieving services
        retrieved_config = container.get_service("test_config")
        assert retrieved_config == config

        retrieved_service = container.get_service("test_service")
        assert retrieved_service == "test_service_instance"

        # Test missing service
        with pytest.raises(ValueError, match="Service 'missing' not registered"):
            container.get_service("missing")

    def test_service_interface_compatibility(self):
        """Test that service implements the expected interface."""
        from packages.backend.components.observability_service import ObservabilityServiceInterface

        service = ObservabilityService()

        # Check that service has methods from interface
        assert hasattr(service, 'initialize')
        assert hasattr(service, 'get_health_status')
        assert hasattr(service, 'is_initialized')
        assert hasattr(service, 'trace_operation')
        assert hasattr(service, 'trace_llm_call')
        assert hasattr(service, 'trace_ai_workflow')

        # Verify method signatures match interface expectations
        assert callable(service.initialize)
        assert callable(service.get_health_status)
        assert callable(service.is_initialized)
        assert callable(service.trace_operation)
        assert callable(service.trace_llm_call)
        assert callable(service.trace_ai_workflow)


class TestCorrelationIdIntegration:
    """Test correlation ID integration features."""

    @pytest.fixture
    def service(self):
        """Create observability service for testing."""
        service = ObservabilityService()
        service.reset_instance()
        return service

    def test_get_correlation_id_for_trace(self, service):
        """Test getting correlation ID for a trace."""
        trace_id = "test_trace_123"

        with patch('packages.backend.components.observability_service.get_correlation_id') as mock_get:
            mock_get.return_value = "test_correlation_id"

            correlation_id = service.get_correlation_id_for_trace(trace_id)
            assert correlation_id == "test_correlation_id"
            mock_get.assert_called_once()

    def test_create_trace_with_correlation(self, service):
        """Test creating trace with correlation ID."""
        with patch('packages.backend.components.observability_service.get_correlation_id') as mock_get:
            mock_get.return_value = "test_correlation_id"

            trace_id = service.create_trace_with_correlation(
                "test_operation",
                custom_tag="test_value"
            )

            assert trace_id.startswith("test_operation_")
            assert len(trace_id) > len("test_operation_")  # Should have random suffix

    def test_create_trace_without_correlation(self, service):
        """Test creating trace without correlation ID."""
        with patch('packages.backend.components.observability_service.get_correlation_id') as mock_get:
            mock_get.return_value = None

            trace_id = service.create_trace_with_correlation("test_operation")

            assert trace_id.startswith("test_operation_")
            assert len(trace_id) > len("test_operation_")


class TestEnhancedObservabilityService:
    """Test enhanced observability service features."""

    @pytest.fixture
    def service(self):
        """Create enhanced observability service for testing."""
        service = ObservabilityService()
        service.reset_instance()
        return service

    def test_configuration_validation_integration(self, service):
        """Test configuration validation integration."""
        config = ObservabilityConfig(
            api_key="ls__test_key",
            project="test_project",
            endpoint=None,
            tracing_enabled=True
        )

        with patch.object(service, 'load_config', return_value=config):
            result = service.validate_config_only()

            assert isinstance(result, ConfigurationValidationResult)
            assert hasattr(result, 'is_valid')
            assert hasattr(result, 'errors')
            assert hasattr(result, 'warnings')
            assert hasattr(result, 'recommendations')

    def test_circuit_breaker_state_methods(self, service):
        """Test circuit breaker state access methods."""
        # Initially should be None
        state = service.get_circuit_breaker_state()
        assert state is None

        is_open = service.is_circuit_breaker_open()
        assert is_open is False

    def test_circuit_breaker_reset_method(self, service):
        """Test circuit breaker reset functionality."""
        # Should not raise error even when not initialized
        service.reset_circuit_breaker()

    def test_health_status_with_enhancements(self, service):
        """Test enhanced health status information."""
        health_status = service.get_health_status()

        assert "correlation_id_support" in health_status
        assert "current_correlation_id" in health_status
        assert health_status["correlation_id_support"] == "enabled"

    def test_performance_metrics_api(self, service):
        """Test performance metrics API."""
        metrics = service.get_performance_metrics("test_operation")

        assert isinstance(metrics, dict)
        assert "operation_type" in metrics
        assert "time_window_seconds" in metrics

    def test_ai_trace_tags_creation(self, service):
        """Test AI-specific trace tags creation."""
        # Test different operation types
        llm_tags = service.create_ai_trace_tags("llm_call", model_name="gpt-4")
        assert llm_tags["operation_type"] == "llm_call"
        assert llm_tags["llm_model"] == "gpt-4"

        workflow_tags = service.create_ai_trace_tags("ai_workflow", stage="processing")
        assert workflow_tags["operation_type"] == "ai_workflow"
        assert workflow_tags["workflow_stage"] == "processing"

        # Test with custom tags
        custom_tags = service.create_ai_trace_tags("custom_op", custom_field="value")
        assert custom_tags["custom_field"] == "value"

    def test_trace_custom_tags_method(self, service):
        """Test custom trace tags addition."""
        trace_id = "test_trace_123"

        # Should not raise error even when not fully initialized
        service.add_custom_trace_tags(trace_id, {"test": "value"})


class TestIntegrationWithExistingFeatures:
    """Test integration between new features and existing functionality."""

    @pytest.fixture
    def service(self):
        """Create service for integration testing."""
        service = ObservabilityService()
        service.reset_instance()
        return service

    def test_validation_and_initialization_integration(self, service):
        """Test integration between validation and initialization."""
        config = ObservabilityConfig(
            api_key="ls__test_key",
            project="test_project",
            endpoint=None,
            tracing_enabled=True
        )

        with patch.object(service, 'load_config', return_value=config):
            with patch.object(service, '_initialize_langsmith_client'):
                # Initialize should trigger validation
                result = service.initialize()

                # Should have validation result after initialization
                validation_result = service.get_validation_result()
                assert validation_result is not None
                assert isinstance(validation_result, ConfigurationValidationResult)

    def test_circuit_breaker_health_integration(self, service):
        """Test circuit breaker integration with health status."""
        config = ObservabilityConfig(
            api_key="ls__test_key",
            project="test_project",
            endpoint=None,
            tracing_enabled=True
        )

        with patch.object(service, 'load_config', return_value=config):
            with patch.object(service, '_initialize_langsmith_client'):
                service.initialize()

                health_status = service.get_health_status()

                # Should include circuit breaker information
                assert "circuit_breaker" in health_status
                cb_state = health_status["circuit_breaker"]
                assert cb_state is not None
                assert "state" in cb_state

    def test_all_features_work_together(self, service):
        """Test that all enhanced features work together."""
        config = ObservabilityConfig(
            api_key="ls__test_key",
            project="test_project",
            endpoint=None,
            tracing_enabled=True
        )

        with patch.object(service, 'load_config', return_value=config):
            with patch.object(service, '_initialize_langsmith_client'):
                # Initialize with all features
                service.initialize()

                # Test that all methods are available and working
                assert service.is_initialized() is True
                assert service.get_validation_result() is not None
                assert service.get_circuit_breaker_state() is not None
                assert service.get_config() == config

                # Test health status includes all feature information
                health = service.get_health_status()
                assert "circuit_breaker" in health
                assert "correlation_id_support" in health
                assert "current_correlation_id" in health