import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from packages.backend.api.action_api import router as action_router
from packages.backend.api.campaign_api import router as campaign_router
from packages.backend.api.character_api import router as character_router
from packages.backend.api.health_api import router as health_router
from packages.backend.api.player_api import router as player_router
from packages.backend.api.server_api import router as server_config_router
from packages.backend.api.voice_api import router as voice_router
from packages.backend.components.ai_client import ai_client
from packages.backend.components.multi_user_conversation_manager import (
    multi_user_conversation_manager,
)
from packages.backend.components.observability_service import observability_service
from packages.backend.components.speaker_identification_service import (
    speaker_identification_service,
)
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

    # Initialize observability service
    print("Initializing observability service...")
    observability_initialized = observability_service.initialize()
    if observability_initialized:
        print("Observability service initialized successfully.")
    else:
        print(
            "WARNING: Observability service failed to initialize. Continuing without observability."
        )

    # Initialize AI client
    print("Initializing AI client...")
    try:
        ai_initialized = await ai_client.initialize()
        if ai_initialized:
            print("AI client initialized successfully.")
        else:
            print(
                "WARNING: AI client failed to initialize. Continuing without AI services."
            )
    except Exception as e:
        print(
            f"WARNING: AI client initialization error: {str(e)}. Continuing without AI services."
        )

    # Initialize advanced voice services (optional)
    import os

    # Check environment variables for enabling advanced voice features
    enable_speaker_id = (
        os.getenv("ENABLE_SPEAKER_IDENTIFICATION", "false").lower() == "true"
    )
    enable_advanced_vad = os.getenv("ENABLE_ADVANCED_VAD", "false").lower() == "true"
    enable_audio_mixing = os.getenv("ENABLE_AUDIO_MIXING", "false").lower() == "true"
    enable_conversation_intelligence = (
        os.getenv("ENABLE_CONVERSATION_INTELLIGENCE", "false").lower() == "true"
    )

    # Initialize speaker identification service
    if enable_speaker_id:
        print("Initializing speaker identification service...")
        try:
            speaker_initialized = speaker_identification_service.initialize()
            if speaker_initialized:
                print("Speaker identification service initialized successfully.")
            else:
                print("WARNING: Speaker identification service failed to initialize.")
        except Exception as e:
            print(f"WARNING: Speaker identification initialization error: {str(e)}.")

    # Initialize advanced VAD processor
    if enable_advanced_vad:
        print("Initializing advanced VAD processor...")
        try:
            # Advanced VAD is ready to use (no special initialization needed)
            print("Advanced VAD processor initialized successfully.")
        except Exception as e:
            print(f"WARNING: Advanced VAD initialization error: {str(e)}.")

    # Initialize audio mixer service
    if enable_audio_mixing:
        print("Initializing audio mixer service...")
        try:
            # Audio mixer is ready to use (no special initialization needed)
            print("Audio mixer service initialized successfully.")
        except Exception as e:
            print(f"WARNING: Audio mixer initialization error: {str(e)}.")

    # Initialize conversation intelligence engine
    if enable_conversation_intelligence:
        print("Initializing conversation intelligence engine...")
        try:
            # Conversation intelligence is ready to use (no special initialization needed)
            print("Conversation intelligence engine initialized successfully.")
        except Exception as e:
            print(f"WARNING: Conversation intelligence initialization error: {str(e)}.")

    # Initialize multi-user conversation manager (depends on other services)
    enable_multi_user_conversation = (
        os.getenv("ENABLE_MULTI_USER_CONVERSATION", "false").lower() == "true"
    )
    if enable_multi_user_conversation:
        print("Initializing multi-user conversation manager...")
        try:
            conversation_initialized = multi_user_conversation_manager.initialize()
            if conversation_initialized:
                print("Multi-user conversation manager initialized successfully.")
            else:
                print("WARNING: Multi-user conversation manager failed to initialize.")
        except Exception as e:
            print(
                f"WARNING: Multi-user conversation manager initialization error: {str(e)}."
            )

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
        response = JSONResponse(
            {"detail": f"internal server error: {str(exc)}"}, status_code=500
        )
    finally:
        response.headers["X-Correlation-ID"] = cid
        clear_correlation_id()
    logger.info("request_finished", status_code=response.status_code)
    return response


app.include_router(server_config_router, prefix=API_PREFIX)
app.include_router(campaign_router, prefix=API_PREFIX)
app.include_router(player_router, prefix=API_PREFIX)
app.include_router(character_router, prefix=API_PREFIX)
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(action_router, prefix=API_PREFIX)
app.include_router(voice_router, prefix=API_PREFIX)


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
                "details": exc.errors(),
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
                "details": str(exc),  # Or nothing for security
            }
        },
    )
