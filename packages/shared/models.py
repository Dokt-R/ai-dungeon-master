from datetime import datetime
from typing import List, Optional

from pydantic import SecretStr
from sqlalchemy import Column, String
from sqlmodel import Field, Relationship, SQLModel


# Server Configuration Model
class ServerConfig(SQLModel, table=True):
    __tablename__ = "keys"
    server_id: str = Field(primary_key=True)
    api_key: SecretStr = Field(sa_column=Column(String), default=None)
    dm_roll_visibility: str = "public"
    player_roll_mode: str = "digital"
    character_sheet_mode: str = "digital_sheet"

    campaigns: List["Campaign"] = Relationship(back_populates="server_config")


# Player Model
class Player(SQLModel, table=True):
    __tablename__ = "players"
    user_id: str = Field(primary_key=True)
    username: Optional[str] = None
    player_status: Optional[str] = "cmd"
    last_active_campaign: Optional[str] = Field(
        default=None, foreign_key="campaigns.campaign_name"
    )

    characters: List["Character"] = Relationship(back_populates="player")
    campaigns: List["Campaign"] = Relationship(
        back_populates="players",
        sa_relationship_kwargs={"secondary": "campaign_players"},
    )


# Character Model
class Character(SQLModel, table=True):
    __tablename__ = "characters"
    character_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    character_url: Optional[str] = None

    player_id: str = Field(foreign_key="players.user_id")
    player: Player = Relationship(back_populates="characters")

    campaign_id: Optional[int] = Field(
        default=None, foreign_key="campaigns.campaign_id"
    )
    campaign: Optional["Campaign"] = Relationship(back_populates="characters")


# Campaign-Player Link Table
class CampaignPlayerLink(SQLModel, table=True):
    __tablename__ = "campaign_players"
    campaign_id: int = Field(primary_key=True, foreign_key="campaigns.campaign_id")
    player_id: str = Field(primary_key=True, foreign_key="players.user_id")


# Campaign Model
class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"
    campaign_id: Optional[int] = Field(default=None, primary_key=True)
    campaign_name: str
    owner_id: str
    state: Optional[str] = None
    last_save: datetime = Field(default_factory=datetime.utcnow)

    server_id: str = Field(foreign_key="keys.server_id")
    server_config: ServerConfig = Relationship(back_populates="campaigns")

    players: List[Player] = Relationship(
        back_populates="campaigns",
        sa_relationship_kwargs={"secondary": "campaign_players"},
    )
    characters: List[Character] = Relationship(back_populates="campaign")


# ======================================================================================
# API Models (Pydantic BaseModels for request/response validation)
# ======================================================================================

from pydantic import BaseModel, Field
from typing import Literal


class ServerConfigModel(BaseModel):
    api_key: SecretStr = Field(
        ...,
        description="LLM API key used to authenticate with the backend",
    )
    dm_roll_visibility: Literal[
        "public",
        "hidden",
    ] = Field(
        "public",
        description="Server wide settings handling DM dice roll visibility",
    )
    player_roll_mode: Literal[
        "physical",
        "digital",
        "auto",
        "hidden",
    ] = Field(
        "digital",
        description="Per player preferences handling dice rolls",
    )
    character_sheet_mode: Literal[
        "digital_sheet",
        "physical_sheet",
    ] = Field(
        "digital_sheet",
        description="Server wide settings handing digital or physical character sheets preference",
    )


class AddCharacterRequest(BaseModel):
    player_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")
    name: str = Field(..., min_length=1, max_length=32, pattern=r"^[\w\- ]+$")
    character_url: str | None = None


class UpdateCharacterRequest(BaseModel):
    character_id: int
    name: str | None = Field(None, min_length=1, max_length=32, pattern=r"^[\w\- ]+$")
    character_url: str | None = None


class RemoveCharacterRequest(BaseModel):
    character_id: int


class ListCharactersRequest(BaseModel):
    player_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")


class CreatePlayerRequest(BaseModel):
    user_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")
    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[\w\- ]+$")


class JoinCampaignRequest(BaseModel):
    server_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")
    campaign_name: str = Field(..., min_length=1, max_length=64)
    player_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")
    character_name: str = Field(
        None, min_length=1, max_length=32, pattern=r"^[\w\- ]+$"
    )
    character_url: str = None


class ContinueCampaignRequest(BaseModel):
    player_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")


class LeaveCampaignRequest(BaseModel):
    server_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")
    campaign_name: str = Field(..., min_length=1, max_length=64)
    player_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")
