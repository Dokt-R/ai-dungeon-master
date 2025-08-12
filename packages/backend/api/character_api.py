from fastapi import APIRouter, Depends
from packages.backend.components.character_manager import CharacterManager
from packages.shared.error_handler import NotFoundError
from packages.shared.models import (
    AddCharacterRequest,
    UpdateCharacterRequest,
    RemoveCharacterRequest,
    ListCharactersRequest,
)

router = APIRouter(prefix="/characters", tags=["characters"])


@router.post("/add")
def add_character(
    req: AddCharacterRequest, character_manager: CharacterManager = Depends()
):
    character = character_manager.add_character(
        player_id=req.player_id,
        name=req.name,
        character_url=req.character_url,
    )
    return {"character_id": character.character_id}


@router.post("/update")
def update_character(
    req: UpdateCharacterRequest, character_manager: CharacterManager = Depends()
):
    result = character_manager.update_character(
        character_id=req.character_id,
        name=req.name,
        character_url=req.character_url,
    )
    return {"success": True}


@router.post("/remove")
def remove_character(
    req: RemoveCharacterRequest, character_manager: CharacterManager = Depends()
):
    result = character_manager.remove_character(character_id=req.character_id)
    if not result:
        raise NotFoundError("Character not found")
    return {"success": result}


@router.post("/list")
def list_characters(
    req: ListCharactersRequest, character_manager: CharacterManager = Depends()
):
    characters = character_manager.get_characters_for_player(player_id=req.player_id)
    return {"characters": characters}
