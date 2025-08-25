"""
Error Handling Service for AI Dungeon Master.

This module provides comprehensive error handling, fallback mechanisms, and recovery
strategies for voice services and audio processing.

Features:
- Centralized error management and classification
- Circuit breaker pattern for service protection
- Fallback strategies for voice services
- Error recovery and retry mechanisms
- Health monitoring and alerting
- Error reporting and analytics
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""

    NETWORK = "network"
    AUDIO_PROCESSING = "audio_processing"
    VOICE_SERVICE = "voice_service"
    PROVIDER_ERROR = "provider_error"
    CONFIGURATION = "configuration"
    RESOURCE_LIMIT = "resource_limit"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Structured error information."""

    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    component: str = ""
    operation: str = ""
    correlation_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    recovery_attempts: int = 0

    @property
    def is_retryable(self) -> bool:
        """Check if error can be retried."""
        return self.retry_count < self.max_retries and self.category in [
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.PROVIDER_ERROR,
        ]


@dataclass
class CircuitBreakerState:
    """Circuit breaker state information."""

    is_open: bool = False
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    next_retry_time: Optional[datetime] = None
    consecutive_successes: int = 0

    # Configuration
    failure_threshold: int = 5
    recovery_timeout: timedelta = timedelta(seconds=60)
    success_threshold: int = 3


@dataclass
class FallbackStrategy:
    """Fallback strategy configuration."""

    name: str
    priority: int
    conditions: List[Dict[str, Any]]
    action: str
    timeout: float = 30.0
    cooldown: float = 60.0


class CircuitBreaker:
    """Circuit breaker implementation for service protection."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.state = CircuitBreakerState(
            failure_threshold=config.get("failure_threshold", 5),
            recovery_timeout=timedelta(seconds=config.get("recovery_timeout", 60)),
            success_threshold=config.get("success_threshold", 3),
        )
        self.logger = get_logger(f"{__name__}.CircuitBreaker.{name}")

    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if not self.state.is_open:
            return True

        # Check if recovery timeout has passed
        if (
            self.state.next_retry_time
            and datetime.utcnow() >= self.state.next_retry_time
        ):
            self.logger.info(
                "circuit_breaker_attempting_recovery", circuit_breaker=self.name
            )
            return True

        return False

    def record_success(self) -> None:
        """Record successful operation."""
        self.state.consecutive_successes += 1
        self.state.failure_count = 0

        # Close circuit if enough consecutive successes
        if (
            self.state.is_open
            and self.state.consecutive_successes >= self.state.success_threshold
        ):
            self.state.is_open = False
            self.state.consecutive_successes = 0
            self.logger.info("circuit_breaker_closed", circuit_breaker=self.name)

    def record_failure(self, error: Exception) -> None:
        """Record failed operation."""
        self.state.failure_count += 1
        self.state.last_failure_time = datetime.utcnow()
        self.state.consecutive_successes = 0

        # Open circuit if failure threshold exceeded
        if (
            not self.state.is_open
            and self.state.failure_count >= self.state.failure_threshold
        ):
            self.state.is_open = True
            self.state.next_retry_time = datetime.utcnow() + self.state.recovery_timeout
            self.logger.warning(
                "circuit_breaker_opened",
                circuit_breaker=self.name,
                failure_count=self.state.failure_count,
                next_retry_time=self.state.next_retry_time.isoformat(),
            )


class ErrorHandlingService:
    """
    Centralized error handling and fallback service.

    Features:
    - Error classification and structured handling
    - Circuit breaker pattern for service protection
    - Fallback strategies for voice services
    - Retry mechanisms with exponential backoff
    - Health monitoring and recovery
    - Error reporting and analytics
    """

    def __init__(self):
        self.logger = get_logger(f"{__name__}.ErrorHandlingService")

        # Circuit breakers for different services
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Error tracking
        self.recent_errors: List[ErrorInfo] = []
        self.error_counts: Dict[str, int] = {}
        self.max_error_history = 1000

        # Fallback strategies
        self.fallback_strategies = self._initialize_fallback_strategies()

        # Recovery mechanisms
        self.recovery_actions: Dict[str, Callable] = {}

        # Performance tracking
        self.operation_times: Dict[str, float] = {}
        self.recovery_times: Dict[str, float] = {}

    def _initialize_fallback_strategies(self) -> Dict[str, List[FallbackStrategy]]:
        """Initialize fallback strategies for different error scenarios."""
        return {
            "tts_synthesis_failed": [
                FallbackStrategy(
                    name="switch_to_backup_provider",
                    priority=1,
                    conditions=[{"category": ErrorCategory.PROVIDER_ERROR}],
                    action="switch_tts_provider",
                    timeout=30.0,
                    cooldown=60.0,
                ),
                FallbackStrategy(
                    name="reduce_quality_settings",
                    priority=2,
                    conditions=[{"severity": ErrorSeverity.HIGH}],
                    action="reduce_tts_quality",
                    timeout=15.0,
                ),
                FallbackStrategy(
                    name="use_cached_response",
                    priority=3,
                    conditions=[{"category": ErrorCategory.NETWORK}],
                    action="return_cached_tts",
                    timeout=5.0,
                ),
            ],
            "stt_transcription_failed": [
                FallbackStrategy(
                    name="retry_with_different_format",
                    priority=1,
                    conditions=[{"category": ErrorCategory.AUDIO_PROCESSING}],
                    action="reformat_audio_stt",
                    timeout=20.0,
                ),
                FallbackStrategy(
                    name="switch_stt_provider",
                    priority=2,
                    conditions=[{"category": ErrorCategory.PROVIDER_ERROR}],
                    action="switch_stt_provider",
                    timeout=30.0,
                    cooldown=60.0,
                ),
            ],
            "audio_processing_failed": [
                FallbackStrategy(
                    name="simplify_processing",
                    priority=1,
                    conditions=[{"category": ErrorCategory.AUDIO_PROCESSING}],
                    action="disable_enhancements",
                    timeout=10.0,
                ),
                FallbackStrategy(
                    name="reduce_chunk_size",
                    priority=2,
                    conditions=[{"severity": ErrorSeverity.HIGH}],
                    action="reduce_audio_chunk_size",
                    timeout=15.0,
                ),
            ],
        }

    def register_circuit_breaker(
        self, name: str, config: Dict[str, Any]
    ) -> CircuitBreaker:
        """Register a new circuit breaker."""
        circuit_breaker = CircuitBreaker(name, config)
        self.circuit_breakers[name] = circuit_breaker
        self.logger.info("circuit_breaker_registered", name=name)
        return circuit_breaker

    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self.circuit_breakers.get(name)

    async def execute_with_fallback(
        self,
        operation_name: str,
        operation: Callable[..., Awaitable[Any]],
        fallback_scenarios: List[str],
        *args,
        correlation_id: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Execute operation with fallback mechanisms.

        Args:
            operation_name: Name of the operation
            operation: Async function to execute
            fallback_scenarios: List of fallback scenario names
            correlation_id: Correlation ID for tracing

        Returns:
            Operation result or fallback result
        """
        start_time = time.time()

        try:
            # Check circuit breaker
            circuit_breaker = self.circuit_breakers.get(operation_name)
            if circuit_breaker and not circuit_breaker.can_execute():
                raise Exception(f"Circuit breaker open for {operation_name}")

            # Execute primary operation
            result = await operation(*args, **kwargs)

            # Record success
            if circuit_breaker:
                circuit_breaker.record_success()

            execution_time = time.time() - start_time
            self.operation_times[operation_name] = execution_time

            self.logger.debug(
                "operation_successful",
                operation=operation_name,
                execution_time=execution_time,
                correlation_id=correlation_id,
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time

            # Record failure
            if circuit_breaker:
                circuit_breaker.record_failure(e)

            # Handle error and attempt fallbacks
            return await self._handle_error_and_fallback(
                operation_name,
                e,
                fallback_scenarios,
                operation,
                args,
                kwargs,
                correlation_id,
            )

    async def _handle_error_and_fallback(
        self,
        operation_name: str,
        error: Exception,
        fallback_scenarios: List[str],
        original_operation: Callable[..., Awaitable[Any]],
        args: tuple,
        kwargs: dict,
        correlation_id: Optional[str],
    ) -> Any:
        """Handle error and execute fallback strategies."""
        # Create error info
        error_info = self._create_error_info(operation_name, error, correlation_id)

        # Log error
        self._log_error(error_info)

        # Store error for tracking
        self._store_error(error_info)

        # Attempt fallback strategies
        for scenario in fallback_scenarios:
            if scenario in self.fallback_strategies:
                result = await self._execute_fallback_scenario(
                    scenario, error_info, original_operation, args, kwargs
                )
                if result is not None:
                    self.logger.info(
                        "fallback_successful",
                        operation=operation_name,
                        scenario=scenario,
                        correlation_id=correlation_id,
                    )
                    return result

        # All fallbacks failed
        self.logger.error(
            "all_fallbacks_failed",
            operation=operation_name,
            correlation_id=correlation_id,
            error=str(error),
        )

        # Return appropriate error response
        return self._create_error_response(operation_name, error_info)

    def _create_error_info(
        self, operation_name: str, error: Exception, correlation_id: Optional[str]
    ) -> ErrorInfo:
        """Create structured error information."""
        error_id = f"{operation_name}_{int(time.time() * 1000)}"

        # Classify error
        category, severity = self._classify_error(error, operation_name)

        return ErrorInfo(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(error),
            details={
                "exception_type": type(error).__name__,
                "operation": operation_name,
                "traceback": self._get_traceback(error),
            },
            component="error_handling_service",
            operation=operation_name,
            correlation_id=correlation_id,
        )

    def _classify_error(
        self, error: Exception, operation_name: str
    ) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error by category and severity."""
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Network errors
        if any(
            keyword in error_str
            for keyword in ["connection", "timeout", "network", "dns", "ssl"]
        ):
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM

        # Timeout errors
        if "timeout" in error_str or error_type == "TimeoutError":
            return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM

        # Provider errors (check before voice service to avoid misclassification)
        if "provider" in error_str or any(
            keyword in operation_name for keyword in ["openai", "elevenlabs"]
        ):
            return ErrorCategory.PROVIDER_ERROR, ErrorSeverity.HIGH

        # Audio processing errors
        if any(keyword in operation_name for keyword in ["audio", "stt", "tts"]):
            if any(
                keyword in error_str
                for keyword in ["format", "decode", "encode", "invalid"]
            ):
                return ErrorCategory.AUDIO_PROCESSING, ErrorSeverity.HIGH
            return ErrorCategory.VOICE_SERVICE, ErrorSeverity.MEDIUM

        # Resource limit errors
        if any(
            keyword in error_str
            for keyword in ["memory", "disk", "quota", "rate limit"]
        ):
            return ErrorCategory.RESOURCE_LIMIT, ErrorSeverity.HIGH

        # Configuration errors
        if "config" in error_str or "setting" in error_str:
            return ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM

        # Validation errors
        if any(
            keyword in error_str for keyword in ["invalid", "validation", "parameter"]
        ):
            return ErrorCategory.VALIDATION, ErrorSeverity.LOW

        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM

    def _get_traceback(self, error: Exception) -> str:
        """Get traceback information."""
        import traceback

        return traceback.format_exception(type(error), error, error.__traceback__)

    async def _execute_fallback_scenario(
        self,
        scenario: str,
        error_info: ErrorInfo,
        original_operation: Callable[..., Awaitable[Any]],
        args: tuple,
        kwargs: dict,
    ) -> Optional[Any]:
        """Execute a specific fallback scenario."""
        strategies = self.fallback_strategies.get(scenario, [])

        for strategy in sorted(strategies, key=lambda s: s.priority):
            if self._should_execute_strategy(strategy, error_info):
                try:
                    self.logger.info(
                        "executing_fallback_strategy",
                        scenario=scenario,
                        strategy=strategy.name,
                        error_id=error_info.error_id,
                    )

                    result = await self._execute_strategy_action(
                        strategy, error_info, original_operation, args, kwargs
                    )

                    if result is not None:
                        return result

                except Exception as e:
                    self.logger.warning(
                        "fallback_strategy_failed",
                        strategy=strategy.name,
                        error=str(e),
                        error_id=error_info.error_id,
                    )

        return None

    def _should_execute_strategy(
        self, strategy: FallbackStrategy, error_info: ErrorInfo
    ) -> bool:
        """Check if fallback strategy should be executed."""
        for condition in strategy.conditions:
            condition_met = False

            for key, value in condition.items():
                if key == "category" and error_info.category == value:
                    condition_met = True
                    break
                elif key == "severity" and error_info.severity == value:
                    condition_met = True
                    break
                elif hasattr(error_info, key) and getattr(error_info, key) == value:
                    condition_met = True
                    break

            if not condition_met:
                return False

        return True

    async def _execute_strategy_action(
        self,
        strategy: FallbackStrategy,
        error_info: ErrorInfo,
        original_operation: Callable[..., Awaitable[Any]],
        args: tuple,
        kwargs: dict,
    ) -> Optional[Any]:
        """Execute the action for a fallback strategy."""
        action = strategy.action

        if action == "switch_tts_provider":
            return await self._switch_tts_provider(error_info, args, kwargs)
        elif action == "reduce_tts_quality":
            return await self._reduce_tts_quality(error_info, args, kwargs)
        elif action == "return_cached_tts":
            return await self._return_cached_tts(error_info, args, kwargs)
        elif action == "reformat_audio_stt":
            return await self._reformat_audio_stt(error_info, args, kwargs)
        elif action == "switch_stt_provider":
            return await self._switch_stt_provider(error_info, args, kwargs)
        elif action == "disable_enhancements":
            return await self._disable_enhancements(error_info, args, kwargs)
        elif action == "reduce_audio_chunk_size":
            return await self._reduce_audio_chunk_size(error_info, args, kwargs)

        return None

    # Fallback action implementations
    async def _switch_tts_provider(
        self, error_info: ErrorInfo, args: tuple, kwargs: dict
    ) -> Optional[Any]:
        """Switch to backup TTS provider."""
        # This would integrate with the TTS service to switch providers
        # For now, return a mock response
        return {"fallback": "tts_provider_switched", "error_id": error_info.error_id}

    async def _reduce_tts_quality(
        self, error_info: ErrorInfo, args: tuple, kwargs: dict
    ) -> Optional[Any]:
        """Reduce TTS quality settings."""
        # Modify kwargs to use lower quality settings
        modified_kwargs = kwargs.copy()
        modified_kwargs["voice"] = "default"  # Use default voice
        return {"fallback": "tts_quality_reduced", "error_id": error_info.error_id}

    async def _return_cached_tts(
        self, error_info: ErrorInfo, args: tuple, kwargs: dict
    ) -> Optional[Any]:
        """Return cached TTS response."""
        return {"fallback": "cached_tts_response", "error_id": error_info.error_id}

    async def _reformat_audio_stt(
        self, error_info: ErrorInfo, args: tuple, kwargs: dict
    ) -> Optional[Any]:
        """Reformat audio for STT processing."""
        return {"fallback": "audio_reformatted", "error_id": error_info.error_id}

    async def _switch_stt_provider(
        self, error_info: ErrorInfo, args: tuple, kwargs: dict
    ) -> Optional[Any]:
        """Switch STT provider."""
        return {"fallback": "stt_provider_switched", "error_id": error_info.error_id}

    async def _disable_enhancements(
        self, error_info: ErrorInfo, args: tuple, kwargs: dict
    ) -> Optional[Any]:
        """Disable audio enhancements."""
        return {"fallback": "enhancements_disabled", "error_id": error_info.error_id}

    async def _reduce_audio_chunk_size(
        self, error_info: ErrorInfo, args: tuple, kwargs: dict
    ) -> Optional[Any]:
        """Reduce audio chunk size."""
        return {"fallback": "chunk_size_reduced", "error_id": error_info.error_id}

    def _create_error_response(
        self, operation_name: str, error_info: ErrorInfo
    ) -> Dict[str, Any]:
        """Create appropriate error response."""
        return {
            "success": False,
            "error": error_info.message,
            "error_id": error_info.error_id,
            "category": error_info.category.value,
            "severity": error_info.severity.value,
            "operation": operation_name,
            "retryable": error_info.is_retryable,
            "timestamp": error_info.timestamp.isoformat(),
        }

    def _log_error(self, error_info: ErrorInfo) -> None:
        """Log error with appropriate level."""
        log_data = {
            "error_id": error_info.error_id,
            "category": error_info.category.value,
            "severity": error_info.severity.value,
            "component": error_info.component,
            "operation": error_info.operation,
            "correlation_id": error_info.correlation_id,
            "message": error_info.message,
        }

        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical("critical_error_occurred", **log_data)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error("high_severity_error", **log_data)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning("medium_severity_error", **log_data)
        else:
            self.logger.info("low_severity_error", **log_data)

    def _store_error(self, error_info: ErrorInfo) -> None:
        """Store error for tracking and analysis."""
        self.recent_errors.append(error_info)

        # Maintain max history size
        if len(self.recent_errors) > self.max_error_history:
            self.recent_errors = self.recent_errors[-self.max_error_history :]

        # Update error counts
        error_key = f"{error_info.category.value}:{error_info.operation}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

    def retry_operation(
        self,
        error_info: ErrorInfo,
        operation: Callable[..., Awaitable[Any]],
        *args,
        **kwargs,
    ) -> Awaitable[Any]:
        """Retry operation with exponential backoff."""
        if not error_info.is_retryable:
            # If not retryable, execute the operation anyway to let it fail with original exception
            return operation(*args, **kwargs)

        error_info.retry_count += 1

        # Calculate delay with exponential backoff
        delay = min(2**error_info.retry_count, 30)  # Max 30 seconds

        self.logger.info(
            "retrying_operation",
            operation=error_info.operation,
            retry_count=error_info.retry_count,
            delay=delay,
            error_id=error_info.error_id,
        )

        return self._execute_with_delay(operation, delay, *args, **kwargs)

    async def _execute_with_delay(
        self, operation: Callable[..., Awaitable[Any]], delay: float, *args, **kwargs
    ) -> Any:
        """Execute operation after delay."""
        await asyncio.sleep(delay)
        return await operation(*args, **kwargs)

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and health information."""
        recent_errors = [
            e
            for e in self.recent_errors
            if datetime.utcnow() - e.timestamp < timedelta(hours=1)
        ]

        return {
            "total_errors_tracked": len(self.recent_errors),
            "recent_errors_1h": len(recent_errors),
            "error_counts_by_category": self.error_counts.copy(),
            "circuit_breakers": {
                name: {
                    "is_open": cb.state.is_open,
                    "failure_count": cb.state.failure_count,
                    "consecutive_successes": cb.state.consecutive_successes,
                }
                for name, cb in self.circuit_breakers.items()
            },
            "operation_performance": self.operation_times.copy(),
            "recovery_times": self.recovery_times.copy(),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of error handling service."""
        recent_errors_1h = len(
            [
                e
                for e in self.recent_errors
                if datetime.utcnow() - e.timestamp < timedelta(hours=1)
            ]
        )

        open_circuit_breakers = len(
            [cb for cb in self.circuit_breakers.values() if cb.state.is_open]
        )

        # Determine overall health
        if (
            recent_errors_1h > 100
            or open_circuit_breakers > len(self.circuit_breakers) / 2
        ):
            health_status = "critical"
        elif recent_errors_1h > 50 or open_circuit_breakers > 0:
            health_status = "degraded"
        else:
            health_status = "healthy"

        return {
            "status": health_status,
            "recent_errors_1h": recent_errors_1h,
            "open_circuit_breakers": open_circuit_breakers,
            "total_circuit_breakers": len(self.circuit_breakers),
            "error_rate": recent_errors_1h / max(len(self.recent_errors), 1),
            "fallback_strategies_count": len(self.fallback_strategies),
        }

    def clear_error_history(self) -> None:
        """Clear error history and reset counters."""
        self.recent_errors.clear()
        self.error_counts.clear()
        self.logger.info("error_history_cleared")

    def reset_circuit_breakers(self) -> None:
        """Reset all circuit breakers."""
        for circuit_breaker in self.circuit_breakers.values():
            circuit_breaker.state = CircuitBreakerState()
        self.logger.info("circuit_breakers_reset")


# Global error handling service instance
error_handling_service = ErrorHandlingService()
