from pydantic import BaseModel, SecretStr, Field
from typing import Literal


class ServerConfigModel(BaseModel):
    api_key: SecretStr = Field(
        ...,
        description="LLM API key used to authenticate with the backend",
    )

    dm_roll_visibility: Literal["public", "hidden"] = Field(
        "public",
        description="Whether the DM's rolls are visible to players",
    )

    player_roll_mode: Literal[
        "physical",
        "digital",
        "auto",
        "hidden",
    ] = Field(
        "digital",
        description="How player dice rolls are handled",
    )

    character_sheet_mode: Literal["digital_sheet", "physical_sheet"] = Field(
        "digital_sheet",
        description="Whether players use digital or physical character sheets",
    )


class ServerConfig(ServerConfigModel):
    server_id: str = Field(
        ...,
        description="Unique identifier for the discord server",
    )
