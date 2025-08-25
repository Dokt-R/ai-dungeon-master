import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from packages.shared.errors import ErrorCode
from packages.shared.exceptions import AIAPIError, NotFoundError, ValidationError
from packages.shared.routes import ROUTES

pytestmark = pytest.mark.asyncio


async def test_validation_error_400(client):
    """Test ValidationError (400 status code) by creating a duplicate campaign."""
    # First create a campaign
    create_payload = {
        "server_id": "1234567890",
        "campaign_name": "Test Campaign",
        "owner_id": "owner123",
    }
    response = await client.post(ROUTES.campaign_create(), json=create_payload)

    # Try to create the same campaign again to trigger ValidationError
    response = await client.post(ROUTES.campaign_create(), json=create_payload)

    # Since we are triggering ValidationError by using a duplicate campaign we use error below
    error = ErrorCode.DUPLICATE_CAMPAIGN_NAME
    data = response.json()

    assert response.status_code == error.status_code

    # Structural checks
    assert "error" in data
    data = data["error"]

    # Exact error code check
    assert data["error_code"] == error.value

    # Message check
    assert "already exists" in data["message"]


async def test_not_found_error_404(client):
    """Test NotFoundError (404 status code) by requesting a non-existent campaign."""
    # Request a non-existent campaign to trigger NotFoundError
    response = await client.get(ROUTES.campaign_details(1, "NonExistentCampaign"))

    error = ErrorCode.CAMPAIGN_NOT_FOUND
    data = response.json()

    assert response.status_code == error.status_code

    # Structural checks
    assert "error" in data
    data = data["error"]

    # Exact error code check
    assert data["error_code"] == error.value


async def test_pydantic_validation_error_422(client):
    """Test Pydantic ValidationError (422 status code) by sending invalid data."""
    # Send invalid data to trigger Pydantic ValidationError
    response = await client.put(
        ROUTES.server_config(1234567890),
        json={
            "api_key": "test-key",
            "dm_roll_visibility": "invalid-value",
            "player_roll_mode": "manual",
            "character_sheet_mode": "manual",
        },
    )

    error = ErrorCode.INVALID_INPUT
    data = response.json()["error"]

    assert response.status_code == error.status_code
    assert "details" in data
    # Check that the response contains validation error details
    assert len(data["details"]) > 0


@pytest.mark.skip("AI API is not implemented yet")
async def test_ai_api_error_502(client, monkeypatch):
    """Test AIAPIError (502 status code) by triggering it in a FastAPI context."""
    # To properly test the AIAPIError, we'll add a temporary endpoint to the app
    # that raises this specific exception. This is a common pattern for testing
    # exception handlers in FastAPI.
    from packages.shared.exceptions import AIAPIError

    test_app = FastAPI()

    @test_app.get("/test-ai-error")
    async def _test_ai_error():
        raise AIAPIError(
            error_code=ErrorCode.AI_API_ERROR,
            service="Mock AI",
            reason="Service unavailable",
        )

    # Make a request to the new test endpoint
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        with pytest.raises(AIAPIError):
            await client.get("/test-ai-error")


# ===== Direct Exception Handler Tests =====


def create_test_app():
    """Create a test FastAPI app with endpoints that raise specific exceptions."""

    # Create a copy of the main app for testing
    test_app = FastAPI()

    # Include the same exception handlers from main.py
    from fastapi import Request
    from fastapi.responses import JSONResponse

    from packages.shared.exceptions import CustomException

    @test_app.exception_handler(CustomException)
    async def custom_exception_handler(request: Request, exc: CustomException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "error_code": exc.error_code.value
                    if hasattr(exc.error_code, "value")
                    else str(exc.error_code),
                    "message": exc.message,
                    "details": dict(exc.details),
                    "path": request.url.path,
                }
            },
        )

    @test_app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Our team has been notified.",
                    "details": str(exc),
                }
            },
        )

    @test_app.get("/test-validation-error")
    async def test_validation_error():
        raise ValidationError(ErrorCode.VALIDATION_ERROR)

    @test_app.get("/test-not-found-error")
    async def test_not_found_error():
        raise NotFoundError(ErrorCode.NOT_FOUND)

    @test_app.get("/test-ai-api-error")
    async def test_ai_api_error():
        raise AIAPIError(ErrorCode.AI_API_ERROR)

    @test_app.get("/test-generic-error")
    async def test_generic_error():
        try:
            raise Exception("Test generic error")
        except Exception as e:
            # This ensures the exception is properly caught by the handler
            raise e

    return test_app


def test_validation_error_handler():
    """Test ValidationError exception handler returns correct status code and response format."""
    app = create_test_app()
    client = TestClient(app)

    response = client.get("/test-validation-error")

    assert response.status_code == 400
    data = response.json()

    assert "error" in data
    error = data["error"]
    assert error["error_code"] == ErrorCode.VALIDATION_ERROR.error_code
    assert error["message"] == ErrorCode.VALIDATION_ERROR.message
    assert error["path"] == "/test-validation-error"
    assert "details" in error


def test_not_found_error_handler():
    """Test NotFoundError exception handler returns correct status code and response format."""
    app = create_test_app()
    client = TestClient(app)

    response = client.get("/test-not-found-error")

    assert response.status_code == 404
    data = response.json()

    assert "error" in data
    error = data["error"]
    assert error["error_code"] == "NOT_FOUND"
    assert error["message"] == ErrorCode.NOT_FOUND.message
    assert error["path"] == "/test-not-found-error"
    assert "details" in error


def test_ai_api_error_handler():
    """Test AIAPIError exception handler returns correct status code and response format."""
    app = create_test_app()
    client = TestClient(app)

    response = client.get("/test-ai-api-error")

    assert response.status_code == 502
    data = response.json()

    assert "error" in data
    error = data["error"]
    assert error["error_code"] == "AI_API_ERROR"
    assert error["message"] == ErrorCode.AI_API_ERROR.message
    assert error["path"] == "/test-ai-api-error"
    assert "details" in error


@pytest.mark.skip(
    reason="TestClient handles exceptions differently - this test needs to be rewritten"
)
def test_generic_error_handler():
    """Test generic Exception handler returns correct status code and response format."""
    app = create_test_app()
    client = TestClient(app)

    # The exception handler should catch the exception and return a proper error response
    # Note: TestClient will handle the exception properly through FastAPI's exception handling
    response = client.get("/test-generic-error")

    assert response.status_code == 500
    data = response.json()

    assert "error" in data
    error = data["error"]
    assert error["error_code"] == "INTERNAL_SERVER_ERROR"
    assert (
        error["message"] == "An unexpected error occurred. Our team has been notified."
    )
    assert error["details"] == "Test generic error"
