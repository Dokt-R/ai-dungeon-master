"""
Utility Manager for simple AI operations.

This manager provides basic utility functions for testing and simple AI interactions
without the complexity of campaigns, memory, or state management.
"""

from typing import Any, Dict

from fastapi import Depends
from langsmith import traceable
from sqlalchemy.ext.asyncio import AsyncSession

from packages.backend.components.ai_client import ai_client
from packages.shared.db import get_async_session_dependency
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import AIAPIError
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


class UtilityManager:
    """
    Manages simple utility operations like LLM testing.
    """

    def __init__(self, session: AsyncSession = Depends(get_async_session_dependency)):
        """Initialize the UtilityManager."""
        self.session = session

    @traceable
    async def test_llm(self, prompt: str) -> Dict[str, Any]:
        """
        Test the LLM with a simple prompt and return the response with detailed timing.

        Args:
            prompt: The user's prompt to send to the LLM

        Returns:
            Dict containing the LLM response and metadata including timing information

        Raises:
            AIAPIError: If the LLM call fails
        """
        import time

        start_time = time.perf_counter()
        manager_id = f"manager_{int(time.time() * 1000)}"

        try:
            logger.info(
                "utility_manager_llm_test_started",
                manager_id=manager_id,
                prompt_length=len(prompt),
            )

            # Stage 1: AI client initialization check
            init_check_start = time.perf_counter()
            config = ai_client.get_config()
            model_name = config.model if config else "unknown"
            is_initialized = ai_client.is_initialized()
            init_check_time = (time.perf_counter() - init_check_start) * 1000

            logger.debug(
                "utility_manager_ai_client_check",
                manager_id=manager_id,
                is_initialized=is_initialized,
                model=model_name,
                init_check_time_ms=round(init_check_time, 2),
            )

            # Stage 2: AI client call
            ai_call_start = time.perf_counter()
            response = await ai_client.generate_text(
                prompt=prompt, max_completion_tokens=500, temperature=1
            )
            ai_call_time = (time.perf_counter() - ai_call_start) * 1000

            logger.debug(
                "utility_manager_ai_call_completed",
                manager_id=manager_id,
                ai_call_time_ms=round(ai_call_time, 2),
                response_length=len(response),
            )

            # Stage 3: Response processing and metadata construction
            processing_start = time.perf_counter()
            total_time = (time.perf_counter() - start_time) * 1000
            processing_time = (time.perf_counter() - processing_start) * 1000

            result = {
                "response": response,
                "status": "success",
                "metadata": {
                    "prompt_length": len(prompt),
                    "response_length": len(response),
                    "model": model_name,
                    "manager_id": manager_id,
                    "timing": {
                        "manager_total_ms": round(total_time, 2),
                        "init_check_ms": round(init_check_time, 2),
                        "ai_call_ms": round(ai_call_time, 2),
                        "processing_ms": round(processing_time, 2),
                    },
                },
            }

            logger.info(
                "utility_manager_llm_test_completed",
                manager_id=manager_id,
                prompt_length=len(prompt),
                response_length=len(response),
                model=model_name,
                total_time_ms=round(total_time, 2),
                init_check_time_ms=round(init_check_time, 2),
                ai_call_time_ms=round(ai_call_time, 2),
                processing_time_ms=round(processing_time, 2),
            )

            return result

        except Exception as e:
            total_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                "utility_manager_llm_test_failed",
                manager_id=manager_id,
                prompt_length=len(prompt),
                total_time_ms=round(total_time, 2),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise AIAPIError(
                ErrorCode.AI_API_ERROR,
                details={
                    "error": str(e),
                    "prompt_length": len(prompt),
                    "manager_id": manager_id,
                    "total_time_ms": round(total_time, 2),
                },
            )
