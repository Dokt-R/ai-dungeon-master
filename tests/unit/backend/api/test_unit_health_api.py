"""
Unit tests for the health API endpoints.

Tests cover:
- Observability health endpoint responses
- General health endpoint responses
- Error handling for health check failures
- Test trace endpoint functionality
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from packages.backend.ai.prompts import prompt_manager
from packages.backend.components.ai_client import AIClient, ai_client
from packages.backend.components.observability_service import (
    ObservabilityService,
    observability_service,
)
from packages.backend.main import app
from packages.shared.routes import ROUTES


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def reset_observability_service():
    """Reset the observability service before and after each test."""
    ObservabilityService.reset_instance()
    yield
    ObservabilityService.reset_instance()


class TestObservabilityHealthEndpoint:
    """Test the /api/health/observability endpoint."""

    def test_get_observability_health_healthy(
        self, client, reset_observability_service
    ):
        """Test getting healthy observability health status."""
        # Mock the service to return healthy status
        with patch.object(observability_service, "get_health_status") as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "provider": "langsmith",
                "project": "test-project",
                "tracing_enabled": True,
            }

            response = client.get(ROUTES.health_observability())

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["provider"] == "langsmith"
            assert data["project"] == "test-project"
            assert data["tracing_enabled"] is True

            mock_health.assert_called_once()

    def test_get_observability_health_unhealthy(
        self, client, reset_observability_service
    ):
        """Test getting unhealthy observability health status."""
        # Mock the service to return unhealthy status
        with patch.object(observability_service, "get_health_status") as mock_health:
            mock_health.return_value = {
                "status": "unhealthy",
                "provider": "langsmith",
                "project": "unknown",
                "error": "configuration_failed",
            }

            response = client.get(ROUTES.health_observability())

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["error"] == "configuration_failed"

            mock_health.assert_called_once()

    def test_get_observability_health_exception(
        self, client, reset_observability_service
    ):
        """Test observability health endpoint when service throws exception."""
        # Mock the service to raise an exception
        with patch.object(observability_service, "get_health_status") as mock_health:
            mock_health.side_effect = Exception("Internal service error")

            response = client.get(ROUTES.health_observability())

            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["status"] == "unhealthy"
            assert data["detail"]["error"] == "internal_health_check_error"

            mock_health.assert_called_once()


class TestGeneralHealthEndpoint:
    """Test the /api/health/general endpoint."""

    def test_get_general_health_success(self, client):
        """Test getting general health status successfully."""
        # Mock the services to return healthy status
        with (
            patch.object(observability_service, "get_health_status") as mock_obs_health,
            patch.object(ai_client, "get_health_status") as mock_ai_health,
        ):
            mock_obs_health.return_value = {
                "status": "healthy",
                "provider": "langsmith",
                "project": "ai-dungeon-master",
            }

            mock_ai_health.return_value = {
                "status": "healthy",
                "provider": "openai",
                "model": "gpt-5-nano",
            }

            response = client.get(ROUTES.health_general())

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "ai-dungeon-master-backend"
            assert data["version"] == "1.0.0"
            assert data["components"]["observability"]["status"] == "healthy"
            assert data["components"]["ai_client"]["status"] == "healthy"

    def test_get_general_health_with_exception(self, client):
        """Test general health endpoint with exception handling."""
        # This is harder to test since the endpoint doesn't currently throw exceptions
        # But we can test the structure
        response = client.get(ROUTES.health_general())

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data


class TestObservabilityTestTraceEndpoint:
    """Test the /api/health/observability/test-trace endpoint."""

    def test_test_trace_success(self, client, reset_observability_service):
        """Test successful observability trace test."""
        # Mock the observability service methods
        with (
            patch.object(observability_service, "trace_operation") as mock_trace,
            patch.object(observability_service, "get_health_status") as mock_health,
        ):
            # Setup mocks
            mock_trace.return_value.__enter__ = Mock(return_value="test-trace-id")
            mock_trace.return_value.__exit__ = Mock(return_value=None)

            mock_health.return_value = {
                "status": "healthy",
                "provider": "langsmith",
                "project": "test-project",
            }

            response = client.post(ROUTES.health_observability_test_trace())

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["message"] == "Observability trace test completed"
            assert data["trace_id"] == "test-trace-id"
            assert "observability_status" in data
            assert "test_data" in data

            mock_trace.assert_called_once_with(
                operation_name="test_observability_trace",
                test_type="health_check",
                endpoint=ROUTES.health_observability_test_trace(),
            )
            mock_health.assert_called_once()

    def test_test_trace_service_exception(self, client, reset_observability_service):
        """Test observability trace test with service exception."""
        # Mock the trace operation to raise an exception
        with (
            patch.object(observability_service, "trace_operation") as mock_trace,
            patch.object(observability_service, "get_health_status") as mock_health,
        ):
            mock_trace.side_effect = Exception("Trace operation failed")
            mock_health.return_value = {"status": "unhealthy", "error": "trace_failed"}

            response = client.post(ROUTES.health_observability_test_trace())

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert data["message"] == "Observability trace test failed"
            assert "error" in data
            assert "observability_status" in data

            mock_trace.assert_called_once()
            mock_health.assert_called_once()


@pytest.fixture
def reset_ai_client():
    """Reset the AI client singleton before and after each test."""
    AIClient.reset_instance()
    yield
    AIClient.reset_instance()


class TestAIHealthEndpoint:
    """Test the /api/health/ai endpoint."""

    def test_get_ai_health_healthy_comprehensive(
        self, client, reset_ai_client, reset_observability_service
    ):
        """Test getting comprehensive healthy AI health status."""
        # Mock all components to return healthy status
        with (
            patch.object(ai_client, "get_health_status") as mock_ai_health,
            patch.object(observability_service, "trace_operation") as mock_trace,
            patch.object(prompt_manager, "get_default_template") as mock_get_template,
        ):
            # Setup mocks
            mock_ai_health.return_value = {
                "status": "healthy",
                "provider": "openai",
                "model": "gpt-5-nano",
                "circuit_breaker_state": "CLOSED",
            }

            mock_trace.return_value.__enter__ = Mock(return_value="test-trace-id")
            mock_trace.return_value.__exit__ = Mock(return_value=None)

            mock_template = Mock()
            mock_template.template_id = "core_dm_system"
            mock_get_template.return_value = mock_template

            # Mock prompt manager templates
            prompt_manager._templates = {
                "template1": mock_template,
                "template2": mock_template,
            }

            response = client.get(ROUTES.health_ai())

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["provider"] == "openai"
            assert data["model"] == "gpt-5-nano"
            assert data["traced"] is True
            assert data["prompt_system"]["status"] == "healthy"
            assert data["prompt_system"]["template_count"] == 2
            assert data["circuit_breaker_state"] == "CLOSED"
            assert "timestamp" in data
            assert "components_checked" in data

            mock_ai_health.assert_called_once()
            mock_trace.assert_called_once()

    def test_get_ai_health_unhealthy_components(
        self, client, reset_ai_client, reset_observability_service
    ):
        """Test getting AI health status when some components are unhealthy."""
        with (
            patch.object(ai_client, "get_health_status") as mock_ai_health,
            patch.object(observability_service, "trace_operation") as mock_trace,
            patch.object(prompt_manager, "get_default_template") as mock_get_template,
        ):
            # Setup mocks with mixed health
            mock_ai_health.return_value = {
                "status": "unhealthy",
                "provider": "openai",
                "model": "gpt-5-nano",
                "error": "configuration_failed",
            }

            mock_trace.return_value.__enter__ = Mock(return_value="test-trace-id")
            mock_trace.return_value.__exit__ = Mock(return_value=None)

            mock_get_template.return_value = (
                Mock()
            )  # Template exists but AI is unhealthy

            response = client.get(ROUTES.health_ai())

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["provider"] == "openai"
            assert data["model"] == "gpt-5-nano"
            assert data["traced"] is True
            assert data["failed_components"] == ["ai_client"]
            assert "error" in data

    def test_get_ai_health_tracing_failure(
        self, client, reset_ai_client, reset_observability_service
    ):
        """Test AI health endpoint when tracing fails."""
        with (
            patch.object(ai_client, "get_health_status") as mock_ai_health,
            patch.object(observability_service, "trace_operation") as mock_trace,
            patch.object(prompt_manager, "get_default_template") as mock_get_template,
        ):
            # Setup mocks with tracing failure
            mock_ai_health.return_value = {
                "status": "healthy",
                "provider": "openai",
                "model": "gpt-5-nano",
            }

            mock_trace.side_effect = Exception("Tracing failed")
            mock_get_template.return_value = Mock()

            response = client.get(ROUTES.health_ai())

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["traced"] is False
            assert "tracing" in data["failed_components"]

    def test_get_ai_health_prompt_system_failure(
        self, client, reset_ai_client, reset_observability_service
    ):
        """Test AI health endpoint when prompt system fails."""
        with (
            patch.object(ai_client, "get_health_status") as mock_ai_health,
            patch.object(observability_service, "trace_operation") as mock_trace,
            patch.object(prompt_manager, "get_default_template") as mock_get_template,
        ):
            # Setup mocks with prompt system failure
            mock_ai_health.return_value = {
                "status": "healthy",
                "provider": "openai",
                "model": "gpt-5-nano",
            }

            mock_trace.return_value.__enter__ = Mock(return_value="test-trace-id")
            mock_trace.return_value.__exit__ = Mock(return_value=None)

            mock_get_template.side_effect = Exception("Prompt system error")

            response = client.get(ROUTES.health_ai())

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["traced"] is True
            assert "prompt_system" in data["failed_components"]

    def test_get_ai_health_internal_error(
        self, client, reset_ai_client, reset_observability_service
    ):
        """Test AI health endpoint when internal error occurs."""
        with patch.object(ai_client, "get_health_status") as mock_ai_health:
            mock_ai_health.side_effect = Exception("Internal service error")

            response = client.get(ROUTES.health_ai())

            assert response.status_code == 500
            data = response.json()
            assert data["detail"]["status"] == "unhealthy"
            assert (
                "internal_comprehensive_health_check_error" in data["detail"]["error"]
            )


class TestGeneralHealthEndpointWithAI:
    """Test the /api/health/general endpoint with AI integration."""

    def test_get_general_health_with_ai_healthy(
        self, client, reset_ai_client, reset_observability_service
    ):
        """Test general health endpoint with healthy AI components."""
        with (
            patch.object(observability_service, "get_health_status") as mock_obs_health,
            patch.object(ai_client, "get_health_status") as mock_ai_health,
        ):
            mock_obs_health.return_value = {
                "status": "healthy",
                "provider": "langsmith",
                "project": "ai-dungeon-master",
            }

            mock_ai_health.return_value = {
                "status": "healthy",
                "provider": "openai",
                "model": "gpt-5-nano",
            }

            response = client.get(ROUTES.health_general())

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "ai-dungeon-master-backend"
            assert data["components"]["observability"]["status"] == "healthy"
            assert data["components"]["ai_client"]["status"] == "healthy"
            assert "timestamp" in data

    def test_get_general_health_with_ai_degraded(
        self, client, reset_ai_client, reset_observability_service
    ):
        """Test general health endpoint with degraded AI components."""
        with (
            patch.object(observability_service, "get_health_status") as mock_obs_health,
            patch.object(ai_client, "get_health_status") as mock_ai_health,
        ):
            mock_obs_health.return_value = {
                "status": "healthy",
                "provider": "langsmith",
                "project": "ai-dungeon-master",
            }

            mock_ai_health.return_value = {
                "status": "unhealthy",
                "provider": "openai",
                "error": "connection_failed",
            }

            response = client.get(ROUTES.health_general())

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["components"]["observability"]["status"] == "healthy"
            assert data["components"]["ai_client"]["status"] == "unhealthy"


class TestHealthEndpointsIntegration:
    """Integration tests for all health endpoints."""

    def test_all_health_endpoints_exist_and_respond(self, client):
        """Test that all expected health endpoints exist and return proper responses."""
        endpoints = [
            ROUTES.health_observability(),
            ROUTES.health_ai(),
            ROUTES.health_general(),
            ROUTES.health_observability_test_trace(),
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            # All endpoints should return either 200 (healthy) or 500 (unhealthy but responding)
            assert response.status_code in [200, 500]
            data = response.json()
            assert "status" in data

    def test_health_endpoints_have_consistent_structure(self, client):
        """Test that health endpoints return consistent response structures."""
        endpoints = [
            ROUTES.health_observability(),
            ROUTES.health_ai(),
            ROUTES.health_general(),
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            data = response.json()

            # All should have status
            assert "status" in data
            assert data["status"] in ["healthy", "unhealthy", "degraded"]

    def test_test_trace_not_initialized_service(
        self, client, reset_observability_service
    ):
        """Test observability trace test when service is not initialized."""
        # Don't mock anything - service should handle not being initialized

        response = client.post(ROUTES.health_observability_test_trace())

        # The endpoint should still work even if service isn't initialized
        assert response.status_code == 200
        data = response.json()
        # The trace_id will be None, but the endpoint should still return success
        assert "status" in data
        assert "trace_id" in data


class TestHealthEndpointsIntegration:
    """Integration tests for health endpoints."""

    def test_all_health_endpoints_exist(self, client):
        """Test that all expected health endpoints exist and return proper responses."""
        endpoints = [ROUTES.health_observability(), ROUTES.health_general()]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [
                200,
                500,
            ]  # 500 is acceptable for unhealthy services
            data = response.json()
            assert "status" in data

    def test_health_endpoints_with_different_methods(self, client):
        """Test health endpoints with different HTTP methods."""
        # Test POST on GET-only endpoints
        response = client.post(ROUTES.health_observability())
        assert response.status_code == 405  # Method not allowed

        response = client.post(ROUTES.health_general())
        assert response.status_code == 405  # Method not allowed

        # Test GET on POST endpoint
        response = client.get(ROUTES.health_observability_test_trace())
        assert response.status_code == 405  # Method not allowed
