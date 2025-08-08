# Database Schema

The SQLite database will contain the "Rules Library" of static SRD data.

```sql
CREATE TABLE Monsters (
    monster\_name TEXT PRIMARY KEY,
    armor\_class INTEGER NOT NULL,
    hit\_points TEXT NOT NULL,
    actions TEXT
);

CREATE TABLE Spells (
    spell\_name TEXT PRIMARY KEY,
    level INTEGER NOT NULL,
    description TEXT NOT NULL
);

-- Server and PlayerCharacters tables will also be in the SQLite DB
-- for structured, relational data.
```

