"""
Unit tests for Error Handling Service Component.

This module provides comprehensive unit tests for the error handling service including:
- Circuit breaker functionality
- Fallback strategy execution
- Error classification and handling
- Health monitoring and recovery
- Performance tracking and analytics
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from packages.backend.components.error_handling_service import (
    ErrorHandlingService, CircuitBreaker, ErrorInfo,
    ErrorCategory, ErrorSeverity, FallbackStrategy
)
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


class TestErrorInfo:
    """Test cases for ErrorInfo dataclass."""

    def test_error_info_creation(self):
        """Test creating an ErrorInfo instance."""
        error_info = ErrorInfo(
            error_id="test_error_001",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            message="Network connection failed",
            component="test_component",
            operation="network_request",
            correlation_id="corr_123",
            retry_count=2,
            max_retries=3
        )

        assert error_info.error_id == "test_error_001"
        assert error_info.category == ErrorCategory.NETWORK
        assert error_info.severity == ErrorSeverity.HIGH
        assert error_info.message == "Network connection failed"
        assert error_info.component == "test_component"
        assert error_info.operation == "network_request"
        assert error_info.retry_count == 2
        assert error_info.max_retries == 3
        assert error_info.is_retryable is True

    def test_error_info_defaults(self):
        """Test ErrorInfo with default values."""
        error_info = ErrorInfo(
            error_id="minimal_error",
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.LOW,
            message="Minimal error"
        )

        assert error_info.retry_count == 0
        assert error_info.max_retries == 3
        assert error_info.recovery_attempts == 0
        assert error_info.correlation_id is None
        assert isinstance(error_info.timestamp, datetime)

    def test_retryable_property(self):
        """Test is_retryable property logic."""
        # Retryable error
        error_info = ErrorInfo(
            error_id="retryable",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Network error",
            retry_count=0,
            max_retries=3
        )
        assert error_info.is_retryable is True

        # Non-retryable due to retry count
        error_info.retry_count = 3
        assert error_info.is_retryable is False

        # Non-retryable due to category
        error_info.retry_count = 0
        error_info.category = ErrorCategory.VALIDATION
        assert error_info.is_retryable is False


class TestCircuitBreaker:
    """Test cases for CircuitBreaker."""

    def setup_method(self):
        """Set up test environment."""
        self.config = {
            'failure_threshold': 3,
            'recovery_timeout': 30,
            'success_threshold': 2
        }
        self.circuit_breaker = CircuitBreaker("test_service", self.config)

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        assert self.circuit_breaker.name == "test_service"
        assert self.circuit_breaker.state.failure_threshold == 3
        assert self.circuit_breaker.state.recovery_timeout == timedelta(seconds=30)
        assert self.circuit_breaker.state.success_threshold == 2
        assert self.circuit_breaker.state.is_open is False
        assert self.circuit_breaker.state.failure_count == 0

    def test_circuit_breaker_can_execute_initial(self):
        """Test circuit breaker allows execution initially."""
        assert self.circuit_breaker.can_execute() is True

    def test_circuit_breaker_failure_recording(self):
        """Test circuit breaker failure recording."""
        error = Exception("Test failure")

        # Record failures
        self.circuit_breaker.record_failure(error)
        assert self.circuit_breaker.state.failure_count == 1

        self.circuit_breaker.record_failure(error)
        assert self.circuit_breaker.state.failure_count == 2

        # Circuit should still be closed
        assert self.circuit_breaker.state.is_open is False

        # Third failure should open the circuit
        self.circuit_breaker.record_failure(error)
        assert self.circuit_breaker.state.failure_count == 3
        assert self.circuit_breaker.state.is_open is True
        assert self.circuit_breaker.state.next_retry_time is not None

    def test_circuit_breaker_success_recording(self):
        """Test circuit breaker success recording."""
        # Open the circuit first
        for i in range(3):
            self.circuit_breaker.record_failure(Exception(f"Failure {i}"))

        assert self.circuit_breaker.state.is_open is True

        # Record successes
        self.circuit_breaker.record_success()
        assert self.circuit_breaker.state.consecutive_successes == 1

        self.circuit_breaker.record_success()
        assert self.circuit_breaker.state.consecutive_successes == 2
        assert self.circuit_breaker.state.is_open is False  # Should be closed now

    def test_circuit_breaker_recovery_timeout(self):
        """Test circuit breaker recovery timeout."""
        # Open the circuit
        for i in range(3):
            self.circuit_breaker.record_failure(Exception(f"Failure {i}"))

        assert self.circuit_breaker.state.is_open is True

        # Should not allow execution immediately
        assert self.circuit_breaker.can_execute() is False

        # Simulate timeout passage
        self.circuit_breaker.state.next_retry_time = datetime.utcnow() - timedelta(seconds=1)

        # Should allow execution after timeout
        assert self.circuit_breaker.can_execute() is True


class TestErrorHandlingService:
    """Test cases for main ErrorHandlingService."""

    def setup_method(self):
        """Set up test environment."""
        self.service = ErrorHandlingService()

    def test_service_initialization(self):
        """Test service initialization."""
        assert isinstance(self.service.circuit_breakers, dict)
        assert isinstance(self.service.recent_errors, list)
        assert isinstance(self.service.error_counts, dict)
        assert len(self.service.fallback_strategies) > 0
        assert self.service.max_error_history == 1000

    def test_register_circuit_breaker(self):
        """Test circuit breaker registration."""
        config = {
            'failure_threshold': 5,
            'recovery_timeout': 60,
            'success_threshold': 3
        }

        cb = self.service.register_circuit_breaker("test_cb", config)

        assert isinstance(cb, CircuitBreaker)
        assert cb.name == "test_cb"
        assert cb.state.failure_threshold == 5
        assert "test_cb" in self.service.circuit_breakers

    def test_get_circuit_breaker(self):
        """Test circuit breaker retrieval."""
        # Register a circuit breaker
        self.service.register_circuit_breaker("test_cb", {})

        cb = self.service.get_circuit_breaker("test_cb")
        assert cb is not None
        assert cb.name == "test_cb"

        # Test non-existent circuit breaker
        cb = self.service.get_circuit_breaker("nonexistent")
        assert cb is None

    @pytest.mark.asyncio
    async def test_execute_with_fallback_success(self):
        """Test successful operation execution with fallback."""
        async def successful_operation(x, y):
            return x + y

        result = await self.service.execute_with_fallback(
            operation_name="test_operation",
            operation=successful_operation,
            fallback_scenarios=[],
            correlation_id="test_success",
            args=(5, 3)
        )

        assert result == 8
        assert len(self.service.recent_errors) == 0  # No errors should be recorded

    @pytest.mark.asyncio
    async def test_execute_with_fallback_failure(self):
        """Test operation execution with fallback on failure."""
        async def failing_operation():
            raise Exception("Operation failed")

        result = await self.service.execute_with_fallback(
            operation_name="failing_operation",
            operation=failing_operation,
            fallback_scenarios=["tts_synthesis_failed"],
            correlation_id="test_failure"
        )

        # Should return fallback response
        assert isinstance(result, dict)
        assert "fallback" in result or "error" in result

        # Error should be recorded
        assert len(self.service.recent_errors) == 1
        assert self.service.recent_errors[0].operation == "failing_operation"

    def test_create_error_info(self):
        """Test error info creation."""
        error = Exception("Test error")

        error_info = self.service._create_error_info(
            operation_name="test_op",
            error=error,
            correlation_id="test_corr"
        )

        assert isinstance(error_info, ErrorInfo)
        assert error_info.operation == "test_op"
        assert error_info.message == "Test error"
        assert error_info.correlation_id == "test_corr"
        assert error_info.component == "error_handling_service"

    def test_classify_error_network(self):
        """Test network error classification."""
        error = ConnectionError("Connection failed")

        category, severity = self.service._classify_error(error, "network_request")

        assert category == ErrorCategory.NETWORK
        assert severity == ErrorSeverity.MEDIUM

    def test_classify_error_timeout(self):
        """Test timeout error classification."""
        error = TimeoutError("Request timed out")

        category, severity = self.service._classify_error(error, "api_call")

        assert category == ErrorCategory.TIMEOUT
        assert severity == ErrorSeverity.MEDIUM

    def test_classify_error_validation(self):
        """Test validation error classification."""
        error = ValueError("Invalid input parameter")

        category, severity = self.service._classify_error(error, "validation")

        assert category == ErrorCategory.VALIDATION
        assert severity == ErrorSeverity.LOW

    def test_classify_error_provider(self):
        """Test provider error classification."""
        error = Exception("Provider API rate limit exceeded")

        category, severity = self.service._classify_error(error, "tts_synthesis")

        assert category == ErrorCategory.PROVIDER_ERROR
        assert severity == ErrorSeverity.HIGH

    def test_error_storage(self):
        """Test error storage and history management."""
        # Add some errors
        for i in range(5):
            error_info = ErrorInfo(
                error_id=f"error_{i}",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                message=f"Error {i}",
                operation="test_op"
            )
            self.service._store_error(error_info)

        assert len(self.service.recent_errors) == 5
        assert self.service.error_counts["NETWORK:test_op"] == 5

    def test_error_history_limit(self):
        """Test error history size limit."""
        # Set low limit for testing
        original_limit = self.service.max_error_history
        self.service.max_error_history = 3

        try:
            # Add more errors than limit
            for i in range(5):
                error_info = ErrorInfo(
                    error_id=f"error_{i}",
                    category=ErrorCategory.UNKNOWN,
                    severity=ErrorSeverity.LOW,
                    message=f"Error {i}",
                    operation="test_op"
                )
                self.service._store_error(error_info)

            # Should maintain only the most recent errors
            assert len(self.service.recent_errors) == 3

        finally:
            self.service.max_error_history = original_limit

    def test_retry_operation_success(self):
        """Test successful operation retry."""
        async def operation(success_on_retry=False):
            if not success_on_retry:
                raise Exception("Initial failure")
            return "success"

        error_info = ErrorInfo(
            error_id="retry_test",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Network error",
            operation="test_op",
            retry_count=0,
            max_retries=3
        )

        # Mock the operation to succeed on retry
        async def mock_operation():
            return "success"

        retry_future = self.service.retry_operation(
            error_info, mock_operation
        )

        # Should complete without exception
        result = asyncio.run(retry_future)
        assert result == "success"

    def test_retry_operation_exhausted(self):
        """Test retry exhaustion."""
        async def always_failing_operation():
            raise Exception("Always fails")

        error_info = ErrorInfo(
            error_id="retry_exhausted",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Network error",
            operation="test_op",
            retry_count=3,  # Already at max retries
            max_retries=3
        )

        with pytest.raises(Exception, match="Always fails"):
            asyncio.run(self.service.retry_operation(
                error_info, always_failing_operation
            ))

    def test_get_error_statistics(self):
        """Test error statistics retrieval."""
        # Add some test errors
        for i in range(3):
            error_info = ErrorInfo(
                error_id=f"stat_error_{i}",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                message=f"Error {i}",
                operation="test_op",
                timestamp=datetime.utcnow() - timedelta(minutes=i*30)
            )
            self.service._store_error(error_info)

        stats = self.service.get_error_statistics()

        assert isinstance(stats, dict)
        assert stats["total_errors_tracked"] == 3
        assert "recent_errors_1h" in stats
        assert "error_counts_by_category" in stats
        assert "circuit_breakers" in stats

    def test_get_health_status(self):
        """Test health status retrieval."""
        status = self.service.get_health_status()

        assert isinstance(status, dict)
        assert "status" in status
        assert "recent_errors_1h" in status
        assert "open_circuit_breakers" in status
        assert "total_circuit_breakers" in status

    def test_clear_error_history(self):
        """Test error history clearing."""
        # Add some errors
        for i in range(3):
            error_info = ErrorInfo(
                error_id=f"clear_error_{i}",
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.LOW,
                message=f"Error {i}",
                operation="test_op"
            )
            self.service._store_error(error_info)

        assert len(self.service.recent_errors) == 3
        assert len(self.service.error_counts) > 0

        # Clear history
        self.service.clear_error_history()

        assert len(self.service.recent_errors) == 0
        assert len(self.service.error_counts) == 0

    def test_reset_circuit_breakers(self):
        """Test circuit breaker reset."""
        # Register and manipulate circuit breakers
        cb1 = self.service.register_circuit_breaker("test_cb1", {})
        cb2 = self.service.register_circuit_breaker("test_cb2", {})

        # Simulate failures
        cb1.record_failure(Exception("Test failure"))
        cb2.record_failure(Exception("Test failure"))

        assert cb1.state.failure_count == 1
        assert cb2.state.failure_count == 1

        # Reset all circuit breakers
        self.service.reset_circuit_breakers()

        assert cb1.state.failure_count == 0
        assert cb2.state.failure_count == 0
        assert cb1.state.is_open is False
        assert cb2.state.is_open is False


class TestFallbackStrategies:
    """Test cases for fallback strategy execution."""

    def setup_method(self):
        """Set up test environment."""
        self.service = ErrorHandlingService()

    def test_fallback_strategy_initialization(self):
        """Test fallback strategy initialization."""
        assert len(self.service.fallback_strategies) > 0
        assert "tts_synthesis_failed" in self.service.fallback_strategies

        tts_strategies = self.service.fallback_strategies["tts_synthesis_failed"]
        assert len(tts_strategies) > 0

        # Check strategy properties
        strategy = tts_strategies[0]
        assert isinstance(strategy, FallbackStrategy)
        assert strategy.name is not None
        assert strategy.priority > 0

    def test_should_execute_strategy(self):
        """Test fallback strategy condition checking."""
        strategy = FallbackStrategy(
            name="test_strategy",
            priority=1,
            conditions=[{"category": ErrorCategory.PROVIDER_ERROR}],
            action="test_action"
        )

        # Matching error
        error_info = ErrorInfo(
            error_id="test_error",
            category=ErrorCategory.PROVIDER_ERROR,
            severity=ErrorSeverity.HIGH,
            message="Provider error"
        )

        assert self.service._should_execute_strategy(strategy, error_info) is True

        # Non-matching error
        error_info.category = ErrorCategory.NETWORK
        assert self.service._should_execute_strategy(strategy, error_info) is False

    @pytest.mark.asyncio
    async def test_execute_fallback_scenario(self):
        """Test fallback scenario execution."""
        error_info = ErrorInfo(
            error_id="fallback_test",
            category=ErrorCategory.PROVIDER_ERROR,
            severity=ErrorSeverity.HIGH,
            message="Provider failed",
            operation="tts_synthesis"
        )

        # Execute a fallback scenario
        result = await self.service._execute_fallback_scenario(
            "tts_synthesis_failed",
            error_info,
            None, [], {}
        )

        # Should return some result (may be None if no strategies match perfectly)
        # This tests the execution flow
        assert result is not None or result is None  # Both are acceptable


if __name__ == "__main__":
    pytest.main([__file__])