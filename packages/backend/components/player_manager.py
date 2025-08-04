class PlayerManager:
    def __init__(self):
        # Should populate upon creation when player joins server probably
        # Or when a player joins server he should populate the DB and set
        self.status = "outsider"

    def join_campaign(
        self, campaign_name: str, player_id: str, character_name: str = None
    ):
        # This is a stub. In a real implementation, this would:
        # - Check if the campaign exists
        # - Add the player to the campaign's player list
        # - Optionally register a character for the player
        # - Persist the updated campaign/player data
        # For now, just simulate success.
        # Additional TODO is check if player already has a campaign name filled
        return {
            "campaign_name": campaign_name,
            "player_id": player_id,
            "character_name": character_name,
            "status": "joined",
        }

    def end_campaign(
        self, campaign_name: str, player_id: str, character_name: str = None
    ):
            # This is a stub. In a real implementation, this would:
            # - Check if the campaign exists
            # - Add the player to the campaign's player list
            # - Optionally register a character for the player
            # - Persist the updated campaign/player data
            # For now, just simulate success.
            return {
                "campaign_name": campaign_name,
                "player_id": player_id,
                "character_name": character_name,
                "player_status": "cmd",
            }
