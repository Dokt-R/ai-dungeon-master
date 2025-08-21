from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from packages.shared.db import get_async_session
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import NotFoundError, ValidationError
from packages.shared.models import Campaign, CampaignPlayerLink, Character, Player


class PlayerManager:
    """
    Manages player participation, campaign membership, and character associations.
    """

    def __init__(self, session: AsyncSession = Depends(get_async_session)):
        """
        Initialize the PlayerManager with a database session.
        """
        self.session = session

    async def create_player(self, player_id: str, username: str) -> dict:
        """
        Create a new player or update the username if the player already exists.
        """
        player = await self.session.get(Player, player_id)
        if player:
            if player.username != username:
                player.username = username
                self.session.add(player)
        else:
            player = Player(player_id=player_id, username=username)
            self.session.add(player)
        await self.session.commit()
        await self.session.refresh(player)
        return {"player_id": player.player_id, "username": player.username}

    async def join_campaign(
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
        player = await self.session.get(Player, player_id)
        if not player:
            player = Player(player_id=player_id, username=username)
            self.session.add(player)

        if not campaign_name:
            if not player.last_active_campaign:
                raise NotFoundError(
                    ErrorCode.NO_LAST_ACTIVE_CAMPAIGN,
                    details={
                        "server_id": server_id,
                        "player_id": player_id,
                        "username": username,
                    },
                )
            campaign_name = player.last_active_campaign

        statement = select(Campaign).where(
            Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
        )
        result = await self.session.execute(statement)
        campaign = result.scalars().first()
        if not campaign:
            raise NotFoundError(
                ErrorCode.CAMPAIGN_NOT_FOUND,
                campaign=campaign_name,
                details={
                    "server_id": server_id,
                    "player_id": player_id,
                    "username": username,
                    "campaign_name": campaign_name,
                },
            )

        # Check if already joined
        statement = (
            select(CampaignPlayerLink)
            .join(Campaign)
            .where(CampaignPlayerLink.player_id == player_id)
            .where(Campaign.server_id == server_id)
            .where(player.player_status == "joined")
        )
        result = await self.session.execute(statement)
        if result.scalars().first():
            if campaign_name == player.last_active_campaign:
                raise ValidationError(
                    ErrorCode.PLAYER_NOT_IN_CMD,
                    details={
                        "server_id": server_id,
                        "player_id": player_id,
                        "username": username,
                        "campaign_name": campaign_name,
                    },
                )

        character = None
        if character_name:
            statement = select(Character).where(
                Character.player_id == player_id, Character.name == character_name
            )
            result = await self.session.execute(statement)
            character = result.scalars().first()
            if not character:
                character = Character(
                    player_id=player_id,
                    name=character_name,
                    character_url=character_url,
                )
                self.session.add(character)
        else:
            statement = select(Character).where(Character.player_id == player_id)
            result = await self.session.execute(statement)
            characters = result.scalars().all()
            if len(characters) > 1:
                raise ValidationError(
                    ErrorCode.PLAYER_HAS_MULTIPLE_CHARACTERS,
                    details={
                        "player_id": player_id,
                        "character_count": len(characters),
                    },
                )
            if not characters:
                raise NotFoundError(
                    ErrorCode.PLAYER_HAS_NO_CHARACTERS,
                    details={"player_id": player_id},
                )
            character = characters[0]

        link = CampaignPlayerLink(
            campaign_id=campaign.campaign_id,
            player_id=player.player_id,
            character_id=character.character_id,
            player_status="joined",
        )

        merge_link = await self.session.merge(link)
        player.last_active_campaign = campaign.campaign_name
        player.player_status = "joined"
        # Pre commit attributes to avoid SQLAlchemy lazy load
        return_campaign_name = campaign.campaign_name
        return_campaign_id = campaign.campaign_id
        return_player_id = player.player_id
        return_character_id = character.character_id
        return_player_status = player.player_status
        # Continue with the DB actions
        self.session.add(player)
        await self.session.commit()
        await self.session.refresh(merge_link)
        return {
            "campaign_name": return_campaign_name,
            "campaign_id": return_campaign_id,
            "player_id": return_player_id,
            "character_id": return_character_id,
            "status": return_player_status,
        }

    async def continue_campaign(
        self,
        player_id: str,
        username: str,
    ) -> dict:
        """
        Continue playing in your last active campaign
        """
        #! TODO: Fix Characters to be Associated with the Campaign so that it auto joins with the character involved
        #! TODO: Define player creation somewhere reusable
        player = await self.session.get(Player, player_id)
        if not player:
            player = Player(player_id=player_id, username=username)
            self.session.add(player)
            await self.session.commit()
            await self.session.refresh(player)

        campaign_name = player.last_active_campaign

        if not campaign_name:
            raise NotFoundError(
                ErrorCode.NO_LAST_ACTIVE_CAMPAIGN,
                details={
                    "player_id": player_id,
                },
            )

        statement = select(Campaign).where(Campaign.campaign_name == campaign_name
        )
        result = await self.session.execute(statement)
        campaign = result.scalars().first()
        if not campaign:
            raise NotFoundError(
                ErrorCode.CAMPAIGN_NOT_FOUND,
                campaign=campaign_name,
                details={
                    "player_id": player_id,
                    "campaign_name": campaign_name,
                },
            )

        # Check if already joined
        statement = (
            select(CampaignPlayerLink)
            .join(Campaign)
            .where(CampaignPlayerLink.player_id == player_id)
            .where(player.player_status == "joined")
        )
        result = await self.session.execute(statement)
        if result.scalars().first():
            if campaign_name == player.last_active_campaign:
                raise ValidationError(
                    ErrorCode.PLAYER_NOT_IN_CMD,
                    details={
                        "player_id": player_id,
                        "campaign_name": campaign_name,
                    },
                )

        character = None
        statement = select(Character).where(Character.player_id == player_id)
        result = await self.session.execute(statement)
        characters = result.scalars().all()
        if len(characters) > 1:
            raise ValidationError(
                ErrorCode.PLAYER_HAS_MULTIPLE_CHARACTERS,
                details={
                    "player_id": player_id,
                    "character_count": len(characters),
                },
            )
        if not characters:
            raise NotFoundError(
                ErrorCode.PLAYER_HAS_NO_CHARACTERS,
                details={"player_id": player_id},
            )
        character = characters[0]

        link = CampaignPlayerLink(
            campaign_id=campaign.campaign_id,
            player_id=player.player_id,
            character_id=character.character_id,
            player_status="joined",
        )

        merge_link = await self.session.merge(link)
        player.last_active_campaign = campaign.campaign_name
        player.player_status = "joined"
        # Pre commit attributes to avoid SQLAlchemy lazy load
        return_campaign_name = campaign.campaign_name
        return_campaign_id = campaign.campaign_id
        return_player_id = player.player_id
        return_character_id = character.character_id
        return_player_status = player.player_status
        # Continue with the DB actions
        self.session.add(player)
        await self.session.commit()
        await self.session.refresh(merge_link)
        return {
            "campaign_name": return_campaign_name,
            "campaign_id": return_campaign_id,
            "player_id": return_player_id,
            "character_id": return_character_id,
            "status": return_player_status,
        }

    async def remove_campaign(
        self, player_id: str, server_id: str, campaign_name: str
    ) -> dict:
        """
        Remove the campaign association for a given player.
        If the removed campaign is the player's last active campaign, clear it.
        """
        player = await self.session.get(Player, player_id)
        if not player:
            raise NotFoundError(
                ErrorCode.PLAYER_NOT_FOUND,
                details={
                    "server_id": server_id,
                    "player_id": player_id,
                    "campaign_name": campaign_name,
                },
            )

        if not campaign_name:
            if not player.last_active_campaign:
                raise NotFoundError(
                    ErrorCode.PLAYER_HAS_NO_CAMPAIGNS, details={"player_id": player_id}
                )
            campaign_name = player.last_active_campaign

        # Get the campaign
        statement = select(Campaign).where(
            Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
        )
        result = await self.session.execute(statement)
        campaign = result.scalars().first()
        if not campaign:
            raise NotFoundError(
                ErrorCode.CAMPAIGN_NOT_FOUND,
                campaign=campaign_name,
                details={
                    "server_id": server_id,
                    "campaign_name": campaign_name,
                    "player_id": player_id,
                },
            )

        # Get the link between player and campaign
        link_stmt = select(CampaignPlayerLink).where(
            CampaignPlayerLink.player_id == player_id,
            CampaignPlayerLink.campaign_id == campaign.campaign_id,
        )
        result = await self.session.execute(link_stmt)
        link = result.scalars().first()
        if not link:
            raise NotFoundError(
                ErrorCode.PLAYER_NOT_IN_CAMPAIGN,
                details={"player_id": player_id, "campaign_id": campaign.campaign_id},
            )

        # Delete the link
        await self.session.delete(link)

        # Clear last active campaign if it's the one being removed
        if player.last_active_campaign == campaign_name:
            player.last_active_campaign = None
            self.session.add(player)

        await self.session.commit()
        return {
            "campaign_name": campaign_name,
            "player_id": player_id,
            "status": "left",
        }

    async def end_campaign(
        self, player_id: str, server_id: str, campaign_name: Optional[str] = None
    ) -> dict:
        """
        End a campaign for a player by setting their status to 'cmd'.
        """
        player = await self.session.get(Player, player_id)
        if not player:
            raise NotFoundError(
                ErrorCode.PLAYER_HAS_NO_CAMPAIGNS,
                details={"server_id": server_id, "player_id": player_id},
            )

        if not campaign_name:
            if not player.last_active_campaign:
                raise NotFoundError(
                    ErrorCode.NO_LAST_ACTIVE_CAMPAIGN, details={"player_id": player_id}
                )

            campaign_name = player.last_active_campaign

        statement = select(Campaign).where(
            Campaign.server_id == server_id, Campaign.campaign_name == campaign_name
        )
        result = await self.session.execute(statement)
        campaign = result.scalars().first()

        if not campaign:
            raise NotFoundError(
                ErrorCode.CAMPAIGN_NOT_FOUND,
                campaign=campaign_name,
                details={
                    "server_id": server_id,
                    "player_id": player_id,
                    "campaign_name": campaign_name,
                },
            )

        statement = (
            select(CampaignPlayerLink)
            .where(CampaignPlayerLink.player_id == player_id)
            .where(CampaignPlayerLink.campaign_id == campaign.campaign_id)
        )
        result = await self.session.execute(statement)
        link = result.scalars().first()

        if not link:
            raise NotFoundError(
                ErrorCode.PLAYER_NOT_IN_CAMPAIGN,
                details={"player_id": player_id, "campaign_id": campaign.campaign_id},
            )

        if player.player_status == "cmd":
            raise ValidationError(
                ErrorCode.PLAYER_ALREADY_IN_CMD, details={"player_id": player_id}
            )

        player.player_status = "cmd"
        self.session.add(player)
        await self.session.commit()

        return {
            "campaign_name": campaign_name,
            "player_id": player_id,
            "player_status": "cmd",
        }

    async def get_player(self, player_id: str) -> dict:
        """
        Retrieve a summary of the player's campaigns, characters, and current status.
        """
        player = await self.session.get(Player, player_id)
        if not player:
            raise NotFoundError(
                ErrorCode.PLAYER_NOT_FOUND, details={"player_id": player_id}
            )

        return {
            "player_id": player.player_id,
            "username": player.username,
            "player_status": player.player_status,
            "last_active_campaign": player.last_active_campaign,
            "campaigns": player.campaigns,
            "characters": player.characters,
        }
