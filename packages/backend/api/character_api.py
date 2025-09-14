from typing import Optional

from fastapi import APIRouter, Depends

from packages.backend.components.character_manager import CharacterManager
from packages.shared.models.api_request_models import (
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
        races_index=req.races_index,
        class_index=req.class_index,
        subclass=req.subclass,
        background_index=req.background_index,
        strength=req.strength,
        dexterity=req.dexterity,
        constitution=req.constitution,
        intelligence=req.intelligence,
        wisdom=req.wisdom,
        charisma=req.charisma,
        proficiencies=req.proficiencies,
        inventory=req.inventory,
    )
    return {
        "message": "Character created successfully.",
        "character_id": character.character_id,
    }


@router.get("/classes")
async def get_classes(character_manager: CharacterManager = Depends()):
    classes = await character_manager.get_classes()
    return {"classes": classes}


@router.get("/subclasses")
async def get_subclasses(character_manager: CharacterManager = Depends()):
    subclasses = await character_manager.get_subclasses()
    return {"subclasses": subclasses}


@router.get("/backgrounds")
async def get_backgrounds(character_manager: CharacterManager = Depends()):
    backgrounds = await character_manager.get_backgrounds()
    return {"backgrounds": backgrounds}


@router.get("/races")
async def get_races(character_manager: CharacterManager = Depends()):
    races = await character_manager.get_races()
    return {"races": races}


@router.get("/subraces")
async def get_subraces(character_manager: CharacterManager = Depends()):
    subraces = await character_manager.get_subraces()
    return {"subraces": subraces}


@router.get("/abilities")
async def get_abilities(character_manager: CharacterManager = Depends()):
    abilities = await character_manager.get_abilities()
    return {"abilities": abilities}


@router.get("/skills")
async def get_skills(character_manager: CharacterManager = Depends()):
    skills = await character_manager.get_skills()
    return {"skills": skills}


@router.get("/conditions")
async def get_conditions(character_manager: CharacterManager = Depends()):
    conditions = await character_manager.get_conditions()
    return {"conditions": conditions}


@router.get("/alignments")
async def get_alignments(character_manager: CharacterManager = Depends()):
    alignments = await character_manager.get_alignments()
    return {"alignments": alignments}


@router.get("/magic_schools")
async def get_magic_schools(character_manager: CharacterManager = Depends()):
    magic_schools = await character_manager.get_magic_schools()
    return {"magic_schools": magic_schools}


@router.get("/languages")
async def get_languages(character_manager: CharacterManager = Depends()):
    languages = await character_manager.get_languages()
    return {"languages": languages}


@router.get("/traits")
async def get_traits(character_manager: CharacterManager = Depends()):
    traits = await character_manager.get_traits()
    return {"traits": traits}

@router.get("/proficiencies")
async def get_proficiencies(character_manager: CharacterManager = Depends()):
    proficiencies = await character_manager.get_proficiencies()
    return {"proficiencies": proficiencies}


@router.get("/spells")
async def get_spells(character_manager: CharacterManager = Depends()):
    spells = await character_manager.get_spells()
    return {"spells": spells}


@router.get("/feats")
async def get_feats(character_manager: CharacterManager = Depends()):
    feats = await character_manager.get_feats()
    return {"feats": feats}


@router.get("/features")
async def get_features(character_manager: CharacterManager = Depends()):
    features = await character_manager.get_features()
    return {"features": features}


@router.get("/monsters")
async def get_monsters(character_manager: CharacterManager = Depends()):
    monsters = await character_manager.get_monsters()
    return {"monsters": monsters}

@router.get("/equipment")
async def get_equipment(
    category_index: Optional[str] = None, character_manager: CharacterManager = Depends()
):
    """
    Get equipment, optionally filtered by category.
    """
    equipment = await character_manager.get_equipment(category_index=category_index)
    return {"equipment": equipment}

@router.get("/equipment/pack/{pack_index}")
async def get_pack_contents(
    pack_index: str, character_manager: CharacterManager = Depends()
):
    """
    Get the contents of an equipment pack.
    """
    contents = await character_manager.get_pack_contents(pack_index=pack_index)
    return {"contents": contents}


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
