"""
API Request/Response Models
Pydantic BaseModels for request/response validation.
"""

from typing import Literal, Optional

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
    species: str = PydanticField(..., min_length=1, max_length=32)
    class_index: str = PydanticField(..., min_length=1, max_length=32)
    subclass: str | None = None
    background: str = PydanticField(..., min_length=1, max_length=1024)
    strength: int = PydanticField(..., ge=1, le=30)
    dexterity: int = PydanticField(..., ge=1, le=30)
    constitution: int = PydanticField(..., ge=1, le=30)
    intelligence: int = PydanticField(..., ge=1, le=30)
    wisdom: int = PydanticField(..., ge=1, le=30)
    charisma: int = PydanticField(..., ge=1, le=30)
    prof_str_save: bool = PydanticField(default=False)
    prof_dex_save: bool = PydanticField(default=False)
    prof_con_save: bool = PydanticField(default=False)
    prof_int_save: bool = PydanticField(default=False)
    prof_wis_save: bool = PydanticField(default=False)
    prof_cha_save: bool = PydanticField(default=False)
    prof_acrobatics: bool = PydanticField(default=False)
    prof_animal_handling: bool = PydanticField(default=False)
    prof_arcana: bool = PydanticField(default=False)
    prof_athletics: bool = PydanticField(default=False)
    prof_deception: bool = PydanticField(default=False)
    prof_history: bool = PydanticField(default=False)
    prof_insight: bool = PydanticField(default=False)
    prof_intimidation: bool = PydanticField(default=False)
    prof_investigation: bool = PydanticField(default=False)
    prof_medicine: bool = PydanticField(default=False)
    prof_nature: bool = PydanticField(default=False)
    prof_perception: bool = PydanticField(default=False)
    prof_performance: bool = PydanticField(default=False)
    prof_persuasion: bool = PydanticField(default=False)
    prof_religion: bool = PydanticField(default=False)
    prof_sleight_of_hand: bool = PydanticField(default=False)
    prof_stealth: bool = PydanticField(default=False)
    prof_survival: bool = PydanticField(default=False)


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
