"""
Action API endpoints for AI narrative interactions.

This module provides the core API endpoints for handling player actions
and receiving AI DM responses in the narrative interaction system.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from packages.shared.models import ActionRequest, ActionResponse
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/action", response_model=ActionResponse)
async def handle_action(
    action_request: ActionRequest,
    request: Request
) -> ActionResponse:
    """
    Handle player actions and return AI DM responses.

    This endpoint processes player prompts and returns narrative responses
    from the AI Dungeon Master. It includes comprehensive validation,
    error handling, and request tracking.

    Args:
        action_request: The validated action request containing player prompt and metadata
        request: FastAPI request object for correlation ID extraction

    Returns:
        ActionResponse: AI DM narrative response with metadata

    Raises:
        HTTPException: For various error conditions with appropriate status codes
    """
    start_time = time.time()
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))

    logger.info(
        "action_request_received",
        session_id=action_request.session_id,
        user_id=action_request.user_id,
        prompt_length=len(action_request.prompt),
        has_campaign_context=bool(action_request.campaign_context),
        correlation_id=correlation_id
    )

    try:
        # Validate request data
        validation_errors = _validate_action_request(action_request)
        if validation_errors:
            logger.warning(
                "action_request_validation_failed",
                errors=validation_errors,
                correlation_id=correlation_id
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "Request validation failed",
                    "details": validation_errors,
                    "correlation_id": correlation_id
                }
            )

        # Process the action (placeholder implementation)
        # TODO: Integrate with AI client and prompt system from Stories 2.1.2 and 2.1.3
        response_narrative = await _process_action_with_ai(action_request)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Create response
        response = ActionResponse(
            narrative=response_narrative,
            session_id=action_request.session_id,
            metadata={
                "request_metadata": action_request.metadata,
                "campaign_context": action_request.campaign_context,
                "generated_at": time.time(),
                "processing_details": {
                    "ai_model": "placeholder",  # TODO: Get from AI client
                    "tokens_used": 0,  # TODO: Get from AI client
                    "prompt_template": "core_dm"  # TODO: Get from prompt system
                }
            },
            processing_time=processing_time,
            status="success",
            correlation_id=correlation_id
        )

        logger.info(
            "action_response_generated",
            session_id=response.session_id,
            response_length=len(response.narrative),
            processing_time=processing_time,
            correlation_id=correlation_id
        )

        return response

    except ValidationError as e:
        logger.error(
            "action_request_pydantic_validation_error",
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Invalid request format",
                "details": e.errors(),
                "correlation_id": correlation_id
            }
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        logger.error(
            "action_processing_unexpected_error",
            error=str(e),
            error_type=type(e).__name__,
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error processing action",
                "correlation_id": correlation_id,
                "error_code": "ACTION_PROCESSING_ERROR"
            }
        )


def _validate_action_request(action_request: ActionRequest) -> list:
    """
    Validate the action request beyond Pydantic validation.

    Args:
        action_request: The action request to validate

    Returns:
        List of validation error messages, empty if valid
    """
    errors = []

    # Check prompt content for potentially harmful content
    if _contains_harmful_content(action_request.prompt):
        errors.append("Prompt contains potentially harmful content")

    # Check session ID format (additional validation)
    if not action_request.session_id.replace("_", "").replace("-", "").isalnum():
        errors.append("Session ID contains invalid characters")

    # Check prompt doesn't exceed reasonable limits
    if len(action_request.prompt) > 2000:
        errors.append("Prompt exceeds maximum length")

    # Validate campaign context if provided
    if action_request.campaign_context:
        if not isinstance(action_request.campaign_context, dict):
            errors.append("Campaign context must be a dictionary")
        elif len(str(action_request.campaign_context)) > 10000:  # 10KB limit
            errors.append("Campaign context is too large")

    return errors


def _contains_harmful_content(text: str) -> bool:
    """
    Check if text contains potentially harmful content.

    Args:
        text: Text to check for harmful content

    Returns:
        True if harmful content detected, False otherwise
    """
    harmful_patterns = [
        # Add patterns for harmful content detection
        # This is a placeholder implementation
        r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',  # Script tags
        r'javascript:',  # JavaScript URLs
    ]

    import re
    for pattern in harmful_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    return False


async def _process_action_with_ai(action_request: ActionRequest) -> str:
    """
    Process the action request with AI to generate a narrative response.

    This is a placeholder implementation that will be replaced with
    actual AI integration using the components from Stories 2.1.2 and 2.1.3.

    Args:
        action_request: The validated action request

    Returns:
        Narrative response from the AI DM
    """
    # TODO: Replace with actual AI integration
    # This should use:
    # 1. AI client from Story 2.1.2
    # 2. Prompt system from Story 2.1.3
    # 3. Observability from Story 2.1.1

    # Simulate processing delay
    await asyncio.sleep(0.1)

    # Generate a placeholder response based on the prompt
    if "attack" in action_request.prompt.lower():
        return "You swing your weapon at the enemy, connecting with a solid blow!"
    elif "investigate" in action_request.prompt.lower():
        return "You carefully examine your surroundings, noticing details you missed before."
    elif "talk" in action_request.prompt.lower():
        return "You engage in conversation, learning more about the situation."
    else:
        return f"You attempt to {action_request.prompt.lower()}, and the DM responds with a narrative continuation of the story."


@router.get("/action/test")
async def test_action_endpoint() -> Dict[str, Any]:
    """
    Test endpoint to verify action API functionality.

    Returns:
        Simple test response to verify endpoint accessibility
    """
    return {
        "status": "success",
        "message": "Action API is operational",
        "endpoint": "/api/action",
        "test_endpoint": "/api/action/test"
    }