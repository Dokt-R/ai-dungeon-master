from pydantic import BaseModel, SecretStr, Field
from typing import Literal


class ServerConfig(BaseModel):
    server_id: str = Field(..., description="The Discord server ID")
    api_key: SecretStr
    dm_roll_visibility: Literal["public", "hidden"] = "public"
    player_roll_mode: Literal["public", "private", "dm_only"] = "public"
    character_sheet_mode: Literal["digital_sheet", "physical_sheet"] = "digital_sheet"


class ServerConfigRequest(BaseModel):
    api_key: SecretStr
    dm_roll_visibility: Literal["public", "hidden"] = "public"
    player_roll_mode: Literal["public", "private", "dm_only"] = "public"
    character_sheet_mode: Literal["digital_sheet", "physical_sheet"] = "digital_sheet"
