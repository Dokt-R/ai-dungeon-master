from typing import Final

API_PREFIX: Final = "/api/v1"


class Routes:
    def __init__(self, prefix: str = API_PREFIX):
        self.prefix = prefix.rstrip("/")

    # Server Config
    def server_config(self, server_id: str) -> str:
        return f"{self.prefix}/servers/{server_id}/config"

    # Campaigns
    def campaign_base(self) -> str:
        return f"{self.prefix}/campaigns"

    def campaign_create(self) -> str:
        return f"{self.campaign_base()}/create"

    def campaign_delete(self) -> str:
        return f"{self.campaign_base()}/delete"

    def campaign_details(self, server_id: str, campaign_name: str) -> str:
        return f"{self.campaign_base()}/{server_id}/{campaign_name}"

    def campaign_players(self, campaign_id: int) -> str:
        return f"{self.campaign_base()}/{campaign_id}/players"

    def campaign_state_update(self, campaign_id: int) -> str:
        return f"{self.campaign_base()}/{campaign_id}/state"

    def campaign_action(self, campaign_id: int) -> str:
        return f"{self.campaign_base()}/{campaign_id}/action"

    # Characters
    def character_base(self) -> str:
        return f"{self.prefix}/characters"

    def character_info(self, character_id: str) -> str:
        return f"{self.character_base()}{character_id}"

    def character_add(self) -> str:
        return f"{self.character_base()}/add"

    def character_update(self) -> str:
        return f"{self.character_base()}/update"

    def character_remove(self) -> str:
        return f"{self.character_base()}/remove"

    def character_list(self) -> str:
        return f"{self.character_base()}/list"

    # Players
    def player_base(self) -> str:
        return f"{self.prefix}/players"

    def player_create(self) -> str:
        return f"{self.player_base()}/create"

    def player_join_campaign(self) -> str:
        return f"{self.player_base()}/join_campaign"

    def player_continue_campaign(self) -> str:
        return f"{self.player_base()}/continue_campaign"

    def player_end_campaign(self) -> str:
        return f"{self.player_base()}/end_campaign"

    def player_remove_campaign(self) -> str:
        return f"{self.player_base()}/remove_campaign"

    def player_status(self, player_id: str) -> str:
        return f"{self.player_base()}/status/{player_id}"

    # Health endpoints
    def health_ai(self) -> str:
        return f"{self.prefix}/health/ai"

    def health_observability(self) -> str:
        return f"{self.prefix}/health/observability"

    def health_general(self) -> str:
        return f"{self.prefix}/health/general"

    def health_observability_test_trace(self) -> str:
        return f"{self.prefix}/health/observability/test-trace"

    # Action endpoints
    def action(self) -> str:
        return f"{self.prefix}/action"

    def action_test(self) -> str:
        return f"{self.prefix}/action/test"

    # Utility endpoints
    def utility_llm_test(self) -> str:
        return f"{self.prefix}/utility/llm-test"

    # Voice endpoints
    def voice_status(self) -> str:
        return f"{self.prefix}/voice/status"

    def voice_session_create(self, session_id: str) -> str:
        return f"{self.prefix}/voice/session/{session_id}/create"

    def voice_session_source(self, session_id: str) -> str:
        return f"{self.prefix}/voice/session/{session_id}/source"

    def voice_session_source_position(self, session_id: str, source_id: str) -> str:
        return f"{self.prefix}/voice/session/{session_id}/source/{source_id}/position"

    def voice_session_focus(self, session_id: str) -> str:
        return f"{self.prefix}/voice/session/{session_id}/focus"

    def voice_session_stats(self, session_id: str) -> str:
        return f"{self.prefix}/voice/session/{session_id}/stats"

    def voice_session_cleanup(self, session_id: str) -> str:
        return f"{self.prefix}/voice/session/{session_id}"

    def voice_conversation_summary(self, conversation_id: str) -> str:
        return f"{self.prefix}/voice/conversation/{conversation_id}/summary"

    def voice_health(self) -> str:
        return f"{self.prefix}/voice/health"


ROUTES = Routes()
