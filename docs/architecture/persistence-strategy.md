# Persistence Strategy

The application uses a four-tiered persistence strategy for different types of data:

1. **Structured World Data (The "Rules Library"):** Static SRD data (monster stats, spells) will be pre-loaded into the **SQLite database** for fast, reliable lookups by the `RulesEngine`.
2. **Long-Term Campaign Memory (The "Campaign Chronicle"):** The historical event log for each campaign will be stored in a **YAML file**, providing a human-readable record.
3. **Campaign Knowledge Base (The "Living Lore"):** Evolving, persistent world data (NPC traits, location details, party state) will be stored in a set of **YAML files** (`npcs.yaml`, `locations.yaml`, `player\_characters.yaml`, `party\_state.yaml`).
4. **Live Session/Encounter State (The "Scratchpad"):** Temporary, in-the-moment data (conversational context, combat tracker) will be managed by the **CrewAI framework's in-memory features** and temporary **JSON files**.
