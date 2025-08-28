"""
Social Interaction State Definitions

This module contains all state definitions and data structures specifically
for social interactions, NPC relationships, and conversation management.
"""

from typing import Any, Dict, List, Optional, TypedDict


# Future social state definitions will go here
# class SocialState(TypedDict):
#     """State for social interactions."""
#     npc_relationships: Dict[str, int]
#     conversation_context: Optional[Dict[str, Any]]
#     current_dialogue: Optional[List[Dict[str, str]]]
#     reputation_scores: Dict[str, float]

# Placeholder for future development
class SocialPhase:
    """Enumeration of social interaction phases."""
    APPROACH = "approach"
    CONVERSATION = "conversation"
    NEGOTIATION = "negotiation"
    CONFLICT = "conflict"
    RESOLUTION = "resolution"