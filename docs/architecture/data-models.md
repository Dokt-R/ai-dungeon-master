# Data Models



The following Pydantic models define the core data structures for the application.



```python
from pydantic import BaseModel, SecretStr
from typing import List, Optional, Literal

class ServerConfig(BaseModel):
    server_id: str
    api_key: SecretStr
    dm_roll_visibility: Literal['public', 'hidden']
    player_roll_mode: Literal['manual_physical', 'manual_digital', 'auto_visible', 'auto_hidden']
    character_sheet_mode: Literal['digital_sheet', 'physical_sheet']

class Campaign(BaseModel):
    # The historical memory_log is now managed in a separate chronicle.yaml file
    # as per our tiered persistence strategy.
    campaign_id: str
    server_id: str
    name: str
    active_player_ids: List[str]

class PlayerCharacter(BaseModel):
    character_id: str
    player_discord_id: str
    campaign_id: str
    name: str
    character_sheet_url: Optional[str] = None
    preferred_output_mode: Literal['text', 'voice'] = 'text'
```

