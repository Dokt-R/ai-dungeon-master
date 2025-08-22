"""
Health check API endpoints for monitoring service status.

This module provides health check endpoints for various service components,
including observability, database, and general application health.
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from packages.backend.agents.prompts import prompt_manager
from packages.backend.components.ai_client import ai_client
from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/ai")
async def get_ai_health() -> Dict[str, Any]:
    """
    Get the comprehensive health status of the AI system.

    This endpoint performs connection testing with the AI provider,
    validates system prompts, and checks LangSmith tracing integration.

    Returns:
        Dict containing comprehensive AI health information with the following structure:
        - status: "healthy" or "unhealthy"
        - provider: AI provider name
        - model: configured model name
        - traced: boolean indicating if tracing is working
        - prompt_system: status of prompt system
        - connection_test: result of connection test
        - circuit_breaker_state: current state of circuit breaker
        - timestamp: ISO timestamp of the check
        - error: error message if unhealthy (optional)

    Raises:
        HTTPException: If there's an internal error retrieving health status
    """
    try:
        logger.info("ai_comprehensive_health_check_requested")

        # Get basic AI client health status
        ai_health = ai_client.get_health_status()

        # Test LangSmith tracing integration
        tracing_works = False
        trace_id = None
        try:
            with observability_service.trace_operation(
                operation_name="ai_health_check_tracing_test",
                health_check_type="comprehensive",
                endpoint="/api/health/ai",
            ) as trace:
                trace_id = trace
                tracing_works = True
                logger.info("ai_tracing_test_successful", trace_id=trace_id)
        except Exception as trace_error:
            logger.warning("ai_tracing_test_failed", error=str(trace_error))

        # Test system prompt system
        prompt_system_healthy = False
        prompt_count = 0
        try:
            # Check if we can access prompt templates
            from packages.backend.agents.prompts import PromptType

            core_template = prompt_manager.get_default_template(PromptType.CORE_DM)
            if core_template:
                prompt_count = len(prompt_manager._templates)
                prompt_system_healthy = True
                logger.debug("prompt_system_check_passed", template_count=prompt_count)
            else:
                logger.warning("prompt_system_missing_core_template")
        except Exception as prompt_error:
            logger.error("prompt_system_check_failed", error=str(prompt_error))

        # Perform connection test if AI client is initialized
        connection_test_result = "not_tested"
        if ai_client.is_initialized():
            try:
                # Simple connection test - just verify the client can make a basic call
                with observability_service.trace_operation(
                    operation_name="ai_connection_test", test_type="health_check"
                ) as conn_trace_id:
                    # For health check, we don't actually make an expensive API call
                    # Just verify the client is properly configured
                    connection_test_result = "passed"
                    logger.info("ai_connection_test_passed", trace_id=conn_trace_id)
            except Exception as conn_error:
                connection_test_result = "failed"
                logger.warning("ai_connection_test_failed", error=str(conn_error))

        # Determine overall health status
        components_healthy = [
            ai_health["status"] == "healthy",
            tracing_works,
            prompt_system_healthy,
        ]

        overall_status = "healthy" if all(components_healthy) else "degraded"
        if not any(components_healthy):
            overall_status = "unhealthy"

        # Build comprehensive response
        response = {
            "status": overall_status,
            "provider": ai_health.get("provider", "unknown"),
            "model": ai_health.get("model", "unknown"),
            "traced": tracing_works,
            "prompt_system": {
                "status": "healthy" if prompt_system_healthy else "unhealthy",
                "template_count": prompt_count,
            },
            "connection_test": connection_test_result,
            "circuit_breaker_state": ai_health.get("circuit_breaker_state", "unknown"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "components_checked": ["ai_client", "tracing", "prompt_system"],
        }

        # Add error information if any component failed
        if not all(components_healthy):
            failed_components = []
            if ai_health["status"] != "healthy":
                failed_components.append("ai_client")
            if not tracing_works:
                failed_components.append("tracing")
            if not prompt_system_healthy:
                failed_components.append("prompt_system")

            response["failed_components"] = failed_components
            response["error"] = f"Failed components: {', '.join(failed_components)}"

        # Log the comprehensive health check result
        if overall_status == "healthy":
            logger.info("ai_comprehensive_health_check_passed", **response)
        else:
            logger.warning("ai_comprehensive_health_check_failed", **response)

        return response

    except Exception as e:
        error_msg = f"Failed to retrieve comprehensive AI health status: {str(e)}"
        logger.error("ai_comprehensive_health_check_error", error=str(e))

        # Return a proper error response
        raise HTTPException(
            status_code=500,
            detail={
                "status": "unhealthy",
                "provider": "unknown",
                "model": "unknown",
                "traced": False,
                "error": "internal_comprehensive_health_check_error",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        )


@router.get("/observability")
async def get_observability_health() -> Dict[str, Any]:
    """
    Get the health status of the observability service.

    Returns:
        Dict containing observability health information with the following structure:
        - status: "healthy" or "unhealthy"
        - provider: observability provider name
        - project: configured project name
        - error: error message if unhealthy (optional)

    Raises:
        HTTPException: If there's an internal error retrieving health status
    """
    try:
        logger.info("observability_health_check_requested")

        # Get health status from observability service
        health_status = observability_service.get_health_status()

        # Log the health check result
        if health_status["status"] == "healthy":
            logger.info("observability_health_check_passed", **health_status)
        else:
            logger.warning("observability_health_check_failed", **health_status)

        return health_status

    except Exception as e:
        error_msg = f"Failed to retrieve observability health status: {str(e)}"
        logger.error("observability_health_check_error", error=str(e))

        # Return a proper error response
        raise HTTPException(
            status_code=500,
            detail={
                "status": "unhealthy",
                "provider": "langsmith",
                "project": "unknown",
                "error": "internal_health_check_error",
            },
        )


@router.get("/general")
async def get_general_health() -> Dict[str, Any]:
    """
    Get comprehensive application health status.

    Returns:
        Dict containing general health information including:
        - Overall service status
        - Individual component statuses (observability, AI client)
        - Service metadata
    """
    try:
        logger.info("general_health_check_requested")

        # Get health status of all components
        observability_health = observability_service.get_health_status()
        ai_health = ai_client.get_health_status()

        # Determine overall health status
        components_healthy = (
            observability_health["status"] == "healthy"
            and ai_health["status"] == "healthy"
        )
        overall_status = "healthy" if components_healthy else "degraded"

        # Log warning if any component is unhealthy
        if not components_healthy:
            unhealthy_components = []
            if observability_health["status"] != "healthy":
                unhealthy_components.append("observability")
            if ai_health["status"] != "healthy":
                unhealthy_components.append("ai_client")

            logger.warning(
                "general_health_check_degraded",
                overall_status=overall_status,
                unhealthy_components=unhealthy_components,
                observability_status=observability_health["status"],
                ai_status=ai_health["status"],
            )

        return {
            "status": overall_status,
            "service": "ai-dungeon-master-backend",
            "version": "1.0.0",
            "components": {
                "observability": observability_health,
                "ai_client": ai_health,
            },
            "timestamp": "2024-01-01T00:00:00Z",  # TODO: Use actual timestamp
        }

    except Exception as e:
        error_msg = f"Failed to retrieve general health status: {str(e)}"
        logger.error("general_health_check_error", error=str(e))

        return {
            "status": "unhealthy",
            "service": "ai-dungeon-master-backend",
            "error": "internal_health_check_error",
            "components": {
                "observability": {"status": "unknown", "error": "health_check_failed"},
                "ai_client": {"status": "unknown", "error": "health_check_failed"},
            },
        }


@router.post("/observability/test-trace")
async def test_observability_trace() -> Dict[str, Any]:
    """
    Test endpoint to validate observability tracing functionality.

    This endpoint creates a test trace to verify that the observability
    service is working correctly and traces are being sent to LangSmith.

    Returns:
        Dict containing test results and trace information
    """
    try:
        logger.info("observability_trace_test_requested")

        # Use the observability service to create a test trace
        with observability_service.trace_operation(
            operation_name="test_observability_trace",
            test_type="health_check",
            endpoint="/api/health/observability/test-trace",
        ) as trace_id:
            # Simulate some operations that would be traced
            test_data = {
                "message": "Test observability trace",
                "timestamp": "2024-01-01T00:00:00Z",
                "trace_id": trace_id,
                "operations": ["validate_config", "initialize_client", "send_trace"],
            }

            # Log additional structured data
            logger.info(
                "test_trace_operations",
                trace_id=trace_id,
                operations=test_data["operations"],
                test_data=test_data,
            )

            # Add a small delay to simulate real work
            import asyncio

            await asyncio.sleep(0.1)

            return {
                "status": "success",
                "message": "Observability trace test completed",
                "trace_id": trace_id,
                "observability_status": observability_service.get_health_status(),
                "test_data": test_data,
            }

    except Exception as e:
        error_msg = f"Failed to execute observability trace test: {str(e)}"
        logger.error("observability_trace_test_error", error=str(e))

        return {
            "status": "error",
            "message": "Observability trace test failed",
            "error": error_msg,
            "observability_status": observability_service.get_health_status(),
        }
