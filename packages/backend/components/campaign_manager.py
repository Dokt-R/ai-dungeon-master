import json
from typing import List

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from packages.shared.db import get_async_session_dependency
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from packages.shared.models import Campaign, Player
from packages.shared.models.langgraph_state_models import MinimalGameState


class CampaignManager:
    """
    Manages campaign creation, updates, removal, and retrieval.
    """

    def __init__(self, session: AsyncSession = Depends(get_async_session_dependency)):
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
                ErrorCode.DUPLICATE_CAMPAIGN_NAME,
                campaign=campaign_name,
                details={
                    "server_id": server_id,
                    "campaign_name": campaign_name,
                    "owner_id": owner_id,
                },
            )

        new_campaign = Campaign(
            server_id=server_id, campaign_name=campaign_name, owner_id=owner_id
        )
        self.session.add(new_campaign)
        await self.session.commit()
        await self.session.refresh(new_campaign)
        return new_campaign

    async def get_campaign(self, server_id: str, campaign_name: str) -> Campaign:
        """
        Retrieve a campaign by server_id and campaign_name.
        """
        statement = select(Campaign).where(
            Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
        )
        results = await self.session.execute(statement)
        result = results.scalars().first()

        if not result:
            raise NotFoundError(
                ErrorCode.CAMPAIGN_NOT_FOUND,
                campaign=campaign_name,
                details={
                    "server_id": server_id,
                    "campaign_name": campaign_name,
                },
            )
        return result

    async def delete_campaign(
        self, server_id: str, campaign_name: str, requester_id: str, is_admin: bool
    ) -> bool:
        """
        Delete a campaign if the requester is the owner or an admin.
        """
        campaign = await self.get_campaign(server_id, campaign_name)
        if not campaign:
            raise NotFoundError(
                ErrorCode.CAMPAIGN_NOT_FOUND,
                campaign=campaign_name,
                details={
                    "server_id": server_id,
                    "campaign_name": campaign_name,
                    "requester_id": requester_id,
                    "is_admin": is_admin,
                },
            )

        if not (is_admin or requester_id == campaign.owner_id):
            raise PermissionDeniedError(
                ErrorCode.PERMISSION_DENIED_ERROR,
                details={
                    "server_id": server_id,
                    "campaign_name": campaign_name,
                    "requester_id": requester_id,
                    "is_admin": is_admin,
                    "owner_id": campaign.owner_id,
                },
            )

        await self.session.delete(campaign)
        await self.session.commit()
        return True

    async def get_campaign_players(self, campaign_id: int) -> List[Player]:
        """
        Retrieve all players for a given campaign.
        """
        campaign = await self.session.get(Campaign, campaign_id)
        if not campaign:
            raise NotFoundError(
                ErrorCode.CAMPAIGN_NOT_FOUND,
                campaign_name=str(campaign_id),
                details={"campaign_id": campaign_id},
            )

        return campaign.players

    async def update_campaign_state(self, campaign_id: int, state: MinimalGameState) -> Campaign:
        """
        Update the state of a campaign using MinimalGameState.
        """
        campaign = await self.session.get(Campaign, campaign_id)
        if not campaign:
            raise NotFoundError(
                ErrorCode.CAMPAIGN_NOT_FOUND,
                campaign_name=str(campaign_id),
                details={"campaign_id": campaign_id, "state": state},
            )

        campaign.state = json.dumps(state)  # Convert MinimalGameState to JSON string
        self.session.add(campaign)
        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign
