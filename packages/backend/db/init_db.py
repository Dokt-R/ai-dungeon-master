from packages.backend.db.schema.campaigns import create_campaigns_table
from packages.backend.db.schema.campaign_autosaves import (
    create_campaign_autosaves_table,
)
from packages.backend.db.schema.campaign_players import create_campaign_players_table
from packages.backend.db.schema.characters import create_characters_table
from packages.backend.db.schema.keys import create_keys_table
from packages.backend.db.schema.players import create_players_table


def initialize_schema(conn):
    create_campaigns_table(conn)
    create_campaign_autosaves_table(conn)
    create_campaign_players_table(conn)
    create_characters_table(conn)
    create_keys_table(conn)
    create_players_table(conn)
    conn.commit()
