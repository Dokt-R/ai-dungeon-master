"""
Integration tests for the observability service component.

These tests verify that the observability service integrates correctly
with LangSmith and provides proper tracing functionality for LLM operations.
"""

import os
from unittest.mock import Mock, patch

import pytest

from packages.backend.components.observability_service import (
    ConfigurationError,
    ObservabilityService,
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


# Note: PYTEST_CURRENT_TEST environment variable is set by pytest automatically
# We don't need to set it manually as it's available during test execution


class TestObservabilityServiceIntegration:
    """Integration tests for ObservabilityService with external dependencies."""

    def setup_method(self):
        """Reset singleton instance before each test."""
        # Set environment variable to indicate this is an integration test for performance optimization
        ObservabilityService.reset_instance()

    def teardown_method(self):
        """Clean up after each test."""
        ObservabilityService.reset_instance()

        # Clean up any environment variables that might persist
        import os

        env_vars_to_clean = [
            "LANGSMITH_API_KEY",
            "LANGSMITH_PROJECT",
            "LANGSMITH_ENDPOINT",
            "LANGSMITH_TRACING",
        ]
        for var in env_vars_to_clean:
            if var in os.environ:
                del os.environ[var]

    def test_successful_initialization_with_valid_config(self):
        """Test successful initialization with valid environment variables."""
        with patch.dict(
            os.environ,
            {
                "LANGSMITH_API_KEY": "ls__test_key_12345",
                "LANGSMITH_PROJECT": "test-project",
                "LANGSMITH_ENDPOINT": "https://api.smith.langchain.com",
            },
        ):
            service = ObservabilityService()

            # Should initialize successfully
            result = service.initialize()
            assert result is True
            assert service.is_initialized() is True

            # Check configuration
            config = service.get_config()
            assert config is not None
            assert config.api_key == "ls__test_key_12345"
            assert config.project == "test-project"
            assert config.endpoint == "https://api.smith.langchain.com"

    def test_initialization_failure_with_invalid_config(self):
        """Test initialization failure with missing API key."""
        with patch.dict(os.environ, {}, clear=True):
            service = ObservabilityService()

            # Should fail to initialize without API key
            result = service.initialize()
            assert result is False
            assert service.is_initialized() is False

    def test_health_status_when_initialized(self):
        """Test health status when service is properly initialized."""
        with patch.dict(
            os.environ,
            {
                "LANGSMITH_API_KEY": "ls__test_key_12345",
                "LANGSMITH_PROJECT": "test-project",
                "LANGSMITH_TRACING": "true",
            },
        ):
            service = ObservabilityService()
            service.initialize()

            health_status = service.get_health_status()

            assert health_status["status"] == "healthy"
            assert health_status["provider"] == "langsmith"
            assert health_status["project"] == "test-project"
            assert health_status["tracing_enabled"] is True

    def test_health_status_when_not_initialized(self):
        """Test health status when service is not initialized."""
        service = ObservabilityService()

        health_status = service.get_health_status()

        assert health_status["status"] == "unhealthy"
        assert health_status["provider"] == "langsmith"
        assert health_status["error"] == "not_initialized"

    @patch("langsmith.Client")
    def test_langsmith_client_creation(self, mock_client_class):
        """Test that LangSmith client is created correctly."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        with patch.dict(
            os.environ,
            {
                "LANGSMITH_API_KEY": "ls__test_key_12345",
                "LANGSMITH_PROJECT": "test-project",
                "LANGSMITH_TRACING": "true",
            },
        ):
            service = ObservabilityService()
            service.initialize()

            # Verify LangSmith client was created
            mock_client_class.assert_called_once()

            # Verify environment variables were set
            assert os.environ.get("LANGSMITH_API_KEY") == "ls__test_key_12345"
            assert os.environ.get("LANGSMITH_PROJECT") == "test-project"

    def test_trace_operation_integration(self):
        """Test trace operation with LangSmith integration."""
        with patch.dict(
            os.environ,
            {
                "LANGSMITH_API_KEY": "ls__test_key_12345",
                "LANGSMITH_PROJECT": "test-project",
                "LANGSMITH_TRACING": "true",
            },
        ):
            with patch("langsmith.traceable") as mock_traceable:
                # Setup mock traceable decorator to properly wrap functions
                def mock_decorator(*args, **kwargs):
                    def wrapper(func):
                        # Return a function that when called, executes the original function
                        def wrapped_func():
                            return func()

                        return wrapped_func

                    return wrapper

                mock_traceable.side_effect = mock_decorator

                service = ObservabilityService()
                service.initialize()

                # Test tracing operation
                with service.trace_operation(
                    operation_name="test_operation",
                    operation_type="integration_test",
                    test_param="test_value",
                ) as trace_id:
                    assert trace_id is not None
                    assert isinstance(trace_id, str)
                    assert "test_operation" in trace_id

                # Verify traceable was called with correct parameters
                mock_traceable.assert_called_once()
                call_args = mock_traceable.call_args
                assert call_args[1]["name"] == "test_operation"
                assert call_args[1]["project_name"] == "test-project"
                assert (
                    "operation_type" in call_args[1]["tags"]
                )  # tags contain parameter keys, not values
                assert "test_param" in call_args[1]["tags"]

    def test_llm_call_tracing_integration(self):
        """Test LLM call tracing with proper metadata."""
        with patch.dict(
            os.environ,
            {
                "LANGSMITH_API_KEY": "ls__test_key_12345",
                "LANGSMITH_PROJECT": "test-project",
                "LANGSMITH_TRACING": "true",
            },
        ):
            with patch("langsmith.traceable") as mock_traceable:
                # Setup mock traceable decorator to properly wrap functions
                def mock_decorator(*args, **kwargs):
                    def wrapper(func):
                        # Return a function that when called, executes the original function
                        def wrapped_func():
                            return func()

                        return wrapped_func

                    return wrapper

                mock_traceable.side_effect = mock_decorator

                service = ObservabilityService()
                service.initialize()

                # Test LLM call tracing
                with service.trace_llm_call(
                    model_name="gpt-5-nano",
                    prompt="Test prompt for LLM",
                    temperature=1,
                    max_tokens=100,
                ) as trace_id:
                    assert trace_id is not None
                    assert "llm_call_gpt-5-nano" in trace_id

                # Verify traceable was called for LLM call
                mock_traceable.assert_called_once()
                call_args = mock_traceable.call_args
                assert "llm_call_gpt-5-nano" in call_args[1]["name"]
                assert "llm_call" in call_args[1]["tags"]
                assert "gpt-5-nano" in call_args[1]["tags"]

    def test_ai_workflow_tracing_integration(self):
        """Test AI workflow tracing with workflow-specific metadata."""
        with patch.dict(
            os.environ,
            {
                "LANGSMITH_API_KEY": "ls__test_key_12345",
                "LANGSMITH_PROJECT": "test-project",
                "LANGSMITH_TRACING": "true",
            },
        ):
            with patch("langsmith.traceable") as mock_traceable:
                # Setup mock traceable decorator to properly wrap functions
                def mock_decorator(*args, **kwargs):
                    def wrapper(func):
                        # Return a function that when called, executes the original function
                        def wrapped_func():
                            return func()

                        return wrapped_func

                    return wrapper

                mock_traceable.side_effect = mock_decorator

                service = ObservabilityService()
                service.initialize()

                # Test AI workflow tracing
                with service.trace_ai_workflow(
                    workflow_name="narrative_generation",
                    workflow_type="story_creation",
                    user_id="user123",
                    session_id="session456",
                ) as trace_id:
                    assert trace_id is not None
                    assert "ai_workflow_narrative_generation" in trace_id

                # Verify traceable was called for AI workflow
                mock_traceable.assert_called_once()
                call_args = mock_traceable.call_args
                assert "ai_workflow_narrative_generation" in call_args[1]["name"]
                assert "ai_workflow" in call_args[1]["tags"]
                assert "story_creation" in call_args[1]["tags"]

    def test_llm_response_tracing(self):
        """Test adding LLM response data to traces."""
        with patch.dict(
            os.environ,
            {
                "LANGSMITH_API_KEY": "ls__test_key_12345",
                "LANGSMITH_PROJECT": "test-project",
                "LANGSMITH_TRACING": "true",  # Enable tracing for this test
            },
        ):
            service = ObservabilityService()
            service.initialize()

            # Test tracing LLM response
            trace_id = "test-response-trace"
            response = "This is a test response from the LLM"
            model_name = "gpt-5-nano"

            # Should not raise exception
            service.trace_llm_response(
                trace_id=trace_id,
                response=response,
                model_name=model_name,
                response_length=len(response),
                tokens_used=150,
            )

    def test_decision_point_tracing(self):
        """Test tracing AI decision points."""
        with patch.dict(
            os.environ,
            {
                "LANGSMITH_API_KEY": "ls__test_key_12345",
                "LANGSMITH_PROJECT": "test-project",
                "LANGSMITH_TRACING": "true",  # Enable tracing for this test
            },
        ):
            service = ObservabilityService()
            service.initialize()

            # Test tracing decision point
            trace_id = "test-decision-trace"
            options = ["option1", "option2", "option3"]
            chosen_option = "option2"
            reasoning = "Option2 provides the best balance of quality and performance"

            # Should not raise exception
            service.trace_decision_point(
                trace_id=trace_id,
                decision_type="model_selection",
                options=options,
                chosen_option=chosen_option,
                reasoning=reasoning,
                confidence_score=0.85,
            )

    def test_tracing_fallback_when_langsmith_unavailable(self):
        """Test that tracing falls back gracefully when LangSmith is unavailable."""
        with patch.dict(
            os.environ,
            {
                "LANGSMITH_API_KEY": "ls__test_key_12345",
                "LANGSMITH_PROJECT": "test-project",
                "LANGSMITH_TRACING": "true",
            },
        ):
            # Mock LangSmith import failure
            with patch(
                "langsmith.traceable",
                side_effect=ImportError("LangSmith not available"),
            ):
                service = ObservabilityService()
                service.initialize()

                # Test that operations still work with fallback
                with service.trace_operation("fallback_test_operation") as trace_id:
                    assert trace_id is not None
                    # Should return a basic trace ID even without LangSmith

                with service.trace_llm_call("gpt-5-nano", "test prompt") as trace_id:
                    assert trace_id is not None

    def test_configuration_validation(self):
        """Test configuration validation with various inputs."""
        # Test with empty API key
        with patch.dict(os.environ, {"LANGSMITH_API_KEY": ""}):
            service = ObservabilityService()
            with pytest.raises(
                ConfigurationError, match="LANGSMITH_API_KEY cannot be empty"
            ):
                service.load_config()

        # Test with empty project name
        with patch.dict(
            os.environ, {"LANGSMITH_API_KEY": "test-key", "LANGSMITH_PROJECT": ""}
        ):
            service = ObservabilityService()
            with pytest.raises(
                ConfigurationError, match="LANGSMITH_PROJECT cannot be empty"
            ):
                service.load_config()

        # Test successful configuration
        with patch.dict(
            os.environ,
            {
                "LANGSMITH_API_KEY": "valid-key",
                "LANGSMITH_PROJECT": "valid-project",
                "LANGSMITH_ENDPOINT": "",  # Explicitly set to empty to override any defaults
            },
        ):
            service = ObservabilityService()
            config = service.load_config()
            assert config.api_key == "valid-key"
            assert config.project == "valid-project"
            assert config.endpoint is None  # Not set

    def test_singleton_pattern(self):
        """Test that ObservabilityService follows singleton pattern."""
        with patch.dict(
            os.environ,
            {"LANGSMITH_API_KEY": "test-key", "LANGSMITH_PROJECT": "test-project"},
        ):
            service1 = ObservabilityService()
            service2 = ObservabilityService()

            # Should be the same instance
            assert service1 is service2

            # Should share initialization state
            service1.initialize()
            assert service2.is_initialized() is True

    def test_tracing_disabled_by_default_integration(self):
        """Test that tracing is disabled by default in integration tests."""
        with patch.dict(
            os.environ,
            {
                "LANGSMITH_API_KEY": "ls__test_key_12345",
                "LANGSMITH_PROJECT": "test-project",
                # Note: LANGSMITH_TRACING is not set, so it should default to disabled
            },
        ):
            service = ObservabilityService()
            service.initialize()

            # All tracing methods should return None when disabled
            with service.trace_operation("test_operation") as trace_id:
                assert trace_id is None

            with service.trace_llm_call("test-model", "test prompt") as trace_id:
                assert trace_id is None

            with service.trace_ai_workflow("test-workflow") as trace_id:
                assert trace_id is None
