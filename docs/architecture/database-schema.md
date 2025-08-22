# Database Schema

The SQLite database contains the comprehensive "Rules Library" of static D&D 5.1 SRD data with compliance tracking and audit capabilities.

## Core SRD Tables

### Monsters Table
```sql
CREATE TABLE monsters (
    monster_id INTEGER PRIMARY KEY AUTOINCREMENT,
    monster_name TEXT NOT NULL UNIQUE,
    armor_class INTEGER NOT NULL,
    hit_points TEXT NOT NULL,
    strength INTEGER NOT NULL,
    dexterity INTEGER NOT NULL,
    constitution INTEGER NOT NULL,
    intelligence INTEGER NOT NULL,
    wisdom INTEGER NOT NULL,
    charisma INTEGER NOT NULL,
    challenge_rating TEXT NOT NULL,
    actions TEXT,
    special_abilities TEXT,
    description TEXT,
    srd_compliance TEXT NOT NULL,
    data_source TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT 1
);
```

### Spells Table
```sql
CREATE TABLE spells (
    spell_id INTEGER PRIMARY KEY AUTOINCREMENT,
    spell_name TEXT NOT NULL UNIQUE,
    level INTEGER NOT NULL CHECK(level >= 0 AND level <= 9),
    school TEXT NOT NULL,
    casting_time TEXT NOT NULL,
    range TEXT NOT NULL,
    components TEXT NOT NULL,
    duration TEXT NOT NULL,
    description TEXT NOT NULL,
    at_higher_levels TEXT,
    classes TEXT NOT NULL,
    srd_compliance TEXT NOT NULL,
    data_source TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT 1
);
```

### Weapons Table
```sql
CREATE TABLE weapons (
    weapon_id INTEGER PRIMARY KEY AUTOINCREMENT,
    weapon_name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    cost TEXT NOT NULL,
    damage TEXT NOT NULL,
    weight TEXT NOT NULL,
    properties TEXT NOT NULL,
    description TEXT,
    srd_compliance TEXT NOT NULL,
    data_source TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT 1
);
```

## System Tables

### Data Migrations Table
```sql
CREATE TABLE data_migrations (
    migration_id TEXT PRIMARY KEY,
    migration_type TEXT NOT NULL,
    status TEXT NOT NULL,
    description TEXT NOT NULL,
    applied_at TEXT,
    rolled_back_at TEXT,
    checksum_before TEXT NOT NULL,
    checksum_after TEXT NOT NULL,
    changes_summary TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Data Versions Table
```sql
CREATE TABLE data_versions (
    version_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    data_version TEXT NOT NULL,
    compatibility TEXT NOT NULL,
    changes TEXT NOT NULL,
    migration_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Database Metadata Table
```sql
CREATE TABLE database_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## Indexes for Performance

```sql
-- Monster indexes
CREATE INDEX idx_monsters_name ON monsters(monster_name);
CREATE INDEX idx_monsters_cr ON monsters(challenge_rating);
CREATE INDEX idx_monsters_active ON monsters(is_active);

-- Spell indexes
CREATE INDEX idx_spells_name ON spells(spell_name);
CREATE INDEX idx_spells_level ON spells(level);
CREATE INDEX idx_spells_school ON spells(school);
CREATE INDEX idx_spells_active ON spells(is_active);

-- Weapon indexes
CREATE INDEX idx_weapons_name ON weapons(weapon_name);
CREATE INDEX idx_weapons_category ON weapons(category);
CREATE INDEX idx_weapons_active ON weapons(is_active);
```

## Integration with Existing Schema

The SRD tables integrate seamlessly with the existing application schema:

- **Server and PlayerCharacters tables** remain for structured, relational data
- **SRD tables** provide the deterministic rules library
- **Foreign key relationships** maintained through application logic
- **Unified data access** through the RulesEngine component

## Compliance Tracking

All SRD data includes:
- **srd_compliance**: JSON field with licensing verification details
- **data_source**: JSON field with source attribution and checksums
- **audit trail**: Complete history of data modifications and verifications
- **version tracking**: Schema and data version management

This schema ensures legal compliance, data integrity, and optimal query performance for the AI Dungeon Master system.

