from fastapi import FastAPI
from contextlib import asynccontextmanager

from packages.backend.api.server_api import router as server_config_router
from packages.backend.api.campaign_api import router as campaign_router
from packages.backend.api.player_api import router as player_router
from packages.backend.api.character_api import router as character_router
from packages.shared.db import get_engine, initialize_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    print("Initializing database...")
    engine = get_engine()
    initialize_schema(engine)
    print("Database initialized.")
    yield
    # On shutdown
    print("Application shutdown.")


app = FastAPI(
    title="AI DM Backend API",
    version="1.0.0",
    description="API for managing campaigns, settings, and interacting with the AI Dungeon Master.",
    lifespan=lifespan,
)

app.include_router(server_config_router)
app.include_router(campaign_router)
app.include_router(player_router)
app.include_router(character_router)
