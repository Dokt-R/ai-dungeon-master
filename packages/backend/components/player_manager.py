from typing import List, Optional

from sqlmodel import Session, select

from packages.shared.db import get_engine
from packages.shared.error_handler import NotFoundError, ValidationError
from packages.shared.models import Campaign, CampaignPlayerLink, Character, Player


class PlayerManager:
    """
    Manages player participation, campaign membership, and character associations.
    """

    def __init__(self, engine=None):
        """
        Initialize the PlayerManager.
        """
        self.engine = engine or get_engine()

    def join_campaign(
        self,
        player_id: str,
        server_id: str,
        username: Optional[str] = None,
        campaign_name: Optional[str] = None,
        character_name: Optional[str] = None,
        character_url: Optional[str] = None,
    ) -> CampaignPlayerLink:
        """
        Join a campaign as a player, optionally associating a character.
        """
        with Session(self.engine) as session:
            player = session.get(Player, player_id)
            if not player:
                player = Player(user_id=player_id, username=username)
                session.add(player)

            if not campaign_name:
                if not player.last_active_campaign:
                    raise NotFoundError(
                        "No campaign specified and no last active campaign found."
                    )
                campaign_name = player.last_active_campaign

            statement = select(Campaign).where(
                Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
            )
            campaign = session.exec(statement).first()
            if not campaign:
                raise NotFoundError(f"Campaign '{campaign_name}' not found.")

            # Check if already joined, to
            statement = (
                select(CampaignPlayerLink)
                .join(Campaign)
                .where(CampaignPlayerLink.player_id == player_id)
                .where(Campaign.server_id == server_id)
                .where(player.player_status == "joined")
            )

            if session.exec(statement).first():
                if campaign_name == player.last_active_campaign:
                    raise ValidationError("""Player is already in a campaign.\n
                        Please user /campaign end to enter command mode\n
                        or specify a different campaign to join""")

            character = None
            if character_name:
                statement = select(Character).where(
                    Character.player_id == player_id, Character.name == character_name
                )
                character = session.exec(statement).first()
                if not character:
                    character = Character(
                        player_id=player_id,
                        name=character_name,
                        character_url=character_url,
                    )
                    session.add(character)
            else:
                statement = select(Character).where(Character.player_id == player_id)
                characters = session.exec(statement).all()
                if len(characters) > 1:
                    raise ValidationError(
                        "Player has multiple characters, please specify one."
                    )
                if not characters:
                    raise NotFoundError("Player has no characters to join with.")
                character = characters[0]

            link = CampaignPlayerLink(
                campaign_id=campaign.campaign_id,
                player_id=player.user_id,
                character_id=character.character_id,
                player_status=player.player_status,
            )

            merge_link = session.merge(link)
            player.last_active_campaign = campaign.campaign_name
            player.player_status = "joined"
            session.add(player)
            session.commit()
            session.refresh(merge_link)
            return merge_link

    def remove_campaign(
        self, player_id: str, server_id: str, campaign_name: Optional[str] = None
    ) -> bool:
        """
        Remove the campaign association for a given player.
        If the removed campaign is the player's last active campaign, clear it.
        """
        with Session(self.engine) as session:
            player = session.get(Player, player_id)
            if not player:
                raise NotFoundError(f"Player with id '{player_id}' not found.")

            if not campaign_name:
                if not player.last_active_campaign:
                    raise NotFoundError(
                        "No campaign specified and no last active campaign found."
                    )
                campaign_name = player.last_active_campaign

            # Get the campaign
            statement = select(Campaign).where(
                Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
            )
            campaign = session.exec(statement).first()
            if not campaign:
                raise NotFoundError(f"Campaign '{campaign_name}' not found.")

            # Get the link between player and campaign
            link_stmt = select(CampaignPlayerLink).where(
                CampaignPlayerLink.player_id == player_id,
                CampaignPlayerLink.campaign_id == campaign.campaign_id,
            )
            link = session.exec(link_stmt).first()
            if not link:
                raise NotFoundError("Player is not part of the specified campaign.")

            # Delete the link
            session.delete(link)

            # Clear last active campaign if it's the one being removed
            if player.last_active_campaign == campaign_name:
                player.last_active_campaign = None
                session.add(player)

            session.commit()
            return True

    def end_campaign(
        self, player_id: str, server_id: str, campaign_name: Optional[str] = None
    ) -> dict:
        """
        End a campaign for a player by setting their status to 'cmd'.
        """
        with Session(self.engine) as session:
            player = session.get(Player, player_id)
            if not player:
                raise NotFoundError(f"Player with id '{player_id}' not found.")

            if not campaign_name:
                if not player.last_active_campaign:
                    raise ValidationError(
                        "No campaign specified and no last active campaign found."
                    )
                campaign_name = player.last_active_campaign

            statement = select(Campaign).where(
                Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
            )
            campaign = session.exec(statement).first()

            if not campaign:
                raise NotFoundError(f"Campaign '{campaign_name}' not found.")

            if player.player_status == "cmd":
                raise ValidationError("Player is already in command mode")

            statement = (
                select(CampaignPlayerLink)
                .where(CampaignPlayerLink.player_id == player_id)
                .where(CampaignPlayerLink.campaign_id == campaign.campaign_id)
            )
            link = session.exec(statement).first()

            if link:
                player.player_status = "cmd"
                session.add(link)
                session.commit()

            return {
                "campaign_name": campaign.campaign_name,
                "player_id": player.user_id,
                "player_status": "cmd",
            }

            statement = (
                select(CampaignPlayerLink)
                .where(CampaignPlayerLink.player_id == player_id)
                .where(CampaignPlayerLink.campaign_id == campaign.campaign_id)
            )
            link = session.exec(statement).first()

            if link:
                session.delete(link)
                session.commit()
                return True
            return False

    def get_player_status(self, player_id: str) -> dict:
        """
        Retrieve a summary of the player's campaigns, characters, and current status.
        """
        with Session(self.engine) as session:
            player = session.get(Player, player_id)
            if not player:
                raise NotFoundError(f"Player with ID '{player_id}' not found.")

            return {
                "player_id": player.user_id,
                "username": player.username,
                "player_status": player.player_status,
                "last_active_campaign": player.last_active_campaign,
                "campaigns": player.campaigns,
                "characters": player.characters,
            }
