"""
Core Database Models
SQLModel tables for the main entities in the system.
"""

import json
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from packages.shared.models.game.equipment_models import CharacterEquipment

from pydantic import ConfigDict, SecretStr
from sqlalchemy import (  # Import Integer and DateTime
    Column,
    Computed,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    Mapped,
    validates,  # Import validates from sqlalchemy.orm
)
from sqlmodel import Field as SQLField, Relationship, SQLModel

from packages.shared.models.game.gameplay_links import (
    CharacterProficiencyLink,
    ProficiencyLevel,
)
from packages.shared.models.game.equipment_models import DamageType

# from packages.shared.models.game.gameplay_models import Background, Race


class Condition(Enum):
    BLINDED = "blinded"
    CHARMED = "charmed"
    DEAFENED = "deafened"
    FRIGHTENED = "frightened"
    GRAPPLED = "grappled"
    INCAPACITATED = "incapacitated"
    INVISIBLE = "invisible"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    POISONED = "poisoned"
    PRONE = "prone"
    RESTRAINED = "restrained"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"


# Attack Model
class Attack(SQLModel, table=True):
    model_config = ConfigDict(
        ignored_types=(hybrid_property,)
    )  # Ignore hybrid properties as fields

    id: Optional[int] = SQLField(default=None, primary_key=True)
    name: str = SQLField(..., min_length=1, max_length=100)
    bonus: int = SQLField(default=0)
    damage_dice: str = SQLField(
        ..., max_length=50, description="Dice notation, e.g., '1d8+2'"
    )
    damage_type_index: Optional[str] = SQLField(
        default=None, foreign_key="damage_types.index"
    )
    damage_type: Mapped[Optional["DamageType"]] = Relationship()
    range: int = SQLField(default=5, ge=0, description="Range in feet (5 for melee)")

    character_id: Optional[int] = SQLField(
        default=None, foreign_key="characters.character_id"
    )
    character: Mapped[Optional["Character"]] = Relationship(back_populates="attacks")

    @hybrid_property
    def average_damage(self) -> float:
        # Simple parser for "XdY+Z" or "XdY"
        parts = self.damage_dice.split("+")
        dice_part = parts[0]
        modifier = int(parts[1]) if len(parts) > 1 else 0

        if "d" in dice_part:
            num_dice, die_type = map(int, dice_part.split("d"))
            return (num_dice * (die_type + 1) / 2) + modifier
        return float(modifier)  # If no dice, just the modifier

    @hybrid_property
    def is_ranged(self) -> bool:
        return self.range > 5

    def model_dump_clean(self) -> Dict[str, Any]:
        """Dump model without relationship fields that could cause circular references."""
        return {
            k: v
            for k, v in self.model_dump().items()
            if k not in ["character", "character_id"]
        }





# Server Configuration Model
class Server(SQLModel, table=True):
    __tablename__ = "keys"
    server_id: str = SQLField(primary_key=True)
    api_key: SecretStr = SQLField(sa_column=Column(String(255)), default=None)
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
    """Enhanced Character with computed columns and advanced patterns"""

    model_config = ConfigDict(
        ignored_types=(hybrid_property,)
    )  # Ignore hybrid properties as fields

    __tablename__ = "characters"

    # Your existing fields
    character_id: Optional[int] = SQLField(default=None, primary_key=True)
    name: str = SQLField(..., min_length=1, max_length=50)
    character_url: Optional[str] = SQLField(default=None)
    player_id: Optional[str] = SQLField(default=None, foreign_key="players.player_id")
    campaign_id: Optional[int] = SQLField(
        default=None, foreign_key="campaigns.campaign_id"
    )

    # Creation Fields
    races_index: Optional[str] = SQLField(default=None, foreign_key="races.index")
    dnd_races: Optional["Race"] = Relationship(back_populates="characters")  # type: ignore # noqa: F821
    class_index: Optional[str] = SQLField(default=None, foreign_key="classes.index")
    dnd_class: Optional["Class"] = Relationship(back_populates="characters")  # type: ignore # noqa: F821
    subclass: Optional[str] = SQLField(default=None, max_length=50)
    background_index: Optional[str] = SQLField(
        default=None, foreign_key="backgrounds.index"
    )
    dnd_background: Optional["Background"] = Relationship(back_populates="characters")  # type: ignore # noqa: F821

    # Core D&D Stats
    level: int = SQLField(default=1, ge=1, le=20)
    hp: int = SQLField(default=10, ge=0)
    max_hp: int = SQLField(default=10, ge=1)
    ac: int = SQLField(default=10, ge=1, le=30)

    # Ability Scores
    strength: int = SQLField(default=10, ge=1, le=30)
    dexterity: int = SQLField(default=10, ge=1, le=30)
    constitution: int = SQLField(default=10, ge=1, le=30)
    intelligence: int = SQLField(default=10, ge=1, le=30)
    wisdom: int = SQLField(default=10, ge=1, le=30)
    charisma: int = SQLField(default=10, ge=1, le=30)

    # COMPUTED COLUMNS - Stored in DB for performance!
    str_modifier: int = SQLField(
        sa_column=Column(
            "str_modifier",
            Integer,
            Computed("((strength - 10) / 2)"),
        )
    )
    dex_modifier: int = SQLField(
        sa_column=Column(
            "dex_modifier",
            Integer,
            Computed("((dexterity - 10) / 2)"),
        )
    )
    con_modifier: int = SQLField(
        sa_column=Column(
            "con_modifier",
            Integer,
            Computed("((constitution - 10) / 2)"),
        )
    )
    int_modifier: int = SQLField(
        sa_column=Column(
            "int_modifier",
            Integer,
            Computed("((intelligence - 10) / 2)"),
        )
    )
    wis_modifier: int = SQLField(
        sa_column=Column(
            "wis_modifier",
            Integer,
            Computed("((wisdom - 10) / 2)"),
        )
    )
    cha_modifier: int = SQLField(
        sa_column=Column(
            "cha_modifier",
            Integer,
            Computed("((charisma - 10) / 2)"),
        )
    )

    proficiency_bonus: int = SQLField(
        sa_column=Column(
            "proficiency_bonus",
            Integer,
            # Proficiency bonus = (level - 1) / 4 + 2, rounded up
            Computed("((level - 1) / 4 + 2)"),
        )
    )

    proficiency_links: Mapped[List["CharacterProficiencyLink"]] = Relationship(
        back_populates="character", sa_relationship_kwargs={"lazy": "selectin"}
    )

    # Advanced JSON Fields
    conditions: Optional[str] = SQLField(default=None, sa_column=Column(JSON))
    features: Optional[str] = SQLField(default=None, sa_column=Column(JSON))
    spells_known: Optional[str] = SQLField(default=None, sa_column=Column(JSON))

    # Currency (using individual fields)
    copper_pieces: int = SQLField(default=0, ge=0)
    silver_pieces: int = SQLField(default=0, ge=0)
    electrum_pieces: int = SQLField(default=0, ge=0)
    gold_pieces: int = SQLField(default=0, ge=0)
    platinum_pieces: int = SQLField(default=0, ge=0)

    # Computed total wealth in copper (for easy comparison)
    total_wealth_cp: int = SQLField(
        sa_column=Column(
            "total_wealth_cp",
            Integer,
            Computed(
                '''
                copper_pieces +
                (silver_pieces * 10) +
                (electrum_pieces * 50) +
                (gold_pieces * 100) +
                (platinum_pieces * 1000)
            '''
            ),
        )
    )

    # Encumbrance tracking
    carrying_capacity: int = SQLField(
        sa_column=Column(
            "carrying_capacity",
            Integer,
            Computed("strength * 15"),  # D&D rule: STR * 15 lbs
        )
    )

    # Status tracking
    in_game: bool = SQLField(default=False)
    current_location: Optional[str] = SQLField(default=None)
    last_action_time: Optional[datetime] = SQLField(default=None)
    is_hostile: bool = SQLField(default=False)

    player: Mapped[Optional["Player"]] = Relationship(
        back_populates="characters", sa_relationship_kwargs={"lazy": "selectin"}
    )

    campaign: Mapped[Optional["Campaign"]] = Relationship(
        back_populates="characters", sa_relationship_kwargs={"lazy": "selectin"}
    )

    attacks: Mapped[List["Attack"]] = Relationship(back_populates="character")
    inventory: Mapped[List["CharacterEquipment"]] = Relationship(back_populates="character")
    action_history: Mapped[List["ActionHistory"]] = Relationship(
        back_populates="character"
    )

    # TODO: Fix total_carried_weight to work with CharacterEquipment and Equipment join.
    # # Computed properties for encumbrance
    # @hybrid_property
    # def total_carried_weight(self) -> float:
    #     """Calculates the total weight of all items in inventory."""
    #     # This needs a session to join Equipment and get the weight.
    #     # A simple sum like this won't work with the new structure.
    #     return 0.0
    #     # return sum(item.quantity * item.equipment.weight for item in self.inventory)

    @hybrid_property
    def is_encumbered(self) -> bool:
        """Checks if the character is encumbered (carrying capacity to 5x strength)."""
        # TODO: This is disabled until total_carried_weight is fixed.
        return False
        # return self.total_carried_weight > self.strength * 5

    @hybrid_property
    def is_heavily_encumbered(self) -> bool:
        """Checks if the character is heavily encumbered (carrying capacity to 10x strength)."""
        # TODO: This is disabled until total_carried_weight is fixed.
        return False
        # return self.total_carried_weight > self.strength * 10

    # Validation methods
    @validates("hp")
    def validate_hp(self, key, hp):
        """Ensure HP never exceeds max_hp"""
        max_hp_value = getattr(self, "max_hp", None)
        if max_hp_value is not None and hp > max_hp_value:
            return max_hp_value
        return max(0, hp)

    # Hybrid properties (work in both Python and SQL queries)
    @hybrid_property
    def is_alive(self) -> bool:
        return self.hp > 0

    @hybrid_property
    def hp_percentage(self) -> float:
        if self.max_hp == 0:
            return 0.0
        return (self.hp / self.max_hp) * 100

    # JSON field helper methods
    def get_conditions(self) -> List[str]:
        """Get conditions as Python list"""
        if not self.conditions:
            return []
        return (
            json.loads(self.conditions)
            if isinstance(self.conditions, str)
            else self.conditions
        )

    def add_condition(self, condition: str):
        """Add a condition"""
        conditions = self.get_conditions()
        if condition not in conditions:
            conditions.append(condition)
            self.conditions = json.dumps(conditions)

    def remove_condition(self, condition: str):
        """Remove a condition"""
        conditions = self.get_conditions()
        if condition in conditions:
            conditions.remove(condition)
            self.conditions = json.dumps(conditions)

    def get_total_wealth_gp(self) -> float:
        """Get total wealth in gold pieces"""
        return self.total_wealth_cp / 100.0

    # Proficiency methods
    def get_proficiency_level(self, proficiency_index: str) -> "ProficiencyLevel":
        """Gets the proficiency level for a given skill, save, or tool."""
        for prof in self.proficiencies:
            if prof.proficiency_index == proficiency_index:
                return prof.level
        return ProficiencyLevel.NONE

    def get_modifier_for_check(
        self, ability_name: str, proficiency_index: str
    ) -> int:
        """Calculates a modifier for any ability check, including proficiency."""
        ability_modifier = getattr(self, f"{ability_name[:3].lower()}_modifier")

        prof_level = self.get_proficiency_level(proficiency_index)
        prof_bonus = 0
        if prof_level == ProficiencyLevel.PROFICIENT:
            prof_bonus = self.proficiency_bonus
        elif prof_level == ProficiencyLevel.EXPERTISE:
            prof_bonus = self.proficiency_bonus * 2
        elif prof_level == ProficiencyLevel.HALF:
            prof_bonus = self.proficiency_bonus // 2

        return ability_modifier + prof_bonus


# Campaign Model
class Campaign(SQLModel, table=True):
    model_config = ConfigDict(
        ignored_types=(hybrid_property,)
    )  # Ignore hybrid properties as fields

    __tablename__ = "campaigns"
    campaign_id: Optional[int] = SQLField(default=None, primary_key=True)
    campaign_name: str = SQLField(..., min_length=1, max_length=100)
    owner_id: str = SQLField(..., foreign_key="players.player_id")
    state: Optional[str] = SQLField(
        default=None, sa_column=Column(JSON)
    )  # JSON serialized game state
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
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
    action_history: Mapped[List["ActionHistory"]] = Relationship(
        back_populates="campaign"
    )

    @hybrid_property
    def is_active(self) -> bool:
        # Example: Consider a campaign active if last_save was within the last 7 days
        return (datetime.utcnow() - self.last_save).days < 7

    def get_state(self) -> Dict[str, Any]:
        if not self.state:
            return {}
        return json.loads(self.state) if isinstance(self.state, str) else self.state

    def update_state(self, new_state: Dict[str, Any]):
        current_state = self.get_state()
        current_state.update(new_state)
        self.state = json.dumps(current_state)
        self.last_save = datetime.utcnow()


# Memory State Model for Database Persistence
class MemoryStateModel(SQLModel, table=True):
    model_config = ConfigDict(
        ignored_types=(hybrid_property,)
    )  # Ignore hybrid properties as fields

    __tablename__ = "memory_states"
    memory_id: Optional[int] = SQLField(default=None, primary_key=True)
    session_id: str = SQLField(..., index=True, unique=True, max_length=255)
    user_id: Optional[str] = SQLField(default=None, index=True, max_length=255)
    campaign_id: Optional[int] = SQLField(
        default=None, foreign_key="campaigns.campaign_id", index=True
    )

    # JSON serialized memory data
    messages: Optional[str] = SQLField(default=None, sa_column=Column(JSON))
    context: Optional[str] = SQLField(default=None, sa_column=Column(JSON))
    scratchpad: Optional[str] = SQLField(default=None, sa_column=Column(JSON))

    # Metadata
    turn_count: int = SQLField(default=0, ge=0)
    total_messages: int = SQLField(default=0, ge=0)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    last_activity: datetime = SQLField(default_factory=datetime.utcnow)
    last_save: datetime = SQLField(default_factory=datetime.utcnow)

    # Relationships
    campaign: Mapped[Optional["Campaign"]] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    # Indexes for performance
    __table_args__ = ({"sqlite_autoincrement": True},)

    def get_messages(self) -> List[Dict[str, Any]]:
        if not self.messages:
            return []
        return (
            json.loads(self.messages)
            if isinstance(self.messages, str)
            else self.messages
        )

    def get_context(self) -> Dict[str, Any]:
        if not self.context:
            return {}
        return (
            json.loads(self.context) if isinstance(self.context, str) else self.context
        )

    def get_scratchpad(self) -> Dict[str, Any]:
        if not self.scratchpad:
            return {}
        return (
            json.loads(self.scratchpad)
            if isinstance(self.scratchpad, str)
            else self.scratchpad
        )


# Action History Model
class ActionHistory(SQLModel, table=True):
    __tablename__ = "action_history"
    id: Optional[int] = SQLField(default=None, primary_key=True)
    campaign_id: int = SQLField(foreign_key="campaigns.campaign_id")
    character_id: Optional[int] = SQLField(
        default=None, foreign_key="characters.character_id"
    )

    # Context
    discord_user_id: str = SQLField(max_length=255)
    discord_channel_id: str = SQLField(max_length=255)
    timestamp: datetime = SQLField(default_factory=datetime.utcnow)

    # Action Details
    action_text: str = SQLField(sa_column=Column(String(1000)))
    parsed_intent: Optional[str] = SQLField(default=None, sa_column=Column(JSON))
    result: str = SQLField(sa_column=Column(String(1000)))
    dice_rolls: Optional[str] = SQLField(default=None, sa_column=Column(JSON))

    # Relationships
    campaign: Mapped["Campaign"] = Relationship(back_populates="action_history")
    character: Mapped[Optional["Character"]] = Relationship(
        back_populates="action_history"
    )