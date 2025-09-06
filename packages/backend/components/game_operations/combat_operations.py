from typing import Dict, List

from packages.backend.ai.tools.dice_roller import DiceRoller
from packages.shared.models.core_db_models import Character


def roll_initiative_for_participants(participants: List[Character]) -> List[Dict]:
    results = []
    for participant in participants:
        # get participant dex modifier
        roll = DiceRoller.roll_initiative(participant.dexterity_modifier)
        results.append(
            {
                "participant_id": participant.id,
                "name": participant.name,
                "roll": roll.rolls,
                "modifier": participant.dexterity_modifier,
                "total": roll.total,
            }
        )
    return sorted(results, key=lambda x: x["total"], reverse=True)
