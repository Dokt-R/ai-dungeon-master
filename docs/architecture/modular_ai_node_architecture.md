# Modular AI Node Architecture

## Overview

This document outlines the modular architecture for AI graph nodes in the Dungeon Master system, providing a scalable framework for organizing and extending AI behavior components. The architecture follows domain-driven design principles with clear separation of concerns and modular organization.

## Rationale

### Problem Solved
Traditional monolithic AI graph implementations become difficult to maintain as complexity increases:
- **Tight Coupling**: All node logic interweaved in single files
- **Scalability Issues**: Adding new AI behaviors requires modifying existing code
- **Debugging Difficulty**: Tracing issues across mixed concerns
- **Team Collaboration**: Multiple developers working on overlapping functionality

### Solution Approach
The modular architecture addresses these issues by:
- **Domain Separation**: Group related functionality by concern/area
- **Independent Evolution**: Each module evolves independently
- **Clear Ownership**: Team members can own specific domains
- **Reusable Components**: Nodes can be mixed and matched across graphs
- **Testability**: Each module can be unit tested in isolation

## Architecture Principles

### 1. Domain-Driven Organization
- **Core Nodes**: Shared functionality (parsing, routing, state management)
- **Domain-Specific Nodes**: Specialized behavior (combat, exploration, social)
- **Separation by Concern**: Each node handles one specific responsibility

### 2. Import Hierarchy
- Clear import paths following Python module conventions
- Consistent naming: `domain_function_node`
- Module-level `__init__.py` for clean exports

### 3. State Management Integration
- Nodes operate on shared state objects
- Stateless function design for testability
- Consistent error handling patterns

### 4. Future-Ready Design
- Extensible structure for new domain additions
- Placeholder modules for planned features
- Minimal breaking changes when adding new nodes

## File Structure

```
packages/backend/ai/nodes/
├── __init__.py                              # Central node registry
├── core/                                     # Shared functionality
│   ├── __init__.py                           # Core node exports
│   ├── parse_intent_node.py                  # Text processing
│   ├── resolve_action_node.py                # Action routing
│   ├── update_state_node.py                  # State management
│   └── narrate_result_node.py                # Response generation
├── combat/                                   # Combat mechanics
│   ├── __init__.py                           # Combat node exports
│   └── combat_resolution_node.py             # Attack resolution
├── exploration/                              # World interaction
│   ├── __init__.py                           # Exploration node exports
│   └── exploration_resolution_node.py        # Search/navigation
├── social/                                   # Social interactions
│   ├── __init__.py                           # Social node exports
│   └── social_interaction_node.py            # NPC conversations (future)
└── [new_domain]/                             # For future expansions
    ├── __init__.py
    └── [domain_nodes]_node.py
```

## Current Implementation

### Core Nodes (`packages/backend/ai/nodes/core/`)

#### parse_intent_node.py
**Purpose**: Analyzes player input text to determine intent
**Function**: `parse_intent_node(state: ActionResolutionState) -> Dict[str, Any]`
**Responsibilities**:
- Keyword-based text analysis
- Target entity extraction
- Confidence scoring
- Intent classification

#### resolve_action_node.py
**Purpose**: Routes parsed intents to appropriate handlers
**Function**: `resolve_action_node(state: ActionResolutionState) -> Dict[str, Any]`
**Responsibilities**:
- Action routing decisions
- Handler selection logic
- Integration with future conditional edges

#### update_state_node.py
**Purpose**: Updates game state based on action results
**Function**: `update_state_node(state: ActionResolutionState) -> Dict[str, Any]`
**Responsibilities**:
- HP and status modifications
- Game state mutations
- Permanent state persistence

#### narrate_result_node.py
**Purpose**: Generates narrative responses for players
**Function**: `narrate_result_node(state: ActionResolutionState) -> Dict[str, Any]`
**Responsibilities**:
- Response text generation
- Narrative variation
- Player feedback formatting

### Domain-Specific Nodes

#### combat_resolution_node.py
**Purpose**: Handles combat mechanics and attack resolution
**Function**: `combat_node(state: ActionResolutionState) -> Dict[str, Any]`
**Responsibilities**:
- Attack roll calculations
- Damage resolution
- Hit/miss determination
- Combat state updates

#### exploration_resolution_node.py
**Purpose**: Manages exploration and world interaction
**Function**: `exploration_node(state: ActionResolutionState) -> Dict[str, Any]`
**Responsibilities**:
- Search mechanics
- World navigation
- Environmental interactions
- Discovery mechanisms

## Node Development Guidelines

### 1. Node Function Signature
All node functions follow this signature:
```python
async def node_name(state: StateType) -> Dict[str, Any]:
    """Clear docstring describing node purpose and behavior."""
    # Implementation
    return {"result_key": "result_value"}
```

### 2. Error Handling
Nodes should handle errors gracefully:
```python
async def node_name(state: StateType) -> Dict[str, Any]:
    try:
        # Node logic
        result = perform_operation()
        return {"result": result}
    except Exception as e:
        logger.error("node_name_failed", error=str(e))
        return {"error": f"Operation failed: {str(e)}"}
```

### 3. Logging Standards
Use structured logging with correlation IDs:
```python
logger.debug("node_processing_started", correlation_id=state["correlation_id"])
logger.info("node_operation_completed", result_length=len(result))
```

### 4. State Management
- Never modify state objects directly (immutable updates)
- Use functional updates: `return {"updated_field": new_value}`
- Validate input state before processing

### 5. Documentation
Each node file should include:
- Purpose description
- Function signature documentation
- Example usage
- Error handling cases
- Future considerations

## Graph Integration

### Current Implementation (Action Resolution Graph)
```python
# Node imports from modular modules
from packages.backend.ai.nodes.core import (
    parse_intent_node,
    resolve_action_node,
    update_state_node,
    narrate_result_node
)
from packages.backend.ai.nodes.combat.combat_resolution_node import combat_node

# Graph construction
workflow.add_node("parse_intent", parse_intent_node)
workflow.add_node("resolve_action", resolve_action_node)
workflow.add_node("combat_node", combat_node)
workflow.add_node("update_state", update_state_node)
workflow.add_node("narrate_result", narrate_result_node)

# Linear flow for current implementation
workflow.set_entry_point("parse_intent")
workflow.add_edge("parse_intent", "resolve_action")
workflow.add_edge("resolve_action", "combat_node")
workflow.add_edge("combat_node", "update_state")
workflow.add_edge("update_state", "narrate_result")
```

## Future Expansions

### Planned Node Categories
- **Social Nodes**: `social_conversation_node.py`, `social_deception_node.py`
- **Magic Nodes**: `spell_casting_node.py`, `spell_resolution_node.py`
- **Crafting Nodes**: `item_creation_node.py`, `resource_gathering_node.py`

### Conditional Routing (Future)
The architecture supports conditional edges for complex flows:
```python
# Future: conditional routing based on action type
workflow.add_conditional_edges(
    "resolve_action",
    lambda state: state.get("action_type", "unknown"),
    {
        "attack": "combat_node",
        "explore": "exploration_node",
        "social": "social_node",
    }
)
```

## Testing Strategy

### Unit Testing
Each node module should have comprehensive tests:
```
tests/unit/backend/ai/nodes/
├── core/
│   ├── test_parse_intent_node.py
│   ├── test_resolve_action_node.py
│   └── ...
├── combat/
│   └── test_combat_resolution_node.py
└── ...
```

### Integration Testing
End-to-end graph testing validates node interactions:
```python
def test_action_resolution_graph():
    # Test complete flow from input to narrative
    result = await action_resolution_service.resolve_action(
        action_text="I attack the goblin",
        game_state=example_state,
        correlation_id="test_123"
    )
    assert "narrative" in result
    assert not result.get("error")
```

## Best Practices

### 1. Single Responsibility
Each node should do "one thing well":
- ✅ Specific node for intent parsing - GOOD
- ❌ One node handling both parsing AND combat - BAD

### 2. Error Boundaries
Handle errors at appropriate levels:
- Node-level: Graceful failure for that operation
- Graph-level: Fallback responses when nodes fail

### 3. Performance Considerations
- Keep node functions lightweight
- Avoid blocking operations in async nodes
- Use observability tracing for monitoring

### 4. Extensibility
Design nodes to accept configuration:
```python
async def combat_node(state: ActionResolutionState, config: Dict = None) -> Dict[str, Any]:
    config = config or {"difficulty_modifier": 0}
    # Use config in resolution logic
```

## Migration Guide

### From Monolithic to Modular
1. **Identify Concerns**: Break down monolith into logical domains
2. **Extract Functions**: Move node functions to separate files
3. **Create Exports**: Add proper `__init__.py` files
4. **Update Imports**: Modify graph files to import from new locations
5. **Test Thoroughly**: Ensure no behavioral changes

### Example Migration Process
```python
# Before (monolithic)
async def _combat_node(self, state):
    # 200 lines of combat logic

# After (modular)
from packages.backend.ai.nodes.combat.combat_resolution_node import combat_node

workflow.add_node("combat_node", combat_node)
```

## Conclusion

The modular AI node architecture provides a scalable foundation for the Dungeon Master system's AI components. By separating concerns into domain-specific modules, we achieve:
- Improved maintainability through clear boundaries
- Enhanced testability with focused unit tests
- Better collaboration through ownership separation
- Future-ready design supporting new capabilities

This architecture positions the system for continued evolution as new AI behaviors and game mechanics are added.