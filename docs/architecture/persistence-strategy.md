# Persistence Strategy

The application uses a four-tiered persistence strategy to efficiently manage different types of data:

1. **Structured World Data (The "Rules Library"):** All static, structured data from the D&D 5.1 SRD (monster stats, spell descriptions, item properties, etc.) will be pre-processed and loaded into the **SQLite database**. This serves as a fast, reliable library for our `Rules Engine`.
2. **Long-Term Campaign Memory (The "Campaign Chronicle"):** The historical, append-only log of events for a single campaign playthrough will be stored in a structured **YAML file**. This provides a human-readable record of the campaign's story.
3. **Campaign Knowledge Base (The "Living Lore"):** The evolving, persistent state of the world (e.g., NPC relationships, updated location descriptions, party knowledge) will be stored in a set of **YAML files** (`npcs.yaml`, `locations.yaml`, `party_state.yaml`, `player_characters.yaml`).
4. **Live Session/Encounter State (The "AI's Scratchpad"):** The temporary, in-the-moment state of a conversation or combat encounter will be managed directly within **LangGraph's state object**. This is the most efficient way to handle the AI's "working memory.".