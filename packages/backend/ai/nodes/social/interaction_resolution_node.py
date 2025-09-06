"""
Interaction Resolution Node for non-combat actions
"""

from typing import Any, Dict

from packages.backend.ai.state.action_resolution_state import ActionResolutionState
from packages.backend.ai.state.base_state import ActionResult
from packages.backend.ai.state.game_state import GameState
from packages.backend.ai.tools import DiceRoller
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)
dice_roller = DiceRoller()


async def interaction_node(state: ActionResolutionState) -> Dict[str, Any]:
    """
    Handle non-combat interactions like talking, using items, picking up objects.
    Now fully integrated with standardized GameState schema.
    """
    try:
        intent = state.get("parsed_intent", {})
        action_type = intent.get("action_type", "").lower()
        target = intent.get("target")
        game_state: GameState = state.get("game_state", {})

        # Ensure we have a valid game state
        if not game_state or not isinstance(game_state, dict):
            return {
                "error": "Invalid game state provided",
                "action_result": {
                    "success": False,
                    "description": "Cannot process interaction: invalid game state",
                },
            }

        logger.debug(
            "interaction_node_processing",
            action_type=action_type,
            target=target,
            correlation_id=state["correlation_id"],
        )

        result = ActionResult(success=False, description="", state_changes={})

        # Handle different interaction types with standardized game state
        if action_type in ["take", "pick", "grab"]:
            result = await handle_item_pickup(target, game_state)

        elif action_type in ["use", "activate"]:
            result = await handle_item_use(target, game_state)

        elif action_type in ["talk", "speak", "say"]:
            # Use dialogue stored in intent.modifier if available
            dialogue = intent.get("modifier") or intent.get("dialogue", "")
            result = await handle_dialogue(target, dialogue, game_state)

        elif action_type in ["persuade", "intimidate", "deceive"]:
            result = await handle_social_check(action_type, target, game_state)

        elif action_type in ["unlock", "pick"]:
            result = await handle_lockpicking(target, game_state)

        # Apply state changes using standardized game state structure
        if result.state_changes:
            game_state = apply_state_changes(game_state, result.state_changes)

        action_result_dict = {
            "success": result.success,
            "description": result.description,
            "state_changes": result.state_changes.__dict__
            if hasattr(result.state_changes, "__dict__")
            else result.state_changes,
        }

        logger.debug(
            "interaction_node_completed",
            success=result.success,
            correlation_id=state["correlation_id"],
        )

        # Return updated state with results
        updated_state = state.copy()
        updated_state["action_result"] = action_result_dict
        updated_state["game_state"] = game_state

        return updated_state

    except Exception as e:
        logger.error(
            "interaction_node_failed",
            error=str(e),
            correlation_id=state["correlation_id"],
        )
        updated_state = state.copy()
        updated_state["error"] = f"Failed to process interaction: {str(e)}"
        return updated_state


async def handle_item_pickup(item_name: str, game_state: GameState) -> ActionResult:
    """Handle picking up an item using standardized schemas."""

    if not item_name:
        return ActionResult(
            success=False,
            description="You need to specify what to pick up.",
            state_changes={},
        )

    # Get current room
    current_room_id = game_state["current_room_id"]
    current_room = game_state["rooms"][current_room_id]

    # Check if item exists in room
    item_found = None
    item_details = None

    # Check both room items (strings) and object containers
    for room_item in current_room["items"]:
        if isinstance(room_item, str) and item_name.lower() in room_item.lower():
            item_found = room_item
            break
        elif (
            isinstance(room_item, dict)
            and item_name.lower() in room_item.get("name", "").lower()
        ):
            item_details = room_item
            item_found = room_item["name"]
            break

    # Check object containers for items
    if not item_found:
        for game_obj in current_room["objects"]:
            if game_obj.get("contains"):
                for contained_item in game_obj["contains"]:
                    if (
                        isinstance(contained_item, dict)
                        and item_name.lower() in contained_item.get("name", "").lower()
                    ):
                        if not game_obj.get("state", {}).get("locked", False):
                            item_details = contained_item
                            item_found = contained_item["name"]
                            break
                if item_found:
                    break

    if not item_found:
        return ActionResult(
            success=False,
            description=f"There is no {item_name} here to pick up.",
            state_changes={},
        )

    return ActionResult(
        success=True,
        description=f"You pick up the {item_found}.",
        state_changes={
            "inventory_add": item_found if item_details is None else item_details,
            "room_item_remove": item_found if item_details is None else item_details,
        },
    )


async def handle_item_use(item_name: str, game_state: GameState) -> ActionResult:
    """Handle using an item with standardized schemas."""

    player_inventory = game_state["player"].get("inventory", [])
    if not player_inventory:
        return ActionResult(
            success=False,
            description="You don't have any items to use.",
            state_changes={},
        )

    # Find the item in inventory
    item_to_use = None
    for item in player_inventory:
        if isinstance(item, str):
            # Legacy string format
            if item_name.lower() in item.lower():
                item_to_use = item
                break
        elif isinstance(item, dict):
            # Standardized Item format
            if item_name.lower() in item.get("name", "").lower():
                item_to_use = item
                break

    if not item_to_use:
        return ActionResult(
            success=False,
            description=f"You don't have a {item_name} to use.",
            state_changes={},
        )

    # Special case: using key on chest
    if "key" in item_name.lower():
        # Check if there's a locked chest in the current room
        current_room_id = game_state["current_room_id"]
        current_room = game_state["rooms"][current_room_id]

        chest_locked = False
        for game_obj in current_room["objects"]:
            if "chest" in game_obj["name"].lower():
                chest_locked = game_obj.get("state", {}).get("locked", False)
                break

        if chest_locked:
            return ActionResult(
                success=True,
                description="You unlock the chest with the key. It creaks open, revealing its contents!",
                state_changes={
                    "inventory_remove": item_to_use,
                    "object_state": {"chest": {"locked": False, "open": True}},
                },
            )

    # Health potion
    if "potion" in item_name.lower():
        # Get item properties for healing effect
        healing_formula = "2d4+2"  # Default
        item_name_for_removal = item_to_use

        if isinstance(item_to_use, dict) and "properties" in item_to_use:
            healing_formula = item_to_use["properties"].get("healing", "2d4+2")

        healing = dice_roller.roll_dice_notation(healing_formula)
        current_hp = game_state["player"]["hp"]
        max_hp = game_state["player"]["max_hp"]
        new_hp = min(current_hp + healing.total, max_hp)

        return ActionResult(
            success=True,
            description=f"You drink the {item_name} and recover {healing.total} hit points!",
            state_changes={
                "inventory_remove": item_name_for_removal,
                "player_hp": new_hp,
            },
        )

    # Generic item use
    return ActionResult(
        success=True,
        description=f"You use the {item_name}.",
        state_changes={"inventory_remove": item_to_use},
    )


async def handle_social_check(
    check_type: str, target: str, game_state: GameState
) -> ActionResult:
    """Handle social skill checks with standardized D&D mechanics."""
    # Determine the appropriate ability based on social skill
    ability_mod = 0
    ability_name = ""

    if check_type == "persuasion":
        ability_mod = game_state["player"]["charisma_mod"]
        ability_name = "Charisma"
    elif check_type == "intimidation":
        # Intimidation uses Strength or Charisma (whichever is higher)
        ability_mod = max(
            game_state["player"]["strength_mod"], game_state["player"]["charisma_mod"]
        )
        ability_name = "Charisma/Strength"
    elif check_type == "deception":
        ability_mod = game_state["player"]["charisma_mod"]
        ability_name = "Charisma"
    else:
        ability_mod = game_state["player"]["charisma_mod"]
        ability_name = "Charisma"

    # Roll a d20 for the check
    roll = dice_roller.roll_dice_notation("1d20")
    total = roll.total + ability_mod

    # Determine DC based on situation and NPC relationship
    # This could be improved with more sophisticated NPC personality systems
    dc = 13  # Slightly harder than medium difficulty

    if total >= dc:
        return ActionResult(
            success=True,
            description=f"[{check_type.capitalize()}] You rolled {roll.total}+{ability_mod}={total} vs DC {dc}. Success! ({ability_name})",
            state_changes={},
        )
    else:
        return ActionResult(
            success=False,
            description=f"[{check_type.capitalize()}] You rolled {roll.total}+{ability_mod}={total} vs DC {dc}. Failed. ({ability_name})",
            state_changes={},
        )


async def handle_lockpicking(target: str, game_state: GameState) -> ActionResult:
    """Handle lockpicking attempts with standardized D&D mechanics."""
    if "chest" in target.lower():
        # Find chest in current room
        current_room_id = game_state["current_room_id"]
        current_room = game_state["rooms"][current_room_id]
        chest_locked = None

        for game_obj in current_room["objects"]:
            if "chest" in game_obj["name"].lower():
                chest_locked = game_obj.get("state", {}).get("locked", True)
                break

        if chest_locked is None:
            return ActionResult(
                success=False,
                description="There is no chest here to unlock.",
                state_changes={},
            )

        if not chest_locked:
            return ActionResult(
                success=False,
                description="The chest is already unlocked.",
                state_changes={},
            )

        # Thieves' tools proficiency check (using D&D expertise)
        has_thieves_tools = any(
            (isinstance(item, str) and "thieves" in item.lower())
            or (isinstance(item, dict) and "thieves" in item.get("name", "").lower())
            for item in game_state["player"].get("inventory", [])
        )

        # Dexterity check with proficiency bonus
        roll = dice_roller.roll_dice_notation("1d20")
        dex_mod = game_state["player"]["dexterity_mod"]
        proficiency = 2 if has_thieves_tools else 0  # D&D proficiency bonus
        total = roll.total + dex_mod + proficiency
        dc = 15  # Moderate lock difficulty

        if total >= dc:
            return ActionResult(
                success=True,
                description=f"You successfully pick the lock! (Rolled {roll.total}+{dex_mod}{f'+{proficiency}' if proficiency else ''}={total} vs DC {dc})",
                state_changes={
                    "object_state": {"chest": {"locked": False, "open": True}}
                },
            )
        else:
            return ActionResult(
                success=False,
                description=f"You fail to pick the lock. (Rolled {roll.total}+{dex_mod}{f'+{proficiency}' if proficiency else ''}={total} vs DC {dc})",
                state_changes={},
            )

    return ActionResult(
        success=False,
        description=f"There's no {target} to unlock here.",
        state_changes={},
    )


async def handle_dialogue(
    target: str, dialogue: str, game_state: GameState
) -> ActionResult:
    """Handle speaking/dialogue actions with standardized response structure."""
    # For now, just acknowledge the dialogue
    # In future, this could trigger NPC responses based on personality, history, etc.
    return ActionResult(
        success=True,
        description=f'You say "{dialogue}" to {target if target else "no one in particular"}.',
        state_changes={},
    )


def apply_state_changes(
    game_state: GameState, state_changes: Dict[str, Any]
) -> GameState:
    """
    Apply state changes to the standardized GameState structure.
    Returns a new GameState with changes applied (immutable updates).
    """
    # Create a deep copy of the game state
    new_game_state = game_state.copy()

    for key, value in state_changes.items():
        if key == "inventory_add" and isinstance(value, str):
            # Add item to player inventory
            if "inventory" not in new_game_state["player"]:
                new_game_state["player"]["inventory"] = []
            new_game_state["player"]["inventory"].append(value)

        elif key == "inventory_remove" and isinstance(value, str):
            # Remove item from player inventory
            if "inventory" in new_game_state["player"]:
                inventory = new_game_state["player"]["inventory"]
                if value in inventory:
                    inventory.remove(value)

        elif key == "object_state" and isinstance(value, dict):
            # Update object states (e.g., chest is now open)
            current_room_id = new_game_state["current_room_id"]
            if current_room_id in new_game_state["rooms"]:
                room = new_game_state["rooms"][current_room_id]
                for obj_name, obj_state in value.items():
                    for i, obj in enumerate(room["objects"]):
                        if (
                            obj["name"].lower().replace(" ", "_") == obj_name.lower()
                            or obj["name"].lower() == obj_name.lower()
                        ):
                            room["objects"][i]["state"].update(obj_state)
                            break

        elif key == "player_hp" and isinstance(value, int):
            # Update player HP
            new_game_state["player"]["hp"] = max(
                0, min(value, new_game_state["player"]["max_hp"])
            )

        elif key == "room_item_add" and isinstance(value, str):
            # Add item to room
            current_room_id = new_game_state["current_room_id"]
            if current_room_id in new_game_state["rooms"]:
                room = new_game_state["rooms"][current_room_id]
                room["items"].append(value)

        elif key == "room_item_remove" and isinstance(value, str):
            # Remove item from room
            current_room_id = new_game_state["current_room_id"]
            if current_room_id in new_game_state["rooms"]:
                room = new_game_state["rooms"][current_room_id]
                if value in room["items"]:
                    room["items"].remove(value)

    return new_game_state
