import os
from packages.backend.components.server_settings_manager import ServerSettingsManager


class CampaignManager:
    def __init__(self, db_path: str = "server_settings.db"):
        if db_path is None:
            db_path = os.environ.get("DB_PATH", "server_settings.db")
        self.db_path = db_path
        self.settings_manager = ServerSettingsManager(db_path=db_path)

    def create_campaign(self, campaign_name: str, server_id: str, owner_id: str):
        # Check if campaign already exists
        if self.settings_manager.get_campaign(server_id, campaign_name):
            raise ValueError(f"A campaign named '{campaign_name}' already exists.")
        self.settings_manager.create_campaign(
            server_id, campaign_name, owner_id, state="active"
        )

    # All player join/end logic is now handled by PlayerManager.
    # Only campaign creation and retrieval remain here.

    def continue_campaign(self, user_id: str, server_id: str):
        """
        Returns a dict with:
            - campaign: campaign info
            - state: state to restore (autosave if newer, else last clean save)
            - source: 'autosave' or 'save'
        """
        return self.settings_manager.get_campaign_to_continue(user_id, server_id)

    def delete_campaign(
        self, server_id: str, campaign_name: str, requester_id: str, is_admin: bool
    ):
        """
        Delete a campaign if the requester is the owner or an admin.
        Raises ValueError or PermissionError if not permitted.
        """
        self.settings_manager.delete_campaign(
            server_id, campaign_name, requester_id, is_admin
        )
