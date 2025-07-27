import pytest


from error_handler import handle_error, NotFoundError, ValidationError


def test_handle_error():
    with pytest.raises(Exception) as exc_info:
        handle_error(Exception("Test error"))
    assert str(exc_info.value) == "Test error"


def test_not_found_error():
    with pytest.raises(NotFoundError):
        raise NotFoundError("Not found error occurred")


def test_validation_error():
    with pytest.raises(ValidationError):
        raise ValidationError("Validation error occurred")