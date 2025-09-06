import json
from typing import Dict, List, Optional

from packages.shared.models.core_db_models import (
    Attack,
    Character,
    DamageType,
    Item,
)
from packages.shared.models.langgraph_state_models import (
    CombatParticipant,
    CombatState,
    MinimalGameState,
)


def create_test_character(
    character_id: int,
    name: str,
    hp: int = 10,
    ac: int = 14,
    is_hostile: bool = False,
    level: int = 1,
    strength: int = 16,
    dexterity: int = 14,
    constitution: int = 12,
    intelligence: int = 12,
    wisdom: int = 12,
    charisma: int = 12,
    attacks: Optional[List[Attack]] = None,
    inventory: Optional[List[Item]] = None,
) -> Character:
    """Factory for creating a test Character."""
    if attacks is None:
        attacks = [
            Attack(
                name="Test Attack",
                bonus=5,
                damage="1d8+3",
                damage_type=DamageType.SLASHING,
                range=5,
            )
        ]
    if inventory is None:
        inventory = []

    return Character(
        character_id=character_id,
        name=name,
        hp=hp,
        max_hp=hp,
        ac=ac,
        is_hostile=is_hostile,
        level=level,
        strength=strength,
        dexterity=dexterity,
        constitution=constitution,
        intelligence=intelligence,
        wisdom=wisdom,
        charisma=charisma,
        conditions=json.dumps([]),
        attacks=attacks,
        inventory=inventory,
    )


def create_test_item(
    name: str,
    item_type: str,
    description: str,
    weight: float = 0.0,
    value: int = 0,
    quantity: int = 1,
) -> Item:
    """Factory for creating a test Item."""
    return Item(
        name=name,
        type=item_type,
        description=description,
        weight=weight,
        value=value,
        quantity=quantity,
    )


def create_test_minimal_game_state(
    player_action: str = "",
    exit_early: bool = False,
    state_players: Optional[List[str]] = None,
    state_enemies: Optional[List[str]] = None,
    state_npcs: Optional[List[str]] = None,
    combat_state: Optional[CombatState] = None,
) -> MinimalGameState:
    """Factory for creating a test MinimalGameState."""
    if state_players is None:
        state_players = ["character_1"]
    if state_enemies is None:
        state_enemies = []
    if state_npcs is None:
        state_npcs = []

    return MinimalGameState(
        campaign_id=1,
        character_id=1,
        state_players=state_players,
        state_npcs=state_npcs,
        state_enemies=state_enemies,
        discord_user_id="test_user",
        discord_channel_id="test_channel",
        correlation_id="test_correlation",
        player_action=player_action,
        parsed_intent=None,
        action_result=None,
        dice_results=None,
        combat_state=combat_state,
        exit_early=exit_early,
        error=None,
    )


def create_test_combat_participant(
    participant_id: int,
    name: str,
    creature_type: str,
    hp: int = 10,
    dex_modifier: int = 2,
) -> CombatParticipant:
    """Factory for creating a test CombatParticipant."""
    return CombatParticipant(
        id=participant_id,
        campaign_id=1,
        creature_type=creature_type,
        creature_id=participant_id,
        creature_name=name,
        current_health=hp,
        max_health=hp,
        initiative_modifier=dex_modifier,
        temp_hp=0,
    )


def create_test_combat_state(
    participants: List[CombatParticipant],
) -> CombatState:
    """Factory for creating a test CombatState."""
    participant_dict: Dict[str, CombatParticipant] = {
        p.participant_key: p for p in participants
    }
    active_keys = [p.participant_key for p in participants]

    return CombatState(
        campaign_id=1,
        participants=participant_dict,
        active_participants=active_keys,
        active_participant_id=active_keys[0] if active_keys else None,
    )


def create_test_game_state_with_combat() -> MinimalGameState:
    """
    Creates a test game state with a player and a monster in combat.
    """
    # Create a player and a monster
    player = create_test_combat_participant(
        participant_id=1, name="Test Player", creature_type="player"
    )
    monster = create_test_combat_participant(
        participant_id=2, name="Test Monster", creature_type="enemy", hp=15
    )

    # Create the combat state
    combat_state = create_test_combat_state(participants=[player, monster])

    # Create the minimal game state
    game_state = create_test_minimal_game_state(
        state_players=[player.participant_key],
        state_enemies=[monster.participant_key],
        combat_state=combat_state,
    )

    return game_state


def create_test_state_for_combat_init() -> (
    MinimalGameState,
    Dict[str, Character],
):
    """
    Creates a test game state for combat initialization.

    Returns a tuple containing:
    - A MinimalGameState with participant keys for a player, NPC, and enemy.
    - A dictionary mapping participant keys to their mock Character objects.
    """
    # Create mock characters
    player_char = create_test_character(character_id=1, name="Test Player")
    friendly_npc_char = create_test_character(character_id=2, name="Friendly NPC")
    hostile_npc_char = create_test_character(
        character_id=3, name="Hostile NPC", is_hostile=True
    )
    enemy_char = create_test_character(character_id=4, name="Goblin", is_hostile=True)

    # The participant key format is `type_id`
    participants = {
        f"character_{player_char.character_id}": player_char,
        f"character_{friendly_npc_char.character_id}": friendly_npc_char,
        f"character_{hostile_npc_char.character_id}": hostile_npc_char,
        f"character_{enemy_char.character_id}": enemy_char,
    }

    # Create the minimal game state
    game_state = create_test_minimal_game_state(
        state_players=[f"character_{player_char.character_id}"],
        state_npcs=[
            f"character_{friendly_npc_char.character_id}",
            f"character_{hostile_npc_char.character_id}",
        ],
        state_enemies=[f"character_{enemy_char.character_id}"],
        combat_state=None,  # No combat state initially
    )

    return game_state, participants


def create_test_state_for_initiative_roll() -> MinimalGameState:
    """
    Creates a MinimalGameState populated with an initialized CombatState,
    ready for testing the initiative roll node.
    """
    # Create participants
    player = create_test_combat_participant(
        participant_id=1, name="Test Player", creature_type="player"
    )
    friendly_npc = create_test_combat_participant(
        participant_id=2, name="Friendly NPC", creature_type="npc"
    )
    hostile_npc = create_test_combat_participant(
        participant_id=3, name="Hostile NPC", creature_type="enemy"
    )
    enemy = create_test_combat_participant(
        participant_id=4, name="Goblin", creature_type="enemy", hp=15
    )
    participants = [player, friendly_npc, hostile_npc, enemy]

    # Create the combat state
    combat_state = create_test_combat_state(participants=participants)

    # Create the minimal game state
    game_state = create_test_minimal_game_state(
        state_players=[player.participant_key],
        state_npcs=[friendly_npc.participant_key, hostile_npc.participant_key],
        state_enemies=[enemy.participant_key],
        combat_state=combat_state,
    )

    return game_state
