"""
Action Resolution State Definitions

This module contains all state definitions and data structures specifically
for the action resolution graph and related functionality.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, TypedDict


class ActionResolutionState(TypedDict):
    """State for the action resolution graph."""
    player_action: str
    game_state: Dict[str, Any]
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
    action_type: str  # "attack", "investigate", "use_item", "move", etc.
    target: Optional[str]  # What the action targets
    modifier: Optional[str]  # additional context
    confidence: float  # How confident we are in this interpretation