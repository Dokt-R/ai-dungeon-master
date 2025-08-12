import logging
from unittest.mock import patch, MagicMock
from fastapi import Request
from fastapi.responses import JSONResponse
from packages.shared.error_handler import handle_error

def test_handle_api_error():
    # Arrange
    mock_request = MagicMock(spec=Request)
    exception = Exception("Test error")

    # Act
    with patch('logging.error') as mock_logging_error:
        response = handle_error(mock_request, exception)

    # Assert
    assert isinstance(response, JSONResponse)
    assert response.status_code == 500
    assert response.body == b'{"detail":"An unexpected error occurred. Please try again later."}'
    mock_logging_error.assert_called_once_with(
        f"API Error: {exception} on request {mock_request.method} {mock_request.url}",
        exc_info=exception
    )