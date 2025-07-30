import pytest
from fastapi import HTTPException
from packages.shared.error_handler import handle_error, NotFoundError, ValidationError


def test_handle_error():
    with pytest.raises(HTTPException) as exc_info:
        handle_error(Exception("Test error"))
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Test error"


def test_not_found_error():
    with pytest.raises(NotFoundError):
        raise NotFoundError("Not found error occurred")


def test_validation_error():
    with pytest.raises(ValidationError):
        raise ValidationError("Validation error occurred")
