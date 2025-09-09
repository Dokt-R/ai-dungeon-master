from typing import List, Optional

from fastapi import Depends
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from packages.shared.db import get_async_session_dependency
from packages.shared.errors import ErrorCode
from packages.shared.exceptions import NotFoundError, ValidationError
from packages.shared.logging_config import configure_logging, get_logger
from packages.shared.models import Character, Player
from packages.shared.models.game.gameplay_models import Class as GameplayClass

configure_logging(log_to_file=True, path="logs/character.log", level="ERROR")
# configure_logging()

# Create logger instance
logger = get_logger(__name__)


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

    async def create_character(
        self,
        player_id: str,
        name: str,
        species: str,
        class_index: str,
        subclass: Optional[str],
        background: str,
        strength: int,
        dexterity: int,
        constitution: int,
        intelligence: int,
        wisdom: int,
        charisma: int,
        prof_str_save: bool,
        prof_dex_save: bool,
        prof_con_save: bool,
        prof_int_save: bool,
        prof_wis_save: bool,
        prof_cha_save: bool,
        prof_acrobatics: bool,
        prof_animal_handling: bool,
        prof_arcana: bool,
        prof_athletics: bool,
        prof_deception: bool,
        prof_history: bool,
        prof_insight: bool,
        prof_intimidation: bool,
        prof_investigation: bool,
        prof_medicine: bool,
        prof_nature: bool,
        prof_perception: bool,
        prof_performance: bool,
        prof_persuasion: bool,
        prof_religion: bool,
        prof_sleight_of_hand: bool,
        prof_stealth: bool,
        prof_survival: bool,
    ) -> Character:
        """
        Create a new character for a player.
        """
        player = await self.session.get(Player, player_id)

        if not player:
            logger.error("Player not found")
            raise NotFoundError(
                ErrorCode.PLAYER_NOT_FOUND, details={"player_id": player_id}
            )

        statement = select(Character).where(
            Character.player_id == player_id, Character.name == name
        )
        result = await self.session.execute(statement)
        if result.scalars().first():
            logger.error("Duplicate character creation")
            raise ValidationError(
                ErrorCode.DUPLICATE_CHARACTER,
                name=name,
                details={
                    "player_id": player_id,
                    "name": name,
                },
            )

        logger.debug(
            "create_character_proficiencies_received",
            player_id=player_id,
            name=name,
            prof_str_save=prof_str_save,
            prof_dex_save=prof_dex_save,
            prof_con_save=prof_con_save,
            prof_int_save=prof_int_save,
            prof_wis_save=prof_wis_save,
            prof_cha_save=prof_cha_save,
        )

        new_character = Character(
            player_id=player_id,
            name=name,
            species=species,
            class_index=class_index,
            subclass=subclass,
            background=background,
            strength=strength,
            dexterity=dexterity,
            constitution=constitution,
            intelligence=intelligence,
            wisdom=wisdom,
            charisma=charisma,
            prof_str_save=prof_str_save,
            prof_dex_save=prof_dex_save,
            prof_con_save=prof_con_save,
            prof_int_save=prof_int_save,
            prof_wis_save=prof_wis_save,
            prof_cha_save=prof_cha_save,
            prof_acrobatics=prof_acrobatics,
            prof_animal_handling=prof_animal_handling,
            prof_arcana=prof_arcana,
            prof_athletics=prof_athletics,
            prof_deception=prof_deception,
            prof_history=prof_history,
            prof_insight=prof_insight,
            prof_intimidation=prof_intimidation,
            prof_investigation=prof_investigation,
            prof_medicine=prof_medicine,
            prof_nature=prof_nature,
            prof_perception=prof_perception,
            prof_performance=prof_performance,
            prof_persuasion=prof_persuasion,
            prof_religion=prof_religion,
            prof_sleight_of_hand=prof_sleight_of_hand,
            prof_stealth=prof_stealth,
            prof_survival=prof_survival,
        )
        self.session.add(new_character)
        await self.session.commit()
        await self.session.refresh(new_character)
        return new_character

    async def get_classes(self) -> List[GameplayClass]:
        """Get all available classes from the database."""
        statement = select(GameplayClass)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

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

    async def get_character_by_id(self, character_id: int) -> Character:
        """Get a character by their ID."""
        statement = select(Character).where(Character.character_id == character_id)
        try:
            result = await self.session.execute(statement).scalar_one()
        except NoResultFound:
            raise NotFoundError(ErrorCode.CHARACTER_NOT_FOUND)
        return result

    async def get_character_by_name(
        self, name: str, campaign_id: Optional[int] = None
    ) -> Character:
        """Get a character by name, optionally within a specific campaign."""
        statement = select(Character).where(Character.name == name)
        if campaign_id:
            statement = statement.where(Character.campaign_id == campaign_id)
        result = await self.session.execute(statement).scalars().first()
        return result
