"""
AI Integration Models
Models for LangGraph tool integration and accuracy validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field as PydanticField


class ToolCall(BaseModel):
    """LangGraph tool call structure for SRD queries."""

    tool_name: str = PydanticField(
        ...,
        description="Name of the tool to call",
        examples=["monster_query", "spell_lookup", "weapon_search"],
    )

    tool_args: Dict[str, Any] = PydanticField(
        ...,
        description="Arguments for the tool call",
        examples=[
            {"name": "Goblin", "context": "combat"},
            {"query_type": "spell", "name": "Fireball"},
        ],
    )

    query_type: str = PydanticField(
        ..., description="Type of SRD query", examples=["monster", "spell", "weapon"]
    )

    confidence_threshold: float = PydanticField(
        default=0.8, ge=0.0, le=1.0, description="Minimum confidence for tool usage"
    )


class ToolResult(BaseModel):
    """Result structure for SRD tool calls."""

    tool_name: str = PydanticField(
        ...,
        description="Name of the tool that was called",
        examples=["monster_query", "spell_lookup"],
    )

    success: bool = PydanticField(
        ..., description="Whether the tool call was successful"
    )

    data: Optional[Dict[str, Any]] = PydanticField(None, description="Tool result data")

    error: Optional[str] = PydanticField(
        None, description="Error message if tool failed"
    )

    execution_time: float = PydanticField(
        ..., ge=0.0, description="Tool execution time in seconds"
    )

    relevance_score: Optional[float] = PydanticField(
        None, ge=0.0, le=1.0, description="Result relevance score"
    )

    summary: Optional[str] = PydanticField(
        None, description="Condensed results summary for AI"
    )


class AccuracyValidation(BaseModel):
    """AI response accuracy validation result."""

    query: str = PydanticField(
        ...,
        description="Original query that was asked",
        examples=["What are the stats for a goblin?"],
    )

    ai_response: str = PydanticField(
        ...,
        description="AI's response to validate",
        examples=["A goblin has AC 15, HP 7 (2d6), and attacks with a scimitar."],
    )

    expected_answer: str = PydanticField(
        ...,
        description="Expected correct answer from SRD",
        examples=["AC 15, HP 7 (2d6), STR 8, DEX 14, CON 10, INT 10, WIS 8, CHA 8"],
    )

    accuracy_score: float = PydanticField(
        ..., ge=0.0, le=1.0, description="Accuracy score (0-1)"
    )

    validation_details: List[str] = PydanticField(
        ...,
        description="Details about validation results",
        examples=[
            "Correct AC and HP values",
            "Missing ability scores",
            "Correct challenge rating",
        ],
    )

    validation_date: datetime = PydanticField(
        ..., description="When validation was performed"
    )
