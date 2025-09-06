#!/usr/bin/env python3
"""Debug the exact import issue"""

print("🔍 DEBUGGING IMPORT ISSUE")

try:
    print("Testing GameState import...")
    from packages.backend.ai.state.game_state import (
        create_micro_adventure_state,
    )

    print("✅ GameState import successful")

    print("Testing LangGraph imports...")
    from langgraph.graph import StateGraph

    print("✅ LangGraph imports successful")

    print("Testing ActionResolutionState...")
    from packages.backend.ai.state import ActionResolutionState

    print("✅ ActionResolutionState import successful")

    print("Testing create_micro_adventure_state() call...")
    game_state = create_micro_adventure_state()
    print("✅ Game state creation successful")

    print("Testing StateGraph construction...")
    workflow = StateGraph(ActionResolutionState)
    print("✅ StateGraph construction successful")
    print("✅ ALL IMPORTS WORKING!")

except Exception as e:
    print(f"❌ IMPORT ERROR: {e}")
    import traceback

    traceback.print_exc()
