"""
Action Resolution State Definitions

This module contains state definitions specifically for the action resolution graph workflow.
Other schema definitions have been moved to their appropriate architecture files.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, TypedDict

from .game_state import GameState


class ActionResolutionState(TypedDict):
    """State for the action resolution graph workflow with standardized schemas."""
    player_action: str
    game_state: GameState  # Must be standardized GameState schema
    parsed_intent: Optional[Dict[str, Any]]
    action_result: Optional[Dict[str, Any]]
    narrative_response: Optional[str]
    error: Optional[str]
    correlation_id: str
    trace_context: Optional[Dict[str, Any]]  # Extended trace context
    performance_metrics: Optional[Dict[str, Any]]  # Performance tracking


@dataclass
class ParsedIntent:
    """Result of parsing player action text."""
    intent: str # Intended node routing
    action_type: str  # "attack", "investigate", "use_item", "move", etc.
    target: Optional[str]  # What the action targets
    modifier: Optional[str]  # Additional context (dialogue, modifiers)
    confidence: float  # How confident we are in this interpretation


# Action result structure for node communication
@dataclass
class ActionResult:
    """Standardized result structure for node operations"""
    success: bool
    description: str
    state_changes: Dict[str, Any]
    resolution_details: Optional[Dict[str, Any]] = None