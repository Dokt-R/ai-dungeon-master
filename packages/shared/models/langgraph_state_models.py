"""
LangGraph State Models
Models for conversational AI interactions in LangGraph.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict

from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Column, Field as SQLField, Index, SQLModel


class MinimalGameState(TypedDict, total=False):
    """Ultra-lightweight state for LangGraph"""
    # Context IDs only
    campaign_id: int
    state_players: List[str]
    state_npcs: List[str]
    state_enemies: List[str]
    character_id: int
    discord_user_id: str
    discord_channel_id: str
    correlation_id: str

    # Current action
    player_action: str
    parsed_intent: Dict[str, Any]

    # Computed results (not persisted)
    action_result: str
    dice_results: Dict[str, Any]

    # Combat context (loaded when needed)
    combat_state: 'CombatState'

    # Control flow flags
    exit_early: bool
    error: Dict[str, Any]

"""
Combat State Definitions

This module contains all state definitions and data structures specifically
for combat mechanics and battle orchestration.
"""


class CombatParticipant(SQLModel, table=True):
    """Represents a single participant in a combat scenario."""
    __tablename__ = "combat_participants"
    participant_id: Optional[int] = SQLField(default=None, primary_key=True)
    campaign_id: int = SQLField(foreign_key="campaigns.campaign_id")

    creature_type: str = SQLField(default=None) # 'player', 'enemy', 'npc'
    creature_id: int = SQLField(default=None)  # character_id or npc_id
    creature_name: str = SQLField(default=None)

    initiative_roll: Optional[int] = SQLField(default=None)
    initiative_modifier: Optional[int] = SQLField(default=None) # Could be deprecated with Character DEX Modifier

    # HP
    current_health: int = SQLField(default=None)
    max_health: int = SQLField(default=None)
    temp_hp: int = SQLField(default=None)
    percent_of_damage_taken_this_round: Optional[float] = SQLField(default=None)

    # Turn management
    is_active: bool = SQLField(default=True)
    has_acted_this_turn: bool = SQLField(default=False)
    has_moved_this_turn: bool = SQLField(default=False)
    has_bonus_action: bool = SQLField(default=True)
    has_reaction: bool = SQLField(default=True)

    # Combat-specific conditions (separate from creature's permanent conditions)
    active_conditions: Optional[str] = SQLField(default=None, sa_column=Column(JSON))
    temporary_effects: Optional[str] = SQLField(default=None, sa_column=Column(JSON))
    
    # Tactical state
    position_x: Optional[float] = SQLField(default=None)  # Battle map coordinates
    position_y: Optional[float] = SQLField(default=None)
    cover_status: Optional[str] = SQLField(default=None)  # e.g., 'none', 'half', 'three-quarters', 'full'
    is_surprised: bool = SQLField(default=False)
    advantage_conditions: Optional[str] = SQLField(default=None)  # e.g., 'advantage', 'disadvantage'

    death_save_successes: Optional[int] = SQLField(default=0, ge=0, le=3)
    death_save_failures: Optional[int] = SQLField(default=0, ge=0, le=3)
    is_stable: bool = SQLField(default=False)

    # Performance indexes
    __table_args__ = (
        Index('idx_combat_participant_creature', 'creature_type', 'creature_id'),
    )

    @property
    def participant_key(self) -> str:
        """Generate unique key for this participant"""
        return f"{self.creature_type}_{self.creature_id}"
    
    @property
    def effective_hp(self) -> int:
        """Current HP + temporary HP"""
        return self.current_hp + self.temp_hp
    
    @property
    def is_unconscious(self) -> bool:
        """Is participant at 0 HP"""
        return self.current_hp <= 0 and self.current_hp > -self.max_hp
    
    @property
    def is_dead(self) -> bool:
        """Is participant dead (failed death saves or massive damage)"""
        return (self.death_save_failures >= 3 or 
                self.current_hp <= -self.max_hp)
    
    def reset_turn_actions(self):
        """Reset action economy for new turn"""
        self.has_acted_this_turn = False
        self.has_moved_this_turn = False
        self.has_bonus_action = True
        self.has_reaction = True


class Effect(TypedDict):
    """Represents a temporary status effect or modifier."""
    effect_id: str
    type: str  # e.g., 'poison', 'haste'
    duration: int  # in rounds
    source_id: str
    target_id: str
    effect_parameters: Dict[str, Any]


@dataclass
class CombatState:
    """Encapsulates all combat-specific information."""
    campaign_id: int
    participants: Dict[str, str] = field(default_factory=dict)  # participant_id -> creature_key
    active_participants: List[str] = field(default_factory=list)

    # Turn management
    current_round: int = 1
    active_participant_id: Optional[str] = None
    combat_phase: str = "initialize"  # 'initiative', 'action', 'movement', 'end_turn', 'end_combat'

    # Initiative system
    initiative_order: List[Dict[str, int]] = field(default_factory=list)
    initiative_complete: bool = False
    needs_initiative_reroll: bool = False

    # Action queues
    pending_damage: List[Dict[str, Any]] = field(default_factory=list)
    pending_effects: List[Dict[str, Any]] = field(default_factory=list)
    pending_saves: List[Dict[str, Any]] = field(default_factory=list)

    # Environmental
    battlefield_effects: List[Dict[str, Any]] = field(default_factory=list)
    round_timer: Optional[int] = None

    # State flags
    is_surprised_round: bool = False
    combat_started: bool = True
    combat_ended: bool = False
    victory_condition: Optional[str] = None