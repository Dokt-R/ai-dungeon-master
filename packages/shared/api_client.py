"""
Thin async API client for AI Dungeon Master backend.
Provides centralized error handling and response parsing.
"""

from typing import Any, Dict, List, Optional

import httpx

from packages.shared.correlation import get_correlation_id
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import (
    CustomException,
)
from packages.shared.models import (
    AddCharacterRequest,
    ListCharactersRequest,
    RemoveCharacterRequest,
    ServerConfigModel,
    UpdateCharacterRequest,
)
from packages.shared.routes import ROUTES


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
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
                return response.json()
            except Exception:
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
        return await self._handle_response(resp)

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
