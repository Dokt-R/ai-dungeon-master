import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from packages.backend.api.campaign_api import router as campaign_router
from packages.backend.api.character_api import router as character_router
from packages.backend.api.player_api import router as player_router
from packages.backend.api.server_api import router as server_config_router
from packages.shared.correlation import (
    clear_correlation_id,
    set_correlation_id,
)
from packages.shared.db import get_async_engine, initialize_schema
from packages.shared.exceptions import CustomException
from packages.shared.logging_config import configure_logging, get_logger
from packages.shared.routes import API_PREFIX

load_dotenv()
configure_logging()

# Create logger instance
logger = get_logger(__name__)

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

# Add correlation ID middleware
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    incoming_cid = request.headers.get("X-Correlation-ID")
    # reuse incoming or generate new
    cid = incoming_cid or str(uuid.uuid4())
    set_correlation_id(cid)
    
    logger.info("request_started", path=request.url.path)

    try:
        # Add correlation ID to response headers
        response = await call_next(request)
    except Exception as exc:
        # ensure correlation header is present on error responses as well
        logger.exception("unhandled_exception")
        # create a JSON error response if an exception bubbles out
        response = JSONResponse({"detail": f"internal server error: {str(exc)}"}, status_code=500)
    finally:
        response.headers["X-Correlation-ID"] = cid
        clear_correlation_id()
    logger.info("request_finished", status_code=response.status_code)
    return response


app.include_router(server_config_router, prefix=API_PREFIX)
app.include_router(campaign_router, prefix=API_PREFIX)
app.include_router(player_router, prefix=API_PREFIX)
app.include_router(character_router, prefix=API_PREFIX)


@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    logger.error(f"Custom exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "error_code": exc.error_code.value
                if hasattr(exc.error_code, "value")
                else str(exc.error_code),
                "message": exc.message,
                "details": dict(exc.details),  # ensure it's JSON serializable
                "path": request.url.path,
            }
        },
    )


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_exception_handler(
    request: Request, exc: PydanticValidationError
):
    logger.error(f"Pydantic validation: {exc}", exc_info=True)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "error_code": "PYDANTIC_VALIDATION_ERROR",
                "message": "Validation failed",
                "details": dict(exc.errors()),
                "path": request.url.path,
            }
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Request validation: {exc}", exc_info=True)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "error_code": "REQUEST_VALIDATION_ERROR",
                "message": "Validation failed",
                "details": exc.errors(),
                "path": request.url.path,
            }
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Our team has been notified.",
                "details": str(exc), # Or nothing for security
            }
        },
    )
