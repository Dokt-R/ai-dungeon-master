"""
Rules Engine Models
Models for SRD data querying and responses.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field as PydanticField


class RulesQuery(BaseModel):
    """Query model for SRD rules data requests."""

    query_type: str = PydanticField(
        ...,
        description="Type of data being queried (monster, spell, weapon)",
        examples=["monster", "spell", "weapon"],
    )

    name: Optional[str] = PydanticField(
        None,
        description="Name of the specific item to query",
        examples=["Goblin", "Fireball", "Longsword"],
    )

    context: Optional[str] = PydanticField(
        None,
        description="Context for the query",
        examples=["combat", "character_creation", "world_lore"],
    )

    filters: Optional[Dict[str, Any]] = PydanticField(
        None,
        description="Additional filters for the query",
        examples=[
            {"min_cr": 1, "max_cr": 5},
            {"level": 3, "school": "Evocation"},
            {"category": "Simple Melee Weapons"},
        ],
    )


class RulesResponse(BaseModel):
    """Response model for SRD rules data queries."""

    query_type: Optional[str] = PydanticField(
        None,
        description="Type of data that was queried",
        examples=["monster", "spell", "weapon"],
    )

    found: Optional[bool] = PydanticField(
        None, description="Whether the requested data was found"
    )

    result: Optional[Any] = PydanticField(None, description="The query result data")

    name: Optional[str] = PydanticField(
        None, description="Name of the queried item", examples=["Goblin", "Fire Bolt"]
    )

    data: Optional[Any] = PydanticField(
        None, description="The raw data returned from the query"
    )

    error: Optional[str] = PydanticField(
        None, description="Error message if the query failed"
    )

    query_time: Optional[float] = PydanticField(
        None, ge=0.0, description="Time taken to execute the query in seconds"
    )

    cache_hit: Optional[bool] = PydanticField(
        None, description="Whether the result came from cache"
    )

    total_results: Optional[int] = PydanticField(
        None, ge=0, description="Total number of results found"
    )

    metadata: Optional[Dict[str, Any]] = PydanticField(
        None, description="Additional metadata about the query"
    )