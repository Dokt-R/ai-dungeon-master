"""
Thin async API client for AI Dungeon Master backend.
Provides centralized error handling and response parsing.
"""

from typing import Any, Dict, List, Optional

import httpx
from langsmith import traceable

from packages.shared.correlation import get_correlation_id
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import (
    CustomException,
)
from packages.shared.logging_config import configure_logging, get_logger
from packages.shared.models import (
    AddCharacterRequest,
    CreateCharacterRequest,
    ListCharactersRequest,
    RemoveCharacterRequest,
    ServerConfigModel,
    UpdateCharacterRequest,
)
from packages.shared.routes import ROUTES

configure_logging(level="INFO", log_to_file=True, path="logs/api_client.log")

# Create logger instance
logger = get_logger(__name__)


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # Store limits for testing purposes
        self.limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        self.client = httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, limits=self.limits
        )

    # ---------------------------
    # Async context manager support
    # ---------------------------

    def __enter__(self):
        raise RuntimeError(
            "ApiClient is async; use `async with ApiClient(...)` instead"
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        # included to follow context manager protocol
        return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # ---------------------------
    # Low level request helpers
    # ---------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """Internal request that attaches correlation id and returns httpx.Response."""
        headers = dict(headers or {})
        cid = get_correlation_id()  # read CID from contextvar
        if cid:
            headers["X-Correlation-ID"] = cid

        response = await self.client.request(method, path, headers=headers, **kwargs)
        return response

    async def close(self):
        """Close the HTTP client and cleanup resources."""
        await self.client.aclose()

    # ---------------------------
    # Centralized response handling
    # ---------------------------

    async def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Centralized response handling with error parsing.
        Maps backend errors to custom exceptions using the existing error system.
        """
        if response.status_code < 300:
            try:
                json_data = response.json()
                # Log successful response for debugging
                logger.debug(
                    "api_response_success",
                    status_code=response.status_code,
                    response_keys=list(json_data.keys())
                    if isinstance(json_data, dict)
                    else "not_dict",
                )
                return json_data
            except Exception as e:
                logger.error(
                    "api_response_json_parse_error",
                    status_code=response.status_code,
                    error=str(e),
                    response_text=response.text[:200],  # First 200 chars
                )
                return {}

        # Parse error response
        try:
            data = response.json()
            error_info = data.get("error", {})
            error_code = error_info.get(
                "error_code", "UNKNOWN"
            )  # Backend uses 'error_code', not 'code'
            details = error_info.get("details", {})
        except Exception:
            # If we can't parse the error response, create a generic error
            error_code = ErrorCode.UNKNOWN
            details = {
                "status_code": response.status_code,
                "response_text": response.text,
            }

        # Convert string error codes to ErrorCode enum if needed
        if isinstance(error_code, str):
            try:
                error_code = ErrorCode(error_code)
            except ValueError:
                # If the error code doesn't exist in our enum, use UNKNOWN
                error_code = ErrorCode.UNKNOWN
                details["original_error_code"] = error_code

        # Use the existing exception system which handles error code mapping
        raise CustomException(error_code, details=details)

    async def _handle_ai_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Specialized response handler for AI action responses.
        Provides better error handling and fallback responses for AI interactions.
        """
        if response.status_code < 300:
            try:
                data = response.json()
                # Ensure we have the required fields for AI responses
                if not data.get("narrative"):
                    data["narrative"] = "The DM is thinking... Please try again."
                if not data.get("status"):
                    data["status"] = "success"

                logger.debug(
                    "ai_response_success",
                    status_code=response.status_code,
                    narrative_length=len(data.get("narrative", "")),
                    status=data.get("status"),
                )
                return data
            except Exception as e:
                logger.error(
                    "ai_response_parse_error",
                    status_code=response.status_code,
                    error=str(e),
                    response_text=response.text[:200],
                )
                # If we can't parse a successful response, return a fallback
                return {
                    "narrative": "The DM encountered an issue processing your request. Please try again.",
                    "status": "error",
                    "error": f"Response parsing failed: {str(e)}",
                }

        # Handle error responses with AI-specific fallbacks
        try:
            data = response.json()
            error_info = data.get("error", {})
            error_message = error_info.get("message", "Unknown error occurred")

            logger.warning(
                "ai_response_error",
                status_code=response.status_code,
                error_code=error_info.get("error_code", "UNKNOWN"),
                error_message=error_message,
            )

            # Return a user-friendly error response instead of raising an exception
            return {
                "narrative": f"The DM encountered an issue: {error_message}. Please try again.",
                "status": "error",
                "error": error_message,
                "error_code": error_info.get("error_code", "UNKNOWN"),
            }
        except Exception as e:
            logger.error(
                "ai_response_error_parse_failed",
                status_code=response.status_code,
                error=str(e),
                response_text=response.text[:200],
            )
            # If we can't parse the error response, return a generic fallback
            return {
                "narrative": "The DM is currently unavailable. Please try again in a moment.",
                "status": "error",
                "error": f"HTTP {response.status_code}: Unable to process request",
                "error_code": "CONNECTION_ERROR",
            }

    # ---------------------------
    # Server Config
    # ---------------------------

    async def set_server_config(
        self, server_id: str, config: ServerConfigModel
    ) -> Dict[str, Any]:
        """Set server configuration."""
        url = f"/api/v1/servers/{server_id}/config"
        resp = await self._request(
            "PUT",
            url,
            json=config.model_dump() if hasattr(config, "model_dump") else config,
        )
        return await self._handle_response(resp)

    # ---------------------------
    # Campaign Management
    # ---------------------------

    async def create_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new campaign."""
        url = "/api/v1/campaigns/create"
        resp = await self._request("POST", url, json=data)
        return await self._handle_response(resp)

    async def delete_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Delete an existing campaign."""
        url = "/api/v1/campaigns/delete"
        resp = await self._request("DELETE", url, json=data)
        return await self._handle_response(resp)

    async def get_campaign_details(
        self, server_id: str, campaign_name: str
    ) -> Dict[str, Any]:
        """Get details for a specific campaign."""
        url = f"/api/v1/campaigns/{server_id}/{campaign_name}"
        resp = await self._request("GET", url)
        return await self._handle_response(resp)

    async def get_campaign_players(self, campaign_id: int) -> List[Dict[str, Any]]:
        """Get all players in a campaign."""
        url = f"/api/v1/campaigns/{campaign_id}/players"
        resp = await self._request("GET", url)
        handle_resp = await self._handle_response(resp)
        return [handle_resp]

    async def update_campaign_state(
        self, campaign_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update campaign state."""
        url = f"/api/v1/campaigns/{campaign_id}/state"
        resp = await self._request("PUT", url, json=data)
        return await self._handle_response(resp)

    async def submit_campaign_action(
        self, campaign_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit an action to a campaign."""
        url = f"/api/v1/campaigns/{campaign_id}/action"
        resp = await self._request("POST", url, json=data)
        return await self._handle_response(resp)

    # ---------------------------
    # Character Management
    # ---------------------------

    async def get_character_info(self, character_id: str) -> Dict[str, Any]:
        """Get information about a specific character."""
        url = f"/api/v1/characters/{character_id}"
        resp = await self._request("GET", url)
        return await self._handle_response(resp)

    async def add_character(self, req: AddCharacterRequest) -> Dict[str, Any]:
        """Add a new character."""
        url = "/api/v1/characters/add"
        resp = await self._request("POST", url, json=req.model_dump())
        return await self._handle_response(resp)

    async def create_character(self, req: CreateCharacterRequest) -> Dict[str, Any]:
        """Create a new character."""
        url = "/api/v1/characters/create"
        resp = await self._request("POST", url, json=req.model_dump())
        return await self._handle_response(resp)

    async def update_character(self, req: UpdateCharacterRequest) -> Dict[str, Any]:
        """Update an existing character."""
        url = "/api/v1/characters/update"
        resp = await self._request("POST", url, json=req.model_dump())
        return await self._handle_response(resp)

    async def remove_character(self, req: RemoveCharacterRequest) -> Dict[str, Any]:
        """Remove a character."""
        url = "/api/v1/characters/remove"
        resp = await self._request("POST", url, json=req.model_dump())
        return await self._handle_response(resp)

    async def list_characters(self, req: ListCharactersRequest) -> Dict[str, Any]:
        """List all characters for a player."""
        url = "/api/v1/characters/list"
        resp = await self._request("POST", url, json=req.model_dump())
        return await self._handle_response(resp)

    # ---------------------------
    # Player Management
    # ---------------------------

    async def join_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Join a campaign as a player."""
        url = "/api/v1/players/join_campaign"
        resp = await self._request("POST", url, json=data)
        return await self._handle_response(resp)

    async def end_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """End a campaign session."""
        url = "/api/v1/players/end_campaign"
        resp = await self._request("POST", url, json=data)
        return await self._handle_response(resp)

    async def remove_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove a player from a campaign."""
        url = "/api/v1/players/remove_campaign"
        resp = await self._request("POST", url, json=data)
        return await self._handle_response(resp)

    async def get_player_status(self, player_id: str) -> Dict[str, Any]:
        """Get the current status of a player."""
        url = f"/api/v1/players/status/{player_id}"
        resp = await self._request("GET", url)
        return await self._handle_response(resp)

    async def continue_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Continue a player's last active campaign."""
        url = "/api/v1/players/continue_campaign"
        resp = await self._request("POST", url, json=data)
        return await self._handle_response(resp)

    async def create_player(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new player."""
        url = "/api/v1/players/create"
        resp = await self._request("POST", url, json=data)
        return await self._handle_response(resp)

    # --------------------------- Action API Methods ---------------------------

    async def submit_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a player action to the AI DM."""
        url = ROUTES.action()
        resp = await self._request("POST", url, json=action_data)
        return await self._handle_ai_response(resp)

    async def test_action_endpoint(self) -> Dict[str, Any]:
        """Test the action API endpoint."""
        url = ROUTES.action_test()
        resp = await self._request("GET", url)
        return await self._handle_response(resp)

    # --------------------------- Voice API Methods ---------------------------

    async def get_voice_status(self) -> Dict[str, Any]:
        """Get the status of all voice features."""
        url = ROUTES.voice_status()
        resp = await self._request("GET", url)
        return await self._handle_response(resp)

    async def create_voice_session(
        self, session_id: str, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new voice session with specified configuration."""
        url = ROUTES.voice_session_create(session_id)
        resp = await self._request("POST", url, json=config or {})
        return await self._handle_response(resp)

    async def add_audio_source(
        self, session_id: str, source_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add an audio source to a voice session."""
        url = ROUTES.voice_session_source(session_id)
        resp = await self._request("POST", url, json=source_config)
        return await self._handle_response(resp)

    async def update_audio_source_position(
        self, session_id: str, source_id: str, position: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update the spatial position of an audio source."""
        url = ROUTES.voice_session_source_position(session_id, source_id)
        resp = await self._request("PUT", url, json=position)
        return await self._handle_response(resp)

    async def set_focus_mode(
        self, session_id: str, focus_speaker: Optional[str] = None, enable: bool = True
    ) -> Dict[str, Any]:
        """Enable or disable focus mode for a session."""
        url = ROUTES.voice_session_focus(session_id)
        data = {"focus_speaker": focus_speaker, "enable": enable}
        resp = await self._request("PUT", url, json=data)
        return await self._handle_response(resp)

    async def get_voice_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a voice session."""
        url = ROUTES.voice_session_stats(session_id)
        resp = await self._request("GET", url)
        return await self._handle_response(resp)

    async def cleanup_voice_session(self, session_id: str) -> Dict[str, Any]:
        """Clean up a voice session and all associated resources."""
        url = ROUTES.voice_session_cleanup(session_id)
        resp = await self._request("DELETE", url)
        return await self._handle_response(resp)

    async def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get a summary of conversation intelligence analysis."""
        url = ROUTES.voice_conversation_summary(conversation_id)
        resp = await self._request("GET", url)
        return await self._handle_response(resp)

    async def get_voice_health(self) -> Dict[str, Any]:
        """Get the health status of all voice system components."""
        url = ROUTES.voice_health()
        resp = await self._request("GET", url)
        return await self._handle_response(resp)

    # --------------------------- Utility API Methods ---------------------------
    @traceable
    async def test_llm(self, prompt: str) -> Dict[str, Any]:
        """Test LLM with a simple prompt with detailed timing."""
        import time

        start_time = time.perf_counter()
        logger.debug(
            "api_client_llm_test_started",
            prompt_length=len(prompt),
            base_url=self.base_url,
        )

        try:
            # Stage 1: Prepare request
            request_start = time.perf_counter()
            url = ROUTES.utility_llm_test()
            request_data = {"prompt": prompt}
            request_prep_time = (time.perf_counter() - request_start) * 1000

            logger.debug(
                "api_client_request_prepared",
                url=url,
                request_prep_time_ms=round(request_prep_time, 2),
            )

            # Stage 2: HTTP request
            http_start = time.perf_counter()
            resp = await self._request("POST", url, json=request_data)
            http_time = (time.perf_counter() - http_start) * 1000

            logger.debug(
                "api_client_http_completed",
                status_code=resp.status_code,
                http_time_ms=round(http_time, 2),
            )

            # Stage 3: Response handling
            response_start = time.perf_counter()
            result = await self._handle_response(resp)
            response_time = (time.perf_counter() - response_start) * 1000

            total_time = (time.perf_counter() - start_time) * 1000

            logger.info(
                "api_client_llm_test_completed",
                prompt_length=len(prompt),
                response_length=len(result.get("response", "")),
                request_prep_time_ms=round(request_prep_time, 2),
                http_time_ms=round(http_time, 2),
                response_time_ms=round(response_time, 2),
                total_time_ms=round(total_time, 2),
                status=result.get("status", "unknown"),
            )

            # Add timing metadata to response
            if isinstance(result, dict):
                result.setdefault("timing", {}).update(
                    {
                        "api_client_total_ms": round(total_time, 2),
                        "request_prep_ms": round(request_prep_time, 2),
                        "http_request_ms": round(http_time, 2),
                        "response_processing_ms": round(response_time, 2),
                    }
                )

            return result

        except Exception as e:
            total_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                "api_client_llm_test_failed",
                prompt_length=len(prompt),
                total_time_ms=round(total_time, 2),
                error=str(e),
            )
            raise

    # --------------------------- Health API Methods ---------------------------

    async def get_ai_health(self) -> Dict[str, Any]:
        """Get the comprehensive health status of the AI system."""
        url = ROUTES.health_ai()
        resp = await self._request("GET", url)
        return await self._handle_response(resp)

    async def get_observability_health(self) -> Dict[str, Any]:
        """Get the health status of the observability service."""
        url = ROUTES.health_observability()
        resp = await self._request("GET", url)
        return await self._handle_response(resp)

    async def get_general_health(self) -> Dict[str, Any]:
        """Get comprehensive application health status."""
        url = ROUTES.health_general()
        resp = await self._request("GET", url)
        return await self._handle_response(resp)

    async def test_observability_trace(self) -> Dict[str, Any]:
        """Test endpoint to validate observability tracing functionality."""
        url = ROUTES.health_observability_test_trace()
        resp = await self._request("POST", url)
        return await self._handle_response(resp)


# Example usage:
# import asyncio
# from packages.shared.models import AddCharacterRequest
#
# async def main():
#     async with ApiClient(base_url="http://localhost:8000") as client:
#         req = AddCharacterRequest(player_id="123", name="Warrior", character_url=None)
#         result = await client.add_character(req)
#         print(result)
#
# asyncio.run(main())
