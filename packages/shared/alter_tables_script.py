# recreate_table.py
from datetime import datetime

import your_models_module as models  # import where Player is defined
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine, select

DB_URL = "sqlite:///./db.sqlite"
engine = create_engine(DB_URL)

# 1) read existing rows
with engine.connect() as conn:
    rows = list(conn.execute(text("SELECT * FROM players")))
    col_names = [c[0] for c in conn.execute(text("PRAGMA table_info(players)"))]  # sqlite; for PG use inspector

# convert rows to dicts
rows_dicts = [dict(zip(col_names, r)) for r in rows]

# 2) rename old table (safer than drop)
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE players RENAME TO players_old"))

# 3) recreate schema
SQLModel.metadata.create_all(engine)

# 4) reinsert — map only columns that exist in new model
with Session(engine) as session:
    for r in rows_dicts:
        # prepare new row dict — keep old fields you still have, and set defaults for new columns
        new_row = {
            "player_id": r["player_id"],
            "username": r.get("username"),
            # new fields:
            "bio": r.get("bio", None),
            "last_seen": r.get("last_seen", None),
            # ... add others if necessary
        }
        session.execute(models.Player.__table__.insert().values(**new_row))
    session.commit()

print("Recreated table and reinserted rows. Old data in players_old.")
