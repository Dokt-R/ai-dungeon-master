import logging


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


def handle_error(error):
    """Centralized error handling function."""
    logging.error(f"An error occurred: {error}")
    raise error
