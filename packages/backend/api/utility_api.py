"""
Utility API endpoints for simple operations.

This module provides basic utility endpoints for testing and simple AI interactions.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from langsmith import traceable
from pydantic import BaseModel, Field

from packages.backend.components.utility_manager import UtilityManager
from packages.shared.exceptions import CustomException
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


class LLMTestRequest(BaseModel):
    """Request model for LLM testing."""

    prompt: str = Field(
        ..., min_length=1, max_length=2000, description="The prompt to send to the LLM"
    )


class LLMTestResponse(BaseModel):
    """Response model for LLM testing."""

    response: str = Field(..., description="The LLM's response")
    status: str = Field(..., description="Status of the request")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")


@router.post("/utility/llm-test", response_model=LLMTestResponse)
@traceable
async def test_llm(
    request: LLMTestRequest, utility_manager: UtilityManager = Depends()
) -> LLMTestResponse:
    """
    Test the LLM with a simple prompt with comprehensive timing tracking.

    This endpoint provides a simple way to test LLM functionality without
    any campaign context, memory, or complex state management.

    Args:
        request: The LLM test request containing the prompt
        utility_manager: Injected utility manager

    Returns:
        LLMTestResponse: The LLM response with metadata

    Raises:
        HTTPException: For various error conditions
    """
    import time

    start_time = time.perf_counter()
    request_id = f"api_{int(time.time() * 1000)}"

    try:
        logger.info(
            "utility_api_llm_test_started",
            request_id=request_id,
            prompt_length=len(request.prompt),
        )

        # Stage 1: Request validation (already done by FastAPI/Pydantic)
        validation_time = time.perf_counter()
        validation_duration = (validation_time - start_time) * 1000

        logger.debug(
            "utility_api_validation_completed",
            request_id=request_id,
            validation_time_ms=round(validation_duration, 2),
        )

        # Stage 2: Call utility manager
        manager_start = time.perf_counter()
        result = await utility_manager.test_llm(request.prompt)
        manager_time = (time.perf_counter() - manager_start) * 1000

        logger.debug(
            "utility_api_manager_completed",
            request_id=request_id,
            manager_time_ms=round(manager_time, 2),
            result_keys=list(result.keys()) if isinstance(result, dict) else "not_dict",
        )

        # Stage 3: Response construction
        response_start = time.perf_counter()
        response = LLMTestResponse(
            response=result["response"],
            status=result["status"],
            metadata=result["metadata"],
        )
        response_time = (time.perf_counter() - response_start) * 1000

        total_time = (time.perf_counter() - start_time) * 1000

        # Add API-level timing to metadata
        if hasattr(response, "metadata") and isinstance(response.metadata, dict):
            response.metadata.update(
                {
                    "api_total_ms": round(total_time, 2),
                    "api_validation_ms": round(validation_duration, 2),
                    "api_manager_ms": round(manager_time, 2),
                    "api_response_construction_ms": round(response_time, 2),
                    "request_id": request_id,
                }
            )

        logger.info(
            "utility_api_llm_test_completed",
            request_id=request_id,
            prompt_length=len(request.prompt),
            response_length=len(response.response),
            total_time_ms=round(total_time, 2),
            validation_time_ms=round(validation_duration, 2),
            manager_time_ms=round(manager_time, 2),
            response_construction_ms=round(response_time, 2),
        )

        return response

    except CustomException as e:
        total_time = (time.perf_counter() - start_time) * 1000
        logger.error(
            "utility_api_llm_test_custom_error",
            request_id=request_id,
            total_time_ms=round(total_time, 2),
            error=str(e),
        )
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error": e.message,
                "error_code": e.error_code.value
                if hasattr(e.error_code, "value")
                else str(e.error_code),
                "details": e.details,
            },
        )

    except Exception as e:
        total_time = (time.perf_counter() - start_time) * 1000
        logger.error(
            "utility_api_llm_test_unexpected_error",
            request_id=request_id,
            total_time_ms=round(total_time, 2),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error during LLM test",
                "error_code": "LLM_TEST_ERROR",
            },
        )
