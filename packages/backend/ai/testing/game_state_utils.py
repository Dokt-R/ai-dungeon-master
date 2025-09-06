"""
Game State Creation Utilities for Testing

This module contains utilities for creating test game states and sample data.
"""

import asyncio
import json

from packages.backend.ai.state.base_state import InteractionType
from packages.backend.ai.state.environment_state import (
    EnvironmentalEffect,
    InteractiveObject,
    TacticalRoom,
    TerrainType,
)
from packages.backend.ai.state.game_state import GameState as GraphGameState
from packages.shared.models.core_db_models import Attack, Character, DamageType, Item


def create_example_game_state() -> GraphGameState:
    """Create example game state for testing using enhanced D&D 5e schema."""

    # Create player character
    player_character = Character(
        character_id=1,  # Assign an ID for DB persistence
        name="Roric",
        hp=12,
        max_hp=12,
        ac=14,
        speed=30,
        strength=14,
        dexterity=13,
        constitution=14,
        intelligence=10,
        wisdom=12,
        charisma=8,
        level=1,
        copper_pieces=0,
        silver_pieces=0,
        electrum_pieces=0,
        gold_pieces=0,
        platinum_pieces=0,
        attacks=[
            Attack(
                name="Shortsword",
                bonus=4,  # +2 str mod, +2 proficiency
                damage="1d6+2",
                damage_type=DamageType.PIERCING,
                range=5,
            )
        ],
        # proficiency_bonus is computed
        conditions=json.dumps([]),  # Store as JSON string
        is_alive=True,
        is_hostile=False,
        # inventory will be handled by relationships
        # equipped_items will be handled by relationships
        # wallet is now individual currency fields
    )
    player_character.inventory.append(
        Item(
            name="Sword",
            type="weapon",
            weight=3.0,
            value=50,
            description="A simple iron shortsword.",
            source="SRD",
            quantity=1,
            is_stackable=False,
            rarity="common",
            requires_attunement=False,
            effects={},
            interactions={},
            properties={"weapon_type": "shortsword"},
            equipped=False,
        )
    )
    player_character.inventory.append(
        Item(
            name="Shield",
            type="armor",
            weight=6.0,
            value=30,
            description="A stout wooden shield.",
            source="SRD",
            quantity=1,
            is_stackable=False,
            rarity="common",
            requires_attunement=False,
            effects={},
            interactions={},
            properties={"armor": 2},
            equipped=False,
        )
    )
    player_character.inventory.append(
        Item(
            name="Healing Potion",
            type="consumable",
            weight=0.5,
            value=50,
            description="A red potion that restores health.",
            source="SRD",
            quantity=1,
            is_stackable=True,
            rarity="common",
            requires_attunement=False,
            effects={"on_use": {"heal": "2d4+2"}},
            interactions={InteractionType.USE.value: {"effect": "heal"}},
            properties={},
            equipped=False,
        )
    )
    player_character.inventory.append(
        Item(
            name="Key",
            type="key",
            weight=0.1,
            value=25,
            description="A simple iron key.",
            source="SRD",
            quantity=1,
            is_stackable=False,
            rarity="common",
            requires_attunement=False,
            effects={},
            interactions={InteractionType.USE.value: {"unlocks": "some_lock"}},
            properties={},
            equipped=False,
        )
    )

    # Create NPC (Goblin)
    goblin_character = Character(
        character_id=2,  # Assign an ID for DB persistence
        name="Goblin",
        hp=7,
        max_hp=7,
        ac=15,
        speed=30,
        strength=8,
        dexterity=14,
        constitution=10,
        intelligence=10,
        wisdom=8,
        charisma=8,
        level=1,
        copper_pieces=5,
        silver_pieces=0,
        electrum_pieces=0,
        gold_pieces=0,
        platinum_pieces=0,
        attacks=[
            Attack(
                name="Scimitar",
                bonus=4,
                damage="1d6+2",
                damage_type=DamageType.SLASHING,
                range=5,
            )
        ],
        # proficiency_bonus is computed
        conditions=json.dumps([]),  # Store as JSON string
        is_alive=True,
        is_hostile=True,
        # inventory will be handled by relationships
        # equipped_items will be handled by relationships
        # wallet is now individual currency fields
    )

    # Create interactive objects
    iron_chest = InteractiveObject(
        name="Iron Chest",
        description={
            "default": "a sturdy iron chest with an intricate lock",
            "unlocked": "an unlocked iron chest",
            "open": "an open chest containing treasures",
            "trapped": "a chest with a visible poison dart trap!",
        },
        current_state="default",
        interactions={
            InteractionType.EXAMINE: {
                "effects": [
                    {
                        "type": "skill_check",
                        "skill": "investigation",
                        "dc": 12,
                        "success": {
                            "reveal": "trap",
                            "message": "You spot a poison dart trap!",
                        },
                        "failure": {"message": "The chest looks valuable."},
                    }
                ]
            },
            InteractionType.USE: {
                "requires": {"item": "golden_key"},
                "next_state": "unlocked",
                "message": "The key turns with a satisfying click!",
            },
            InteractionType.OPEN: {
                "requires": {"state": "unlocked"},
                "next_state": "open",
                "message": "The chest creaks open, revealing its contents!",
            },
        },
        state_transitions={},
        properties={"locked": True, "trap_present": True},
    )

    # Create environmental effects
    goblin_reinforcements_effect = EnvironmentalEffect(
        name="Goblin Reinforcements",
        trigger_condition="every_n_turns",
        trigger_frequency=5,
        effect_type="spawn",
        effect_data={"spawn": "goblin_warrior", "location": "entrance"},
        warning_signs=[
            "You hear footsteps echoing from the entrance...",
            "The footsteps grow louder!",
            "Something is coming!",
        ],
        active=True,
        turns_until_trigger=5,
    )

    # Create the TacticalRoom
    dungeon_room = TacticalRoom(
        name="Goblin's Lair",
        base_description="A damp stone chamber lit by a flickering torch.",
        conditional_descriptions=[
            ("goblin_dead", "The goblin's body lies crumpled on the floor."),
            ("chest_open", "The chest stands open, revealing its treasures."),
            ("hp<5", "Your vision blurs from your wounds."),
            ("trap_triggered", "Poison darts stick out from the walls!"),
        ],
        lighting="dim",
        sounds=["dripping water", "distant scratching", "your own breathing"],
        smells=["mildew", "goblin stench", "old leather"],
        zones={
            "entrance": {
                "terrain": TerrainType.NORMAL,
                "cover": "none",
                "elevation": 0,
            },
            "center": {"terrain": TerrainType.NORMAL, "cover": "none", "elevation": 0},
            "chest_area": {
                "terrain": TerrainType.DIFFICULT,
                "cover": "half",
                "elevation": 0,
            },
            "goblin_corner": {
                "terrain": TerrainType.NORMAL,
                "cover": "three_quarters",
                "elevation": 5,
            },
        },
        positions={"player": "entrance", "goblin_1": "goblin_corner"},
        objects=[iron_chest],
        environmental_effects=[goblin_reinforcements_effect],
        flags=set(),
    )

    # Create clean dicts to prevent circular reference issues
    player_dump = player_character.model_dump()
    player_dump["inventory"] = [
        item.model_dump_clean() for item in player_character.inventory
    ]
    player_dump["attacks"] = [
        attack.model_dump_clean() for attack in player_character.attacks
    ]

    goblin_dump = goblin_character.model_dump()
    goblin_dump["attacks"] = [
        attack.model_dump_clean() for attack in goblin_character.attacks
    ]

    return GraphGameState(
        player=player_dump,  # Clean dict to prevent circular references
        npcs={"goblin_1": goblin_dump},  # Clean dict to prevent circular references
        current_room_id="goblin_lair",
        rooms={
            "goblin_lair": dungeon_room.model_dump()
        },  # Convert TacticalRoom to dict
        quest_flags={"has_key": False, "chest_opened": False, "goblin_defeated": False},
        completed_objectives=[],
        in_combat=False,
        combat_order=None,
        current_turn=None,
        recent_actions=[],
        narrative_tone="heroic",
        turn_count=0,
        session_id="enhanced_micro_adventure",
        difficulty="medium",
    )


# This section moved from action_resolution.py to consolidate testing
async def test_action_resolution():
    """Test the action resolution system."""
    print("=" * 50)
    print("🎲 TESTING ACTION RESOLUTION SYSTEM")
    print("=" * 50)

    # Import here to avoid circular import
    from packages.backend.ai.graphs.action_resolution import action_resolution_service

    # Initialize service
    await action_resolution_service.initialize()

    # Test game state
    game_state = create_example_game_state()

    # Test actions to verify routing works correctly
    test_actions = [
        # Combat actions (should route to combat_node)
        # {"action": "I attack the goblin with my sword", "expected_route": "combat_subgraph", "category": "Combat"},
        # {"action": "I swing my sword at the goblin", "expected_route": "combat_subgraph", "category": "Combat"},
        # DEMO: Combat with early exit after initiative (for testing exit_early)
        {
            "action": "I attack the goblin with my sword",
            "expected_route": "combat_subgraph",
            "category": "Combat Demo",
            "test_exit_after_initiative": True,
        },
        # # Interaction actions (should route to interaction_node)
        # {"action": "I use the key on the chest", "expected_route": "interaction_node", "category": "Interaction"},
        # {"action": "I take the silver coin", "expected_route": "interaction_node", "category": "Interaction"},
        # {"action": "I say hello to the goblin", "expected_route": "interaction_node", "category": "Interaction"},
        # {"action": "I use the healing potion", "expected_route": "interaction_node", "category": "Interaction"},
        # {"action": "I open the chest", "expected_route": "interaction_node", "category": "Interaction"},
        # # Exploration actions (should route to exploration_node)
        # {"action": "I search the room", "expected_route": "exploration_node", "category": "Exploration"},
        # {"action": "I examine the chest", "expected_route": "exploration_node", "category": "Exploration"},
        # {"action": "I look around the room", "expected_route": "exploration_node", "category": "Exploration"},
        # {"action": "I stand up", "expected_route": "exploration_node", "category": "Exploration"}
    ]

    # Get current room information
    current_room = TacticalRoom(
        **game_state["rooms"][game_state["current_room_id"]]
    )  # Re-instantiate for methods

    # Explicitly convert inventory items to Item models for the test's Character instantiation
    # The game_state['player'] and game_state['npcs'] are still dicts for LangGraph compatibility.
    # When we need to interact with them as Character objects, we'll load them from the DB.
    # For display purposes, we can create a temporary Character object.
    # This section will be removed or heavily modified in Phase 3.
    # Create Character without relationships first
    player_dict_copy = game_state["player"].copy()
    # Remove relationship fields to avoid SQLAlchemy errors
    for field in [
        "player",
        "campaign",
        "inventory",
        "attacks",
        "action_history",
        "updated_game_state",
    ]:
        player_dict_copy.pop(field, None)
    inventory_dicts = game_state["player"]["inventory"]
    attacks_dicts = game_state["player"]["attacks"]
    player_char = Character(**player_dict_copy)
    player_char.inventory = [Item(**item_data) for item_data in inventory_dicts]
    player_char.attacks = [Attack(**attack_data) for attack_data in attacks_dicts]

    print(f"🏃 Player Character: {player_char.name}")
    print(f"❤️  Health: {player_char.hp}/{player_char.max_hp}")
    print(f"🛡️ AC: {player_char.ac}")

    inventory_display = (
        ", ".join([item.name for item in player_char.inventory])
        if player_char.inventory
        else "Empty"
    )
    print(f"🎒 Inventory: {inventory_display}")
    print(f"📍 Current Room: {current_room.name}")

    room_objects_display = (
        ", ".join([obj.name for obj in current_room.objects])
        if current_room.objects
        else "None"
    )
    print(f"📍 Room objects: {room_objects_display}")

    chest_obj = next(
        (obj for obj in current_room.objects if obj.name == "Iron Chest"), None
    )
    chest_status = "Not found"
    if chest_obj:
        if chest_obj.current_state == "open":
            chest_status = "🔓 Open"
        elif chest_obj.properties.get("locked"):
            chest_status = "🔒 Locked"
        else:
            chest_status = "   box Unlocked"
    print(f"💰 Chest: {chest_status}")
    print("=" * 50)

    # Show quest flags
    quest_flags = game_state.get("quest_flags", {})
    if quest_flags:
        active_quests = [
            f"'{k.replace('_', ' ').title()}'" for k, v in quest_flags.items() if v
        ]
        if active_quests:
            print(f"🎯 Active Quests: {', '.join(active_quests)}")

    print()

    success_count = 0
    total_tests = len(test_actions)

    for test_case in test_actions:
        action = test_case["action"]
        expected_route = test_case["expected_route"]
        category = test_case["category"]

        print(f"\n🎮 [{category}] Testing: '{action}'")
        print("-" * 60)

        # Prepare the state for this test
        test_state = game_state.copy()

        # Handle special test cases
        if test_case.get("test_exit_after_initiative", False):
            test_state["test_exit_after_initiative"] = True
            print("🧪 Special test mode: Exit early after initiative roll")

        try:
            # Pass a copy of the game_state to avoid side effects between tests
            result = await action_resolution_service.resolve_action(
                player_action=action,
                game_state=test_state,
                correlation_id=f"test_{hash(action) % 1000}",
            )

            if result.get("error"):
                print(f"❌ Error: {result['error']}")
                continue

            # Show routing information
            action_type = result.get("parsed_intent", {}).get("action_type", "unknown")
            narrative = result.get("narrative", "No response")
            routed_to = result.get("performance", {}).get("routing_path", "unknown")

            print(f"🎯 Action Type: {action_type}")
            print(f"🎭 Routed to: {routed_to}")

            # Special handling for exit_early tests
            if test_case.get("test_exit_after_initiative", False):
                initiative_completed = result.get("initiative_completed", False)
                exit_early = result.get("exit_early", False)

                if initiative_completed and exit_early:
                    print("✅ INITIATIVE COMPLETED - Testing exit_early signal")
                    print("🛑 PROCESS TERMINATED EARLY (no process_turn)")
                    print(
                        "📖 Response: Initiative rolled successfully, system exited per test mode"
                    )

                    # Show combat state from result
                    combat_state = result.get(
                        "resolved_combat_state", {}
                    ) or test_state.get("combat_state", {})
                    if combat_state:
                        print("🔥 Final Combat State Summary:")
                        initiative_queue = combat_state.get("initiative_queue", [])
                        if initiative_queue:
                            print(f"   Turn Order: {' → '.join(initiative_queue)}")
                            print(
                                f"   Active Turn: {combat_state.get('active_turn_participant_id', 'None')}"
                            )
                else:
                    print(
                        "⚠️  Expected initiative completion and exit_early, but didn't receive it"
                    )
            else:
                print(f"📖 Response: {narrative}")

            # Show state changes if any (compare key properties)
            updated_game_state = result.get("updated_game_state")
            if updated_game_state and updated_game_state != game_state:
                state_changes = []

                # For display purposes, create temporary Character objects from the dicts
                updated_player_dict = updated_game_state["player"].copy()
                for field in [
                    "player",
                    "campaign",
                    "inventory",
                    "attacks",
                    "action_history",
                ]:
                    updated_player_dict.pop(field, None)
                updated_player_char = Character(**updated_player_dict)
                updated_player_char.inventory = [
                    Item(**item_data)
                    for item_data in updated_game_state["player"]["inventory"]
                ]
                updated_player_char.attacks = [
                    Attack(**attack_data)
                    for attack_data in updated_game_state["player"]["attacks"]
                ]

                original_player_dict = game_state["player"].copy()
                for field in [
                    "player",
                    "campaign",
                    "inventory",
                    "attacks",
                    "action_history",
                ]:
                    original_player_dict.pop(field, None)
                original_player_char = Character(**original_player_dict)
                original_player_char.inventory = [
                    Item(**item_data) for item_data in game_state["player"]["inventory"]
                ]
                original_player_char.attacks = [
                    Attack(**attack_data)
                    for attack_data in game_state["player"]["attacks"]
                ]

                if updated_player_char.hp != original_player_char.hp:
                    state_changes.append(
                        f"HP: {original_player_char.hp} → {updated_player_char.hp}"
                    )

                # Compare individual currency fields
                if (
                    updated_player_char.copper_pieces
                    != original_player_char.copper_pieces
                    or updated_player_char.silver_pieces
                    != original_player_char.silver_pieces
                    or updated_player_char.electrum_pieces
                    != original_player_char.electrum_pieces
                    or updated_player_char.gold_pieces
                    != original_player_char.gold_pieces
                    or updated_player_char.platinum_pieces
                    != original_player_char.platinum_pieces
                ):
                    state_changes.append("Wallet changed.")

                if len(updated_player_char.inventory) != len(
                    original_player_char.inventory
                ):
                    state_changes.append(
                        f"Inventory changed (count: {len(original_player_char.inventory)} → {len(updated_player_char.inventory)})."
                    )
                else:
                    # More detailed inventory comparison if needed
                    pass

                updated_room = TacticalRoom(
                    **updated_game_state["rooms"][updated_game_state["current_room_id"]]
                )
                original_room = TacticalRoom(
                    **game_state["rooms"][game_state["current_room_id"]]
                )

                if updated_room.objects != original_room.objects:
                    state_changes.append("Room objects changed.")

                if updated_game_state["quest_flags"] != game_state["quest_flags"]:
                    state_changes.append("Quest flags changed.")

                if state_changes:
                    print(f"📊 State Changes: {', '.join(state_changes)}")
                else:
                    print("📊 No significant state changes detected.")

            # Special success checking for exit_early tests
            if test_case.get("test_exit_after_initiative", False):
                initiative_completed = result.get("initiative_completed", False)
                if initiative_completed and exit_early:
                    print("✅ EXIT_EARLY demo test passed!")
                    success_count += 1
                else:
                    print(
                        "❌ EXIT_EARLY demo test failed - initiation may not have completed"
                    )
            elif routed_to == expected_route:
                print("✅ Routing test passed.")
                success_count += 1
            else:
                print(
                    f"❌ Routing test FAILED. Expected: {expected_route}, Got: {routed_to}"
                )

        except Exception as e:
            print(f"❌ Test failed: {str(e)}")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {success_count}/{total_tests} tests passed")
    print(
        "🎯 Enhanced conditional routing implementation provides flexible action routing!"
    )


if __name__ == "__main__":
    asyncio.run(test_action_resolution())
