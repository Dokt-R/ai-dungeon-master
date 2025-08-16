import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from packages.backend.api.campaign_api import router as campaign_router
from packages.backend.api.character_api import router as character_router
from packages.backend.api.player_api import router as player_router
from packages.backend.api.server_api import router as server_config_router
from packages.shared.db import get_async_engine, initialize_schema
from packages.shared.exceptions import CustomException

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    print("Initializing database...")
    engine = get_async_engine()
    await initialize_schema(engine)
    print("Database initialized.")
    yield
    # On shutdown
    await engine.dispose()
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


@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "error_code": exc.error_code.value if hasattr(exc.error_code, "value") else str(exc.error_code),
                "message": exc.message,
                "details": dict(exc.details),  # ensure it's JSON serializable
            }
        },
    )


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_exception_handler(
    request: Request, exc: PydanticValidationError
):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "error_code": "PYDANTIC_VALIDATION_ERROR",
                "message": "Validation failed",
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Our team has been notified.",
            }
        },
    )

