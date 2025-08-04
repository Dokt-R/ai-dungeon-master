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

    # All player join/end logic is now handled by PlayerManager.
    # Only campaign creation and retrieval remain here.
