from pydantic_settings import BaseSettings, SettingsConfigDict
from packages.shared.models import ServerConfig, SecretStr  # noqa: F401


class ServerConfig(ServerConfig, BaseSettings):
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
        },
    )
