from pydantic import BaseModel, SecretStr, Field
import os
from typing import Literal


class ServerConfig(BaseModel):
    api_key: SecretStr = Field(
        default_factory=lambda: SecretStr(os.getenv("API_KEY", ""))
    )
    server_id: str
    api_key: SecretStr
    dm_roll_visibility: Literal["public", "hidden"]
    player_roll_mode: Literal[
        "manual_physical_total",
        "manual_physical_raw",
        "manual_digital",
        "auto_visible",
        "auto_hidden",
    ]
    character_sheet_mode: Literal["digital_sheet", "physical_sheet"]
