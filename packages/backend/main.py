from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from packages.shared.error_handler import ValidationError, NotFoundError, AIAPIError
from pydantic import ValidationError as PydanticValidationError
from contextlib import asynccontextmanager

from packages.backend.api.server_api import router as server_config_router
from packages.backend.api.campaign_api import router as campaign_router
from packages.backend.api.player_api import router as player_router
from packages.backend.api.character_api import router as character_router
from packages.shared.db import get_engine, initialize_schema

import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


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


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": exc.error_code or "VALIDATION_ERROR",
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(NotFoundError)
async def not_found_exception_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": exc.error_code or "NOT_FOUND",
                "message": exc.message,
                "details": exc.details,
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
                "code": "PYDANTIC_VALIDATION_ERROR",
                "message": "Validation failed",
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(AIAPIError)
async def ai_api_exception_handler(request: Request, exc: AIAPIError):
    return JSONResponse(
        status_code=502,  # Bad Gateway - indicates problem with upstream service
        content={
            "error": {
                "code": exc.error_code or "AI_API_ERROR",
                "message": exc.message,
                "details": exc.details,
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
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Our team has been notified.",
            }
        },
    )
