"""
API Request/Response Models
Pydantic BaseModels for request/response validation.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field as PydanticField, SecretStr


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


class CreateCharacterRequest(BaseModel):
    player_id: str = PydanticField(
        ..., min_length=3, max_length=64, pattern=r"^[\w\-]+$"
    )
    name: str = PydanticField(..., min_length=1, max_length=32, pattern=r"^[\w\- ]+$")
    races_index: str = PydanticField(..., min_length=1, max_length=32)
    class_index: str = PydanticField(..., min_length=1, max_length=32)
    subclass: str | None = None
    background_index: str = PydanticField(..., min_length=1, max_length=1024)
    strength: int = PydanticField(..., ge=1, le=30)
    dexterity: int = PydanticField(..., ge=1, le=30)
    constitution: int = PydanticField(..., ge=1, le=30)
    intelligence: int = PydanticField(..., ge=1, le=30)
    wisdom: int = PydanticField(..., ge=1, le=30)
    charisma: int = PydanticField(..., ge=1, le=30)
    proficiencies: List[str] = PydanticField(default=[])
    inventory: Optional[List[dict]] = PydanticField(default=[])


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
    character_name: Optional[str] = PydanticField(
        None, min_length=1, max_length=32, pattern=r"^[\w\- ]+$"
    )
    character_url: Optional[str] = None


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
    campaign_name: Optional[str] = PydanticField(
        default=None, min_length=1, max_length=64
    )
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
