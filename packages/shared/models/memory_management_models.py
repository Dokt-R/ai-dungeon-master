"""
Memory Management Models
Models for campaign memory and AI integration.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import (
    BaseModel,
    Field as PydanticField,
    field_serializer,
)
from pydantic.config import ConfigDict


class MemoryEvent(BaseModel):
    """Represents a historical event in the campaign chronicle."""

    model_config = ConfigDict(serialize_default_values=True)

    event_id: str = PydanticField(
        ...,
        description="Unique event identifier",
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=128,
    )

    timestamp: datetime = PydanticField(..., description="When the event occurred")

    event_type: Literal["narrative", "combat", "social", "exploration"] = PydanticField(
        ..., description="Type of event"
    )

    description: str = PydanticField(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable event description",
    )

    participants: List[str] = PydanticField(
        ..., description="Characters/NPCs involved", min_length=1
    )

    location: Optional[str] = PydanticField(
        None, description="Where the event occurred"
    )

    metadata: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Additional event data"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When memory was created"
    )

    updated_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When memory was last updated"
    )

    version: int = PydanticField(default=1, description="Memory version for updates")

    @field_serializer("timestamp", "created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime fields to ISO format strings."""
        return value.isoformat()


class MemoryFact(BaseModel):
    """Represents a persistent fact about the campaign world."""

    model_config = ConfigDict(serialize_default_values=True)

    fact_id: str = PydanticField(
        ...,
        description="Unique fact identifier",
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=128,
    )

    fact_type: Literal["npc", "location", "quest", "relationship", "knowledge"] = (
        PydanticField(..., description="Type of fact")
    )

    subject: str = PydanticField(..., description="Primary subject of the fact")

    description: str = PydanticField(
        ..., min_length=1, max_length=500, description="Fact description"
    )

    confidence: float = PydanticField(
        ..., ge=0.0, le=1.0, description="AI confidence in this fact"
    )

    last_updated: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When fact was last updated"
    )

    source: str = PydanticField(..., description="Source of this knowledge")

    tags: List[str] = PydanticField(
        default_factory=list, description="Searchable tags", max_length=10
    )

    related_events: List[str] = PydanticField(
        default_factory=list, description="Related event IDs", max_length=50
    )

    @field_serializer("last_updated")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime fields to ISO format strings."""
        return value.isoformat()


class MemoryContext(BaseModel):
    """Context structure for AI memory integration."""

    recent_events: List[MemoryEvent] = PydanticField(
        ..., description="Recent campaign events"
    )

    relevant_facts: List[MemoryFact] = PydanticField(
        ..., description="Facts relevant to current context"
    )

    character_knowledge: Dict[str, List[str]] = PydanticField(
        ..., description="What each character knows"
    )

    world_state: Dict[str, Any] = PydanticField(
        ..., description="Current world state snapshot"
    )

    summary: str = PydanticField(
        ..., description="Condensed memory summary for AI", min_length=1
    )

    context_size: int = PydanticField(..., description="Estimated token count", ge=0)


class MemoryOperation(BaseModel):
    """Result of a memory CRUD operation."""

    model_config = ConfigDict(serialize_default_values=True)

    operation: Literal["create", "read", "update", "delete"] = PydanticField(
        ..., description="Operation performed"
    )

    success: bool = PydanticField(..., description="Whether operation succeeded")

    memory_id: str = PydanticField(..., description="ID of affected memory")

    memory_type: str = PydanticField(..., description="Type of memory affected")

    error: Optional[str] = PydanticField(None, description="Error message if failed")

    timestamp: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Operation timestamp"
    )

    @field_serializer("timestamp")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime fields to ISO format strings."""
        return value.isoformat()


class CreateMemoryEventRequest(BaseModel):
    """Request to create a new memory event."""

    event_type: Literal["narrative", "combat", "social", "exploration"] = PydanticField(
        ..., description="Type of event"
    )

    description: str = PydanticField(
        ..., min_length=1, max_length=1000, description="Event description"
    )

    participants: List[str] = PydanticField(
        ..., description="Characters/NPCs involved", min_length=1
    )

    location: Optional[str] = PydanticField(
        None, description="Where the event occurred"
    )

    metadata: Optional[Dict[str, Any]] = PydanticField(
        None, description="Additional event data"
    )


class UpdateMemoryEventRequest(BaseModel):
    """Request to update an existing memory event."""

    event_id: str = PydanticField(..., description="Event to update")

    description: Optional[str] = PydanticField(
        None, min_length=1, max_length=1000, description="Updated description"
    )

    participants: Optional[List[str]] = PydanticField(
        None, description="Updated participants"
    )

    location: Optional[str] = PydanticField(None, description="Updated location")

    metadata: Optional[Dict[str, Any]] = PydanticField(
        None, description="Updated metadata"
    )


class CreateMemoryFactRequest(BaseModel):
    """Request to create a new memory fact."""

    fact_type: Literal["npc", "location", "quest", "relationship", "knowledge"] = (
        PydanticField(..., description="Type of fact")
    )

    subject: str = PydanticField(..., description="Primary subject of the fact")

    description: str = PydanticField(
        ..., min_length=1, max_length=500, description="Fact description"
    )

    confidence: float = PydanticField(
        ..., ge=0.0, le=1.0, description="AI confidence in this fact"
    )

    source: str = PydanticField(..., description="Source of this knowledge")

    tags: Optional[List[str]] = PydanticField(None, description="Searchable tags")

    related_events: Optional[List[str]] = PydanticField(
        None, description="Related event IDs"
    )


class UpdateMemoryFactRequest(BaseModel):
    """Request to update an existing memory fact."""

    fact_id: str = PydanticField(..., description="Fact to update")

    description: Optional[str] = PydanticField(
        None, min_length=1, max_length=500, description="Updated description"
    )

    confidence: Optional[float] = PydanticField(
        None, ge=0.0, le=1.0, description="Updated confidence"
    )

    tags: Optional[List[str]] = PydanticField(None, description="Updated tags")

    related_events: Optional[List[str]] = PydanticField(
        None, description="Updated related events"
    )
