"""
Combat Step by Step
Combat unfolds in these steps:
1: Establish Positions. The Game Master determines where all the characters and monsters are
located. Given the adventurers’ marching order
or their stated positions in the room or other location, the GM figures out where the adversaries
are—how far away and in what direction.
2: Roll Initiative. Everyone involved in the combat
encounter rolls Initiative, determining the order
of combatants’ turns.
3: Take Turns. Each participant in the battle takes
a turn in Initiative order. When everyone involved in the combat has had a turn, the round
ends. Repeat this step until the fighting stops
"""

# import asyncio
# import time
# from dataclasses import dataclass, field
# from operator import add
# from langgraph.prebuilt import ToolNode
# from typing_extensions import Annotated
# from packages.backend.agents.prompts import prompt_manager
# from packages.backend.components.ai_client import ai_client
# from packages.backend.components.memory_service import memory_service
# from packages.backend.components.observability_service import observability_service
# from packages.shared.logging_config import configure_logging, get_logger
# from packages.shared.models import MemoryState
# configure_logging()
# logger = get_logger(__name__)
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict

# from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph


# State definition
class CombatState(TypedDict):
    phase: str  # "setup", "initiative", "combat", "end"
    participants: List[Dict[str, Any]]  # Character/creature data
    surprise_round: bool
    initiative_order: List[Dict[str, Any]]
    current_turn: int
    round_number: int
    needs_dm_input: Optional[str]
    dm_context: str
    setup_complete: bool
    combat_active: bool


@dataclass
class Participant:
    name: str
    initiative: int = 0
    hp: int = 0
    max_hp: int = 0
    ac: int = 10
    is_surprised: bool = False
    conditions: List[str] = None

    def __post_init__(self):
        if self.conditions is None:
            self.conditions = []


"""
Example main AI DM system

def main_dm_agent(state):
    # Normal narrative generation
    if combat_graph_needs_input(state):
        # Combat graph is asking for a decision
        input_type = state["needs_dm_input"]
        
        if input_type == "combat_participants":
            # AI DM analyzes scene and determines participants
            participants = analyze_scene_for_combatants(state["scene_context"])
            return resume_combat_graph(state, {"participants": participants})
            
        elif input_type == "surprise_check":
            # AI DM makes narrative decision about surprise
            surprise_decision = decide_surprise(state["dm_context"], state["ai_suggestion"])
            return resume_combat_graph(state, {"surprise_round": surprise_decision})
            
        elif input_type == "combat_action":
            # AI DM decides what NPCs do, prompts for PC actions
            current_participant = state["current_participant"]
            if is_npc(current_participant):
                action = ai_decide_npc_action(current_participant, state)
                return resume_combat_graph(state, {"action_result": action})
            else:
                # Prompt player for their action
                return {"message": f"What does {current_participant['name']} do?"}


def ai_analyze_surprise(scene_context: str) -> bool:
    # AI DM decides surprise based on narrative context
    # Call your main AI DM with specific prompt
    prompt = f"
    Based on this scene: {scene_context}
    
    Should any creatures be surprised? Consider:
    - Was this an ambush?
    - Were participants aware of each other?
    - Did anyone have the drop on others?
    
    Return only: TRUE or FALSE
    "
    
    result = your_ai_dm_llm.invoke(prompt)
    return "TRUE" in result.upper()

def ai_decide_npc_action(npc_data: dict, combat_state: dict) -> dict:
    # AI DM decides what NPCs do on their turn
    prompt = f"
    You are controlling {npc_data['name']} in combat.
    
    NPC Stats: HP {npc_data['hp']}/{npc_data['max_hp']}, AC {npc_data['ac']}
    Current situation: {describe_combat_situation(combat_state)}
    
    What does {npc_data['name']} do? Choose an action and target.
    Return format: {{"action": "attack", "target": "Aragorn", "description": "swings sword"}}
    "
    
    return parse_ai_action(your_ai_dm_llm.invoke(prompt))
"""


def get_combat_participants():
    """
    Determine participants
    """
    return


def establish_positions():
    """
    Determine where all the characters and monsters are
    located. Given the adventurers marching order
    or their stated positions in the room or other location,
    the GM figures out where the adversaries are,
    how far away and in what direction
    """
    return


# Node implementations
def setup_combat(state: CombatState) -> Dict[str, Any]:
    """
    Initial combat setup - DM provides participants and conditions
    """
    print("Starting setup!!!")
    # Check if we have participants
    if not state.get("participants"):
        return {
            "needs_dm_input": "combat_participants",
            "dm_context": "Who is participating in this combat? Please provide participant names and basic stats.",  #! Proceed by generating monsters from statblocks
        }

    # Check surprise conditions
    if "surprise_round" not in state:
        # AI can suggest based on context
        scenario_context = state.get("dm_context", "")
        suggestion = analyze_surprise_conditions(scenario_context)

        return {
            "needs_dm_input": "surprise_check",
            "dm_context": f"Surprise round? Context: {scenario_context}",
            "ai_suggestion": suggestion,
        }

    # Setup complete
    return {
        "setup_complete": True,
        "phase": "initiative",
        "round_number": 1 if not state.get("surprise_round") else 0,
    }


def analyze_surprise_conditions(context: str) -> str:
    """
    AI helper to suggest surprise conditions based on narrative context
    """
    # This would call your LLM to analyze
    # For now, simple keyword analysis
    context_lower = context.lower()

    if any(
        word in context_lower for word in ["ambush", "sneak", "unaware", "surprise"]
    ):
        return "LIKELY - Context suggests ambush or stealth scenario"
    elif any(word in context_lower for word in ["ready", "prepared", "expecting"]):
        return "UNLIKELY - Participants seem prepared for combat"
    else:
        return "UNCLEAR - Need DM decision based on narrative context"


def roll_initiative_node(state: CombatState) -> Dict[str, Any]:
    """
    Roll initiative for all participants
    """
    print("🎲 Rolling Initiative...")

    participants = state["participants"]
    initiative_results = []

    for participant in participants:
        # Roll 1d20 + DEX modifier
        dex_mod = participant.get("dex_modifier", 0)
        roll = random.randint(1, 20) + dex_mod

        participant_data = {
            "name": participant["name"],
            "initiative": roll,
            "roll_detail": f"d20({roll - dex_mod}) + DEX({dex_mod}) = {roll}",
            "hp": participant.get("hp", participant.get("max_hp", 10)),
            "max_hp": participant.get("max_hp", 10),
            "ac": participant.get("ac", 10),
            "is_surprised": participant.get("is_surprised", False),
        }

        initiative_results.append(participant_data)
        print(f"  {participant['name']}: {roll} ({participant_data['roll_detail']})")

    return {"phase": "initiative_rolled", "participants": initiative_results}


def determine_turn_order(state: CombatState) -> Dict[str, Any]:
    """
    Sort participants by initiative and set up turn order
    """
    print("🎲 Determining Turn Order...")

    participants = state["participants"]

    # Sort by initiative (highest first), with tie-breaking by DEX
    sorted_participants = sorted(
        participants,
        key=lambda p: (p["initiative"], p.get("dex_modifier", 0)),
        reverse=True,
    )

    print("Turn Order:")
    for i, participant in enumerate(sorted_participants, 1):
        surprise_status = " (SURPRISED)" if participant.get("is_surprised") else ""
        print(
            f"  {i}. {participant['name']}: {participant['initiative']}{surprise_status}"
        )

    return {
        "initiative_order": sorted_participants,
        "current_turn": 0,
        "phase": "combat",
        "combat_active": True,
    }


def combat_round_node(state: CombatState) -> Dict[str, Any]:
    """
    Execute a single combat round
    """
    initiative_order = state["initiative_order"]
    current_turn = state["current_turn"]
    round_number = state["round_number"]

    # Check if round is complete
    if current_turn >= len(initiative_order):
        return end_round(state)

    # Get current participant
    current_participant = initiative_order[current_turn]

    # Skip surprised participants in round 1 (round 0 is surprise round)
    if round_number == 1 and current_participant.get("is_surprised", False):
        print(f"⏭️  {current_participant['name']} is surprised and loses their turn")
        return {"current_turn": current_turn + 1}

    # Execute turn
    print(f"\n🗡️  {current_participant['name']}'s turn (Round {round_number})")
    print(f"   HP: {current_participant['hp']}/{current_participant['max_hp']}")
    print(f"   AC: {current_participant['ac']}")

    if current_participant.get("conditions"):
        print(f"   Conditions: {', '.join(current_participant['conditions'])}")

    # This is where you'd hand control back to DM or AI for action resolution
    return {
        "needs_dm_input": "combat_action",
        "dm_context": f"{current_participant['name']}'s turn. What do they do?",
        "current_participant": current_participant,
    }


def process_combat_action(
    state: CombatState, action_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process the result of a combat action and advance turn
    """
    # This would be called after DM inputs the action result
    current_turn = state["current_turn"]

    # Apply any damage, effects, etc. from action_result
    if "damage" in action_result:
        target_name = action_result["target"]
        damage = action_result["damage"]

        # Find and update target
        for participant in state["initiative_order"]:
            if participant["name"] == target_name:
                participant["hp"] = max(0, participant["hp"] - damage)
                print(
                    f"💥 {target_name} takes {damage} damage! ({participant['hp']}/{participant['max_hp']} HP remaining)"
                )
                break

    # Advance to next turn
    return {"current_turn": current_turn + 1, "needs_dm_input": None}


def end_round(state: CombatState) -> Dict[str, Any]:
    """
    End current round and start new one
    """
    round_number = state["round_number"]
    print(f"\n🔄 End of Round {round_number}")

    # Check for combat end conditions
    alive_participants = [p for p in state["initiative_order"] if p["hp"] > 0]

    # Simple check: if only one "side" remains (this is simplified)
    if len(alive_participants) <= 1:
        return end_combat(state)

    # Process end-of-round effects (concentration, conditions, etc.)
    updated_participants = process_end_of_round_effects(state["initiative_order"])

    print(f"\n🆕 Starting Round {round_number + 1}")

    return {
        "round_number": round_number + 1,
        "current_turn": 0,
        "initiative_order": updated_participants,
    }


def process_end_of_round_effects(participants: List[Dict]) -> List[Dict]:
    """
    Handle end-of-round effects like condition duration, concentration, etc.
    """
    for participant in participants:
        # Remove expired conditions (simplified)
        if participant.get("conditions"):
            # This would be more complex in reality
            participant["conditions"] = [
                c
                for c in participant["conditions"]
                if not c.startswith("temp_")  # Remove temporary conditions
            ]

    return participants


def end_combat(state: CombatState) -> Dict[str, Any]:
    """
    End combat and return to narrative mode
    """
    print("\n⚔️  Combat Ended!")

    # Summary
    survivors = [p for p in state["initiative_order"] if p["hp"] > 0]
    casualties = [p for p in state["initiative_order"] if p["hp"] <= 0]

    if survivors:
        print("Survivors:")
        for survivor in survivors:
            print(f"  {survivor['name']}: {survivor['hp']}/{survivor['max_hp']} HP")

    if casualties:
        print("Casualties:")
        for casualty in casualties:
            print(f"  {casualty['name']}: 0 HP")

    return {
        "phase": "end",
        "combat_active": False,
        "combat_summary": {
            "rounds": state["round_number"],
            "survivors": survivors,
            "casualties": casualties,
        },
    }


# Routing function
def route_combat(state: CombatState) -> str:
    """
    Determine next node based on current state
    """
    if state.get("needs_dm_input"):
        return "wait_for_dm"

    phase = state.get("phase", "setup")

    if phase == "setup" and not state.get("setup_complete"):
        return "setup_combat"
    elif phase == "initiative" or (state.get("setup_complete") and phase == "setup"):
        return "roll_initiative"
    elif phase == "initiative_rolled":
        return "determine_turn_order"
    elif phase == "combat" and state.get("combat_active"):
        return "combat_round"
    else:
        return "end_combat"


# Example of building the graph
def create_combat_graph():
    """
    Create the complete combat state graph
    """
    workflow = StateGraph(CombatState)

    # Add nodes
    workflow.add_node("get_combat_participants", get_combat_participants)
    workflow.add_node("establish_positions", establish_positions)
    workflow.add_node("setup_combat", setup_combat)
    workflow.add_node("roll_initiative", roll_initiative_node)
    workflow.add_node("determine_turn_order", determine_turn_order)
    workflow.add_node("combat_round", combat_round_node)
    workflow.add_node("end_combat", end_combat)

    # Set entry point
    workflow.set_entry_point("setup_combat")

    # Add conditional routing
    workflow.add_conditional_edges(
        "setup_combat",
        route_combat,
        {
            "setup_combat": "setup_combat",
            "roll_initiative": "roll_initiative",
            "wait_for_dm": "__end__",  # Pause for DM input
        },
    )

    workflow.add_conditional_edges(
        "roll_initiative",
        route_combat,
        {"determine_turn_order": "determine_turn_order"},
    )

    workflow.add_conditional_edges(
        "determine_turn_order", route_combat, {"combat_round": "combat_round"}
    )

    workflow.add_conditional_edges(
        "combat_round",
        route_combat,
        {
            "combat_round": "combat_round",
            "end_combat": "end_combat",
            "wait_for_dm": "__end__",  # Pause for action input
        },
    )

    return workflow.compile()


# Usage example
if __name__ == "__main__":
    # Create graph
    combat_graph = create_combat_graph()

    # Example initial state
    initial_state = {
        "phase": "setup",
        "participants": [
            {"name": "Aragorn", "hp": 45, "max_hp": 45, "ac": 18, "dex_modifier": 2},
            {"name": "Legolas", "hp": 35, "max_hp": 35, "ac": 16, "dex_modifier": 4},
            {
                "name": "Orc Warrior",
                "hp": 25,
                "max_hp": 25,
                "ac": 14,
                "dex_modifier": 1,
            },
        ],
        "surprise_round": False,
        "dm_context": "The party encounters orc raiders on the road",
        "setup_complete": False,
        "combat_active": False,
        "current_turn": 0,
        "round_number": 1,
    }

    # Run combat
    result = combat_graph.invoke(initial_state)
    print(f"\nFinal State: {result}")
