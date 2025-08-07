from typing import List, Optional

from sqlmodel import Session, select

from packages.shared.db import get_engine
from packages.shared.error_handler import NotFoundError, ValidationError
from packages.shared.models import Campaign, CampaignPlayerLink, Player


class CampaignManager:
    """
    Manages campaign creation, updates, removal, and retrieval.
    """

    def __init__(self, engine=None):
        """
        Initialize the CampaignManager.
        """
        self.engine = engine or get_engine()

    def create_campaign(
        self, server_id: str, campaign_name: str, owner_id: str
    ) -> Campaign:
        """
        Create a new campaign.
        """
        with Session(self.engine) as session:
            statement = select(Campaign).where(
                Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
            )
            if session.exec(statement).first():
                raise ValidationError(
                    f"A campaign named '{campaign_name}' already exists."
                )

            new_campaign = Campaign(
                server_id=server_id, campaign_name=campaign_name, owner_id=owner_id
            )
            session.add(new_campaign)
            session.commit()
            session.refresh(new_campaign)
            return new_campaign

    def get_campaign(self, server_id: str, campaign_name: str) -> Optional[Campaign]:
        """
        Retrieve a campaign by server_id and campaign_name.
        """
        with Session(self.engine) as session:
            statement = select(Campaign).where(
                Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
            )
            return session.exec(statement).first()

    def delete_campaign(
        self, server_id: str, campaign_name: str, requester_id: str, is_admin: bool
    ) -> bool:
        """
        Delete a campaign if the requester is the owner or an admin.
        """
        with Session(self.engine) as session:
            campaign = self.get_campaign(server_id, campaign_name)
            if not campaign:
                raise NotFoundError(f"Campaign '{campaign_name}' not found.")

            if not (is_admin or requester_id == campaign.owner_id):
                raise PermissionError("Only the owner or an admin can delete.")

            session.delete(campaign)
            session.commit()
            return True

    def get_campaign_players(self, campaign_id: int) -> List[Player]:
        """
        Retrieve all players for a given campaign.
        """
        with Session(self.engine) as session:
            campaign = session.get(Campaign, campaign_id)
            if not campaign:
                raise NotFoundError(f"Campaign with id '{campaign_id}' not found.")
            return campaign.players

    def update_campaign_state(self, campaign_id: int, state: str) -> Campaign:
        """
        Update the state of a campaign.
        """
        with Session(self.engine) as session:
            campaign = session.get(Campaign, campaign_id)
            if not campaign:
                raise NotFoundError(f"Campaign with id '{campaign_id}' not found.")
            campaign.state = state
            session.add(campaign)
            session.commit()
            session.refresh(campaign)
            return campaign
