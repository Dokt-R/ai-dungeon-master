"""
AI Action Models
Models for narrative interactions with the AI DM.
"""

from typing import Optional

from pydantic import BaseModel, Field as PydanticField


class ActionRequest(BaseModel):
    """Request model for player actions sent to the AI DM."""

    prompt: str = PydanticField(
        ...,
        min_length=1,
        max_length=2000,
        description="The player's action or message to the DM",
        examples=[
            "I want to investigate the strange statue",
            "I attack the goblin with my sword",
        ],
    )

    session_id: str = PydanticField(
        ...,
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=128,
        description="Unique session identifier for conversation tracking",
        examples=["session_123", "campaign_session_abc"],
    )

    campaign_context: Optional[dict] = PydanticField(
        None,
        description="Additional campaign context and metadata",
        examples=[
            {
                "campaign_name": "Lost Mines of Phandelver",
                "player_level": 3,
                "character_name": "Eldrin",
            }
        ],
    )

    user_id: Optional[str] = PydanticField(
        None,
        pattern=r"^[a-zA-Z0-9_-]+$",
        max_length=128,
        description="User identifier for personalization and tracking",
        examples=["user_456", "discord_user_789"],
    )

    metadata: Optional[dict] = PydanticField(
        None,
        description="Additional metadata for the action request",
        examples=[
            {"source": "discord", "channel_id": "123456789", "message_id": "987654321"}
        ],
    )


class ActionResponse(BaseModel):
    """Response model for AI DM narrative responses."""

    narrative: str = PydanticField(
        ...,
        min_length=1,
        max_length=4000,
        description="The DM's narrative response to the player",
        examples=[
            "You carefully examine the statue, noticing intricate carvings that seem to tell a story..."
        ],
    )

    session_id: str = PydanticField(
        ...,
        description="Session identifier for conversation continuity",
        examples=["session_123"],
    )

    metadata: Optional[dict] = PydanticField(
        None,
        description="Additional response metadata",
        examples=[
            {
                "generated_at": "2024-01-01T12:00:00Z",
                "model_used": "gpt-5-nano-2025-08-07",
                "tokens_used": 150,
            }
        ],
    )

    processing_time: Optional[float] = PydanticField(
        None,
        gt=0,
        le=300,
        description="Response generation time in seconds",
        examples=[2.5],
    )

    status: str = PydanticField(
        default="success",
        description="Response status",
        examples=["success", "partial", "error"],
    )

    correlation_id: Optional[str] = PydanticField(
        None,
        description="Correlation ID for request tracking",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    error: Optional[dict] = PydanticField(
        None,
        description="Error information if status is not success",
        examples=[{"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests"}],
    )