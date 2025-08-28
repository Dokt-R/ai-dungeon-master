"""
Combat State Definitions

This module contains all state definitions and data structures specifically
for combat mechanics and battle orchestration.
"""

from typing import Any, Dict, List, Optional, TypedDict


# Future combat state definitions will go here
# class CombatState(TypedDict):
#     """State for combat resolution."""
#     participants: List[Dict[str, Any]]
#     initiative_order: List[Dict[str, Any]]
#     current_turn: int
#     round_number: int
#     combat_active: bool
#     current_participant: Optional[Dict[str, Any]]
#     needs_dm_input: Optional[str]

# Placeholder for future development
class CombatPhase:
    """Enumeration of combat phases."""
    SETUP = "setup"
    INITIATIVE = "initiative"
    COMBAT = "combat"
    END = "end"