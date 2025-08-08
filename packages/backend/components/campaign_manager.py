from typing import List, Optional

from sqlmodel import Session, select
from fastapi import Depends

from packages.shared.db import get_session
from packages.shared.error_handler import NotFoundError, ValidationError
from packages.shared.models import Campaign, CampaignPlayerLink, Player


class CampaignManager:
    """
    Manages campaign creation, updates, removal, and retrieval.
    """

    def __init__(self, session: Session = Depends(get_session)):
        """
        Initialize the CampaignManager.
        """
        self.session = session

    def create_campaign(
        self, server_id: str, campaign_name: str, owner_id: str
    ) -> Campaign:
        """
        Create a new campaign.
        """
        statement = select(Campaign).where(
            Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
        )
        if self.session.exec(statement).first():
            raise ValidationError(f"A campaign named '{campaign_name}' already exists.")

        new_campaign = Campaign(
            server_id=server_id, campaign_name=campaign_name, owner_id=owner_id
        )
        self.session.add(new_campaign)
        self.session.commit()
        self.session.refresh(new_campaign)
        return new_campaign

    def get_campaign(self, server_id: str, campaign_name: str) -> Optional[Campaign]:
        """
        Retrieve a campaign by server_id and campaign_name.
        """
        statement = select(Campaign).where(
            Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
        )
        return self.session.exec(statement).first()

    def delete_campaign(
        self, server_id: str, campaign_name: str, requester_id: str, is_admin: bool
    ) -> bool:
        """
        Delete a campaign if the requester is the owner or an admin.
        """
        campaign = self.get_campaign(server_id, campaign_name)
        if not campaign:
            raise NotFoundError(f"Campaign '{campaign_name}' not found.")

        if not (is_admin or requester_id == campaign.owner_id):
            raise PermissionError("Only the owner or an admin can delete.")

        self.session.delete(campaign)
        self.session.commit()
        return True

    def get_campaign_players(self, campaign_id: int) -> List[Player]:
        """
        Retrieve all players for a given campaign.
        """
        campaign = self.session.get(Campaign, campaign_id)
        if not campaign:
            raise NotFoundError(f"Campaign with id '{campaign_id}' not found.")
        return campaign.players

    def update_campaign_state(self, campaign_id: int, state: str) -> Campaign:
        """
        Update the state of a campaign.
        """
        campaign = self.session.get(Campaign, campaign_id)
        if not campaign:
            raise NotFoundError(f"Campaign with id '{campaign_id}' not found.")
        campaign.state = state
        self.session.add(campaign)
        self.session.commit()
        self.session.refresh(campaign)
        return campaign
