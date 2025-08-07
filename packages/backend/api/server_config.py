import os
from fastapi import APIRouter, Path
from packages.shared.models import ServerConfigModel, ServerConfig
from packages.shared.error_handler import (
    ValidationError,
    fastapi_error_handler,
)
from packages.backend.components.server_settings_manager import ServerSettingsManager

router = APIRouter()

# This should be replaced with a proper dependency injection system
settings_manager = ServerSettingsManager()


@router.put(
    "/servers/{server_id}/config", summary="Create or Update Server Configuration"
)
@fastapi_error_handler
def set_server_config(
    server_id: str = Path(..., description="The Discord server ID"),
    config: ServerConfigModel = ...,
):
    """
    Sets the configuration for a given server.
    The incoming data is a Pydantic `ServerConfigModel`.
    This is then used to create a `ServerConfig` SQLModel for the database.
    """
    # The manager now handles the validation, but we can keep this for early exit
    if not config.api_key.get_secret_value().strip():
        raise ValidationError("API key is required and must be a non-empty string.")

    # Create the database model from the API model
    server_config_db = ServerConfig(
        server_id=server_id,
        api_key=config.api_key,
        dm_roll_visibility=config.dm_roll_visibility,
        player_roll_mode=config.player_roll_mode,
        character_sheet_mode=config.character_sheet_mode,
    )

    settings_manager.store_server_config(server_config_db)
    return {"message": "Server configuration updated successfully."}
