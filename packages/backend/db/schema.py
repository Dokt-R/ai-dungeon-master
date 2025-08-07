from typing import Optional
from pydantic import SecretStr
from sqlmodel import Field, SQLModel


class ServerConfigBase(SQLModel):
    api_key: SecretStr
    dm_roll_visibility: str = "public"
    player_roll_mode: str = "digital"
    character_sheet_mode: str = "digital_sheet"


class ServerConfigDB(ServerConfigBase, table=True):
    __tablename__ = "keys"  # Explicitly name the table
    server_id: str = Field(default=None, primary_key=True)
