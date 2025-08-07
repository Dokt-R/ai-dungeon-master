from fastapi import APIRouter
from packages.backend.components.character_manager import CharacterManager
from packages.shared.error_handler import fastapi_error_handler, NotFoundError
from packages.shared.models import (
    AddCharacterRequest,
    UpdateCharacterRequest,
    RemoveCharacterRequest,
    ListCharactersRequest,
)

router = APIRouter(prefix="/characters", tags=["characters"])
character_manager = CharacterManager()


@router.post("/add")
@fastapi_error_handler
def add_character(req: AddCharacterRequest):
    character = character_manager.add_character(
        player_id=req.player_id,
        name=req.name,
        character_url=req.character_url,
    )
    return {"character_id": character.character_id}


@router.post("/update")
@fastapi_error_handler
def update_character(req: UpdateCharacterRequest):
    result = character_manager.update_character(
        character_id=req.character_id,
        name=req.name,
        character_url=req.character_url,
    )
    return {"success": True}


@router.post("/remove")
@fastapi_error_handler
def remove_character(req: RemoveCharacterRequest):
    result = character_manager.remove_character(character_id=req.character_id)
    if not result:
        raise NotFoundError("Character not found")
    return {"success": result}


@router.post("/list")
@fastapi_error_handler
def list_characters(req: ListCharactersRequest):
    characters = character_manager.get_characters_for_player(player_id=req.player_id)
    return {"characters": characters}
