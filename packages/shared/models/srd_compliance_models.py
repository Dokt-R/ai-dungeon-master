"""
SRD Compliance Models
SRD licensing and compliance data structures.
"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field as PydanticField


class SRDCompliance(BaseModel):
    """SRD licensing and compliance tracking."""

    data_source: str = PydanticField(
        ...,
        description="Official SRD source reference",
        examples=["Dungeons & Dragons 5.1 SRD", "Player's Handbook (SRD)"],
    )

    license_version: str = PydanticField(
        ..., description="SRD license version", examples=["5.1", "5.0"]
    )

    usage_restrictions: List[str] = PydanticField(
        default_factory=list,
        description="Documented usage restrictions",
        examples=[
            "Non-commercial use only",
            "Must attribute to Wizards of the Coast",
            "Cannot use for commercial products",
        ],
    )

    last_verified: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Last compliance verification date"
    )

    verification_hash: str = PydanticField(
        ...,
        description="Data integrity verification hash",
        examples=["sha256:abc123...", "md5:def456..."],
    )

    compliance_officer: Optional[str] = PydanticField(
        None,
        description="Person responsible for compliance verification",
        examples=["legal@company.com", "compliance@company.com"],
    )

    audit_trail: List[dict] = PydanticField(
        default_factory=list,
        description="Audit trail of compliance checks and updates",
        examples=[
            {
                "timestamp": "2024-01-01T12:00:00Z",
                "action": "verified",
                "details": "Verified against official SRD source",
            }
        ],
    )


class DataSource(BaseModel):
    """Source tracking for SRD data."""

    source_name: str = PydanticField(
        ...,
        description="Source document name",
        examples=["System Reference Document 5.1", "Player's Handbook SRD"],
    )

    source_url: str = PydanticField(
        ...,
        description="Official source URL",
        examples=["https://dnd.wizards.com/resources/systems-reference-document"],
    )

    publication_date: datetime = PydanticField(
        ..., description="Source publication date"
    )

    version: str = PydanticField(
        ..., description="SRD version", examples=["5.1", "5.0"]
    )

    checksum: str = PydanticField(
        ...,
        description="Source data checksum for integrity verification",
        examples=["sha256:abc123def456"],
    )

    is_official: bool = PydanticField(
        default=True,
        description="Whether this is an official Wizards of the Coast source",
    )

    attribution_required: bool = PydanticField(
        default=True,
        description="Whether attribution to Wizards of the Coast is required",
    )


class Monster(BaseModel):
    """SRD monster data structure with compliance tracking."""

    monster_id: Optional[int] = PydanticField(
        None, description="Unique monster identifier"
    )

    monster_name: str = PydanticField(
        ..., description="Official monster name", examples=["Goblin", "Orc", "Dragon"]
    )

    armor_class: int = PydanticField(
        ..., ge=0, le=50, description="Monster's armor class", examples=[12, 15, 18]
    )

    hit_points: str = PydanticField(
        ...,
        description="Hit point range or average",
        examples=["7 (2d4)", "15 (2d8+6)", "100 (8d12+48)"],
    )

    strength: int = PydanticField(
        ..., ge=1, le=30, description="Strength ability score", examples=[8, 14, 20]
    )

    dexterity: int = PydanticField(
        ..., ge=1, le=30, description="Dexterity ability score", examples=[14, 10, 12]
    )

    constitution: int = PydanticField(
        ...,
        ge=1,
        le=30,
        description="Constitution ability score",
        examples=[10, 14, 18],
    )

    intelligence: int = PydanticField(
        ..., ge=1, le=30, description="Intelligence ability score", examples=[8, 10, 12]
    )

    wisdom: int = PydanticField(
        ..., ge=1, le=30, description="Wisdom ability score", examples=[8, 12, 14]
    )

    charisma: int = PydanticField(
        ..., ge=1, le=30, description="Charisma ability score", examples=[8, 10, 12]
    )

    challenge_rating: str = PydanticField(
        ..., description="Challenge rating", examples=["1/4", "1", "5", "10"]
    )

    actions: Optional[str] = PydanticField(
        None,
        description="Monster's actions and abilities",
        examples=[
            "Scimitar. Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6 + 2) slashing damage."
        ],
    )

    special_abilities: Optional[str] = PydanticField(
        None,
        description="Special abilities and traits",
        examples=[
            "Nimble Escape. The goblin can take the Disengage or Hide action as a bonus action on each of its turns."
        ],
    )

    description: Optional[str] = PydanticField(
        None,
        description="Monster description and background",
        examples=[
            "Goblins are small, green-skinned humanoids with a mischievous and cruel nature."
        ],
    )

    srd_compliance: SRDCompliance = PydanticField(
        ..., description="Licensing compliance information"
    )

    data_source: DataSource = PydanticField(
        ..., description="Source tracking information"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Record creation timestamp"
    )

    updated_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Record last update timestamp"
    )

    is_active: bool = PydanticField(
        default=True, description="Whether this monster is active and available"
    )


class Spell(BaseModel):
    """SRD spell data structure with compliance tracking."""

    spell_id: Optional[int] = PydanticField(None, description="Unique spell identifier")

    spell_name: str = PydanticField(
        ...,
        description="Official spell name",
        examples=["Fireball", "Magic Missile", "Cure Wounds"],
    )

    level: int = PydanticField(
        ...,
        ge=0,
        le=9,
        description="Spell level (0-9, where 0 is cantrip)",
        examples=[1, 3, 5],
    )

    school: str = PydanticField(
        ...,
        description="Magic school",
        examples=["Evocation", "Conjuration", "Necromancy", "Abjuration"],
    )

    casting_time: str = PydanticField(
        ...,
        description="Spell casting time",
        examples=["1 action", "1 bonus action", "1 minute", "10 minutes"],
    )

    range: str = PydanticField(
        ...,
        description="Spell range",
        examples=["60 feet", "Touch", "120 feet", "Self (30-foot radius)"],
    )

    components: str = PydanticField(
        ...,
        description="Spell components (V, S, M)",
        examples=["V, S, M (a pinch of sulfur)", "V, S", "V"],
    )

    duration: str = PydanticField(
        ...,
        description="Spell duration",
        examples=[
            "Instantaneous",
            "Concentration, up to 1 minute",
            "1 hour",
            "Until dispelled",
        ],
    )

    description: str = PydanticField(
        ...,
        description="Complete spell description and mechanics",
        examples=[
            "A bright streak flashes from your pointing finger to a point you choose within range..."
        ],
    )

    at_higher_levels: Optional[str] = PydanticField(
        None,
        description="Effects when cast at higher levels",
        examples=[
            "When you cast this spell using a spell slot of 4th level or higher, the damage increases by 1d6 for each slot level above 3rd."
        ],
    )

    classes: List[str] = PydanticField(
        default_factory=list,
        description="Character classes that can use this spell",
        examples=[["Wizard", "Sorcerer"], ["Cleric", "Druid"], ["Bard"]],
    )

    srd_compliance: SRDCompliance = PydanticField(
        ..., description="Licensing compliance information"
    )

    data_source: DataSource = PydanticField(
        ..., description="Source tracking information"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Record creation timestamp"
    )

    updated_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Record last update timestamp"
    )

    is_active: bool = PydanticField(
        default=True, description="Whether this spell is active and available"
    )


class Weapon(BaseModel):
    """SRD weapon data structure with compliance tracking."""

    weapon_id: Optional[int] = PydanticField(
        None, description="Unique weapon identifier"
    )

    weapon_name: str = PydanticField(
        ...,
        description="Official weapon name",
        examples=["Longsword", "Shortbow", "Quarterstaff"],
    )

    category: str = PydanticField(
        ...,
        description="Weapon category",
        examples=["Simple", "Martial", "Ranged", "Melee"],
    )

    cost: str = PydanticField(
        ...,
        description="Weapon cost in gold pieces",
        examples=["15 gp", "25 gp", "2 gp"],
    )

    damage: str = PydanticField(
        ...,
        description="Weapon damage dice and type",
        examples=["1d8 slashing", "1d6 piercing", "1d6 bludgeoning"],
    )

    weight: str = PydanticField(
        ..., description="Weapon weight", examples=["3 lb.", "2 lb.", "4 lb."]
    )

    properties: List[str] = PydanticField(
        default_factory=list,
        description="Weapon properties",
        examples=[
            ["Versatile (1d10)"],
            ["Ammunition (range 80/320)"],
            ["Light", "Finesse"],
        ],
    )

    description: Optional[str] = PydanticField(
        None,
        description="Weapon description and special rules",
        examples=["This sword is about 3½ feet in length."],
    )

    srd_compliance: SRDCompliance = PydanticField(
        ..., description="Licensing compliance information"
    )

    data_source: DataSource = PydanticField(
        ..., description="Source tracking information"
    )

    created_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Record creation timestamp"
    )

    updated_at: datetime = PydanticField(
        default_factory=datetime.utcnow, description="Record last update timestamp"
    )

    is_active: bool = PydanticField(
        default=True, description="Whether this weapon is active and available"
    )