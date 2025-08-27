from typing import List, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from packages.shared.db import get_async_session_dependency
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import NotFoundError, ValidationError
from packages.shared.models import Character, Player


class CharacterManager:
    """
    Manages character creation, updates, removal, and retrieval for players.
    """

    def __init__(self, session: AsyncSession = Depends(get_async_session_dependency)):
        """
        Initialize the CharacterManager.
        """
        self.session = session

    async def add_character(
        self, player_id: str, name: str, character_url: Optional[str] = None
    ) -> Character:
        """
        Add a new character for a player.
        """
        player = await self.session.get(Player, player_id)

        if not player:
            raise NotFoundError(
                ErrorCode.PLAYER_NOT_FOUND, details={"player_id": player_id}
            )

        statement = select(Character).where(
            Character.player_id == player_id, Character.name == name
        )
        result = await self.session.execute(statement)
        if result.scalars().first():
            raise ValidationError(
                ErrorCode.DUPLICATE_CHARACTER,
                name=name,
                details={
                    "player_id": player_id,
                    "name": name,
                    "character_url": character_url,
                },
            )

        new_character = Character(
            player_id=player_id, name=name, character_url=character_url
        )
        self.session.add(new_character)
        await self.session.commit()
        await self.session.refresh(new_character)
        return new_character

    async def update_character(
        self,
        character_id: int,
        name: Optional[str] = None,
        character_url: Optional[str] = None,
    ) -> Character:
        """
        Update character data by character_id.
        """
        if name is None and character_url is None:
            raise ValidationError(
                ErrorCode.CHARACTER_EMPTY_FIELDS,
                details={
                    "character_id": character_id,
                    "name": name,
                    "character_url": character_url,
                },
            )

        character = await self.session.get(Character, character_id)
        if not character:
            raise NotFoundError(
                ErrorCode.CHARACTER_NOT_FOUND,
                details={"character_id": character_id},
            )

        if name is not None:
            statement = (
                select(Character)
                .where(Character.player_id == character.player_id)
                .where(Character.name == name)
                .where(Character.character_id != character_id)
            )
            result = await self.session.execute(statement)
            if result.scalars().first():
                raise ValidationError(
                    ErrorCode.DUPLICATE_CHARACTER,
                    name=name,
                    details={
                        "player_id": character.player_id,
                        "name": name,
                        "character_id": character_id,
                    },
                )
            character.name = name

        if character_url is not None:
            character.character_url = character_url

        self.session.add(character)
        await self.session.commit()
        await self.session.refresh(character)
        return character

    async def remove_character(self, character_id: int) -> bool:
        """
        Remove a character by character_id.
        """
        character = await self.session.get(Character, character_id)
        if not character:
            raise NotFoundError(
                ErrorCode.CHARACTER_NOT_FOUND,
                details={"character_id": character_id},
            )

        await self.session.delete(character)
        await self.session.commit()
        return True

    async def get_characters_for_player(self, player_id: str) -> List[Character]:
        """
        Retrieve all characters for a given player.
        """
        statement = select(Character).where(Character.player_id == player_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
