from typing import List, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from packages.shared.db import get_async_session
from packages.shared.error_handler import NotFoundError, ValidationError
from packages.shared.models import Campaign, Player


class CampaignManager:
    """
    Manages campaign creation, updates, removal, and retrieval.
    """

    def __init__(self, session: AsyncSession = Depends(get_async_session)):
        """
        Initialize the CampaignManager.
        """
        self.session = session

    async def create_campaign(
        self, server_id: str, campaign_name: str, owner_id: str
    ) -> Campaign:
        """
        Create a new campaign.
        """
        statement = select(Campaign).where(
            Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
        )
        result = await self.session.execute(statement)
        if result.scalars().first():
            raise ValidationError(
                f"A campaign named **{campaign_name}** already exists."
            )

        new_campaign = Campaign(
            server_id=server_id, campaign_name=campaign_name, owner_id=owner_id
        )
        self.session.add(new_campaign)
        await self.session.commit()
        await self.session.refresh(new_campaign)
        return new_campaign

    async def get_campaign(
        self, server_id: str, campaign_name: str
    ) -> Optional[Campaign]:
        """
        Retrieve a campaign by server_id and campaign_name.
        """
        statement = select(Campaign).where(
            Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def delete_campaign(
        self, server_id: str, campaign_name: str, requester_id: str, is_admin: bool
    ) -> bool:
        """
        Delete a campaign if the requester is the owner or an admin.
        """
        campaign = await self.get_campaign(server_id, campaign_name)
        if not campaign:
            raise NotFoundError(f"Campaign named **{campaign_name}** not found.")

        if not (is_admin or requester_id == campaign.owner_id):
            raise PermissionError("Only the owner or an admin can delete.")

        await self.session.delete(campaign)
        await self.session.commit()
        return True

    async def get_campaign_players(self, campaign_id: int) -> List[Player]:
        """
        Retrieve all players for a given campaign.
        """
        campaign = await self.session.get(Campaign, campaign_id)
        if not campaign:
            raise NotFoundError(f"Campaign with name **{campaign_id}** not found.")
        return campaign.players

    async def update_campaign_state(self, campaign_id: int, state: str) -> Campaign:
        """
        Update the state of a campaign.
        """
        campaign = await self.session.get(Campaign, campaign_id)
        if not campaign:
            raise NotFoundError(f"Campaign with name **{campaign_id}** not found.")
        campaign.state = state
        self.session.add(campaign)
        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign
