from pydantic import BaseModel, SecretStr, Field
from typing import Literal


class ServerConfigModel(BaseModel):
    api_key: SecretStr = Field(
        ...,
        description="LLM API key used to authenticate with the backend",
    )

    dm_roll_visibility: Literal["public", # DM will announce his dice rolls to the players
                                "hidden"  # DM will roll for himself and proceed with narrative
                                ] = Field(
        "public",
        description="Server wide settings handling DM dice roll visibility",
    )

    # TODO: Refactor for player specific settings instead of system wide
    player_roll_mode: Literal[
        "physical", # Player is prompted to roll physical dice
        "digital", # Player is prompted to roll with /roll command
        "auto", # DM uses /roll command for the player and announces the result
        "hidden", # DM rolls behind the scenes and proceeds with the narrative
    ] = Field(
        "digital",
        description="Per player preferences handling dice rolls",
    )

    # TODO: Refactor for player specific settings instead of system wide
    character_sheet_mode: Literal[
        "digital_sheet", # Players will use Digital DnD Beyond sheets
        "physical_sheet" # Players will use Digital DnD Beyond sheets
        ] = Field(
        "digital_sheet",
        description="Server wide settings handing digital or physical character sheets preference",
    )


class ServerConfig(ServerConfigModel):
    server_id: str = Field(
        ...,
        description="Unique identifier for the discord server",
    )
