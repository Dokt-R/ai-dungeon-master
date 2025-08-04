# Data Models



The following Pydantic models define the core data structures for the application.



```python
from pydantic import BaseModel, SecretStr, Field
from typing import List, Optional, Literal
from datetime import datetime

class Player(BaseModel):
    """Represents a player, typically a Discord user."""
    user_id: str = Field(..., description="Unique identifier for the player (e.g., Discord user ID).")
    username: Optional[str] = Field(None, description="The player's username (e.g., Discord username).")

class Character(BaseModel):
    """Represents a character in a campaign."""
    name: str = Field(..., description="The character's name.")
    dnd_beyond_url: Optional[str] = Field(None, description="Optional URL to a D&D Beyond character sheet.")

class PlayerCampaign(BaseModel):
    """Association model linking a Player to a Campaign."""
    id: int
    campaign_id: int
    player_id: str
    character_name: Optional[str] = None
    player_status: str
    joined_at: datetime
```
