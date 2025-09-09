from fastapi import APIRouter, Depends

from packages.backend.components.character_manager import CharacterManager
from packages.shared.models import (
    AddCharacterRequest,
    CreateCharacterRequest,
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


@router.post("/create")
async def create_character(
    req: CreateCharacterRequest, character_manager: CharacterManager = Depends()
):
    character = await character_manager.create_character(
        player_id=req.player_id,
        name=req.name,
        species=req.species,
        class_index=req.class_index,
        subclass=req.subclass,
        background=req.background,
        strength=req.strength,
        dexterity=req.dexterity,
        constitution=req.constitution,
        intelligence=req.intelligence,
        wisdom=req.wisdom,
        charisma=req.charisma,
        prof_str_save=req.prof_str_save,
        prof_dex_save=req.prof_dex_save,
        prof_con_save=req.prof_con_save,
        prof_int_save=req.prof_int_save,
        prof_wis_save=req.prof_wis_save,
        prof_cha_save=req.prof_cha_save,
        prof_acrobatics=req.prof_acrobatics,
        prof_animal_handling=req.prof_animal_handling,
        prof_arcana=req.prof_arcana,
        prof_athletics=req.prof_athletics,
        prof_deception=req.prof_deception,
        prof_history=req.prof_history,
        prof_insight=req.prof_insight,
        prof_intimidation=req.prof_intimidation,
        prof_investigation=req.prof_investigation,
        prof_medicine=req.prof_medicine,
        prof_nature=req.prof_nature,
        prof_perception=req.prof_perception,
        prof_performance=req.prof_performance,
        prof_persuasion=req.prof_persuasion,
        prof_religion=req.prof_religion,
        prof_sleight_of_hand=req.prof_sleight_of_hand,
        prof_stealth=req.prof_stealth,
        prof_survival=req.prof_survival,
    )
    return {
        "message": "Character created successfully.",
        "character_id": character.character_id,
    }


@router.get("/classes")
async def get_classes(character_manager: CharacterManager = Depends()):
    classes = await character_manager.get_classes()
    return {"classes": classes}


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
