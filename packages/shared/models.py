# from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field as PydanticField, SecretStr
from sqlalchemy import Column, String
from sqlalchemy.orm import Mapped
from sqlmodel import Field as SQLField, Relationship, SQLModel


# Server Configuration Model
class Server(SQLModel, table=True):
    __tablename__ = "keys"
    server_id: str = SQLField(primary_key=True)
    api_key: SecretStr = SQLField(sa_column=Column(String), default=None)
    dm_roll_visibility: str = SQLField(default="public")
    player_roll_mode: str = SQLField(default="digital")
    character_sheet_mode: str = SQLField(default="digital_sheet")

    campaigns: Mapped[List["Campaign"]] = Relationship(
        back_populates="server_api", sa_relationship_kwargs={"lazy": "selectin"}
    )


# Campaign-Player Link Table
class CampaignPlayerLink(SQLModel, table=True):
    __tablename__ = "campaign_players"
    campaign_id: int = SQLField(primary_key=True, foreign_key="campaigns.campaign_id")
    player_id: str = SQLField(primary_key=True, foreign_key="players.player_id")
    

# Player Model
class Player(SQLModel, table=True):
    __tablename__ = "players"
    player_id: str = SQLField(primary_key=True)
    username: Optional[str] = SQLField(default=None)
    player_status: str = SQLField(default="cmd")
    last_active_campaign: Optional[str] = SQLField(
        default=None, foreign_key="campaigns.campaign_name"
    )

    characters: Mapped[List["Character"]] = Relationship(
        back_populates="player", sa_relationship_kwargs={"lazy": "selectin"}
    )
    campaigns: Mapped[List["Campaign"]] = Relationship(
        back_populates="players",
        link_model=CampaignPlayerLink,
        sa_relationship_kwargs={"lazy": "selectin"}
    )


# Character Model
class Character(SQLModel, table=True):
    __tablename__ = "characters"
    character_id: Optional[int] = SQLField(default=None, primary_key=True)
    name: str = SQLField(...)
    character_url: Optional[str] = SQLField(default=None)

    player_id: str = SQLField(foreign_key="players.player_id")
    player: Mapped["Player"] = Relationship(
        back_populates="characters", sa_relationship_kwargs={"lazy": "selectin"}
    )

    campaign_id: Optional[int] = SQLField(
        default=None, foreign_key="campaigns.campaign_id"
    )
    campaign: Mapped["Campaign"] = Relationship(
        back_populates="characters", sa_relationship_kwargs={"lazy": "selectin"}
    )


# Campaign Model
class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"
    campaign_id: Optional[int] = SQLField(default=None, primary_key=True)
    campaign_name: str = SQLField(...)
    owner_id: str = SQLField(...)
    state: Optional[str] = SQLField(default=None)
    last_save: datetime = SQLField(default_factory=datetime.utcnow)

    server_id: str = SQLField(foreign_key="keys.server_id")
    server_api: Mapped["Server"] = Relationship(
        back_populates="campaigns", sa_relationship_kwargs={"lazy": "selectin"}
    )

    players: Mapped[List["Player"]] = Relationship(
        back_populates="campaigns",
        link_model=CampaignPlayerLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    characters: Mapped[List["Character"]] = Relationship(
        back_populates="campaign", sa_relationship_kwargs={"lazy": "selectin"}
    )


# ======================================================================================
# API Models (Pydantic BaseModels for request/response validation)
# ======================================================================================


class ServerConfigModel(BaseModel):
    api_key: SecretStr = PydanticField(
        ...,
        description="LLM API key used to authenticate with the backend",
        min_length=1,
    )
    dm_roll_visibility: Literal[
        "public",
        "hidden",
    ] = PydanticField(
        "public",
        description="Server wide settings handling DM dice roll visibility",
    )
    player_roll_mode: Literal[
        "physical",
        "digital",
        "auto",
        "hidden",
    ] = PydanticField(
        "digital",
        description="Per player preferences handling dice rolls",
    )
    character_sheet_mode: Literal[
        "digital_sheet",
        "physical_sheet",
    ] = PydanticField(
        "digital_sheet",
        description="Server wide settings handing digital or physical character sheets preference",
    )


class AddCharacterRequest(BaseModel):
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    name: str = PydanticField(..., min_length=1, max_length=32, pattern=r"^[\w\- ]+$")
    character_url: str | None = None


class UpdateCharacterRequest(BaseModel):
    character_id: int
    name: str | None = PydanticField(
        None, min_length=1, max_length=32, pattern=r"^[\w\- ]+$"
    )
    character_url: str | None = None


class RemoveCharacterRequest(BaseModel):
    character_id: int


class ListCharactersRequest(BaseModel):
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )


class CreatePlayerRequest(BaseModel):
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    username: str = PydanticField(
        ..., min_length=3, max_length=32, pattern=r"^[\w\- ]+$"
    )


class JoinCampaignRequest(BaseModel):
    server_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    campaign_name: str = PydanticField(..., min_length=1, max_length=64)
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    character_name: str = PydanticField(
        None, min_length=1, max_length=32, pattern=r"^[\w\- ]+$"
    )
    character_url: str = None


class ContinueCampaignRequest(BaseModel):
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    username: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )



class LeaveCampaignRequest(BaseModel):
    server_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    campaign_name: str = PydanticField(..., min_length=1, max_length=64)
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )


class CampaignCreateRequest(BaseModel):
    server_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    campaign_name: str = PydanticField(..., min_length=1, max_length=64)
    owner_id: str


class CampaignEndRequest(BaseModel):
    server_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    campaign_name: Optional[str] = PydanticField(default=None, min_length=1, max_length=64)
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )


class CampaignDeleteRequest(BaseModel):
    server_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    campaign_name: str = PydanticField(..., min_length=1, max_length=64)
    requester_id: str = PydanticField(
        ..., min_length=1, max_length=64, pattern=r"^[\w\-]+$"
    )
    is_admin: bool


class CampaignStateRequest(BaseModel):
    state: str


# ======================================================================================
# Enums used for as a single source of truth for field validations
# ======================================================================================

class DMVisibility(str, Enum):
    public = "public"
    hidden = "hidden"

class PlayerRollMode(str, Enum):
    physical = "physical"
    digital = "digital"
    auto = "auto"
    hidden = "hidden"

class CharacterSheetMode(str, Enum):
    digital_sheet = "digital_sheet"
    physical_sheet = "physical_sheet"
