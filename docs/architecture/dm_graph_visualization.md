# DM Graph Visualization

This document explains how to visualize the LangGraph state machine implemented in `packages/backend/agents/dm_graph.py`.

## Visualization Options

### 1. Static DOT File Visualization
- **File**: `docs/architecture/dm_graph.dot`
- **Requirements**: Graphviz installed system-wide
- **Generation**:
  ```bash
  dot -Tpng docs/architecture/dm_graph.dot -o docs/architecture/dm_graph.png
  ```
- **Features**: 
  - Shows predefined state machine structure
  - Color-coded paths (normal vs error handling)
  - Clear entry/exit points

### 2. Dynamic Visualization from Code
- **Script**: `packages/backend/scripts/visualize_dm_graph.py`
- **Requirements**:
  ```bash
  pip install pygraphviz
  # Install Graphviz binaries from https://graphviz.org/download/
  ```
- **Usage**:
  ```bash
  python packages/backend/scripts/visualize_dm_graph.py
  ```
- **Output**: `dm_graph_visualization.png` in current directory
- **Features**:
  - Generated directly from runtime code
  - Always matches current implementation
  - Shows actual node/edge relationships

## Interpreting the Visualization

The DM Graph visualization shows:
1. **Nodes**: Processing stages (process_prompt, compile_context, etc.)
2. **Edges**:
   - Solid lines: Normal workflow progression
   - Dashed lines: Conditional error routing
   - Red arrows: Error handling paths
3. **Special Nodes**:
   - Entry point: Where processing begins
   - END: Final state after successful completion

## Example Output
![DM Graph Visualization](dm_graph_visualization.png)

## Customization
To modify the visualization:
1. For static version: Edit `docs/architecture/dm_graph.dot`
2. For dynamic version: Modify the script to customize Graphviz attributes:
```python
# Example: Custom node styling
graph = compiled_graph.get_graph()
graph.node_attr.update(style='filled', fillcolor='lightblue')
graph.edge_attr.update(color='blue', arrowhead='vee')
graph.draw("custom_dm_graph.png")