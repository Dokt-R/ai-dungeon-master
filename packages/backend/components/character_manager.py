from typing import List, Optional

from sqlmodel import Session, select

from packages.shared.db import get_engine
from packages.shared.error_handler import NotFoundError, ValidationError
from packages.shared.models import Character, Player


class CharacterManager:
    """
    Manages character creation, updates, removal, and retrieval for players.
    """

    def __init__(self, engine=None):
        """
        Initialize the CharacterManager.
        """
        self.engine = engine or get_engine()

    def add_character(
        self, player_id: str, name: str, character_url: Optional[str] = None
    ) -> Character:
        """
        Add a new character for a player.
        """
        with Session(self.engine) as session:
            player = session.get(Player, player_id)
            if not player:
                raise NotFoundError(f"Player with id '{player_id}' does not exist.")

            statement = select(Character).where(
                Character.player_id == player_id, Character.name == name
            )
            if session.exec(statement).first():
                raise ValidationError(
                    f"Character with name '{name}' already exists for player '{player_id}'."
                )

            new_character = Character(
                player_id=player_id, name=name, character_url=character_url
            )
            session.add(new_character)
            session.commit()
            session.refresh(new_character)
            return new_character

    def update_character(
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
                "At least one of name or character_url must be provided."
            )

        with Session(self.engine) as session:
            character = session.get(Character, character_id)
            if not character:
                raise NotFoundError(
                    f"Character with id '{character_id}' does not exist."
                )

            if name is not None:
                statement = (
                    select(Character)
                    .where(Character.player_id == character.player_id)
                    .where(Character.name == name)
                    .where(Character.character_id != character_id)
                )
                if session.exec(statement).first():
                    raise ValidationError(
                        f"Character with name '{name}' already exists for this player."
                    )
                character.name = name

            if character_url is not None:
                character.character_url = character_url

            session.add(character)
            session.commit()
            session.refresh(character)
            return character

    def remove_character(self, character_id: int) -> bool:
        """
        Remove a character by character_id.
        """
        with Session(self.engine) as session:
            character = session.get(Character, character_id)
            if character:
                session.delete(character)
                session.commit()
                return True
            return False

    def get_characters_for_player(self, player_id: str) -> List[Character]:
        """
        Retrieve all characters for a given player.
        """
        with Session(self.engine) as session:
            statement = select(Character).where(Character.player_id == player_id)
            return session.exec(statement).all()
