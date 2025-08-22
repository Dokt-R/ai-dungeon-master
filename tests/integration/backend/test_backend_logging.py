import uuid
from unittest.mock import patch

import structlog
from fastapi.testclient import TestClient

from packages.backend.main import app

client = TestClient(app)


def test_correlation_id_middleware():
    with patch.object(
        uuid, "uuid4", return_value=uuid.UUID("12345678123456781234567812345678")
    ):
        response = client.get("/")
        assert response.status_code == 404
        assert (
            response.headers["X-Correlation-ID"]
            == "12345678-1234-5678-1234-567812345678"
        )


def test_correlation_id_in_logs():
    with patch.object(
        uuid, "uuid4", return_value=uuid.UUID("12345678123456781234567812345678")
    ):
        with structlog.testing.capture_logs() as cap_logs:
            client.get("/nonexistent-route")

            print("caplog", cap_logs)
            # Verify correlation ID is present in all logs
            for log in cap_logs:
                print("log", log)
                print(
                    log.get("correlation_id") == "12345678-1234-5678-1234-567812345678"
                )
                assert (
                    log.get("correlation_id") == "12345678-1234-5678-1234-567812345678"
                )

            # Verify at least one log contains the 404 status
            assert any("404" in log.get("event", "") for log in cap_logs)
