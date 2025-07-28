from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class ServerConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    api_key: SecretStr = Field(
        ...,
        description="API key used to authenticate with the backend",
    )
    server_id: str = Field(
        ...,
        description="Unique identifier for the server",
    )
    dm_roll_visibility: Literal["public", "hidden"] = Field(
        "public",
        description="Whether the DM's rolls are visible to players",
    )
    player_roll_mode: Literal[
        "manual_physical_total",
        "manual_physical_raw",
        "manual_digital",
        "auto_visible",
        "auto_hidden",
    ] = Field(
        "manual_digital",
        description="How player dice rolls are handled",
    )
    character_sheet_mode: Literal["digital_sheet", "physical_sheet"] = Field(
        "digital_sheet",
        description="Whether players use digital or physical character sheets",
    )

    # Set which env vars to load per field:
    model_config = SettingsConfigDict(
        env_prefix="",  # Optional: disable default uppercase prefix
        env_file=".env",  # Optional: loads from .env file
        extra="ignore",
        env={
            "api_key": "API_KEY",
            "server_id": "SERVER_ID",
            "dm_roll_visibility": "DM_VISIBILITY",
            "player_roll_mode": "PLAYER_ROLL_MODE",
            "character_sheet_mode": "CHARACTER_SHEET_MODE",
        }
    )
