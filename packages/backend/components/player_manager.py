from typing import List, Optional

from sqlmodel import Session, select
from fastapi import Depends

from packages.shared.db import get_session
from packages.shared.error_handler import NotFoundError, ValidationError
from packages.shared.models import Campaign, CampaignPlayerLink, Character, Player


class PlayerManager:
    """
    Manages player participation, campaign membership, and character associations.
    """

    def __init__(self, session: Session = Depends(get_session)):
        """
        Initialize the PlayerManager with a database session.
        """
        self.session = session

    def create_player(self, player_id: str, username: str) -> dict:
        """
        Create a new player or update the username if the player already exists.
        """
        player = self.session.get(Player, player_id)
        if player:
            if player.username != username:
                player.username = username
                self.session.add(player)
        else:
            player = Player(player_id=player_id, username=username)
            self.session.add(player)
        self.session.commit()
        self.session.refresh(player)
        return {"player_id": player.player_id, "username": player.username}

    def join_campaign(
        self,
        player_id: str,
        server_id: str,
        username: Optional[str] = None,
        campaign_name: Optional[str] = None,
        character_name: Optional[str] = None,
        character_url: Optional[str] = None,
    ) -> dict:
        """
        Join a campaign as a player, optionally associating a character.
        """
        player = self.session.get(Player, player_id)
        if not player:
            player = Player(player_id=player_id, username=username)
            self.session.add(player)

        if not campaign_name:
            if not player.last_active_campaign:
                raise NotFoundError(
                    "No campaign specified and no last active campaign found."
                )
            campaign_name = player.last_active_campaign

        statement = select(Campaign).where(
            Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
        )
        campaign = self.session.exec(statement).first()
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

        if self.session.exec(statement).first():
            if campaign_name == player.last_active_campaign:
                raise ValidationError("""Player is already in a campaign.\n
                    Please user /campaign end to enter command mode\n
                    or specify a different campaign to join""")

        character = None
        if character_name:
            statement = select(Character).where(
                Character.player_id == player_id, Character.name == character_name
            )
            character = self.session.exec(statement).first()
            if not character:
                character = Character(
                    player_id=player_id,
                    name=character_name,
                    character_url=character_url,
                )
                self.session.add(character)
        else:
            statement = select(Character).where(Character.player_id == player_id)
            characters = self.session.exec(statement).all()
            if len(characters) > 1:
                raise ValidationError(
                    "Player has multiple characters, please specify one."
                )
            if not characters:
                raise NotFoundError("Player has no characters to join with.")
            character = characters[0]

        link = CampaignPlayerLink(
            campaign_id=campaign.campaign_id,
            player_id=player.player_id,
            character_id=character.character_id,
            player_status="joined",
        )

        merge_link = self.session.merge(link)
        player.last_active_campaign = campaign.campaign_name
        player.player_status = "joined"
        self.session.add(player)
        self.session.commit()
        self.session.refresh(merge_link)
        return {
            "campaign_name": campaign.campaign_name,
            "player_id": player.player_id,
            "character_id": character.character_id,
            "status": player.player_status,
        }

    def remove_campaign(
        self, player_id: str, server_id: str, campaign_name: str
    ) -> dict:
        """
        Remove the campaign association for a given player.
        If the removed campaign is the player's last active campaign, clear it.
        """
        player = self.session.get(Player, player_id)
        if not player:
            raise NotFoundError(f"Player with id '{player_id}' not found.")

        if not campaign_name:
            if not player.last_active_campaign:
                raise NotFoundError("Please specify which campaign to remove.")
            campaign_name = player.last_active_campaign

        # Get the campaign
        statement = select(Campaign).where(
            Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
        )
        campaign = self.session.exec(statement).first()
        if not campaign:
            raise NotFoundError(f"Campaign '{campaign_name}' not found.")

        # Get the link between player and campaign
        link_stmt = select(CampaignPlayerLink).where(
            CampaignPlayerLink.player_id == player_id,
            CampaignPlayerLink.campaign_id == campaign.campaign_id,
        )
        link = self.session.exec(link_stmt).first()
        if not link:
            raise NotFoundError("Player is not part of the specified campaign.")

        # Delete the link
        self.session.delete(link)

        # Clear last active campaign if it's the one being removed
        if player.last_active_campaign == campaign_name:
            player.last_active_campaign = None
            self.session.add(player)

        self.session.commit()
        return {
            "campaign_name": campaign_name,
            "player_id": player_id,
            "status": "left",
        }

    def end_campaign(
        self, player_id: str, server_id: str, campaign_name: Optional[str] = None
    ) -> dict:
        """
        End a campaign for a player by setting their status to 'cmd'.
        """
        player = self.session.get(Player, player_id)
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
        campaign = self.session.exec(statement).first()

        if not campaign:
            raise NotFoundError(f"Campaign '{campaign_name}' not found.")

        if player.player_status == "cmd":
            raise ValidationError("Player is already in command mode")

        statement = (
            select(CampaignPlayerLink)
            .where(CampaignPlayerLink.player_id == player_id)
            .where(CampaignPlayerLink.campaign_id == campaign.campaign_id)
        )
        link = self.session.exec(statement).first()

        if link:
            player.player_status = "cmd"
            self.session.add(link)
            self.session.commit()

        return {
            "campaign_name": campaign.campaign_name,
            "player_id": player.player_id,
            "player_status": "cmd",
        }

        statement = (
            select(CampaignPlayerLink)
            .where(CampaignPlayerLink.player_id == player_id)
            .where(CampaignPlayerLink.campaign_id == campaign.campaign_id)
        )
        link = self.session.exec(statement).first()

        if link:
            self.session.delete(link)
            self.session.commit()
            return True
        return False

    def get_player(self, player_id: str) -> dict:
        """
        Retrieve a summary of the player's campaigns, characters, and current status.
        """
        player = self.session.get(Player, player_id)
        if not player:
            raise NotFoundError(f"Player with ID '{player_id}' not found.")

        return {
            "player_id": player.player_id,
            "username": player.username,
            "player_status": player.player_status,
            "last_active_campaign": player.last_active_campaign,
            "campaigns": player.campaigns,
            "characters": player.characters,
        }
