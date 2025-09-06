"""
Safe Observability Wrappers for AI Operations

This module provides robust wrapper functions that ensure AI operations
continue working even when observability services are unavailable or failing.

Features:
- Circuit breaker pattern to prevent cascade failures
- Graceful degradation when monitoring is unavailable
- Automatic fallback to basic logging
- Service health monitoring and recovery detection
- Performance isolation (observability failures don't impact business logic)
"""

import asyncio
from functools import wraps
from typing import Any, Callable, Dict

from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


class SafeObservabilityWrapper:
    """Safe observability wrapper with circuit breaker pattern."""

    def __init__(self, service_name: str = "action_resolution"):
        self.service_name = service_name
        self.logger = get_logger(f"{__name__}.{service_name}")

    def trace_operation_safe(
        self,
        operation_name: str,
        operation_func: Callable,
        *args,
        default_result: Any = None,
        **kwargs,
    ) -> Any:
        """
        Safely execute operation with tracing, falling back gracefully.

        Args:
            operation_name: Name of the operation for tracing
            operation_func: Function to execute with tracing
            default_result: Value to return if observability fails
            *args: Arguments for the operation function
            **kwargs: Keyword arguments for the operation function (and tracing)

        Returns:
            Result of operation_func or default_result if observability fails
        """

        # Check service health first
        if not observability_service.is_initialized():
            self.logger.debug(
                f"Observability not initialized - executing {operation_name} without tracing"
            )
            return operation_func(*args, **kwargs)

        if observability_service.is_circuit_breaker_open():
            self.logger.warning(
                f"Observability circuit breaker open - executing {operation_name} without tracing"
            )
            return operation_func(*args, **kwargs)

        try:
            # Extract tracing parameters from kwargs
            trace_tags = kwargs.pop("trace_tags", {})
            correlation_id = kwargs.get("correlation_id", "none")

            # Attempt traced execution
            with observability_service.trace_operation(
                operation_name=operation_name,
                correlation_id=correlation_id,
                **trace_tags,
            ) as trace_id:
                self.logger.debug(
                    "Traced operation started",
                    operation=operation_name,
                    trace_id=trace_id,
                )
                result = operation_func(*args, **kwargs)

                # Add custom metadata if result is available
                if isinstance(result, dict) and "trace_id" not in result:
                    result["trace_id"] = trace_id

                return result

        except Exception as e:
            # Log the observability failure but continue with business logic
            self.logger.warning(f"Observability failed for {operation_name}: {e}")

            # Try to notify about circuit breaker opening
            try:
                if (
                    hasattr(observability_service, "is_circuit_breaker_open")
                    and observability_service.is_circuit_breaker_open()
                ):
                    self.logger.info(
                        "Circuit breaker opened - falling back to basic operation"
                    )
            except Exception:
                pass  # Ignore further observability failures

            # Execute operation without tracing
            try:
                result = operation_func(*args, **kwargs)
                return result if result is not None else default_result
            except Exception as op_error:
                self.logger.error(
                    f"Operation failed after observability error: {op_error}",
                    operation=operation_name,
                )
                return default_result

    async def trace_async_operation_safe(
        self,
        operation_name: str,
        operation_func: Callable,
        *args,
        default_result: Any = None,
        **kwargs,
    ) -> Any:
        """
        Safely execute async operation with tracing.

        Args:
            operation_name: Name of the operation for tracing
            operation_func: Async function to execute with tracing
            default_result: Value to return if observability fails
            *args: Arguments for the operation function

        Returns:
            Result of operation_func or default_result
        """

        # Check service health first
        if not observability_service.is_initialized():
            self.logger.debug(
                f"Observability not initialized - executing {operation_name} without tracing"
            )
            return await operation_func(*args, **kwargs)

        if observability_service.is_circuit_breaker_open():
            self.logger.warning(
                f"Observability circuit breaker open - executing {operation_name} without tracing"
            )
            return await operation_func(*args, **kwargs)

        try:
            # Extract tracing parameters
            trace_tags = kwargs.pop("trace_tags", {})
            correlation_id = kwargs.get("correlation_id", "none")

            # Attempt traced execution
            with observability_service.trace_operation(
                operation_name=operation_name,
                correlation_id=correlation_id,
                **trace_tags,
            ) as trace_id:
                self.logger.debug(
                    "Traced async operation started",
                    operation=operation_name,
                    trace_id=trace_id,
                )
                result = await operation_func(*args, **kwargs)

                # Add custom metadata
                if isinstance(result, dict) and "trace_id" not in result:
                    result["trace_id"] = trace_id

                return result

        except Exception as e:
            self.logger.warning(f"Observability failed for async {operation_name}: {e}")

            # Execute operation without tracing
            try:
                result = await operation_func(*args, **kwargs)
                return result if result is not None else default_result
            except Exception as op_error:
                self.logger.error(
                    f"Async operation failed after observability error: {op_error}",
                    operation=operation_name,
                )
                return default_result

    def trace_llm_call_safe(
        self,
        model_name: str,
        prompt_func: Callable,
        *args,
        default_result: str = "",
        **kwargs,
    ) -> str:
        """
        Safely execute LLM call with tracing.

        Args:
            model_name: Name of the LLM model
            prompt_func: Function that makes the LLM call
            default_result: Default response if tracing fails
            *args: Arguments for prompt_func

        Returns:
            LLM response or fallback
        """

        if (
            not observability_service.is_initialized()
            or observability_service.is_circuit_breaker_open()
        ):
            try:
                return prompt_func(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"LLM call failed: {e}")
                return default_result

        try:
            correlation_id = kwargs.get("correlation_id", "none")

            with observability_service.trace_llm_call(
                model_name=model_name,
                prompt="",  # Could optionally extract if needed
                correlation_id=correlation_id,
            ) as trace_id:
                result = prompt_func(*args, **kwargs)
                self.logger.debug(
                    "LLM call traced", model=model_name, trace_id=trace_id
                )
                return result

        except Exception as e:
            self.logger.warning(f"LLM observability failed: {e}")
            try:
                return prompt_func(*args, **kwargs)
            except Exception as op_error:
                self.logger.error(
                    f"LLM call failed after observability error: {op_error}"
                )
                return default_result

    def create_resilient_wrapper(
        self, operation_name: str, default_result: Any = None, is_async: bool = False
    ) -> Callable:
        """
        Create a resilient wrapper decorator for functions.

        Args:
            operation_name: Name for the traced operation
            default_result: Default return value on failure
            is_async: Whether the function is async

        Returns:
            Decorator function
        """

        def decorator(func):
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self.trace_operation_safe(
                    operation_name, func, *args, default_result=default_result, **kwargs
                )

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.trace_async_operation_safe(
                    operation_name, func, *args, default_result=default_result, **kwargs
                )

            return async_wrapper if is_async else sync_wrapper

        return decorator


# Global instance
safe_observability = SafeObservabilityWrapper("action_resolution")


# Convenience functions for common patterns
def safe_trace_operation(
    operation_name: str,
    operation_func: Callable,
    default_result: Any = None,
    **trace_tags,
):
    """
    Convenience function for safe operation tracing.

    Usage:
        result = safe_trace_operation("my_operation", my_function, arg1, arg2)
    """
    return safe_observability.trace_operation_safe(
        operation_name,
        operation_func,
        default_result=default_result,
        trace_tags=trace_tags,
    )


async def safe_trace_async_operation(
    operation_name: str,
    operation_func: Callable,
    default_result: Any = None,
    **trace_tags,
):
    """
    Convenience function for safe async operation tracing.

    Usage:
        result = await safe_trace_async_operation("my_async_operation", my_async_function, args...)
    """
    return await safe_observability.trace_async_operation_safe(
        operation_name,
        operation_func,
        default_result=default_result,
        trace_tags=trace_tags,
    )


def resilient_trace(
    operation_name: str, default_result: Any = None, is_async: bool = False
):
    """
    Decorator for making any function observability-resilient.

    Usage:
        @resilient_trace("my_operation")
        def my_function():
            return do_something()

        @resilient_trace("my_async_operation", is_async=True)
        async def my_async_function():
            return await do_something_async()
    """
    if is_async:

        def async_decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await safe_observability.trace_async_operation_safe(
                    operation_name, func, default_result=default_result, *args, **kwargs
                )

            return wrapper

        return async_decorator
    else:

        def sync_decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return safe_observability.trace_operation_safe(
                    operation_name, func, default_result=default_result, *args, **kwargs
                )

            return wrapper

        return sync_decorator


def get_service_health() -> Dict[str, Any]:
    """
    Get comprehensive health status of observability services.

    Returns:
        Dictionary with health information
    """
    health = {
        "observability_initialized": observability_service.is_initialized(),
        "circuit_breaker_open": False,
        "service_name": "action_resolution_safe_observability",
    }

    try:
        health["circuit_breaker_open"] = observability_service.is_circuit_breaker_open()
    except AttributeError:
        pass  # Circuit breaker may not be implemented

    try:
        health["full_health"] = observability_service.get_health_status()
    except AttributeError:
        pass  # get_health_status may not be available

    return health


# Example usage function for testing
async def example_usage():
    """Demonstrate safe observability wrappers"""
    print("Testing Safe Observability Wrappers")

    # Example sync operation
    def risky_operation():
        return {"result": "success", "data": [1, 2, 3]}

    # Safe tracing
    result = safe_trace_operation(
        "example_sync_operation",
        risky_operation,
        trace_tags={"service": "demo", "operation_type": "test"},
    )
    print(f"Sync result: {result}")

    # Example async operation
    async def risky_async_operation():
        await asyncio.sleep(0.1)
        return {"async_result": "success", "processing_time": 0.1}

    # Safe async tracing
    async_result = await safe_trace_async_operation(
        "example_async_operation",
        risky_async_operation,
        trace_tags={"service": "demo", "operation_type": "test"},
    )
    print(f"Async result: {async_result}")

    # Health check
    health = get_service_health()
    print(f"Service health: {health}")


if __name__ == "__main__":
    asyncio.run(example_usage())
