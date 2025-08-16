from fastapi import APIRouter, Depends

from packages.backend.components.character_manager import CharacterManager
from packages.shared.models import (
    AddCharacterRequest,
    ListCharactersRequest,
    RemoveCharacterRequest,
    UpdateCharacterRequest,
)

router = APIRouter(prefix="/characters", tags=["characters"])


@router.post("/add")
async def add_character(
    req: AddCharacterRequest, character_manager: CharacterManager = Depends()
):
    character = await character_manager.add_character(
        player_id=req.player_id,
        name=req.name,
        character_url=req.character_url,
    )
    return {
        "message": "Character created successfully.",
        "character_id": character.character_id,
    }


@router.post("/update")
async def update_character(
    req: UpdateCharacterRequest, character_manager: CharacterManager = Depends()
):
    await character_manager.update_character(
        character_id=req.character_id,
        name=req.name,
        character_url=req.character_url,
    )
    return {"success": True}


@router.post("/remove")
async def remove_character(
    req: RemoveCharacterRequest, character_manager: CharacterManager = Depends()
):
    result = await character_manager.remove_character(character_id=req.character_id)
    return {"success": result}


@router.post("/list")
async def list_characters(
    req: ListCharactersRequest, character_manager: CharacterManager = Depends()
):
    characters = await character_manager.get_characters_for_player(
        player_id=req.player_id
    )
    return {"characters": characters}
