"""
Integration tests for end-to-end tracing workflow functionality.

This module tests the complete tracing workflow including:
- Tracing decorators for AI operations
- Performance monitoring and metrics collection
- Custom trace tags for AI-specific operations
- End-to-end trace propagation and validation
"""

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from packages.backend.components.observability_service import (
    ObservabilityService,
    ObservabilityConfig
)


class TestTracingWorkflowIntegration:
    """Integration tests for tracing workflow functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock observability configuration."""
        return ObservabilityConfig(
            api_key="test_api_key",
            project="test_project",
            endpoint="https://test.langsmith.com",
            tracing_enabled=True
        )

    @pytest.fixture
    def service(self, mock_config):
        """Create observability service with mock configuration."""
        service = ObservabilityService()
        service.reset_instance()

        with patch.object(service, 'load_config', return_value=mock_config):
            with patch.object(service, '_initialize_langsmith_client'):
                service.initialize()
                yield service

        service.reset_instance()

    def test_trace_ai_operation_decorator(self, service):
        """Test the AI operation tracing decorator."""
        @service.trace_ai_operation(operation_type="test_operation")
        def sample_ai_function(param1: str, param2: int = 42):
            time.sleep(0.01)  # Simulate some processing time
            return f"processed_{param1}_{param2}"

        with patch.object(service, '_add_performance_metrics') as mock_perf:
            with patch.object(service, '_add_result_metadata') as mock_result:
                result = sample_ai_function("test", param2=123)

                assert result == "processed_test_123"
                mock_perf.assert_called_once()
                mock_result.assert_called_once()

    def test_trace_llm_call_decorator(self, service):
        """Test the LLM call tracing decorator."""
        @service.trace_llm_call_decorator(model_name="gpt-4", include_prompt=True)
        def mock_llm_call(prompt: str, model: str = "gpt-4"):
            time.sleep(0.01)
            return f"Response to: {prompt}"

        with patch.object(service, 'trace_llm_response') as mock_response:
            result = mock_llm_call("Test prompt", model="gpt-4")

            assert result == "Response to: Test prompt"
            mock_response.assert_called_once()

    def test_trace_ai_workflow_decorator(self, service):
        """Test the AI workflow tracing decorator."""
        @service.trace_ai_workflow_decorator(workflow_type="narrative_generation")
        def generate_narrative(topic: str):
            time.sleep(0.02)
            return f"Narrative about {topic}"

        result = generate_narrative("dragons")

        assert result == "Narrative about dragons"

    def test_performance_metrics_collection(self, service):
        """Test performance metrics collection."""
        with patch.object(service, '_add_performance_metrics') as mock_perf:
            @service.trace_ai_operation(operation_type="performance_test")
            def slow_operation():
                time.sleep(0.05)
                return "completed"

            result = slow_operation()

            assert result == "completed"
            mock_perf.assert_called_once()
            # Verify duration was passed (should be ~0.05 seconds)
            call_args = mock_perf.call_args[0]
            assert len(call_args) >= 2  # trace_id and duration
            duration = call_args[1]  # Second argument should be duration
            assert 0.04 <= duration <= 0.1  # Allow some variance

    def test_custom_trace_tags(self, service):
        """Test custom trace tags functionality."""
        with patch.object(service, 'add_custom_trace_tags') as mock_tags:
            tags = service.create_ai_trace_tags(
                operation_type="llm_call",
                model_name="gpt-4",
                provider="openai",
                prompt_tokens=150,
                response_tokens=75
            )

            expected_keys = {
                "ai_operation", "operation_type", "ai_service",
                "llm_model", "llm_provider", "prompt_tokens", "response_tokens"
            }
            assert expected_keys.issubset(tags.keys())
            assert tags["operation_type"] == "llm_call"
            assert tags["llm_model"] == "gpt-4"

    def test_trace_error_handling(self, service):
        """Test error handling in traced operations."""
        @service.trace_ai_operation(operation_type="error_test")
        def failing_operation():
            time.sleep(0.01)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_operation()

    def test_nested_trace_operations(self, service):
        """Test nested tracing operations."""
        @service.trace_ai_operation(operation_type="outer_operation")
        def outer_operation():
            time.sleep(0.01)

            @service.trace_ai_operation(operation_type="inner_operation")
            def inner_operation():
                time.sleep(0.01)
                return "inner_result"

            inner_result = inner_operation()
            return f"outer_result_{inner_result}"

        result = outer_operation()
        assert result == "outer_result_inner_result"

    def test_trace_context_propagation(self, service):
        """Test trace context propagation across operations."""
        trace_context = {}

        @service.trace_ai_operation(operation_type="context_test")
        def operation_with_context():
            # Simulate storing context for verification
            trace_context['executed'] = True
            return "context_result"

        result = operation_with_context()
        assert result == "context_result"
        assert trace_context.get('executed') is True

    def test_performance_metrics_api(self, service):
        """Test performance metrics retrieval API."""
        metrics = service.get_performance_metrics(operation_type="test_operation")

        assert isinstance(metrics, dict)
        assert "operation_type" in metrics
        assert "time_window_seconds" in metrics
        assert metrics["operation_type"] == "test_operation"

    def test_ai_specific_trace_tags_creation(self, service):
        """Test creation of AI-specific trace tags for different operation types."""
        # Test LLM call tags
        llm_tags = service.create_ai_trace_tags(
            operation_type="llm_call",
            model_name="gpt-4",
            provider="openai",
            temperature=0.7
        )
        assert llm_tags["operation_type"] == "llm_call"
        assert llm_tags["llm_model"] == "gpt-4"
        assert llm_tags["temperature"] == 0.7

        # Test AI workflow tags
        workflow_tags = service.create_ai_trace_tags(
            operation_type="ai_workflow",
            stage="generation",
            step="narrative_creation",
            data_size=1024
        )
        assert workflow_tags["operation_type"] == "ai_workflow"
        assert workflow_tags["workflow_stage"] == "generation"

        # Test embedding tags
        embedding_tags = service.create_ai_trace_tags(
            operation_type="embedding",
            model_name="text-embedding-ada-002",
            dimension=1536,
            text_length=512
        )
        assert embedding_tags["operation_type"] == "embedding"
        assert embedding_tags["embedding_dimension"] == 1536

    def test_decorator_with_various_argument_types(self, service):
        """Test tracing decorators with various argument types."""
        @service.trace_ai_operation(operation_type="args_test", include_args=True)
        def function_with_various_args(
            required_arg: str,
            optional_arg: int = 42,
            *args,
            **kwargs
        ):
            return f"{required_arg}_{optional_arg}_{len(args)}_{len(kwargs)}"

        result = function_with_various_args(
            "test", 123, "extra1", "extra2", kwarg1="value1", kwarg2="value2"
        )
        assert result == "test_123_2_2"

    def test_decorator_result_inclusion(self, service):
        """Test including function results in trace metadata."""
        @service.trace_ai_operation(operation_type="result_test", include_result=True)
        def function_with_result():
            return {"status": "success", "data": [1, 2, 3, 4, 5]}

        with patch.object(service, '_add_result_metadata') as mock_result:
            result = function_with_result()

            assert result["status"] == "success"
            mock_result.assert_called_once()
            call_args = mock_result.call_args[0]
            assert call_args[1] == result  # Second argument should be the result

    def test_end_to_end_trace_workflow(self, service):
        """Test complete end-to-end tracing workflow."""
        execution_log = []

        @service.trace_ai_workflow_decorator(workflow_type="e2e_test")
        def complex_ai_workflow(input_data: dict):
            execution_log.append("workflow_started")

            # Simulate multiple AI operations within workflow
            @service.trace_ai_operation(operation_type="data_preprocessing")
            def preprocess_data(data):
                execution_log.append("preprocessing")
                time.sleep(0.01)
                return data.upper()

            @service.trace_llm_call_decorator(model_name="test-model")
            def generate_content(processed_data):
                execution_log.append("content_generation")
                time.sleep(0.02)
                return f"Generated content from: {processed_data}"

            processed = preprocess_data(input_data["text"])
            content = generate_content(processed)

            execution_log.append("workflow_completed")
            return {"processed": processed, "content": content}

        input_data = {"text": "hello world", "metadata": {"source": "test"}}
        result = complex_ai_workflow(input_data)

        # Verify execution flow
        expected_log = [
            "workflow_started",
            "preprocessing",
            "content_generation",
            "workflow_completed"
        ]
        assert execution_log == expected_log

        # Verify result structure
        assert "processed" in result
        assert "content" in result
        assert result["processed"] == "HELLO WORLD"
        assert "Generated content from: HELLO WORLD" in result["content"]


class TestTracingErrorScenarios:
    """Test error scenarios in tracing workflow."""

    def test_uninitialized_service_decorators(self):
        """Test decorators when service is not initialized."""
        service = ObservabilityService()
        service.reset_instance()

        @service.trace_ai_operation(operation_type="uninitialized_test")
        def test_function():
            return "test_result"

        # Should work without tracing when service is not initialized
        result = test_function()
        assert result == "test_result"

        service.reset_instance()

    def test_decorator_with_exception_propagation(self, service):
        """Test that exceptions are properly propagated through decorators."""
        @service.trace_ai_operation(operation_type="exception_test")
        def function_that_raises():
            raise RuntimeError("Test exception")

        with pytest.raises(RuntimeError, match="Test exception"):
            function_that_raises()

    def test_performance_metrics_with_exceptions(self, service):
        """Test performance metrics are still collected even when operations fail."""
        with patch.object(service, '_add_performance_metrics') as mock_perf:
            @service.trace_ai_operation(operation_type="failing_performance_test")
            def failing_function():
                time.sleep(0.01)
                raise Exception("Performance test failure")

            with pytest.raises(Exception):
                failing_function()

            # Performance metrics should still be called
            mock_perf.assert_called_once()