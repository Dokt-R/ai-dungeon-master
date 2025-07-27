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
│   ├── bot/
│   ├── backend/
│   └── shared/
└── docs/
```
