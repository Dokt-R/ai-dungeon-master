# packages/shared/routes.py
from typing import Final

API_PREFIX: Final = "/api/v1"

class Routes:
    def __init__(self, prefix: str = API_PREFIX):
        self.prefix = prefix.rstrip("/")

    # Server Config
    def server_config(self, server_id: str) -> str:
        return f"{self.prefix}/servers/{server_id}/config"

    # Campaigns
    def campaigns_base(self) -> str:
        return f"{self.prefix}/campaigns"

    def campaign_create(self) -> str:
        return f"{self.campaigns_base()}/new"

    def campaign_delete(self) -> str:
        return f"{self.campaigns_base()}/delete"

    def campaign_details(self, server_id: str, campaign_name: str) -> str:
        return f"{self.campaigns_base()}/{server_id}/{campaign_name}"

    def campaign_players(self, campaign_id: int) -> str:
        return f"{self.campaigns_base()}/{campaign_id}/players"

    def campaign_state_update(self, campaign_id: int) -> str:
        return f"{self.campaigns_base()}/{campaign_id}/state"

    def campaign_action(self, campaign_id: int) -> str:
        return f"{self.campaigns_base()}/{campaign_id}/action"

    # Characters
    def characters_base(self) -> str:
        return f"{self.prefix}/characters"

    def character_info(self, character_id: str) -> str:
        return f"{self.characters_base()}{character_id}"

    def character_add(self) -> str:
        return f"{self.characters_base()}add"

    def character_update(self) -> str:
        return f"{self.characters_base()}update"

    def character_remove(self) -> str:
        return f"{self.characters_base()}remove"

    def character_list(self) -> str:
        return f"{self.characters_base()}list"

    # Players
    def players_base(self) -> str:
        return f"{self.prefix}/players"

    def players_join_campaign(self) -> str:
        return f"{self.players_base()}/join_campaign"

    def players_end_campaign(self) -> str:
        return f"{self.players_base()}/end_campaign"

    def players_remove_campaign(self) -> str:
        return f"{self.players_base()}/remove_campaign"

    def players_status(self, player_id: str) -> str:
        return f"{self.players_base()}/status/{player_id}"

ROUTES = Routes()
