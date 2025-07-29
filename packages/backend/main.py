from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, SecretStr
from typing import Literal
from packages.backend.api_key_service import APIKeyService
from packages.backend.server_config import ServerConfig
from packages.backend.server_settings_manager import ServerSettingsManager
import os

app = FastAPI(
    title="AI DM Backend API",
    version="1.0.0",
    description="API for managing campaigns, settings, and interacting with the AI Dungeon Master."
)

# Initialize services
settings_manager = ServerSettingsManager(db_path=os.getenv("SERVER_SETTINGS_DB", "server_settings.db"))
api_key_service = APIKeyService(memory_service=settings_manager)

class ServerConfigRequest(BaseModel):
    api_key: SecretStr
    dm_roll_visibility: Literal["public", "hidden"] = "public"
    player_roll_mode: Literal["public", "private", "dm_only"] = "public"
    character_sheet_mode: Literal["digital_sheet", "physical_sheet"] = "digital_sheet"

@app.put("/servers/{server_id}/config", summary="Create or Update Server Configuration")
def set_server_config(
    server_id: str = Path(..., description="The Discord server ID"),
    config: ServerConfigRequest = ...
):
    try:
        # Store the API key securely
        server_config = ServerConfig(
            server_id=server_id,
            api_key=config.api_key,
            dm_roll_visibility=config.dm_roll_visibility,
            player_roll_mode=config.player_roll_mode,
            character_sheet_mode=config.character_sheet_mode
        )
        api_key_service.store_api_key(server_config)
        return {"message": "Server configuration updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update server config: {str(e)}")