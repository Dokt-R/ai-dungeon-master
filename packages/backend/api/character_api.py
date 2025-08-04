from fastapi import APIRouter
from pydantic import BaseModel, Field
from packages.backend.components.character_manager import CharacterManager
from packages.shared.error_handler import fastapi_error_handler, NotFoundError


router = APIRouter(prefix="/characters", tags=["characters"])
character_manager = CharacterManager()


class AddCharacterRequest(BaseModel):
    """
    Request model for adding a new character.

    Fields:
        player_id (str): Unique identifier for the player. 3-64 chars, alphanumeric, dashes or underscores.
        name (str): Name of the character. 1-32 chars, alphanumeric, dashes, underscores, or spaces.
        dnd_beyond_url (str, optional): D&D Beyond URL for the character.
    """

    player_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")
    name: str = Field(..., min_length=1, max_length=32, pattern=r"^[\w\- ]+$")
    dnd_beyond_url: str | None = None


class UpdateCharacterRequest(BaseModel):
    """
    Request model for updating a character.

    Fields:
        character_id (int): Unique identifier for the character.
        name (str, optional): New name for the character. 1-32 chars, alphanumeric, dashes, underscores, or spaces.
        dnd_beyond_url (str, optional): New D&D Beyond URL for the character.
    """

    character_id: int
    name: str | None = Field(None, min_length=1, max_length=32, pattern=r"^[\w\- ]+$")
    dnd_beyond_url: str | None = None


class RemoveCharacterRequest(BaseModel):
    """
    Request model for removing a character.

    Fields:
        character_id (int): Unique identifier for the character to remove.
    """

    character_id: int


class ListCharactersRequest(BaseModel):
    """
    Request model for listing all characters for a player.

    Fields:
        player_id (str): Unique identifier for the player. 3-64 chars, alphanumeric, dashes or underscores.
    """

    player_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[\w\-]+$")


@router.post("/add")
@fastapi_error_handler
def add_character(req: AddCharacterRequest):
    """
    Add a new character for a player.

    Validates that the player exists and that the character name is unique for the player.

    Args:
        req (AddCharacterRequest): Request body containing player_id, name, and optional dnd_beyond_url.

    Returns:
        dict: The character_id of the newly created character.

    Raises:
        NotFoundError: If the player does not exist.
        ValidationError: If a character with the same name already exists for the player.
    """
    character_id = character_manager.add_character(
        player_id=req.player_id,
        name=req.name,
        dnd_beyond_url=req.dnd_beyond_url,
    )
    return {"character_id": character_id}


@router.post("/update")
@fastapi_error_handler
def update_character(req: UpdateCharacterRequest):
    """
    Update an existing character's name and/or D&D Beyond URL.

    At least one of name or dnd_beyond_url must be provided. Ensures name uniqueness for the player.

    Args:
        req (UpdateCharacterRequest): Request body containing character_id, and optional name and dnd_beyond_url.

    Returns:
        dict: Success status.

    Raises:
        NotFoundError: If the character does not exist.
        ValidationError: If no update fields are provided or if the new name would violate uniqueness.
    """
    result = character_manager.update_character(
        character_id=req.character_id,
        name=req.name,
        dnd_beyond_url=req.dnd_beyond_url,
    )
    return {"success": result}


@router.post("/remove")
@fastapi_error_handler
def remove_character(req: RemoveCharacterRequest):
    """
    Remove a character by character_id.

    Also sets character_id to NULL in CampaignPlayers for any affected rows.

    Args:
        req (RemoveCharacterRequest): Request body containing character_id.

    Returns:
        dict: Success status.

    Raises:
        NotFoundError: If the character does not exist.
    """
    result = character_manager.remove_character(character_id=req.character_id)
    if not result:
        raise NotFoundError("Character not found")
    return {"success": True}


@router.post("/list")
@fastapi_error_handler
def list_characters(req: ListCharactersRequest):
    """
    Retrieve all characters for a given player.

    Args:
        req (ListCharactersRequest): Request body containing player_id.

    Returns:
        dict: List of characters, each with character_id, name, and dnd_beyond_url.

    Raises:
        NotFoundError: If the player does not exist.
    """
    characters = character_manager.get_characters_for_player(player_id=req.player_id)
    return {"characters": characters}
