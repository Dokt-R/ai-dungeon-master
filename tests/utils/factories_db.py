#! The code below is an example only and should be used as an idea for implementation
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from packages.shared.models import Campaign, Character, Player


def create_player(
    db: Session, player_id: str = None, username: str = None, **overrides
) -> Player:
    """Create and persist a Player in the test DB."""
    player = Player(
        player_id=player_id or str(uuid.uuid4()),
        username=username or f"user_{uuid.uuid4().hex[:6]}",
        created_at=datetime.utcnow(),
        campaigns=[],
        characters=[],
        **overrides,
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def create_campaign(
    db: Session, campaign_id: str = None, campaign_name: str = None, **overrides
) -> Campaign:
    """Create and persist a Campaign in the test DB."""
    campaign = Campaign(
        campaign_id=campaign_id or str(uuid.uuid4()),
        campaign_name=campaign_name or f"campaign_{uuid.uuid4().hex[:6]}",
        created_at=datetime.utcnow(),
        **overrides,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def create_character(
    db: Session, character_id: str = None, name: str = None, **overrides
) -> Character:
    """Create and persist a Character in the test DB."""
    character = Character(
        character_id=character_id or str(uuid.uuid4()),
        name=name or f"char_{uuid.uuid4().hex[:6]}",
        created_at=datetime.utcnow(),
        **overrides,
    )
    db.add(character)
    db.commit()
    db.refresh(character)
    return character
