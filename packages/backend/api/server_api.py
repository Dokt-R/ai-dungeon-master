from fastapi import APIRouter, Body, Depends, Path

from packages.backend.components.server_manager import ServerSettingsManager
from packages.shared.models import Server, ServerConfigModel

router = APIRouter()


@router.put(
    "/servers/{server_id}/config", summary="Create or Update Server Configuration"
)
async def set_server_config(
    server_id: str = Path(..., description="The Discord server ID"),
    config: ServerConfigModel = Body(...),
    settings_manager: ServerSettingsManager = Depends(),
):
    """
    Sets the configuration for a given server.
    The incoming data is a Pydantic `ServerConfigModel`.
    This is then used to create a `Server` SQLModel for the database.
    """
    # Create the database model from the API model
    server_config = Server(
        server_id=server_id,
        api_key=config.api_key,
        dm_roll_visibility=config.dm_roll_visibility,
        player_roll_mode=config.player_roll_mode,
        character_sheet_mode=config.character_sheet_mode,
    )
    await settings_manager.store_server_config(server_config)
    return {"message": "Server configuration updated successfully."}
