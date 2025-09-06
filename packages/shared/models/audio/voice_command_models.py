"""
Voice Command Models
Models for voice command processing and intent classification.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field as PydanticField


class VoiceCommandIntent(BaseModel):
    """Voice command intent classification."""

    intent_id: str = PydanticField(..., description="Unique intent identifier")

    primary_intent: str = PydanticField(
        ...,
        description="Primary command intent",
        examples=["attack", "move", "inventory", "character", "system", "social"],
    )

    confidence_score: float = PydanticField(
        ..., ge=0.0, le=1.0, description="Intent confidence score"
    )

    alternative_intents: List[Dict[str, Any]] = PydanticField(
        default_factory=list,
        description="Alternative intent interpretations with scores",
    )

    entities: Dict[str, Any] = PydanticField(
        default_factory=dict,
        description="Extracted entities (characters, items, locations, etc.)",
        examples={
            "character": "Eldrin",
            "target": "goblin",
            "item": "health_potion",
            "quantity": 2,
            "location": "dungeon_entrance",
        },
    )

    context: Dict[str, Any] = PydanticField(
        default_factory=dict,
        description="Command context and metadata",
        examples={
            "session_id": "voice_session_123",
            "user_id": "user_456",
            "game_state": "combat",
            "timestamp": "2025-08-22T21:31:31Z",
        },
    )

    original_text: str = PydanticField(..., description="Original transcribed text")

    processed_text: str = PydanticField(
        ..., description="Processed and normalized text"
    )

    language: str = PydanticField(default="en-US", description="Detected language code")

    sentiment: Optional[float] = PydanticField(
        None, ge=-1.0, le=1.0, description="Text sentiment score (-1.0 to 1.0)"
    )

    urgency: Optional[float] = PydanticField(
        None, ge=0.0, le=1.0, description="Command urgency level"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When intent was created"
    )

    processing_time: float = PydanticField(
        ..., ge=0.0, description="Time taken to process intent in seconds"
    )


class CommandPattern(BaseModel):
    """Voice command pattern definition for recognition."""

    pattern_id: str = PydanticField(..., description="Unique pattern identifier")

    intent: str = PydanticField(..., description="Associated intent type")

    patterns: List[str] = PydanticField(..., description="Text patterns to match")

    entities: Dict[str, str] = PydanticField(
        default_factory=dict,
        description="Entity definitions and types",
        examples={
            "character": "PERSON",
            "target": "MONSTER",
            "item": "ITEM",
            "quantity": "NUMBER",
            "location": "LOCATION",
        },
    )

    priority: int = PydanticField(
        default=1,
        ge=1,
        le=10,
        description="Pattern matching priority (higher = more important)",
    )

    examples: List[str] = PydanticField(
        default_factory=list, description="Example phrases that match this pattern"
    )

    context_requirements: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Context requirements for this pattern"
    )

    fuzzy_matching: bool = PydanticField(
        default=True, description="Whether to use fuzzy string matching"
    )

    case_sensitive: bool = PydanticField(
        default=False, description="Whether pattern matching is case sensitive"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When pattern was created"
    )

    updated_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When pattern was last updated"
    )

    usage_count: int = PydanticField(
        default=0, description="Number of times this pattern has been matched"
    )

    success_rate: float = PydanticField(
        default=1.0, ge=0.0, le=1.0, description="Success rate for this pattern"
    )


class CommandHistory(BaseModel):
    """User command history and preferences for learning."""

    user_id: str = PydanticField(..., description="User identifier")

    command_history: List[Dict[str, Any]] = PydanticField(
        default_factory=list,
        description="History of executed commands",
        examples=[
            {
                "intent": "attack",
                "entities": {"target": "goblin"},
                "success": True,
                "timestamp": "2025-08-22T21:31:31Z",
            }
        ],
    )

    preferred_patterns: Dict[str, int] = PydanticField(
        default_factory=dict,
        description="User's preferred command patterns and frequency",
    )

    command_success_rate: float = PydanticField(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Overall command success rate for this user",
    )

    common_entities: Dict[str, Dict[str, int]] = PydanticField(
        default_factory=dict,
        description="Frequently used entities by type",
        examples={
            "character": {"Eldrin": 25, "Throg": 15},
            "target": {"goblin": 30, "orc": 20},
        },
    )

    speech_patterns: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Learned speech patterns and preferences"
    )

    last_updated: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When history was last updated"
    )

    total_commands: int = PydanticField(
        default=0, description="Total number of commands executed"
    )

    successful_commands: int = PydanticField(
        default=0, description="Number of successful commands"
    )

    failed_commands: int = PydanticField(
        default=0, description="Number of failed commands"
    )


class CommandExecutionResult(BaseModel):
    """Result of executing a voice command."""

    execution_id: str = PydanticField(..., description="Unique execution identifier")

    intent_id: str = PydanticField(..., description="Associated intent identifier")

    session_id: str = PydanticField(..., description="Voice session identifier")

    user_id: str = PydanticField(..., description="User who executed the command")

    command: str = PydanticField(..., description="Original command text")

    intent: str = PydanticField(..., description="Recognized intent")

    entities: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Extracted entities"
    )

    success: bool = PydanticField(
        ..., description="Whether command execution was successful"
    )

    result_data: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Result data from command execution"
    )

    error_message: Optional[str] = PydanticField(
        None, description="Error message if execution failed"
    )

    execution_time: float = PydanticField(
        ..., ge=0.0, description="Time taken to execute command in seconds"
    )

    response_text: Optional[str] = PydanticField(
        None, description="Response text to send back to user"
    )

    game_state_changes: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Changes made to game state"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When execution occurred"
    )

    confidence_score: float = PydanticField(
        ..., ge=0.0, le=1.0, description="Confidence score of the command recognition"
    )


class CommandFeedback(BaseModel):
    """User feedback on voice command processing."""

    feedback_id: str = PydanticField(..., description="Unique feedback identifier")

    session_id: str = PydanticField(..., description="Voice session identifier")

    user_id: str = PydanticField(..., description="User providing feedback")

    intent_id: Optional[str] = PydanticField(
        None, description="Associated intent identifier"
    )

    execution_id: Optional[str] = PydanticField(
        None, description="Associated execution identifier"
    )

    rating: float = PydanticField(
        ..., ge=1.0, le=5.0, description="User rating (1.0 to 5.0)"
    )

    feedback_type: str = PydanticField(
        ...,
        description="Type of feedback",
        examples=["accuracy", "speed", "usability", "recognition", "execution"],
    )

    comments: Optional[str] = PydanticField(None, description="Optional user comments")

    categories: List[str] = PydanticField(
        default_factory=list,
        description="Feedback categories",
        examples=[
            "command_recognition",
            "entity_extraction",
            "execution_speed",
            "response_clarity",
        ],
    )

    suggested_improvement: Optional[str] = PydanticField(
        None, description="User's suggestion for improvement"
    )

    technical_details: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Technical details for analysis"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When feedback was provided"
    )

    resolved: bool = PydanticField(
        default=False, description="Whether feedback has been addressed"
    )

    resolution_notes: Optional[str] = PydanticField(
        None, description="Notes about how feedback was resolved"
    )
