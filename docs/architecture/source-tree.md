# Source Tree

The project will use a monorepo structure that separates the reusable campaign modules from the dynamic campaign saves.

```plaintext
/ai-dm-project/
├── data/
│   ├── modules/
│   │   └── [module_name]/
│   │       └── lore/
│   ├── saves/
│   │   └── [campaign_save_id]/
│   │       ├── chronicle.yaml
│   │       ├── parties/
│   │       │   └── [party_name]/
│   │       └── player_characters.yaml
│   └── srd_database.sqlite
├── packages/
|    └── backend/
|        ├── __init__.py
|        ├── main.py          # FastAPI application entrypoint
|        ├── api/             # API endpoint definitions (routers)
|        ├── components/      # Our high-level service components (CampaignMemoryService, etc.)
|        ├── core/            # Core logic, e.g., security
|        ├── agents/          # <-- For defining our AI agent personas & LangGraph graphs
|        │   ├── __init__.py
|        │   └── dm_graph.py
|        └── tools/             # <-- For our deterministic rule functions (e.g., dice rolls)
|            ├── __init__.py
|            └── dice_tools.py
└── docs/
```

