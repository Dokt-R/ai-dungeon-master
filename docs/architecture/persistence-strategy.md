# Persistence Strategy

The application uses a **five-tiered persistence strategy** to efficiently manage different types of data, including the new SRD infrastructure:

## Tier 1: SRD Rules Library (SQLite Database)
All static, structured data from the D&D 5.1 SRD (monster stats, spell descriptions, weapon properties, etc.) is stored in a dedicated **SQLite database** with compliance tracking:

- **Tables**: `monsters`, `spells`, `weapons`, `data_migrations`, `data_versions`, `database_metadata`
- **Features**: Full OGL 1.0a compliance tracking, source verification, audit trails
- **Performance**: Optimized with indexes for <100ms query response times
- **Backup**: Automated backup procedures with rollback capabilities
- **Components**: Accessed via `SRDDatabaseManager`, `RulesEngine`, and `SRDComplianceService`

## Tier 2: Structured World Data
Static, structured data for campaigns (server settings, player characters, etc.) continues to be stored in **SQLite database** with proper relational design:

- **Tables**: Server configurations, player data, character sheets
- **Purpose**: Centralized storage for application state
- **Integration**: Seamless integration with SRD database

## Tier 3: Long-Term Campaign Memory (Campaign Chronicle)
The historical, append-only log of events for a single campaign playthrough is stored in structured **YAML files**:

- **Files**: `data/saves/[campaign_id]/chronicle.yaml`
- **Content**: Complete campaign history with timestamps
- **Purpose**: Human-readable campaign narrative archive

## Tier 4: Campaign Knowledge Base (Living Lore)
The evolving, persistent state of the world (NPC relationships, updated location descriptions, party knowledge) is stored in **YAML files**:

- **Files**: `npcs.yaml`, `locations.yaml`, `party_state.yaml`, `player_characters.yaml`
- **Location**: `data/saves/[campaign_id]/`
- **Purpose**: Dynamic world state that changes during gameplay

## Tier 5: Live Session State (AI Scratchpad)
The temporary, in-the-moment state of conversations or combat encounters is managed directly within **LangGraph's state object**:

- **Purpose**: Most efficient for AI's working memory
- **Scope**: Current session/encounter only
- **Persistence**: None - ephemeral by design

## SRD Integration Points

The SRD Rules Library (Tier 1) integrates with all other tiers:

- **RulesEngine** provides deterministic access to SRD data for AI decision making
- **SRD Tool Service** enables LangGraph tools for AI agent queries
- **AI Validation Service** uses SRD data to validate AI response accuracy
- **Audit Service** tracks all SRD data access and modifications
- **Migration Service** handles SRD database updates and versioning

## Data Flow Architecture

```
User Query → AI Agent → LangGraph Tools → RulesEngine → SRD Database
                                      ↓
AI Response ← AI Validation ← SRD Verification ← Audit Logging
```

## Performance Characteristics

- **SRD Queries**: <100ms response time with caching
- **AI Validation**: <500ms per response validation
- **Data Import**: Batch processing with progress tracking
- **Backup Operations**: Automated with minimal performance impact
- **Audit Logging**: Async logging with minimal latency impact

## Backup and Recovery

- **SRD Database**: Automated backups with rollback capabilities
- **Campaign Data**: Version control with YAML file history
- **Configuration**: Regular backups of server settings
- **Recovery**: Point-in-time recovery for all data tiers

This five-tiered strategy ensures optimal performance, data integrity, and compliance while maintaining the flexibility needed for a dynamic AI Dungeon Master system.