"""
Combat State Definitions

This module contains all state definitions and data structures specifically
for combat mechanics and battle orchestration.
"""

from typing import Any, Dict, List, Set, TypedDict


class CombatParticipant(TypedDict):
    """Represents a single participant in a combat scenario."""
    id: str
    type: str  # 'player', 'enemy', 'npc'
    current_health: int
    max_health: int
    percent_of_damage_taken_this_round: float
    status_conditions: Set[str]  # e.g., 'healthy', 'wounded', 'dead', 'unconscious'
    active_effects: List[Dict[str, Any]]  # Buffs/debuffs
    initiative_score: int
    cover_status: str  # e.g., 'none', 'half', 'three-quarters', 'full'
    advantage_conditions: Set[str]  # e.g., 'advantage', 'disadvantage', 'normal'
    is_surprised: bool
    death_save_successes: int
    death_save_failures: int


class Effect(TypedDict):
    """Represents a temporary status effect or modifier."""
    effect_id: str
    type: str  # e.g., 'poison', 'haste'
    duration: int  # in rounds
    source_id: str
    target_id: str
    effect_parameters: Dict[str, Any]


class CombatState(TypedDict):
    """Encapsulates all combat-specific information."""
    participants: Dict[str, CombatParticipant]
    current_round: int
    active_turn_participant_id: str
    combat_phase: str  # e.g., 'initiative', 'action', 'end_of_round'
    initiative_queue: List[str]
    damage_queue: List[Dict[str, Any]]
    pending_effects: List[Effect]
    environmental_effects: List[Dict[str, Any]]