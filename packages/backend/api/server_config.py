from fastapi import APIRouter, HTTPException, Path
from packages.shared.models import ServerConfig, ServerConfigRequest
from packages.backend.api_key_service import APIKeyService
import os

router = APIRouter()

# Initialize services (should be refactored for DI in production)
from packages.backend.server_settings_manager import ServerSettingsManager

settings_manager = ServerSettingsManager(
    db_path=os.getenv("SERVER_SETTINGS_DB", "server_settings.db")
)
api_key_service = APIKeyService(memory_service=settings_manager)


@router.put(
    "/servers/{server_id}/config", summary="Create or Update Server Configuration"
)
def set_server_config(
    server_id: str = Path(..., description="The Discord server ID"),
    config: ServerConfigRequest = ...,
):
    try:
        server_config = ServerConfig(
            server_id=server_id,
            api_key=config.api_key,
            dm_roll_visibility=config.dm_roll_visibility,
            player_roll_mode=config.player_roll_mode,
            character_sheet_mode=config.character_sheet_mode,
        )
        api_key_service.store_api_key(server_config)
        return {"message": "Server configuration updated successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update server config: {str(e)}"
        )
