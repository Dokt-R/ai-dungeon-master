from fastapi import APIRouter, HTTPException, Path
from packages.shared.models import ServerConfigModel, ServerConfig
from packages.backend.components.api_key_service import APIKeyService
from packages.shared.error_handler import handle_error, ValidationError, NotFoundError, fastapi_error_handler
import os

# Initialize services (should be refactored for DI in production)
from packages.backend.components.server_settings_manager import ServerSettingsManager


router = APIRouter()

settings_manager = ServerSettingsManager(
    db_path=os.getenv("SERVER_SETTINGS_DB", "server_settings.db")
)
api_key_service = APIKeyService(manager=settings_manager)


@router.put(
    "/servers/{server_id}/config", summary="Create or Update Server Configuration"
)
@fastapi_error_handler
def set_server_config(
    server_id: str = Path(..., description="The Discord server ID"),
    config: ServerConfigModel = ...,
):
    # Example validation: API key must be present and non-empty
    api_key_value = (
        config.api_key.get_secret_value()
        if hasattr(config.api_key, "get_secret_value")
        else config.api_key
    )
    if (
        not api_key_value
        or not isinstance(api_key_value, str)
        or len(api_key_value.strip()) == 0
    ):
        raise ValidationError("API key is required and must be a non-empty string.")

    server_config = ServerConfig(
        server_id=server_id,
        api_key=config.api_key,
        dm_roll_visibility=config.dm_roll_visibility,
        player_roll_mode=config.player_roll_mode,
        character_sheet_mode=config.character_sheet_mode,
    )
    api_key_service.store_api_key(server_config)
    return {"message": "Server configuration updated successfully."}
