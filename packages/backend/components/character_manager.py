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
from packages.shared.models.game.equipment_models import (
    CharacterEquipment,
    Equipment,
    EquipmentPackContent,
)
from packages.shared.models.game.gameplay_links import CharacterProficiencyLink
from packages.shared.models.game.gameplay_models import (
    Ability,
    Alignment,
    Background,
    Class,
    Condition,
    Feat,
    Feature,
    Language,
    MagicSchool,
    Monster,
    Proficiency,
    Race,
    Skill,
    Spell,
    Subclass,
    Subrace,
    Trait,
)

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
        races_index: str,
        class_index: str,
        subclass: Optional[str],
        background_index: str,
        strength: int,
        dexterity: int,
        constitution: int,
        intelligence: int,
        wisdom: int,
        charisma: int,
        proficiencies: List[str],
        inventory: Optional[List[dict]] = None,
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

        new_character = Character(
            player_id=player_id,
            name=name,
            races_index=races_index,
            class_index=class_index,
            subclass=subclass,
            background_index=background_index,
            strength=strength,
            dexterity=dexterity,
            constitution=constitution,
            intelligence=intelligence,
            wisdom=wisdom,
            charisma=charisma,
        )
        self.session.add(new_character)
        await self.session.flush()  # Flush to get the new_character.character_id

        # Create proficiency links
        for prof_index in proficiencies:
            link = CharacterProficiencyLink(
                character_id=new_character.character_id,
                proficiency_index=prof_index,
            )
            self.session.add(link)

        # Create inventory items
        if inventory:
            for item_data in inventory:
                new_equipment_link = CharacterEquipment(
                    character_id=new_character.character_id,
                    equipment_index=item_data["index"],
                    quantity=item_data["quantity"],
                )
                self.session.add(new_equipment_link)

        await self.session.commit()
        await self.session.refresh(new_character)
        return new_character

    async def get_classes(self) -> List[Class]:
        """Get all available classes from the database."""
        statement = select(Class)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_subclasses(self) -> List[Subclass]:
        """Get all available subclasses from the database."""
        statement = select(Subclass)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
        
    async def get_backgrounds(self) -> List[Background]:
        """Get all available backgrounds from the database."""
        statement = select(Background)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_races(self) -> List[Race]:
        """Get all available races from the database."""
        statement = select(Race)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
    
    async def get_subraces(self) -> List[Subrace]:
        """Get all available subraces from the database."""
        statement = select(Subrace)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_abilities(self) -> List[Ability]:
        """Get all available abilities from the database."""
        statement = select(Ability)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_skills(self) -> List[Skill]:
        """Get all available skills from the database."""
        statement = select(Skill)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_conditions(self) -> List[Condition]:
        """Get all available conditions from the database."""
        statement = select(Condition)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_alignments(self) -> List[Alignment]:
        """Get all available alignments from the database."""
        statement = select(Alignment)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_magic_schools(self) -> List[MagicSchool]:
        """Get all available magic schools from the database."""
        statement = select(MagicSchool)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_languages(self) -> List[Language]:
        """Get all available languages from the database."""
        statement = select(Language)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_traits(self) -> List[Trait]:
        """Get all available traits from the database."""
        statement = select(Trait)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_proficiencies(self) -> List[Proficiency]:
        """Get all available proficiencies from the database."""
        statement = select(Proficiency)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
    
    async def get_spells(self) -> List[Spell]:
        """Get all available spells from the database."""
        statement = select(Spell)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
    
    async def get_feats(self) -> List[Feat]:
        """Get all available feats from the database."""
        statement = select(Feat)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
    
    async def get_features(self) -> List[Feature]:
        """Get all available features from the database."""
        statement = select(Feature)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
    
    async def get_monsters(self) -> List[Monster]:
        """Get all available monsters from the database."""
        statement = select(Monster)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_equipment(self, category_index: Optional[str] = None) -> List[Equipment]:
        """Get all equipment, optionally filtered by category."""
        statement = select(Equipment)
        if category_index:
            statement = statement.where(Equipment.equipment_category_index == category_index)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_pack_contents(self, pack_index: str) -> List[dict]:
        """Get the contents of an equipment pack."""
        statement = select(EquipmentPackContent).where(
            EquipmentPackContent.pack_index == pack_index
        )
        result = await self.session.execute(statement)
        contents = result.scalars().all()

        # The view expects a list of dicts with 'index' and 'quantity'
        return [
            {"index": content.item_index, "quantity": content.quantity}
            for content in contents
        ]
    
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
