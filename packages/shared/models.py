from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field as PydanticField, SecretStr
from sqlalchemy import Column, String
from sqlalchemy.orm import Mapped
from sqlmodel import Field as SQLField, Relationship, SQLModel


# Server Configuration Model
class Server(SQLModel, table=True):
    __tablename__ = "keys"
    server_id: str = SQLField(primary_key=True)
    api_key: SecretStr = SQLField(sa_column=Column(String), default=None)
    dm_roll_visibility: str = SQLField(default="public")
    player_roll_mode: str = SQLField(default="digital")
    character_sheet_mode: str = SQLField(default="digital_sheet")

    campaigns: Mapped[List["Campaign"]] = Relationship(
        back_populates="server_api", sa_relationship_kwargs={"lazy": "selectin"}
    )


# Campaign-Player Link Table
class CampaignPlayerLink(SQLModel, table=True):
    __tablename__ = "campaign_players"
    campaign_id: int = SQLField(primary_key=True, foreign_key="campaigns.campaign_id")
    player_id: str = SQLField(primary_key=True, foreign_key="players.player_id")


# Player Model
class Player(SQLModel, table=True):
    __tablename__ = "players"
    player_id: str = SQLField(primary_key=True)
    username: Optional[str] = SQLField(default=None)
    player_status: str = SQLField(default="cmd")
    last_active_campaign: Optional[str] = SQLField(
        default=None, foreign_key="campaigns.campaign_name"
    )

    characters: Mapped[List["Character"]] = Relationship(
        back_populates="player", sa_relationship_kwargs={"lazy": "selectin"}
    )
    campaigns: Mapped[List["Campaign"]] = Relationship(
        back_populates="players",
        link_model=CampaignPlayerLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )


# Character Model
class Character(SQLModel, table=True):
    __tablename__ = "characters"
    character_id: Optional[int] = SQLField(default=None, primary_key=True)
    name: str = SQLField(...)
    character_url: Optional[str] = SQLField(default=None)

    player_id: str = SQLField(foreign_key="players.player_id")
    player: Mapped["Player"] = Relationship(
        back_populates="characters", sa_relationship_kwargs={"lazy": "selectin"}
    )

    campaign_id: Optional[int] = SQLField(
        default=None, foreign_key="campaigns.campaign_id"
    )
    campaign: Mapped["Campaign"] = Relationship(
        back_populates="characters", sa_relationship_kwargs={"lazy": "selectin"}
    )


# Campaign Model
class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"
    campaign_id: Optional[int] = SQLField(default=None, primary_key=True)
    campaign_name: str = SQLField(...)
    owner_id: str = SQLField(...)
    state: Optional[str] = SQLField(default=None)
    last_save: datetime = SQLField(default_factory=datetime.utcnow)

    server_id: str = SQLField(foreign_key="keys.server_id")
    server_api: Mapped["Server"] = Relationship(
        back_populates="campaigns", sa_relationship_kwargs={"lazy": "selectin"}
    )

    players: Mapped[List["Player"]] = Relationship(
        back_populates="campaigns",
        link_model=CampaignPlayerLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    characters: Mapped[List["Character"]] = Relationship(
        back_populates="campaign", sa_relationship_kwargs={"lazy": "selectin"}
    )


# Memory State Model for Database Persistence
class MemoryStateModel(SQLModel, table=True):
    __tablename__ = "memory_states"
    memory_id: Optional[int] = SQLField(default=None, primary_key=True)
    session_id: str = SQLField(..., index=True, unique=True)
    user_id: Optional[str] = SQLField(default=None, index=True)
    campaign_id: Optional[int] = SQLField(default=None, foreign_key="campaigns.campaign_id", index=True)

    # JSON serialized memory data
    messages: str = SQLField(..., sa_column=Column(String))  # JSON serialized
    context: str = SQLField(..., sa_column=Column(String))   # JSON serialized
    scratchpad: str = SQLField(..., sa_column=Column(String)) # JSON serialized

    # Metadata
    turn_count: int = SQLField(default=0)
    total_messages: int = SQLField(default=0)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    last_activity: datetime = SQLField(default_factory=datetime.utcnow)
    last_save: datetime = SQLField(default_factory=datetime.utcnow)

    # Relationships
    campaign: Mapped[Optional["Campaign"]] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    # Indexes for performance
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


# ======================================================================================
# API Models (Pydantic BaseModels for request/response validation)
# ======================================================================================


class ServerConfigModel(BaseModel):
    api_key: SecretStr = PydanticField(
        ...,
        description="LLM API key used to authenticate with the backend",
        min_length=1,
    )
    dm_roll_visibility: Literal[
        "public",
        "hidden",
    ] = PydanticField(
        "public",
        description="Server wide settings handling DM dice roll visibility",
    )
    player_roll_mode: Literal[
        "physical",
        "digital",
        "auto",
        "hidden",
    ] = PydanticField(
        "digital",
        description="Per player preferences handling dice rolls",
    )
    character_sheet_mode: Literal[
        "digital_sheet",
        "physical_sheet",
    ] = PydanticField(
        "digital_sheet",
        description="Server wide settings handing digital or physical character sheets preference",
    )


class AddCharacterRequest(BaseModel):
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    name: str = PydanticField(..., min_length=1, max_length=32, pattern=r"^[\w\- ]+$")
    character_url: str | None = None


class UpdateCharacterRequest(BaseModel):
    character_id: int
    name: str | None = PydanticField(
        None, min_length=1, max_length=32, pattern=r"^[\w\- ]+$"
    )
    character_url: str | None = None


class RemoveCharacterRequest(BaseModel):
    character_id: int


class ListCharactersRequest(BaseModel):
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )


class CreatePlayerRequest(BaseModel):
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    username: str = PydanticField(
        ..., min_length=3, max_length=32, pattern=r"^[\w\- ]+$"
    )


class JoinCampaignRequest(BaseModel):
    server_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    campaign_name: str = PydanticField(..., min_length=1, max_length=64)
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    character_name: Optional[str] = PydanticField(
        None, min_length=1, max_length=32, pattern=r"^[\w\- ]+$"
    )
    character_url: Optional[str] = None


class ContinueCampaignRequest(BaseModel):
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    username: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )


class LeaveCampaignRequest(BaseModel):
    server_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    campaign_name: str = PydanticField(..., min_length=1, max_length=64)
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )


class CampaignCreateRequest(BaseModel):
    server_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    campaign_name: str = PydanticField(..., min_length=1, max_length=64)
    owner_id: str


class CampaignEndRequest(BaseModel):
    server_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    campaign_name: Optional[str] = PydanticField(
        default=None, min_length=1, max_length=64
    )
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )


class CampaignDeleteRequest(BaseModel):
    server_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    campaign_name: str = PydanticField(..., min_length=1, max_length=64)
    requester_id: str = PydanticField(
        ..., min_length=1, max_length=64, pattern=r"^[\w\-]+$"
    )
    is_admin: bool


class CampaignStateRequest(BaseModel):
    state: str


# ======================================================================================
# AI Action Models (for narrative interactions)
# ======================================================================================


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
                "model_used": "gpt-4",
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


# ======================================================================================
# Enums used for as a single source of truth for field validations
# ======================================================================================


class DMVisibility(str, Enum):
    public = "public"
    hidden = "hidden"


class PlayerRollMode(str, Enum):
    physical = "physical"
    digital = "digital"
    auto = "auto"
    hidden = "hidden"


class CharacterSheetMode(str, Enum):
    digital_sheet = "digital_sheet"
    physical_sheet = "physical_sheet"


# ======================================================================================
# LangGraph State Models (for conversational AI interactions)
# ======================================================================================


class MemoryState(BaseModel):
    """Represents the conversational memory state for LangGraph."""

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

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.messages.append({"role": role, "content": content})
        self.turn_count = len([msg for msg in self.messages if msg["role"] == "user"])
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
        if "last_activity" in data:
            instance.last_activity = datetime.fromisoformat(data["last_activity"])
        return instance


# ======================================================================================
# SRD (System Reference Document) Compliance Models
# ======================================================================================


class SRDCompliance(BaseModel):
    """SRD licensing and compliance tracking."""

    data_source: str = PydanticField(
        ...,
        description="Official SRD source reference",
        examples=["Dungeons & Dragons 5.1 SRD", "Player's Handbook (SRD)"],
    )

    license_version: str = PydanticField(
        ..., description="SRD license version", examples=["5.1", "5.0"]
    )

    usage_restrictions: List[str] = PydanticField(
        default_factory=list,
        description="Documented usage restrictions",
        examples=[
            "Non-commercial use only",
            "Must attribute to Wizards of the Coast",
            "Cannot use for commercial products",
        ],
    )

    last_verified: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Last compliance verification date"
    )

    verification_hash: str = PydanticField(
        ...,
        description="Data integrity verification hash",
        examples=["sha256:abc123...", "md5:def456..."],
    )

    compliance_officer: Optional[str] = PydanticField(
        None,
        description="Person responsible for compliance verification",
        examples=["legal@company.com", "compliance@company.com"],
    )

    audit_trail: List[dict] = PydanticField(
        default_factory=list,
        description="Audit trail of compliance checks and updates",
        examples=[
            {
                "timestamp": "2024-01-01T12:00:00Z",
                "action": "verified",
                "details": "Verified against official SRD source",
            }
        ],
    )


class DataSource(BaseModel):
    """Source tracking for SRD data."""

    source_name: str = PydanticField(
        ...,
        description="Source document name",
        examples=["System Reference Document 5.1", "Player's Handbook SRD"],
    )

    source_url: str = PydanticField(
        ...,
        description="Official source URL",
        examples=["https://dnd.wizards.com/resources/systems-reference-document"],
    )

    publication_date: datetime = PydanticField(
        ..., description="Source publication date"
    )

    version: str = PydanticField(
        ..., description="SRD version", examples=["5.1", "5.0"]
    )

    checksum: str = PydanticField(
        ...,
        description="Source data checksum for integrity verification",
        examples=["sha256:abc123def456"],
    )

    is_official: bool = PydanticField(
        default=True,
        description="Whether this is an official Wizards of the Coast source",
    )

    attribution_required: bool = PydanticField(
        default=True,
        description="Whether attribution to Wizards of the Coast is required",
    )


class Monster(BaseModel):
    """SRD monster data structure with compliance tracking."""

    monster_id: Optional[int] = PydanticField(
        None, description="Unique monster identifier"
    )

    monster_name: str = PydanticField(
        ..., description="Official monster name", examples=["Goblin", "Orc", "Dragon"]
    )

    armor_class: int = PydanticField(
        ..., ge=0, le=50, description="Monster's armor class", examples=[12, 15, 18]
    )

    hit_points: str = PydanticField(
        ...,
        description="Hit point range or average",
        examples=["7 (2d4)", "15 (2d8+6)", "100 (8d12+48)"],
    )

    strength: int = PydanticField(
        ..., ge=1, le=30, description="Strength ability score", examples=[8, 14, 20]
    )

    dexterity: int = PydanticField(
        ..., ge=1, le=30, description="Dexterity ability score", examples=[14, 10, 12]
    )

    constitution: int = PydanticField(
        ...,
        ge=1,
        le=30,
        description="Constitution ability score",
        examples=[10, 14, 18],
    )

    intelligence: int = PydanticField(
        ..., ge=1, le=30, description="Intelligence ability score", examples=[8, 10, 12]
    )

    wisdom: int = PydanticField(
        ..., ge=1, le=30, description="Wisdom ability score", examples=[8, 12, 14]
    )

    charisma: int = PydanticField(
        ..., ge=1, le=30, description="Charisma ability score", examples=[8, 10, 12]
    )

    challenge_rating: str = PydanticField(
        ..., description="Challenge rating", examples=["1/4", "1", "5", "10"]
    )

    actions: Optional[str] = PydanticField(
        None,
        description="Monster's actions and abilities",
        examples=[
            "Scimitar. Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6 + 2) slashing damage."
        ],
    )

    special_abilities: Optional[str] = PydanticField(
        None,
        description="Special abilities and traits",
        examples=[
            "Nimble Escape. The goblin can take the Disengage or Hide action as a bonus action on each of its turns."
        ],
    )

    description: Optional[str] = PydanticField(
        None,
        description="Monster description and background",
        examples=[
            "Goblins are small, green-skinned humanoids with a mischievous and cruel nature."
        ],
    )

    srd_compliance: SRDCompliance = PydanticField(
        ..., description="Licensing compliance information"
    )

    data_source: DataSource = PydanticField(
        ..., description="Source tracking information"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Record creation timestamp"
    )

    updated_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Record last update timestamp"
    )

    is_active: bool = PydanticField(
        default=True, description="Whether this monster is active and available"
    )


class Spell(BaseModel):
    """SRD spell data structure with compliance tracking."""

    spell_id: Optional[int] = PydanticField(None, description="Unique spell identifier")

    spell_name: str = PydanticField(
        ...,
        description="Official spell name",
        examples=["Fireball", "Magic Missile", "Cure Wounds"],
    )

    level: int = PydanticField(
        ...,
        ge=0,
        le=9,
        description="Spell level (0-9, where 0 is cantrip)",
        examples=[1, 3, 5],
    )

    school: str = PydanticField(
        ...,
        description="Magic school",
        examples=["Evocation", "Conjuration", "Necromancy", "Abjuration"],
    )

    casting_time: str = PydanticField(
        ...,
        description="Spell casting time",
        examples=["1 action", "1 bonus action", "1 minute", "10 minutes"],
    )

    range: str = PydanticField(
        ...,
        description="Spell range",
        examples=["60 feet", "Touch", "120 feet", "Self (30-foot radius)"],
    )

    components: str = PydanticField(
        ...,
        description="Spell components (V, S, M)",
        examples=["V, S, M (a pinch of sulfur)", "V, S", "V"],
    )

    duration: str = PydanticField(
        ...,
        description="Spell duration",
        examples=[
            "Instantaneous",
            "Concentration, up to 1 minute",
            "1 hour",
            "Until dispelled",
        ],
    )

    description: str = PydanticField(
        ...,
        description="Complete spell description and mechanics",
        examples=[
            "A bright streak flashes from your pointing finger to a point you choose within range..."
        ],
    )

    at_higher_levels: Optional[str] = PydanticField(
        None,
        description="Effects when cast at higher levels",
        examples=[
            "When you cast this spell using a spell slot of 4th level or higher, the damage increases by 1d6 for each slot level above 3rd."
        ],
    )

    classes: List[str] = PydanticField(
        default_factory=list,
        description="Character classes that can use this spell",
        examples=[["Wizard", "Sorcerer"], ["Cleric", "Druid"], ["Bard"]],
    )

    srd_compliance: SRDCompliance = PydanticField(
        ..., description="Licensing compliance information"
    )

    data_source: DataSource = PydanticField(
        ..., description="Source tracking information"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Record creation timestamp"
    )

    updated_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Record last update timestamp"
    )

    is_active: bool = PydanticField(
        default=True, description="Whether this spell is active and available"
    )


class Weapon(BaseModel):
    """SRD weapon data structure with compliance tracking."""

    weapon_id: Optional[int] = PydanticField(
        None, description="Unique weapon identifier"
    )

    weapon_name: str = PydanticField(
        ...,
        description="Official weapon name",
        examples=["Longsword", "Shortbow", "Quarterstaff"],
    )

    category: str = PydanticField(
        ...,
        description="Weapon category",
        examples=["Simple", "Martial", "Ranged", "Melee"],
    )

    cost: str = PydanticField(
        ...,
        description="Weapon cost in gold pieces",
        examples=["15 gp", "25 gp", "2 gp"],
    )

    damage: str = PydanticField(
        ...,
        description="Weapon damage dice and type",
        examples=["1d8 slashing", "1d6 piercing", "1d6 bludgeoning"],
    )

    weight: str = PydanticField(
        ..., description="Weapon weight", examples=["3 lb.", "2 lb.", "4 lb."]
    )

    properties: List[str] = PydanticField(
        default_factory=list,
        description="Weapon properties",
        examples=[
            ["Versatile (1d10)"],
            ["Ammunition (range 80/320)"],
            ["Light", "Finesse"],
        ],
    )

    description: Optional[str] = PydanticField(
        None,
        description="Weapon description and special rules",
        examples=["This sword is about 3½ feet in length."],
    )

    srd_compliance: SRDCompliance = PydanticField(
        ..., description="Licensing compliance information"
    )

    data_source: DataSource = PydanticField(
        ..., description="Source tracking information"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Record creation timestamp"
    )

    updated_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Record last update timestamp"
    )

    is_active: bool = PydanticField(
        default=True, description="Whether this weapon is active and available"
    )


# ======================================================================================
# Memory Management Models (for campaign memory and AI integration)
# ======================================================================================


class MemoryEvent(BaseModel):
    """Represents a historical event in the campaign chronicle."""

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

    participants: List[str] = PydanticField(..., description="Characters/NPCs involved")

    location: Optional[str] = PydanticField(
        None, description="Where the event occurred"
    )

    metadata: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Additional event data"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When memory was created"
    )

    version: int = PydanticField(default=1, description="Memory version for updates")


class MemoryFact(BaseModel):
    """Represents a persistent fact about the campaign world."""

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

    tags: List[str] = PydanticField(default_factory=list, description="Searchable tags")

    related_events: List[str] = PydanticField(
        default_factory=list, description="Related event IDs"
    )


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

    summary: str = PydanticField(..., description="Condensed memory summary for AI")

    context_size: int = PydanticField(..., description="Estimated token count")


class MemoryOperation(BaseModel):
    """Result of a memory CRUD operation."""

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


# Memory CRUD Request/Response Models
class CreateMemoryEventRequest(BaseModel):
    """Request to create a new memory event."""

    event_type: Literal["narrative", "combat", "social", "exploration"] = PydanticField(
        ..., description="Type of event"
    )

    description: str = PydanticField(
        ..., min_length=1, max_length=1000, description="Event description"
    )

    participants: List[str] = PydanticField(..., description="Characters/NPCs involved")

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


# ======================================================================================
# Discord Voice Integration Models (for voice channel management)
# ======================================================================================


class VoiceChannelInfo(BaseModel):
    """Information about a Discord voice channel."""

    channel_id: str = PydanticField(
        ..., description="Discord voice channel ID", pattern=r"^[0-9]+$"
    )

    guild_id: str = PydanticField(
        ..., description="Discord guild ID", pattern=r"^[0-9]+$"
    )

    channel_name: str = PydanticField(
        ..., description="Voice channel name", min_length=1, max_length=100
    )

    user_limit: Optional[int] = PydanticField(
        None, description="User limit for channel", ge=0, le=99
    )

    bitrate: int = PydanticField(..., description="Channel bitrate", ge=8000, le=512000)

    region: str = PydanticField(..., description="Voice region")

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When this info was retrieved"
    )


class VoiceConnection(BaseModel):
    """Represents an active voice connection."""

    connection_id: str = PydanticField(
        ...,
        description="Unique connection identifier",
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=128,
    )

    channel_id: str = PydanticField(
        ..., description="Connected voice channel ID", pattern=r"^[0-9]+$"
    )

    guild_id: str = PydanticField(
        ..., description="Discord guild ID", pattern=r"^[0-9]+$"
    )

    status: Literal["connecting", "connected", "disconnected", "error"] = PydanticField(
        ..., description="Connection status"
    )

    connected_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Connection start time"
    )

    participants: List[str] = PydanticField(
        default_factory=list, description="User IDs in voice"
    )

    last_activity: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Last voice activity"
    )

    error_message: Optional[str] = PydanticField(
        None, description="Last error message", max_length=500
    )

    disconnect_reason: Optional[str] = PydanticField(
        None, description="Reason for disconnection", max_length=200
    )

    connection_quality: Optional[Dict[str, Any]] = PydanticField(
        None, description="Connection quality metrics"
    )


class VoicePermission(BaseModel):
    """Voice channel permissions for users and bot."""

    user_id: str = PydanticField(..., description="User or bot ID", pattern=r"^[0-9]+$")

    can_connect: bool = PydanticField(..., description="Can connect to voice channel")

    can_speak: bool = PydanticField(..., description="Can speak in voice channel")

    can_mute_members: bool = PydanticField(..., description="Can mute other members")

    can_deafen_members: bool = PydanticField(
        ..., description="Can deafen other members"
    )

    can_move_members: bool = PydanticField(
        ..., description="Can move members between channels"
    )

    can_use_voice_activity: bool = PydanticField(
        ..., description="Can use voice activity detection"
    )

    can_priority_speaker: bool = PydanticField(
        ..., description="Can be priority speaker"
    )

    checked_at: datetime = PydanticField(
        default_factory=datetime.utcnow,
        description="When permissions were last checked",
    )


class AudioStreamInfo(BaseModel):
    """Information about an audio stream."""

    stream_id: str = PydanticField(
        ...,
        description="Unique stream identifier",
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=128,
    )

    user_id: str = PydanticField(
        ..., description="User ID of the stream source", pattern=r"^[0-9]+$"
    )

    channel_id: str = PydanticField(
        ..., description="Voice channel ID", pattern=r"^[0-9]+$"
    )

    format: str = PydanticField(..., description="Audio format (e.g., 's16le', 'opus')")

    sample_rate: int = PydanticField(
        ..., description="Sample rate in Hz", ge=8000, le=192000
    )

    channels: int = PydanticField(
        ..., description="Number of audio channels", ge=1, le=2
    )

    bitrate: int = PydanticField(
        ..., description="Audio bitrate in bits per second", ge=8000, le=512000
    )

    started_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When the stream started"
    )

    last_activity: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Last audio activity"
    )

    is_speaking: bool = PydanticField(
        ..., description="Whether user is currently speaking"
    )

    volume_level: float = PydanticField(
        ..., description="Current volume level (0.0 to 1.0)", ge=0.0, le=1.0
    )

    silence_threshold: float = PydanticField(
        ..., description="Silence detection threshold", ge=0.0, le=1.0
    )


class VoiceSession(BaseModel):
    """Represents a complete voice session."""

    session_id: str = PydanticField(
        ...,
        description="Unique session identifier",
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=128,
    )

    guild_id: str = PydanticField(
        ..., description="Discord guild ID", pattern=r"^[0-9]+$"
    )

    channel_id: str = PydanticField(
        ..., description="Voice channel ID", pattern=r"^[0-9]+$"
    )

    started_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Session start time"
    )

    ended_at: Optional[datetime] = PydanticField(None, description="Session end time")

    total_participants: int = PydanticField(
        0, description="Total unique participants", ge=0
    )

    max_concurrent_participants: int = PydanticField(
        0, description="Maximum concurrent participants", ge=0
    )

    total_audio_time: float = PydanticField(
        0.0, description="Total audio time in seconds", ge=0.0
    )

    connection_issues: List[Dict[str, Any]] = PydanticField(
        default_factory=list, description="Connection issues encountered"
    )

    audio_quality_metrics: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Audio quality metrics"
    )

    status: Literal["active", "ended", "error"] = PydanticField(
        ..., description="Session status"
    )


# Voice Command Request/Response Models
class VoiceJoinRequest(BaseModel):
    """Request to join a voice channel."""

    channel_id: str = PydanticField(
        ..., description="Voice channel ID to join", pattern=r"^[0-9]+$"
    )

    user_id: str = PydanticField(
        ..., description="User requesting to join", pattern=r"^[0-9]+$"
    )

    force: bool = PydanticField(
        False, description="Force join even if already connected"
    )

    self_deaf: bool = PydanticField(False, description="Join deafened")

    self_mute: bool = PydanticField(False, description="Join muted")


class VoiceLeaveRequest(BaseModel):
    """Request to leave voice channel."""

    user_id: str = PydanticField(
        ..., description="User requesting to leave", pattern=r"^[0-9]+$"
    )

    reason: Optional[str] = PydanticField(
        None, description="Reason for leaving", max_length=200
    )


class VoiceStatusResponse(BaseModel):
    """Response containing voice connection status."""

    connected: bool = PydanticField(
        ..., description="Whether bot is connected to voice"
    )

    channel_id: Optional[str] = PydanticField(
        None, description="Current voice channel ID"
    )

    channel_name: Optional[str] = PydanticField(
        None, description="Current voice channel name"
    )

    guild_id: Optional[str] = PydanticField(None, description="Current guild ID")

    participant_count: int = PydanticField(
        0, description="Number of participants", ge=0
    )

    participants: List[str] = PydanticField(
        default_factory=list, description="List of participant user IDs"
    )

    connection_quality: Optional[Dict[str, Any]] = PydanticField(
        None, description="Connection quality information"
    )

    connected_at: Optional[datetime] = PydanticField(
        None, description="When connection was established"
    )


class VoiceChannelResponse(BaseModel):
    """Response containing voice channel information."""

    channel_id: str = PydanticField(..., description="Voice channel ID")

    channel_name: str = PydanticField(..., description="Voice channel name")

    user_limit: Optional[int] = PydanticField(None, description="User limit")

    bitrate: int = PydanticField(..., description="Channel bitrate")

    region: str = PydanticField(..., description="Voice region")

    member_count: int = PydanticField(0, description="Current member count", ge=0)

    bot_can_join: bool = PydanticField(
        ..., description="Whether bot has permission to join"
    )

    bot_permissions: Optional[Dict[str, bool]] = PydanticField(
        None, description="Bot's permissions in the channel"
    )


class VoiceCommandResponse(BaseModel):
    """Generic response for voice commands."""

    success: bool = PydanticField(..., description="Whether the command was successful")

    message: str = PydanticField(
        ..., description="Response message", min_length=1, max_length=500
    )

    data: Optional[Dict[str, Any]] = PydanticField(
        None, description="Additional response data"
    )

    error_code: Optional[str] = PydanticField(
        None, description="Error code if not successful", max_length=100
    )


class MemoryQueryRequest(BaseModel):
    """Request to query memory data."""

    query_type: Literal["events", "facts", "context"] = PydanticField(
        ..., description="Type of memory to query"
    )

    filters: Optional[Dict[str, Any]] = PydanticField(None, description="Query filters")

    limit: Optional[int] = PydanticField(
        100, ge=1, le=1000, description="Maximum results to return"
    )

    include_metadata: Optional[bool] = PydanticField(
        True, description="Whether to include metadata in results"
    )


# ======================================================================================
# Performance Optimization & Quality Enhancement Models
# ======================================================================================


class VoiceLatencyMetrics(BaseModel):
    """Voice interaction latency tracking."""

    session_id: str = PydanticField(..., description="Voice session identifier")

    user_speech_start: datetime = PydanticField(
        ..., description="User speech start time"
    )

    transcription_complete: Optional[datetime] = PydanticField(
        None, description="STT completion time"
    )

    ai_processing_start: Optional[datetime] = PydanticField(
        None, description="AI processing start time"
    )

    ai_response_complete: Optional[datetime] = PydanticField(
        None, description="AI response completion time"
    )

    tts_generation_complete: Optional[datetime] = PydanticField(
        None, description="TTS completion time"
    )

    audio_playback_start: Optional[datetime] = PydanticField(
        None, description="Audio playback start time"
    )

    total_latency: Optional[float] = PydanticField(
        None, description="Total roundtrip latency in seconds"
    )

    stt_latency: Optional[float] = PydanticField(
        None, description="STT processing latency in seconds"
    )

    ai_latency: Optional[float] = PydanticField(
        None, description="AI processing latency in seconds"
    )

    tts_latency: Optional[float] = PydanticField(
        None, description="TTS generation latency in seconds"
    )

    audio_delivery_latency: Optional[float] = PydanticField(
        None, description="Audio delivery latency in seconds"
    )

    network_latency: Optional[float] = PydanticField(
        None, description="Network transmission latency in seconds"
    )

    processing_stage: str = PydanticField(
        default="speech_start", description="Current processing stage"
    )

    correlation_id: Optional[str] = PydanticField(
        None, description="Correlation ID for tracing"
    )

    metadata: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Additional latency metadata"
    )


class AudioQualityMetrics(BaseModel):
    """Audio quality assessment metrics."""

    session_id: str = PydanticField(..., description="Voice session identifier")

    transcription_accuracy: Optional[float] = PydanticField(
        None, ge=0.0, le=1.0, description="STT accuracy score"
    )

    voice_clarity: Optional[float] = PydanticField(
        None, ge=0.0, le=5.0, description="Voice synthesis clarity rating"
    )

    audio_artifacts: int = PydanticField(
        default=0, ge=0, description="Number of audio artifacts detected"
    )

    noise_level: Optional[float] = PydanticField(
        None, ge=0.0, le=1.0, description="Background noise level (0.0 to 1.0)"
    )

    signal_to_noise_ratio: Optional[float] = PydanticField(
        None, description="Signal-to-noise ratio in dB"
    )

    audio_bitrate: Optional[int] = PydanticField(
        None, description="Audio bitrate in bits per second"
    )

    sample_rate: Optional[int] = PydanticField(
        None, description="Audio sample rate in Hz"
    )

    audio_format: Optional[str] = PydanticField(None, description="Audio format used")

    user_feedback: Optional[str] = PydanticField(
        None, description="User feedback on quality"
    )

    quality_score: Optional[float] = PydanticField(
        None, ge=0.0, le=1.0, description="Overall quality score"
    )

    provider_performance: Dict[str, Any] = PydanticField(
        default_factory=dict, description="Provider-specific performance metrics"
    )

    timestamp: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Metrics collection timestamp"
    )

    correlation_id: Optional[str] = PydanticField(
        None, description="Correlation ID for tracing"
    )


class VoiceSessionConfig(BaseModel):
    """Voice session configuration and limits."""

    max_concurrent_sessions: int = PydanticField(
        default=10, ge=1, le=100, description="Maximum concurrent voice sessions"
    )

    session_timeout: int = PydanticField(
        default=3600, ge=300, le=86400, description="Session timeout in seconds"
    )

    max_session_duration: int = PydanticField(
        default=7200,
        ge=600,
        le=43200,
        description="Maximum session duration in seconds",
    )

    audio_quality_threshold: float = PydanticField(
        default=0.8, ge=0.0, le=1.0, description="Minimum audio quality threshold"
    )

    privacy_mode_enabled: bool = PydanticField(
        default=True, description="Privacy mode enabled"
    )

    latency_threshold: float = PydanticField(
        default=4.0,
        ge=0.1,
        le=30.0,
        description="Maximum acceptable latency in seconds (NFR1)",
    )

    audio_retention_days: int = PydanticField(
        default=7, ge=0, le=365, description="Audio data retention period in days"
    )

    enable_performance_monitoring: bool = PydanticField(
        default=True, description="Enable detailed performance monitoring"
    )

    enable_quality_assessment: bool = PydanticField(
        default=True, description="Enable audio quality assessment"
    )


class PerformanceAlert(BaseModel):
    """Performance alert configuration and state."""

    alert_id: str = PydanticField(..., description="Unique alert identifier")

    alert_type: Literal["latency", "quality", "error_rate", "resource_usage"] = (
        PydanticField(..., description="Type of performance alert")
    )

    severity: Literal["low", "medium", "high", "critical"] = PydanticField(
        ..., description="Alert severity level"
    )

    threshold: float = PydanticField(..., description="Alert threshold value")

    current_value: float = PydanticField(..., description="Current measured value")

    session_id: Optional[str] = PydanticField(None, description="Associated session ID")

    message: str = PydanticField(..., description="Alert message")

    triggered_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When the alert was triggered"
    )

    resolved_at: Optional[datetime] = PydanticField(
        None, description="When the alert was resolved"
    )

    resolution_notes: Optional[str] = PydanticField(
        None, description="Notes about alert resolution"
    )


class PerformanceReport(BaseModel):
    """Performance report with aggregated metrics."""

    report_id: str = PydanticField(..., description="Unique report identifier")

    time_range_start: datetime = PydanticField(
        ..., description="Report time range start"
    )

    time_range_end: datetime = PydanticField(..., description="Report time range end")

    total_voice_sessions: int = PydanticField(
        default=0, description="Total number of voice sessions"
    )

    average_latency: Optional[float] = PydanticField(
        None, description="Average total latency in seconds"
    )

    p95_latency: Optional[float] = PydanticField(
        None, description="95th percentile latency in seconds"
    )

    p99_latency: Optional[float] = PydanticField(
        None, description="99th percentile latency in seconds"
    )

    sessions_meeting_latency_target: int = PydanticField(
        default=0, description="Sessions meeting latency target (< 4s)"
    )

    average_quality_score: Optional[float] = PydanticField(
        None, description="Average audio quality score"
    )

    stt_success_rate: Optional[float] = PydanticField(
        None, description="STT success rate"
    )

    tts_success_rate: Optional[float] = PydanticField(
        None, description="TTS success rate"
    )

    error_rate: Optional[float] = PydanticField(None, description="Overall error rate")

    provider_performance: Dict[str, Dict[str, Any]] = PydanticField(
        default_factory=dict, description="Provider-specific performance metrics"
    )

    alerts_generated: int = PydanticField(
        default=0, description="Number of alerts generated in period"
    )

    critical_issues: int = PydanticField(
        default=0, description="Number of critical issues identified"
    )

    recommendations: List[str] = PydanticField(
        default_factory=list, description="Performance improvement recommendations"
    )


class PrivacyComplianceRecord(BaseModel):
    """Privacy compliance tracking for voice data."""

    session_id: str = PydanticField(..., description="Voice session identifier")

    user_id: str = PydanticField(..., description="User identifier")

    data_collection_timestamp: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When audio data was collected"
    )

    data_retention_period_days: int = PydanticField(
        default=7, description="Data retention period in days"
    )

    data_deletion_date: datetime = PydanticField(
        ..., description="Scheduled data deletion date"
    )

    privacy_consent_obtained: bool = PydanticField(
        default=False, description="Whether user consent was obtained"
    )

    consent_timestamp: Optional[datetime] = PydanticField(
        None, description="When consent was obtained"
    )

    data_encrypted: bool = PydanticField(
        default=False, description="Whether data is encrypted"
    )

    encryption_method: Optional[str] = PydanticField(
        None, description="Encryption method used"
    )

    compliance_officer: str = PydanticField(
        default="system", description="Person responsible for compliance"
    )

    audit_trail: List[Dict[str, Any]] = PydanticField(
        default_factory=list, description="Audit trail of data access and processing"
    )


# ======================================================================================
# Voice Command Processing Models
# ======================================================================================


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


# ======================================================================================
# Advanced Voice Features Models
# ======================================================================================


class SpeakerProfile(BaseModel):
    """Voice profile for speaker identification."""

    profile_id: str = PydanticField(
        ..., description="Unique speaker profile identifier"
    )

    user_id: str = PydanticField(..., description="Associated user ID")

    voice_print: bytes = PydanticField(..., description="Voice biometric data")

    voice_characteristics: Dict[str, float] = PydanticField(
        default_factory=dict,
        description="Voice characteristics (pitch, tone, speed, etc.)",
        examples={
            "average_pitch": 120.5,
            "pitch_variance": 15.2,
            "speaking_rate": 150.0,
            "tone_stability": 0.85,
        },
    )

    sample_audio_clips: List[bytes] = PydanticField(
        default_factory=list, description="Sample audio clips for voice training"
    )

    confidence_threshold: float = PydanticField(
        default=0.8, ge=0.0, le=1.0, description="Identification confidence threshold"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When profile was created"
    )

    last_updated: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When profile was last updated"
    )

    total_training_samples: int = PydanticField(
        default=0, description="Number of training samples"
    )

    identification_accuracy: float = PydanticField(
        default=0.0, ge=0.0, le=1.0, description="Speaker identification accuracy"
    )

    last_identification: Optional[datetime] = PydanticField(
        None, description="When speaker was last identified"
    )


class VoiceActivitySegment(BaseModel):
    """Voice activity detection segment."""

    segment_id: str = PydanticField(..., description="Unique segment identifier")

    session_id: str = PydanticField(..., description="Voice session identifier")

    speaker_id: Optional[str] = PydanticField(None, description="Identified speaker ID")

    start_time: datetime = PydanticField(..., description="Segment start time")

    end_time: datetime = PydanticField(..., description="Segment end time")

    confidence: float = PydanticField(
        ..., ge=0.0, le=1.0, description="VAD confidence score"
    )

    energy_level: float = PydanticField(..., description="Audio energy level")

    noise_level: float = PydanticField(..., description="Background noise level")

    overlap_detected: bool = PydanticField(
        default=False, description="Whether speaker overlap was detected"
    )

    speaker_confidence: Optional[float] = PydanticField(
        None, ge=0.0, le=1.0, description="Speaker identification confidence"
    )

    audio_features: Dict[str, float] = PydanticField(
        default_factory=dict,
        description="Extracted audio features",
        examples={
            "mfcc_mean": 0.5,
            "spectral_centroid": 2500.0,
            "zero_crossing_rate": 0.15,
        },
    )

    duration: float = PydanticField(..., description="Segment duration in seconds")


class MultiUserConversation(BaseModel):
    """Multi-user conversation context."""

    conversation_id: str = PydanticField(
        ..., description="Unique conversation identifier"
    )

    session_id: str = PydanticField(..., description="Voice session identifier")

    active_speakers: List[str] = PydanticField(
        default_factory=list, description="Currently active speaker IDs"
    )

    speaker_segments: List[VoiceActivitySegment] = PydanticField(
        default_factory=list, description="Voice activity segments"
    )

    conversation_flow: List[Dict[str, Any]] = PydanticField(
        default_factory=list,
        description="Conversation flow and turn-taking events",
        examples=[
            {
                "speaker_id": "user_123",
                "start_time": "2025-08-22T21:35:20Z",
                "end_time": "2025-08-22T21:35:25Z",
                "text": "I want to attack the goblin",
                "sentiment": 0.2,
            }
        ],
    )

    turn_taking_events: List[Dict[str, Any]] = PydanticField(
        default_factory=list, description="Turn-taking events and transitions"
    )

    engagement_metrics: Dict[str, float] = PydanticField(
        default_factory=dict,
        description="Group engagement metrics",
        examples={
            "average_participation": 0.75,
            "turn_taking_efficiency": 0.85,
            "conversation_balance": 0.70,
            "engagement_trend": 0.05,
        },
    )

    started_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When conversation started"
    )

    last_activity: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When last activity occurred"
    )

    total_speakers: int = PydanticField(
        default=0, description="Total number of speakers"
    )

    total_turns: int = PydanticField(
        default=0, description="Total number of conversation turns"
    )

    average_turn_duration: float = PydanticField(
        default=0.0, description="Average turn duration in seconds"
    )

    dominant_speaker: Optional[str] = PydanticField(
        None, description="Most active speaker ID"
    )


class AudioMixConfiguration(BaseModel):
    """Audio mixing configuration for multi-user scenarios."""

    mix_id: str = PydanticField(..., description="Unique mix configuration identifier")

    session_id: str = PydanticField(..., description="Voice session identifier")

    input_streams: List[str] = PydanticField(..., description="Input audio stream IDs")

    output_stream: str = PydanticField(..., description="Output mixed stream ID")

    volume_levels: Dict[str, float] = PydanticField(
        default_factory=dict, description="Per-stream volume levels (0.0 to 1.0)"
    )

    spatial_positions: Dict[str, Dict[str, float]] = PydanticField(
        default_factory=dict,
        description="3D spatial positions for each stream",
        examples={
            "user_123": {
                "x": 1.0,
                "y": 0.0,
                "z": 0.0,
                "azimuth": 30.0,
                "elevation": 0.0,
            }
        },
    )

    priority_speakers: List[str] = PydanticField(
        default_factory=list, description="Priority speaker order for ducking"
    )

    ducking_enabled: bool = PydanticField(
        default=True, description="Enable audio ducking for priority speakers"
    )

    ducking_threshold: float = PydanticField(
        default=0.7, ge=0.0, le=1.0, description="Ducking trigger threshold"
    )

    ducking_amount: float = PydanticField(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="How much to duck other streams (0.0 = no ducking, 1.0 = mute)",
    )

    room_simulation: bool = PydanticField(
        default=False, description="Enable room acoustics simulation"
    )

    room_size: str = PydanticField(
        default="medium",
        description="Room size for acoustics simulation",
        examples=["small", "medium", "large", "hall"],
    )

    reverb_enabled: bool = PydanticField(
        default=True, description="Enable reverb effects"
    )

    reverb_decay: float = PydanticField(
        default=0.5, ge=0.0, le=1.0, description="Reverb decay time"
    )


class ConversationIntelligenceData(BaseModel):
    """Conversation intelligence and analysis data."""

    conversation_id: str = PydanticField(..., description="Conversation identifier")

    session_id: str = PydanticField(..., description="Voice session identifier")

    sentiment_analysis: Dict[str, float] = PydanticField(
        default_factory=dict,
        description="Sentiment analysis results",
        examples={
            "overall_sentiment": 0.3,
            "positive_ratio": 0.4,
            "negative_ratio": 0.2,
            "neutral_ratio": 0.4,
        },
    )

    engagement_scores: Dict[str, float] = PydanticField(
        default_factory=dict,
        description="Engagement scores by speaker",
        examples={"user_123": 0.75, "user_456": 0.85, "user_789": 0.60},
    )

    topic_detection: List[Dict[str, Any]] = PydanticField(
        default_factory=list,
        description="Detected conversation topics",
        examples=[
            {
                "topic": "combat_strategy",
                "confidence": 0.8,
                "start_time": "2025-08-22T21:35:20Z",
                "end_time": "2025-08-22T21:35:35Z",
            }
        ],
    )

    rhythm_analysis: Dict[str, Any] = PydanticField(
        default_factory=dict,
        description="Conversation rhythm and pacing analysis",
        examples={
            "average_pause_duration": 1.2,
            "turn_taking_speed": 0.8,
            "interruption_rate": 0.15,
            "conversation_tempo": "moderate",
        },
    )

    highlight_moments: List[Dict[str, Any]] = PydanticField(
        default_factory=list,
        description="Identified conversation highlights",
        examples=[
            {
                "type": "exciting_moment",
                "timestamp": "2025-08-22T21:35:30Z",
                "description": "Player successfully lands critical hit",
                "intensity": 0.9,
            }
        ],
    )

    summary: str = PydanticField(
        default="", description="Generated conversation summary"
    )

    key_insights: List[str] = PydanticField(
        default_factory=list, description="Key insights from conversation analysis"
    )

    generated_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When analysis was generated"
    )


# ======================================================================================
# STT/TTS Service Models (for speech-to-text and text-to-speech services)
# ======================================================================================


class AudioTranscriptionRequest(BaseModel):
    """Request to transcribe audio to text."""

    audio_data: bytes = PydanticField(..., description="Raw audio data to transcribe")

    audio_format: Literal["wav", "mp3", "ogg", "flac", "webm"] = PydanticField(
        ..., description="Audio format of the input data"
    )

    sample_rate: int = PydanticField(
        ..., description="Sample rate in Hz", ge=8000, le=192000
    )

    channels: int = PydanticField(
        ..., description="Number of audio channels", ge=1, le=2
    )

    language: Optional[str] = PydanticField(
        "en-US",
        description="Language code for transcription",
        pattern=r"^[a-z]{2}-[A-Z]{2}$",
    )

    provider: Optional[str] = PydanticField(
        "auto", description="Preferred STT provider"
    )

    session_id: Optional[str] = PydanticField(
        None, description="Session identifier for tracking"
    )

    user_id: Optional[str] = PydanticField(None, description="User identifier")

    metadata: Optional[Dict[str, Any]] = PydanticField(
        None, description="Additional request metadata"
    )


class TranscriptionResult(BaseModel):
    """Result of speech-to-text transcription."""

    text: str = PydanticField(..., description="Transcribed text", min_length=1)

    confidence: float = PydanticField(
        ..., description="Confidence score (0.0 to 1.0)", ge=0.0, le=1.0
    )

    language: str = PydanticField(
        ...,
        description="Detected or specified language",
        pattern=r"^[a-z]{2}-[A-Z]{2}$",
    )

    duration: float = PydanticField(
        ..., description="Audio duration in seconds", ge=0.0
    )

    provider: str = PydanticField(..., description="STT provider used")

    word_timestamps: Optional[List[Dict[str, Any]]] = PydanticField(
        None, description="Word-level timestamps"
    )

    segments: Optional[List[Dict[str, Any]]] = PydanticField(
        None, description="Segment-level results"
    )

    processing_time: float = PydanticField(
        ..., description="Processing time in seconds", ge=0.0
    )

    error: Optional[str] = PydanticField(
        None, description="Error message if transcription failed"
    )


class TextToSpeechRequest(BaseModel):
    """Request to convert text to speech."""

    text: str = PydanticField(
        ..., description="Text to convert to speech", min_length=1, max_length=4000
    )

    voice: Optional[str] = PydanticField(
        "default", description="Voice identifier to use"
    )

    language: Optional[str] = PydanticField(
        "en-US",
        description="Language code for speech synthesis",
        pattern=r"^[a-z]{2}-[A-Z]{2}$",
    )

    speed: Optional[float] = PydanticField(
        1.0, description="Speech speed (0.5 to 2.0)", ge=0.5, le=2.0
    )

    pitch: Optional[float] = PydanticField(
        1.0, description="Voice pitch (0.5 to 2.0)", ge=0.5, le=2.0
    )

    volume: Optional[float] = PydanticField(
        1.0, description="Volume level (0.0 to 1.0)", ge=0.0, le=1.0
    )

    provider: Optional[str] = PydanticField(
        "auto", description="Preferred TTS provider"
    )

    output_format: Optional[Literal["wav", "mp3", "ogg", "flac"]] = PydanticField(
        "wav", description="Output audio format"
    )

    session_id: Optional[str] = PydanticField(
        None, description="Session identifier for tracking"
    )

    user_id: Optional[str] = PydanticField(None, description="User identifier")

    metadata: Optional[Dict[str, Any]] = PydanticField(
        None, description="Additional request metadata"
    )


class SpeechSynthesisResult(BaseModel):
    """Result of text-to-speech synthesis."""

    audio_data: bytes = PydanticField(..., description="Generated audio data")

    audio_format: str = PydanticField(..., description="Format of the generated audio")

    sample_rate: int = PydanticField(..., description="Sample rate in Hz")

    channels: int = PydanticField(..., description="Number of audio channels")

    duration: float = PydanticField(
        ..., description="Audio duration in seconds", ge=0.0
    )

    voice_used: str = PydanticField(..., description="Voice identifier used")

    provider: str = PydanticField(..., description="TTS provider used")

    processing_time: float = PydanticField(
        ..., description="Processing time in seconds", ge=0.0
    )

    file_size: int = PydanticField(
        ..., description="Size of generated audio in bytes", ge=0
    )

    error: Optional[str] = PydanticField(
        None, description="Error message if synthesis failed"
    )


class AudioProcessingConfig(BaseModel):
    """Configuration for audio processing operations."""

    chunk_size: int = PydanticField(
        1024, description="Audio chunk size for processing", ge=64, le=8192
    )

    overlap_size: int = PydanticField(
        256, description="Overlap size between chunks", ge=0, le=4096
    )

    silence_threshold: float = PydanticField(
        0.01, description="Threshold for silence detection (0.0 to 1.0)", ge=0.0, le=1.0
    )

    min_speech_duration: float = PydanticField(
        0.1, description="Minimum speech duration in seconds", ge=0.0, le=5.0
    )

    max_speech_duration: float = PydanticField(
        30.0, description="Maximum speech duration in seconds", ge=1.0, le=300.0
    )

    vad_mode: Literal["aggressive", "normal", "light"] = PydanticField(
        "normal", description="Voice activity detection sensitivity"
    )

    noise_reduction: bool = PydanticField(True, description="Enable noise reduction")

    normalize_audio: bool = PydanticField(
        True, description="Enable audio normalization"
    )


class AudioStreamInfo(BaseModel):
    """Information about an audio stream for STT processing."""

    stream_id: str = PydanticField(
        ...,
        description="Unique stream identifier",
        pattern=r"^[a-zA-Z0-9_-]+$",
        min_length=1,
        max_length=128,
    )

    user_id: str = PydanticField(
        ..., description="User ID of the stream source", pattern=r"^[0-9]+$"
    )

    channel_id: str = PydanticField(
        ..., description="Voice channel ID", pattern=r"^[0-9]+$"
    )

    session_id: str = PydanticField(..., description="Voice session identifier")

    format: str = PydanticField(..., description="Audio format (e.g., 's16le', 'opus')")

    sample_rate: int = PydanticField(
        ..., description="Sample rate in Hz", ge=8000, le=192000
    )

    channels: int = PydanticField(
        ..., description="Number of audio channels", ge=1, le=2
    )

    started_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="When the stream started"
    )

    last_activity: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Last audio activity"
    )

    is_active: bool = PydanticField(
        True, description="Whether stream is currently active"
    )

    buffer_size: int = PydanticField(
        0, description="Current buffer size in bytes", ge=0
    )

    processed_chunks: int = PydanticField(
        0, description="Number of chunks processed", ge=0
    )

    total_transcriptions: int = PydanticField(
        0, description="Total transcriptions generated", ge=0
    )

    average_confidence: float = PydanticField(
        0.0, description="Average transcription confidence", ge=0.0, le=1.0
    )


class ProviderHealthStatus(BaseModel):
    """Health status for STT/TTS providers."""

    provider_name: str = PydanticField(..., description="Name of the provider")

    service_type: Literal["stt", "tts"] = PydanticField(
        ..., description="Type of service"
    )

    status: Literal["healthy", "degraded", "unhealthy"] = PydanticField(
        ..., description="Current health status"
    )

    response_time: float = PydanticField(
        ..., description="Average response time in seconds", ge=0.0
    )

    success_rate: float = PydanticField(
        ..., description="Success rate (0.0 to 1.0)", ge=0.0, le=1.0
    )

    last_check: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Last health check timestamp"
    )

    consecutive_failures: int = PydanticField(
        0, description="Number of consecutive failures", ge=0
    )

    total_requests: int = PydanticField(0, description="Total requests made", ge=0)

    error_message: Optional[str] = PydanticField(
        None, description="Last error message", max_length=500
    )

    is_primary: bool = PydanticField(
        False, description="Whether this is the primary provider"
    )


class STTServiceStatus(BaseModel):
    """Overall status of the STT service."""

    is_available: bool = PydanticField(
        ..., description="Whether STT service is available"
    )

    active_streams: int = PydanticField(
        0, description="Number of active audio streams", ge=0
    )

    queued_requests: int = PydanticField(
        0, description="Number of queued transcription requests", ge=0
    )

    healthy_providers: int = PydanticField(
        0, description="Number of healthy providers", ge=0
    )

    total_providers: int = PydanticField(
        0, description="Total number of configured providers", ge=0
    )

    average_response_time: float = PydanticField(
        0.0, description="Average response time across all providers", ge=0.0
    )

    last_activity: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Last STT service activity"
    )

    service_uptime: float = PydanticField(
        0.0, description="Service uptime in seconds", ge=0.0
    )


class TTSServiceStatus(BaseModel):
    """Overall status of the TTS service."""

    is_available: bool = PydanticField(
        ..., description="Whether TTS service is available"
    )

    active_syntheses: int = PydanticField(
        0, description="Number of active speech syntheses", ge=0
    )

    queued_requests: int = PydanticField(
        0, description="Number of queued synthesis requests", ge=0
    )

    healthy_providers: int = PydanticField(
        0, description="Number of healthy providers", ge=0
    )

    total_providers: int = PydanticField(
        0, description="Total number of configured providers", ge=0
    )

    average_response_time: float = PydanticField(
        0.0, description="Average response time across all providers", ge=0.0
    )

    last_activity: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Last TTS service activity"
    )

    service_uptime: float = PydanticField(
        0.0, description="Service uptime in seconds", ge=0.0
    )
