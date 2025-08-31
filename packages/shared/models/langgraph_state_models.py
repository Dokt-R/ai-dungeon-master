"""
LangGraph State Models
Models for conversational AI interactions in LangGraph.
"""

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field as PydanticField, model_validator
from pydantic.config import ConfigDict


class MemoryState(BaseModel):
    """Represents the conversational memory state for LangGraph."""

    model_config = ConfigDict(serialize_default_values=True)

    messages: List[Dict[str, str]] = PydanticField(
        default_factory=list,
        description="Conversation history with user and AI messages",
        examples=[
            [
                {"role": "user", "content": "I want to investigate the room"},
                {"role": "assistant", "content": "You carefully examine the room..."},
            ]
        ],
    )

    context: Dict[str, Any] = PydanticField(
        default_factory=dict,
        description="Additional context data for the conversation",
        examples=[
            {
                "campaign_name": "Lost Mines of Phandelver",
                "player_level": 3,
                "character_name": "Eldrin",
                "current_location": "Goblin Hideout",
            }
        ],
    )

    session_id: str = PydanticField(
        ...,
        description="Unique session identifier for conversation tracking",
        examples=["session_123", "campaign_session_abc"],
    )

    turn_count: int = PydanticField(
        default=0,
        ge=0,
        description="Number of conversation turns in this session",
        examples=[5, 15, 42],
    )

    last_activity: datetime = PydanticField(
        default_factory=datetime.utcnow,
        description="Timestamp of the last activity in this session",
    )

    scratchpad: List[str] = PydanticField(
        default_factory=list,
        description="Temporary notes and observations for the current interaction",
        examples=[
            [
                "Player is investigating a statue",
                "Player has detect magic ability",
                "Statue appears to be magical",
            ]
        ],
    )

    turn_count_explicitly_set: bool = PydanticField(
        default=False,
        description="Whether turn_count was explicitly set (not auto-calculated)",
        exclude=True,  # Don't include in serialization
    )

    @model_validator(mode="after")
    def detect_explicit_turn_count(self):
        """Detect if turn_count was explicitly set."""
        # Check if turn_count was set to a non-default value
        if hasattr(self, "__pydantic_fields_set__"):
            if "turn_count" in self.__pydantic_fields_set__ and self.turn_count != 0:
                self.turn_count_explicitly_set = True
        return self

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.messages.append({"role": role, "content": content})
        # Only auto-update turn_count if it wasn't explicitly set
        if not self.turn_count_explicitly_set:
            self.turn_count = len(
                [msg for msg in self.messages if msg["role"] == "user"]
            )
        self.last_activity = datetime.utcnow()

    def add_to_scratchpad(self, note: str) -> None:
        """Add a note to the scratchpad."""
        self.scratchpad.append(note)
        self.last_activity = datetime.utcnow()

    def clear_scratchpad(self) -> None:
        """Clear all scratchpad notes."""
        self.scratchpad.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory state to dictionary for serialization."""
        return {
            "messages": self.messages,
            "context": self.context,
            "session_id": self.session_id,
            "turn_count": self.turn_count,
            "last_activity": self.last_activity.isoformat(),
            "scratchpad": self.scratchpad,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryState":
        """Create memory state from dictionary."""
        instance = cls(
            messages=data.get("messages", []),
            context=data.get("context", {}),
            session_id=data["session_id"],
            turn_count=data.get("turn_count", 0),
            scratchpad=data.get("scratchpad", []),
        )
        # Mark turn_count as explicitly set if it was in the data
        if "turn_count" in data:
            instance.turn_count_explicitly_set = True
        if "last_activity" in data:
            instance.last_activity = datetime.fromisoformat(data["last_activity"])
        return instance