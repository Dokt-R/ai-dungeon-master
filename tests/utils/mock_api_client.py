"""
Mock API client for testing purposes.
Provides the same interface as ApiClient but with controllable responses.
"""

from typing import Any, Dict, List, Optional

from packages.shared.errors import ErrorCode
from packages.shared.exceptions import NotFoundError, ValidationError
from packages.shared.models import (
    AddCharacterRequest,
    ListCharactersRequest,
    RemoveCharacterRequest,
    ServerConfigModel,
    UpdateCharacterRequest,
)


class MockApiClient:
    """Mock API client that mimics the real ApiClient interface."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 10.0):
        self.base_url = base_url
        self.timeout = timeout

        # Mock data storage
        self.characters = {}
        self.campaigns = {}
        self.players = {}
        self.server_configs = {}

        # Response overrides for testing specific scenarios
        self.response_overrides = {}
        self.exception_overrides = {}

        # Call tracking
        self.call_history = []

    async def close(self):
        """Mock close method."""
        pass

    def set_response_override(self, method_name: str, response: Dict[str, Any]):
        """Set a specific response for a method call."""
        self.response_overrides[method_name] = response

    def set_exception_override(self, method_name: str, exception: Exception):
        """Set an exception to be raised for a method call."""
        self.exception_overrides[method_name] = exception

    def clear_overrides(self):
        """Clear all response and exception overrides."""
        self.response_overrides.clear()
        self.exception_overrides.clear()

    def _track_call(self, method_name: str, *args, **kwargs):
        """Track method calls for testing verification."""
        self.call_history.append(
            {"method": method_name, "args": args, "kwargs": kwargs}
        )

    def _check_overrides(self, method_name: str):
        """Check if there are any overrides for this method."""
        if method_name in self.exception_overrides:
            raise self.exception_overrides[method_name]
        if method_name in self.response_overrides:
            return self.response_overrides[method_name]
        return None

    # Server Config
    async def set_server_config(
        self, server_id: str, config: ServerConfigModel
    ) -> Dict[str, Any]:
        """Mock set server configuration."""
        self._track_call("set_server_config", server_id, config)
        override = self._check_overrides("set_server_config")
        if override is not None:
            return override

        self.server_configs[server_id] = config.model_dump()
        return {"message": "Server configuration updated successfully"}

    # Characters
    async def get_character_info(self, character_id: str) -> Dict[str, Any]:
        """Mock get character information."""
        self._track_call("get_character_info", character_id)
        override = self._check_overrides("get_character_info")
        if override is not None:
            return override

        if character_id not in self.characters:
            raise NotFoundError(ErrorCode.CHARACTER_NOT_FOUND)
        return self.characters[character_id]

    async def add_character(self, req: AddCharacterRequest) -> Dict[str, Any]:
        """Mock add character."""
        self._track_call("add_character", req)
        override = self._check_overrides("add_character")
        if override is not None:
            return override

        # Check for duplicate names
        for char in self.characters.values():
            if char["name"] == req.name and char["player_id"] == req.player_id:
                raise ValidationError(ErrorCode.DUPLICATE_CHARACTER, name=req.name)

        character_id = len(self.characters) + 1
        character_data = {
            "character_id": character_id,
            "name": req.name,
            "player_id": req.player_id,
            "character_url": req.character_url,
        }
        self.characters[str(character_id)] = character_data
        return character_data

    async def update_character(self, req: UpdateCharacterRequest) -> Dict[str, Any]:
        """Mock update character."""
        self._track_call("update_character", req)
        override = self._check_overrides("update_character")
        if override is not None:
            return override

        character_id = str(req.character_id)
        if character_id not in self.characters:
            raise NotFoundError(ErrorCode.CHARACTER_NOT_FOUND)

        character = self.characters[character_id]
        if req.name is not None:
            character["name"] = req.name
        if req.character_url is not None:
            character["character_url"] = req.character_url

        return character

    async def remove_character(self, req: RemoveCharacterRequest) -> Dict[str, Any]:
        """Mock remove character."""
        self._track_call("remove_character", req)
        override = self._check_overrides("remove_character")
        if override is not None:
            return override

        character_id = str(req.character_id)
        if character_id not in self.characters:
            raise NotFoundError(ErrorCode.CHARACTER_NOT_FOUND)

        del self.characters[character_id]
        return {"message": "Character removed successfully"}

    async def list_characters(self, req: ListCharactersRequest) -> Dict[str, Any]:
        """Mock list characters."""
        self._track_call("list_characters", req)
        override = self._check_overrides("list_characters")
        if override is not None:
            return override

        player_characters = [
            char
            for char in self.characters.values()
            if char["player_id"] == req.player_id
        ]
        return {"characters": player_characters}

    # Campaigns
    async def create_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock create campaign."""
        self._track_call("create_campaign", data)
        override = self._check_overrides("create_campaign")
        if override is not None:
            return override

        campaign_id = len(self.campaigns) + 1
        campaign_data = {"campaign_id": campaign_id, **data}
        self.campaigns[campaign_id] = campaign_data
        return campaign_data

    async def delete_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock delete campaign."""
        self._track_call("delete_campaign", data)
        override = self._check_overrides("delete_campaign")
        if override is not None:
            return override

        return {"message": "Campaign deleted successfully"}

    async def get_campaign_details(
        self, server_id: str, campaign_name: str
    ) -> Dict[str, Any]:
        """Mock get campaign details."""
        self._track_call("get_campaign_details", server_id, campaign_name)
        override = self._check_overrides("get_campaign_details")
        if override is not None:
            return override

        # Find campaign by server_id and name
        for campaign in self.campaigns.values():
            if (
                campaign.get("server_id") == server_id
                and campaign.get("campaign_name") == campaign_name
            ):
                return campaign
        raise NotFoundError(ErrorCode.CAMPAIGN_NOT_FOUND, campaign=campaign_name)

    async def get_campaign_players(self, campaign_id: int) -> List[Dict[str, Any]]:
        """Mock get campaign players."""
        self._track_call("get_campaign_players", campaign_id)
        override = self._check_overrides("get_campaign_players")
        if override is not None:
            return override

        return []  # Return empty list for mock

    async def update_campaign_state(
        self, campaign_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock update campaign state."""
        self._track_call("update_campaign_state", campaign_id, data)
        override = self._check_overrides("update_campaign_state")
        if override is not None:
            return override

        return {"message": "Campaign state updated successfully"}

    async def submit_campaign_action(
        self, campaign_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock submit campaign action."""
        self._track_call("submit_campaign_action", campaign_id, data)
        override = self._check_overrides("submit_campaign_action")
        if override is not None:
            return override

        return {"message": "Action submitted successfully"}

    # Players
    async def join_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock join campaign."""
        self._track_call("join_campaign", data)
        override = self._check_overrides("join_campaign")
        if override is not None:
            return override

        return {"message": "Joined campaign successfully"}

    async def end_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock end campaign."""
        self._track_call("end_campaign", data)
        override = self._check_overrides("end_campaign")
        if override is not None:
            return override

        return {"message": "Campaign ended successfully"}

    async def remove_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock remove campaign."""
        self._track_call("remove_campaign", data)
        override = self._check_overrides("remove_campaign")
        if override is not None:
            return override

        return {"message": "Removed from campaign successfully"}

    async def continue_campaign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock continue campaign."""
        self._track_call("continue_campaign", data)
        override = self._check_overrides("continue_campaign")
        if override is not None:
            return override

        return {"message": "Campaign continued successfully"}

    async def get_player_status(self, player_id: str) -> Dict[str, Any]:
        """Mock get player status."""
        self._track_call("get_player_status", player_id)
        override = self._check_overrides("get_player_status")
        if override is not None:
            return override

        return {"player_id": player_id, "status": "cmd", "last_active_campaign": None}

    async def create_player(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock create player."""
        self._track_call("create_player", data)
        override = self._check_overrides("create_player")
        if override is not None:
            return override

        # Create or update player (Discord IDs are unique)
        player_id = data.get("player_id")
        player_data = {
            "player_id": player_id,
            "username": data.get("username"),
            "status": "cmd",
        }
        self.players[player_id] = player_data
        return player_data

    # Health endpoints
    async def get_ai_health(self) -> Dict[str, Any]:
        """Mock get AI health."""
        self._track_call("get_ai_health")
        override = self._check_overrides("get_ai_health")
        if override is not None:
            return override

        return {
            "status": "healthy",
            "provider": "openai",
            "model": "gpt-5-nano",
            "traced": True,
            "timestamp": "2025-08-24T20:30:00Z",
        }

    async def get_observability_health(self) -> Dict[str, Any]:
        """Mock get observability health."""
        self._track_call("get_observability_health")
        override = self._check_overrides("get_observability_health")
        if override is not None:
            return override

        return {
            "status": "healthy",
            "provider": "langsmith",
            "project": "ai-dungeon-master",
        }

    async def get_general_health(self) -> Dict[str, Any]:
        """Mock get general health."""
        self._track_call("get_general_health")
        override = self._check_overrides("get_general_health")
        if override is not None:
            return override

        return {
            "status": "healthy",
            "service": "ai-dungeon-master-backend",
            "version": "1.0.0",
            "components": {
                "observability": {"status": "healthy"},
                "ai_client": {"status": "healthy"},
            },
            "timestamp": "2025-08-24T20:30:00Z",
        }

    async def test_observability_trace(self) -> Dict[str, Any]:
        """Mock test observability trace."""
        self._track_call("test_observability_trace")
        override = self._check_overrides("test_observability_trace")
        if override is not None:
            return override

        return {
            "status": "success",
            "message": "Observability trace test completed",
            "trace_id": "test-trace-123",
            "test_data": {
                "operations": ["validate_config", "initialize_client", "send_trace"]
            },
        }

    # Action endpoints
    async def submit_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock submit action."""
        self._track_call("submit_action", action_data)
        override = self._check_overrides("submit_action")
        if override is not None:
            return override

        return {
            "narrative": "The DM responds with a narrative continuation based on your action.",
            "session_id": action_data.get("session_id", "test-session"),
            "metadata": action_data.get("metadata", {}),
            "processing_time": 0.5,
            "status": "success",
            "correlation_id": "test-cid-123",
        }

    async def test_action_endpoint(self) -> Dict[str, Any]:
        """Mock test action endpoint."""
        self._track_call("test_action_endpoint")
        override = self._check_overrides("test_action_endpoint")
        if override is not None:
            return override

        return {
            "status": "success",
            "message": "Action API is operational",
            "endpoint": "/api/action",
            "test_endpoint": "/api/action/test",
        }

    # Voice endpoints
    async def get_voice_status(self) -> Dict[str, Any]:
        """Mock get voice status."""
        self._track_call("get_voice_status")
        override = self._check_overrides("get_voice_status")
        if override is not None:
            return override

        return {
            "speaker_identification": {"enabled": True, "status": "active"},
            "advanced_vad": {"enabled": False, "status": "not_available"},
            "audio_mixing": {"enabled": True, "status": "active"},
            "conversation_intelligence": {"enabled": True, "status": "active"},
            "multi_user_conversation": {"enabled": False, "status": "not_available"},
        }

    async def create_voice_session(
        self, session_id: str, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Mock create voice session."""
        self._track_call("create_voice_session", session_id, config)
        override = self._check_overrides("create_voice_session")
        if override is not None:
            return override

        return {"session_id": session_id, "status": "created"}

    async def add_audio_source(
        self, session_id: str, source_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock add audio source."""
        self._track_call("add_audio_source", session_id, source_config)
        override = self._check_overrides("add_audio_source")
        if override is not None:
            return override

        return {"status": "source_added", "source_id": source_config.get("source_id")}

    async def update_audio_source_position(
        self, session_id: str, source_id: str, position: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock update audio source position."""
        self._track_call(
            "update_audio_source_position", session_id, source_id, position
        )
        override = self._check_overrides("update_audio_source_position")
        if override is not None:
            return override

        return {"status": "position_updated"}

    async def set_focus_mode(
        self, session_id: str, focus_speaker: Optional[str] = None, enable: bool = True
    ) -> Dict[str, Any]:
        """Mock set focus mode."""
        self._track_call("set_focus_mode", session_id, focus_speaker, enable)
        override = self._check_overrides("set_focus_mode")
        if override is not None:
            return override

        mode = "enabled" if enable else "disabled"
        return {"status": f"focus_mode_{mode}", "focus_speaker": focus_speaker}

    async def get_voice_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Mock get voice session stats."""
        self._track_call("get_voice_session_stats", session_id)
        override = self._check_overrides("get_voice_session_stats")
        if override is not None:
            return override

        return {
            "audio_mixing": {
                "active_sources": 2,
                "master_volume": 1.0,
                "focus_mode": True,
                "focus_speaker": "user123",
            }
        }

    async def cleanup_voice_session(self, session_id: str) -> Dict[str, Any]:
        """Mock cleanup voice session."""
        self._track_call("cleanup_voice_session", session_id)
        override = self._check_overrides("cleanup_voice_session")
        if override is not None:
            return override

        return {
            "session_id": session_id,
            "status": "cleaned",
            "services": {
                "audio_mixing": "cleaned",
                "multi_user_conversation": "cleaned",
                "conversation_intelligence": "cleaned",
            },
        }

    async def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Mock get conversation summary."""
        self._track_call("get_conversation_summary", conversation_id)
        override = self._check_overrides("get_conversation_summary")
        if override is not None:
            return override

        return {
            "conversation_id": conversation_id,
            "summary": "This is a mock conversation summary.",
            "participants": ["user1", "user2"],
            "duration": 300,
            "topics": ["adventure", "combat"],
        }

    async def get_voice_health(self) -> Dict[str, Any]:
        """Mock get voice health."""
        self._track_call("get_voice_health")
        override = self._check_overrides("get_voice_health")
        if override is not None:
            return override

        return {
            "overall_status": "healthy",
            "services": {
                "speaker_identification": {"status": "healthy", "available": True},
                "advanced_vad": {"status": "not_available", "available": False},
                "audio_mixing": {"status": "healthy", "available": True},
                "conversation_intelligence": {"status": "healthy", "available": True},
                "multi_user_conversation": {
                    "status": "not_available",
                    "available": False,
                },
            },
        }

    # Context manager support
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
