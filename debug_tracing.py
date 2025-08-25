#!/usr/bin/env python3
"""
Debug script to investigate tracing workflow issues.
"""

import time
import os
from unittest.mock import patch, MagicMock

# Add the packages directory to Python path
import sys
sys.path.insert(0, 'packages')

from packages.backend.components.observability_service import ObservabilityService, ObservabilityConfig

def debug_service_initialization():
    """Debug service initialization and state."""
    print("=== DEBUG: Service Initialization ===")

    # Reset any existing instance
    ObservabilityService.reset_instance()

    # Create service with test config
    config = ObservabilityConfig(
        api_key="test_api_key",
        project="test_project",
        endpoint="https://test.langsmith.com",
        tracing_enabled=True,
    )

    service = ObservabilityService()

    print(f"Service created: {service}")
    print(f"Initial _is_initialized: {getattr(service, '_is_initialized', 'Not set')}")

    # Mock the config loading
    with patch.object(service, 'load_config', return_value=config):
        with patch.object(service, '_initialize_langsmith_client'):
            success = service.initialize()
            print(f"Initialization success: {success}")
            print(f"After init _is_initialized: {getattr(service, '_is_initialized', 'Not set')}")
            print(f"Config: {service._config}")
            print(f"Circuit breaker state: {service.get_circuit_breaker_state()}")
            print(f"LangSmith client: {service._langsmith_client}")

    return service

def debug_decorator_execution(service):
    """Debug decorator execution with detailed logging."""
    print("\n=== DEBUG: Decorator Execution ===")

    # Test the AI operation decorator
    @service.trace_ai_operation(operation_type="debug_test")
    def test_function(param1: str, param2: int = 42):
        print("Inside test_function")
        time.sleep(0.01)  # Simulate some processing time
        return f"processed_{param1}_{param2}"

    # Mock the methods we're testing
    with patch.object(service, '_add_performance_metrics') as mock_perf:
        with patch.object(service, '_add_result_metadata') as mock_result:
            print("Starting decorated function call...")
            result = test_function("test", param2=123)
            print(f"Function result: {result}")
            print(f"_add_performance_metrics called: {mock_perf.called}")
            print(f"_add_result_metadata called: {mock_result.called}")

            if mock_perf.called:
                print(f"_add_performance_metrics call args: {mock_perf.call_args}")
            if mock_result.called:
                print(f"_add_result_metadata call args: {mock_result.call_args}")

    # Test LLM call decorator
    @service.trace_llm_call_decorator(model_name="gpt-4", include_prompt=True)
    def mock_llm_call(prompt: str, model: str = "gpt-4"):
        print("Inside mock_llm_call")
        time.sleep(0.01)
        return f"Response to: {prompt}"

    with patch.object(service, 'trace_llm_response') as mock_response:
        print("Starting LLM decorated function call...")
        result = mock_llm_call("Test prompt", model="gpt-4")
        print(f"LLM Function result: {result}")
        print(f"trace_llm_response called: {mock_response.called}")

        if mock_response.called:
            print(f"trace_llm_response call args: {mock_response.call_args}")

def debug_conditional_logic(service):
    """Debug the conditional logic in decorators."""
    print("\n=== DEBUG: Conditional Logic ===")

    print(f"Service initialized: {service._is_initialized}")
    print(f"Circuit breaker open: {service.is_circuit_breaker_open()}")
    print(f"LangSmith client available: {service._langsmith_client is not None}")

    # Check if tracing would be disabled
    if not service._is_initialized:
        print("❌ Tracing disabled: service not initialized")
    elif service.is_circuit_breaker_open():
        print("❌ Tracing disabled: circuit breaker open")
    elif not service._langsmith_client:
        print("❌ Tracing disabled: no LangSmith client")
    else:
        print("✅ Tracing should be enabled")

if __name__ == "__main__":
    print("Starting tracing workflow debug...")

    service = debug_service_initialization()
    debug_conditional_logic(service)
    debug_decorator_execution(service)

    print("\nDebug complete.")