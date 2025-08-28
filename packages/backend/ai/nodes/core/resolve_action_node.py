"""
Resolve Action Node for Action Resolution

This module provides action routing functionality to determine which
specific action handler (combat, exploration, social) should process
the parsed player intent.
"""

import time
from typing import Any, Dict

from packages.backend.ai.state.action_resolution_state import ActionResolutionState
from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


def _display_action(message: str) -> None:
    """Display action message to screen."""
    print(message)


async def resolve_action_node(state: ActionResolutionState) -> Dict[str, Any]:
    """Route to the appropriate action handler."""
    start_time = time.time()

    with observability_service.trace_operation(
        operation_name="resolve_action_node_execution",
        action_routing=True,
        correlation_id=state["correlation_id"]
    ) as node_trace_id:
        try:
            parsed_intent = state.get("parsed_intent", {})
            action_type = parsed_intent.get("action_type", "unknown")

            _display_action(f"🎮 Routing to: {action_type}_node")

            # For now, all actions route to combat (simplified flow)
            # In a full implementation, this would have conditional routing

            execution_time = time.time() - start_time
            logger.debug("resolve_action_node_completed",
                        trace_id=node_trace_id,
                        execution_time=f"{execution_time:.4f}s",
                        routing_target=f"{action_type}_node")

            return {}

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Action routing failed: {str(e)}"
            logger.error("action_routing_failed",
                        error=str(e),
                        execution_time=f"{execution_time:.4f}s",
                        trace_id=node_trace_id)
            return {"error": error_msg}