from fastapi import FastAPI
from packages.backend.api.server_config import router as server_config_router
from packages.backend.api.campaign_api import router as campaign_router
from packages.backend.api.player_api import router as player_router
from packages.backend.api.character_api import router as character_router


app = FastAPI(
    title="AI DM Backend API",
    version="1.0.0",
    description="API for managing campaigns, settings, and interacting with the AI Dungeon Master.",
)

app.include_router(server_config_router)
app.include_router(campaign_router)
app.include_router(player_router)
app.include_router(character_router)
