import logging
from fastapi import HTTPException


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class CustomException(Exception):
    """Base class for custom exceptions."""

    pass


class NotFoundError(CustomException):
    """Exception raised for not found errors."""

    pass


class ValidationError(CustomException):
    """Exception raised for validation errors."""

    pass


def handle_error(error, context="fastapi"):
    """Centralized error handling function.
    context: "fastapi" (default) or "discord"
    """
    logging.error(f"An error occurred: {error}")
    if context == "fastapi":
        if isinstance(error, ValidationError):
            raise HTTPException(status_code=400, detail=str(error))
        if isinstance(error, NotFoundError):
            raise HTTPException(status_code=404, detail=str(error))
        # For all other errors, return 500
        raise HTTPException(status_code=500, detail=str(error))
    # For discord context, just log and do not raise


"""
Centralized Error Handler

Usage:
- In FastAPI endpoints, call handle_error(error, context="fastapi") in except blocks.
  - ValidationError -> HTTP 400
  - NotFoundError   -> HTTP 404
  - Other Exception -> HTTP 500
- In Discord command handlers, call handle_error(error, context="discord").
  - Only logs the error; does not raise.
  - Always send a user-facing message after calling handle_error.

Do NOT use handle_error in low-level service or database code; propagate exceptions up to the API or command handler layer.
"""
