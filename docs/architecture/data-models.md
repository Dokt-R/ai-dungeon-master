# Data Models

The following Pydantic models define the core data structures for the application, including both existing models and the new SRD (System Reference Document) models for D&D 5.1 rules integration.

## Core Application Models

```python
from pydantic import BaseModel, SecretStr, Field
from typing import List, Optional, Literal
from datetime import datetime

class Player(BaseModel):
    """Represents a player, typically a Discord user."""
    player_id: str = Field(..., description="Unique identifier for the player (e.g., Discord user ID).")
    username: Optional[str] = Field(None, description="The player's username (e.g., Discord username).")

class Character(BaseModel):
    """Represents a character in a campaign."""
    name: str = Field(..., description="The character's name.")
    character_url: Optional[str] = Field(None, description="Optional URL to a D&D Beyond character sheet.")

class PlayerCampaign(BaseModel):
    """Association model linking a Player to a Campaign."""
    id: int
    campaign_id: int
    player_id: str
    character_name: Optional[str] = None
    player_status: str
    joined_at: datetime
```

## SRD (D&D 5.1 System Reference Document) Models

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class SRDCompliance(BaseModel):
    """SRD licensing and compliance tracking."""
    data_source: str = Field(..., description="Official SRD source reference")
    license_version: str = Field(..., description="SRD license version (e.g., '5.1')")
    usage_restrictions: List[str] = Field(..., description="Documented usage restrictions under OGL 1.0a")
    last_verified: datetime = Field(..., description="Last compliance verification date")
    verification_hash: str = Field(..., description="Data integrity verification hash")
    compliance_officer: Optional[str] = Field(None, description="Officer responsible for compliance verification")
    audit_trail: List[str] = Field(default_factory=list, description="History of compliance actions")

class DataSource(BaseModel):
    """Source tracking for SRD data."""
    source_name: str = Field(..., description="Source document name (e.g., 'D&D 5.1 SRD')")
    source_url: str = Field(..., description="Official source URL")
    publication_date: datetime = Field(..., description="Source publication date")
    version: str = Field(..., description="SRD version")
    checksum: str = Field(..., description="Source data checksum for integrity verification")
    is_official: bool = Field(..., description="Whether this is an official WotC source")
    attribution_required: bool = Field(..., description="Whether attribution is required by license")

class Monster(BaseModel):
    """SRD monster data structure with compliance tracking."""
    monster_id: Optional[int] = Field(None, description="Database primary key")
    monster_name: str = Field(..., description="Official monster name")
    armor_class: int = Field(..., ge=5, le=25, description="Monster's armor class")
    hit_points: str = Field(..., description="Hit point range or average (e.g., '45 (7d8 + 14)')")
    strength: int = Field(..., ge=1, le=30, description="Strength ability score")
    dexterity: int = Field(..., ge=1, le=30, description="Dexterity ability score")
    constitution: int = Field(..., ge=1, le=30, description="Constitution ability score")
    intelligence: int = Field(..., ge=1, le=30, description="Intelligence ability score")
    wisdom: int = Field(..., ge=1, le=30, description="Wisdom ability score")
    charisma: int = Field(..., ge=1, le=30, description="Charisma ability score")
    challenge_rating: str = Field(..., description="Challenge rating (e.g., '2', '1/4', '5')")
    actions: Optional[str] = Field(None, description="Monster's actions and abilities")
    special_abilities: Optional[str] = Field(None, description="Special abilities and traits")
    description: Optional[str] = Field(None, description="Monster description and background")
    srd_compliance: SRDCompliance = Field(..., description="Licensing compliance information")
    data_source: DataSource = Field(..., description="Source attribution and verification")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Record last update timestamp")
    is_active: bool = Field(default=True, description="Whether this record is active")

class Spell(BaseModel):
    """SRD spell data structure with compliance tracking."""
    spell_id: Optional[int] = Field(None, description="Database primary key")
    spell_name: str = Field(..., description="Official spell name")
    level: int = Field(..., ge=0, le=9, description="Spell level (0-9, where 0 = cantrip)")
    school: str = Field(..., description="Spell school (e.g., 'Evocation', 'Conjuration')")
    casting_time: str = Field(..., description="Spell casting time (e.g., '1 action', '1 bonus action')")
    range: str = Field(..., description="Spell range (e.g., '120 feet', 'Self', 'Touch')")
    components: str = Field(..., description="Spell components (e.g., 'V, S, M (a handful of sand)')")
    duration: str = Field(..., description="Spell duration (e.g., 'Concentration, up to 1 minute')")
    description: str = Field(..., description="Complete spell description and mechanics")
    at_higher_levels: Optional[str] = Field(None, description="Effects when cast at higher levels")
    classes: List[str] = Field(..., description="Character classes that can cast this spell")
    srd_compliance: SRDCompliance = Field(..., description="Licensing compliance information")
    data_source: DataSource = Field(..., description="Source attribution and verification")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Record last update timestamp")
    is_active: bool = Field(default=True, description="Whether this record is active")

class Weapon(BaseModel):
    """SRD weapon data structure with compliance tracking."""
    weapon_id: Optional[int] = Field(None, description="Database primary key")
    weapon_name: str = Field(..., description="Official weapon name")
    category: str = Field(..., description="Weapon category (e.g., 'Martial Melee Weapons')")
    cost: str = Field(..., description="Weapon cost (e.g., '15 gp', '5 sp')")
    damage: str = Field(..., description="Weapon damage (e.g., '1d8 slashing', '2d6 piercing')")
    weight: str = Field(..., description="Weapon weight (e.g., '3 lb.', '0.5 lb.')")
    properties: List[str] = Field(..., description="Weapon properties (e.g., ['Finesse', 'Light'])")
    description: Optional[str] = Field(None, description="Weapon description and special rules")
    srd_compliance: SRDCompliance = Field(..., description="Licensing compliance information")
    data_source: DataSource = Field(..., description="Source attribution and verification")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Record last update timestamp")
    is_active: bool = Field(default=True, description="Whether this record is active")

class RulesQuery(BaseModel):
    """Query structure for SRD rules requests."""
    query_type: str = Field(..., description="Type of SRD query ('monster', 'spell', 'weapon')")
    name: str = Field(..., description="Name to look up in SRD database")
    context: Optional[str] = Field(None, description="Context for the query (e.g., 'encounter', 'combat')")
    filters: Optional[dict] = Field(None, description="Additional query filters")

class RulesResponse(BaseModel):
    """Response structure for SRD rules queries."""
    query_type: str = Field(..., description="Type of query processed")
    name: str = Field(..., description="Original query name")
    found: bool = Field(..., description="Whether the item was found in SRD")
    data: Optional[dict] = Field(None, description="SRD data if found")
    error: Optional[str] = Field(None, description="Error message if query failed")
    query_time: float = Field(..., description="Query execution time in seconds")

class AccuracyValidation(BaseModel):
    """AI response accuracy validation result."""
    query: str = Field(..., description="Original query that was asked")
    ai_response: str = Field(..., description="AI's response to validate")
    expected_answer: str = Field(..., description="Expected correct answer from SRD")
    accuracy_score: float = Field(..., ge=0.0, le=1.0, description="Accuracy score (0-1)")
    validation_details: List[str] = Field(..., description="Details about validation results")
    validation_date: datetime = Field(default_factory=datetime.utcnow, description="When validation was performed")

class ToolCall(BaseModel):
    """LangGraph tool call structure for SRD queries."""
    tool_name: str = Field(..., description="Name of the tool to call")
    tool_args: dict = Field(..., description="Arguments for the tool call")
    query_type: str = Field(..., description="Type of SRD query")
    confidence_threshold: float = Field(default=0.8, description="Minimum confidence for tool usage")

class ToolResult(BaseModel):
    """Result structure for SRD tool calls."""
    tool_name: str = Field(..., description="Name of the tool that was called")
    success: bool = Field(..., description="Whether the tool call was successful")
    data: Optional[dict] = Field(None, description="Tool result data")
    error: Optional[str] = Field(None, description="Error message if tool failed")
    execution_time: float = Field(..., description="Tool execution time in seconds")
```

## Model Relationships

- **SRD Models** extend base models with compliance tracking
- **RulesQuery/Response** provide the API for RulesEngine interactions
- **AccuracyValidation** enables AI response quality assessment
- **ToolCall/ToolResult** support LangGraph tool integration
- All models include comprehensive validation and type safety
