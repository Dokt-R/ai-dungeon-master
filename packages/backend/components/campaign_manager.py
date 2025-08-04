from packages.backend.components.server_settings_manager import ServerSettingsManager


class CampaignManager:
    def __init__(self, db_path: str = "server_settings.db"):
        self.settings_manager = ServerSettingsManager(db_path=db_path)

    def create_campaign(self, campaign_name: str, server_id: str, owner_id: str):
        # Check if campaign already exists
        if self.settings_manager.get_campaign(server_id, campaign_name):
            raise ValueError(f"A campaign named '{campaign_name}' already exists.")
        self.settings_manager.create_campaign(
            server_id, campaign_name, owner_id, state="{}"
        )

    def resume_campaign(
        self, campaign_name: str, player_discord_id: str, server_id: str = None
    ):
        # Find campaign by name and server_id
        if not server_id:
            raise ValueError("server_id is required to resume a campaign.")
        campaign = self.settings_manager.get_campaign(server_id, campaign_name)
        if not campaign:
            raise ValueError("Campaign does not exist")
        # Simulate loading state and narrative
        return {
            "narrative": f"Resuming campaign '{campaign_name}' at the last clean save point. (Simulated narrative for player {player_discord_id})"
        }

    def end_campaign(
        self,
        campaign_name: str,
        server_id: str,
        player_id: str,
        character_name: str = None,
    ):
        campaign = self.settings_manager.get_campaign(server_id, campaign_name)
        self.settings_manager.remove_player_from_campaign(
            campaign["campaign_id"], player_id, character_name
        )
        # return {"player_status": "cmd"} #! Line could be deleted
