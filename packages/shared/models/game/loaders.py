from typing import Any, Dict

from packages.shared.models.core_db_models import Character
from packages.shared.models.game.creature_models import NPC, Monster
from packages.shared.models.langgraph_state_models import CombatParticipant, CombatState


# Helper class for loading full creature data when needed
class CombatCreatureLoader:
    """Utility class to load creature data into combat state when needed"""

    def __init__(self, session):
        self.session = session

    def load_creature(self, participant_key: str):
        """Load full creature data by key"""
        creature_type, creature_id = participant_key.split("_")

        if creature_type == "character":
            return self.session.get(Character, int(creature_id))
        elif creature_type == "npc":
            return self.session.get(NPC, int(creature_id))
        elif creature_type == "monster":
            return self.session.get(Monster, int(creature_id))
        else:
            raise ValueError(f"Unknown creature type: {creature_type}")

    def load_participants_data(self, state: CombatState) -> Dict[str, Any]:
        """Load full data for all participants in combat"""
        participants_data = {}

        for participant_id, participant_key in state["participants"].items():
            # Load participant record
            participant = self.session.get(CombatParticipant, int(participant_id))

            # Load creature data if needed for complex operations
            creature = self.load_creature(participant_key)

            participants_data[participant_id] = {
                "participant": participant,
                "creature": creature,  # Full stats when needed
            }

        return participants_data

    def sync_participant_stats(self, participant: CombatParticipant):
        """Sync participant stats from source creature (for initiative, etc.)"""
        creature = self.load_creature(participant.participant_key)

        # Sync stats that might change
        participant.max_hp = creature.max_hp
        participant.initiative_modifier = creature.dex_modifier

        # Only sync current HP if participant is newly created
        if participant.current_hp is None:
            participant.current_hp = creature.hp


# Combat utility functions
def create_combat_participant(
    participant_key: str, campaign_id: int, session
) -> CombatParticipant:
    """Factory function to create a CombatParticipant from a creature"""
    creature_type, creature_id = participant_key.split("_")

    # Load the source creature
    loader = CombatCreatureLoader(session)
    creature = loader.load_creature(participant_key)

    participant = CombatParticipant(
        # combat_id=combat_id,
        campaign_id=campaign_id,
        creature_type=creature_type,
        creature_id=int(creature_id),
        creature_name=creature.name,
        current_hp=creature.hp,
        max_hp=creature.max_hp,
        initiative_modifier=creature.dex_modifier,
    )

    return participant
