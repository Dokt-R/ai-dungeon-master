"""
Script to visualize the DM Graph using LangGraph's built-in visualization

Dependencies:
  - pygraphviz: Install with `pip install pygraphviz`
  - Graphviz: Install system-wide (see https://graphviz.org/download/)
"""

import asyncio

from packages.backend.ai.dm_graph import dm_graph_service


async def visualize_dm_graph():
    # Initialize the DM graph service
    if not await dm_graph_service.initialize():
        print("Failed to initialize DM Graph service")
        return

    # Access the compiled graph
    compiled_graph = dm_graph_service._graph

    # Generate and save visualization
    compiled_graph.get_graph().draw("dm_graph_visualization.png")
    print("DM Graph visualization saved as 'dm_graph_visualization.png'")


if __name__ == "__main__":
    asyncio.run(visualize_dm_graph())
