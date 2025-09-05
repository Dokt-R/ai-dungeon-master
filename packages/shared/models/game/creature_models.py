"""
Gameplay Database Models
SQLModel tables for the main entities in the system.
"""

import json
from typing import List, Optional

from pydantic import ConfigDict
from sqlalchemy import (  # Import Integer and DateTime
    Column,
    Computed,
    Integer,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    Mapped,
)
from sqlmodel import Field as SQLField, Relationship, SQLModel

from packages.shared.models.core_db_models import Campaign


class BaseCreature(SQLModel):
    """Base class for all D&D creatures with common stats"""
    model_config = ConfigDict(ignored_types=(hybrid_property,))
    
    # Basic identity
    name: str = SQLField(..., min_length=1, max_length=50)
    campaign_id: Optional[int] = SQLField(default=None, foreign_key="campaigns.campaign_id")
    
    # Core combat stats
    hp: int = SQLField(default=10, ge=0)
    max_hp: int = SQLField(default=10, ge=1)
    ac: int = SQLField(default=10, ge=1, le=30)
    
    # Core D&D ability scores
    strength: int = SQLField(default=10, ge=1, le=30)
    dexterity: int = SQLField(default=10, ge=1, le=30)
    constitution: int = SQLField(default=10, ge=1, le=30)
    intelligence: int = SQLField(default=10, ge=1, le=30)
    wisdom: int = SQLField(default=10, ge=1, le=30)
    charisma: int = SQLField(default=10, ge=1, le=30)
    
    # Common computed modifiers
    str_modifier: int = SQLField(
        sa_column=Column("str_modifier", Integer, Computed("((strength - 10) / 2)"))
    )
    dex_modifier: int = SQLField(
        sa_column=Column("dex_modifier", Integer, Computed("((dexterity - 10) / 2)"))
    )
    con_modifier: int = SQLField(
        sa_column=Column("con_modifier", Integer, Computed("((constitution - 10) / 2)"))
    )
    int_modifier: int = SQLField(
        sa_column=Column("int_modifier", Integer, Computed("((intelligence - 10) / 2)"))
    )
    wis_modifier: int = SQLField(
        sa_column=Column("wis_modifier", Integer, Computed("((wisdom - 10) / 2)"))
    )
    cha_modifier: int = SQLField(
        sa_column=Column("cha_modifier", Integer, Computed("((charisma - 10) / 2)"))
    )
    
    # Common JSON fields
    conditions: Optional[str] = SQLField(default=None, sa_column=Column(JSON))
    
    # Common status fields
    is_alive: bool = SQLField(default=True)
    is_hostile: bool = SQLField(default=False)
    in_combat: bool = SQLField(default=False)
    
    # Common hybrid properties
    @hybrid_property
    def hp_percentage(self) -> float:
        if self.max_hp == 0:
            return 0.0
        return (self.hp / self.max_hp) * 100
    
    @hybrid_property
    def is_conscious(self) -> bool:
        return self.hp > 0
    
    @hybrid_property  
    def initiative_modifier(self) -> int:
        """Initiative is always DEX modifier in D&D"""
        return self.dex_modifier

    @hybrid_property
    def is_unconscious(self) -> bool:
        return self.hp <= 0 and self.hp > -self.max_hp

    @hybrid_property  
    def is_dead(self) -> bool:
        return self.hp <= -self.max_hp

    @hybrid_property
    def death_threshold(self) -> int:
        """HP threshold for instant death"""
        return -self.max_hp
    
    @hybrid_property
    def participant_key(self) -> str:
        """Return a unique key for combat participant lookup"""
        return f"{self.__class__.__name__.lower()}_{self.id}"


    def get_ability_modifier(self, ability: str) -> int:
        """Get modifier for any ability score"""
        ability_map = {
            'str': self.str_modifier, 'dex': self.dex_modifier, 
            'con': self.con_modifier, 'int': self.int_modifier,
            'wis': self.wis_modifier, 'cha': self.cha_modifier
        }
        return ability_map.get(ability.lower(), 0)

    def make_saving_throw(self, ability: str, proficient: bool = False) -> int:
        """Calculate saving throw bonus"""
        modifier = self.get_ability_modifier(ability)
        bonus = self.proficiency_bonus if proficient else 0
        return modifier + bonus
    
    # Common helper methods
    def get_conditions(self) -> List[str]:
        """Get conditions as Python list"""
        if not self.conditions:
            return []
        return json.loads(self.conditions) if isinstance(self.conditions, str) else self.conditions
    
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

class NPC(BaseCreature, table=True):
    """Minimal NPC model for D&D gameplay"""

    model_config = ConfigDict(ignored_types=(hybrid_property,))

    __tablename__ = "npcs"

    # Identity
    npc_id: Optional[int] = SQLField(default=None, primary_key=True)

    # Basic stats for combat/interaction
    level: int = SQLField(default=1, ge=1, le=20)

    proficiency_bonus: int = SQLField(
        sa_column=Column(
            "proficiency_bonus",
            Integer,
            Computed("((level - 1) / 4 + 2)")
        )
    )

    # NPC-specific fields
    npc_type: str = SQLField(default="humanoid")  # creature type
    disposition: str = SQLField(default="neutral")  # friendly, neutral, hostile
    role: Optional[str] = SQLField(default=None)  # merchant, guard, noble, etc.
    location: Optional[str] = SQLField(default=None)

    # JSON fields for flexibility
    traits: Optional[str] = SQLField(default=None, sa_column=Column(JSON))
    conditions: Optional[str] = SQLField(default=None, sa_column=Column(JSON))

    # Relationships
    # campaign: Mapped[Optional["Campaign"]] = Relationship(
    #     back_populates="npcs", sa_relationship_kwargs={"lazy": "selectin"}
    # )


class Monster(SQLModel, table=True):
    """Minimal Monster model for D&D combat"""

    model_config = ConfigDict(ignored_types=(hybrid_property,))

    __tablename__ = "monsters"

    # Identity
    monster_id: Optional[int] = SQLField(default=None, primary_key=True)

    # Challenge Rating instead of level for monsters
    challenge_rating: float = SQLField(default=0.125, ge=0, le=30)  # CR 1/8 to 30

    # Proficiency bonus based on CR
    proficiency_bonus: int = SQLField(
        sa_column=Column(
            "proficiency_bonus",
            Integer,
            # CR 0-4: +2, CR 5-8: +3, CR 9-12: +4, CR 13-16: +5, CR 17-20: +6, CR 21+: +7
            Computed("""
                CASE 
                    WHEN challenge_rating <= 4 THEN 2
                    WHEN challenge_rating <= 8 THEN 3
                    WHEN challenge_rating <= 12 THEN 4
                    WHEN challenge_rating <= 16 THEN 5
                    WHEN challenge_rating <= 20 THEN 6
                    ELSE 7
                END
            """),
        )
    )

    # Monster-specific fields
    monster_type: str = SQLField(default="beast")  # beast, humanoid, undead, etc.
    size: str = SQLField(
        default="medium"
    )  # tiny, small, medium, large, huge, gargantuan
    alignment: str = SQLField(default="neutral")

    # Movement and senses
    speed: int = SQLField(default=30)  # feet
    darkvision: int = SQLField(default=0)  # feet, 0 = no darkvision

    # Monster Specific Fields (JSON for flexibility)
    damage_resistances: Optional[str] = SQLField(default=None, sa_column=Column(JSON))
    damage_immunities: Optional[str] = SQLField(default=None, sa_column=Column(JSON))
    condition_immunities: Optional[str] = SQLField(default=None, sa_column=Column(JSON))
    special_abilities: Optional[str] = SQLField(default=None, sa_column=Column(JSON))
    legendary_actions: Optional[str] = SQLField(default=None, sa_column=Column(JSON))

    # Relationships
    # campaign: Mapped[Optional["Campaign"]] = Relationship(
    #     back_populates="monsters", sa_relationship_kwargs={"lazy": "selectin"}
    # )

    @hybrid_property
    def is_legendary(self) -> bool:
        """Check if monster has legendary actions"""
        if not self.legendary_actions:
            return False
        legendary = (
            json.loads(self.legendary_actions)
            if isinstance(self.legendary_actions, str)
            else self.legendary_actions
        )
        return len(legendary) > 0 if legendary else False


# Helper functions for JSON field management
def get_json_field(field_value) -> List[str]:
    """Helper to get JSON field as Python list"""
    if not field_value:
        return []
    return json.loads(field_value) if isinstance(field_value, str) else field_value


def set_json_field(field_list: List[str]) -> str:
    """Helper to set JSON field from Python list"""
    return json.dumps(field_list)
