from datetime import datetime
from typing import List, Optional, Literal
from pydantic import SecretStr, BaseModel, Field as PydanticField
from sqlalchemy import Column, String
from sqlmodel import Relationship, SQLModel, Field as SQLField


# Server Configuration Model
class Server(SQLModel, table=True):
    __tablename__ = "keys"
    server_id: str = SQLField(primary_key=True)
    api_key: SecretStr = SQLField(sa_column=Column(String), default=None)
    dm_roll_visibility: str = "public"
    player_roll_mode: str = "digital"
    character_sheet_mode: str = "digital_sheet"

    campaigns: List["Campaign"] = Relationship(back_populates="server_api")


# Player Model
class Player(SQLModel, table=True):
    __tablename__ = "players"
    player_id: str = SQLField(primary_key=True)
    username: Optional[str] = None
    player_status: Optional[str] = "cmd"
    last_active_campaign: Optional[str] = SQLField(
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
    character_id: Optional[int] = SQLField(default=None, primary_key=True)
    name: str
    character_url: Optional[str] = None

    player_id: str = SQLField(foreign_key="players.player_id")
    player: Player = Relationship(back_populates="characters")

    campaign_id: Optional[int] = SQLField(
        default=None, foreign_key="campaigns.campaign_id"
    )
    campaign: Optional["Campaign"] = Relationship(back_populates="characters")


# Campaign-Player Link Table
class CampaignPlayerLink(SQLModel, table=True):
    __tablename__ = "campaign_players"
    campaign_id: int = SQLField(primary_key=True, foreign_key="campaigns.campaign_id")
    player_id: str = SQLField(primary_key=True, foreign_key="players.player_id")


# Campaign Model
class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"
    campaign_id: Optional[int] = SQLField(default=None, primary_key=True)
    campaign_name: str
    owner_id: str
    state: Optional[str] = None
    last_save: datetime = SQLField(default_factory=datetime.utcnow)

    server_id: str = SQLField(foreign_key="keys.server_id")
    server_api: Server = Relationship(back_populates="campaigns")

    players: List[Player] = Relationship(
        back_populates="campaigns",
        sa_relationship_kwargs={"secondary": "campaign_players"},
    )
    characters: List[Character] = Relationship(back_populates="campaign")


# ======================================================================================
# API Models (Pydantic BaseModels for request/response validation)
# ======================================================================================


class ServerConfigModel(BaseModel):
    api_key: SecretStr = PydanticField(
        ...,
        description="LLM API key used to authenticate with the backend",
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
    campaign_name: str = PydanticField(..., min_length=1, max_length=64)
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
