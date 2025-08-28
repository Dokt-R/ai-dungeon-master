"""
Exploration Resolution Node for Action Resolution

This module handles exploration-specific action resolution including
investigation, searching, and world navigation mechanics.
"""

from typing import Any, Dict

from packages.backend.ai.state.action_resolution_state import ActionResolutionState
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


async def exploration_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Handle exploration actions (not implemented yet)."""
    return {"action_result": {"type": "exploration", "description": "Exploration not implemented"}}