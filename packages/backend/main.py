from fastapi import FastAPI
from packages.backend.api.server_config import router as server_config_router

app = FastAPI(
    title="AI DM Backend API",
    version="1.0.0",
    description="API for managing campaigns, settings, and interacting with the AI Dungeon Master.",
)

app.include_router(server_config_router)
