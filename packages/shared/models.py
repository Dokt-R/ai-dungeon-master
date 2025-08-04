from pydantic import BaseModel, SecretStr, Field
from typing import Literal, Optional
from datetime import datetime


class ServerConfigModel(BaseModel):
    api_key: SecretStr = Field(
        ...,
        description="LLM API key used to authenticate with the backend",
    )

    dm_roll_visibility: Literal[
        "public",  # DM will announce his dice rolls to the players
        "hidden",  # DM will roll for himself and proceed with narrative
    ] = Field(
        "public",
        description="Server wide settings handling DM dice roll visibility",
    )

    # TODO: Refactor for player specific settings instead of system wide
    player_roll_mode: Literal[
        "physical",  # Player is prompted to roll physical dice
        "digital",  # Player is prompted to roll with /roll command
        "auto",  # DM uses /roll command for the player and announces the result
        "hidden",  # DM rolls behind the scenes and proceeds with the narrative
    ] = Field(
        "digital",
        description="Per player preferences handling dice rolls",
    )

    # TODO: Refactor for player specific settings instead of system wide
    character_sheet_mode: Literal[
        "digital_sheet",  # Players will use Digital DnD Beyond sheets
        "physical_sheet",  # Players will use Digital DnD Beyond sheets
    ] = Field(
        "digital_sheet",
        description="Server wide settings handing digital or physical character sheets preference",
    )


class ServerConfig(ServerConfigModel):
    server_id: str = Field(
        ...,
        description="Unique identifier for the discord server",
    )


class Player(BaseModel):
    """Represents a player, typically a Discord user."""

    user_id: str = Field(
        ..., description="Unique identifier for the player (e.g., Discord user ID)."
    )
    username: Optional[str] = Field(
        None, description="The player's username (e.g., Discord username)."
    )


class Character(BaseModel):
    """Represents a character in a campaign."""

    name: str = Field(..., description="The character's name.")
    dnd_beyond_url: Optional[str] = Field(
        None, description="Optional URL to a D&D Beyond character sheet."
    )


class PlayerCampaign(BaseModel):
    """Association model linking a Player to a Campaign."""

    id: int
    campaign_id: int
    player_id: str
    character_name: Optional[str] = None
    player_status: str
    joined_at: datetime
